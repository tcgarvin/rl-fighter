//! WP2 acceptance (SIM_SPEC §14): thrusters, drag, soft cap, power, actions, setup,
//! and same-seed hash equality; WP11 (§14.1): throttle ramp, v2 damping, reaction
//! delay, control lock and the `act_mask` contract. Drives the full `Match::step`.

mod common;

use common::{
    FIGHTER, GUNSHIP, STRAFER, catalogue_with_static, config, new_match, new_present_match,
    test_catalogue,
};
use sim::DT;
use sim::actions::{
    ACTION_WIDTH, ShipAction, THROTTLE_DECREASE, THROTTLE_HOLD, THROTTLE_INCREASE, act_mask,
    fixed_turret, thruster_mask, turret_mask,
};
use sim::data::Catalogue;
use sim::math::PI;
use sim::physics::{ANGULAR_DRAG, LINEAR_DRAG, RAMP_RATE, RAMP_STEP, ramp_level};
use sim::power::{self, POWER_TARGETS, multiplier, two_way_target};
use sim::setup::{MatchConfig, SetupError};
use sim::state::{Attach, MAX_REACTION_TICKS, Match, MatchPhase, NONE};

const EPS: f32 = 1e-5;

fn close(a: f32, b: f32, tol: f32) -> bool {
    (a - b).abs() <= tol
}

/// Fighter 1v1 with ship 0 driven by the throttle heads `throttle` (other heads idle;
/// no reaction delay). The arena is widened and the opponent parked off the flight
/// line, so long runs under the full `step` see free-flight physics only (no
/// boundary push, no collision).
fn fighter_with_throttle(throttle: &[u8]) -> (Catalogue, Match) {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 1, &[FIGHTER], &[FIGHTER]);
    m.cfg.arena_radius = 1.0e5;
    m.ships[1].pos = sim::Vec2::new(0.0, 5000.0);
    let mut a = ShipAction::IDLE;
    a.throttle[..throttle.len()].copy_from_slice(throttle);
    m.set_action(0, a);
    (cat, m)
}

#[test]
fn main_thruster_accelerates_forward() {
    let (cat, mut m) = fighter_with_throttle(&[2]);
    let start = m.ships[0].pos;
    m.step(&cat);
    let s = &m.ships[0];
    // The first INCREASE already pushes at level 1/6 (stage 3 ramps before stage 5):
    // 900 N * 1/6 / 10 kg at even power (P_e = 1), one tick, then drag.
    assert_eq!(s.thrust_level[0], RAMP_STEP);
    let want = 900.0 * RAMP_STEP / 10.0 * DT * LINEAR_DRAG;
    assert!(close(s.vel.x, want, EPS), "vel.x {} want {want}", s.vel.x);
    assert_eq!(s.vel.y, 0.0);
    assert_eq!(s.omega, 0.0, "main thruster is on the axis: no torque");
    assert!(s.pos.x > start.x);
    assert_eq!(s.heading, 0.0);
}

#[test]
fn force_is_max_force_times_level_times_engine_power() {
    // Held levels 0.25 / 0.5 / 1.0 at even power, and 0.5 at engines 0.75 (P_e = 1.4).
    let cases = [(0.25, 0, 1.0), (0.5, 0, 1.0), (1.0, 0, 1.0), (0.5, 2, 1.4)];
    for (level, power_idx, p_e) in cases {
        let (cat, mut m) = fighter_with_throttle(&[THROTTLE_HOLD]);
        m.ships[0].thrust_level[0] = level;
        m.ships[0].power = two_way_target(power_idx);
        m.ships[0].power_target = two_way_target(power_idx);
        let mut a = m.pending[0];
        a.power = power_idx as u8;
        m.set_action(0, a);
        m.step(&cat);
        assert_eq!(m.ships[0].thrust_level[0], level, "HOLD keeps the level");
        let want = 900.0 * level * p_e / 10.0 * DT * LINEAR_DRAG;
        let got = m.ships[0].vel.x;
        assert!(
            close(got, want, 1e-4),
            "level {level} P_e {p_e}: {got} want {want}"
        );
    }
}

#[test]
fn thrust_follows_heading() {
    let (cat, mut m) = fighter_with_throttle(&[2]);
    m.ships[0].thrust_level[0] = 1.0;
    m.ships[0].heading = 0.5 * PI;
    m.step(&cat);
    let s = &m.ships[0];
    assert!(s.vel.y > 2.9, "vel {:?}", s.vel);
    assert!(s.vel.x.abs() < 1e-4, "vel {:?}", s.vel);
}

