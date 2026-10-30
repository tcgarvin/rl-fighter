//! v4 missions, hangars, launches and the commander layer (SIM_SPEC §5.9, §5.10).

mod common;

use common::asset_catalogue;
use sim::command::{
    BAY_COOLDOWN_TICKS, COMMAND_TICKS, Command, CommanderMode, LAUNCH_LOCK_TICKS, LAUNCH_SPEED,
    Order, Outcome, Refusal, Waypoint,
};
use sim::data::{Catalogue, HullId};
use sim::events::Event;
use sim::math::Vec2;
use sim::mission::{
    CarrierBattle, ConvoyEscort, EndReason, JumpState, Mission, TRANSPORT_CRUISE_FRAC,
};
use sim::obs::{OBS_DIM, SHIP_W, SHIPS_OFF};
use sim::scripted;
use sim::setup::{MatchConfig, SetupError};
use sim::state::{Attach, Match, MatchPhase, NONE};

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

fn carrier_cfg(cat: &Catalogue, seed: u64) -> MatchConfig {
    let team = [
        "carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter",
    ];
    MatchConfig {
        seed,
        fleets: [ids(cat, &team), ids(cat, &team)],
        mission: Mission::CarrierBattle(CarrierBattle::default()),
        time_limit_ticks: 9000,
        ..MatchConfig::default()
    }
}

fn convoy_cfg(cat: &Catalogue, seed: u64) -> MatchConfig {
    let t0 = [
        "freighter",
        "freighter",
        "freighter",
        "freighter",
        "fighter",
        "strafer",
        "fighter",
    ];
    let t1 = [
        "fighter", "fighter", "strafer", "gunship", "fighter", "strafer",
    ];
    MatchConfig {
        seed,
        fleets: [ids(cat, &t0), ids(cat, &t1)],
        mission: Mission::ConvoyEscort(ConvoyEscort::standard(450.0)),
        time_limit_ticks: 9000,
        ..MatchConfig::default()
    }
}

/// Diagnostic: `cargo test -p sim --test missions timeline -- --ignored --nocapture`.
#[test]
#[ignore]
fn timeline() {
    let cat = asset_catalogue();
    for cfg in [carrier_cfg(&cat, 23), convoy_cfg(&cat, 29)] {
        let mut m = Match::new(&cat, &cfg).unwrap();
        while m.phase() == MatchPhase::Running {
            scripted_step(&mut m, &cat);
            for e in m.events() {
                match e {
                    Event::Fire { .. }
                    | Event::Hit { .. }
                    | Event::ShieldHit { .. }
                    | Event::Burst { .. }
                    | Event::Beam { .. } => {}
                    other => println!("{} {other:?}", m.tick()),
                }
            }
            if m.tick() % 300 == 0 {
                let line: Vec<String> = m
                    .ships()
                    .iter()
                    .map(|s| {
                        format!(
                            "{}{}:{:.0}/{:.0}@({:.0},{:.0})",
                            &cat.hull(s.hull).name[..2],
                            s.team,
                            s.hp,
                            s.shield,
                            s.pos.x,
                            s.pos.y
                        )
                    })
                    .collect();
                println!("{} {}", m.tick(), line.join(" "));
            }
        }
        println!(
            "end {} winner {} {:?}",
            m.tick(),
            m.winner(),
            m.mission.end_reason
        );
    }
}

fn external(mut cfg: MatchConfig) -> MatchConfig {
    cfg.commanders = [CommanderMode::External; 2];
    cfg
}

/// Step with IDLE actions until the step that ends on tick `t`.
fn idle_until(m: &mut Match, cat: &Catalogue, t: u32) {
    while m.tick() < t {
        m.step(cat);
    }
}

