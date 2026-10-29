//! WP6 / WP13 acceptance (SIM_SPEC §7.2 v2, §14.1): obs layout, body-frame rotation,
//! all-ships ordering, threat-sorted hostile projectiles, thrust levels, pending
//! actions, `lock_left`, absent slots, clamping, dead observer, determinism.
//!
//! Ship state is set explicitly in most tests (positions, headings, present/alive)
//! so they do not depend on arrival placement; the `lock_left` and queue tests step
//! a real match.

mod common;

use common::{FIGHTER, GUNSHIP, STRAFER, new_match, test_catalogue};
use sim::Vec2;
use sim::actions::{SLEW_HOLD, ShipAction, THROTTLE_DECREASE, THROTTLE_HOLD, THROTTLE_INCREASE};
use sim::data::{Catalogue, HullId, WeaponKind};
use sim::math::PI;
use sim::obs::*;
use sim::setup::MatchConfig;
use sim::state::{MAX_PROJECTILES, MAX_REACTION_TICKS, MAX_SHIPS, Match, Projectile};

const EPS: f32 = 1e-5;

/// A match with every ship present, alive, at rest, at `pos[i]` facing `heading[i]`,
/// with the projectile pool empty.
fn placed(cat: &Catalogue, team0: &[HullId], team1: &[HullId], poses: &[(f32, f32, f32)]) -> Match {
    let mut m = new_match(cat, 3, team0, team1);
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

fn obs(m: &Match, cat: &Catalogue, ship: u8) -> [f32; OBS_DIM] {
    let mut out = [f32::NAN; OBS_DIM];
    m.write_obs(cat, ship, &mut out);
    out
}

fn ship_rec(o: &[f32], k: usize) -> &[f32] {
    &o[SHIPS_OFF + k * SHIP_W..SHIPS_OFF + (k + 1) * SHIP_W]
}

fn proj_rec(o: &[f32], k: usize) -> &[f32] {
    &o[PROJ_OFF + k * PROJ_W..PROJ_OFF + (k + 1) * PROJ_W]
}

fn pending_rec(o: &[f32], k: usize) -> &[f32] {
    &o[PENDING_OFF + k * PENDING_W..PENDING_OFF + (k + 1) * PENDING_W]
}

fn thruster_rec(o: &[f32], j: usize) -> &[f32] {
    &o[THRUSTERS_OFF + j * THRUSTER_W..THRUSTERS_OFF + (j + 1) * THRUSTER_W]
}

fn bullet(team: u8, pos: (f32, f32), vel: (f32, f32), damage: f32) -> Projectile {
    Projectile {
        alive: true,
        kind: WeaponKind::Bullet,
        team,
        owner: 0,
        pos: Vec2::new(pos.0, pos.1),
        vel: Vec2::new(vel.0, vel.1),
        speed: 240.0,
        damage,
        life_ticks: 10,
        ..Projectile::DEAD
    }
}

#[test]
fn block_offsets_match_spec() {
    assert_eq!(OBS_DIM, 385);
    assert_eq!((SELF_OFF, SELF_WIDTH), (0, 21));
    assert_eq!((THRUSTERS_OFF, THRUSTERS_WIDTH), (21, 56));
    assert_eq!((TURRETS_OFF, TURRETS_WIDTH), (77, 60));
    assert_eq!((SHIPS_OFF, SHIPS_WIDTH), (137, 84));
    assert_eq!((PROJ_OFF, PROJ_WIDTH), (221, 64));
    assert_eq!((PENDING_OFF, PENDING_WIDTH), (285, 88));
    assert_eq!((TURRET_ARC_OFF, TURRET_ARC_WIDTH), (373, 6));
    assert_eq!((TURRET_RANGE_OFF, TURRET_RANGE_WIDTH), (379, 6));
    assert_eq!(
        (SELF_W, THRUSTER_W, TURRET_W, SHIP_W, PROJ_W, PENDING_W),
        (21, 7, 10, 12, 8, 22)
    );
    assert_eq!(
        (N_NEAR_SHIPS, N_NEAR_PROJ, N_PENDING_SLOTS),
        (MAX_SHIPS - 1, 8, MAX_REACTION_TICKS)
    );
    assert_eq!(
        (
            pending_f::THROTTLE,
            pending_f::SLEW,
            pending_f::FIRE,
            pending_f::POWER
        ),
        (1, 9, 15, 21)
    );
}

#[test]
fn obs_layout_and_slots_are_contiguous_and_cover_obs() {
    let mut next = 0;
    for &(name, off, width) in OBS_LAYOUT {
        assert_eq!(off, next, "block {name} not contiguous");
        assert!(width > 0, "block {name} empty");
        next = off + width;
    }
    assert_eq!(next, OBS_DIM);
    let names: Vec<&str> = OBS_LAYOUT.iter().map(|b| b.0).collect();
    assert_eq!(
        names,
        [
            "self",
            "thrusters",
            "turrets",
            "ships",
            "projectiles",
            "pending",
            "turret_arc",
            "turret_range"
        ]
    );
    let slots: Vec<(&str, usize)> = OBS_SLOTS.to_vec();
    assert_eq!(
        slots,
        [
            ("self", 1),
            ("thrusters", 8),
            ("turrets", 6),
            ("ships", 7),
            ("projectiles", 8),
            ("pending", 4),
            ("turret_arc", 6),
            ("turret_range", 6)
        ]
    );
    for (&(name, _, width), &(slot_name, n)) in OBS_LAYOUT.iter().zip(OBS_SLOTS) {
        assert_eq!(name, slot_name);
        assert_eq!(width % n, 0, "block {name} not a whole number of records");
    }
}

#[test]
fn enemy_dead_ahead_is_on_body_x_axis_for_any_heading() {
    let cat = test_catalogue();
    for &h in &[0.0, 0.3, PI / 2.0, 2.0, PI, -PI / 2.0, -2.7] {
        let dir = Vec2::from_angle(h);
        let enemy = Vec2::new(10.0, -20.0) + dir * 150.0;
        let m = placed(
            &cat,
            &[FIGHTER],
            &[FIGHTER],
            &[(10.0, -20.0, h), (enemy.x, enemy.y, 1.0)],
        );
        let o = obs(&m, &cat, 0);
        let r = ship_rec(&o, 0);
        assert_eq!(r[ship_f::PRESENT], 1.0);
        assert_eq!(r[ship_f::IS_ENEMY], 1.0);
        assert!(r[ship_f::REL_POS_X] > 0.0, "heading {h}: x {}", r[2]);
        assert!((r[ship_f::REL_POS_X] - 150.0 / 450.0).abs() < 1e-4);
        assert!(r[ship_f::REL_POS_Y].abs() < EPS, "heading {h}: y {}", r[3]);
        assert!((r[ship_f::DIST] - 150.0 / 450.0).abs() < 1e-4);
    }
}

#[test]
fn enemy_to_port_has_positive_body_y() {
    let cat = test_catalogue();
    for &h in &[0.0, 1.0, PI, -2.0] {
        // Port = 90 degrees CCW of the heading.
        let port = Vec2::from_angle(h + PI / 2.0) * 50.0;
        let m = placed(
            &cat,
            &[FIGHTER],
            &[FIGHTER],
            &[(0.0, 0.0, h), (port.x, port.y, 0.0)],
        );
        let r = obs(&m, &cat, 0);
        let r = ship_rec(&r, 0);
        assert!(r[ship_f::REL_POS_Y] > 0.0, "heading {h}");
        assert!(r[ship_f::REL_POS_X].abs() < EPS, "heading {h}");
    }
}

#[test]
fn self_velocity_and_centre_are_in_body_frame() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(100.0, 0.0, PI / 2.0), (-100.0, 0.0, 0.0)],
    );
    m.ships[0].vel = Vec2::new(0.0, 50.0); // straight ahead
    let o = obs(&m, &cat, 0);
    assert_eq!(o[self_f::PRESENT], 1.0);
    assert_eq!(o[self_f::LOCK_LEFT], 0.0);
    assert!((o[self_f::FWD_SPEED] - 0.5).abs() < EPS);
    assert!(o[self_f::LAT_SPEED].abs() < EPS);
    assert!((o[self_f::SPEED] - 0.5).abs() < EPS);
    // Centre is to world -x; facing +y, that is to port (+y body).
    assert!(o[self_f::DIR_TO_CENTRE_X].abs() < EPS);
    assert!((o[self_f::DIR_TO_CENTRE_Y] - 1.0).abs() < EPS);
    assert!((o[self_f::ARENA_MARGIN] - 350.0 / 450.0).abs() < EPS);
    assert!((o[self_f::TIME_LEFT] - 1.0).abs() < EPS);
    assert!((o[self_f::HP] - 1.0).abs() < EPS);
    assert_eq!(o[self_f::HAS_SHIELD], 0.0);
    // The common fixture builds matches with reaction_ticks 0.
    assert_eq!(o[self_f::REACTION_TICKS], 0.0);
}