#[test]
fn engine_power_scales_thrust() {
    // Fighter is two-way: target 2 = engines 0.75 → P_e = 0.2 + 0.8*2*0.75 = 1.4.
    let (cat, mut m) = fighter_with_throttle(&[2]);
    m.ships[0].thrust_level[0] = 1.0;
    m.ships[0].power = two_way_target(2);
    m.ships[0].power_target = two_way_target(2);
    let mut a = m.pending[0];
    a.power = 2;
    m.set_action(0, a);
    m.step(&cat);
    let want = 900.0 * 1.4 / 10.0 * DT * LINEAR_DRAG;
    assert!(close(m.ships[0].vel.x, want, 1e-4));
}

#[test]
fn rcs_pair_pivots_without_translating() {
    // fl (pushes -y at the nose-port) + rr (pushes +y at the tail-starboard): clockwise.
    let (cat, mut cw) = fighter_with_throttle(&[0, 2, 0, 0, 2]);
    // fr + rl: counter-clockwise.
    let (_, mut ccw) = fighter_with_throttle(&[0, 0, 2, 2, 0]);
    let start = cw.ships[0].pos;
    // Few enough ticks that the heading has not wrapped past ±π.
    for _ in 0..10 {
        cw.step(&cat);
        ccw.step(&cat);
    }
    let (a, b) = (&cw.ships[0], &ccw.ships[0]);
    assert!(
        a.omega < -0.1 && a.heading < -0.1,
        "cw omega {} heading {}",
        a.omega,
        a.heading
    );
    assert!(
        b.omega > 0.1 && b.heading > 0.1,
        "ccw omega {} heading {}",
        b.omega,
        b.heading
    );
    assert!(close(a.omega, -b.omega, EPS), "pairs are mirror images");
    for s in [a, b] {
        assert!(s.vel.length() < 1e-4, "net force cancels: vel {:?}", s.vel);
        assert!((s.pos - start).length() < 1e-4);
    }
    // First-tick torque at level 1/6: |cross(fl.pos, fl.F)| + |cross(rr.pos, rr.F)| =
    // (352 + 448) / 6.
    let (cat, mut one) = fighter_with_throttle(&[0, 2, 0, 0, 2]);
    one.step(&cat);
    let want = -800.0 * RAMP_STEP / 55.0 * DT * ANGULAR_DRAG;
    assert!(close(one.ships[0].omega, want, EPS));
}

#[test]
fn drag_settles_motion() {
    let (cat, mut m) = fighter_with_throttle(&[]);
    m.ships[0].vel = sim::Vec2::new(20.0, -10.0);
    m.ships[0].omega = 2.0;
    let v0 = m.ships[0].vel.length();
    m.step(&cat);
    assert!(close(m.ships[0].vel.length(), v0 * LINEAR_DRAG, 1e-4));
    assert!(close(m.ships[0].omega, 2.0 * ANGULAR_DRAG, EPS));
    for _ in 0..1500 {
        m.step(&cat);
    }
    let s = &m.ships[0];
    assert!(s.vel.length() < 0.01 * v0, "speed {}", s.vel.length());
    assert!(s.omega.abs() < 1e-6, "omega {}", s.omega);
}

#[test]
fn soft_cap_limits_speed_under_full_thrust() {
    let (cat, mut m) = fighter_with_throttle(&[2]);
    for _ in 0..300 {
        m.step(&cat);
    }
    // Even split: P_e = 1 → cap = speed_cap. Uncapped terminal speed would be ~600.
    let speed = m.ships[0].vel.length();
    assert!(close(speed, 60.0, 0.05), "speed {speed}");
}

#[test]
fn soft_cap_bleeds_at_most_eight_percent_per_tick() {
    let (cat, mut m) = fighter_with_throttle(&[]);
    m.ships[0].vel = sim::Vec2::new(200.0, 0.0);
    let mut prev = 200.0f32;
    for _ in 0..200 {
        m.step(&cat);
        let speed = m.ships[0].vel.length();
        let floor = prev * LINEAR_DRAG * 0.92;
        assert!(speed >= floor - 1e-3 && speed < prev, "{prev} → {speed}");
        prev = speed;
    }
    assert!(prev < 60.0);
}

#[test]
fn soft_cap_rises_with_engine_power() {
    // Engines 0.75 → P_e = 1.4 → cap = 60 * (0.6 + 0.56) = 69.6.
    let (cat, mut m) = fighter_with_throttle(&[2]);
    let mut a = m.pending[0];
    a.power = 2;
    m.set_action(0, a);
    for _ in 0..400 {
        m.step(&cat);
    }
    let speed = m.ships[0].vel.length();
    assert!(close(speed, 69.6, 0.1), "speed {speed}");
}

