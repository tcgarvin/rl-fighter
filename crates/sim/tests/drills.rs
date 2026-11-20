//! Start layouts and drill rules (`MatchConfig.start_layout`, `MatchConfig.drill`;
//! SIM_SPEC §5.10). The goldens in `determinism.rs` pin that a match without them is
//! unchanged.

mod common;

use common::asset_catalogue;
use sim::command::{Command, CommanderMode, NO_DEADLINE, Order};
use sim::data::{Catalogue, HullId};
use sim::math::Vec2;
use sim::mission::{EndReason, Mission};
use sim::order;
use sim::scripted;
use sim::setup::{MatchConfig, SetupError, ShipStart};
use sim::state::{Match, MatchPhase, WINNER_DRAW};

fn ids(cat: &Catalogue, names: &[&str]) -> Vec<HullId> {
    names.iter().map(|n| cat.hull_id(n).unwrap()).collect()
}

fn at(x: f32, y: f32) -> ShipStart {
    ShipStart {
        pos: Vec2::new(x, y),
        vel: Vec2::ZERO,
        heading: 0.0,
    }
}

fn placed(cat: &Catalogue, team0: &[&str], team1: &[&str], layout: Vec<ShipStart>) -> MatchConfig {
    MatchConfig {
        seed: 7,
        fleets: [ids(cat, team0), ids(cat, team1)],
        commanders: [CommanderMode::External; 2],
        start_layout: Some(layout),
        ..MatchConfig::default()
    }
}

fn drill(cat: &Catalogue, team0: &[&str], team1: &[&str], layout: Vec<ShipStart>) -> MatchConfig {
    MatchConfig {
        drill: true,
        time_limit_ticks: 300,
        ..placed(cat, team0, team1, layout)
    }
}

fn scripted_step(m: &mut Match, cat: &Catalogue) {
    for i in 0..m.ships().len() {
        let a = scripted::act(m, cat, i as u8);
        m.set_action(i as u8, a);
    }
    m.step(cat);
}

fn squad(members: u32, order: Order) -> Command {
    Command::Squad {
        squad: 0,
        members,
        order,
    }
}

#[test]
fn ships_start_where_the_layout_says_and_can_act_at_once() {
    let cat = asset_catalogue();
    let start = ShipStart {
        pos: Vec2::new(-120.0, 35.0),
        vel: Vec2::new(5.0, -12.0),
        heading: 1.25,
    };
    let cfg = placed(
        &cat,
        &["fighter"],
        &["gunship", "strafer"],
        vec![start, at(200.0, 0.0), at(200.0, 60.0)],
    );
    let m = Match::new(&cat, &cfg).unwrap();
    let ship = &m.ships()[0];
    assert_eq!(ship.pos, start.pos);
    assert_eq!(ship.vel, start.vel);
    assert_eq!(ship.heading, start.heading);
    assert!(ship.present && ship.active());
    assert_eq!(ship.control_lock_until, 0);
    assert_eq!(m.ships()[2].pos, Vec2::new(200.0, 60.0));
    assert!(sim::actions::act_mask(ship, m.tick()));
}

#[test]
fn a_layout_draws_nothing_from_the_match_rng() {
    let cat = asset_catalogue();
    let cfg = placed(
        &cat,
        &["fighter"],
        &["fighter"],
        vec![at(-100.0, 0.0), at(100.0, 0.0)],
    );
    let m = Match::new(&cat, &cfg).unwrap();
    assert_eq!(m.rng, sim::rng::Pcg32::new(cfg.seed));
}

#[test]
fn a_layout_without_drill_rules_still_pays_the_result() {
    let cat = asset_catalogue();
    let cfg = placed(
        &cat,
        &["fighter"],
        &["fighter"],
        vec![at(-100.0, 0.0), at(100.0, 0.0)],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.ships[1].hp = 0.0;
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), 0);
    assert!(m.rewards()[0] >= 1.0 - 1e-3);
}

