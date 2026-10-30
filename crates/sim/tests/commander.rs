//! WP-S2: the scripted commander and order-following scripted pilots
//! (SIM_SPEC §5.9 "Scripted commander", §11 "Squad orders").

mod common;

use common::asset_catalogue;
use sim::command::{COMMAND_TICKS, Command, CommanderMode, Order, Squad};
use sim::data::{Catalogue, HullId};
use sim::events::Event;
use sim::math::{Vec2, wrap_angle};
use sim::mission::{Mission, MissionKind, default_rosters};
use sim::scripted;
use sim::scripted::commander::LAUNCH_INTERVAL_TICKS;
use sim::setup::MatchConfig;
use sim::state::{Match, MatchPhase};

fn ids(cat: &Catalogue, names: &[&str]) -> Vec<HullId> {
    names.iter().map(|n| cat.hull_id(n).unwrap()).collect()
}

fn scripted_step(m: &mut Match, cat: &Catalogue) {
    for i in 0..m.ships().len() {
        let a = scripted::act(m, cat, i as u8);
        m.set_action(i as u8, a);
    }
    m.step(cat);
}

/// The first default roster of `kind`, its default clock and parameters.
fn default_match(cat: &Catalogue, kind: MissionKind, seed: u64) -> Match {
    let r = default_rosters(kind)[0];
    let cfg = MatchConfig {
        seed,
        fleets: [ids(cat, r.fleets[0]), ids(cat, r.fleets[1])],
        time_limit_ticks: kind.default_time_limit_ticks(),
        mission: Mission::standard(kind, 450.0),
        ..MatchConfig::default()
    };
    Match::new(cat, &cfg).unwrap()
}

#[test]
fn every_default_roster_sets_up() {
    let cat = asset_catalogue();
    for kind in [MissionKind::CarrierBattle, MissionKind::ConvoyEscort] {
        let rosters = default_rosters(kind);
        assert!(rosters.len() >= 2);
        for r in rosters {
            let cfg = MatchConfig {
                fleets: [ids(&cat, r.fleets[0]), ids(&cat, r.fleets[1])],
                mission: Mission::standard(kind, 450.0),
                ..MatchConfig::default()
            };
            Match::new(&cat, &cfg).unwrap_or_else(|e| panic!("{}: {e:?}", r.name));
        }
    }
    assert!(default_rosters(MissionKind::Deathmatch).is_empty());
}

#[test]
fn carrier_commander_guards_strikes_and_paces_launches() {
    let cat = asset_catalogue();
    let mut m = default_match(&cat, MissionKind::CarrierBattle, 3);
    let mut launches: [Vec<u32>; 2] = [Vec::new(), Vec::new()];
    while m.tick() < 30 * 60 && m.phase() == MatchPhase::Running {
        scripted_step(&mut m, &cat);
        for e in m.events() {
            if let Event::Launch { carrier, .. } = e {
                let team = usize::from(m.ships[usize::from(*carrier)].team);
                launches[team].push(m.tick());
            }
        }
        if m.tick() == COMMAND_TICKS {
            for team in 0..2u8 {
                let own = m.carrier_of(team);
                let foe = m.carrier_of(1 - team);
                let [guard, strike, ..] = m.command.squads[usize::from(team)];
                assert_eq!(guard.order, Order::Guard { ward: own }, "team {team}");
                assert!(!guard.is_empty() && !strike.is_empty());
                // The enemy carrier, or (its escort outnumbering the strike) an enemy.
                let Order::Attack { target } = strike.order else {
                    panic!("team {team} strikes: {:?}", strike.order)
                };
                assert!(target == foe || m.ships[usize::from(target)].team != team);
            }
        }
    }
    for (team, ticks) in launches.iter().enumerate() {
        // The first launch is on the first slow tick, and the hangar is not emptied
        // in the opening: launches spread over at least three slow ticks.
        assert_eq!(
            ticks.first(),
            Some(&COMMAND_TICKS),
            "team {team}: {ticks:?}"
        );
        let mut distinct = ticks.clone();
        distinct.dedup();
        assert!(distinct.len() >= 3, "team {team}: {ticks:?}");
        // Outside a scramble (two launches on one slow tick) they are paced.
        let singles: Vec<u32> = distinct
            .iter()
            .copied()
            .filter(|t| ticks.iter().filter(|u| *u == t).count() == 1)
            .collect();
        for w in singles.windows(2) {
            assert!(
                w[1] - w[0] >= LAUNCH_INTERVAL_TICKS || w[1] - w[0] == COMMAND_TICKS,
                "team {team}: {ticks:?}"
            );
        }
    }
}