#[test]
fn static_hull_is_not_integrated() {
    let (cat, station) = catalogue_with_static();
    let mut m = new_present_match(&cat, 3, &[station], &[FIGHTER]);
    m.ships[0].vel = sim::Vec2::new(5.0, 0.0);
    let mut a = ShipAction::IDLE;
    a.fire[0] = 1;
    a.power = 3;
    m.set_action(0, a);
    let before = m.ships[0].clone();
    for _ in 0..30 {
        m.step(&cat);
    }
    let s = &m.ships[0];
    assert_eq!(s.pos, before.pos);
    assert_eq!(s.vel, before.vel);
    assert_eq!(s.heading, before.heading);
    // v2: a static hull is always locked (§5 stage 3): no fire, power target kept.
    assert_eq!(
        m.applied[0],
        ShipAction::LOCKED,
        "static hulls apply LOCKED"
    );
    assert_eq!(m.shots_fired[0], 0, "static hulls never fire");
    assert_eq!(s.power_target, before.power_target);
}

/// Fighter + gunship vs fighter, all present and spread out, delay `d`; ships 0 and 1
/// control-locked until tick `lock` with every level at 1. Returns the action that
/// asks for everything: thrust up, slew left, fire, power 3.
fn locked_match(d: u8, lock: u32) -> (Catalogue, Match, ShipAction) {
    let cat = test_catalogue();
    let mut cfg = config(21, &[FIGHTER, GUNSHIP], &[FIGHTER]);
    cfg.reaction_ticks = d;
    cfg.arena_radius = 1.0e5;
    let mut m = Match::new(&cat, &cfg).unwrap();
    common::make_all_present(&mut m);
    for (i, s) in m.ships.iter_mut().enumerate() {
        s.pos = sim::Vec2::new(0.0, 1000.0 * i as f32);
    }
    let mut a = ShipAction::IDLE;
    a.throttle = [THROTTLE_INCREASE; 8];
    a.slew = [0; 6];
    a.fire = [1; 6];
    a.power = 3;
    for s in 0..2 {
        m.ships[s].control_lock_until = lock;
        m.ships[s].thrust_level[..5].fill(1.0);
    }
    (cat, m, a)
}

#[test]
fn locked_ship_decays_levels_holds_turrets_and_keeps_power() {
    for d in 0..=MAX_REACTION_TICKS as u8 {
        let lock = 12;
        let (cat, mut m, a) = locked_match(d, lock);
        let before = m.ships.clone();
        let mut prev_level = 1.0;
        // The steps that end at ticks 1..lock-1 are all inside the lock.
        while m.tick() + 1 < lock {
            for s in 0..3 {
                m.set_action(s, a);
            }
            m.step(&cat);
            for (s, was) in before.iter().enumerate().take(2) {
                let ship = &m.ships[s];
                assert_eq!(m.applied[s], ShipAction::LOCKED, "d {d} tick {}", m.tick());
                assert_eq!(ship.turret_angle, was.turret_angle, "turrets hold");
                assert_eq!(ship.power_target, was.power_target, "power kept");
                assert_eq!(m.shots_fired[s], 0, "no fire while locked");
            }
            let level = m.ships[0].thrust_level[0];
            assert_eq!(level, ramp_level(prev_level, THROTTLE_DECREASE));
            prev_level = level;
        }
        assert_eq!(m.ships[0].thrust_level, [0.0; 8], "d {d}: decayed to 0");
        assert_eq!(m.ships[1].thrust_level, [0.0; 8], "d {d}: decayed to 0");
        // The unlocked ship 2 has been acting since tick 1 + d.
        assert_eq!(m.ships[2].power_target, two_way_target(3), "d {d}");
        // The lock ends: the actions chosen in the last d locked ticks now apply.
        for s in 0..3 {
            m.set_action(s, a);
        }
        m.step(&cat);
        assert_eq!(m.tick(), lock);
        assert_eq!(m.applied[0], a.sanitized(cat.hull(FIGHTER)), "d {d}");
        assert_eq!(m.ships[0].thrust_level[0], RAMP_STEP);
        assert_eq!(m.shots_fired[0], 1, "d {d}");
    }
}

