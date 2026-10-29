//! WP7 acceptance (SIM_SPEC §11, §14): thruster allocator against sim.js, and the
//! fighter, strafer and gunship pilots. Uses `Match::step_motion` (stages 3–5) because
//! weapons and the full step land in other packages; turret slew (stage 6) is
//! emulated here where a test needs it.
//!
//! The "scripted 1v1 ends in a kill for 20/20 seeds" acceptance test runs the full
//! `Match::step` and lives in `tests/step.rs`.

mod common;

use common::{FIGHTER, GUNSHIP, STRAFER, new_present_match, test_catalogue};
use sim::DT;
use sim::actions::{ShipAction, THROTTLE_DECREASE, THROTTLE_HOLD, THROTTLE_INCREASE};
use sim::data::Catalogue;
use sim::math::{PI, Vec2, clamp, wrap_angle};
use sim::physics::RAMP_STEP;
use sim::scripted::strafer::{ORBIT_RADIUS, orbit_sign};
use sim::scripted::{act, allocate_thrusters, levels_to_throttle_heads, projected_levels};
use sim::state::{MAX_THRUSTERS, Match};
use sim::turrets::{cooldown_after_tick, cooldown_after_ticks};

// ---------------------------------------------------------------------------
// Allocator: expected outputs worked by hand from sim.js `allocateThrusters`:
//   f̂ = f/|f| (0 if |f| <= 1e-6), along = dot(dir, f̂) * min(|f|, 1),
//   arm = pos.x*dir.y - pos.y*dir.x, score = along + 1.2*sign(arm)*torque,
//   score > 0.6 → target level 1 (JS 1), > 0.25 → 0.5 (JS 0.5), else 0.
//
// Fighter thrusters (pos; dir → arm, sign):
//   0 main (-4.6, 0);  (1, 0)  → -4.6*0 - 0*1      =  0    → 0
//   1 fl   (2.2, 2.3); (0,-1)  →  2.2*-1 - 2.3*0   = -2.2  → -1
//   2 fr   (2.2,-2.3); (0, 1)  →  2.2*1 - (-2.3)*0 =  2.2  → +1
//   3 rl   (-2.8,2.3); (0,-1)  → -2.8*-1           =  2.8  → +1
//   4 rr   (-2.8,-2.3);(0, 1)  → -2.8*1            = -2.8  → -1
// Strafer: main (-4.1,0)(1,0) → 0; fl (2.4,4.7)(0,-1) → -2.4; fr (2.4,-4.7)(0,1) → 2.4;
//   rl (-2.4,4.7)(0,-1) → 2.4; rr (-2.4,-4.7)(0,1) → -2.4.
// Gunship: main.l (-7,2)(1,0) → 0 - 2*1 = -2; main.r (-7,-2)(1,0) → 0 - (-2)*1 = 2;
//   fl (4,4.4)(0,-1) → -4; fr (4,-4.4)(0,1) → 4; rl (-4.5,4.6)(0,-1) → 4.5;
//   rr (-4.5,-4.6)(0,1) → -4.5.
// ---------------------------------------------------------------------------

/// Allocator target levels as 0/1/2 halves, so the cases read like sim.js.
fn alloc(cat: &Catalogue, hull: u16, f: (f32, f32), torque: f32) -> [u8; MAX_THRUSTERS] {
    allocate_thrusters(cat.hull(hull), Vec2::new(f.0, f.1), torque).map(|l| (l * 2.0) as u8)
}

#[test]
fn allocator_fighter_pure_forward() {
    // f = (1,0), τ = 0: main along 1 → 2; RCS dirs ⟂ x → along 0, spin 0 → 0.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, FIGHTER, (1.0, 0.0), 0.0),
        [2, 0, 0, 0, 0, 0, 0, 0]
    );
}

#[test]
fn allocator_fighter_pure_ccw_torque() {
    // f = 0, τ = 1: scores main 0; fl -1.2; fr +1.2; rl +1.2; rr -1.2.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, FIGHTER, (0.0, 0.0), 1.0),
        [0, 0, 2, 2, 0, 0, 0, 0]
    );
}