/// Order changes per squad over a whole scripted match of every mission: each is a
/// line in the command log, so they must be events, not noise.
#[test]
fn orders_change_rarely() {
    let cat = asset_catalogue();
    for (kind, seed) in [
        (MissionKind::CarrierBattle, 5),
        (MissionKind::ConvoyEscort, 6),
        (MissionKind::CarrierBattle, 7),
        (MissionKind::ConvoyEscort, 8),
    ] {
        let mut m = default_match(&cat, kind, seed);
        let mut changes = [[0u32; 4]; 2];
        let mut last = [[0u32; 4]; 2];
        let mut back_to_back = 0;
        while m.phase() == MatchPhase::Running {
            scripted_step(&mut m, &cat);
            for e in m.events() {
                if let Event::Order { team, squad, .. } = e {
                    let (t, k) = (usize::from(*team), usize::from(*squad));
                    changes[t][k] += 1;
                    if changes[t][k] > 1 && m.tick() - last[t][k] == COMMAND_TICKS {
                        back_to_back += 1;
                    }
                    last[t][k] = m.tick();
                }
            }
        }
        let slow_ticks = m.tick() / COMMAND_TICKS;
        let worst = changes.iter().flatten().max().copied().unwrap();
        assert!(
            worst * 3 <= slow_ticks.max(9),
            "{kind:?}: a squad changed order {worst} times in {slow_ticks} slow ticks"
        );
        assert!(
            back_to_back * 4 <= slow_ticks,
            "{kind:?}: {back_to_back} changes on consecutive slow ticks"
        );
    }
}

#[test]
fn convoy_commanders_guard_intercept_and_send_waves() {
    let cat = asset_catalogue();
    let mut m = default_match(&cat, MissionKind::ConvoyEscort, 4);
    while m.tick() < COMMAND_TICKS {
        scripted_step(&mut m, &cat);
    }
    let [guard, intercept, ..] = m.command.squads[0];
    let Order::Guard { ward } = guard.order else {
        panic!("defenders guard: {:?}", guard.order)
    };
    assert!(
        m.mission.transports & (1 << ward) != 0,
        "the ward is a transport"
    );
    assert!(matches!(
        intercept.order,
        Order::Attack { .. } | Order::Hold { .. }
    ));
    let [one, two, ..] = m.command.squads[1];
    let Order::Attack { target } = one.order else {
        panic!("wave 1 attacks: {:?}", one.order)
    };
    assert!(m.mission.transports & (1 << target) != 0, "at a transport");
    assert!(matches!(two.order, Order::Hold { .. }), "wave 2 stages");
    assert_eq!(one.len() + two.len(), 6);
    // Wave 2 goes in by 30 s, on a transport.
    while m.tick() < 30 * 31 && m.phase() == MatchPhase::Running {
        scripted_step(&mut m, &cat);
    }
    let two = m.command.squads[1][1];
    if let Order::Attack { target } = two.order {
        assert!(m.mission.transports & (1 << target) != 0);
    } else {
        assert!(two.is_empty(), "wave 2 committed: {:?}", two.order);
    }
}