#[test]
fn act_mask_follows_the_application_tick() {
    let cat = test_catalogue();
    for d in 0..=MAX_REACTION_TICKS as u8 {
        let mut m = new_present_match(&cat, 1, &[FIGHTER], &[FIGHTER]);
        m.ships[0].reaction_ticks = d;
        m.ships[0].control_lock_until = 10;
        // Chosen at obs tick t, applied at t + 1 + d: unmasked iff that is >= 10.
        for t in 0..12u32 {
            m.tick = t;
            assert_eq!(m.act_mask(0), t + 1 + u32::from(d) >= 10, "d {d} t {t}");
        }
        m.ships[0].present = false;
        assert!(!act_mask(&m.ships[0], 20));
        m.ships[0].present = true;
        m.ships[0].alive = false;
        assert!(!act_mask(&m.ships[0], 20));
    }
}

#[test]
fn power_slew_reaches_target_in_gap_over_rate() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 1, &[STRAFER], &[FIGHTER]);
    let mut a = ShipAction::IDLE;
    a.power = 2; // (0.2, 0.6, 0.2)
    m.set_action(0, a);
    let target = POWER_TARGETS[2];
    let gap = target[1] - 1.0 / 3.0;
    let ticks = (gap / power::POWER_SLEW_RATE / DT).ceil() as u32; // 0.593 s → 18
    for t in 1..=ticks {
        m.step(&cat);
        let p = m.ships[0].power;
        assert!(
            close(p.iter().sum::<f32>(), 1.0, 1e-5),
            "shares sum to 1: {p:?}"
        );
        let reached = p.iter().zip(&target).all(|(a, b)| close(*a, *b, 1e-6));
        assert_eq!(reached, t == ticks, "tick {t}: {p:?}");
        if t < ticks {
            // The largest gap closes linearly at 0.45 / s.
            let want = 1.0 / 3.0 + power::POWER_SLEW_RATE * DT * t as f32;
            assert!(close(p[1], want, 1e-5), "tick {t}: {} want {want}", p[1]);
        }
    }
}

#[test]
fn shieldless_hull_keeps_zero_shield_power() {
    let (cat, mut m) = fighter_with_throttle(&[]);
    let mut a = m.pending[0];
    a.power = 1; // shields-heavy on a three-way hull; even split on two-way
    m.set_action(0, a);
    m.step(&cat);
    assert_eq!(m.ships[0].power, [0.0, 0.5, 0.5]);
    a.power = 4;
    m.set_action(0, a);
    for _ in 0..60 {
        m.step(&cat);
        assert_eq!(m.ships[0].power[0], 0.0);
    }
    assert!(close(m.ships[0].power[1], 2.0 / 3.0, 1e-5));
}

#[test]
fn power_target_table_values() {
    for row in POWER_TARGETS {
        assert!(close(row.iter().sum::<f32>(), 1.0, 1e-6));
    }
    let want = [
        [0.5, 0.5],
        [0.5, 0.5],
        [0.75, 0.25],
        [0.25, 0.75],
        [2.0 / 3.0, 1.0 / 3.0],
        [1.0 / 3.0, 2.0 / 3.0],
        [0.5, 0.5],
    ];
    for (i, w) in want.iter().enumerate() {
        let t = two_way_target(i);
        assert_eq!(t[0], 0.0);
        assert!(
            close(t[1], w[0], 1e-6) && close(t[2], w[1], 1e-6),
            "idx {i}: {t:?}"
        );
        assert!(close(t[1] + t[2], 1.0, 1e-6));
    }
    let cat = test_catalogue();
    assert_eq!(power::target_for(cat.hull(GUNSHIP), 5), POWER_TARGETS[5]);
    assert_eq!(power::target_for(cat.hull(FIGHTER), 0), [0.0, 0.5, 0.5]);
}

#[test]
fn multiplier_table_values() {
    // Even split → 1.0; cap (0.6 three-way / 0.8 two-way) → 1.64 / 1.48; zero → 0.2.
    assert!(close(multiplier(3, 1.0 / 3.0), 1.0, EPS));
    assert!(close(multiplier(2, 0.5), 1.0, EPS));
    assert!(close(multiplier(3, 0.6), 1.64, EPS));
    assert!(close(multiplier(2, 0.8), 1.48, EPS));
    assert!(close(multiplier(3, 0.2), 0.68, EPS));
    assert!(close(multiplier(2, 0.75), 1.4, EPS));
    assert_eq!(multiplier(3, 0.0), 0.2);
    assert_eq!(multiplier(2, 0.0), 0.2);
    let p = power::multipliers(3, POWER_TARGETS[2]);
    assert!(close(p[0], 0.68, EPS) && close(p[1], 1.64, EPS) && close(p[2], 0.68, EPS));
}