#[test]
fn allocator_fighter_gentle_cw_torque() {
    // f = 0, τ = -0.3: fl 1.2*-1*-0.3 = 0.36 → 1; fr -0.36 → 0; rl -0.36 → 0; rr 0.36 → 1.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, FIGHTER, (0.0, 0.0), -0.3),
        [0, 1, 0, 0, 1, 0, 0, 0]
    );
}

#[test]
fn allocator_fighter_partial_forward() {
    // f = (0.4,0): f̂ = (1,0), along main = 1 * min(0.4,1) = 0.4 → 1.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, FIGHTER, (0.4, 0.0), 0.0),
        [1, 0, 0, 0, 0, 0, 0, 0]
    );
}

#[test]
fn allocator_fighter_forward_with_torque() {
    // f = (0.2,0), τ = 0.4: main 0.2 → 0; fl -0.48 → 0; fr 0.48 → 1; rl 0.48 → 1; rr -0.48 → 0.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, FIGHTER, (0.2, 0.0), 0.4),
        [0, 0, 1, 1, 0, 0, 0, 0]
    );
}

#[test]
fn allocator_strafer_lateral_port() {
    // f = (0,1), τ = 0: fr, rr push +y → along 1 → 2; fl, rl along -1 → 0; main 0.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, STRAFER, (0.0, 1.0), 0.0),
        [0, 0, 2, 0, 2, 0, 0, 0]
    );
}

#[test]
fn allocator_strafer_diagonal_with_torque() {
    // f = (0.8,-0.6), |f| = 1, τ = 0.1 (spin ±0.12):
    //   main 0.8 → 2; fl 0.6 - 0.12 = 0.48 → 1; fr -0.6 + 0.12 = -0.48 → 0;
    //   rl 0.6 + 0.12 = 0.72 → 2; rr -0.6 - 0.12 → 0.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, STRAFER, (0.8, -0.6), 0.1),
        [2, 1, 0, 2, 0, 0, 0, 0]
    );
}

#[test]
fn allocator_gunship_forward_with_torque() {
    // f = (1,0), τ = 0.6 (spin ±0.72): main.l 1 - 0.72 = 0.28 → 1; main.r 1.72 → 2;
    //   fl -0.72 → 0; fr 0.72 → 2; rl 0.72 → 2; rr -0.72 → 0.
    let cat = test_catalogue();
    assert_eq!(
        alloc(&cat, GUNSHIP, (1.0, 0.0), 0.6),
        [1, 2, 0, 2, 2, 0, 0, 0]
    );
}

#[test]
fn allocator_zero_request_is_all_off() {
    // |f| <= 1e-6 → f̂ = 0; τ = 0 → every score 0.
    let cat = test_catalogue();
    for hull in [FIGHTER, STRAFER, GUNSHIP] {
        assert_eq!(alloc(&cat, hull, (0.0, 0.0), 0.0), [0; MAX_THRUSTERS]);
    }
}

// ---------------------------------------------------------------------------
// Pilots
// ---------------------------------------------------------------------------

/// A 1v1 with ship 0 at `pos`/`heading` and ship 1 at `target`, both at rest.
fn duel(hull0: u16, hull1: u16, pos: Vec2, heading: f32, target: Vec2) -> (Catalogue, Match) {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 3, &[hull0], &[hull1]);
    m.ships[0].pos = pos;
    m.ships[0].heading = heading;
    m.ships[1].pos = target;
    (cat, m)
}

fn bearing_err(m: &Match, from: usize, to: usize) -> f32 {
    let rel = m.ships[to].pos - m.ships[from].pos;
    wrap_angle(rel.angle() - m.ships[from].heading)
}

