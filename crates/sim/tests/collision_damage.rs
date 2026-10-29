//! v3 collision damage (SIM_SPEC §5.5): excess normal kinetic energy above the free
//! speed, impact arcs per ship, shield first, no HitRecord, damage-taken reward, and
//! the `Collision` event.

mod common;

use common::{FIGHTER, GUNSHIP, STRAFER, catalogue_with_static, new_present_match, test_catalogue};
use sim::collision::{
    COLLISION_DAMAGE_PER_J, COLLISION_FREE_SPEED, collision_base_damage, deepest_contact,
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

#[test]
fn head_on_fighters_take_nose_multiplied_damage() {
    let cat = test_catalogue();
    let mut m = nose_to_nose(&cat, 100.0);
    m.resolve_collisions(&cat);
    // mu = 5 kg, excess 90 m/s: 20,250 J -> 40.5 hp, times the 1.5x nose.
    let base = expected_base(100.0, 10.0, 10.0);
    assert!(close(base, 40.5, 1e-3), "{base}");
    for s in 0..2 {
        let ship = &m.ships[s];
        assert!(
            close(ship.hp, 80.0 - 1.5 * base, 1e-3),
            "slot {s}: {}",
            ship.hp
        );
        assert!(close(m.collision_damage[s], 1.5 * base, 1e-3));
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
    assert!(base > 1.0, "{base}");
    assert!(
        close(m.collision_damage[0], base, 1e-3),
        "flank 1x: {:?}",
        m.collision_damage
    );
    assert!(close(m.collision_damage[1], 1.5 * base, 1e-3), "nose 1.5x");
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
    // Infinite mass: mu is the fighter's own 10 kg; it hits nose first.
    let want = 1.5 * COLLISION_DAMAGE_PER_J * 0.5 * 10.0 * 10.0 * 10.0;
    assert!(
        close(m.collision_damage[1], want, 1e-4),
        "{:?}",
        m.collision_damage
    );
}

#[test]
fn raised_shield_absorbs_collision_damage_without_impact_arcs() {
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
    for (s, shield_before) in shields.into_iter().enumerate() {
        let ship = &m.ships[s];
        assert_eq!(
            ship.hp,
            cat.hull(ship.hull).hp,
            "slot {s}: no overflow to hull"
        );
        assert!(
            close(m.collision_shield_damage[s], base, 1e-3),
            "raw amount, no arcs"
        );
        // Even power split: P_s = 1, so the shield loses exactly the raw amount.
        assert!(close(ship.shield, shield_before - base, 1e-3), "slot {s}");
        assert_eq!(m.collision_damage[s], 0.0);
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
    let mut m = nose_to_nose_stepped(&cat, 100.0);
    m.step(&cat);
    assert_eq!(m.phase, MatchPhase::Running, "60.75 of 80 hp: both survive");
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
        let want = -SHIELD_DAMAGE_WEIGHT * dmg;
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
