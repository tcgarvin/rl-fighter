//! WP2 acceptance (SIM_SPEC §14): thrusters, drag, soft cap, power, actions, setup,
//! and same-seed hash equality. Uses the temporary `Match::step_physics_only`.

mod common;

use common::{FIGHTER, GUNSHIP, STRAFER, catalogue_with_static, new_match, test_catalogue};
use sim::DT;
use sim::actions::{ACTION_WIDTH, ShipAction, act_mask, fixed_turret, thruster_mask, turret_mask};
use sim::data::Catalogue;
use sim::math::PI;
use sim::physics::{ANGULAR_DRAG, LINEAR_DRAG};
use sim::power::{self, POWER_TARGETS, multiplier, two_way_target};
use sim::setup::{MatchConfig, SetupError};
use sim::state::{Attach, Match, MatchPhase, NONE};

const EPS: f32 = 1e-5;

fn close(a: f32, b: f32, tol: f32) -> bool {
    (a - b).abs() <= tol
}

/// Fighter 1v1 with ship 0 driven by `throttle` (other heads idle).
fn fighter_with_throttle(throttle: &[u8]) -> (Catalogue, Match) {
    let cat = test_catalogue();
    let mut m = new_match(&cat, 1, &[FIGHTER], &[FIGHTER]);
    let mut a = ShipAction::IDLE;
    a.throttle[..throttle.len()].copy_from_slice(throttle);
    m.set_action(0, a);
    (cat, m)
}

#[test]
fn main_thruster_accelerates_forward() {
    let (cat, mut m) = fighter_with_throttle(&[2]);
    let start = m.ships[0].pos;
    m.step_physics_only(&cat);
    let s = &m.ships[0];
    // 900 N / 10 kg at even power (P_e = 1), one tick, then drag.
    let want = 900.0 / 10.0 * DT * LINEAR_DRAG;
    assert!(close(s.vel.x, want, EPS), "vel.x {} want {want}", s.vel.x);
    assert_eq!(s.vel.y, 0.0);
    assert_eq!(s.omega, 0.0, "main thruster is on the axis: no torque");
    assert!(s.pos.x > start.x);
    assert_eq!(s.heading, 0.0);
}

#[test]
fn half_throttle_gives_half_force() {
    let (cat, mut full) = fighter_with_throttle(&[2]);
    let (_, mut half) = fighter_with_throttle(&[1]);
    full.step_physics_only(&cat);
    half.step_physics_only(&cat);
    assert!(close(half.ships[0].vel.x * 2.0, full.ships[0].vel.x, EPS));
}

#[test]
fn thrust_follows_heading() {
    let (cat, mut m) = fighter_with_throttle(&[2]);
    m.ships[0].heading = 0.5 * PI;
    m.step_physics_only(&cat);
    let s = &m.ships[0];
    assert!(s.vel.y > 2.9, "vel {:?}", s.vel);
    assert!(s.vel.x.abs() < 1e-4, "vel {:?}", s.vel);
}

#[test]
fn engine_power_scales_thrust() {
    // Fighter is two-way: target 2 = engines 0.75 → P_e = 0.2 + 0.8*2*0.75 = 1.4.
    let (cat, mut m) = fighter_with_throttle(&[2]);
    m.ships[0].power = two_way_target(2);
    m.ships[0].power_target = two_way_target(2);
    let mut a = m.pending[0];
    a.power = 2;
    m.set_action(0, a);
    m.step_physics_only(&cat);
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
        cw.step_physics_only(&cat);
        ccw.step_physics_only(&cat);
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
    // First-tick torque: |cross(fl.pos, fl.F)| + |cross(rr.pos, rr.F)| = 352 + 448.
    let (cat, mut one) = fighter_with_throttle(&[0, 2, 0, 0, 2]);
    one.step_physics_only(&cat);
    let want = -800.0 / 55.0 * DT * ANGULAR_DRAG;
    assert!(close(one.ships[0].omega, want, EPS));
}