#[test]
fn seven_ship_slots_filled_in_4v4_and_sorted_by_distance() {
    let cat = test_catalogue();
    // Observer slot 0; allies (slots 1-3) at 80, 50, 30; enemies (4-7) at 120, 50, 200, 10.
    let m = placed(
        &cat,
        &[FIGHTER, FIGHTER, STRAFER, GUNSHIP],
        &[FIGHTER, FIGHTER, STRAFER, GUNSHIP],
        &[
            (0.0, 0.0, 0.0),
            (0.0, 80.0, 0.0),
            (50.0, 0.0, 0.0),
            (0.0, -30.0, 0.0),
            (-120.0, 0.0, 0.0),
            (-50.0, 0.0, 0.0),
            (200.0, 0.0, 0.0),
            (0.0, 10.0, 0.0),
        ],
    );
    let o = obs(&m, &cat, 0);
    let d = |k| ship_rec(&o, k)[ship_f::DIST] * 450.0;
    let expected = [10.0, 30.0, 50.0, 50.0, 80.0, 120.0, 200.0];
    for (k, &e) in expected.iter().enumerate() {
        assert_eq!(ship_rec(&o, k)[ship_f::PRESENT], 1.0, "slot {k}");
        assert!((d(k) - e).abs() < 1e-3, "slot {k}: {} vs {e}", d(k));
    }
    // Tie at 50 m: slot 2 (ahead, +x) before slot 5 (behind, -x).
    assert!(ship_rec(&o, 2)[ship_f::REL_POS_X] > 0.0);
    assert!(ship_rec(&o, 3)[ship_f::REL_POS_X] < 0.0);
    // Sorted: enemy 10, ally 30, ally 50, enemy 50, ally 80, enemy 120, enemy 200.
    let enemy: Vec<f32> = (0..N_NEAR_SHIPS)
        .map(|k| ship_rec(&o, k)[ship_f::IS_ENEMY])
        .collect();
    assert_eq!(enemy, [1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 1.0]);
}