#[test]
fn carrier_battle_setup_docks_the_wing_behind_the_jump_ins() {
    let cat = asset_catalogue();
    let m = Match::new(&cat, &carrier_cfg(&cat, 1)).unwrap();
    for team in 0..2u8 {
        let c = m.carrier_of(team);
        assert_ne!(c, NONE);
        let carrier = &m.ships()[usize::from(c)];
        assert!(
            carrier.present && carrier.alive,
            "carrier present at tick 0"
        );
        assert!(carrier.vel.length() > 0.0, "under way");
        // 6 wing ships: 2 jump in, 4 docked in fleet order.
        let hangar = m.hangar(team);
        assert_eq!(hangar.len(), 4);
        for &s in hangar {
            let ship = &m.ships()[usize::from(s)];
            assert_eq!(ship.attach, Attach::Docked);
            assert_eq!(ship.parent, c);
            assert!(!ship.present);
        }
        let jumpers: Vec<_> = m
            .ships()
            .iter()
            .filter(|s| s.team == team && !s.present && s.attach == Attach::None)
            .collect();
        assert_eq!(jumpers.len(), 2);
        assert!(jumpers.iter().all(|s| s.arrive_tick > 0));
    }
}

#[test]
fn launch_puts_a_reserve_at_the_bay_mouth_and_cools_the_bay() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &external(carrier_cfg(&cat, 2))).unwrap();
    idle_until(&mut m, &cat, COMMAND_TICKS - 1);
    assert!(m.command_due());
    let fighter = cat.hull_id("fighter").unwrap();
    m.submit_command(
        0,
        Command::Launch {
            hull: Some(fighter),
            bay: Some(0),
        },
    );
    m.submit_command(
        0,
        Command::Launch {
            hull: None,
            bay: Some(0),
        },
    );
    m.submit_command(
        0,
        Command::Launch {
            hull: None,
            bay: Some(7),
        },
    );
    let c = m.carrier_of(0);
    let before = m.ships()[usize::from(c)].clone();
    m.step(&cat);
    let res = m.command_results(0);
    let Outcome::Launched { ship, bay } = res[0].outcome else {
        panic!("{res:?}");
    };
    assert_eq!(bay, 0);
    assert_eq!(res[1].outcome, Outcome::Refused(Refusal::BayBusy));
    assert_eq!(res[2].outcome, Outcome::Refused(Refusal::NoSuchBay));
    let s = &m.ships()[usize::from(ship)];
    assert_eq!(s.hull, fighter);
    assert!(s.present && s.attach == Attach::None && s.parent == NONE);
    assert_eq!(s.control_lock_until, COMMAND_TICKS + LAUNCH_LOCK_TICKS);
    let (carrier, bay, mouth_ev, dir) = m
        .events()
        .iter()
        .find_map(|e| match *e {
            Event::Launch {
                ship: l,
                carrier,
                bay,
                pos,
                dir,
            } if l == ship => Some((carrier, bay, pos, dir)),
            _ => None,
        })
        .expect("Launch event");
    assert_eq!((carrier, bay), (c, 0));
    // The mouth is the bay mount on the carrier as it was when launching.
    let mouth = before.to_world(cat.hull(before.hull).bays[0].pos);
    assert!((mouth_ev - mouth).length() < 1e-3);
    // Moving out along the bay at carrier velocity + LAUNCH_SPEED (one tick of
    // physics with the throttle locked down since: within a few percent).
    let rel = s.vel - before.vel;
    assert!((rel.dot(dir) - LAUNCH_SPEED).abs() < 2.0, "{rel:?}");
    assert!((s.pos - mouth).dot(dir) > 0.0);
    assert_eq!(
        m.mission.bay_ready[0][0],
        COMMAND_TICKS + BAY_COOLDOWN_TICKS
    );
    assert_eq!(m.hangar(0).len(), 3);
}

