//! Start layouts and drill rules (`MatchConfig.start_layout`, `MatchConfig.drill`;
//! SIM_SPEC §5.10). The goldens in `determinism.rs` pin that a match without them is
//! unchanged.

mod common;

use common::asset_catalogue;
use sim::command::{Command, CommanderMode, Order};
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
    let carrier = MatchConfig {
        fleets: [ids(&cat, &["carrier"]), ids(&cat, &["carrier"])],
        mission: Mission::standard(sim::mission::MissionKind::CarrierBattle, 450.0),
        start_layout: Some(vec![at(-100.0, 0.0), at(100.0, 0.0)]),
        ..MatchConfig::default()
    };
    refused(carrier, "only a deathmatch");
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
