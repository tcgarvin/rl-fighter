//! v5 (M3 stage B), v6 (B3: attack / defend / go-to): a ship's own order in its obs
//! (SIM_SPEC §7.2 `order`, `ship_extras` and `order_ships` blocks), order instances,
//! threat sets, the order reward (§8), hidden-order mode and the random commander
//! (§5.9).

mod common;

use common::{
    CARRIER, FIGHTER, FREIGHTER, GUNSHIP, STRAFER, TORPEDO, asset_catalogue, config, test_catalogue,
};
use sim::command::{COMMAND_TICKS, Command, CommanderMode, Order, Outcome, Squad, Waypoint};
use sim::data::{Catalogue, HullId};
use sim::events::HitRecord;
use sim::math::{PI, Vec2, rot};
use sim::mission::{Mission, MissionKind, default_rosters, is_capital_ship};
use sim::obs::*;
use sim::order::{
    CAPITAL_WAYPOINT_RADIUS, GOTO_SAME_POINT, RECENT_HIT_TICKS, THREAT_MARGIN, effective_order,
    standing_order,
};
use sim::pilot_obs_dim;
use sim::reward::{
    DEFEND_HULL_LOSS_WEIGHT, DEFEND_WARD_DEATH, ORDER_ARRIVAL_BONUS, ORDER_HULL_WEIGHT,
    ORDER_SHAPING_GAMMA, ORDER_SHIELD_WEIGHT,
};
use sim::rng::Pcg32;
use sim::scripted;
use sim::scripted::random_commander::{
    self, DEFEND_CAPITAL_P, GOTO_FAR_P, GOTO_JITTER, GOTO_LERP_MAX, GOTO_LERP_MIN, GOTO_POINT_FRAC,
    GOTO_RADIUS_MAX, GOTO_RADIUS_MIN, RANDOM_SQUADS, RandomCommander, UNASSIGNED_FRAC,
};
use sim::setup::{MatchConfig, SetupError};
use sim::state::{MAX_PROJECTILES, MAX_SHIPS, Match, MatchPhase, NONE, Projectile};

const EPS: f32 = 1e-5;
const R: f32 = 450.0;
const ALL: [bool; MAX_SHIPS] = [true; MAX_SHIPS];

/// A deathmatch under external commanders (no orders unless a test sets them) with
/// every ship present, at rest, at `poses[i]` = (x, y, heading).
fn placed(cat: &Catalogue, team0: &[HullId], team1: &[HullId], poses: &[(f32, f32, f32)]) -> Match {
    let mut cfg = config(3, team0, team1);
    cfg.commanders = [CommanderMode::External; 2];
    let mut m = Match::new(cat, &cfg).unwrap();
    assert_eq!(m.ships.len(), poses.len());
    for (s, &(x, y, h)) in m.ships.iter_mut().zip(poses) {
        s.pos = Vec2::new(x, y);
        s.heading = h;
        s.vel = Vec2::ZERO;
        s.omega = 0.0;
        s.present = true;
        s.alive = true;
        s.control_lock_until = 0;
    }
    m.projectiles = [Projectile::DEAD; MAX_PROJECTILES];
    m
}

fn set_squad(m: &mut Match, team: usize, k: usize, members: &[usize], order: Order) {
    m.command.squads[team][k] = Squad {
        members: members.iter().fold(0, |a, &s| a | 1 << s),
        order,
    };
}

/// Refresh the order tracks (and order rewards) without moving anything.
fn refresh(m: &mut Match, cat: &Catalogue) -> [f32; MAX_SHIPS] {
    m.compute_order_rewards(cat, &ALL);
    m.order_rewards
}

fn order_block(m: &Match, cat: &Catalogue, ship: u8) -> Vec<f32> {
    let mut out = vec![f32::NAN; OBS_DIM];
    m.write_obs(cat, ship, &mut out);
    out[ORDER_OFF..ORDER_OFF + ORDER_WIDTH].to_vec()
}

fn close(a: f32, b: f32) -> bool {
    (a - b).abs() < EPS
}

#[test]
fn pilot_obs_dims_cover_every_compatible_version() {
    for &v in sim::PILOT_COMPAT_VERSIONS {
        assert!(pilot_obs_dim(v).is_some(), "version {v}");
    }
    assert_eq!(pilot_obs_dim(3), Some(OBS_DIM_V4));
    assert_eq!(pilot_obs_dim(4), Some(OBS_DIM_V4));
    assert_eq!(pilot_obs_dim(5), Some(OBS_DIM_V5));
    assert_eq!((OBS_DIM_V5, OBS_DIM), (403, 583));
    assert_eq!(pilot_obs_dim(sim::SIM_VERSION), Some(OBS_DIM));
    assert_eq!(pilot_obs_dim(2), None);
}

#[test]
fn no_order_is_an_all_zero_block() {
    let cat = test_catalogue();
    let m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (100.0, 0.0, PI)],
    );
    assert!(order_block(&m, &cat, 0).iter().all(|&x| x == 0.0));
}

#[test]
fn an_order_does_not_change_the_v4_prefix() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, GUNSHIP],
        &[FIGHTER],
        &[(0.0, 0.0, 0.3), (40.0, 10.0, 1.0), (150.0, -30.0, PI)],
    );
    let mut before = vec![0.0; OBS_DIM];
    m.write_obs(&cat, 0, &mut before);
    set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 2 });
    refresh(&mut m, &cat);
    let mut after = vec![0.0; OBS_DIM];
    m.write_obs(&cat, 0, &mut after);
    assert_eq!(before[..OBS_DIM_V4], after[..OBS_DIM_V4]);
    assert_eq!(after[ORDER_OFF + order_f::HAS_ORDER], 1.0);
}

