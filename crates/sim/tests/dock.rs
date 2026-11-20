//! v11 dock and repair (SIM_SPEC §0.9, §5.11; `sim::dock`): the dock order, the docking
//! rule (capture by distance and relative speed, dead bays and carriers), repair and
//! turnaround, relaunch as the same slot, the scripted commanders' recalls (and nobody else's), and the
//! script's dock statistics (`diag_dock_stats`, ignored: a lab harness).

mod common;

use common::asset_catalogue;
use sim::Vec2;
use sim::command::{Command, CommanderMode, Order, Outcome, Refusal};
use sim::data::Catalogue;
use sim::dock::{
    DOCK_CAPTURE_RADIUS, DOCK_MAX_REL_SPEED, DOCK_TURNAROUND_TICKS, DockPhase, NO_BAY,
    REPAIR_FRAC_PER_S,
};
use sim::events::Event;
use sim::mission::{CarrierBattle, Mission, MissionKind, StationAssault, default_rosters};
use sim::order::{effective_order, read_as};
use sim::scripted;
use sim::scripted::commander::{self, RECALL_HULL_FRAC, RELAUNCH_HULL_FRAC};
use sim::setup::MatchConfig;
use sim::state::{Attach, Match, MatchPhase};

fn hull_ids(cat: &Catalogue, names: &[&str]) -> Vec<u16> {
    names
        .iter()
        .map(|n| cat.hull_id(n).expect("hull"))
        .collect()
}

/// A carrier battle: a carrier and `wing` per side, every strike craft jumping in (so
/// none starts docked), the given commanders.
fn carrier_cfg(
    cat: &Catalogue,
    seed: u64,
    wing: &[&str],
    commanders: [CommanderMode; 2],
) -> MatchConfig {
    let mut fleet = vec!["carrier"];
    fleet.extend_from_slice(wing);
    let ids = hull_ids(cat, &fleet);
    MatchConfig {
        seed,
        fleets: [ids.clone(), ids],
        mission: Mission::CarrierBattle(CarrierBattle {
            jump_in: [wing.len() as u8; 2],
        }),
        commanders,
        time_limit_ticks: MissionKind::CarrierBattle.default_time_limit_ticks(),
        ..MatchConfig::default()
    }
}

/// Step until every ship is on the field (jump-ins done) with idle actions.
fn settle(m: &mut Match, cat: &Catalogue) {
    while m
        .ships
        .iter()
        .any(|s| s.alive && !s.present && s.attach == Attach::None)
    {
        m.step(cat);
    }
}

/// Put slot `s` at `pos` with velocity `vel`, all else as it was.
fn place(m: &mut Match, s: usize, pos: Vec2, vel: Vec2) {
    m.ships[s].pos = pos;
    m.ships[s].vel = vel;
}

/// A carrier battle with external commanders on both sides (nobody recalls unless told
/// to), a fighter of team 0 at slot 1, settled; team 0's carrier is slot 0.
fn external_battle(cat: &Catalogue) -> Match {
    let cfg = carrier_cfg(
        cat,
        5,
        &["fighter", "fighter"],
        [CommanderMode::External, CommanderMode::External],
    );
    let mut m = Match::new(cat, &cfg).expect("setup");
    settle(&mut m, cat);
    m
}

/// Submit `cmd` for team 0 and step to the next slow tick (idle actions).
fn command(m: &mut Match, cat: &Catalogue, cmd: Command) -> Outcome {
    m.submit_command(0, cmd);
    while !m.command_due_for(0) {
        m.step(cat);
    }
    m.step(cat);
    m.command_results(0)[0].outcome
}

fn docked_events(m: &Match) -> Vec<Event> {
    m.events()
        .iter()
        .copied()
        .filter(|e| matches!(e, Event::Docked { .. }))
        .collect()
}

