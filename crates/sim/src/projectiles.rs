//! Projectile advance, torpedo steering, swept hit tests and flak bursts
//! (SIM_SPEC §5 stage 8, §5.3), plus the segment/circle geometry and the
//! shield-first target shape shared with beams.

use crate::DT;
use crate::damage::{apply_damage, can_hit};
use crate::data::{Catalogue, HullDef, WeaponKind};
use crate::events::Event;
use crate::math::{Vec2, clamp, wrap_angle};
use crate::state::{MAX_PROJECTILES, Match, NONE, Projectile, Ship, ShipIdx};

/// Slack added to `hit_radius` in the swept and beam broad phases.
pub const BROAD_PHASE_SLACK: f32 = 0.5;

/// Visual radius of the `Burst` a torpedo impact emits (torpedoes do no splash
/// damage; the value is sim.js's impact flash).
pub const TORPEDO_IMPACT_RADIUS: f32 = 14.0;

/// Parameter `t ∈ [0, 1]` of the point on segment `a → b` closest to `c`.
#[inline]
pub fn closest_t(a: Vec2, b: Vec2, c: Vec2) -> f32 {
    let d = b - a;
    let len2 = d.length_sq();
    if len2 > 0.0 {
        clamp((c - a).dot(d) / len2, 0.0, 1.0)
    } else {
        0.0
    }
}

/// Point on segment `a → b` closest to `c`.
#[inline]
pub fn closest_point(a: Vec2, b: Vec2, c: Vec2) -> Vec2 {
    a + (b - a) * closest_t(a, b, c)
}

/// Distance from `c` to segment `a → b`.
#[inline]
pub fn segment_dist(a: Vec2, b: Vec2, c: Vec2) -> f32 {
    (closest_point(a, b, c) - c).length()
}

/// Whether segment `a → b` passes strictly within `r` of `c` (sim.js
/// `segmentHitsCircle`).
#[inline]
pub fn segment_hits_circle(a: Vec2, b: Vec2, c: Vec2, r: f32) -> bool {
    (closest_point(a, b, c) - c).length_sq() < r * r
}

/// Parameter `t ∈ [0, 1]` where segment `a → b` first enters the circle `(c, r)`;
/// 0 when `a` is already inside, `None` on a miss.
pub fn segment_circle_entry(a: Vec2, b: Vec2, c: Vec2, r: f32) -> Option<f32> {
    let f = a - c;
    let cc = f.length_sq() - r * r;
    if cc < 0.0 {
        return Some(0.0);
    }
    let d = b - a;
    let aa = d.length_sq();
    if aa == 0.0 {
        return None;
    }
    let bb = 2.0 * f.dot(d);
    let disc = bb * bb - 4.0 * aa * cc;
    if disc < 0.0 {
        return None;
    }
    let t = (-bb - libm::sqrtf(disc)) / (2.0 * aa);
    (0.0..=1.0).contains(&t).then_some(t)
}

/// What a projectile, beam or flak burst tests against on one ship, read at the
/// moment of the test (SIM_SPEC §5.3, v2 shield-first): while `shield > 0` the
/// single shield bubble `(pos, shield_radius)`, otherwise the hull's compound
/// collision circles in world space.
#[derive(Clone, Copy, Debug)]
pub struct TargetShape<'a> {
    ship: &'a Ship,
    hull: &'a HullDef,
}

impl<'a> TargetShape<'a> {
    pub fn of(cat: &'a Catalogue, ship: &'a Ship) -> Self {
        TargetShape {
            ship,
            hull: cat.hull(ship.hull),
        }
    }

    /// The shield is up, so the bubble is the shape.
    #[inline]
    pub fn shielded(&self) -> bool {
        self.ship.shield > 0.0
    }

    /// Broad-phase radius around `ship.pos`: `shield_radius` while shielded, else
    /// `bound_radius`.
    #[inline]
    pub fn hit_radius(&self) -> f32 {
        if self.shielded() {
            self.hull.shield_radius
        } else {
            self.hull.bound_radius
        }
    }

    /// The circles to test, as world `(centre, r)`: the bubble alone, or the hull
    /// circles in hull order.
    pub fn circles(&self) -> impl Iterator<Item = (Vec2, f32)> + 'a {
        let ship = self.ship;
        let (bubble, hull_circles) = if self.shielded() {
            (Some((ship.pos, self.hull.shield_radius)), &[][..])
        } else {
            (None, &self.hull.collision[..])
        };
        bubble.into_iter().chain(
            hull_circles
                .iter()
                .map(move |c| (ship.to_world(c.pos), c.r)),
        )
    }
}

/// `TargetShape::hit_radius` of `ship` (SIM_SPEC §5.3).
#[inline]
pub fn hit_radius(cat: &Catalogue, ship: &Ship) -> f32 {
    TargetShape::of(cat, ship).hit_radius()
}