#[test]
fn ally_flagged_and_inactive_ships_skipped() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, STRAFER],
        &[FIGHTER, GUNSHIP],
        &[
            (0.0, 0.0, 0.0),
            (10.0, 0.0, 0.0),
            (20.0, 0.0, 0.0),
            (30.0, 0.0, 0.0),
        ],
    );
    m.ships[2].alive = false;
    m.ships[3].present = false;
    let o = obs(&m, &cat, 0);
    let r = ship_rec(&o, 0);
    assert_eq!(r[ship_f::PRESENT], 1.0);
    assert_eq!(r[ship_f::IS_ENEMY], 0.0);
    assert!((r[ship_f::SHIELD] - 1.0).abs() < EPS); // strafer, full shield
    for k in 1..N_NEAR_SHIPS {
        assert!(ship_rec(&o, k).iter().all(|&x| x == 0.0), "slot {k}");
    }
}

/// Hand-computed §7.2 threat parts for an observer at rest at the origin.
fn hand_threat(pos: (f32, f32), vel: (f32, f32)) -> (f32, f32, f32) {
    let (rx, ry, vx, vy) = (pos.0, pos.1, vel.0, vel.1);
    let v2 = vx * vx + vy * vy;
    let t = if v2 == 0.0 {
        0.0
    } else {
        (-(rx * vx + ry * vy) / v2).clamp(0.0, T_H)
    };
    let (mx, my) = (rx + vx * t, ry + vy * t);
    let miss = (mx * mx + my * my).sqrt();
    (t, miss, miss + L * t)
}

