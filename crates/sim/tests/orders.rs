//! v5 (M3 stage B): a ship's own order in its obs (SIM_SPEC §7.2 `order` block), order
//! instances, the order reward (§8) and the random commander (§5.9).

mod common;

use common::{FIGHTER, FREIGHTER, GUNSHIP, asset_catalogue, config, test_catalogue};
use sim::command::{COMMAND_TICKS, Command, CommanderMode, Order, Outcome, Squad, Waypoint};
use sim::data::{Catalogue, HullId};
use sim::events::HitRecord;
use sim::math::{PI, Vec2, rot};
use sim::mission::{Mission, MissionKind, default_rosters, is_capital_ship};
use sim::obs::*;
use sim::order::{CAPITAL_WAYPOINT_RADIUS, GUARD_PRESENCE};
use sim::pilot_obs_dim;
use sim::reward::{
    ORDER_ARRIVAL_BONUS, ORDER_HULL_WEIGHT, ORDER_PRESENCE_CAP_TICKS, ORDER_PRESENCE_REWARD,
    ORDER_SHAPING_GAMMA, ORDER_SHIELD_WEIGHT,
};
use sim::scripted;
use sim::scripted::random_commander::{
    self, HOLD_POINT_FRAC, HOLD_RADIUS_MAX, HOLD_RADIUS_MIN, RANDOM_SQUADS, RandomCommander,
    UNASSIGNED_FRAC,
};
use sim::setup::MatchConfig;
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
    out[ORDER_OFF..].to_vec()
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
fn guard_radius_is_presence_plus_the_ward_and_distance_is_signed() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, GUNSHIP],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (50.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Guard { ward: 1 });
    refresh(&mut m, &cat);
    let o = order_block(&m, &cat, 0);
    let radius = GUARD_PRESENCE + cat.hull(GUNSHIP).bound_radius;
    assert_eq!(o[order_f::KIND..order_f::KIND + 3], [0.0, 1.0, 0.0]);
    assert!(close(o[order_f::RADIUS], radius / R));
    assert!(close(o[order_f::SIGNED_DIST], (50.0 - radius) / R));
    assert!(
        o[order_f::SIGNED_DIST] < 0.0,
        "inside the radius reads negative"
    );
    assert!(close(o[order_f::HP], 1.0));
}