#[test]
fn a_dock_order_reads_as_a_goto_to_the_bay_and_leaves_the_squad() {
    let cat = asset_catalogue();
    let mut m = external_battle(&cat);
    let squad = Command::Squad {
        squad: 0,
        members: 0b110,
        order: Order::None,
    };
    command(&mut m, &cat, squad);
    let out = command(
        &mut m,
        &cat,
        Command::Dock {
            ship: 1,
            bay: Some(1),
        },
    );
    assert_eq!(out, Outcome::Applied);
    assert_eq!(m.squad_of(1), None, "left its squad");
    assert_eq!(m.squad_of(2), Some(0));
    let order = effective_order(&m, 1);
    assert_eq!(order, Order::Dock { carrier: 0, bay: 1 });
    let Order::GoTo {
        point,
        radius,
        deadline,
    } = read_as(&m, order)
    else {
        panic!("reads as a go-to");
    };
    assert_eq!(point, m.dock_point(0, 1));
    assert_eq!(radius, DOCK_CAPTURE_RADIUS);
    assert_eq!(deadline, sim::command::NO_DEADLINE);
    assert_eq!(m.dock_phase(1), DockPhase::Inbound);
    // The point tracks the moving carrier.
    let before = m.dock_point(0, 1);
    for _ in 0..30 {
        m.step(&cat);
    }
    assert_ne!(m.dock_point(0, 1), before);
    let mut obs = vec![0.0; sim::obs::OBS_DIM];
    m.write_obs(&cat, 1, &mut obs);
    let kind = sim::obs::ORDER_OFF + sim::obs::order_f::KIND;
    assert_eq!(&obs[kind..kind + 3], &[0.0, 0.0, 1.0], "the go-to one-hot");
}

#[test]
fn a_squad_cannot_hold_a_dock_order_and_bad_dock_commands_are_refused() {
    let cat = asset_catalogue();
    let mut m = external_battle(&cat);
    let out = command(
        &mut m,
        &cat,
        Command::Squad {
            squad: 0,
            members: 0b10,
            order: Order::Dock { carrier: 0, bay: 0 },
        },
    );
    assert_eq!(out, Outcome::Sanitized);
    assert_eq!(m.command.squads[0][0].order, Order::None);
    let refused = |m: &mut Match, cmd| match command(m, &cat, cmd) {
        Outcome::Refused(r) => r,
        o => panic!("{o:?}"),
    };
    assert_eq!(
        refused(&mut m, Command::Dock { ship: 0, bay: None }),
        Refusal::NotStrikeCraft
    );
    assert_eq!(
        refused(&mut m, Command::Dock { ship: 4, bay: None }),
        Refusal::NotOwnShip
    );
    assert_eq!(
        refused(
            &mut m,
            Command::Dock {
                ship: 1,
                bay: Some(2)
            }
        ),
        Refusal::NoSuchBay
    );
    // Docking off: refused, and nothing about the match changes.
    let mut cfg = m.cfg.clone();
    cfg.docking = false;
    let mut off = Match::new(&cat, &cfg).expect("setup");
    settle(&mut off, &cat);
    assert_eq!(
        refused(&mut off, Command::Dock { ship: 1, bay: None }),
        Refusal::DockingOff
    );
}

#[test]
fn a_ship_docks_within_the_capture_radius_slow_enough_and_not_otherwise() {
    let cat = asset_catalogue();
    let base = {
        let mut m = external_battle(&cat);
        command(
            &mut m,
            &cat,
            Command::Dock {
                ship: 1,
                bay: Some(0),
            },
        );
        m
    };
    // Close and slow: docks this step.
    let try_at = |offset: Vec2, rel: Vec2| {
        let mut m = base.clone();
        let p = m.dock_point(0, 0);
        let v = m.ships[0].vel;
        place(&mut m, 1, p + offset, v + rel);
        m.step(&cat);
        (m.ships[1].attach == Attach::Docked, docked_events(&m))
    };
    let (docked, events) = try_at(Vec2::new(2.0, 0.0), Vec2::new(3.0, 0.0));
    assert!(docked);
    assert_eq!(events.len(), 1);
    // Too far.
    let far = Vec2::new(0.0, DOCK_CAPTURE_RADIUS + 8.0);
    assert!(!try_at(far, Vec2::ZERO).0);
    // Too fast relative to the carrier (the bay "catches" up to the threshold only).
    assert!(!try_at(Vec2::ZERO, Vec2::new(DOCK_MAX_REL_SPEED + 5.0, 0.0)).0);
    assert!(try_at(Vec2::ZERO, Vec2::new(DOCK_MAX_REL_SPEED - 2.0, 0.0)).0);
    // Any live bay of its carrier catches it, not only the ordered one.
    let mut m = base.clone();
    let other = m.dock_point(0, 1);
    let v = m.ships[0].vel;
    place(&mut m, 1, other, v);
    m.step(&cat);
    assert!(matches!(
        docked_events(&m)[..],
        [Event::Docked { bay: 1, .. }]
    ));
    // A ship without a dock order never docks.
    let mut m = base.clone();
    let p = m.dock_point(0, 0);
    let v = m.ships[0].vel;
    place(&mut m, 2, p, v);
    m.step(&cat);
    assert_eq!(m.ships[2].attach, Attach::None);
}