#[test]
fn action_row_round_trip() {
    let a = ShipAction {
        throttle: [0, 1, 2, 0, 1, 2, 0, 1],
        slew: [0, 1, 2, 2, 1, 0],
        fire: [1, 0, 1, 0, 0, 1],
        power: 6,
    };
    let mut row = [0i8; ACTION_WIDTH];
    a.to_row(&mut row);
    assert_eq!(
        row,
        [
            0, 1, 2, 0, 1, 2, 0, 1, 0, 1, 2, 2, 1, 0, 1, 0, 1, 0, 0, 1, 6
        ]
    );
    assert_eq!(ShipAction::from_row(&row), a);
    assert_eq!(ACTION_WIDTH, 21);
}

#[test]
fn action_row_clamps_out_of_range() {
    let mut row = [0i8; ACTION_WIDTH];
    row[0] = 5;
    row[1] = -3;
    row[2] = i8::MIN;
    row[8] = 9;
    row[9] = -1;
    row[14] = 2;
    row[15] = i8::MAX;
    row[16] = -7;
    row[20] = 100;
    let a = ShipAction::from_row(&row);
    assert_eq!(&a.throttle[..3], &[2, 0, 0]);
    assert_eq!(&a.slew[..2], &[2, 0]);
    assert_eq!(&a.fire[..3], &[1, 1, 0]);
    assert_eq!(a.power, 6);
    // to_row clamps too.
    let wild = ShipAction {
        throttle: [9; 8],
        slew: [7; 6],
        fire: [3; 6],
        power: 200,
    };
    let mut out = [0i8; ACTION_WIDTH];
    wild.to_row(&mut out);
    let clamped = ShipAction {
        throttle: [2; 8],
        slew: [2; 6],
        fire: [1; 6],
        power: 6,
    };
    assert_eq!(ShipAction::from_row(&out), clamped);
}

#[test]
fn slew_sign_and_masks() {
    let mut a = ShipAction::IDLE;
    a.slew[0] = 0;
    a.slew[2] = 2;
    assert_eq!(
        [a.slew_sign(0), a.slew_sign(1), a.slew_sign(2)],
        [1.0, 0.0, -1.0]
    );
    let cat = test_catalogue();
    let g = cat.hull(GUNSHIP);
    assert_eq!(
        thruster_mask(g),
        [true, true, true, true, true, true, false, false]
    );
    assert_eq!(turret_mask(g), [true, true, true, false, false, false]);
    assert_eq!(fixed_turret(g), [false; 6]);
    assert!(fixed_turret(cat.hull(FIGHTER))[0]);
    assert!(!fixed_turret(cat.hull(FIGHTER))[1]);
}

#[test]
fn unused_slots_are_ignored() {
    // Throttles beyond the fighter's 5 thrusters must not move it.
    let (cat, mut m) = fighter_with_throttle(&[0, 0, 0, 0, 0, 2, 2, 2]);
    m.step(&cat);
    assert_eq!(m.ships[0].thrust_level, [0.0; 8]);
    assert_eq!(m.ships[0].vel, sim::Vec2::ZERO);
}

#[test]
fn setup_places_teams_on_opposite_sides() {
    let cat = test_catalogue();
    let m = new_match(&cat, 5, &[FIGHTER, STRAFER], &[GUNSHIP]);
    assert_eq!(m.ships.len(), 3);
    assert_eq!(m.tick(), 0);
    assert_eq!(m.phase(), MatchPhase::Running);
    assert_eq!(m.winner(), -2);
    for (i, s) in m.ships().iter().enumerate() {
        assert_eq!(s.slot as usize, i);
        assert!(s.alive && !s.present, "ships jump in later (§5.6)");
        assert_eq!(s.hp, cat.hull(s.hull).hp);
        assert_eq!(s.parent, NONE);
        assert_eq!(s.attach, Attach::None);
        assert_eq!(s.last_hit_tick, u32::MAX);
        assert!(s.pos.length() < m.cfg.arena_radius);
    }
    let (a, b, c) = (&m.ships[0], &m.ships[1], &m.ships[2]);
    assert_eq!((a.team, b.team, c.team), (0, 0, 1));
    assert!(a.pos.x < 0.0 && b.pos.x < 0.0 && c.pos.x > 0.0);
    assert_eq!(a.heading, 0.0);
    assert_eq!(c.heading, PI);
    assert_ne!(a.pos, b.pos);
    assert_eq!(b.shield, 40.0);
    assert_eq!(a.shield, 0.0);
    assert_eq!(c.power, POWER_TARGETS[0]);
    assert_eq!(a.power, [0.0, 0.5, 0.5]);
    // Turrets start at rest.
    assert!(close(c.turret_angle[1], 0.5 * PI, EPS));
    assert!(m.projectiles().iter().all(|p| !p.alive));
}

