//! WP3 acceptance (SIM_SPEC §14): turrets, fire, projectiles, beams, flak, torpedoes,
//! shields, events and HitRecords. `tick` below deliberately runs only stage 1's
//! clears, `step_motion` (stages 3–5) and stages 6–9, so deaths, collisions and the
//! arena never interfere with what a test measures.

mod common;

use common::{FIGHTER, GUNSHIP, STRAFER, TORPEDO, new_present_match, test_catalogue};
use sim::DT;
use sim::actions::ShipAction;
use sim::damage::{apply_damage, same_entity};
use sim::data::{Catalogue, WeaponKind};
use sim::events::{EVENT_STRIDE, Event, KIND_SHIELD_HIT};
use sim::math::{PI, Vec2};
use sim::state::{MAX_PROJECTILES, Match, NONE, Projectile};
use sim::turrets::COOLDOWN_RATE;

fn close(a: f32, b: f32, tol: f32) -> bool {
    (a - b).abs() <= tol
}

/// One tick of the weapons pipeline: stage 1 clears + `tick += 1`, stages 3–9.
fn tick(m: &mut Match, cat: &Catalogue) {
    m.tick += 1;
    m.clear_combat_outputs();
    m.step_motion(cat);
    m.step_turrets(cat);
    m.step_fire(cat);
    m.step_projectiles(cat);
    m.step_shield_regen(cat);
}

fn place(m: &mut Match, slot: usize, pos: Vec2, heading: f32, vel: Vec2) {
    let s = &mut m.ships[slot];
    s.pos = pos;
    s.heading = heading;
    s.vel = vel;
    s.omega = 0.0;
}

/// Park a ship far away so it does not interfere.
fn park(m: &mut Match, slot: usize) {
    place(
        m,
        slot,
        Vec2::new(0.0, 5000.0 + 100.0 * slot as f32),
        0.0,
        Vec2::ZERO,
    );
}

fn fire_turret(j: usize) -> ShipAction {
    let mut a = ShipAction::IDLE;
    a.fire[j] = 1;
    a
}

fn alive_projectiles(m: &Match) -> Vec<(usize, Projectile)> {
    m.projectiles()
        .iter()
        .copied()
        .enumerate()
        .filter(|(_, p)| p.alive)
        .collect()
}

fn point_in_ship(cat: &Catalogue, m: &Match, slot: usize, p: Vec2) -> bool {
    let s = &m.ships[slot];
    cat.hull(s.hull)
        .collision
        .iter()
        .any(|c| (s.to_world(c.pos) - p).length() < c.r)
}

#[test]
fn bullet_swept_hit_on_fast_crossing_ship_does_not_tunnel() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 3, &[FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    // Bullet ends tick k at x = 3.8 + 8k; the target sits between two samples (x = 63.8)
    // turned broadside-on, so its x-extent (±2.6 m) is narrower than one 8 m step,
    // and crosses the bullet line at ~60 m/s.
    place(
        &mut m,
        1,
        Vec2::new(63.8, -14.0),
        0.5 * PI,
        Vec2::new(0.0, 60.0),
    );
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    m.set_action(0, ShipAction::IDLE);
    assert_eq!(m.shots_fired[0], 1);

    let mut hit_tick = None;
    for _ in 0..20 {
        if let Some((_, p)) = alive_projectiles(&m).first().copied() {
            assert!(
                !point_in_ship(&cat, &m, 1, p.pos),
                "a point test would have hit"
            );
        }
        tick(&mut m, &cat);
        if !m.hits().is_empty() {
            hit_tick = Some(m.tick);
            break;
        }
    }
    assert!(
        hit_tick.is_some(),
        "bullet tunnelled through the crossing ship"
    );
    assert_eq!(m.ships[1].hp, 60.0 - 6.0);
    let h = m.hits()[0];
    assert_eq!(
        (h.shooter, h.target, h.fire_tick, h.shield),
        (0, 1, 1, false)
    );
    assert!(
        alive_projectiles(&m).is_empty(),
        "the hit consumes the bullet"
    );
    assert!(m.events().iter().any(|e| matches!(
        e,
        Event::Hit {
            target: 1,
            shooter: 0,
            ..
        }
    )));
}