#[test]
fn launch_refusals_are_deterministic_and_never_panic() {
    let cat = asset_catalogue();
    let f = cat.hull_id("fighter").unwrap();
    let mut dm = Match::new(
        &cat,
        &external(MatchConfig {
            seed: 1,
            fleets: [vec![f], vec![f]],
            ..MatchConfig::default()
        }),
    )
    .unwrap();
    assert_eq!(dm.launch(&cat, 0, None, None), Err(Refusal::NoCarrier));
    let mut m = Match::new(&cat, &external(carrier_cfg(&cat, 3))).unwrap();
    let freighter = cat.hull_id("freighter").unwrap();
    assert_eq!(
        m.launch(&cat, 0, Some(freighter), None),
        Err(Refusal::NoReserveOfHull)
    );
    m.reserves[0].clear();
    assert_eq!(m.launch(&cat, 0, None, None), Err(Refusal::HangarEmpty));
    let c = usize::from(m.carrier_of(1));
    m.ships[c].hp = 0.0;
    m.step(&cat);
    assert_eq!(m.launch(&cat, 1, None, None), Err(Refusal::CarrierLost));
}

#[test]
fn losing_the_carrier_loses_the_match_and_the_hangar() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &carrier_cfg(&cat, 4)).unwrap();
    m.step(&cat);
    let c = usize::from(m.carrier_of(1));
    let docked: Vec<u8> = m.hangar(1).to_vec();
    m.ships[c].hp = 0.0;
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), 0);
    assert_eq!(m.mission.end_reason, EndReason::CarrierDestroyed);
    assert!(m.hangar(1).is_empty());
    for s in docked {
        assert!(
            !m.ships()[usize::from(s)].alive,
            "docked ships die with the carrier"
        );
    }
    assert!(m.events().iter().any(|e| matches!(
        e,
        Event::MatchEnd {
            winner: 0,
            reason: EndReason::CarrierDestroyed
        }
    )));
}

#[test]
fn carrier_battle_time_limit_goes_to_the_healthier_carrier() {
    let cat = asset_catalogue();
    let mut cfg = carrier_cfg(&cat, 5);
    cfg.time_limit_ticks = 10;
    let mut m = Match::new(&cat, &cfg).unwrap();
    let c0 = usize::from(m.carrier_of(0));
    m.ships[c0].hp -= 100.0;
    idle_until(&mut m, &cat, 10);
    assert_eq!(m.mission.end_reason, EndReason::TimeLimit);
    assert_eq!(m.winner(), 1);
}

#[test]
fn convoy_starts_under_way_pointed_at_the_jump_point() {
    let cat = asset_catalogue();
    let cfg = convoy_cfg(&cat, 6);
    let Mission::ConvoyEscort(ce) = cfg.mission.clone() else {
        unreachable!()
    };
    let m = Match::new(&cat, &cfg).unwrap();
    let freighter = cat.hull(cat.hull_id("freighter").unwrap());
    let mut n = 0;
    for s in m.ships().iter().filter(|s| s.team == 0) {
        assert!(s.present, "team 0 is present at tick 0");
        assert!(s.vel.length() > 1.0);
        if cat.hull(s.hull).role == "transport" {
            n += 1;
            let to_jump = (ce.jump_point - s.pos).angle();
            assert!(
                (s.heading - to_jump).abs() < 1e-5,
                "pointed at the jump point"
            );
            let speed = s.vel.length();
            assert!((speed - TRANSPORT_CRUISE_FRAC * freighter.speed_cap).abs() < 1e-3);
            assert_eq!(
                m.command.waypoints[usize::from(s.slot)],
                Waypoint::At(ce.jump_point)
            );
        }
    }
    assert_eq!(n, 4);
    assert!(m.ships().iter().filter(|s| s.team == 1).all(|s| !s.present));
    let st = m.convoy_status();
    assert_eq!(
        (st.total, st.en_route, st.to_destroy, st.to_escape),
        (4, 4, 2, 3)
    );
}