#[test]
fn attack_block_is_in_the_body_frame() {
    let cat = test_catalogue();
    for &h in &[0.0, 0.4, PI / 2.0, 2.5, -1.2] {
        let me = Vec2::new(10.0, -20.0);
        let off = Vec2::from_angle(h + 0.5) * 150.0;
        let tp = me + off;
        let mut m = placed(
            &cat,
            &[FIGHTER],
            &[FIGHTER],
            &[(me.x, me.y, h), (tp.x, tp.y, 1.0)],
        );
        m.ships[1].vel = Vec2::new(5.0, 0.0);
        m.ships[0].vel = Vec2::new(0.0, 2.0);
        let hp_max = cat.hull(FIGHTER).hp;
        m.ships[1].hp = 0.5 * hp_max;
        set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 1 });
        refresh(&mut m, &cat);
        let o = order_block(&m, &cat, 0);
        let rel = rot(-h, off) / R;
        let vel = rot(-h, Vec2::new(5.0, -2.0)) / VS;
        assert_eq!(o[order_f::HAS_ORDER], 1.0);
        assert_eq!(o[order_f::KIND..order_f::KIND + 3], [1.0, 0.0, 0.0]);
        assert!(close(o[order_f::REL_POS_X], rel.x) && close(o[order_f::REL_POS_Y], rel.y));
        // Body-frame: the target sits 0.5 rad to port of the nose at any heading.
        assert!(close(
            o[order_f::REL_POS_Y].atan2(o[order_f::REL_POS_X]),
            0.5
        ));
        assert!(close(o[order_f::REL_VEL_X], vel.x) && close(o[order_f::REL_VEL_Y], vel.y));
        assert!(close(o[order_f::SIGNED_DIST], 150.0 / R));
        assert_eq!(o[order_f::RADIUS], 0.0);
        assert!(close(o[order_f::HP], 0.5));
        assert!(close(
            o[order_f::BOUND_RADIUS],
            cat.hull(FIGHTER).bound_radius / L
        ));
        assert!(close(o[order_f::SIN_REL_HEADING], (1.0 - h).sin()));
        assert!(close(o[order_f::COS_REL_HEADING], (1.0 - h).cos()));
        assert_eq!(o[order_f::AGE], 0.0);
        assert_eq!(o[order_f::MISSION..order_f::MISSION + 3], [1.0, 0.0, 0.0]);
    }
}

#[test]
fn defend_block_has_radius_zero_and_the_wards_features() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, GUNSHIP],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (50.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Defend { ward: 1 });
    refresh(&mut m, &cat);
    let o = order_block(&m, &cat, 0);
    assert_eq!(o[order_f::KIND..order_f::KIND + 3], [0.0, 1.0, 0.0]);
    assert_eq!(o[order_f::RADIUS], 0.0);
    assert!(close(o[order_f::SIGNED_DIST], 50.0 / R));
    assert!(close(o[order_f::HP], 1.0));
    assert!(close(
        o[order_f::BOUND_RADIUS],
        cat.hull(GUNSHIP).bound_radius / L
    ));
}

#[test]
fn goto_block_has_no_target_features_and_minus_own_velocity() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, PI / 2.0), (300.0, 0.0, PI)],
    );
    m.ships[0].vel = Vec2::new(3.0, 4.0);
    let point = Vec2::new(100.0, 0.0);
    set_squad(
        &mut m,
        0,
        0,
        &[0],
        Order::GoTo {
            point,
            radius: 60.0,
        },
    );
    refresh(&mut m, &cat);
    let o = order_block(&m, &cat, 0);
    let vel = rot(-PI / 2.0, Vec2::new(-3.0, -4.0)) / VS;
    let rel = rot(-PI / 2.0, point) / R;
    assert_eq!(o[order_f::KIND..order_f::KIND + 3], [0.0, 0.0, 1.0]);
    assert!(close(o[order_f::REL_POS_X], rel.x) && close(o[order_f::REL_POS_Y], rel.y));
    assert!(close(o[order_f::REL_VEL_X], vel.x) && close(o[order_f::REL_VEL_Y], vel.y));
    assert!(close(o[order_f::SIGNED_DIST], 40.0 / R));
    assert!(close(o[order_f::RADIUS], 60.0 / R));
    for f in [
        order_f::HP,
        order_f::BOUND_RADIUS,
        order_f::SIN_REL_HEADING,
        order_f::COS_REL_HEADING,
    ] {
        assert_eq!(o[f], 0.0);
    }
}

#[test]
fn a_capital_waypoint_reads_as_a_small_goto() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FREIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    m.command.waypoints[0] = Waypoint::At(Vec2::new(0.0, 200.0));
    refresh(&mut m, &cat);
    let o = order_block(&m, &cat, 0);
    assert_eq!(o[order_f::KIND..order_f::KIND + 3], [0.0, 0.0, 1.0]);
    assert!(close(o[order_f::RADIUS], CAPITAL_WAYPOINT_RADIUS / R));
    assert!(close(
        o[order_f::SIGNED_DIST],
        (200.0 - CAPITAL_WAYPOINT_RADIUS) / R
    ));
}

#[test]
fn mission_one_hot_and_carriers_see_their_waypoint() {
    let cat = asset_catalogue();
    for (kind, hot) in [
        (MissionKind::CarrierBattle, [0.0, 1.0, 0.0]),
        (MissionKind::ConvoyEscort, [0.0, 0.0, 1.0]),
    ] {
        let r = default_rosters(kind)[0];
        let ids = |names: &[&str]| -> Vec<HullId> {
            names.iter().map(|n| cat.hull_id(n).unwrap()).collect()
        };
        let cfg = MatchConfig {
            fleets: [ids(r.fleets[0]), ids(r.fleets[1])],
            mission: Mission::standard(kind, R),
            ..MatchConfig::default()
        };
        let m = Match::new(&cat, &cfg).unwrap();
        // Slot 0 is a capital ship present at tick 0 with setup's waypoint.
        assert!(is_capital_ship(cat.hull(m.ships[0].hull)));
        let o = order_block(&m, &cat, 0);
        assert_eq!(o[order_f::HAS_ORDER], 1.0, "{kind:?}");
        assert_eq!(o[order_f::MISSION..order_f::MISSION + 3], hot);
        assert!(close(o[order_f::RADIUS], CAPITAL_WAYPOINT_RADIUS / R));
    }
}

#[test]
fn order_age_counts_ticks_and_saturates() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 1 });
    refresh(&mut m, &cat);
    for _ in 0..150 {
        m.step(&cat);
    }
    let o = order_block(&m, &cat, 0);
    assert!(
        close(o[order_f::AGE], 150.0 / ORDER_AGE_TICKS),
        "{}",
        o[order_f::AGE]
    );
    for _ in 0..400 {
        m.step(&cat);
    }
    assert_eq!(order_block(&m, &cat, 0)[order_f::AGE], 1.0);
}