#[test]
fn projectiles_sorted_by_threat_score_and_own_shots_absent() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER, FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (0.0, 100.0, 0.0), (300.0, 0.0, PI)],
    );
    // Hostile shots, in reverse threat order in the pool:
    //   receding:   50 m ahead, flying away        t_ca 0,   miss 50, score 50
    //   passing:    crosses 30 m to port            t_ca 0.2, miss 30, score 34
    //   converging: nearly head-on, 5 m miss        t_ca 0.5, miss 5,  score 15
    //   far:        1000 m out, closing; t_ca clamps to T_H        score 640
    let receding = ((50.0, 0.0), (200.0, 0.0));
    let passing = ((-40.0, 30.0), (200.0, 0.0));
    let converging = ((100.0, 5.0), (-200.0, 0.0));
    let far = ((1000.0, 0.0), (-200.0, 0.0));
    m.projectiles[3] = bullet(1, receding.0, receding.1, 6.0);
    m.projectiles[7] = bullet(1, passing.0, passing.1, 6.0);
    m.projectiles[11] = bullet(1, converging.0, converging.1, 55.0);
    m.projectiles[12] = bullet(1, far.0, far.1, 6.0);
    // Own and allied shots right on top of the observer are not listed.
    m.projectiles[1] = bullet(0, (1.0, 0.0), (-240.0, 0.0), 6.0);
    m.projectiles[2] = Projectile {
        owner: 1,
        ..bullet(0, (0.0, 2.0), (0.0, -240.0), 6.0)
    };
    // A dead hostile entry is ignored.
    m.projectiles[4] = Projectile {
        alive: false,
        ..bullet(1, (2.0, 0.0), (-200.0, 0.0), 6.0)
    };
    let o = obs(&m, &cat, 0);
    let staged = [converging, passing, receding, far];
    let mut last_score = f32::NEG_INFINITY;
    for (k, &(pos, vel)) in staged.iter().enumerate() {
        let r = proj_rec(&o, k);
        let (t, miss, score) = hand_threat(pos, vel);
        assert!(score > last_score, "hand scores must be increasing");
        last_score = score;
        assert_eq!(r[proj_f::PRESENT], 1.0, "slot {k}");
        assert!(
            (r[proj_f::REL_POS_X] * 450.0 - pos.0).abs() < 1e-2,
            "slot {k}"
        );
        assert!(
            (r[proj_f::REL_POS_Y] * 450.0 - pos.1).abs() < 1e-3,
            "slot {k}"
        );
        assert!((r[proj_f::REL_VEL_X] * VS - vel.0).abs() < 1e-3, "slot {k}");
        // t_ca / miss features agree with the hand-computed score.
        let (t_obs, miss_obs) = (r[proj_f::T_CA] * T_H, r[proj_f::MISS] * L);
        assert!((t_obs - t).abs() < 1e-5, "slot {k}: t_ca {t_obs} vs {t}");
        let miss_feat = miss.min(OBS_CLIP * L);
        assert!(
            (miss_obs - miss_feat).abs() < 1e-3,
            "slot {k}: {miss_obs} vs {miss}"
        );
        if miss < OBS_CLIP * L {
            assert!((miss_obs + L * t_obs - score).abs() < 1e-3, "slot {k}");
        }
    }
    let (t, miss, score) = hand_threat(converging.0, converging.1);
    assert_eq!((t, miss, score), (0.5, 5.0, 15.0));
    assert_eq!(proj_rec(&o, 3)[proj_f::T_CA], 1.0); // clamped at T_H
    assert!((proj_rec(&o, 0)[proj_f::DAMAGE] - 55.0 / 60.0).abs() < EPS);
    for k in staged.len()..N_NEAR_PROJ {
        assert!(proj_rec(&o, k).iter().all(|&x| x == 0.0), "slot {k}");
    }

    // The threat() helper matches the hand computation.
    let p = &m.projectiles[7];
    let th = threat(&m.ships[0], p);
    let (t, miss, score) = hand_threat(passing.0, passing.1);
    assert!((th.t_ca - t).abs() < 1e-6 && (th.miss - miss).abs() < 1e-4);
    assert!((th.score - score).abs() < 1e-4);
}