#[test]
fn transports_charge_then_jump_out_and_count_as_escaped() {
    let cat = asset_catalogue();
    let mut cfg = convoy_cfg(&cat, 7);
    if let Mission::ConvoyEscort(ce) = &mut cfg.mission {
        ce.charge_ticks = 30;
    }
    let mut m = Match::new(&cat, &cfg).unwrap();
    let Mission::ConvoyEscort(ce) = m.cfg.mission.clone() else {
        unreachable!()
    };
    // Put transport 0 inside the jump radius (a test shortcut, not a sim rule).
    m.ships[0].pos = ce.jump_point;
    m.step(&cat);
    assert!(matches!(m.jump_state(0), JumpState::Charging { until: 31 }));
    assert!(
        m.events()
            .iter()
            .any(|e| matches!(e, Event::JumpCharge { ship: 0, .. }))
    );
    idle_until(&mut m, &cat, 31);
    assert_eq!(m.jump_state(0), JumpState::Departed);
    assert!(
        m.events()
            .iter()
            .any(|e| matches!(e, Event::JumpOut { ship: 0, .. }))
    );
    let s = &m.ships()[0];
    assert!(s.alive && !s.present);
    assert!(!m.in_match(0));
    assert_eq!(m.convoy_status().escaped, 1);
    m.step(&cat);
    assert!(!m.ships()[0].present, "a departed ship never comes back");
    let mut obs = vec![0.0; OBS_DIM];
    m.write_obs(&cat, 0, &mut obs);
    assert!(obs.iter().all(|&x| x == 0.0));
}

#[test]
fn convoy_ends_when_half_is_destroyed_or_enough_escape() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &convoy_cfg(&cat, 8)).unwrap();
    m.ships[0].hp = 0.0;
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Running, "one of four is not enough");
    m.ships[1].hp = 0.0;
    m.step(&cat);
    assert_eq!(
        (m.winner(), m.mission.end_reason),
        (1, EndReason::ConvoyDestroyed)
    );

    let mut m = Match::new(&cat, &convoy_cfg(&cat, 8)).unwrap();
    for s in 0..3 {
        m.mission.jump[s] = JumpState::Departed;
        m.ships[s].present = false;
    }
    m.step(&cat);
    assert_eq!(
        (m.winner(), m.mission.end_reason),
        (0, EndReason::ConvoyThrough)
    );

    let mut cfg = convoy_cfg(&cat, 8);
    cfg.time_limit_ticks = 5;
    let mut m = Match::new(&cat, &cfg).unwrap();
    idle_until(&mut m, &cat, 5);
    assert_eq!(
        (m.winner(), m.mission.end_reason),
        (1, EndReason::TimeLimit)
    );
}

#[test]
fn squad_orders_are_sanitised_hashed_and_announced_once() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &external(carrier_cfg(&cat, 9))).unwrap();
    idle_until(&mut m, &cat, COMMAND_TICKS - 1);
    let enemy_carrier = m.carrier_of(1);
    let own = m.carrier_of(0);
    // Every bit set: the other team, the carrier and bits past the match are dropped.
    m.submit_command(
        0,
        Command::Squad {
            squad: 0,
            members: u32::MAX,
            order: Order::Attack {
                target: enemy_carrier,
            },
        },
    );
    m.submit_command(
        0,
        Command::Squad {
            squad: 9,
            members: 0,
            order: Order::None,
        },
    );
    m.submit_command(
        0,
        Command::Waypoint {
            ship: 1,
            waypoint: Waypoint::At(Vec2::ZERO),
        },
    );
    m.submit_command(
        0,
        Command::Waypoint {
            ship: own,
            waypoint: Waypoint::At(Vec2::new(1e5, 0.0)),
        },
    );
    m.submit_command(
        0,
        Command::Waypoint {
            ship: enemy_carrier,
            waypoint: Waypoint::Unset,
        },
    );
    let hash_before = m.state_hash();
    m.step(&cat);
    let res = m.command_results(0);
    assert_eq!(res[0].outcome, Outcome::Sanitized);
    assert_eq!(res[1].outcome, Outcome::Refused(Refusal::NoSuchSquad));
    assert_eq!(res[2].outcome, Outcome::Refused(Refusal::NotCapital));
    assert_eq!(res[3].outcome, Outcome::Applied);
    assert_eq!(res[4].outcome, Outcome::Refused(Refusal::NotOwnShip));
    let Waypoint::At(p) = m.command.waypoints[usize::from(own)] else {
        panic!("waypoint set")
    };
    assert!(
        p.length() <= 0.95 * 450.0 + 1e-3,
        "waypoint clamped into the arena"
    );
    let squad = m.command.squads[0][0];
    for (i, s) in m.ships().iter().enumerate() {
        let want = s.team == 0 && cat.hull(s.hull).role != "carrier";
        assert_eq!(squad.contains(i), want, "slot {i}");
    }
    assert_eq!(
        squad.order,
        Order::Attack {
            target: enemy_carrier
        }
    );
    let orders = |m: &Match| {
        m.events()
            .iter()
            .filter(|e| matches!(e, Event::Order { .. }))
            .count()
    };
    assert_eq!(orders(&m), 1);
    assert_ne!(m.state_hash(), hash_before);
    // No commands: the order stands, and no new event.
    idle_until(&mut m, &cat, 2 * COMMAND_TICKS);
    assert_eq!(
        m.command.squads[0][0].order,
        Order::Attack {
            target: enemy_carrier
        }
    );
    assert_eq!(orders(&m), 0);
}