/// Stage 6 turret slew as SIM_SPEC §5 describes it (WP3 owns the real one).
fn emulate_turret_slew(m: &mut Match, cat: &Catalogue, ship: usize, a: &ShipAction) {
    let hull = cat.hull(m.ships[ship].hull);
    for (j, t) in hull.turrets.iter().enumerate() {
        if t.arc > 0.0 {
            let angle = m.ships[ship].turret_angle[j] + a.slew_sign(j) * t.slew_rate * DT;
            let half = 0.5 * t.arc;
            m.ships[ship].turret_angle[j] = clamp(angle, t.rest - half, t.rest + half);
        }
    }
}

#[test]
fn fighter_facing_away_turns_toward_target() {
    let (cat, mut m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(-200.0, 0.0));
    assert!(bearing_err(&m, 0, 1).abs() > 3.0);
    let mut turned_at = None;
    for tick in 0..90 {
        let a = act(&m, &cat, 0);
        m.set_action(0, a);
        m.step_motion(&cat);
        if bearing_err(&m, 0, 1).abs() < 0.1 {
            turned_at = Some(tick);
            break;
        }
    }
    assert!(
        turned_at.is_some(),
        "still {} rad off",
        bearing_err(&m, 0, 1)
    );
}

#[test]
fn fighter_fires_only_when_aligned_and_in_range() {
    let cat = test_catalogue();
    let gauss_range = cat.weapon(cat.hull(FIGHTER).turrets[0].weapon).range;

    // Dead ahead at 200 m (< 300 m range), target at rest: fire.
    let (_, m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(200.0, 0.0));
    assert_eq!(act(&m, &cat, 0).fire[0], 1);

    // 0.2 rad off the nose (tolerance 0.1): hold fire.
    let (_, m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.2, Vec2::new(200.0, 0.0));
    assert_eq!(act(&m, &cat, 0).fire[0], 0);

    // 0.05 rad off: inside tolerance, fire.
    let (_, m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.05, Vec2::new(200.0, 0.0));
    assert_eq!(act(&m, &cat, 0).fire[0], 1);

    // Aligned but beyond range: hold fire.
    let far = Vec2::new(gauss_range + 20.0, 0.0);
    let (_, m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, far);
    assert_eq!(act(&m, &cat, 0).fire[0], 0);

    // Aligned and in range but the gun is cooling down: hold fire.
    let (_, mut m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(200.0, 0.0));
    m.ships[0].turret_cooldown[0] = 0.05;
    assert_eq!(act(&m, &cat, 0).fire[0], 0);
}

#[test]
fn fighter_leads_a_crossing_target() {
    // Target 200 m ahead crossing at 50 m/s to port: lead time 200/240 s puts the aim
    // point ~41.7 m to port, ~0.2 rad, so the nose-on gun holds fire and the pilot turns CCW.
    let (cat, mut m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(200.0, 0.0));
    m.ships[1].vel = Vec2::new(0.0, 50.0);
    let a = act(&m, &cat, 0);
    assert_eq!(a.fire[0], 0);
    // CCW torque: fr and rl (positive arm) ramp up, fl and rr stay off (hold at 0).
    assert_eq!(
        (a.throttle[2], a.throttle[3]),
        (THROTTLE_INCREASE, THROTTLE_INCREASE)
    );
    assert_eq!(
        (a.throttle[1], a.throttle[4]),
        (THROTTLE_HOLD, THROTTLE_HOLD)
    );
}

#[test]
fn fighter_power_follows_range() {
    let cat = test_catalogue();
    // In gauss range (300 m): weapons (3).
    let (_, m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(200.0, 0.0));
    assert_eq!(act(&m, &cat, 0).power, 3);
    // Between range and 1.5 × range: balanced (0).
    let (_, m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(350.0, 0.0));
    assert_eq!(act(&m, &cat, 0).power, 0);
    // Beyond 1.5 × range: engines (2).
    let (_, m) = duel(
        FIGHTER,
        FIGHTER,
        Vec2::new(-200.0, 0.0),
        0.0,
        Vec2::new(300.0, 0.0),
    );
    assert_eq!(act(&m, &cat, 0).power, 2);
}