#[test]
fn docking_takes_the_ship_off_the_field_into_the_hangar_with_its_shield_full() {
    let cat = asset_catalogue();
    let mut m = external_battle(&cat);
    command(&mut m, &cat, Command::Dock { ship: 1, bay: None });
    m.ships[1].hp = 20.0;
    let p = m.dock_point(0, m.dock.bay[1]);
    let v = m.ships[0].vel;
    place(&mut m, 1, p, v);
    m.step(&cat);
    let s = &m.ships[1];
    assert!(s.alive && !s.present && s.attach == Attach::Docked && s.parent == 0);
    assert_eq!(m.hangar(0), &[1]);
    assert_eq!(m.dock.bay[1], NO_BAY);
    assert_eq!(m.dock_phase(1), DockPhase::Repairing);
    assert_eq!(effective_order(&m, 1), Order::None);
    // The dock pays the arrival bonus on its step.
    assert!(m.order_rewards()[1] > 0.1, "{}", m.order_rewards()[1]);
    // Zero obs while docked, as a reserve.
    let mut obs = vec![1.0; sim::obs::OBS_DIM];
    m.write_obs(&cat, 1, &mut obs);
    assert!(obs.iter().all(|&f| f == 0.0));
}

/// Dock ship 1 of `m` at `frac` of its hull; the tick it docked.
fn dock_at(m: &mut Match, cat: &Catalogue, frac: f32) -> u32 {
    command(
        m,
        cat,
        Command::Dock {
            ship: 1,
            bay: Some(0),
        },
    );
    m.ships[1].hp = frac * cat.hull(m.ships[1].hull).hp;
    let p = m.dock_point(0, 0);
    let v = m.ships[0].vel;
    place(m, 1, p, v);
    m.step(cat);
    assert_eq!(m.ships[1].attach, Attach::Docked);
    m.tick()
}

#[test]
fn the_turnaround_is_plain_and_the_script_relaunches_a_returned_craft_only_once_repaired() {
    let cat = asset_catalogue();
    let mut m = external_battle(&cat);
    let at = dock_at(&mut m, &cat, 0.1);
    // The sim's turnaround is the same however damaged the ship came in.
    assert_eq!(m.dock.ready_at[1] - at, DOCK_TURNAROUND_TICKS);
    while m.tick() < m.dock.ready_at[1] {
        m.step(&cat);
    }
    assert!(m.launch_ready(1));
    // The script's rule: past the recall threshold when urgent, else nearly whole.
    let max = cat.hull(m.ships[1].hull).hp;
    assert!(m.ships[1].hp < RECALL_HULL_FRAC * max);
    assert!(!commander::may_relaunch(&m, &cat, 1, true));
    m.ships[1].hp = RECALL_HULL_FRAC * max;
    assert!(commander::may_relaunch(&m, &cat, 1, true));
    assert!(!commander::may_relaunch(&m, &cat, 1, false));
    m.ships[1].hp = RELAUNCH_HULL_FRAC * max;
    assert!(commander::may_relaunch(&m, &cat, 1, false));
    // A fresh reserve always may.
    assert!(m.dock.docked_at[2] == 0 && commander::may_relaunch(&m, &cat, 2, false));
}