#[test]
fn a_new_order_target_or_squad_move_starts_an_instance_a_dead_target_does_not() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, FIGHTER],
        &[FIGHTER, FIGHTER],
        &[
            (0.0, 0.0, 0.0),
            (0.0, 40.0, 0.0),
            (300.0, 0.0, PI),
            (300.0, 80.0, PI),
        ],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 2 });
    set_squad(&mut m, 0, 1, &[1], Order::Attack { target: 3 });
    refresh(&mut m, &cat);
    for _ in 0..10 {
        m.step(&cat);
    }
    assert_eq!(m.order_age(0), 10);
    // Same order re-sent: the same instance.
    set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 2 });
    m.step(&cat);
    assert_eq!(m.order_age(0), 11);
    // A new target.
    set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 3 });
    m.step(&cat);
    assert_eq!(m.order_age(0), 0);
    assert_eq!(m.order_track(0).target, 3);
    // Moving to a squad with the same order keeps the instance; with another order
    // it starts a new one.
    m.step(&cat);
    set_squad(&mut m, 0, 0, &[], Order::None);
    set_squad(&mut m, 0, 1, &[0, 1], Order::Attack { target: 3 });
    m.step(&cat);
    assert_eq!(m.order_age(0), 2);
    set_squad(&mut m, 0, 1, &[1], Order::Attack { target: 3 });
    set_squad(&mut m, 0, 2, &[0], Order::Defend { ward: 1 });
    m.step(&cat);
    assert_eq!((m.order_age(0), m.order_track(0).kind), (0, 2));
    // A go-to point that moves more than GOTO_SAME_POINT is a new instance; a smaller
    // move or a radius change alone is not.
    let hold = |p: f32, r: f32| Order::GoTo {
        point: Vec2::new(p, 0.0),
        radius: r,
    };
    set_squad(&mut m, 0, 2, &[0], hold(100.0, 50.0));
    m.step(&cat);
    m.step(&cat);
    set_squad(&mut m, 0, 2, &[0], hold(100.0, 80.0));
    m.step(&cat);
    assert_eq!(m.order_age(0), 2);
    set_squad(&mut m, 0, 2, &[0], hold(130.0, 80.0));
    m.step(&cat);
    assert_eq!(m.order_age(0), 3);
    set_squad(&mut m, 0, 2, &[0], hold(145.0, 80.0));
    m.step(&cat);
    assert_eq!(m.order_age(0), 0);
    // Ship 1's attack target dies: its order reads as none at once, but (v6) the
    // instance is keyed on the standing order, which persists until the slow tick:
    // same start tick, same target, standing kind still attack.
    m.step(&cat);
    let start = m.order_track(1).start_tick;
    m.ships[3].hp = 0.0;
    m.step(&cat);
    assert!(!m.ships[3].alive);
    assert_eq!(m.order_track(1).start_tick, start);
    assert_eq!((m.order_track(1).kind, m.order_track(1).target), (1, 3));
    assert_eq!(standing_order(&m, 1), Order::Attack { target: 3 });
    assert_eq!(effective_order(&m, 1), Order::None);
    assert!(order_block(&m, &cat, 1).iter().all(|&x| x == 0.0));
}

/// v6: a defender's ward dying does not start an instance either; `hull_lost` counts
/// the ward's death step (the rest of its hull).
#[test]
fn a_dead_ward_keeps_the_instance_and_its_death_step_counts_as_hull_lost() {
    let cat = test_catalogue();
    let mut m = defend_match(&cat, 400.0);
    refresh(&mut m, &cat);
    m.tick = 40;
    refresh(&mut m, &cat);
    let start = m.order_track(0).start_tick;
    let max = cat.hull(FREIGHTER).hp;
    m.ships[1].hp = 0.4 * max;
    refresh(&mut m, &cat);
    m.ships[1].hp = -5.0;
    m.resolve_deaths();
    m.tick += 1;
    refresh(&mut m, &cat);
    assert!(close(m.hull_lost[1], 0.4), "{}", m.hull_lost[1]);
    assert_eq!(m.order_track(0).start_tick, start);
    assert_eq!(standing_order(&m, 0), Order::Defend { ward: 1 });
    assert_eq!(effective_order(&m, 0), Order::None);
}

/// v6: an arrived go-to keeps its standing order (and instance) until the commander
/// changes it, while its effective order is none.
#[test]
fn an_arrived_goto_keeps_its_standing_order_and_instance() {
    let cat = test_catalogue();
    let mut m = goto_match(&cat, 200.0, 50.0);
    refresh(&mut m, &cat);
    let start = m.order_track(0).start_tick;
    m.ships[0].pos.x = 0.0;
    m.tick += 30;
    refresh(&mut m, &cat);
    assert!(m.order_track(0).arrived);
    assert_eq!(m.order_track(0).start_tick, start);
    assert!(matches!(standing_order(&m, 0), Order::GoTo { .. }));
    assert_eq!(effective_order(&m, 0), Order::None);
}

/// A fighter `dist` metres from the origin along +x, with a go-to at the origin.
fn goto_match(cat: &Catalogue, dist: f32, radius: f32) -> Match {
    let mut m = placed(
        cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(dist, 0.0, 0.0), (0.0, 400.0, PI)],
    );
    set_squad(
        &mut m,
        0,
        0,
        &[0],
        Order::GoTo {
            point: Vec2::ZERO,
            radius,
        },
    );
    m
}

#[test]
fn goto_shaping_uses_the_match_s_discount() {
    let cat = test_catalogue();
    let mut m = goto_match(&cat, 200.0, 50.0);
    m.cfg.order_shaping_gamma = 0.995;
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
    let phi = -(200.0 - 50.0) / R;
    m.ships[0].pos.x = 180.0;
    let phi2 = -(180.0 - 50.0) / R;
    assert!(close(refresh(&mut m, &cat)[0], 0.995 * phi2 - phi));
    // Standing still far out pays only the (1 − γ) drift of the potential.
    assert!(close(refresh(&mut m, &cat)[0], (0.995 - 1.0) * phi2));
}

#[test]
fn order_shaping_gamma_is_validated_and_defaults_to_the_constant() {
    let cat = test_catalogue();
    assert_eq!(
        MatchConfig::default().order_shaping_gamma,
        ORDER_SHAPING_GAMMA
    );
    // A Python 0.99 reaches the sim as exactly the old constant: a gamma-0.99 trainer
    // keeps the pay it always had.
    assert_eq!(0.99_f64 as f32, ORDER_SHAPING_GAMMA);
    let cfg = |gamma: f32| MatchConfig {
        fleets: [vec![FIGHTER], vec![FIGHTER]],
        order_shaping_gamma: gamma,
        ..MatchConfig::default()
    };
    for gamma in [
        0.0,
        -0.1,
        1.0001,
        f32::NAN,
        f32::INFINITY,
        f32::NEG_INFINITY,
    ] {
        assert!(
            matches!(
                cfg(gamma).validate(&cat),
                Err(SetupError::InvalidOrderShapingGamma { .. })
            ),
            "gamma {gamma} must be rejected"
        );
    }
    for gamma in [0.5, 0.995, 1.0] {
        assert_eq!(cfg(gamma).validate(&cat), Ok(()), "gamma {gamma}");
    }
}