#[test]
fn shielded_ship_under_fire_with_low_shield_powers_shields() {
    let (cat, mut m) = duel(STRAFER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(100.0, 0.0));
    m.tick = 100;
    m.ships[0].last_hit_tick = 95;
    m.ships[0].shield = 5.0; // 5/40 < 0.3
    assert_eq!(act(&m, &cat, 0).power, 1);
    // Badly hurt as well: break off (shields and engines).
    m.ships[0].hp = 20.0; // 20/70 < 0.45
    assert_eq!(act(&m, &cat, 0).power, 4);
}

#[test]
fn ship_near_arena_edge_turns_for_centre() {
    // Past 0.85 R (382.5 m of 450) heading outward, target further out: full forward
    // thrust request, and the heading goal is the centre (behind it).
    let (cat, mut m) = duel(
        FIGHTER,
        FIGHTER,
        Vec2::new(400.0, 0.0),
        0.0,
        Vec2::new(430.0, 0.0),
    );
    let a = act(&m, &cat, 0);
    assert_eq!(a.throttle[0], THROTTLE_INCREASE);
    for _ in 0..90 {
        let a = act(&m, &cat, 0);
        m.set_action(0, a);
        m.step_motion(&cat);
    }
    let to_centre = wrap_angle((-m.ships[0].pos).angle() - m.ships[0].heading);
    assert!(to_centre.abs() < 0.5, "heading error to centre {to_centre}");
}

#[test]
fn strafer_orbits_target_near_120m() {
    // Strafer in slot 0 (orbit sign +1) 120 m east of an idle fighter at the origin.
    let (cat, mut m) = duel(
        STRAFER,
        FIGHTER,
        Vec2::new(ORBIT_RADIUS, 0.0),
        PI,
        Vec2::ZERO,
    );
    assert_eq!(orbit_sign(&m.ships[0]), 1.0);
    let start_bearing = m.ships[0].pos.angle();
    let mut swept = 0.0f32;
    let mut last = start_bearing;
    for tick in 0..300 {
        let a = act(&m, &cat, 0);
        m.set_action(0, a);
        m.step_motion(&cat);
        let rel = m.ships[0].pos - m.ships[1].pos;
        let dist = rel.length();
        if tick > 30 {
            assert!((80.0..160.0).contains(&dist), "tick {tick}: dist {dist}");
        }
        let b = rel.angle();
        swept += wrap_angle(b - last);
        last = b;
    }
    // CCW orbit at ~45 m/s on r = 120 m is ~0.37 rad/s, so ~3.7 rad in 10 s.
    assert!(swept > 1.5, "swept only {swept} rad");
    // Nose stays on the target (fixed laser).
    assert!(bearing_err(&m, 0, 1).abs() < 0.3);
}

#[test]
fn strafer_orbit_sign_follows_slot_parity() {
    let cat = test_catalogue();
    let m = new_present_match(&cat, 1, &[STRAFER, STRAFER], &[FIGHTER]);
    assert_eq!(orbit_sign(&m.ships[0]), 1.0);
    assert_eq!(orbit_sign(&m.ships[1]), -1.0);
}

#[test]
fn gunship_broadside_turret_slews_onto_target_and_fires() {
    // Gunship heading +x at the origin, fighter at rest 150 m away on the port quarter
    // (bearing 120°). The port gauss (rest 90°, arc 220°) turns CCW toward it.
    let target = Vec2::from_angle(120f32.to_radians()) * 150.0;
    let (cat, mut m) = duel(GUNSHIP, FIGHTER, Vec2::ZERO, 0.0, target);
    let a = act(&m, &cat, 0);
    assert_eq!(a.slew[1], 0, "port turret should slew CCW");
    let mut fired = false;
    for _ in 0..60 {
        // Hold the hull still so only the turret moves.
        let a = act(&m, &cat, 0);
        emulate_turret_slew(&mut m, &cat, 0, &a);
        if a.fire[1] == 1 {
            fired = true;
            break;
        }
    }
    assert!(fired, "port turret never fired");
    let s = &m.ships[0];
    let muzzle = s.to_world(cat.hull(GUNSHIP).turrets[1].pos);
    let aim = wrap_angle((target - muzzle).angle() - s.heading);
    assert!(wrap_angle(aim - s.turret_angle[1]).abs() < 0.06);
}