#[test]
fn bad_layouts_are_refused_at_the_boundary() {
    let cat = asset_catalogue();
    let duel = |layout: Vec<ShipStart>| placed(&cat, &["fighter"], &["fighter"], layout);
    let refused = |cfg: MatchConfig, says: &str| match Match::new(&cat, &cfg).map(|_| ()) {
        Err(SetupError::StartLayout(msg)) => {
            assert!(msg.contains(says), "{msg:?} should mention {says:?}");
        }
        other => panic!("expected a layout error about {says:?}, got {other:?}"),
    };
    refused(duel(vec![at(0.0, 0.0)]), "1 entries for 2 ships");
    refused(duel(vec![at(0.0, 0.0), at(f32::NAN, 0.0)]), "non-finite");
    refused(
        duel(vec![at(0.0, 0.0), at(451.0, 0.0)]),
        "outside the arena",
    );
    refused(duel(vec![at(0.0, 0.0), at(1.0, 0.0)]), "overlap");
    let mut fast = at(100.0, 0.0);
    fast.vel = Vec2::new(61.0, 0.0);
    refused(duel(vec![at(0.0, 0.0), fast]), "speed cap");
    let convoy = MatchConfig {
        fleets: [ids(&cat, &["freighter"]), ids(&cat, &["fighter"])],
        mission: Mission::standard(sim::mission::MissionKind::ConvoyEscort, 450.0),
        start_layout: Some(vec![at(-100.0, 0.0), at(100.0, 0.0)]),
        ..MatchConfig::default()
    };
    refused(convoy, "a convoy escort places its own ships");
    let mut weak = duel(vec![at(-100.0, 0.0), at(100.0, 0.0)]);
    weak.start_hull = Some(vec![0.5]);
    refused(weak.clone(), "start_hull has 1 entries for 2 ships");
    weak.start_hull = Some(vec![0.5, 0.0]);
    refused(weak.clone(), "slot 1 start hull 0 is not in (0, 1]");
    weak.start_hull = Some(vec![f32::NAN, 1.0]);
    refused(weak, "slot 0 start hull NaN");
    let unplaced = MatchConfig {
        fleets: [ids(&cat, &["fighter"]), ids(&cat, &["fighter"])],
        start_hull: Some(vec![0.5, 1.0]),
        ..MatchConfig::default()
    };
    refused(unplaced, "start_hull needs a start_layout");
    let no_layout = MatchConfig {
        fleets: [ids(&cat, &["fighter"]), ids(&cat, &["fighter"])],
        drill: true,
        ..MatchConfig::default()
    };
    refused(no_layout, "need a start_layout");
}

#[test]
fn drill_ends_on_the_clock_as_a_draw_with_no_terminal_pay() {
    let cat = asset_catalogue();
    let cfg = drill(
        &cat,
        &["fighter"],
        &["fighter"],
        vec![at(-400.0, 0.0), at(400.0, 0.0)],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    while m.phase() == MatchPhase::Running {
        m.step(&cat);
        assert_eq!(
            m.rewards()[0],
            0.0,
            "tick {}: idle ships earn nothing",
            m.tick()
        );
    }
    assert_eq!(m.tick(), 300);
    assert_eq!(m.winner(), WINNER_DRAW);
    assert_eq!(m.mission.end_reason, EndReason::TimeLimit);
}

#[test]
fn drill_ends_with_no_terminal_pay_when_team_0_loses_its_strike_craft() {
    let cat = asset_catalogue();
    // The freighter stays alive: it does not keep a drill going, nobody is learning.
    let cfg = drill(
        &cat,
        &["fighter", "freighter"],
        &["fighter"],
        vec![at(-400.0, 0.0), at(-200.0, 0.0), at(400.0, 0.0)],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.ships[0].hp = 0.0;
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), WINNER_DRAW);
    assert_eq!(m.mission.end_reason, EndReason::Eliminated);
    assert_eq!(m.rewards()[2], 0.0);
}

#[test]
fn killing_every_enemy_does_not_cut_a_go_to_short() {
    let cat = asset_catalogue();
    let cfg = drill(
        &cat,
        &["fighter"],
        &["fighter"],
        vec![at(-300.0, 0.0), at(300.0, 0.0)],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(
        0,
        squad(
            1,
            Order::GoTo {
                point: Vec2::new(-200.0, 0.0),
                radius: 20.0,
                deadline: NO_DEADLINE,
            },
        ),
    );
    while m.tick() < 61 {
        m.step(&cat);
    }
    m.ships[1].hp = 0.0;
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Running, "the go-to is still open");
    assert_eq!(m.rewards()[0], 0.0, "no result is paid for the kill");
    // Arrive: nothing is left to do, so the drill ends, still as a draw.
    m.ships[0].pos = Vec2::new(-200.0, 0.0);
    m.step(&cat);
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), WINNER_DRAW);
}