#[test]
fn hold_block_has_no_target_features_and_minus_own_velocity() {
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
        Order::Hold {
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
fn a_capital_waypoint_reads_as_a_small_hold() {
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
fn a_new_order_target_squad_move_or_dead_target_starts_an_instance() {
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
    set_squad(&mut m, 0, 2, &[0], Order::Guard { ward: 1 });
    m.step(&cat);
    assert_eq!((m.order_age(0), m.order_track(0).kind), (0, 2));
    // A hold point that moves is a new instance; a radius change alone is not.
    let hold = |p: f32, r: f32| Order::Hold {
        point: Vec2::new(p, 0.0),
        radius: r,
    };
    set_squad(&mut m, 0, 2, &[0], hold(100.0, 50.0));
    m.step(&cat);
    m.step(&cat);
    set_squad(&mut m, 0, 2, &[0], hold(100.0, 80.0));
    m.step(&cat);
    assert_eq!(m.order_age(0), 2);
    set_squad(&mut m, 0, 2, &[0], hold(120.0, 80.0));
    m.step(&cat);
    assert_eq!(m.order_age(0), 0);
    // Ship 1's attack target dies: its order reads as none at once.
    m.step(&cat);
    m.ships[3].hp = 0.0;
    m.step(&cat);
    assert_eq!((m.order_age(1), m.order_track(1).kind), (0, 0));
    assert!(order_block(&m, &cat, 1).iter().all(|&x| x == 0.0));
}

/// A fighter `dist` metres from the origin along +x, with a hold at the origin.
fn hold_match(cat: &Catalogue, dist: f32, radius: f32) -> Match {
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
        Order::Hold {
            point: Vec2::ZERO,
            radius,
        },
    );
    m
}

#[test]
fn hold_shaping_is_gamma_phi_prime_minus_phi_and_resets_on_a_new_instance() {
    let cat = test_catalogue();
    let mut m = hold_match(&cat, 200.0, 50.0);
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
    // A new hold point: Φ restarts, no reward for the jump in potential.
    set_squad(
        &mut m,
        0,
        0,
        &[0],
        Order::Hold {
            point: Vec2::new(-200.0, 0.0),
            radius: 50.0,
        },
    );
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
    assert!(close(m.order_track(0).last_phi, -(380.0 - 50.0) / R));
}

#[test]
fn arrival_pays_once_and_presence_is_capped_per_instance() {
    let cat = test_catalogue();
    let mut m = hold_match(&cat, 100.0, 50.0);
    refresh(&mut m, &cat);
    let phi = -50.0 / R;
    m.ships[0].pos.x = 30.0;
    let first = refresh(&mut m, &cat)[0];
    assert!(close(
        first,
        -phi + ORDER_ARRIVAL_BONUS + ORDER_PRESENCE_REWARD
    ));
    assert!(m.order_track(0).arrived);
    // Leave and come back: no second arrival bonus in the same instance.
    m.ships[0].pos.x = 60.0;
    refresh(&mut m, &cat);
    m.ships[0].pos.x = 30.0;
    let back = refresh(&mut m, &cat)[0];
    assert!(back < ORDER_ARRIVAL_BONUS);
    // Presence: at most ORDER_PRESENCE_CAP_TICKS ticks paid.
    let mut paid = 0;
    for _ in 0..500 {
        if refresh(&mut m, &cat)[0] > 0.0 {
            paid += 1;
        }
    }
    assert_eq!(m.order_track(0).presence_ticks, ORDER_PRESENCE_CAP_TICKS);
    assert_eq!(paid, usize::from(ORDER_PRESENCE_CAP_TICKS) - 2);
    assert_eq!(refresh(&mut m, &cat)[0], 0.0);
    // A new instance pays arrival and presence again.
    set_squad(
        &mut m,
        0,
        0,
        &[0],
        Order::Hold {
            point: Vec2::new(10.0, 0.0),
            radius: 50.0,
        },
    );
    assert!(close(
        refresh(&mut m, &cat)[0],
        ORDER_ARRIVAL_BONUS + ORDER_PRESENCE_REWARD
    ));
}

#[test]
fn ships_that_do_not_earn_get_no_order_reward() {
    let cat = test_catalogue();
    let mut m = hold_match(&cat, 20.0, 50.0);
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

#[test]
fn guard_pays_damage_to_enemies_near_the_ward() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, GUNSHIP],
        &[FIGHTER, FIGHTER],
        &[
            (0.0, 0.0, 0.0),
            (0.0, 20.0, 0.0),
            (100.0, 20.0, PI),
            (400.0, 20.0, PI),
        ],
    );
    set_squad(&mut m, 0, 0, &[0], Order::Guard { ward: 1 });
    refresh(&mut m, &cat);
    m.hits = vec![hit(0, 2, 10.0, false), hit(0, 3, 10.0, false)];
    let r = refresh(&mut m, &cat)[0];
    // Inside the guard radius from the start: shaping 0 (Φ = 0 both steps).
    assert!(close(r, ORDER_HULL_WEIGHT * 10.0 + ORDER_PRESENCE_REWARD));
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
                            Order::Guard { ward } => {
                                assert_eq!(m.ships[usize::from(ward)].team, team);
                                assert_eq!(members & (1 << ward), 0, "guarding itself");
                            }
                            Order::Hold { point, radius } => {
                                assert!(point.length() <= HOLD_POINT_FRAC * R + 1e-3);
                                assert!((HOLD_RADIUS_MIN..HOLD_RADIUS_MAX).contains(&radius));
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
/// hold a point away from the only enemy flies to the point under `Random`, and at
/// the enemy under `Scripted`.
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
            Order::Hold {
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
            matches!(m.command.squads[0][0].order, Order::Hold { .. })
                || mode != CommanderMode::Random
        );
        (m.ships[0].pos - point).length()
    };
    let random = run(CommanderMode::Random);
    let scripted = run(CommanderMode::Scripted);
    assert!(random < 120.0, "random: {random} m from the hold point");
    assert!(
        scripted > 250.0,
        "scripted: {scripted} m from the hold point"
    );
}
