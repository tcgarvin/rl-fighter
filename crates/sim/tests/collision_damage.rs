//! v3 collision damage (SIM_SPEC §5.5): excess normal kinetic energy above the free
//! speed, impact arcs per ship, shield first, no HitRecord, damage-taken reward, and
//! the `Collision` event. v7: each ship's own velocity change above `CRASH_DV_FREE`
//! adds hull damage past any shield, so a light ship pays far more than a heavy one.

mod common;

use common::{
    CARRIER, FIGHTER, GUNSHIP, STRAFER, catalogue_with_static, new_present_match, test_catalogue,
};
use sim::collision::{
    COLLISION_DAMAGE_PER_J, COLLISION_FREE_SPEED, CRASH_DV_FREE, CRASH_HULL_PER_DV, RESTITUTION,
    collision_base_damage, crash_dv_damage, deepest_contact,
};
use sim::data::Catalogue;
use sim::events::{EVENT_STRIDE, Event, KIND_COLLISION};
use sim::math::PI;
use sim::reward::{HULL_DAMAGE_WEIGHT, SHIELD_DAMAGE_WEIGHT};
use sim::state::{Match, MatchPhase, NEVER, WINNER_DRAW};
use sim::{DT, Vec2};

fn close(a: f32, b: f32, tol: f32) -> bool {
    (a - b).abs() <= tol
}

/// Two fighters nose to nose on the x axis, noses overlapping at the origin, closing
/// at `closing` m/s (each moving at half of it).
fn nose_to_nose(cat: &Catalogue, closing: f32) -> Match {
    nose_to_nose_at(cat, closing, 3.0)
}

/// As `nose_to_nose`, but for a full `step`: backed off by one tick of motion so the
/// noses overlap as above when stage 10 runs (otherwise they pass through).
fn nose_to_nose_stepped(cat: &Catalogue, closing: f32) -> Match {
    nose_to_nose_at(cat, closing, 3.0 + closing / 2.0 * DT)
}

fn nose_to_nose_at(cat: &Catalogue, closing: f32, x: f32) -> Match {
    let mut m = new_present_match(cat, 1, &[FIGHTER], &[FIGHTER]);
    m.ships[0].pos = Vec2::new(-x, 0.0);
    m.ships[0].heading = 0.0;
    m.ships[0].vel = Vec2::new(closing / 2.0, 0.0);
    m.ships[1].pos = Vec2::new(x, 0.0);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::new(-closing / 2.0, 0.0);
    m
}

/// `COLLISION_DAMAGE_PER_J * 0.5 * mu * (c - free)^2`, written independently.
fn expected_base(closing: f32, mass_a: f32, mass_b: f32) -> f32 {
    let mu = mass_a * mass_b / (mass_a + mass_b);
    let excess = closing - COLLISION_FREE_SPEED;
    COLLISION_DAMAGE_PER_J * 0.5 * mu * excess * excess
}

/// v7 velocity-change term, written independently, for a ship of mass `own` in a
/// contact closing at `closing` with one of mass `other` (`f32::INFINITY`: static):
/// its velocity changes by `(1 + e) * closing * other / (own + other)`.
fn expected_dv(closing: f32, own: f32, other: f32) -> f32 {
    let share = if other.is_infinite() {
        1.0
    } else {
        other / (own + other)
    };
    CRASH_HULL_PER_DV * ((1.0 + RESTITUTION) * closing * share - CRASH_DV_FREE).max(0.0)
}

#[test]
fn head_on_fighters_take_nose_multiplied_damage() {
    let cat = test_catalogue();
    let mut m = nose_to_nose(&cat, 100.0);
    m.resolve_collisions(&cat);
    // mu = 5 kg, excess 90 m/s: 20,250 J -> 40.5 hp. Each changes velocity by
    // 1.2 * 100 / 2 = 60 m/s: 1.25 * 48 = 60 more. Both times the 1.5x nose.
    let base = expected_base(100.0, 10.0, 10.0);
    assert!(close(base, 40.5, 1e-3), "{base}");
    let dv = expected_dv(100.0, 10.0, 10.0);
    assert!(close(dv, 60.0, 1e-3), "{dv}");
    for s in 0..2 {
        let ship = &m.ships[s];
        assert!(
            close(ship.hp, 80.0 - 1.5 * (base + dv), 1e-3),
            "slot {s}: {}",
            ship.hp
        );
        assert!(close(m.collision_damage[s], 1.5 * (base + dv), 1e-3));
        assert_eq!(m.collision_shield_damage[s], 0.0);
        assert_eq!(
            ship.last_hit_tick, m.tick,
            "collisions delay shield regen like hits"
        );
        assert!(ship.alive, "damage never flips alive");
    }
    assert!(m.hits().is_empty(), "collisions create no HitRecord");
}