#[test]
fn setup_rejects_bad_configs() {
    let cat = test_catalogue();
    let cfg = |t0: Vec<u16>, t1: Vec<u16>| MatchConfig {
        fleets: [t0, t1],
        ..MatchConfig::default()
    };
    assert_eq!(
        Match::new(&cat, &cfg(vec![], vec![0])).unwrap_err(),
        SetupError::EmptyFleet { team: 0 }
    );
    assert_eq!(
        Match::new(&cat, &cfg(vec![0; 5], vec![0; 4])).unwrap_err(),
        SetupError::TooManyShips { count: 9 }
    );
    assert_eq!(
        Match::new(&cat, &cfg(vec![0], vec![7])).unwrap_err(),
        SetupError::UnknownHull { team: 1, hull: 7 }
    );
    let mut bad = cfg(vec![0], vec![0]);
    bad.arena_radius = 0.0;
    assert!(matches!(
        Match::new(&cat, &bad),
        Err(SetupError::InvalidArenaRadius { .. })
    ));
    bad.arena_radius = 450.0;
    bad.time_limit_ticks = 0;
    assert_eq!(
        Match::new(&cat, &bad).unwrap_err(),
        SetupError::ZeroTimeLimit
    );
    bad.time_limit_ticks = 100;
    bad.reaction_ticks = 5;
    assert_eq!(
        Match::new(&cat, &bad).unwrap_err(),
        SetupError::ReactionTooLong { ticks: 5 }
    );
    bad.reaction_ticks = MAX_REACTION_TICKS as u8;
    assert!(Match::new(&cat, &bad).is_ok());
    assert!(Match::new(&cat, &cfg(vec![0; 4], vec![1; 4])).is_ok());
}

/// A deterministic, varied action for ship `slot` at tick `t`.
fn scripted_row(t: u32, slot: usize) -> ShipAction {
    let mut row = [0i8; ACTION_WIDTH];
    for (i, r) in row.iter_mut().enumerate() {
        *r = ((t as usize * 7 + slot * 13 + i * 5) % 3) as i8;
    }
    row[20] = ((t / 20 + slot as u32) % 7) as i8;
    ShipAction::from_row(&row)
}

fn drive(m: &mut Match, cat: &Catalogue) {
    let t = m.tick();
    for slot in 0..m.ships.len() {
        m.set_action(slot as u8, scripted_row(t, slot));
    }
    m.step(cat);
}

#[test]
fn same_seed_matches_hash_equal_every_tick() {
    let cat = test_catalogue();
    let fleets: (&[u16], &[u16]) = (&[FIGHTER, STRAFER], &[GUNSHIP, FIGHTER]);
    let mut a = new_present_match(&cat, 11, fleets.0, fleets.1);
    let mut b = new_present_match(&cat, 11, fleets.0, fleets.1);
    let mut other = new_present_match(&cat, 12, fleets.0, fleets.1);
    assert_eq!(a.state_hash(), b.state_hash());
    assert_ne!(
        a.state_hash(),
        other.state_hash(),
        "seed is part of the state"
    );
    for _ in 0..300 {
        drive(&mut a, &cat);
        drive(&mut other, &cat);
        drive(&mut b, &cat);
        assert_eq!(a.state_hash(), b.state_hash(), "tick {}", a.tick());
    }
    assert!(a.ships.iter().all(|s| s.pos.x.is_finite()));
    // The hash sees the state: any nudge changes it.
    let h = a.state_hash();
    a.ships[3].omega = f32::from_bits(a.ships[3].omega.to_bits() ^ 1);
    assert_ne!(a.state_hash(), h);
}

// ---------------------------------------------------------------------------
// v2 (WP11): throttle ramp, damping, reaction delay, act_mask contract
// ---------------------------------------------------------------------------

#[test]
fn level_ramps_zero_to_full_in_exactly_six_ticks_and_clamps() {
    assert_eq!(RAMP_STEP, RAMP_RATE * DT);
    let (cat, mut m) = fighter_with_throttle(&[THROTTLE_INCREASE]);
    for t in 1..=8 {
        m.step(&cat);
        let level = m.ships[0].thrust_level[0];
        if t < 6 {
            assert!(level < 1.0, "tick {t}: {level}");
            assert!(
                close(level, t as f32 * RAMP_STEP, 1e-6),
                "tick {t}: {level}"
            );
        } else {
            assert_eq!(level, 1.0, "tick {t}: full from tick 6 on, clamped");
        }
    }
    let mut a = ShipAction::IDLE;
    a.throttle[0] = THROTTLE_DECREASE;
    m.set_action(0, a);
    for t in 1..=8 {
        m.step(&cat);
        let level = m.ships[0].thrust_level[0];
        assert_eq!(level == 0.0, t >= 6, "tick {t}: {level}");
        assert!(level >= 0.0);
    }
}