#[test]
fn dead_targets_clear_orders_on_the_slow_tick() {
    let cat = asset_catalogue();
    let f = cat.hull_id("fighter").unwrap();
    let cfg = external(MatchConfig {
        seed: 3,
        fleets: [vec![f, f], vec![f, f, f]],
        ..MatchConfig::default()
    });
    let mut m = Match::new(&cat, &cfg).unwrap();
    for s in &mut m.ships {
        s.present = true;
    }
    idle_until(&mut m, &cat, COMMAND_TICKS - 1);
    m.submit_command(
        0,
        Command::Squad {
            squad: 2,
            members: 0b11,
            order: Order::Attack { target: 2 },
        },
    );
    m.submit_command(
        0,
        Command::Squad {
            squad: 3,
            members: 0,
            order: Order::Attack { target: 1 },
        },
    );
    m.step(&cat);
    assert_eq!(m.command.squads[0][2].order, Order::Attack { target: 2 });
    assert_eq!(
        m.command.squads[0][3].order,
        Order::None,
        "an own ship is not an attack target"
    );
    m.ships[2].hp = 0.0;
    idle_until(&mut m, &cat, 2 * COMMAND_TICKS);
    assert_eq!(m.command.squads[0][2].order, Order::None);
    assert!(m.events().iter().any(|e| matches!(
        e,
        Event::Order {
            team: 0,
            squad: 2,
            kind: 0,
            ..
        }
    )));
}

#[test]
fn deathmatch_with_twenty_ships_observes_the_nearest_seven() {
    let cat = asset_catalogue();
    let f = cat.hull_id("fighter").unwrap();
    let cfg = MatchConfig {
        seed: 11,
        fleets: [vec![f; 10], vec![f; 10]],
        ..MatchConfig::default()
    };
    let mut m = Match::new(&cat, &cfg).unwrap();
    for s in &mut m.ships {
        s.present = true;
    }
    let mut obs = vec![0.0; OBS_DIM];
    m.write_obs(&cat, 0, &mut obs);
    let present: Vec<f32> = (0..7).map(|k| obs[SHIPS_OFF + k * SHIP_W]).collect();
    assert_eq!(present, vec![1.0; 7]);
    for _ in 0..600 {
        scripted_step(&mut m, &cat);
    }
}

#[test]
fn mission_rosters_are_validated() {
    let cat = asset_catalogue();
    let mut cfg = carrier_cfg(&cat, 1);
    cfg.fleets[1].remove(0);
    assert!(matches!(
        Match::new(&cat, &cfg),
        Err(SetupError::Mission(_))
    ));
    let mut cfg = convoy_cfg(&cat, 1);
    cfg.fleets[0].retain(|&h| cat.hull(h).role != "transport");
    assert!(matches!(
        Match::new(&cat, &cfg),
        Err(SetupError::Mission(_))
    ));
    let mut cfg = convoy_cfg(&cat, 1);
    cfg.fleets[1].push(cat.hull_id("freighter").unwrap());
    assert!(matches!(
        Match::new(&cat, &cfg),
        Err(SetupError::Mission(_))
    ));
    let mut cfg = convoy_cfg(&cat, 1);
    if let Mission::ConvoyEscort(ce) = &mut cfg.mission {
        ce.jump_radius = -1.0;
    }
    assert!(matches!(
        Match::new(&cat, &cfg),
        Err(SetupError::Mission(_))
    ));
}