#[test]
fn drag_settles_motion() {
    let (cat, mut m) = fighter_with_throttle(&[]);
    m.ships[0].vel = sim::Vec2::new(20.0, -10.0);
    m.ships[0].omega = 2.0;
    let v0 = m.ships[0].vel.length();
    m.step_physics_only(&cat);
    assert!(close(m.ships[0].vel.length(), v0 * LINEAR_DRAG, 1e-4));
    assert!(close(m.ships[0].omega, 2.0 * ANGULAR_DRAG, EPS));
    for _ in 0..1500 {
        m.step_physics_only(&cat);
    }
    let s = &m.ships[0];
    assert!(s.vel.length() < 0.01 * v0, "speed {}", s.vel.length());
    assert!(s.omega.abs() < 1e-6, "omega {}", s.omega);
}

#[test]
fn soft_cap_limits_speed_under_full_thrust() {
    let (cat, mut m) = fighter_with_throttle(&[2]);
    for _ in 0..300 {
        m.step_physics_only(&cat);
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
        m.step_physics_only(&cat);
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
        m.step_physics_only(&cat);
    }
    let speed = m.ships[0].vel.length();
    assert!(close(speed, 69.6, 0.1), "speed {speed}");
}

#[test]
fn static_hull_is_not_integrated() {
    let (cat, station) = catalogue_with_static();
    let mut m = new_match(&cat, 3, &[station], &[FIGHTER]);
    m.ships[0].vel = sim::Vec2::new(5.0, 0.0);
    let mut a = ShipAction::IDLE;
    a.fire[0] = 1;
    a.power = 3;
    m.set_action(0, a);
    let before = m.ships[0].clone();
    for _ in 0..30 {
        m.step_physics_only(&cat);
    }
    let s = &m.ships[0];
    assert_eq!(s.pos, before.pos);
    assert_eq!(s.vel, before.vel);
    assert_eq!(s.heading, before.heading);
    assert_eq!(m.pending[0].fire[0], 0, "static hulls never fire");
    assert_eq!(
        s.power_target, POWER_TARGETS[3],
        "power target still applies"
    );
}

#[test]
fn control_lock_forces_throttle_off() {
    let (cat, mut m) = fighter_with_throttle(&[2, 2]);
    m.ships[0].control_lock_until = 5;
    let mut a = m.pending[0];
    a.fire[0] = 1;
    m.set_action(0, a);
    assert!(!act_mask(&m.ships[0], 1));
    m.step_physics_only(&cat);
    assert_eq!(m.ships[0].throttle, [0; 8]);
    assert_eq!(m.ships[0].vel.x, 0.0);
    assert_eq!(m.pending[0].fire[0], 0);
    assert!(act_mask(&m.ships[0], 5));
}

#[test]
fn power_slew_reaches_target_in_gap_over_rate() {
    let cat = test_catalogue();
    let mut m = new_match(&cat, 1, &[STRAFER], &[FIGHTER]);
    let mut a = ShipAction::IDLE;
    a.power = 2; // (0.2, 0.6, 0.2)
    m.set_action(0, a);
    let target = POWER_TARGETS[2];
    let gap = target[1] - 1.0 / 3.0;
    let ticks = (gap / power::POWER_SLEW_RATE / DT).ceil() as u32; // 0.593 s → 18
    for t in 1..=ticks {
        m.step_physics_only(&cat);
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
    m.step_physics_only(&cat);
    assert_eq!(m.ships[0].power, [0.0, 0.5, 0.5]);
    a.power = 4;
    m.set_action(0, a);
    for _ in 0..60 {
        m.step_physics_only(&cat);
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
    m.step_physics_only(&cat);
    assert_eq!(m.ships[0].throttle, [0; 8]);
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
        assert!(s.alive && s.present);
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
    m.step_physics_only(cat);
}

#[test]
fn same_seed_matches_hash_equal_every_tick() {
    let cat = test_catalogue();
    let fleets: (&[u16], &[u16]) = (&[FIGHTER, STRAFER], &[GUNSHIP, FIGHTER]);
    let mut a = new_match(&cat, 11, fleets.0, fleets.1);
    let mut b = new_match(&cat, 11, fleets.0, fleets.1);
    let mut other = new_match(&cat, 12, fleets.0, fleets.1);
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