#[test]
fn flank_impact_takes_one_x_while_the_rammer_nose_takes_one_and_a_half() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 1, &[FIGHTER], &[FIGHTER]);
    // Ship 0 broadside (nose up, +y), at rest; ship 1 rams its starboard side nose first.
    m.ships[0].pos = Vec2::ZERO;
    m.ships[0].heading = PI / 2.0;
    m.ships[0].vel = Vec2::ZERO;
    m.ships[1].pos = Vec2::new(5.0, 0.0);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::new(-80.0, 0.0);
    let (a, b) = (&m.ships[0], &m.ships[1]);
    let c = deepest_contact(a, cat.hull(a.hull), b, cat.hull(b.hull)).expect("overlap");
    let closing = 80.0 * c.normal.x;
    m.resolve_collisions(&cat);
    let base = expected_base(closing, 10.0, 10.0);
    let dv = expected_dv(closing, 10.0, 10.0);
    assert!(base > 1.0 && dv > 1.0, "{base} {dv}");
    assert!(
        close(m.collision_damage[0], base + dv, 1e-3),
        "flank 1x: {:?}",
        m.collision_damage
    );
    assert!(
        close(m.collision_damage[1], 1.5 * (base + dv), 1e-3),
        "nose 1.5x"
    );
}

#[test]
fn closing_at_or_below_the_free_speed_does_no_damage() {
    let cat = test_catalogue();
    for closing in [1.0, 8.0, COLLISION_FREE_SPEED] {
        let mut m = nose_to_nose(&cat, closing);
        m.resolve_collisions(&cat);
        for ship in &m.ships {
            assert_eq!(ship.hp, 80.0, "closing {closing}");
            assert_eq!(ship.last_hit_tick, NEVER, "closing {closing}");
        }
        assert_eq!(m.collision_damage, [0.0; sim::state::MAX_SHIPS]);
        assert!(m.events().is_empty(), "scrapes emit nothing");
        assert!(m.ships[0].vel.x < 0.0, "still bounces");
    }
    assert_eq!(collision_base_damage(-COLLISION_FREE_SPEED, 0.1, 0.1), 0.0);
    assert_eq!(collision_base_damage(5.0, 0.1, 0.1), 0.0, "separating");
    assert_eq!(crash_dv_damage(CRASH_DV_FREE), 0.0);
    assert_eq!(
        CRASH_DV_FREE,
        (1.0 + RESTITUTION) * COLLISION_FREE_SPEED,
        "the dv term never fires without the energy term"
    );
}

#[test]
fn static_hull_takes_no_collision_damage() {
    let (cat, station) = catalogue_with_static();
    let mut m = new_present_match(&cat, 2, &[station], &[FIGHTER]);
    m.ships[0].pos = Vec2::ZERO;
    m.ships[0].vel = Vec2::ZERO;
    m.ships[1].pos = Vec2::new(12.0, 0.0);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::new(-20.0, 0.0);
    let station_before = m.ships[0].clone();
    m.resolve_collisions(&cat);
    assert_eq!(
        m.ships[0], station_before,
        "static: no damage, no regen delay"
    );
    assert_eq!(m.collision_damage[0], 0.0);
    assert_eq!(m.collision_shield_damage[0], 0.0);
    // Infinite mass: mu is the fighter's own 10 kg; it hits nose first, and its whole
    // 1.2 * 20 = 24 m/s velocity change counts.
    let dv = expected_dv(20.0, 10.0, f32::INFINITY);
    assert!(close(dv, 15.0, 1e-4), "{dv}");
    let want = 1.5 * (COLLISION_DAMAGE_PER_J * 0.5 * 10.0 * 10.0 * 10.0 + dv);
    assert!(
        close(m.collision_damage[1], want, 1e-4),
        "{:?}",
        m.collision_damage
    );
}