/// One capital ship alone at the origin with `waypoint` (its enemy, a fighter, never
/// arrives), scripted.
fn lone_capital(cat: &Catalogue, hull: &str, heading: f32, waypoint: Vec2) -> Match {
    let h = cat.hull_id(hull).unwrap();
    let f = cat.hull_id("fighter").unwrap();
    let cfg = external(MatchConfig {
        seed: 1,
        fleets: [vec![h], vec![f]],
        time_limit_ticks: 100_000,
        ..MatchConfig::default()
    });
    let mut m = Match::new(cat, &cfg).unwrap();
    m.ships[0].present = true;
    m.ships[0].pos = Vec2::ZERO;
    m.ships[0].heading = heading;
    m.ships[0].vel = Vec2::ZERO;
    m.ships[1].arrive_tick = u32::MAX - 1;
    m.command.waypoints[0] = Waypoint::At(waypoint);
    m
}

#[test]
fn carrier_turns_around_and_reaches_its_waypoint() {
    let cat = asset_catalogue();
    let goal = Vec2::new(-300.0, 0.0);
    let mut m = lone_capital(&cat, "carrier", 0.0, goal);
    let cap = cat.hull(cat.hull_id("carrier").unwrap()).speed_cap;
    let mut top = 0.0f32;
    for _ in 0..30 * 90 {
        scripted_step(&mut m, &cat);
        top = top.max(m.ships[0].vel.length());
    }
    let s = &m.ships[0];
    assert!(top > 0.8 * cap, "reached speed: {top}");
    assert!((s.pos - goal).length() < 40.0, "arrived: {:?}", s.pos);
    assert!(s.vel.length() < 3.0, "and settled: {:?}", s.vel);
}

#[test]
fn freighter_cruises_and_holds_heading_after_a_knock() {
    let cat = asset_catalogue();
    let fr = cat.hull(cat.hull_id("freighter").unwrap()).clone();
    let goal = Vec2::new(0.0, 400.0);
    let mut m = lone_capital(&cat, "freighter", 0.5 * std::f32::consts::PI, goal);
    for _ in 0..30 * 6 {
        scripted_step(&mut m, &cat);
    }
    let cruise = TRANSPORT_CRUISE_FRAC * fr.speed_cap;
    assert!(
        (m.ships[0].vel.length() - cruise).abs() < 1.5,
        "{:?}",
        m.ships[0].vel
    );
    // A knock spins it at 0.2 rad/s; the weak RCS stops it and brings the nose back.
    m.ships[0].omega = 0.2;
    let mut max_err = 0.0f32;
    for _ in 0..30 * 12 {
        scripted_step(&mut m, &cat);
        let want = (goal - m.ships[0].pos).angle();
        max_err = max_err.max((m.ships[0].heading - want).abs());
    }
    let want = (goal - m.ships[0].pos).angle();
    assert!(
        (m.ships[0].heading - want).abs() < 0.08,
        "heading restored: {} vs {want}",
        m.ships[0].heading
    );
    assert!(max_err < 1.0, "never spins around: {max_err}");
    // It cannot dodge: the script turns it with the RCS only, whose yaw authority is
    // tiny.
    let tau: f32 = fr
        .thrusters
        .iter()
        .filter(|t| t.dir.x.abs() < 0.5)
        .map(|t| t.pos.cross(t.dir).abs() * t.max_force)
        .sum::<f32>()
        / 2.0;
    assert!(
        tau / fr.inertia < 0.2,
        "yaw accel {} rad/s^2",
        tau / fr.inertia
    );
}