#[test]
fn hold_keeps_a_level_bit_exact() {
    let (cat, mut m) = fighter_with_throttle(&[THROTTLE_INCREASE, THROTTLE_INCREASE]);
    for _ in 0..3 {
        m.step(&cat);
    }
    let levels = m.ships[0].thrust_level;
    assert!(levels[0] > 0.0 && levels[0] < 1.0);
    m.set_action(0, ShipAction::IDLE);
    for _ in 0..100 {
        m.step(&cat);
        assert_eq!(
            m.ships[0].thrust_level.map(f32::to_bits),
            levels.map(f32::to_bits)
        );
    }
}

#[test]
fn damping_constants_are_the_v2_literals() {
    assert!(close(LINEAR_DRAG, 1.0 - 0.005 * 2.0 / 3.0, 1e-7));
    assert_eq!(LINEAR_DRAG, 0.996_666_7);
    assert_eq!(ANGULAR_DRAG, 0.96);
    // A coasting ship keeps LINEAR_DRAG^30 (about 0.9048) of its speed after 1 s.
    let (cat, mut m) = fighter_with_throttle(&[]);
    m.ships[0].vel = sim::Vec2::new(30.0, 0.0);
    for _ in 0..30 {
        m.step(&cat);
    }
    let kept = m.ships[0].vel.x / 30.0;
    assert!(close(kept, 0.996_666_7f32.powi(30), 1e-5), "kept {kept}");
    assert!(close(kept, 0.9048, 1e-3), "kept {kept}");
}

/// A present fighter 1v1 (opponent parked) with reaction delay `d` on both ships.
fn delayed_fighter(d: u8) -> (Catalogue, Match) {
    let cat = test_catalogue();
    let mut cfg = config(5, &[FIGHTER], &[FIGHTER]);
    cfg.reaction_ticks = d;
    cfg.arena_radius = 1.0e5;
    let mut m = Match::new(&cat, &cfg).unwrap();
    common::make_all_present(&mut m);
    m.ships[1].pos = sim::Vec2::new(0.0, 5000.0);
    (cat, m)
}

#[test]
fn delay_two_applies_on_the_third_step_and_shows_in_the_queue() {
    let (cat, mut m) = delayed_fighter(2);
    assert_eq!(m.ships[0].reaction_ticks, 2);
    for _ in 0..5 {
        m.step(&cat);
    }
    let t = m.tick();
    let mut a = ShipAction::IDLE;
    a.throttle[0] = THROTTLE_INCREASE;
    m.set_action(0, a);
    m.step(&cat); // ends at t + 1: enqueued at the back
    m.set_action(0, ShipAction::IDLE);
    assert_eq!(m.ships[0].thrust_level[0], 0.0);
    assert_eq!(m.ships[0].queue[1], a);
    assert_eq!(m.ships[0].queue[0], ShipAction::IDLE);
    m.step(&cat); // ends at t + 2: next in line
    assert_eq!(m.ships[0].thrust_level[0], 0.0);
    assert_eq!(m.ships[0].queue[0], a);
    assert_eq!(m.ships[0].queue[1], ShipAction::IDLE);
    m.step(&cat); // ends at t + 3: applied
    assert_eq!(m.tick(), t + 3);
    assert_eq!(m.applied[0], a);
    assert_eq!(m.ships[0].thrust_level[0], RAMP_STEP);
    assert_eq!(m.ships[0].queue, [ShipAction::IDLE; MAX_REACTION_TICKS]);
    m.step(&cat);
    assert_eq!(m.ships[0].thrust_level[0], RAMP_STEP, "a single INCREASE");
}