#[test]
fn goto_shaping_is_gamma_phi_prime_minus_phi_and_resets_on_a_new_instance() {
    let cat = test_catalogue();
    let mut m = goto_match(&cat, 200.0, 50.0);
    // The step the instance starts pays nothing for the jump.
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
    let phi = -(200.0 - 50.0) / R;
    assert!(close(m.order_track(0).last_phi, phi));
    m.ships[0].pos.x = 180.0;
    let phi2 = -(180.0 - 50.0) / R;
    assert!(close(
        refresh(&mut m, &cat)[0],
        ORDER_SHAPING_GAMMA * phi2 - phi
    ));
    // Standing still far out pays only the (1 − γ) drift of the potential.
    assert!(close(
        refresh(&mut m, &cat)[0],
        (ORDER_SHAPING_GAMMA - 1.0) * phi2
    ));
    // A new point (more than GOTO_SAME_POINT away): Φ restarts, no reward for the
    // jump in potential.
    set_squad(
        &mut m,
        0,
        0,
        &[0],
        Order::GoTo {
            point: Vec2::new(-200.0, 0.0),
            radius: 50.0,
        },
    );
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
    assert!(close(m.order_track(0).last_phi, -(380.0 - 50.0) / R));
}

/// v6: arrival pays `ORDER_ARRIVAL_BONUS` once and completes the go-to for that ship:
/// its effective order is none (obs block zero, no order reward) while the squad's
/// standing order stays; there is no presence term.
#[test]
fn goto_completes_on_arrival_and_pays_once() {
    let cat = test_catalogue();
    let mut m = goto_match(&cat, 100.0, 50.0);
    refresh(&mut m, &cat);
    assert!(matches!(effective_order(&m, 0), Order::GoTo { .. }));
    let phi = -50.0 / R;
    m.ships[0].pos.x = 30.0;
    let first = refresh(&mut m, &cat)[0];
    assert!(close(first, -phi + ORDER_ARRIVAL_BONUS), "{first}");
    assert!(m.order_track(0).arrived);
    assert_eq!(effective_order(&m, 0), Order::None);
    assert!(matches!(standing_order(&m, 0), Order::GoTo { .. }));
    assert!(order_block(&m, &cat, 0).iter().all(|&x| x == 0.0));
    // Parked inside, then out and back: nothing more.
    let parked: f32 = (0..400).map(|_| refresh(&mut m, &cat)[0]).sum();
    assert_eq!(parked, 0.0);
    m.ships[0].pos.x = 300.0;
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
    m.ships[0].pos.x = 0.0;
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
}

/// A re-issued go-to point within `GOTO_SAME_POINT` of the instance's first point is
/// the same instance (still complete, no second bonus); farther is a new one.
#[test]
fn a_goto_reissued_within_40_m_is_the_same_instance() {
    let cat = test_catalogue();
    let mut m = goto_match(&cat, 20.0, 50.0);
    refresh(&mut m, &cat);
    assert!(
        m.order_track(0).arrived,
        "inside at the start: arrives at once"
    );
    let start = m.order_track(0).start_tick;
    let goto = |x: f32| Order::GoTo {
        point: Vec2::new(x, 0.0),
        radius: 50.0,
    };
    for x in [GOTO_SAME_POINT - 1.0, -30.0, 10.0] {
        set_squad(&mut m, 0, 0, &[0], goto(x));
        m.tick += 60;
        assert_eq!(refresh(&mut m, &cat)[0], 0.0, "re-issued at {x}");
        assert_eq!(m.order_track(0).start_tick, start);
        assert_eq!(effective_order(&m, 0), Order::None);
    }
    // 45 m from the instance's first point: a new instance, paid again on arrival.
    m.ships[0].pos.x = 45.0;
    set_squad(&mut m, 0, 0, &[0], goto(GOTO_SAME_POINT + 5.0));
    assert!(close(refresh(&mut m, &cat)[0], ORDER_ARRIVAL_BONUS));
    assert_ne!(m.order_track(0).start_tick, start);
}

#[test]
fn ships_that_do_not_earn_get_no_order_reward() {
    let cat = test_catalogue();
    let mut m = goto_match(&cat, 20.0, 50.0);
    let mut earning = ALL;
    earning[0] = false;
    m.compute_order_rewards(&cat, &earning);
    assert_eq!(m.order_rewards[0], 0.0);
    assert!(
        !m.order_track(0).arrived,
        "arrival is kept for an earning step"
    );
}

fn hit(shooter: u8, target: u8, damage: f32, shield: bool) -> HitRecord {
    HitRecord {
        shooter,
        target,
        damage,
        fire_tick: 0,
        decision_tick: 0,
        shield,
    }
}

#[test]
fn attack_pays_damage_to_its_target_only() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER, FIGHTER],
        &[(0.0, 0.0, 0.0), (100.0, 0.0, PI), (100.0, 50.0, PI)],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 1 });
    refresh(&mut m, &cat);
    m.hits = vec![
        hit(0, 1, 10.0, false),
        hit(0, 2, 10.0, false),
        hit(0, 1, 4.0, true),
    ];
    let r = refresh(&mut m, &cat)[0];
    assert!(close(
        r,
        ORDER_HULL_WEIGHT * 10.0 + ORDER_SHIELD_WEIGHT * 4.0
    ));
    // The hit that kills the target still pays (standing order), though the
    // effective order is already none.
    m.ships[1].alive = false;
    m.ships[1].present = false;
    m.hits = vec![hit(0, 1, 6.0, false)];
    assert!(close(refresh(&mut m, &cat)[0], ORDER_HULL_WEIGHT * 6.0));
}