/// v8: a go-to whose deadline has passed is no longer open, so with the enemies gone
/// the drill ends instead of waiting for an arrival that no longer counts.
#[test]
fn a_missed_go_to_no_longer_keeps_a_drill_open() {
    let cat = asset_catalogue();
    let cfg = drill(
        &cat,
        &["fighter"],
        &["fighter"],
        vec![at(-300.0, 0.0), at(300.0, 0.0)],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(
        0,
        squad(
            1,
            Order::GoTo {
                point: Vec2::new(200.0, 200.0),
                radius: 20.0,
                deadline: 90,
            },
        ),
    );
    while m.tick() < 61 {
        m.step(&cat);
    }
    assert_eq!(m.order_track(0).deadline, 90);
    m.ships[1].hp = 0.0;
    while m.tick() < 90 {
        m.step(&cat);
        assert_eq!(m.phase(), MatchPhase::Running, "the go-to is still open");
    }
    // Tick 91 marks the miss (and charges it); tick 92's end check sees no open go-to.
    m.step(&cat);
    assert!(m.order_track(0).missed);
    // The charge, less that step's small shaping term.
    let paid = m.order_rewards()[0];
    assert!(
        (paid + sim::reward::ORDER_MISS_PENALTY).abs() < 0.05,
        "{paid}"
    );
    assert_eq!(m.phase(), MatchPhase::Running);
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), WINNER_DRAW);
    assert_eq!(m.rewards()[0], 0.0, "a drill still pays no result");
}