#[test]
fn threat_uses_relative_velocity_and_breaks_ties_by_pool_index() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    // Observer flying +x at 100 m/s; a shot keeping pace beside it is static
    // relative to it (t_ca 0, miss 40), so it ties with a stationary shot 40 m away
    // that the observer flies straight away from (t_ca 0 too).
    m.ships[0].vel = Vec2::new(100.0, 0.0);
    m.projectiles[9] = bullet(1, (0.0, 40.0), (100.0, 0.0), 6.0);
    m.projectiles[20] = bullet(1, (-40.0, 0.0), (0.0, 0.0), 6.0);
    let o = obs(&m, &cat, 0);
    let first = proj_rec(&o, 0);
    let second = proj_rec(&o, 1);
    assert!((first[proj_f::REL_POS_Y] * 450.0 - 40.0).abs() < 1e-3);
    assert_eq!(first[proj_f::REL_VEL_X], 0.0);
    assert!((second[proj_f::REL_POS_X] * 450.0 + 40.0).abs() < 1e-3);
    assert!((second[proj_f::REL_VEL_X] + 1.0).abs() < EPS);
    assert_eq!(first[proj_f::T_CA], 0.0);
    assert!((first[proj_f::MISS] - second[proj_f::MISS]).abs() < EPS);
}

#[test]
fn more_than_eight_hostile_shots_keep_the_eight_most_threatening() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    // Twelve static shots at 10, 20, ..., 120 m, in descending pool order.
    for i in 0..12 {
        let dist = 10.0 * (12 - i) as f32;
        m.projectiles[i] = bullet(1, (0.0, dist), (0.0, 0.0), 6.0);
    }
    let o = obs(&m, &cat, 0);
    for k in 0..N_NEAR_PROJ {
        let y = proj_rec(&o, k)[proj_f::REL_POS_Y] * 450.0;
        assert!((y - 10.0 * (k + 1) as f32).abs() < 1e-3, "slot {k}: {y}");
    }
}

#[test]
fn thrust_levels_appear_in_thruster_records() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    let levels = [1.0, 0.5, 0.0, 1.0 / 6.0, 0.25];
    m.ships[0].thrust_level[..5].copy_from_slice(&levels);
    let o = obs(&m, &cat, 0);
    for (j, &lvl) in levels.iter().enumerate() {
        assert_eq!(thruster_rec(&o, j)[thruster_f::LEVEL], lvl, "thruster {j}");
    }
    for j in levels.len()..N_THRUSTER_SLOTS {
        assert!(thruster_rec(&o, j).iter().all(|&x| x == 0.0));
    }
}

