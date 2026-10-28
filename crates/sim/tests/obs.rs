//! WP6 acceptance (SIM_SPEC §7.2, §14): obs layout, body-frame rotation, nearest-K
//! selection, absent slots, clamping, dead observer, determinism.
//!
//! Ship state is set explicitly in every test (positions, headings, present/alive)
//! so the tests do not depend on arrival placement.

mod common;

use common::{FIGHTER, GUNSHIP, STRAFER, new_match, test_catalogue};
use sim::Vec2;
use sim::data::{Catalogue, HullId, WeaponKind};
use sim::math::PI;
use sim::obs::*;
use sim::state::{MAX_PROJECTILES, Match, Projectile};

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
    assert_eq!(OBS_DIM, 204);
    assert_eq!((SELF_OFF, SELF_WIDTH), (0, 20));
    assert_eq!((THRUSTERS_OFF, THRUSTERS_WIDTH), (20, 48));
    assert_eq!((TURRETS_OFF, TURRETS_WIDTH), (68, 60));
    assert_eq!((SHIPS_OFF, SHIPS_WIDTH), (128, 36));
    assert_eq!((PROJ_OFF, PROJ_WIDTH), (164, 28));
    assert_eq!((TURRET_ARC_OFF, TURRET_ARC_WIDTH), (192, 6));
    assert_eq!((TURRET_RANGE_OFF, TURRET_RANGE_WIDTH), (198, 6));
    assert_eq!((THRUSTER_W, TURRET_W, SHIP_W, PROJ_W), (6, 10, 12, 7));
    let total = SELF_WIDTH
        + THRUSTERS_WIDTH
        + TURRETS_WIDTH
        + SHIPS_WIDTH
        + PROJ_WIDTH
        + TURRET_ARC_WIDTH
        + TURRET_RANGE_WIDTH;
    assert_eq!(total, OBS_DIM);
}

#[test]
fn obs_layout_is_contiguous_and_covers_obs() {
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
            "turret_arc",
            "turret_range"
        ]
    );
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
}

#[test]
fn nearest_ships_sorted_by_distance_with_slot_tie_break() {
    let cat = test_catalogue();
    // Observer slot 0; slot 1 ally at 80; enemies slots 2..5 at 50, 30, 50, 200.
    let m = placed(
        &cat,
        &[FIGHTER, FIGHTER],
        &[FIGHTER, FIGHTER, FIGHTER, FIGHTER],
        &[
            (0.0, 0.0, 0.0),
            (0.0, 80.0, 0.0),
            (50.0, 0.0, 0.0),
            (0.0, -30.0, 0.0),
            (-50.0, 0.0, 0.0),
            (200.0, 0.0, 0.0),
        ],
    );
    let o = obs(&m, &cat, 0);
    let d = |k| ship_rec(&o, k)[ship_f::DIST] * 450.0;
    assert!((d(0) - 30.0).abs() < 1e-3);
    assert!((d(1) - 50.0).abs() < 1e-3);
    assert!((d(2) - 50.0).abs() < 1e-3);
    // Tie at 50 m: slot 2 (ahead, +x) before slot 4 (behind, -x).
    assert!(ship_rec(&o, 1)[ship_f::REL_POS_X] > 0.0);
    assert!(ship_rec(&o, 2)[ship_f::REL_POS_X] < 0.0);
    // The ally at 80 m is fourth, so it is cut.
    for k in 0..N_NEAR_SHIPS {
        assert_eq!(ship_rec(&o, k)[ship_f::IS_ENEMY], 1.0);
    }
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

#[test]
fn nearest_projectiles_ordering_hostility_and_tie_break() {
    let cat = test_catalogue();
    let mut m = placed(
        &cat,
        &[FIGHTER],
        &[FIGHTER],
        &[(0.0, 0.0, 0.0), (300.0, 0.0, PI)],
    );
    // Pool order: 5 → 40 m own, 9 → 20 m hostile, 12 → 40 m hostile (ties with 5),
    // 20 → 100 m hostile, 30 → 10 m dead (ignored), 40 → 60 m hostile.
    m.projectiles[5] = bullet(0, (40.0, 0.0), (240.0, 0.0), 6.0);
    m.projectiles[9] = bullet(1, (0.0, 20.0), (-240.0, 0.0), 6.0);
    m.projectiles[12] = bullet(1, (-40.0, 0.0), (0.0, 0.0), 55.0);
    m.projectiles[20] = bullet(1, (100.0, 0.0), (0.0, 0.0), 6.0);
    m.projectiles[30] = Projectile {
        alive: false,
        ..bullet(1, (10.0, 0.0), (0.0, 0.0), 6.0)
    };
    m.projectiles[40] = bullet(1, (60.0, 0.0), (0.0, 0.0), 6.0);
    let o = obs(&m, &cat, 0);
    let x = |k| proj_rec(&o, k)[proj_f::REL_POS_X] * 450.0;
    let y = |k| proj_rec(&o, k)[proj_f::REL_POS_Y] * 450.0;
    assert!((y(0) - 20.0).abs() < 1e-3);
    assert!((x(1) - 40.0).abs() < 1e-3, "slot 5 before slot 12 on tie");
    assert!((x(2) + 40.0).abs() < 1e-3);
    assert!((x(3) - 60.0).abs() < 1e-3);
    assert_eq!(proj_rec(&o, 0)[proj_f::HOSTILE], 1.0);
    assert_eq!(proj_rec(&o, 1)[proj_f::HOSTILE], 0.0);
    assert!((proj_rec(&o, 1)[proj_f::REL_VEL_X] - 2.4).abs() < EPS);
    assert!((proj_rec(&o, 2)[proj_f::DAMAGE] - 55.0 / 60.0).abs() < EPS);
    for k in 0..N_NEAR_PROJ {
        assert_eq!(proj_rec(&o, k)[proj_f::PRESENT], 1.0);
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
        let rec = &o[THRUSTERS_OFF + j * THRUSTER_W..THRUSTERS_OFF + (j + 1) * THRUSTER_W];
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
    assert!((o[TURRET_RANGE_OFF] - 300.0 / 450.0).abs() < EPS);
    for k in 1..N_NEAR_SHIPS {
        assert!(ship_rec(&o, k).iter().all(|&x| x == 0.0));
    }
    for k in 0..N_NEAR_PROJ {
        assert!(proj_rec(&o, k).iter().all(|&x| x == 0.0));
    }
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
    }
    m.ships[2].vel = Vec2::new(-1.0e8, 1.0e8);
    m.tick = 1_000_000; // far past the time limit
    m.projectiles[0] = bullet(1, (-1.0e9, 1.0e9), (1.0e9, 1.0e9), 1.0e9);
    m.projectiles[1] = bullet(0, (1.0e9, 0.0), (-1.0e9, 0.0), -1.0e9);
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