#[test]
fn hull_repairs_at_the_rate_and_the_ship_relaunches_as_the_same_slot_after_the_turnaround() {
    let cat = asset_catalogue();
    let mut m = external_battle(&cat);
    command(
        &mut m,
        &cat,
        Command::Dock {
            ship: 1,
            bay: Some(0),
        },
    );
    let max = cat.hull(m.ships[1].hull).hp;
    m.ships[1].hp = 0.45 * max;
    let p = m.dock_point(0, 0);
    let v = m.ships[0].vel;
    place(&mut m, 1, p, v);
    m.step(&cat);
    let docked_tick = m.tick();
    assert_eq!(m.dock.ready_at[1], docked_tick + DOCK_TURNAROUND_TICKS);
    // Repair starts on the docking step; then exactly one second of it.
    let start = m.ships[1].hp;
    assert!(start > 0.45 * max);
    for _ in 0..30 {
        m.step(&cat);
    }
    let gained = (m.ships[1].hp - start) / max;
    assert!((gained - REPAIR_FRAC_PER_S).abs() < 1e-3, "{gained}");
    // Inside the turnaround a launch is refused...
    m.mission.bay_ready = [[0; sim::state::MAX_BAYS]; 2];
    assert_eq!(m.launch(&cat, 0, None, None), Err(Refusal::Repairing));
    // ...after it, the same slot launches, and `Relaunched` follows its `Launch`.
    while m.tick() < docked_tick + DOCK_TURNAROUND_TICKS {
        m.step(&cat);
    }
    assert_eq!(m.dock_phase(1), DockPhase::Ready);
    m.events.clear();
    let (slot, _) = m.launch(&cat, 0, None, None).expect("launches");
    assert_eq!(slot, 1);
    let kinds: Vec<u8> = m.events().iter().map(|e| e.kind()).collect();
    assert_eq!(
        kinds,
        [sim::events::KIND_LAUNCH, sim::events::KIND_RELAUNCHED]
    );
    assert!(m.ships[1].present && m.ships[1].attach == Attach::None);
    assert_eq!(m.dock_phase(1), DockPhase::None);
    // Repaired fully given time: `Repaired` once.
    let mut m2 = m.clone();
    m2.ships[1].hp = max - 0.1;
    m2.ships[1].attach = Attach::Docked;
    m2.ships[1].present = false;
    m2.reserves[0].push(1);
    m2.dock.docked_at[1] = m2.tick();
    m2.step(&cat);
    assert!(
        m2.events()
            .iter()
            .any(|e| matches!(e, Event::Repaired { ship: 1, .. }))
    );
    assert_eq!(m2.ships[1].hp, max);
}

#[test]
fn a_fresh_reserve_launches_before_a_returned_ship() {
    let cat = asset_catalogue();
    let mut cfg = carrier_cfg(
        &cat,
        6,
        &["fighter", "strafer"],
        [CommanderMode::External, CommanderMode::External],
    );
    cfg.mission = Mission::CarrierBattle(CarrierBattle { jump_in: [1, 1] });
    let mut m = Match::new(&cat, &cfg).expect("setup");
    settle(&mut m, &cat);
    assert_eq!(m.hangar(0), &[2]);
    command(
        &mut m,
        &cat,
        Command::Dock {
            ship: 1,
            bay: Some(0),
        },
    );
    let p = m.dock_point(0, 0);
    let v = m.ships[0].vel;
    place(&mut m, 1, p, v);
    m.step(&cat);
    assert_eq!(m.hangar(0), &[2, 1]);
    for _ in 0..DOCK_TURNAROUND_TICKS {
        m.step(&cat);
    }
    m.mission.bay_ready = [[0; sim::state::MAX_BAYS]; 2];
    assert_eq!(m.launch(&cat, 0, None, None).map(|(s, _)| s), Ok(2));
}

#[test]
fn a_destroyed_bay_refuses_and_the_order_moves_to_a_live_one_or_is_dropped() {
    let cat = asset_catalogue();
    let base = {
        let mut m = external_battle(&cat);
        command(
            &mut m,
            &cat,
            Command::Dock {
                ship: 1,
                bay: Some(0),
            },
        );
        m
    };
    // Bay 0 destroyed: it does not catch the ship, and the order moves to bay 1.
    let mut m = base.clone();
    m.ships[0].dead_bays = 0b01;
    let p = m.dock_point(0, 0);
    let v = m.ships[0].vel;
    place(&mut m, 1, p, v);
    m.step(&cat);
    assert_eq!(m.ships[1].attach, Attach::None);
    assert_eq!(m.dock.bay[1], 1);
    // Both destroyed: the order is dropped.
    let mut m = base.clone();
    m.ships[0].dead_bays = 0b11;
    m.step(&cat);
    assert_eq!(m.dock.bay[1], NO_BAY);
    assert!(m.events().iter().any(|e| matches!(
        e,
        Event::DockAborted {
            ship: 1,
            reason: sim::dock::ABORT_NO_BAY,
            ..
        }
    )));
}