#[test]
fn pending_slots_encode_the_queue_and_slots_past_d_are_zero() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    let mut a = ShipAction::IDLE;
    a.throttle[0] = THROTTLE_INCREASE;
    a.throttle[1] = THROTTLE_DECREASE;
    a.throttle[2] = THROTTLE_HOLD;
    a.slew[0] = 0; // left → +1
    a.slew[1] = 2; // right → -1
    a.slew[2] = SLEW_HOLD;
    a.fire[0] = 1;
    a.power = 3;
    for d in 0..=MAX_REACTION_TICKS {
        let ship = &mut m.ships[0];
        ship.reaction_ticks = d as u8;
        ship.queue = [ShipAction::IDLE; MAX_REACTION_TICKS];
        if d >= 2 {
            ship.queue[1] = a;
        }
        let o = obs(&m, &cat, 0);
        assert_eq!(
            o[self_f::REACTION_TICKS],
            d as f32 / MAX_REACTION_TICKS as f32
        );
        for k in 0..N_PENDING_SLOTS {
            let r = pending_rec(&o, k);
            if k >= d {
                assert!(r.iter().all(|&x| x == 0.0), "d {d} slot {k}");
                continue;
            }
            assert_eq!(r[pending_f::PRESENT], 1.0, "d {d} slot {k}");
            let q = m.ships[0].queue[k];
            for i in 0..8 {
                let e = q.throttle[i] as f32 - 1.0;
                assert_eq!(r[pending_f::THROTTLE + i], e, "d {d} slot {k} thr {i}");
            }
            for j in 0..6 {
                assert_eq!(r[pending_f::SLEW + j], q.slew_sign(j));
                assert_eq!(r[pending_f::FIRE + j], q.fire[j] as f32);
            }
            assert_eq!(r[pending_f::POWER], q.power as f32 / 6.0);
        }
        if d >= 2 {
            let r = pending_rec(&o, 1);
            assert_eq!(
                &r[pending_f::THROTTLE..pending_f::THROTTLE + 3],
                [1.0, -1.0, 0.0]
            );
            assert_eq!(&r[pending_f::SLEW..pending_f::SLEW + 3], [1.0, -1.0, 0.0]);
            assert_eq!(r[pending_f::FIRE], 1.0);
            assert_eq!(r[pending_f::POWER], 0.5);
            // A queued IDLE is present with every head at 0.
            let idle = pending_rec(&o, 0);
            assert_eq!(idle[pending_f::PRESENT], 1.0);
            assert!(idle[1..].iter().all(|&x| x == 0.0));
        }
    }
}

/// A fighter duel with reaction delay `d`, stepped with `IDLE` until ship 0 arrives.
fn arrived_match(cat: &Catalogue, d: u8) -> Match {
    let cfg = MatchConfig {
        seed: 5,
        reaction_ticks: d,
        fleets: [vec![FIGHTER], vec![FIGHTER]],
        ..MatchConfig::default()
    };
    let mut m = Match::new(cat, &cfg).expect("match setup");
    while !m.ships[0].present {
        m.step(cat);
        assert!(m.tick < 200, "ship 0 never arrived");
    }
    m
}

#[test]
fn lock_left_counts_down_from_21_to_0() {
    let cat = test_catalogue();
    let mut m = arrived_match(&cat, 2);
    let mut seen = Vec::new();
    for _ in 0..25 {
        seen.push(obs(&m, &cat, 0)[self_f::LOCK_LEFT]);
        m.step(&cat);
    }
    for (i, &v) in seen.iter().enumerate() {
        let expected = 21usize.saturating_sub(i) as f32 / 21.0;
        assert!((v - expected).abs() < EPS, "tick +{i}: {v} vs {expected}");
    }
    assert_eq!(seen[0], 1.0);
    assert_eq!(seen[21], 0.0);
}

#[test]
fn stepped_queue_shows_up_in_pending_slots() {
    let cat = test_catalogue();
    let mut m = arrived_match(&cat, 2);
    // Step past the lock so chosen actions enter the queue.
    while !m.act_mask(0) {
        m.step(&cat);
    }
    let mut a = ShipAction::IDLE;
    a.throttle[0] = THROTTLE_INCREASE;
    a.fire[0] = 1;
    m.set_action(0, a);
    m.step(&cat);
    m.set_action(0, ShipAction::IDLE);
    // Chosen from the previous obs: now the last queue slot (d - 1 = 1).
    let o = obs(&m, &cat, 0);
    assert_eq!(m.ships[0].queue[1], a);
    assert_eq!(pending_rec(&o, 1)[pending_f::THROTTLE], 1.0);
    assert_eq!(pending_rec(&o, 1)[pending_f::FIRE], 1.0);
    assert_eq!(pending_rec(&o, 0)[pending_f::THROTTLE], 0.0);
    m.step(&cat);
    let o = obs(&m, &cat, 0);
    assert_eq!(pending_rec(&o, 0)[pending_f::THROTTLE], 1.0);
    assert_eq!(pending_rec(&o, 1)[pending_f::THROTTLE], 0.0);
    assert_eq!(thruster_rec(&o, 0)[thruster_f::LEVEL], 0.0);
    m.step(&cat);
    let o = obs(&m, &cat, 0);
    assert_eq!(pending_rec(&o, 0)[pending_f::THROTTLE], 0.0);
    assert!(thruster_rec(&o, 0)[thruster_f::LEVEL] > 0.0);
    for k in 2..N_PENDING_SLOTS {
        assert!(pending_rec(&o, k).iter().all(|&x| x == 0.0));
    }
}