#[test]
fn raised_shield_absorbs_the_energy_term_but_not_the_velocity_change_term() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 1, &[STRAFER], &[GUNSHIP]);
    m.ships[0].pos = Vec2::new(-6.0, 0.0);
    m.ships[0].heading = 0.0;
    m.ships[0].vel = Vec2::new(40.0, 0.0);
    m.ships[1].pos = Vec2::new(4.0, 0.0);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::ZERO;
    let shields = [m.ships[0].shield, m.ships[1].shield];
    m.resolve_collisions(&cat);
    let base = expected_base(40.0, 11.0, 60.0);
    // The strafer changes velocity by 1.2 * 40 * 60 / 71 = 40.6 m/s (hull, nose 1.5x,
    // shield or no); the gunship by 7.4, under the free change.
    let dv = [expected_dv(40.0, 11.0, 60.0), expected_dv(40.0, 60.0, 11.0)];
    assert!(dv[0] > 25.0 && dv[1] == 0.0, "{dv:?}");
    let hull_dmg = [1.5 * dv[0], 0.0];
    for (s, shield_before) in shields.into_iter().enumerate() {
        let ship = &m.ships[s];
        assert!(
            close(ship.hp, cat.hull(ship.hull).hp - hull_dmg[s], 1e-3),
            "slot {s}: the energy term does not overflow, the dv term bypasses: {}",
            ship.hp
        );
        assert!(
            close(m.collision_shield_damage[s], base, 1e-3),
            "raw amount, no arcs"
        );
        // Even power split: P_s = 1, so the shield loses exactly the raw amount.
        assert!(close(ship.shield, shield_before - base, 1e-3), "slot {s}");
        assert!(close(m.collision_damage[s], hull_dmg[s], 1e-3), "slot {s}");
    }
}

#[test]
fn collision_event_carries_slots_point_normal_and_closing_speed() {
    let cat = test_catalogue();
    let mut m = nose_to_nose(&cat, 100.0);
    m.resolve_collisions(&cat);
    let events = m.events();
    assert_eq!(events.len(), 1, "{events:?}");
    let Event::Collision {
        a,
        b,
        pos,
        normal,
        closing,
    } = events[0]
    else {
        panic!("{events:?}");
    };
    assert_eq!((a, b), (0, 1));
    // Nose circles at x = -1 and +1 (r 2.4): surfaces at +1.4 and -1.4, midpoint 0.
    assert!(
        close(pos.x, 0.0, 1e-5) && close(pos.y, 0.0, 1e-5),
        "{pos:?}"
    );
    assert!(
        close(normal.x, 1.0, 1e-6) && close(normal.y, 0.0, 1e-6),
        "{normal:?}"
    );
    assert!(close(closing, 100.0, 1e-4));
    let flat: [f32; EVENT_STRIDE] = events[0].encode();
    assert_eq!(flat[0], f32::from(KIND_COLLISION));
    assert_eq!(KIND_COLLISION, 7, "appended after Arrival");
    assert_eq!(&flat[1..3], &[0.0, 1.0]);
    assert_eq!(&flat[3..7], &[pos.x, pos.y, normal.x, normal.y]);
    assert_eq!(flat[7], closing);
}

#[test]
fn collision_damage_is_taken_reward_with_no_credit() {
    let cat = test_catalogue();
    let mut m = nose_to_nose_stepped(&cat, 60.0);
    m.step(&cat);
    // 1.5 * (12.5 energy + 1.25 * 24 dv) = 63.75 of 80 hp: both survive.
    assert_eq!(m.phase, MatchPhase::Running);
    assert!(m.hits().is_empty());
    for s in 0..2 {
        let dmg = m.collision_damage[s];
        assert!(dmg > 50.0, "slot {s}: {dmg}");
        let want = -HULL_DAMAGE_WEIGHT * dmg;
        assert!(
            close(m.rewards[s], want, 1e-6),
            "slot {s}: {} vs {want}",
            m.rewards[s]
        );
    }
    // The per-step output is cleared on the next step.
    m.step(&cat);
    assert_eq!(m.collision_damage, [0.0; sim::state::MAX_SHIPS]);
}