#[test]
fn docked_ships_die_with_their_carrier_and_inbound_orders_are_dropped() {
    let cat = asset_catalogue();
    let mut m = external_battle(&cat);
    command(
        &mut m,
        &cat,
        Command::Dock {
            ship: 1,
            bay: Some(0),
        },
    );
    command(
        &mut m,
        &cat,
        Command::Dock {
            ship: 2,
            bay: Some(1),
        },
    );
    let p = m.dock_point(0, 0);
    let v = m.ships[0].vel;
    place(&mut m, 1, p, v);
    m.step(&cat);
    assert_eq!(m.ships[1].attach, Attach::Docked);
    m.ships[0].hp = 0.0;
    m.step(&cat);
    assert!(!m.ships[1].alive, "died with the hangar");
    assert!(m.hangar(0).is_empty());
    assert_eq!(m.dock.bay[2], NO_BAY, "nothing to fly home to");
}

/// Run `cfg` with scripted pilots until it ends; count `DockOrdered` events and the
/// docks.
fn run_counting(cat: &Catalogue, cfg: &MatchConfig) -> (u32, u32) {
    let mut m = Match::new(cat, cfg).expect("setup");
    let (mut ordered, mut docked) = (0, 0);
    while m.phase() == MatchPhase::Running {
        for i in 0..m.ships.len() {
            let a = scripted::act(&m, cat, i as u8);
            m.set_action(i as u8, a);
        }
        m.step(cat);
        for e in m.events() {
            match e {
                Event::DockOrdered { .. } => ordered += 1,
                Event::Docked { .. } => docked += 1,
                _ => {}
            }
        }
    }
    (ordered, docked)
}

fn wing8_cfg(cat: &Catalogue, seed: u64) -> MatchConfig {
    let roster = default_rosters(MissionKind::CarrierBattle)[0];
    MatchConfig {
        seed,
        fleets: [
            hull_ids(cat, roster.fleets[0]),
            hull_ids(cat, roster.fleets[1]),
        ],
        mission: Mission::CarrierBattle(CarrierBattle::default()),
        time_limit_ticks: MissionKind::CarrierBattle.default_time_limit_ticks(),
        ..MatchConfig::default()
    }
}

#[test]
fn the_scripted_and_random_commanders_recall_and_learned_and_external_never_do() {
    let cat = asset_catalogue();
    for commanders in [[CommanderMode::Scripted; 2], [CommanderMode::Random; 2]] {
        let mut recalls = 0;
        for seed in 0..4 {
            let mut cfg = wing8_cfg(&cat, 300 + seed);
            cfg.commanders = commanders;
            let shown = run_counting(&cat, &cfg);
            recalls += shown.0;
            // Hiding the orders from the pilots changes nothing the script does.
            cfg.hide_orders = [true, true];
            assert_eq!(run_counting(&cat, &cfg), shown, "{commanders:?} hidden");
        }
        assert!(recalls > 0, "{commanders:?}");
    }
    // The sim recalls nobody on its own: a learned commander has no recall output and
    // an external one sends none here.
    for commanders in [[CommanderMode::Learned; 2], [CommanderMode::External; 2]] {
        for seed in 0..2 {
            let mut cfg = wing8_cfg(&cat, 300 + seed);
            cfg.commanders = commanders;
            assert_eq!(run_counting(&cat, &cfg), (0, 0), "{commanders:?}");
        }
    }
}

#[test]
fn the_script_recalls_below_the_threshold_only() {
    let cat = asset_catalogue();
    let mut m = external_battle(&cat);
    let max = cat.hull(m.ships[1].hull).hp;
    m.ships[1].hp = (RECALL_HULL_FRAC + 0.05) * max;
    m.ships[2].hp = (RECALL_HULL_FRAC - 0.05) * max;
    let mut out = Vec::new();
    commander::recalls(&m, &cat, 0, &mut out);
    assert_eq!(out, [Command::Dock { ship: 2, bay: None }]);
    // Without the dock rules, none.
    m.cfg.docking = false;
    out.clear();
    commander::recalls(&m, &cat, 0, &mut out);
    assert!(out.is_empty());
}