#[test]
fn absent_slots_are_zero() {
    let cat = test_catalogue();
    let m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (100.0, 0.0, PI)],
    );
    let o = obs(&m, &cat, 0);
    let fighter = &cat.hulls[FIGHTER as usize];
    let (nt, nr) = (fighter.thrusters.len(), fighter.turrets.len());
    assert_eq!((nt, nr), (5, 1));
    for j in 0..N_THRUSTER_SLOTS {
        let rec = thruster_rec(&o, j);
        assert_eq!(rec[thruster_f::PRESENT], if j < nt { 1.0 } else { 0.0 });
        if j >= nt {
            assert!(rec.iter().all(|&x| x == 0.0));
        }
    }
    for j in 0..N_TURRET_SLOTS {
        let rec = &o[TURRETS_OFF + j * TURRET_W..TURRETS_OFF + (j + 1) * TURRET_W];
        if j < nr {
            assert_eq!(rec[turret_f::PRESENT], 1.0);
            assert_eq!(rec[turret_f::KIND + WeaponKind::Bullet.index()], 1.0);
            assert!((rec[turret_f::COS_ANGLE] - 1.0).abs() < EPS);
        } else {
            assert!(rec.iter().all(|&x| x == 0.0));
            assert_eq!(o[TURRET_ARC_OFF + j], 0.0);
            assert_eq!(o[TURRET_RANGE_OFF + j], 0.0);
        }
    }
    assert_eq!(o[TURRET_ARC_OFF], 0.0); // fixed nose gun
    let range = cat.weapon(fighter.turrets[0].weapon).range;
    assert!((o[TURRET_RANGE_OFF] - range / 450.0).abs() < EPS);
    for k in 1..N_NEAR_SHIPS {
        assert!(ship_rec(&o, k).iter().all(|&x| x == 0.0));
    }
    for k in 0..N_NEAR_PROJ {
        assert!(proj_rec(&o, k).iter().all(|&x| x == 0.0));
    }
    // d = 0 in the fixture: no pending slots.
    assert!(
        o[PENDING_OFF..PENDING_OFF + PENDING_WIDTH]
            .iter()
            .all(|&x| x == 0.0)
    );
}

#[test]
fn gunship_turret_extras() {
    let cat = test_catalogue();
    let m = placed(
        &cat,
        &[GUNSHIP],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (100.0, 0.0, PI)],
    );
    let o = obs(&m, &cat, 0);
    assert!((o[TURRET_ARC_OFF] - 240.0 / 360.0).abs() < EPS);
    assert!((o[TURRET_ARC_OFF + 1] - 220.0 / 360.0).abs() < EPS);
    assert!((o[TURRET_RANGE_OFF] - 230.0 / 450.0).abs() < EPS);
    let fore = &o[TURRETS_OFF..TURRETS_OFF + TURRET_W];
    assert_eq!(fore[turret_f::KIND + WeaponKind::Flak.index()], 1.0);
    let port = &o[TURRETS_OFF + TURRET_W..TURRETS_OFF + 2 * TURRET_W];
    assert!((port[turret_f::SIN_ANGLE] - 1.0).abs() < EPS); // rest 90 degrees
    assert_eq!(o[self_f::HAS_SHIELD], 1.0);
}