#[test]
fn hit_record_carries_owner_and_fire_tick() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 4, &[FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    place(&mut m, 1, Vec2::new(100.0, 0.0), PI, Vec2::ZERO);
    for _ in 0..4 {
        tick(&mut m, &cat);
    }
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    let fired_on = m.tick;
    m.set_action(0, ShipAction::IDLE);
    let p = alive_projectiles(&m)[0].1;
    assert_eq!(
        (p.owner, p.fire_tick, p.kind),
        (0, fired_on, WeaponKind::Bullet)
    );
    while m.hits().is_empty() {
        assert!(m.tick < fired_on + 30, "bullet never hit");
        tick(&mut m, &cat);
    }
    assert!(
        m.tick > fired_on + 5,
        "hit lands several ticks after the shot"
    );
    let h = m.hits()[0];
    assert_eq!((h.shooter, h.target, h.fire_tick), (0, 1, fired_on));
    assert_eq!(h.damage, 6.0);
}

#[test]
fn beam_hits_nearest_enemy_only() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 5, &[STRAFER], &[FIGHTER, FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    // Slot 1 is farther than slot 2: nearest wins, not slot order.
    place(&mut m, 1, Vec2::new(100.0, 0.0), 0.0, Vec2::ZERO);
    place(&mut m, 2, Vec2::new(50.0, 0.0), 0.0, Vec2::ZERO);
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    assert_eq!(m.ships[2].hp, 60.0 - 3.0);
    assert_eq!(m.ships[1].hp, 60.0);
    assert!(
        alive_projectiles(&m).is_empty(),
        "beams never enter the pool"
    );
    let beam = m.events().iter().find_map(|e| match *e {
        Event::Beam {
            ship,
            from,
            to,
            hit,
        } => Some((ship, from, to, hit)),
        _ => None,
    });
    let (ship, from, to, hit) = beam.expect("Beam event");
    assert_eq!(ship, 0);
    assert!(hit);
    assert!(close(from.x, 3.4, 1e-4), "beam starts at the muzzle");
    // Fighter's rear circle is (-2.2, 0) r 2.6 → entry at x ≈ 50 - 4.8.
    assert!(
        close(to.x, 45.2, 0.05),
        "beam ends at the entry point, got {to:?}"
    );
    let h = m.hits()[0];
    assert_eq!((h.shooter, h.target, h.fire_tick), (0, 2, m.tick));
}

#[test]
fn beam_miss_reaches_full_range() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 5, &[STRAFER], &[FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    park(&mut m, 1);
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    let to = m.events().iter().find_map(|e| match *e {
        Event::Beam { to, hit: false, .. } => Some(to),
        _ => None,
    });
    let to = to.expect("missed Beam event");
    assert!(close((to - Vec2::new(3.4, 0.0)).length(), 180.0, 1e-3));
    assert!(m.hits().is_empty());
}

#[test]
fn flak_burst_damages_within_radius() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 6, &[GUNSHIP], &[FIGHTER, FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    park(&mut m, 1);
    park(&mut m, 2);
    m.set_action(0, fire_turret(0)); // fore flak
    tick(&mut m, &cat);
    m.set_action(0, ShipAction::IDLE);
    let p = alive_projectiles(&m)[0].1;
    assert_eq!(p.kind, WeaponKind::Flak);
    let full_life = cat.weapon(p.weapon).life_ticks;
    assert!(
        p.life_ticks < full_life,
        "fuse is jittered and already advanced once"
    );
    let burst_at = p.pos + p.vel * DT * p.life_ticks as f32;
    let side = p.vel.normalized().perp();
    // Off the flight line (no direct hit), inside / outside 14 + bound_radius (≈ 18.8).
    place(&mut m, 1, burst_at + side * 15.0, 0.0, Vec2::ZERO);
    place(&mut m, 2, burst_at - side * 22.0, 0.0, Vec2::ZERO);

    let mut burst = None;
    for _ in 0..60 {
        tick(&mut m, &cat);
        burst = m.events().iter().find_map(|e| match *e {
            Event::Burst { team, pos, radius } => Some((team, pos, radius)),
            _ => None,
        });
        if burst.is_some() {
            break;
        }
    }
    let (team, pos, radius) = burst.expect("flak burst at fuse end");
    assert_eq!((team, radius), (0, 14.0));
    assert!((pos - burst_at).length() < 1e-2);
    assert_eq!(m.ships[1].hp, 60.0 - 4.0, "inside the burst radius");
    assert_eq!(m.ships[2].hp, 60.0, "outside the burst radius");
    assert_eq!(m.hits().len(), 1);
    assert!(alive_projectiles(&m).is_empty());
}

/// Fighters carrying a torpedo rack on the nose instead of the gauss gun.
fn torpedo_catalogue() -> Catalogue {
    let mut cat = test_catalogue();
    cat.hulls[FIGHTER as usize].turrets[0].weapon = TORPEDO;
    cat
}