#[test]
fn a_deathmatch_and_a_convoy_never_dock_and_hash_as_with_docking_off() {
    let cat = asset_catalogue();
    let dm = MatchConfig {
        seed: 9,
        fleets: [
            hull_ids(&cat, &["fighter", "strafer"]),
            hull_ids(&cat, &["gunship", "fighter"]),
        ],
        ..MatchConfig::default()
    };
    let roster = default_rosters(MissionKind::ConvoyEscort)[0];
    let convoy = MatchConfig {
        seed: 10,
        fleets: [
            hull_ids(&cat, roster.fleets[0]),
            hull_ids(&cat, roster.fleets[1]),
        ],
        mission: Mission::standard(MissionKind::ConvoyEscort, 450.0),
        time_limit_ticks: MissionKind::ConvoyEscort.default_time_limit_ticks(),
        ..MatchConfig::default()
    };
    for cfg in [dm, convoy] {
        let mut on = Match::new(&cat, &cfg).expect("setup");
        let mut off_cfg = cfg.clone();
        off_cfg.docking = false;
        let mut off = Match::new(&cat, &off_cfg).expect("setup");
        assert!(!on.docking_live());
        while on.phase() == MatchPhase::Running && on.tick() < 1500 {
            for i in 0..on.ships.len() {
                let a = scripted::act(&on, &cat, i as u8);
                on.set_action(i as u8, a);
                off.set_action(i as u8, a);
            }
            on.step(&cat);
            off.step(&cat);
            assert_eq!(on.state_hash(), off.state_hash(), "tick {}", on.tick());
        }
    }
}

#[test]
fn station_assault_garrison_and_attackers_dock_in_their_own_carriers() {
    let cat = asset_catalogue();
    let roster = default_rosters(MissionKind::StationAssault)[0];
    let mut docks = [0u32; 2];
    for seed in 0..6 {
        let cfg = MatchConfig {
            seed: 40 + seed,
            fleets: [
                hull_ids(&cat, roster.fleets[0]),
                hull_ids(&cat, roster.fleets[1]),
            ],
            mission: Mission::StationAssault(StationAssault::default()),
            time_limit_ticks: MissionKind::StationAssault.default_time_limit_ticks(),
            ..MatchConfig::default()
        };
        let mut m = Match::new(&cat, &cfg).expect("setup");
        while m.phase() == MatchPhase::Running {
            for i in 0..m.ships.len() {
                let a = scripted::act(&m, &cat, i as u8);
                m.set_action(i as u8, a);
            }
            m.step(&cat);
            for e in m.events() {
                if let Event::Docked { ship, carrier, .. } = *e {
                    let team = m.ships[usize::from(ship)].team;
                    assert_eq!(carrier, m.carrier_of(team));
                    docks[usize::from(team)] += 1;
                }
            }
        }
    }
    println!("station assault docks by team: {docks:?}");
    assert!(docks[0] + docks[1] > 0);
}

// ---------------------------------------------------------------------------------
// Lab harness: dock statistics of scripted pilots (lab/runs/2026-11-20-dock-repair).

/// A scenario of the harness: the config of a seed.
type MakeCfg<'a> = Box<dyn Fn(u64) -> MatchConfig + 'a>;

#[derive(Default, Debug)]
struct Recall {
    ordered: u32,
    /// Closest approach to the ordered bay's dock point and the relative speed there.
    min_dist: f32,
    speed_at_min: f32,
    outcome: &'static str,
    done_tick: u32,
    /// Distance to the dock point when ordered.
    start_dist: f32,
    /// At the order: inside an enemy capital ship's reach (+40 m); an enemy strike
    /// craft within 150 m.
    deep: bool,
    engaged: bool,
}