/// Ward (slot 1, a freighter at the origin) defended by slot 0; enemies: slot 2 a
/// gunship, slot 3 a fighter, both `dist` metres out on +x, slot 4 a fighter far off.
fn defend_match(cat: &Catalogue, dist: f32) -> Match {
    let mut m = placed(
        cat,
        &[FIGHTER, FREIGHTER],
        &[GUNSHIP, FIGHTER, FIGHTER],
        &[
            (-30.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (dist, 10.0, PI),
            (dist, -10.0, PI),
            (0.0, 420.0, PI),
        ],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Defend { ward: 1 });
    m
}

/// v6 threat set: enemies within their own longest weapon range + `THREAT_MARGIN` +
/// the ward's bound radius, so a gunship's torpedo (340 m) counts where a fighter's
/// gun does not; and anyone who hit the ward in the last `RECENT_HIT_TICKS` ticks.
#[test]
fn defend_threat_set_uses_each_enemys_own_reach_and_recent_hits() {
    // The shipped gunship carries no torpedo: give its fore turret one.
    let mut cat = test_catalogue();
    cat.hulls[GUNSHIP as usize].turrets[0].weapon = TORPEDO;
    let bound = cat.hull(FREIGHTER).bound_radius;
    let torpedo = m_reach(&cat, GUNSHIP);
    let gun = m_reach(&cat, FIGHTER);
    assert!(torpedo >= 340.0 && gun < 300.0, "{torpedo} {gun}");
    // Just inside the gunship's threat range, beyond the fighter's.
    let dist = torpedo + THREAT_MARGIN + bound - 5.0;
    let mut m = defend_match(&cat, dist);
    let all = m.active_mask();
    assert_eq!(m.threat_set(&cat, 1, all), 1 << 2);
    // Slot 4 hit the ward: in the set wherever it is, for RECENT_HIT_TICKS ticks.
    m.tick = 100;
    m.hits = vec![hit(4, 1, 3.0, true)];
    refresh(&mut m, &cat);
    assert_eq!(m.hit_by[1][4], 100);
    assert_eq!(m.threat_set(&cat, 1, all), 1 << 2 | 1 << 4);
    assert_eq!(m.ward_threat[1], 1 << 2 | 1 << 4);
    m.hits.clear();
    m.tick = 100 + RECENT_HIT_TICKS - 1;
    assert_eq!(m.threat_set(&cat, 1, all), 1 << 2 | 1 << 4);
    m.tick = 100 + RECENT_HIT_TICKS;
    assert_eq!(m.threat_set(&cat, 1, all), 1 << 2);
    // Allies are never threats, whatever they did.
    m.hit_by[1][0] = m.tick;
    assert_eq!(m.threat_set(&cat, 1, all) & 1, 0);
}

fn m_reach(cat: &Catalogue, hull: HullId) -> f32 {
    sim::order::hull_reach(cat, cat.hull(hull))
}

/// Defend pays the damage weights on hits on the ward's threat set only, and every
/// defender pays `DEFEND_HULL_LOSS_WEIGHT` × the ward's hull fraction lost.
#[test]
fn defend_pays_damage_on_the_threat_set_and_shares_the_wards_hull_loss() {
    let cat = test_catalogue();
    let dist = m_reach(&cat, GUNSHIP) + THREAT_MARGIN;
    let mut m = defend_match(&cat, dist);
    // The enemy gunship's own order: it is not a defender.
    set_squad(&mut m, 1, 0, &[2], Order::Attack { target: 0 });
    refresh(&mut m, &cat);
    // Hits on the gunship (threat) and on the far fighter (not).
    m.hits = vec![
        hit(0, 2, 10.0, false),
        hit(0, 4, 10.0, false),
        hit(0, 2, 6.0, true),
    ];
    let r = refresh(&mut m, &cat)[0];
    assert!(
        close(r, ORDER_HULL_WEIGHT * 10.0 + ORDER_SHIELD_WEIGHT * 6.0),
        "{r}"
    );
    // The ward loses a quarter of its hull: no location term, just the loss.
    let max = cat.hull(FREIGHTER).hp;
    m.ships[1].hp -= 0.25 * max;
    m.hits.clear();
    let r = refresh(&mut m, &cat);
    assert!(close(r[0], DEFEND_HULL_LOSS_WEIGHT * 0.25), "{}", r[0]);
    assert!(close(m.hull_lost[1], 0.25));
    assert_eq!(r[2], 0.0, "an attacker pays no defend terms");
    // Nothing lost: nothing paid (no shaping, arrival or presence for defend).
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
}

/// The ward's death costs every defender `DEFEND_WARD_DEATH` once (plus the rest of
/// its hull), through the standing order, though the effective order is already none.
#[test]
fn ward_death_is_paid_by_every_defender_via_the_standing_order() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, FIGHTER, FREIGHTER, FIGHTER],
        &[FIGHTER],
        &[
            (-30.0, 0.0, 0.0),
            (-30.0, 30.0, 0.0),
            (0.0, 0.0, 0.0),
            (-30.0, -30.0, 0.0),
            (200.0, 0.0, PI),
        ],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Defend { ward: 2 });
    set_squad(&mut m, 0, 1, &[1], Order::Defend { ward: 2 });
    refresh(&mut m, &cat);
    let max = cat.hull(FREIGHTER).hp;
    m.ships[2].hp = 0.1 * max;
    refresh(&mut m, &cat);
    m.ships[2].hp = 0.0;
    m.resolve_deaths();
    assert_eq!(effective_order(&m, 0), Order::None);
    let r = refresh(&mut m, &cat);
    let want = DEFEND_HULL_LOSS_WEIGHT * 0.1 + DEFEND_WARD_DEATH;
    assert!(close(r[0], want) && close(r[1], want), "{r:?}");
    assert_eq!(r[3], 0.0, "slot 3 has no order");
    // Once only.
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
}

/// The transit flag (`Match::order_transit`): a go-to not yet arrived, or a defend
/// whose ward's threat set is empty; never attack or no order.
#[test]
fn transit_flag_is_goto_in_flight_or_defend_without_threat() {
    let cat = test_catalogue();
    let mut m = goto_match(&cat, 200.0, 50.0);
    refresh(&mut m, &cat);
    assert!(m.order_transit(&cat, 0));
    m.ships[0].pos.x = 10.0;
    refresh(&mut m, &cat);
    assert!(!m.order_transit(&cat, 0), "arrived: complete");
    let mut m = defend_match(&cat, 440.0);
    m.ships[2].pos.x = 450.0;
    m.ships[3].pos.x = 450.0;
    refresh(&mut m, &cat);
    assert_eq!(m.threat_set(&cat, 1, m.active_mask()), 0);
    assert!(m.order_transit(&cat, 0));
    m.ships[3].pos.x = 100.0;
    assert!(!m.order_transit(&cat, 0), "a threat: combat");
    set_squad(&mut m, 0, 0, &[0], Order::Attack { target: 2 });
    assert!(!m.order_transit(&cat, 0));
    assert!(!m.order_transit(&cat, 4));
}

fn scripted_step(m: &mut Match, cat: &Catalogue) {
    for i in 0..m.ships().len() {
        let a = scripted::act(m, cat, i as u8);
        m.set_action(i as u8, a);
    }
    m.step(cat);
}