#[test]
fn gunship_turns_broadside_within_standoff() {
    let (cat, mut m) = duel(GUNSHIP, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(150.0, 0.0));
    for _ in 0..600 {
        let a = act(&m, &cat, 0);
        m.set_action(0, a);
        m.step_motion(&cat);
        m.ships[1].pos = m.ships[0].pos + Vec2::new(150.0, 0.0);
    }
    // Target on the starboard beam: relative bearing -90°.
    let err = bearing_err(&m, 0, 1);
    assert!((err + 0.5 * PI).abs() < 0.2, "relative bearing {err}");
}

#[test]
fn inactive_ship_or_no_enemy_is_idle() {
    let (cat, mut m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(200.0, 0.0));
    m.ships[0].present = false;
    assert_eq!(act(&m, &cat, 0), ShipAction::IDLE);
    m.ships[0].present = true;
    m.ships[0].alive = false;
    assert_eq!(act(&m, &cat, 0), ShipAction::IDLE);
    m.ships[0].alive = true;
    // Enemy dead or not yet arrived: nothing to fight.
    m.ships[1].alive = false;
    assert_eq!(act(&m, &cat, 0), ShipAction::IDLE);
    m.ships[1].alive = true;
    m.ships[1].present = false;
    assert_eq!(act(&m, &cat, 0), ShipAction::IDLE);
}

#[test]
fn unknown_role_is_idle() {
    let mut cat = test_catalogue();
    cat.hulls[FIGHTER as usize].role = "tug".to_string();
    let m = new_present_match(&cat, 1, &[FIGHTER], &[GUNSHIP]);
    assert_eq!(act(&m, &cat, 0), ShipAction::IDLE);
}

#[test]
fn allies_are_not_targets() {
    // Two fighters on team 0, the only enemy far behind ship 0: ship 0 must not
    // treat its wingman dead ahead as a target.
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 1, &[FIGHTER, FIGHTER], &[FIGHTER]);
    m.ships[0].pos = Vec2::ZERO;
    m.ships[0].heading = 0.0;
    m.ships[1].pos = Vec2::new(100.0, 0.0);
    m.ships[2].pos = Vec2::new(-250.0, 0.0);
    assert_eq!(act(&m, &cat, 0).fire[0], 0);
}

#[test]
fn same_state_gives_same_action() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 9, &[FIGHTER, STRAFER], &[GUNSHIP, FIGHTER]);
    for _ in 0..120 {
        let mut acts = [ShipAction::IDLE; 4];
        for (i, a) in acts.iter_mut().enumerate() {
            *a = act(&m, &cat, i as u8);
        }
        let twin = m.clone();
        for (i, a) in acts.iter().enumerate() {
            assert_eq!(act(&twin, &cat, i as u8), *a);
            assert_eq!(act(&m, &cat, i as u8), *a);
            m.set_action(i as u8, *a);
        }
        m.step_motion(&cat);
    }
}

// ---------------------------------------------------------------------------
// v2 (WP11): rate heads, projected levels, acting through the delay
// ---------------------------------------------------------------------------