fn at_bearing(deg: f32, dist: f32) -> Vec2 {
    Vec2::from_angle(deg.to_radians()) * dist
}

#[test]
fn torpedo_locks_within_cone_and_turns_at_its_rate() {
    let cat = torpedo_catalogue();
    let mut m = new_present_match(&cat, 7, &[FIGHTER], &[FIGHTER, FIGHTER, FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::new(30.0, 0.0));
    place(&mut m, 1, at_bearing(20.0, 120.0), 0.0, Vec2::ZERO); // outside the 15° half-cone
    place(&mut m, 2, at_bearing(10.0, 120.0), 0.0, Vec2::ZERO); // the lock
    place(&mut m, 3, at_bearing(3.0, 400.0), 0.0, Vec2::ZERO); // in cone, beyond range
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    m.set_action(0, ShipAction::IDLE);

    let (slot, p) = alive_projectiles(&m)[0];
    assert_eq!((p.kind, p.target), (WeaponKind::Torpedo, 2));
    let w = cat.weapon(TORPEDO);
    assert!(
        close(p.vel.length(), w.speed, 1e-3),
        "torpedo does not inherit ship vel"
    );
    let step = w.turn_rate * DT;
    // Spawned on the nose line (spread 0), then steered once this tick.
    assert!(
        close(p.vel.angle(), step, 1e-5),
        "first turn {}",
        p.vel.angle()
    );
    tick(&mut m, &cat);
    let p2 = m.projectiles()[slot];
    assert!(close(p2.vel.angle() - p.vel.angle(), step, 1e-5));
    assert!(close(p2.vel.length(), w.speed, 1e-3));

    let mut hit = false;
    for _ in 0..120 {
        tick(&mut m, &cat);
        if let Some(h) = m.hits().first() {
            assert_eq!((h.target, h.damage), (2, 55.0));
            assert!(
                m.events()
                    .iter()
                    .any(|e| matches!(e, Event::Burst { team: 0, .. }))
            );
            hit = true;
            break;
        }
    }
    assert!(hit, "locked torpedo reaches its target");
}

#[test]
fn torpedo_without_lock_flies_straight() {
    let cat = torpedo_catalogue();
    let mut m = new_present_match(&cat, 8, &[FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    place(&mut m, 1, at_bearing(40.0, 100.0), 0.0, Vec2::ZERO);
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    m.set_action(0, ShipAction::IDLE);
    let (slot, p) = alive_projectiles(&m)[0];
    assert_eq!(p.target, NONE);
    for _ in 0..30 {
        tick(&mut m, &cat);
        let q = m.projectiles()[slot];
        assert!(q.alive);
        assert_eq!(q.vel, p.vel, "no lock → no steering");
    }
}

#[test]
fn shield_absorbs_without_overflow_then_regens_after_delay() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 9, &[FIGHTER], &[STRAFER]);
    m.tick = 100;
    let hp0 = m.ships[1].hp;
    let pos = m.ships[1].pos;
    apply_damage(&mut m, &cat, 1, 10.0, pos + Vec2::new(-5.0, 0.0), 0, 95);
    // Even split: P_s = 1 → absorbed = 10 / 1.
    assert!(close(m.ships[1].shield, 30.0, 1e-5));
    assert_eq!(m.ships[1].hp, hp0, "shield takes the whole hit");
    assert_eq!(m.ships[1].last_hit_tick, 100);
    let h = m.hits()[0];
    assert!(h.shield && h.damage == 10.0 && h.fire_tick == 95 && h.shooter == 0);

    // Delay 3 s = 90 ticks at P_s = 1.
    for t in 101..190 {
        m.tick = t;
        m.step_shield_regen(&cat);
        assert!(
            close(m.ships[1].shield, 30.0, 1e-5),
            "regen before delay at {t}"
        );
    }
    m.tick = 190;
    m.step_shield_regen(&cat);
    assert!(close(m.ships[1].shield, 30.0 + 8.0 * DT, 1e-5));

    // A big hit on a small shield depletes it; nothing overflows to the hull.
    m.ships[1].shield = 2.0;
    m.events.clear();
    apply_damage(&mut m, &cat, 1, 50.0, pos, 0, 190);
    assert_eq!(m.ships[1].shield, 0.0);
    assert_eq!(m.ships[1].hp, hp0);
    assert!(matches!(
        m.events()[0],
        Event::ShieldHit { depleted: true, .. }
    ));
    // With the shield down the next hit goes to the hull.
    apply_damage(&mut m, &cat, 1, 5.0, pos, 0, 190);
    assert_eq!(m.ships[1].hp, hp0 - 5.0);
    assert!(!m.hits()[2].shield);
}

#[test]
fn shield_power_scales_absorption_delay_and_regen() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 10, &[FIGHTER], &[STRAFER]);
    let split = [0.6, 0.2, 0.2];
    m.ships[1].power = split;
    m.ships[1].power_target = split;
    let p_s = 0.2 + 0.8 * 3.0 * 0.6; // 1.64
    m.tick = 10;
    let pos = m.ships[1].pos;
    apply_damage(&mut m, &cat, 1, 10.0, pos + Vec2::X, 0, 10);
    let after_hit = 40.0 - 10.0 / (0.7 + 0.3 * p_s);
    assert!(close(m.ships[1].shield, after_hit, 1e-4));

    let delay = (3.0 * 30.0 / p_s).round() as u32; // 55, not 90
    assert_eq!(delay, 55);
    m.tick = 10 + delay - 1;
    m.step_shield_regen(&cat);
    assert!(close(m.ships[1].shield, after_hit, 1e-5));
    m.tick = 10 + delay;
    m.step_shield_regen(&cat);
    assert!(close(m.ships[1].shield, after_hit + 8.0 * p_s * DT, 1e-4));
}