/// A 1v2 deathmatch with external commanders: one fighter, two enemies parked
/// (never moving: they arrive but fly IDLE because the test steps them idle).
fn ordered_duel(cat: &Catalogue) -> Match {
    let cfg = MatchConfig {
        seed: 2,
        fleets: [ids(cat, &["fighter"]), ids(cat, &["fighter", "fighter"])],
        commanders: [CommanderMode::External; 2],
        time_limit_ticks: 100_000,
        ..MatchConfig::default()
    };
    let mut m = Match::new(cat, &cfg).unwrap();
    for (s, pos) in [
        (0, Vec2::ZERO),
        (1, Vec2::new(100.0, 0.0)),
        (2, Vec2::new(0.0, 300.0)),
    ] {
        let ship = &mut m.ships[s];
        ship.present = true;
        ship.pos = pos;
        ship.vel = Vec2::ZERO;
        ship.heading = 0.0;
        ship.arrive_tick = 0;
        ship.control_lock_until = 0;
    }
    m
}

/// Step with ship 0 scripted and everyone else idle.
fn step_ship0(m: &mut Match, cat: &Catalogue) {
    let a = scripted::act(m, cat, 0);
    m.set_action(0, a);
    m.step(cat);
}

#[test]
fn scripted_pilot_attacks_its_ordered_target_not_the_nearest() {
    let cat = asset_catalogue();
    let mut m = ordered_duel(&cat);
    // Ordered from the first tick (as if the last slow tick had set it).
    m.command.squads[0][0] = Squad {
        members: 1,
        order: Order::Attack { target: 2 },
    };
    while m.tick() < 45 {
        step_ship0(&mut m, &cat);
    }
    let off = |target: usize| {
        let bearing = (m.ships[target].pos - m.ships[0].pos).angle();
        wrap_angle(m.ships[0].heading - bearing).abs()
    };
    // Nose on the ordered target (within its lead), away from the nearer one.
    assert!(
        off(2) < 0.8 && off(1) > 1.2,
        "turned to the ordered target: off {} (ordered), {} (nearest)",
        off(2),
        off(1)
    );
    // Without an order it takes the nearest.
    let mut n = ordered_duel(&cat);
    while n.tick() < 45 {
        step_ship0(&mut n, &cat);
    }
    assert!(n.ships[0].heading.abs() < 0.3, "{}", n.ships[0].heading);
}

#[test]
fn scripted_pilot_holds_a_point_with_nobody_near_it() {
    let cat = asset_catalogue();
    let mut m = ordered_duel(&cat);
    // Enemies far from the hold point: the pilot keeps station rather than fighting.
    let point = Vec2::new(-250.0, -200.0);
    m.submit_command(
        0,
        Command::Squad {
            squad: 0,
            members: 1,
            order: Order::Hold {
                point,
                radius: 40.0,
            },
        },
    );
    while m.tick() < 30 * 40 {
        step_ship0(&mut m, &cat);
    }
    let d = (m.ships[0].pos - point).length();
    assert!(d < 60.0, "kept station {d} m from the hold point");
}

/// In a deathmatch under the scripted commander the orders exist but are only
/// shown: every scripted action equals the action with the squads cleared.
#[test]
fn scripted_deathmatch_orders_are_advisory() {
    let cat = asset_catalogue();
    let cfg = MatchConfig {
        seed: 9,
        fleets: [
            ids(&cat, &["fighter", "strafer", "gunship"]),
            ids(&cat, &["gunship", "fighter", "strafer"]),
        ],
        ..MatchConfig::default()
    };
    let mut m = Match::new(&cat, &cfg).unwrap();
    let mut checked = 0;
    while m.tick() < 30 * 40 && m.phase() == MatchPhase::Running {
        if m.command.squads[0][0].order != Order::None {
            let mut bare = m.clone();
            bare.command = Default::default();
            for i in 0..m.ships().len() as u8 {
                assert_eq!(scripted::act(&m, &cat, i), scripted::act(&bare, &cat, i));
            }
            checked += 1;
        }
        scripted_step(&mut m, &cat);
    }
    assert!(checked > 100, "orders were set: {checked}");
}