#[test]
fn levels_to_throttle_heads_holds_within_half_a_step() {
    let cat = test_catalogue();
    let hull = cat.hull(FIGHTER);
    let band = 0.5 * RAMP_STEP;
    let target = [0.5; MAX_THRUSTERS];
    let heads = |level: f32| levels_to_throttle_heads(hull, &[level; MAX_THRUSTERS], &target);
    assert_eq!(heads(0.5)[0], THROTTLE_HOLD);
    assert_eq!(heads(0.5 + 0.99 * band)[0], THROTTLE_HOLD);
    assert_eq!(heads(0.5 - 0.99 * band)[0], THROTTLE_HOLD);
    assert_eq!(heads(0.5 + 1.01 * band)[0], THROTTLE_DECREASE);
    assert_eq!(heads(0.5 - 1.01 * band)[0], THROTTLE_INCREASE);
    assert_eq!(heads(0.0)[0], THROTTLE_INCREASE);
    assert_eq!(heads(1.0)[0], THROTTLE_DECREASE);
    // Slots beyond the fighter's five thrusters always hold.
    assert_eq!(&heads(0.0)[5..], &[THROTTLE_HOLD; 3]);
    // A ramp driven by these heads settles on the target and stays there.
    let mut level = 0.0;
    for _ in 0..12 {
        let h = levels_to_throttle_heads(hull, &[level; MAX_THRUSTERS], &target)[0];
        level = sim::physics::ramp_level(level, h);
    }
    assert!((level - 0.5).abs() <= band, "settled at {level}");
}

#[test]
fn projected_levels_apply_the_queue_and_the_lock() {
    let cat = test_catalogue();
    let hull = cat.hull(FIGHTER);
    let mut m = new_present_match(&cat, 1, &[FIGHTER], &[FIGHTER]);
    let s = &mut m.ships[0];
    s.reaction_ticks = 3;
    s.thrust_level[0] = 0.5;
    s.thrust_level[1] = 0.5;
    let mut up = ShipAction::IDLE;
    up.throttle[0] = THROTTLE_INCREASE;
    s.queue[0] = up;
    s.queue[1] = up;
    s.queue[2] = ShipAction::IDLE;
    let p = projected_levels(s, hull, 10);
    assert!((p[0] - (0.5 + 2.0 * RAMP_STEP)).abs() < 1e-6, "{p:?}");
    assert_eq!(p[1], 0.5);
    // Queued entries that apply inside the control lock ramp down instead.
    s.control_lock_until = 12; // ticks 11 locked; 12 and 13 not
    let p = projected_levels(s, hull, 10);
    assert!((p[0] - (0.5 - RAMP_STEP + RAMP_STEP)).abs() < 1e-6, "{p:?}");
    assert!((p[1] - (0.5 - RAMP_STEP)).abs() < 1e-6, "{p:?}");
    // No delay: the current levels.
    s.reaction_ticks = 0;
    assert_eq!(projected_levels(s, hull, 10), s.thrust_level);
}

#[test]
fn cooldown_after_ticks_matches_repeated_ticks() {
    for (c, p_w) in [(0.2, 1.0), (0.05, 1.48), (0.16, 0.2), (0.0, 1.0)] {
        let mut want = c;
        for n in 0..8 {
            assert_eq!(
                cooldown_after_ticks(c, p_w, n),
                want,
                "c {c} p_w {p_w} n {n}"
            );
            want = cooldown_after_tick(want, p_w);
        }
    }
}

#[test]
fn fighter_with_delay_fires_for_the_application_tick() {
    // Cooling down now, but ready by the tick the action applies (d + 1 = 3 ticks).
    let cat = test_catalogue();
    let (_, mut m) = duel(FIGHTER, FIGHTER, Vec2::ZERO, 0.0, Vec2::new(200.0, 0.0));
    m.ships[0].reaction_ticks = 2;
    let per_tick = 0.65 * DT;
    m.ships[0].turret_cooldown[0] = 2.5 * per_tick;
    assert_eq!(act(&m, &cat, 0).fire[0], 1);
    m.ships[0].turret_cooldown[0] = 3.5 * per_tick;
    assert_eq!(act(&m, &cat, 0).fire[0], 0);
    // Spinning so that the nose will be off target by the application tick: hold fire.
    m.ships[0].turret_cooldown[0] = 0.0;
    m.ships[0].omega = 1.5; // 3 ticks * 1.5 rad/s = 0.15 rad > 0.1 tolerance
    assert_eq!(act(&m, &cat, 0).fire[0], 0);
    m.ships[0].reaction_ticks = 0; // 1 tick: 0.05 rad, inside tolerance
    assert_eq!(act(&m, &cat, 0).fire[0], 1);
}