/// Swept test of a projectile moving `from → to` against `ship`'s target shape:
/// broad phase on `hit_radius + 0.5`, then `segment_hits_circle` on each circle of
/// the shape. Returns the hit point: where the segment first enters any circle it
/// hits (its start if it starts inside).
///
/// Deviation from SIM_SPEC §5.3, which takes the closest point on the segment to
/// the circle's centre: for a segment through a circle that point is the centre
/// itself, so armour bearings would collapse onto circle centres (an abeam shot on
/// the fighter reads as nose or engine) and a shot through the shield bubble's
/// centre would have no normal. The entry point is where the shot really crossed,
/// the same rule beams use; which ship is hit is unchanged.
pub fn swept_hit(cat: &Catalogue, ship: &Ship, from: Vec2, to: Vec2) -> Option<Vec2> {
    let shape = TargetShape::of(cat, ship);
    if segment_dist(from, to, ship.pos) >= shape.hit_radius() + BROAD_PHASE_SLACK {
        return None;
    }
    shape
        .circles()
        .filter(|&(centre, r)| segment_hits_circle(from, to, centre, r))
        .map(|(centre, r)| {
            // `segment_hits_circle` passing guarantees an entry up to rounding; fall
            // back to the closest point if the quadratic loses it.
            segment_circle_entry(from, to, centre, r).unwrap_or(closest_t(from, to, centre))
        })
        .reduce(f32::min)
        .map(|t| from + (to - from) * t)
}

/// Parameter of the first entry of segment `from → to` into `ship`'s target shape
/// (beams, SIM_SPEC §6): broad phase on `hit_radius + 0.5`, then the earliest entry
/// over the shape's circles; `None` on a miss.
pub fn segment_shape_entry(cat: &Catalogue, ship: &Ship, from: Vec2, to: Vec2) -> Option<f32> {
    let shape = TargetShape::of(cat, ship);
    if segment_dist(from, to, ship.pos) >= shape.hit_radius() + BROAD_PHASE_SLACK {
        return None;
    }
    shape
        .circles()
        .filter_map(|(centre, r)| segment_circle_entry(from, to, centre, r))
        .reduce(f32::min)
}

/// Torpedo steering (before advance): turn the velocity toward the locked target
/// by at most `turn_rate * DT`, keeping `speed`. No-op without an active target.
pub fn steer_torpedo(p: &mut Projectile, ships: &[Ship], turn_rate: f32) {
    if p.target == NONE {
        return;
    }
    let target = &ships[p.target as usize];
    if !target.active() {
        return;
    }
    let want = (target.pos - p.pos).angle();
    let have = p.vel.angle();
    let max_turn = turn_rate * DT;
    let have = have + clamp(wrap_angle(want - have), -max_turn, max_turn);
    p.vel = Vec2::from_angle(have) * p.speed;
}

impl Match {
    /// Stage 8 of SIM_SPEC §5 (projectiles), in pool order: torpedo steer, advance,
    /// `life_ticks -= 1`, swept hit against enemy active ships in slot order (first
    /// hit consumes; damage applied immediately), else flak bursts at fuse end, else
    /// expiry at `life_ticks == 0`. Uses no randomness.
    pub fn step_projectiles(&mut self, cat: &Catalogue) {
        for i in 0..MAX_PROJECTILES {
            let mut p = self.projectiles[i];
            if !p.alive {
                continue;
            }
            let w = cat.weapon(p.weapon);
            if p.kind == WeaponKind::Torpedo {
                steer_torpedo(&mut p, &self.ships, w.turn_rate);
            }
            let next = p.pos + p.vel * DT;
            p.life_ticks = p.life_ticks.saturating_sub(1);

            if let Some((target, point)) = self.first_swept_hit(cat, &p, next) {
                apply_damage(
                    self,
                    cat,
                    target,
                    p.damage,
                    point,
                    p.owner,
                    p.fire_tick,
                    p.decision_tick,
                );
                if p.kind == WeaponKind::Torpedo {
                    self.events.push(Event::Burst {
                        team: p.team,
                        pos: point,
                        radius: TORPEDO_IMPACT_RADIUS,
                    });
                }
                p.alive = false;
            } else if p.life_ticks == 0 {
                if p.kind == WeaponKind::Flak {
                    self.flak_burst(cat, &p, next, w.burst_radius);
                }
                p.alive = false;
            } else {
                p.pos = next;
            }
            self.projectiles[i] = p;
        }
    }

    /// First enemy ship in slot order that the segment `p.pos → next` hits.
    fn first_swept_hit(
        &self,
        cat: &Catalogue,
        p: &Projectile,
        next: Vec2,
    ) -> Option<(ShipIdx, Vec2)> {
        let owner = &self.ships[p.owner as usize];
        self.ships
            .iter()
            .filter(|s| can_hit(p.team, owner, s))
            .find_map(|s| swept_hit(cat, s, p.pos, next).map(|pt| (s.slot, pt)))
    }

    /// Flak fuse burst at `at`: emit `Burst`, then full damage to every enemy active
    /// ship with `|ship.pos - at| < burst_radius + hit_radius`, in slot order.
    fn flak_burst(&mut self, cat: &Catalogue, p: &Projectile, at: Vec2, burst_radius: f32) {
        self.events.push(Event::Burst {
            team: p.team,
            pos: at,
            radius: burst_radius,
        });
        for j in 0..self.ships.len() {
            let owner = &self.ships[p.owner as usize];
            let s = &self.ships[j];
            if !can_hit(p.team, owner, s) {
                continue;
            }
            let reach = burst_radius + hit_radius(cat, s);
            if (s.pos - at).length() < reach {
                apply_damage(
                    self,
                    cat,
                    j as ShipIdx,
                    p.damage,
                    at,
                    p.owner,
                    p.fire_tick,
                    p.decision_tick,
                );
            }
        }
    }
}