#[test]
fn commands_queued_at_tick_0_reach_the_ships_on_the_first_slow_tick() {
    let cat = asset_catalogue();
    let cfg = drill(
        &cat,
        &["fighter"],
        &["fighter", "fighter"],
        vec![at(-300.0, 0.0), at(300.0, 0.0), at(300.0, 100.0)],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(0, squad(1, Order::Attack { target: 2 }));
    assert_eq!(order::standing_order(&m, 0), Order::None);
    while m.tick() < 59 {
        m.step(&cat);
    }
    assert_eq!(order::standing_order(&m, 0), Order::None);
    m.step(&cat);
    assert_eq!(m.tick(), 60);
    assert_eq!(order::standing_order(&m, 0), Order::Attack { target: 2 });
    assert_eq!(m.order_track(0).start_tick, 60);
}

#[test]
fn under_drill_rules_the_first_action_anyone_chooses_sees_the_orders() {
    let cat = asset_catalogue();
    let mut start = at(-300.0, 0.0);
    start.vel = Vec2::new(0.0, 20.0);
    let cfg = drill(
        &cat,
        &["fighter"],
        &["fighter"],
        vec![start, at(300.0, 0.0)],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(0, squad(1, Order::Attack { target: 1 }));
    while m.tick() < 60 {
        assert!(!m.act_mask(0), "tick {} is before the order", m.tick());
        // A locked ship coasts whatever it asks for.
        let a = scripted::act(&m, &cat, 0);
        m.set_action(0, a);
        m.step(&cat);
    }
    assert_eq!(order::standing_order(&m, 0), Order::Attack { target: 1 });
    assert!(m.act_mask(0));
    assert!(m.ships()[0].pos.y > 0.0, "it kept its start velocity");
    assert!(m.ships()[0].pos.x.abs() - 300.0 < 1e-3);
}

#[test]
fn a_script_under_an_external_commander_flies_at_the_named_target_in_a_drill() {
    let cat = asset_catalogue();
    // The nearer enemy is on the left; the order names the farther one on the right.
    let layout = vec![at(0.0, 0.0), at(-280.0, 0.0), at(330.0, 0.0)];
    let mut cfg = drill(&cat, &["fighter"], &["gunship", "gunship"], layout);
    cfg.time_limit_ticks = 900;
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(0, squad(1, Order::Attack { target: 2 }));
    for _ in 0..240 {
        scripted_step(&mut m, &cat);
    }
    assert!(
        m.ships()[0].pos.x > 100.0,
        "script went to x = {}",
        m.ships()[0].pos.x
    );
}

#[test]
fn enemies_ordered_onto_a_freighter_are_in_its_threat_set_and_hurt_it() {
    let cat = asset_catalogue();
    let layout = vec![at(0.0, 0.0), at(300.0, 0.0), at(350.0, 40.0)];
    let mut cfg = drill(&cat, &["fighter", "freighter"], &["fighter"], layout);
    cfg.time_limit_ticks = 900;
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(1, squad(1 << 2, Order::Attack { target: 1 }));
    m.submit_command(0, squad(1, Order::Defend { ward: 1 }));
    let start = m.ships()[1].hp + m.ships()[1].shield;
    while m.tick() < 400 {
        // Only the enemy flies: the pilot sits, so the freighter is the one thing the
        // enemy can be after.
        let a = scripted::act(&m, &cat, 2);
        m.set_action(2, a);
        m.step(&cat);
    }
    assert!(m.ships()[1].hp + m.ships()[1].shield < start);
    assert_ne!(m.ward_threat[1] & (1 << 2), 0);
    assert!(
        m.ships()[1].pos.length() < 310.0,
        "an unset waypoint coasts"
    );
}

#[test]
fn a_drill_reads_as_a_deathmatch_in_the_obs() {
    let cat = asset_catalogue();
    let layout = vec![at(-100.0, 0.0), at(100.0, 0.0)];
    let plain = Match::new(
        &cat,
        &placed(&cat, &["fighter"], &["fighter"], layout.clone()),
    )
    .unwrap();
    let drilled = Match::new(&cat, &drill(&cat, &["fighter"], &["fighter"], layout)).unwrap();
    let mut a = vec![0.0; sim::obs::OBS_DIM];
    let mut b = vec![0.0; sim::obs::OBS_DIM];
    plain.write_obs(&cat, 0, &mut a);
    drilled.write_obs(&cat, 0, &mut b);
    // Only the clock block may differ: the two have different time limits.
    let differing = a.iter().zip(&b).filter(|(x, y)| x != y).count();
    assert!(differing <= 1, "{differing} obs floats differ");
}

// -- v11: dock drills (a carrier battle or a station assault laid out by hand) -----------

/// A dock drill in a carrier battle: team 0 a carrier at the origin heading +x (moving
/// at `carrier_vel`) and `pilot` at `pilot_at` with `hull` of its maximum hull; team 1 a
/// carrier far away, plus `attackers` beside the pilot.
fn dock_drill(
    cat: &Catalogue,
    pilot: &str,
    pilot_at: Vec2,
    hull: f32,
    carrier_vel: Vec2,
    attackers: &[&str],
) -> MatchConfig {
    let mut team1 = vec!["carrier"];
    team1.extend_from_slice(attackers);
    let mut layout = vec![
        ShipStart {
            pos: Vec2::ZERO,
            vel: carrier_vel,
            heading: 0.0,
        },
        at(pilot_at.x, pilot_at.y),
        ShipStart {
            pos: Vec2::new(320.0, 200.0),
            vel: Vec2::ZERO,
            heading: std::f32::consts::PI,
        },
    ];
    for k in 0..attackers.len() {
        layout.push(at(pilot_at.x + 60.0, pilot_at.y + 40.0 * k as f32));
    }
    let mut start_hull = vec![1.0; layout.len()];
    start_hull[1] = hull;
    MatchConfig {
        mission: Mission::standard(sim::mission::MissionKind::CarrierBattle, 450.0),
        time_limit_ticks: 1800,
        start_hull: Some(start_hull),
        ..drill(cat, &["carrier", pilot], &team1, layout)
    }
}

fn dock(ship: u8) -> Command {
    Command::Dock { ship, bay: None }
}

#[test]
fn a_carrier_battle_laid_out_by_hand_has_everyone_on_the_field() {
    let cat = asset_catalogue();
    let cfg = dock_drill(
        &cat,
        "gunship",
        Vec2::new(-200.0, 0.0),
        0.3,
        Vec2::new(3.0, 0.0),
        &[],
    );
    let m = Match::new(&cat, &cfg).unwrap();
    assert!(m.ships().iter().all(|s| s.present && s.alive));
    assert_eq!(
        m.mission.carrier,
        [0, 2],
        "each team's carrier is its carrier"
    );
    assert!(
        m.reserves.iter().all(|r| r.is_empty()),
        "nobody in a hangar"
    );
    assert!(m.docking_live());
    let gunship = cat.hull(cat.hull_id("gunship").unwrap()).hp;
    assert!((m.ships()[1].hp - 0.3 * gunship).abs() < 1e-3);
    assert_eq!(m.ships()[0].hp, cat.hull(m.ships()[0].hull).hp);
    assert_eq!(m.ships()[0].vel, Vec2::new(3.0, 0.0));
    assert_eq!(m.rng, sim::rng::Pcg32::new(cfg.seed), "no rng draw");
}

#[test]
fn a_station_assault_laid_out_by_hand_makes_the_station_team_0s_carrier() {
    let cat = asset_catalogue();
    let layout = vec![
        at(-150.0, 0.0),
        at(50.0, 100.0),
        ShipStart {
            pos: Vec2::new(320.0, 0.0),
            vel: Vec2::ZERO,
            heading: std::f32::consts::PI,
        },
    ];
    let cfg = MatchConfig {
        mission: Mission::standard(sim::mission::MissionKind::StationAssault, 450.0),
        start_hull: Some(vec![1.0, 0.4, 1.0]),
        ..drill(&cat, &["station", "fighter"], &["carrier"], layout)
    };
    let mut m = Match::new(&cat, &cfg).unwrap();
    assert_eq!(m.mission.carrier, [0, 2]);
    m.submit_command(0, dock(1));
    while m.tick() < 61 {
        m.step(&cat);
    }
    assert!(m.has_dock_order(1), "the station takes a dock order");
    let (point, ..) = m.dock_approach(1).unwrap();
    assert!((point - Vec2::new(-150.0, 0.0)).length() < 40.0);
}

#[test]
fn a_dock_drill_ends_on_the_step_its_pilot_docks_as_a_draw_paying_the_dock_bonus() {
    let cat = asset_catalogue();
    let mut cfg = dock_drill(
        &cat,
        "fighter",
        Vec2::new(-200.0, 50.0),
        0.4,
        Vec2::ZERO,
        &["fighter"],
    );
    cfg.dock_bonus = 0.7;
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(0, dock(1));
    while m.tick() < 61 {
        m.step(&cat);
    }
    assert!(m.has_dock_order(1));
    assert_eq!(m.phase(), MatchPhase::Running);
    // Put the pilot at its dock point, at rest like the carrier: the bay takes it in.
    let (point, ..) = m.dock_approach(1).unwrap();
    m.ships[1].pos = point;
    m.ships[1].vel = Vec2::ZERO;
    m.step(&cat);
    assert_eq!(m.docked_now, 1 << 1);
    assert_eq!(m.phase(), MatchPhase::Over, "its last pilot left the field");
    assert_eq!(m.winner(), WINNER_DRAW);
    assert_eq!(m.mission.end_reason, EndReason::Eliminated);
    let paid = m.order_rewards()[1];
    assert!(
        (paid - 0.7).abs() < 0.02,
        "the dock bonus, less a small shaping term: {paid}"
    );
    assert!(m.rewards()[1].abs() < 0.05, "no result: {}", m.rewards()[1]);
}

#[test]
fn a_dock_drill_ends_when_its_pilot_is_shot_down() {
    let cat = asset_catalogue();
    let cfg = dock_drill(
        &cat,
        "strafer",
        Vec2::new(-200.0, 50.0),
        0.4,
        Vec2::ZERO,
        &[],
    );
    let mut m = Match::new(&cat, &cfg).unwrap();
    m.submit_command(0, dock(1));
    while m.tick() < 61 {
        m.step(&cat);
    }
    m.ships[1].hp = 0.0;
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), WINNER_DRAW);
    assert_eq!(m.docked_now, 0);
}