fn mission_cfg(cat: &Catalogue, kind: MissionKind, roster: usize, seed: u64) -> MatchConfig {
    let r = default_rosters(kind)
        .get(roster)
        .copied()
        .unwrap_or(default_rosters(MissionKind::CarrierBattle)[0]);
    let ids =
        |names: &[&str]| -> Vec<HullId> { names.iter().map(|n| cat.hull_id(n).unwrap()).collect() };
    let (fleets, mission) = if kind == MissionKind::Deathmatch {
        let f = |n: &[&str]| ids(n);
        (
            [
                f(&["fighter", "strafer", "gunship", "fighter"]),
                f(&["gunship", "fighter", "strafer"]),
            ],
            Mission::Deathmatch,
        )
    } else {
        (
            [ids(r.fleets[0]), ids(r.fleets[1])],
            Mission::standard(kind, R),
        )
    };
    MatchConfig {
        seed,
        fleets,
        mission,
        time_limit_ticks: kind.default_time_limit_ticks(),
        commanders: [CommanderMode::Random; 2],
        ..MatchConfig::default()
    }
}

/// Every command the random commander issues is applied as given, and every order it
/// gives is a valid one of the plan's shapes.
#[test]
fn random_commander_issues_only_valid_commands() {
    let cat = asset_catalogue();
    let mut kinds = [0usize; 4];
    let mut squad_cmds = 0;
    for kind in [
        MissionKind::Deathmatch,
        MissionKind::CarrierBattle,
        MissionKind::ConvoyEscort,
    ] {
        for seed in 0..6u64 {
            let mut m =
                Match::new(&cat, &mission_cfg(&cat, kind, seed as usize % 2, seed)).unwrap();
            while m.phase() == MatchPhase::Running {
                scripted_step(&mut m, &cat);
                if m.tick() % COMMAND_TICKS != 0 {
                    continue;
                }
                for team in 0..2u8 {
                    for res in m.command_results(team) {
                        let Command::Squad {
                            squad,
                            members,
                            order,
                        } = res.command
                        else {
                            continue;
                        };
                        squad_cmds += 1;
                        assert_eq!(res.outcome, Outcome::Applied, "{kind:?} {res:?}");
                        assert!(usize::from(squad) < RANDOM_SQUADS);
                        for s in 0..m.ships.len() {
                            if members & (1 << s) != 0 {
                                assert_eq!(m.ships[s].team, team);
                                assert!(!is_capital_ship(cat.hull(m.ships[s].hull)));
                            }
                        }
                        kinds[usize::from(order.kind())] += 1;
                        match order {
                            Order::Attack { target } => {
                                assert_ne!(m.ships[usize::from(target)].team, team);
                            }
                            Order::Defend { ward } => {
                                assert_eq!(m.ships[usize::from(ward)].team, team);
                                assert_eq!(members & (1 << ward), 0, "defending itself");
                            }
                            Order::GoTo { point, radius } => {
                                assert!(point.length() <= GOTO_POINT_FRAC * R + 1e-3);
                                assert!((GOTO_RADIUS_MIN..GOTO_RADIUS_MAX).contains(&radius));
                            }
                            Order::None => {}
                        }
                    }
                }
            }
        }
    }
    assert!(squad_cmds > 200, "{squad_cmds}");
    for (k, &n) in kinds.iter().enumerate() {
        assert!(n * 10 > squad_cmds, "kind {k} issued {n} of {squad_cmds}");
    }
}

/// Order kinds are drawn uniformly, about `UNASSIGNED_FRAC` of strike craft are in no
/// squad, and the redraw timer lies in the plan's 3–8 slow ticks.
#[test]
fn random_commander_draw_statistics() {
    let cat = asset_catalogue();
    let mut kinds = [0usize; 4];
    let (mut unassigned, mut strike) = (0usize, 0usize);
    for seed in 0..400u64 {
        let mut m = Match::new(&cat, &mission_cfg(&cat, MissionKind::Deathmatch, 0, seed)).unwrap();
        for s in &mut m.ships {
            s.present = true;
        }
        m.tick = COMMAND_TICKS;
        let mut st = RandomCommander::new(seed);
        let cmds = random_commander::commands(&m, &cat, 0, &mut st);
        for s in 0..4 {
            strike += 1;
            unassigned += usize::from(st.squad[s] == NONE);
        }
        for k in 0..RANDOM_SQUADS {
            if st.next_draw[0][k] != 0 {
                let wait = st.next_draw[0][k] - m.tick;
                assert!((3 * COMMAND_TICKS..=8 * COMMAND_TICKS).contains(&wait));
                assert_eq!(wait % COMMAND_TICKS, 0);
                kinds[usize::from(st.drawn[0][k])] += 1;
            }
        }
        assert!(cmds.iter().all(|c| matches!(c, Command::Squad { .. })));
    }
    let frac = unassigned as f32 / strike as f32;
    assert!((frac - UNASSIGNED_FRAC).abs() < 0.04, "unassigned {frac}");
    let total: usize = kinds.iter().sum();
    for (k, &n) in kinds.iter().enumerate() {
        let p = n as f32 / total as f32;
        assert!((p - 0.25).abs() < 0.05, "kind {k}: {p}");
    }
}

/// Random go-to points lie near the squad's fight (after run 1): between the squad's
/// centroid and the centroid of its two nearest enemies, `GOTO_LERP_MIN..MAX` of the
/// way plus at most `GOTO_JITTER`, except a `GOTO_FAR_P` share drawn over the whole
/// disc of `GOTO_POINT_FRAC` R; every point is inside that disc.
#[test]
fn random_goto_points_lie_near_the_squads_fight() {
    let cat = test_catalogue();
    // Squad (slots 0, 1) round (-150, 0); enemies: two near (150, ±40), one far.
    let m = placed(
        &cat,
        &[FIGHTER, FIGHTER],
        &[FIGHTER, FIGHTER, FIGHTER],
        &[
            (-150.0, 20.0, 0.0),
            (-150.0, -20.0, 0.0),
            (150.0, 40.0, 0.0),
            (150.0, -40.0, 0.0),
            (-100.0, 300.0, 0.0),
        ],
    );
    let squad = Vec2::new(-150.0, 0.0);
    let foes = Vec2::new(150.0, 0.0);
    let reach = GOTO_POINT_FRAC * R;
    let (mut near, n) = (0usize, 4000usize);
    for seed in 0..n as u64 {
        let mut rng = Pcg32::with_stream(seed, 99);
        let p = random_commander::goto_point(&m, 0, 0b11, &mut rng);
        assert!(p.length() <= reach + 1e-3, "{p:?} outside the disc");
        // Distance from the segment's lerp band, along the x axis.
        let along = (p.x - squad.x) / (foes.x - squad.x);
        let in_band = (GOTO_LERP_MIN - GOTO_JITTER / 300.0..GOTO_LERP_MAX + GOTO_JITTER / 300.0)
            .contains(&along)
            && p.y.abs() <= GOTO_JITTER + 1e-3;
        near += usize::from(in_band);
    }
    let share = near as f32 / n as f32;
    // Far points land in the band with probability about its area over the disc's.
    assert!(
        (share - (1.0 - GOTO_FAR_P)).abs() < 0.05,
        "near share {share}, expected about {}",
        1.0 - GOTO_FAR_P
    );
    // Without an enemy every point is a far one, still inside the disc.
    let alone = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
    );
    let mut alone = alone;
    alone.ships[1].alive = false;
    let mut rng = Pcg32::with_stream(1, 99);
    for _ in 0..100 {
        let p = random_commander::goto_point(&alone, 0, 0b1, &mut rng);
        assert!(p.length() <= reach + 1e-3);
    }
}