#[test]
fn every_delay_applies_after_d_plus_one_steps() {
    for d in 0..=MAX_REACTION_TICKS as u8 {
        let (cat, mut m) = delayed_fighter(d);
        let mut a = ShipAction::IDLE;
        a.throttle[0] = THROTTLE_INCREASE;
        m.set_action(0, a);
        m.step(&cat);
        m.set_action(0, ShipAction::IDLE);
        for k in 0..d {
            assert_eq!(m.ships[0].thrust_level[0], 0.0, "d {d} step {k}");
            assert_eq!(
                m.ships[0].queue[usize::from(d - 1 - k)],
                a,
                "d {d} step {k}"
            );
            m.step(&cat);
        }
        assert_eq!(m.ships[0].thrust_level[0], RAMP_STEP, "d {d}");
        // Queue slots at and beyond d stay IDLE throughout.
        assert!(m.ships[0].queue.iter().all(|q| *q == ShipAction::IDLE));
    }
}

#[test]
fn hull_reaction_ticks_overrides_the_match_config() {
    let mut cat = test_catalogue();
    cat.hulls[STRAFER as usize].reaction_ticks = Some(4);
    let mut cfg = config(5, &[FIGHTER, STRAFER], &[FIGHTER]);
    cfg.reaction_ticks = 1;
    let m = Match::new(&cat, &cfg).unwrap();
    let d: Vec<u8> = m.ships.iter().map(|s| s.reaction_ticks).collect();
    assert_eq!(d, vec![1, 4, 1]);
    assert_eq!(MatchConfig::default().reaction_ticks, 2);
}

/// Sticky random action rows from a private LCG (the test's own stream).
struct RowGen(u64);

impl RowGen {
    fn next(&mut self) -> u32 {
        self.0 = self
            .0
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        (self.0 >> 33) as u32
    }

    fn row(&mut self) -> ShipAction {
        let mut row = [0i8; ACTION_WIDTH];
        for (i, r) in row.iter_mut().enumerate() {
            let n = if i == ACTION_WIDTH - 1 { 7 } else { 3 };
            *r = (self.next() % n) as i8;
        }
        ShipAction::from_row(&row)
    }
}

/// A 2v2 from the real jump-in with delay `d`, up to 3000 ticks of sticky random
/// rows; with `patch`, every row whose `act_mask` is false is replaced by noise.
/// Returns the state hash after every step.
fn masked_rows_run(d: u8, patch: bool) -> Vec<u64> {
    let cat = test_catalogue();
    let mut cfg = config(31, &[FIGHTER, STRAFER], &[GUNSHIP, FIGHTER]);
    cfg.reaction_ticks = d;
    cfg.time_limit_ticks = 3000;
    let mut m = Match::new(&cat, &cfg).unwrap();
    let mut base = RowGen(7);
    let mut noise = RowGen(99);
    let mut rows = [ShipAction::IDLE; 4];
    let mut hashes = Vec::new();
    let mut patched = 0;
    while m.phase() == MatchPhase::Running {
        for (s, row) in rows.iter_mut().enumerate() {
            if base.next() % 8 == 0 {
                *row = base.row();
            }
            let noisy = noise.row();
            let a = if patch && !m.act_mask(s as u8) {
                patched += 1;
                noisy
            } else {
                *row
            };
            m.set_action(s as u8, a);
        }
        m.step(&cat);
        hashes.push(m.state_hash());
    }
    assert!(
        !patch || patched > 100,
        "d {d}: only {patched} rows patched"
    );
    hashes
}

#[test]
fn masked_rows_have_no_effect_on_state() {
    for d in [0, 2, 4] {
        let clean = masked_rows_run(d, false);
        let patched = masked_rows_run(d, true);
        assert!(clean.len() > 200, "d {d}: match ran {} ticks", clean.len());
        assert_eq!(clean, patched, "d {d}");
    }
}

#[test]
fn unmasked_rows_on_the_last_locked_ticks_take_effect() {
    let cat = test_catalogue();
    for d in 1..=MAX_REACTION_TICKS as u8 {
        let mut cfg = config(31, &[FIGHTER], &[FIGHTER]);
        cfg.reaction_ticks = d;
        let mut m = Match::new(&cat, &cfg).unwrap();
        // Run until ship 0 is inside its arrival lock with act_mask already true.
        while !(m.ships[0].present && m.act_mask(0)) {
            m.step(&cat);
        }
        assert!(
            m.ships[0].control_locked(m.tick() + 1),
            "d {d}: still locked"
        );
        let mut twin = m.clone();
        let mut a = ShipAction::IDLE;
        a.throttle[0] = THROTTLE_INCREASE;
        twin.set_action(0, a);
        assert_eq!(m.state_hash(), twin.state_hash());
        for _ in 0..=d {
            m.step(&cat);
            twin.step(&cat);
        }
        assert_ne!(m.state_hash(), twin.state_hash(), "d {d}");
        assert_eq!(twin.ships[0].thrust_level[0], RAMP_STEP);
    }
}