#[test]
fn dock_bonus_must_be_finite_and_not_negative() {
    let cat = asset_catalogue();
    for bad in [-0.1, f32::NAN, f32::INFINITY] {
        let mut cfg = dock_drill(
            &cat,
            "fighter",
            Vec2::new(-200.0, 0.0),
            0.4,
            Vec2::ZERO,
            &[],
        );
        cfg.dock_bonus = bad;
        assert!(matches!(
            Match::new(&cat, &cfg),
            Err(SetupError::InvalidGotoPay {
                name: "dock_bonus",
                ..
            })
        ));
    }
    assert_eq!(
        MatchConfig::default().dock_bonus,
        sim::reward::ORDER_ARRIVAL_BONUS
    );
}

/// The script, which flies a dock order in every mission, docks from 250 m out with its
/// carrier under way (a waypoint ahead), alone and with an enemy on its tail.
#[test]
fn the_script_docks_in_a_dock_drill_with_its_carrier_under_way() {
    let cat = asset_catalogue();
    for (pilot, attackers) in [("fighter", &[][..]), ("gunship", &["fighter"][..])] {
        let cfg = dock_drill(
            &cat,
            pilot,
            Vec2::new(-150.0, -200.0),
            0.35,
            Vec2::new(4.0, 0.0),
            attackers,
        );
        let mut m = Match::new(&cat, &cfg).unwrap();
        m.submit_command(0, dock(1));
        m.submit_command(
            0,
            Command::Waypoint {
                ship: 0,
                waypoint: sim::command::Waypoint::At(Vec2::new(300.0, 0.0)),
            },
        );
        if !attackers.is_empty() {
            m.submit_command(1, squad(1 << 3, Order::Attack { target: 1 }));
        }
        let mut docked = false;
        while m.phase() == MatchPhase::Running {
            scripted_step(&mut m, &cat);
            docked |= m.docked_now & (1 << 1) != 0;
        }
        assert!(docked, "{pilot} did not dock by tick {}", m.tick());
        assert!(m.ships()[0].pos.x > 20.0, "the carrier was under way");
        assert_eq!(m.winner(), WINNER_DRAW);
    }
}