/// The random commander's draws never touch the match rng: the same seed under
/// scripted and random commanders has the same match rng after the first slow tick
/// (both setups draw identically; pilots have not reacted to any order yet), and
/// team 1's draws do not depend on team 0's mode.
#[test]
fn random_commander_rng_is_its_own_stream() {
    let cat = asset_catalogue();
    let run = |commanders: [CommanderMode; 2]| {
        let mut cfg = mission_cfg(&cat, MissionKind::CarrierBattle, 0, 77);
        cfg.commanders = commanders;
        let mut m = Match::new(&cat, &cfg).unwrap();
        while m.tick() < COMMAND_TICKS {
            scripted_step(&mut m, &cat);
        }
        m
    };
    let scripted = run([CommanderMode::Scripted; 2]);
    let random = run([CommanderMode::Random; 2]);
    let mixed = run([CommanderMode::Scripted, CommanderMode::Random]);
    assert_eq!(scripted.rng, random.rng);
    assert_ne!(random.random_commander.rng, scripted.random_commander.rng);
    assert_eq!(scripted.random_commander, RandomCommander::new(77));
    assert_eq!(
        mixed.random_commander.rng[1],
        random.random_commander.rng[1]
    );
    assert_eq!(mixed.command.squads[1], random.command.squads[1]);
}

/// Scripted strike craft follow a random commander's orders, deathmatch included
/// (unlike the scripted deathmatch commander's advisory orders): a fighter told to
/// go to a point away from the only enemy flies to the point under `Random` (and,
/// arrived, completes the order), and at the enemy under `Scripted`.
#[test]
fn scripted_pilots_follow_random_orders_in_deathmatch() {
    let cat = test_catalogue();
    let point = Vec2::new(300.0, 0.0);
    let run = |mode: CommanderMode| {
        let mut m = placed(
            &cat,
            &[FIGHTER],
            &[FIGHTER],
            &[(0.0, 0.0, 0.0), (-350.0, 0.0, 0.0)],
        );
        m.cfg.commanders = [mode, CommanderMode::External];
        set_squad(
            &mut m,
            0,
            0,
            &[0],
            Order::GoTo {
                point,
                radius: 60.0,
            },
        );
        // The random commander keeps this order for the whole test.
        let rc = &mut m.random_commander;
        rc.assigned[0] = true;
        rc.squad[0] = 0;
        rc.drawn[0][0] = 3;
        rc.next_draw[0][0] = u32::MAX;
        for _ in 0..240 {
            let a = scripted::act(&m, &cat, 0);
            m.set_action(0, a);
            m.step(&cat);
        }
        assert!(
            matches!(m.command.squads[0][0].order, Order::GoTo { .. })
                || mode != CommanderMode::Random
        );
        (m.order_track(0).arrived, m.ships[0].pos.x)
    };
    let (random_arrived, _) = run(CommanderMode::Random);
    let (scripted_arrived, scripted_x) = run(CommanderMode::Scripted);
    assert!(random_arrived, "random: never reached the go-to point");
    assert!(
        !scripted_arrived && scripted_x < 50.0,
        "scripted: x {scripted_x}"
    );
}

fn full_obs(m: &Match, cat: &Catalogue, ship: u8) -> Vec<f32> {
    let mut out = vec![f32::NAN; OBS_DIM];
    m.write_obs(cat, ship, &mut out);
    out
}

/// A defender (slot 0) of a freighter (slot 1) with an ally (slot 2) and five enemies
/// spread round the ward; slot 3 hit the ward recently.
fn crowded(cat: &Catalogue) -> Match {
    let mut m = placed(
        cat,
        &[FIGHTER, FREIGHTER, GUNSHIP],
        &[FIGHTER, STRAFER, GUNSHIP, FIGHTER, FIGHTER],
        &[
            (-200.0, 0.0, 0.3),
            (100.0, 0.0, 0.0),
            (120.0, 40.0, 0.0),
            (330.0, 60.0, PI),
            (100.0, 90.0, PI),
            (300.0, -50.0, PI),
            (-160.0, 30.0, PI),
            (100.0, -140.0, PI),
        ],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Defend { ward: 1 });
    m.tick = 50;
    m.hits = vec![hit(3, 1, 4.0, false)];
    refresh(&mut m, cat);
    m.hits.clear();
    m
}

/// v6 `order_ships`: the `N_ORDER_SHIPS` active ships nearest the order point, allies
/// and enemies, never the observer or the order's own ship, nearest first, each a
/// ship record relative to the observer plus its extras.
#[test]
fn order_ships_are_nearest_the_order_point_excluding_self_and_the_ward() {
    let cat = test_catalogue();
    let m = crowded(&cat);
    let obs = full_obs(&m, &cat, 0);
    let ward = m.ships[1].pos;
    let mut want: Vec<usize> = (2..m.ships.len()).collect();
    want.sort_by(|&a, &b| {
        let da = (m.ships[a].pos - ward).length();
        let db = (m.ships[b].pos - ward).length();
        da.total_cmp(&db).then(a.cmp(&b))
    });
    want.truncate(N_ORDER_SHIPS);
    assert!(!want.contains(&0) && !want.contains(&1));
    for (k, &s) in want.iter().enumerate() {
        let o = ORDER_SHIPS_OFF + k * ORDER_SHIP_W;
        let mut ship = vec![0.0; SHIP_W];
        write_ship(&cat, &m.ships[0], &m.ships[s], R, &mut ship);
        assert_eq!(obs[o..o + SHIP_W], ship[..], "order ship {k} is slot {s}");
        let e = &obs[o + SHIP_W..o + ORDER_SHIP_W];
        assert!(close(
            e[extra_f::ORDER_DIST],
            (m.ships[s].pos - ward).length() / R
        ));
        assert_eq!(e[extra_f::IS_ORDER_SHIP], 0.0);
        assert_eq!(e[extra_f::HIT_MY_WARD], f32::from(u8::from(s == 3)));
    }
    // Without an order the block is zero.
    let mut m = m;
    set_squad(&mut m, 0, 0, &[0], Order::None);
    let obs = full_obs(&m, &cat, 0);
    assert!(obs[ORDER_SHIPS_OFF..].iter().all(|&x| x == 0.0));
}