#[test]
fn shield_hit_normal_is_unit_and_outward() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 11, &[FIGHTER], &[STRAFER]);
    let centre = Vec2::new(20.0, -7.0);
    place(&mut m, 1, centre, 1.0, Vec2::ZERO);
    m.tick = 1;
    for (point, want) in [
        (centre + Vec2::new(3.0, 4.0), Vec2::new(0.6, 0.8)),
        (centre + Vec2::new(-0.5, 0.0), Vec2::new(-1.0, 0.0)),
        (centre, Vec2::X), // degenerate: defined fallback
    ] {
        m.events.clear();
        m.ships[1].shield = 40.0;
        apply_damage(&mut m, &cat, 1, 1.0, point, 0, 1);
        let Event::ShieldHit {
            target,
            shooter,
            pos,
            normal,
            depleted,
        } = m.events()[0]
        else {
            panic!("expected ShieldHit, got {:?}", m.events()[0]);
        };
        assert_eq!((target, shooter, depleted), (1, 0, false));
        assert!(close(normal.length(), 1.0, 1e-6));
        assert!(close(normal.x, want.x, 1e-6) && close(normal.y, want.y, 1e-6));
        let r = cat.hull(STRAFER).shield_radius;
        assert!(close((pos - centre).length(), r, 1e-4), "on the bubble");
        assert!((pos - centre).dot(normal) > 0.0, "outward");
        let flat = m.events()[0].encode();
        assert_eq!(flat.len(), EVENT_STRIDE);
        assert_eq!(flat[0], f32::from(KIND_SHIELD_HIT));
        assert_eq!((flat[5], flat[6]), (normal.x, normal.y));
    }
}

#[test]
fn pool_recycles_oldest_slot() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 12, &[FIGHTER], &[FIGHTER]);
    park(&mut m, 1);
    let marker = Projectile {
        alive: true,
        fire_tick: 999,
        life_ticks: 1000,
        ..Projectile::DEAD
    };
    m.projectiles = [marker; MAX_PROJECTILES];
    m.proj_next = MAX_PROJECTILES - 1;
    m.set_action(0, fire_turret(0));
    m.tick = 1;
    m.step_fire(&cat);
    assert_eq!(m.projectiles[MAX_PROJECTILES - 1].fire_tick, 1);
    assert_eq!(m.proj_next, 0);
    m.ships[0].turret_cooldown[0] = 0.0;
    m.tick = 2;
    m.step_fire(&cat);
    assert_eq!(
        m.projectiles[0].fire_tick, 2,
        "overwrites the live oldest slot"
    );
    assert_eq!(m.projectiles[1].fire_tick, 999);
    assert_eq!(m.proj_next, 1);
}