#[test]
fn values_stay_within_clip_under_extreme_states() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[GUNSHIP, STRAFER],
        &[FIGHTER, GUNSHIP],
        &[
            (1.0e7, -1.0e7, 1.0e4),
            (-1.0e7, 3.0e6, -55.0),
            (0.0, 0.0, 0.0),
            (1.0e7, -1.0e7, 2.0),
        ],
    );
    for s in m.ships.iter_mut() {
        s.vel = Vec2::new(1.0e8, -3.0e8);
        s.omega = -1.0e6;
        s.hp = 1.0e9;
        s.shield = -1.0e9;
        s.turret_cooldown = [1.0e6; 6];
        s.control_lock_until = u32::MAX;
        s.reaction_ticks = MAX_REACTION_TICKS as u8;
        s.thrust_level = [1.0; 8];
    }
    m.ships[2].vel = Vec2::new(-1.0e8, 1.0e8);
    m.tick = 1_000_000; // far past the time limit
    m.projectiles[0] = bullet(1, (-1.0e9, 1.0e9), (1.0e9, 1.0e9), 1.0e9);
    m.projectiles[1] = bullet(0, (1.0e9, 0.0), (-1.0e9, 0.0), -1.0e9);
    m.projectiles[2] = bullet(0, (5.0, 0.0), (0.0, 0.0), 1.0e9);
    for ship in 0..4u8 {
        let o = obs(&m, &cat, ship);
        for (i, &x) in o.iter().enumerate() {
            assert!(
                x.is_finite() && (-OBS_CLIP..=OBS_CLIP).contains(&x),
                "ship {ship} [{i}] = {x}"
            );
        }
        assert_eq!(o[self_f::PRESENT], 1.0);
    }
    let o = obs(&m, &cat, 0);
    assert_eq!(o[self_f::OMEGA], -OBS_CLIP);
    assert_eq!(o[self_f::HP], OBS_CLIP);
    assert_eq!(o[self_f::LOCK_LEFT], OBS_CLIP);
}

#[test]
fn dead_or_absent_observer_gets_all_zeros() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[STRAFER],
        &[(0.0, 0.0, 0.0), (50.0, 0.0, PI)],
    );
    m.projectiles[0] = bullet(1, (5.0, 0.0), (0.0, 0.0), 6.0);
    m.ships[0].alive = false;
    m.ships[0].hp = 0.0;
    m.ships[1].present = false;
    m.ships[1].reaction_ticks = 2;
    for ship in 0..2u8 {
        let o = obs(&m, &cat, ship);
        assert!(o.iter().all(|&x| x == 0.0), "ship {ship}");
    }
}

#[test]
fn obs_is_deterministic_bitwise() {
    let cat = test_catalogue();
    let build = || {
        let mut m = placed(
            &cat,
            &[FIGHTER, STRAFER],
            &[GUNSHIP, FIGHTER],
            &[
                (-123.4, 56.7, 0.37),
                (-80.1, -12.9, -1.2),
                (140.3, 20.2, 2.9),
                (95.5, -60.6, -2.4),
            ],
        );
        for (i, s) in m.ships.iter_mut().enumerate() {
            s.vel = Vec2::new(13.1 * i as f32 - 20.0, 7.7 - 3.3 * i as f32);
            s.omega = 0.4 - 0.25 * i as f32;
            s.reaction_ticks = 2;
            s.thrust_level[0] = 0.1 * i as f32;
        }
        for i in 0..10 {
            let f = i as f32;
            m.projectiles[i * 7] = bullet(
                (i % 2) as u8,
                (f * 17.0 - 80.0, 40.0 - f * 9.0),
                (200.0, -f),
                6.0,
            );
        }
        m.tick = 400;
        m
    };
    let (a, b) = (build(), build());
    for ship in 0..4u8 {
        let (oa, ob) = (obs(&a, &cat, ship), obs(&b, &cat, ship));
        assert!(oa.iter().zip(&ob).all(|(x, y)| x.to_bits() == y.to_bits()));
        // Rewriting into a dirty buffer gives the same bits.
        let mut dirty = [7.0f32; OBS_DIM];
        a.write_obs(&cat, ship, &mut dirty);
        assert!(
            oa.iter()
                .zip(&dirty)
                .all(|(x, y)| x.to_bits() == y.to_bits())
        );
    }
}

#[test]
#[should_panic(expected = "OBS_DIM")]
fn wrong_buffer_length_panics() {
    let cat = test_catalogue();
    let m = new_match(&cat, 1, &[FIGHTER], &[FIGHTER]);
    let mut out = [0.0f32; OBS_DIM - 1];
    m.write_obs(&cat, 0, &mut out);
}