/// RCS pods of `hull` (thrusters that are not mains).
fn rcs_slots(cat: &Catalogue, hull: &str) -> Vec<usize> {
    let h = cat.hull(cat.hull_id(hull).unwrap());
    (0..h.thrusters.len())
        .filter(|&i| h.thrusters[i].dir.x.abs() < 0.5)
        .collect()
}

/// Per tick: whether any RCS pod of ship 0 fires, over `ticks` scripted steps.
fn rcs_trace(m: &mut Match, cat: &Catalogue, ticks: u32) -> Vec<bool> {
    let rcs = rcs_slots(cat, "carrier");
    (0..ticks)
        .map(|_| {
            scripted_step(m, cat);
            rcs.iter().any(|&i| m.ships[0].thrust_level[i] > 0.0)
        })
        .collect()
}

/// Switch-ons (off → on) in `trace`, and the shortest gap (ticks) between a
/// switch-off and the next switch-on (`u32::MAX` with fewer than two burns).
fn burns(trace: &[bool]) -> (u32, u32) {
    let (mut ons, mut shortest_gap, mut off_since) = (0, u32::MAX, None);
    for (t, w) in trace.windows(2).enumerate() {
        if w[0] && !w[1] {
            off_since = Some(t as u32);
        }
        if !w[0] && w[1] {
            ons += 1;
            if let Some(off) = off_since {
                shortest_gap = shortest_gap.min(t as u32 - off);
            }
        }
    }
    (ons, shortest_gap)
}

#[test]
fn carrier_is_ponderous() {
    let cat = asset_catalogue();
    let carrier = cat.hull(cat.hull_id("carrier").unwrap()).clone();
    let yaw = scripted::capital::yaw_authority(&carrier);
    let mains: f32 = carrier
        .thrusters
        .iter()
        .filter(|t| t.dir.x > 0.5)
        .map(|t| t.max_force)
        .sum();
    // Even at the engines-max power split (x1.64) it neither spins nor sprints.
    assert!(yaw * 1.64 < 0.3, "yaw authority {yaw} rad/s^2");
    let accel = mains / carrier.mass;
    assert!(accel * 1.64 < 3.0, "main accel {accel} m/s^2");

    // A 90 degree turn onto a waypoint 340 m off, and the run there.
    let goal = Vec2::new(0.0, 340.0);
    let mut m = lone_capital(&cat, "carrier", 0.0, goal);
    let mut top_omega = 0.0f32;
    for _ in 0..30 * 70 {
        scripted_step(&mut m, &cat);
        top_omega = top_omega.max(m.ships[0].omega.abs());
    }
    let s = &m.ships[0];
    let bearing = (goal - s.pos).angle();
    let err = sim::math::wrap_angle(s.heading - bearing).abs();
    assert!(err < 0.06, "settled on the waypoint bearing: {err}");
    assert!(top_omega < 0.15, "a ponderous turn: {top_omega} rad/s");
    assert!((s.pos - goal).length() < 60.0, "got there: {:?}", s.pos);
}

#[test]
fn carrier_holds_heading_without_rcs_chatter() {
    let cat = asset_catalogue();
    // On the axis to a far waypoint, knocked into a slow spin: one correcting burn,
    // then the nose stays put with the RCS quiet.
    let mut m = lone_capital(&cat, "carrier", 0.0, Vec2::new(370.0, 0.0));
    m.ships[0].pos = Vec2::new(-300.0, 0.0);
    m.ships[0].omega = 0.03;
    let trace = rcs_trace(&mut m, &cat, 30 * 40);
    let (ons, gap) = burns(&trace);
    assert!(ons <= 3, "RCS switched on {ons} times");
    assert!(gap >= 15, "RCS off for only {gap} ticks between burns");
    let quiet = trace[30 * 15..].iter().filter(|&&on| on).count();
    assert!(quiet <= 15, "RCS fired {quiet} ticks after settling");
    let s = &m.ships[0];
    assert!(s.heading.abs() < 0.05, "held heading: {}", s.heading);
    assert!(s.omega.abs() < 0.01, "and stopped turning: {}", s.omega);
}