#[test]
fn shield_collision_damage_uses_the_shield_weight() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 1, &[STRAFER], &[STRAFER]);
    m.ships[0].pos = Vec2::new(-3.0, 0.0);
    m.ships[0].heading = 0.0;
    m.ships[0].vel = Vec2::new(30.0, 0.0);
    m.ships[1].pos = Vec2::new(3.0, 0.0);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::new(-30.0, 0.0);
    m.step(&cat);
    for s in 0..2 {
        let dmg = m.collision_shield_damage[s];
        assert!(dmg > 0.0, "slot {s}");
        // v7: the velocity-change term reaches the hull past the shield, at hull weight.
        let hull = m.collision_damage[s];
        assert!(hull > 0.0, "slot {s}");
        let want = -SHIELD_DAMAGE_WEIGHT * dmg - HULL_DAMAGE_WEIGHT * hull;
        assert!(
            close(m.rewards[s], want, 1e-6),
            "slot {s}: {} vs {want}",
            m.rewards[s]
        );
    }
}

#[test]
fn mutual_lethal_crash_is_a_draw() {
    let cat = test_catalogue();
    let mut m = nose_to_nose_stepped(&cat, 100.0);
    m.ships[0].hp = 20.0;
    m.ships[1].hp = 20.0;
    m.step(&cat);
    assert!(m.ships.iter().all(|s| !s.alive), "both die in stage 12");
    assert_eq!(m.phase, MatchPhase::Over);
    assert_eq!(m.winner, WINNER_DRAW);
    let deaths = m
        .events()
        .iter()
        .filter(|e| matches!(e, Event::Death { .. }))
        .count();
    assert_eq!(deaths, 2);
    // Draw: no terminal term; only the damage taken.
    for s in 0..2 {
        let want = -HULL_DAMAGE_WEIGHT * m.collision_damage[s];
        assert!(close(m.rewards[s], want, 1e-6), "slot {s}");
    }
}

/// A fighter at its 60 m/s cap into a carrier at rest, at heading `heading` (it still
/// moves in -x): carrier at the origin, fighter just touching its bow circle.
fn fighter_into_carrier(cat: &Catalogue, speed: f32, heading: f32) -> Match {
    let mut m = new_present_match(cat, 1, &[CARRIER], &[FIGHTER]);
    m.ships[0].pos = Vec2::ZERO;
    m.ships[0].heading = 0.0;
    m.ships[0].vel = Vec2::ZERO;
    m.ships[0].shield = 0.0;
    // Bow circle at (13, 0) r 6.5; the fighter's centre 1 m outside it, so one of its
    // circles (offset 2 m along its heading) overlaps the bow at every heading.
    m.ships[1].pos = Vec2::new(13.0 + 6.5 + 1.0, 0.0);
    m.ships[1].heading = heading;
    m.ships[1].vel = Vec2::new(-speed, 0.0);
    m
}

#[test]
fn fighter_at_full_speed_into_a_carrier_is_destroyed_from_any_bearing() {
    let cat = test_catalogue();
    for deg in [0.0_f32, 45.0, 90.0, 135.0, 180.0, 270.0] {
        let mut m = fighter_into_carrier(&cat, 60.0, deg.to_radians());
        m.resolve_collisions(&cat);
        assert!(
            m.ships[1].hp <= 0.0,
            "heading {deg}: fighter left with {}",
            m.ships[1].hp
        );
        // The carrier's velocity change (about 1.2 m/s) is under the free change: it
        // takes only the energy term, at most 0.5 * 24.6 with its shield down.
        let carrier = &m.ships[0];
        assert!(
            carrier.hp > 1000.0 - 12.5,
            "heading {deg}: carrier at {}",
            carrier.hp
        );
    }
}

#[test]
fn fighter_at_low_speed_into_a_carrier_survives() {
    let cat = test_catalogue();
    for deg in [0.0_f32, 90.0, 180.0] {
        let mut m = fighter_into_carrier(&cat, 25.0, deg.to_radians());
        m.resolve_collisions(&cat);
        assert!(m.collision_damage[1] > 0.0, "heading {deg}: it hurts");
        assert!(m.ships[1].hp > 40.0, "heading {deg}: {}", m.ships[1].hp);
    }
}