/// v6 `ship_extras`: one record per `ships` slot in the same order: hull class from
/// the catalogue role, longest weapon range, distance to my order point, is my order
/// ship, hit my ward recently.
#[test]
fn ship_extras_follow_the_ships_block() {
    let cat = test_catalogue();
    let m = crowded(&cat);
    let obs = full_obs(&m, &cat, 0);
    let ward = m.ships[1].pos;
    for k in 0..N_NEAR_SHIPS {
        let rec = &obs[SHIPS_OFF + k * SHIP_W..SHIPS_OFF + (k + 1) * SHIP_W];
        let ext =
            &obs[SHIP_EXTRAS_OFF + k * SHIP_EXTRA_W..SHIP_EXTRAS_OFF + (k + 1) * SHIP_EXTRA_W];
        // Identify the slot by its relative position.
        let s = (1..m.ships.len())
            .find(|&s| {
                let mut r = vec![0.0; SHIP_W];
                write_ship(&cat, &m.ships[0], &m.ships[s], R, &mut r);
                r[..] == rec[..]
            })
            .expect("a ship record");
        let class = sim::order::hull_class(cat.hull(m.ships[s].hull));
        let mut hot = [0.0f32; 6];
        hot[usize::from(class)] = 1.0;
        assert_eq!(ext[extra_f::CLASS..extra_f::CLASS + 6], hot, "slot {s}");
        assert!(close(
            ext[extra_f::REACH],
            m_reach(&cat, m.ships[s].hull) / R
        ));
        assert!(close(
            ext[extra_f::ORDER_DIST],
            (m.ships[s].pos - ward).length() / R
        ));
        assert_eq!(ext[extra_f::IS_ORDER_SHIP], f32::from(u8::from(s == 1)));
        assert_eq!(ext[extra_f::HIT_MY_WARD], f32::from(u8::from(s == 3)));
    }
    // Classes from roles: fighter, strafer, gunship, carrier, freighter.
    let classes: Vec<u8> = [FIGHTER, STRAFER, GUNSHIP, CARRIER, FREIGHTER]
        .iter()
        .map(|&h| sim::order::hull_class(cat.hull(h)))
        .collect();
    assert_eq!(classes, [0, 1, 2, 3, 4]);
}

/// v6 hidden-order mode: a hidden team's obs is exactly that of the same ship with no
/// order (order block, `order_ships` and the order extras zero); the other team and
/// the rewards are unaffected.
#[test]
fn hidden_orders_read_exactly_as_no_order() {
    let cat = test_catalogue();
    let shown = crowded(&cat);
    let mut hidden = crowded(&cat);
    hidden.cfg.hide_orders = [true, false];
    let mut none = crowded(&cat);
    set_squad(&mut none, 0, 0, &[0], Order::None);
    let obs_hidden = full_obs(&hidden, &cat, 0);
    assert_eq!(obs_hidden, full_obs(&none, &cat, 0));
    assert_ne!(obs_hidden, full_obs(&shown, &cat, 0));
    assert_eq!(
        obs_hidden[..ORDER_OFF],
        full_obs(&shown, &cat, 0)[..ORDER_OFF]
    );
    // Team 1 is not hidden: same obs as in the shown match.
    for s in 3..8u8 {
        assert_eq!(full_obs(&hidden, &cat, s), full_obs(&shown, &cat, s));
    }
    // Rewards and tracks do not depend on the flag.
    let (mut a, mut b) = (shown, hidden);
    for m in [&mut a, &mut b] {
        m.ships[1].hp -= 10.0;
        m.hits = vec![hit(0, 3, 5.0, false)];
    }
    assert_eq!(refresh(&mut a, &cat), refresh(&mut b, &cat));
    assert_eq!(a.order_tracks, b.order_tracks);
}

/// v6 random commander: a defend wards a capital ship about `DEFEND_CAPITAL_P` of the
/// time when the team has one (else any own active ship outside the squad).
#[test]
fn random_defend_wards_a_capital_ship_half_the_time() {
    let cat = asset_catalogue();
    let (mut capital, mut defends) = (0usize, 0usize);
    for seed in 0..60u64 {
        let mut m = Match::new(
            &cat,
            &mission_cfg(&cat, MissionKind::CarrierBattle, 0, seed),
        )
        .unwrap();
        while m.phase() == MatchPhase::Running && m.tick() < 1800 {
            scripted_step(&mut m, &cat);
            if m.tick() % COMMAND_TICKS != 0 {
                continue;
            }
            for res in m.command_results(0) {
                if let Command::Squad {
                    order: Order::Defend { ward },
                    ..
                } = res.command
                {
                    defends += 1;
                    capital +=
                        usize::from(is_capital_ship(cat.hull(m.ships[usize::from(ward)].hull)));
                }
            }
        }
    }
    assert!(defends > 40, "{defends}");
    // Capital share: DEFEND_CAPITAL_P plus the uniform draw's share of capital ships.
    let share = capital as f32 / defends as f32;
    assert!(
        share > DEFEND_CAPITAL_P && share < 0.85,
        "capital share {share}"
    );
}

/// v6 scripted defender: it engages its ward's threat set, a recent hitter of the
/// ward first, even when another threat is nearer the ward.
#[test]
fn scripted_defender_engages_the_recent_hitter_first() {
    let cat = test_catalogue();
    let m = crowded(&cat);
    let set = m.threat_set(&cat, 1, m.active_mask());
    assert!(set & (1 << 3) != 0 && set & (1 << 4) != 0);
    let ward = m.ships[1].pos;
    assert!((m.ships[4].pos - ward).length() < (m.ships[3].pos - ward).length());
    let target = scripted::orders::defend_target(&m, &cat, 1).map(|s| s.slot);
    assert_eq!(target, Some(3));
    // Once the hit is old, the nearest threat to the ward.
    let mut m = m;
    m.tick += RECENT_HIT_TICKS;
    let target = scripted::orders::defend_target(&m, &cat, 1).map(|s| s.slot);
    assert_eq!(target, Some(4));
}