/// `RLF_DIAG_N` matches (default 32) per scenario, seeds 1000 on; prints per scenario:
/// recalls, docks, completion, median time to dock, failures by kind, relaunches, hp
/// restored a match, and the closest approach of the recalls that did not dock.
#[test]
#[ignore = "lab harness: prints the script's dock statistics"]
fn diag_dock_stats() {
    let cat = asset_catalogue();
    let n: u64 = std::env::var("RLF_DIAG_N")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(32);
    let scenarios: Vec<(&str, MakeCfg<'_>)> = vec![
        ("carrier wing of 8", Box::new(|s| wing8_cfg(&cat, s))),
        (
            "station strike of 8",
            Box::new(|s| {
                let r = default_rosters(MissionKind::StationAssault)[0];
                MatchConfig {
                    seed: s,
                    fleets: [hull_ids(&cat, r.fleets[0]), hull_ids(&cat, r.fleets[1])],
                    mission: Mission::StationAssault(StationAssault::default()),
                    time_limit_ticks: MissionKind::StationAssault.default_time_limit_ticks(),
                    ..MatchConfig::default()
                }
            }),
        ),
        (
            "station citadel",
            Box::new(|s| {
                let r = default_rosters(MissionKind::StationAssault)[1];
                MatchConfig {
                    seed: s,
                    arena_radius: sim::mission::arena_radius_for_mission(
                        MissionKind::StationAssault,
                        r.fleets[0].len() + r.fleets[1].len(),
                    ),
                    fleets: [hull_ids(&cat, r.fleets[0]), hull_ids(&cat, r.fleets[1])],
                    mission: Mission::StationAssault(StationAssault::default()),
                    time_limit_ticks: MissionKind::StationAssault.default_time_limit_ticks(),
                    ..MatchConfig::default()
                }
            }),
        ),
    ];
    for (name, make) in &scenarios {
        let mut all: Vec<Recall> = Vec::new();
        let (mut relaunches, mut restored, mut wins) = (0u32, 0.0f32, [0u32; 3]);
        for seed in 0..n {
            let mut cfg = make(1000 + seed);
            cfg.docking = std::env::var("RLF_DIAG_DOCKING").map_or(true, |v| v != "0");
            let mut m = Match::new(&cat, &cfg).expect("setup");
            let mut open: Vec<Option<usize>> = vec![None; m.ships.len()];
            let mut hp_in = vec![0.0f32; m.ships.len()];
            while m.phase() == MatchPhase::Running {
                for i in 0..m.ships.len() {
                    let a = scripted::act(&m, &cat, i as u8);
                    m.set_action(i as u8, a);
                }
                m.step(&cat);
                for e in m.events().to_vec() {
                    match e {
                        Event::DockOrdered { ship, pos, .. } => {
                            open[usize::from(ship)] = Some(all.len());
                            all.push(Recall {
                                start_dist: (m.ships[usize::from(ship)].pos - pos).length(),
                                deep: m.ships.iter().enumerate().any(|(e, o)| {
                                    let me = &m.ships[usize::from(ship)];
                                    o.active()
                                        && o.team != me.team
                                        && sim::mission::is_capital_ship(cat.hull(o.hull))
                                        && (o.pos - me.pos).length() < m.ship_reach[e] + 40.0
                                }),
                                engaged: m.ships.iter().any(|o| {
                                    let me = &m.ships[usize::from(ship)];
                                    o.active()
                                        && o.team != me.team
                                        && !sim::mission::is_capital_ship(cat.hull(o.hull))
                                        && (o.pos - me.pos).length() < 150.0
                                }),
                                ordered: m.tick(),
                                min_dist: f32::INFINITY,
                                outcome: "match ended",
                                ..Recall::default()
                            });
                        }
                        Event::Docked { ship, hp_frac, .. } => {
                            let s = usize::from(ship);
                            hp_in[s] = hp_frac;
                            if let Some(k) = open[s].take() {
                                all[k].outcome = "docked";
                                all[k].done_tick = m.tick();
                            }
                        }
                        Event::Relaunched { ship, hp_frac, .. } => {
                            relaunches += 1;
                            restored += hp_frac - hp_in[usize::from(ship)];
                        }
                        Event::Death { ship, .. } => {
                            if let Some(k) = open[usize::from(ship)].take() {
                                all[k].outcome = "killed en route";
                                all[k].done_tick = m.tick();
                            }
                        }
                        Event::DockAborted { ship, reason, .. } => {
                            if let Some(k) = open[usize::from(ship)].take() {
                                all[k].outcome = if reason == 0 {
                                    "carrier lost"
                                } else {
                                    "no bay left"
                                };
                            }
                        }
                        _ => {}
                    }
                }
                for (s, slot) in open.iter().enumerate() {
                    let Some(k) = *slot else { continue };
                    if !m.has_dock_order(s) || !m.ships[s].active() {
                        continue;
                    }
                    let c = m.carrier_of(m.ships[s].team);
                    let p = m.dock_point(c, m.dock.bay[s]);
                    let d = (m.ships[s].pos - p).length();
                    if d < all[k].min_dist {
                        all[k].min_dist = d;
                        all[k].speed_at_min =
                            (m.ships[s].vel - m.ships[usize::from(c)].vel).length();
                    }
                }
            }
            wins[(m.winner() + 1) as usize] += 1;
        }
        let docked: Vec<&Recall> = all.iter().filter(|r| r.outcome == "docked").collect();
        let mut secs: Vec<f32> = docked
            .iter()
            .map(|r| (r.done_tick - r.ordered) as f32 / 30.0)
            .collect();
        secs.sort_by(f32::total_cmp);
        let median = secs.get(secs.len() / 2).copied().unwrap_or(f32::NAN);
        let mut kinds = std::collections::BTreeMap::<&str, u32>::new();
        for r in &all {
            *kinds.entry(r.outcome).or_default() += 1;
        }
        println!(
            "{name}: {n} matches, winner draw/0/1 {wins:?}; recalls {} ({:.2}/match), docked {} \
             ({:.2}), median {median:.1} s to dock, relaunches {relaunches} ({:.2}/match), hull \
             restored {:.2} max-hulls/match; outcomes {kinds:?}",
            all.len(),
            all.len() as f32 / n as f32,
            docked.len(),
            docked.len() as f32 / all.len().max(1) as f32,
            relaunches as f32 / n as f32,
            restored / n as f32,
        );
        let mut misses: Vec<(f32, f32)> = all
            .iter()
            .filter(|r| r.outcome != "docked" && r.min_dist.is_finite())
            .map(|r| (r.min_dist, r.speed_at_min))
            .collect();
        misses.sort_by(|a, b| a.0.total_cmp(&b.0));
        for (label, f) in [
            (
                "deep",
                Box::new(|r: &Recall| r.deep) as Box<dyn Fn(&Recall) -> bool>,
            ),
            (
                "engaged, not deep",
                Box::new(|r: &Recall| r.engaged && !r.deep),
            ),
            ("clear", Box::new(|r: &Recall| !r.engaged && !r.deep)),
        ] {
            let sel: Vec<&Recall> = all.iter().filter(|r| f(r)).collect();
            let k = sel
                .iter()
                .filter(|r| r.outcome == "killed en route")
                .count();
            let d = sel.iter().filter(|r| r.outcome == "docked").count();
            println!("  {label}: {} recalls, {d} docked, {k} killed", sel.len());
        }
        let mut killed: Vec<(f32, f32)> = all
            .iter()
            .filter(|r| r.outcome == "killed en route")
            .map(|r| (r.start_dist, (r.done_tick - r.ordered) as f32 / 30.0))
            .collect();
        killed.sort_by(|a, b| a.1.total_cmp(&b.1));
        let q = |v: &[(f32, f32)], f: f32| {
            v.get((v.len() as f32 * f) as usize)
                .map_or(f32::NAN, |x| x.1)
        };
        let mut starts: Vec<f32> = all.iter().map(|r| r.start_dist).collect();
        starts.sort_by(f32::total_cmp);
        println!(
            "  killed en route: seconds after the order p25/p50/p75 {:.1}/{:.1}/{:.1}; distance at the order p50 {:.0} m (all recalls p50 {:.0} m)",
            q(&killed, 0.25),
            q(&killed, 0.5),
            q(&killed, 0.75),
            {
                let mut d: Vec<f32> = killed.iter().map(|k| k.0).collect();
                d.sort_by(f32::total_cmp);
                d.get(d.len() / 2).copied().unwrap_or(f32::NAN)
            },
            starts.get(starts.len() / 2).copied().unwrap_or(f32::NAN),
        );
        println!(
            "  undocked closest approach (m, rel m/s): {:?}",
            misses
                .iter()
                .take(24)
                .map(|(d, v)| (d.round(), v.round()))
                .collect::<Vec<_>>()
        );
    }
}