#[test]
fn no_friendly_fire_bullets_and_beams_pass_allies() {
    let cat = test_catalogue();
    // Bullet: ally fighter directly in the line of fire, enemy behind it.
    let mut m = new_present_match(&cat, 13, &[FIGHTER, FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    place(&mut m, 1, Vec2::new(30.0, 0.0), 0.0, Vec2::ZERO);
    place(&mut m, 2, Vec2::new(80.0, 0.0), 0.0, Vec2::ZERO);
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    m.set_action(0, ShipAction::IDLE);
    for _ in 0..20 {
        tick(&mut m, &cat);
    }
    assert_eq!(m.ships[1].hp, 60.0, "ally untouched");
    assert_eq!(m.ships[2].hp, 54.0, "enemy behind the ally hit");

    // Beam: strafer with an ally in front.
    let mut m = new_present_match(&cat, 14, &[STRAFER, FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::ZERO, 0.0, Vec2::ZERO);
    place(&mut m, 1, Vec2::new(20.0, 0.0), 0.0, Vec2::ZERO);
    place(&mut m, 2, Vec2::new(60.0, 0.0), 0.0, Vec2::ZERO);
    m.set_action(0, fire_turret(0));
    tick(&mut m, &cat);
    assert_eq!(m.ships[1].hp, 60.0);
    assert_eq!(m.ships[2].hp, 57.0);
    assert!(same_entity(&m.ships[0], &m.ships[0]));
    assert!(!same_entity(&m.ships[0], &m.ships[1]));
}

#[test]
fn cooldown_scales_with_weapons_power_and_gates_fire() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 15, &[FIGHTER], &[FIGHTER]);
    park(&mut m, 1);
    // Two-way hull, weapons share 0.75 → P_w = 0.2 + 0.8 * 2 * 0.75 = 1.4.
    let split = [0.0, 0.25, 0.75];
    m.ships[0].power = split;
    m.ships[0].power_target = split;
    m.ships[0].turret_cooldown[0] = 1.0;
    m.step_turrets(&cat);
    let want = 1.0 - DT * COOLDOWN_RATE * 1.4;
    assert!(close(m.ships[0].turret_cooldown[0], want, 1e-6));

    // Trigger held while cooling down: no shot, no event.
    m.set_action(0, fire_turret(0));
    m.step_fire(&cat);
    assert_eq!(m.shots_fired[0], 0);
    assert!(m.events().is_empty());
    // Cooldown floors at exactly 0, then the shot goes and resets it to `interval`.
    for _ in 0..40 {
        m.step_turrets(&cat);
    }
    assert_eq!(m.ships[0].turret_cooldown[0], 0.0);
    m.step_fire(&cat);
    assert_eq!(m.shots_fired[0], 1);
    assert_eq!(m.ships[0].turret_cooldown[0], cat.weapon(0).interval);
    assert!(matches!(
        m.events()[0],
        Event::Fire {
            ship: 0,
            turret: 0,
            weapon: 0,
            ..
        }
    ));
}

#[test]
fn turrets_slew_at_rate_and_clamp_to_arc() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 16, &[GUNSHIP], &[FIGHTER]);
    let mut a = ShipAction::IDLE;
    a.slew[0] = 0; // fore flak: left (CCW)
    a.slew[1] = 2; // port gauss: right (CW)
    m.set_action(0, a);
    m.step_turrets(&cat);
    let fore = &cat.hull(GUNSHIP).turrets[0];
    let port = &cat.hull(GUNSHIP).turrets[1];
    assert!(close(m.ships[0].turret_angle[0], fore.slew_rate * DT, 1e-6));
    assert!(close(
        m.ships[0].turret_angle[1],
        port.rest - port.slew_rate * DT,
        1e-6
    ));
    for _ in 0..200 {
        m.step_turrets(&cat);
    }
    assert!(close(m.ships[0].turret_angle[0], 120f32.to_radians(), 1e-5));
    assert!(close(
        m.ships[0].turret_angle[1],
        (90f32 - 110.0).to_radians(),
        1e-5
    ));
}

#[test]
fn control_locked_ship_does_not_fire() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 17, &[FIGHTER], &[FIGHTER]);
    park(&mut m, 1);
    m.ships[0].control_lock_until = 10;
    m.tick = 5;
    m.set_action(0, fire_turret(0));
    m.step_fire(&cat);
    assert_eq!(m.shots_fired[0], 0);
    assert!(alive_projectiles(&m).is_empty());
}

#[test]
fn same_seed_same_fire_sequence() {
    let cat = test_catalogue();
    let run = || {
        let mut m = new_present_match(&cat, 18, &[GUNSHIP], &[FIGHTER]);
        place(&mut m, 1, Vec2::new(120.0, 10.0), PI, Vec2::ZERO);
        m.set_action(0, fire_turret(0));
        for _ in 0..90 {
            tick(&mut m, &cat);
        }
        m.state_hash()
    };
    assert_eq!(run(), run());
}
