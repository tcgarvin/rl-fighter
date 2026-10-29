//! Ship-ship compound-circle collision impulses and (v3) collision damage
//! (SIM_SPEC §5.5).
//!
//! Pairs `(i < j)` of active ships are resolved in slot order, each against the
//! positions left by the previous pair. Only the deepest overlapping circle pair of a
//! ship pair is resolved. Static hulls have zero inverse mass, so they never move and
//! take no damage. No torque transfer. A closing contact faster than
//! `COLLISION_FREE_SPEED` damages both (non-static) ships by the excess kinetic energy
//! of the normal approach, scaled per ship by its `impact` arcs, and emits
//! `Collision`. No `HitRecord`: collisions credit no shooter.

use crate::damage::{apply_collision_damage, impact_bearing, same_entity};
use crate::data::{Catalogue, HullDef};
use crate::events::Event;
use crate::math::Vec2;
use crate::state::{Match, Ship};

/// Coefficient of restitution for the normal impulse.
pub const RESTITUTION: f32 = 0.2;
/// v3: closing speeds up to this many m/s along the contact normal do no damage
/// (scrapes and formation bumps are free).
pub const COLLISION_FREE_SPEED: f32 = 10.0;
/// v3: hull points per joule of excess normal kinetic energy (before impact arcs).
pub const COLLISION_DAMAGE_PER_J: f32 = 0.002;

/// Deepest overlapping circle pair of two ships: unit normal from `a` to `b`,
/// penetration depth, and the contact point (v3): the midpoint between the two
/// circles' surfaces along the normal.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Contact {
    pub normal: Vec2,
    pub pen: f32,
    pub point: Vec2,
}

#[inline]
fn inv_mass(hull: &HullDef) -> f32 {
    if hull.is_static { 0.0 } else { 1.0 / hull.mass }
}

/// Deepest overlapping circle pair of `a` and `b`, or `None` if they do not touch.
/// Circles are compared in hull order (a's outer, b's inner); ties keep the first.
/// Coincident centres take the normal `+x` so the pair still separates.
pub fn deepest_contact(a: &Ship, ha: &HullDef, b: &Ship, hb: &HullDef) -> Option<Contact> {
    if (b.pos - a.pos).length() >= ha.bound_radius + hb.bound_radius {
        return None;
    }
    let mut best: Option<Contact> = None;
    for ca in &ha.collision {
        let pa = a.to_world(ca.pos);
        for cb in &hb.collision {
            let pb = b.to_world(cb.pos);
            let delta = pb - pa;
            let d = delta.length();
            let pen = ca.r + cb.r - d;
            if pen <= 0.0 || best.is_some_and(|c| pen <= c.pen) {
                continue;
            }
            let normal = if d > 0.0 { delta / d } else { Vec2::X };
            let point = ((pa + normal * ca.r) + (pb - normal * cb.r)) * 0.5;
            best = Some(Contact { normal, pen, point });
        }
    }
    best
}

/// Collision damage before impact arcs for a contact whose relative normal speed
/// is `vn` (negative = closing) between ships of inverse masses `wa`, `wb`
/// (`wa + wb > 0`): `COLLISION_DAMAGE_PER_J * 0.5 * mu * max(0, -vn - FREE)^2` with
/// reduced mass `mu = 1 / (wa + wb)`. 0 unless closing faster than the free speed.
pub fn collision_base_damage(vn: f32, wa: f32, wb: f32) -> f32 {
    let excess = (-vn - COLLISION_FREE_SPEED).max(0.0);
    let mu = 1.0 / (wa + wb);
    COLLISION_DAMAGE_PER_J * (0.5 * mu * excess * excess)
}

/// Positional correction and restitution impulse for one contact. Operations are
/// evaluated left to right exactly as written in the spec (f32 determinism).
/// Returns the pre-impulse relative normal speed `vn` (negative = closing).
fn resolve(a: &mut Ship, wa: f32, b: &mut Ship, wb: f32, c: Contact) -> f32 {
    let w = wa + wb;
    let n = c.normal;
    a.pos -= n * c.pen * wa / w;
    b.pos += n * c.pen * wb / w;
    let vn = (b.vel - a.vel).dot(n);
    if vn < 0.0 {
        let jimp = -(1.0 + RESTITUTION) * vn / w;
        a.vel -= n * jimp * wa;
        b.vel += n * jimp * wb;
    }
    vn
}

impl Match {
    /// Stage 10 (SIM_SPEC §5): resolve every overlapping pair of active ships.
    /// Not-yet-present and dead ships are skipped, as are parent/child pairs.
    /// Damaging contacts add to `collision_damage` / `collision_shield_damage` and
    /// emit `Collision` (v3).
    pub fn resolve_collisions(&mut self, cat: &Catalogue) {
        let n = self.ships.len();
        let tick = self.tick;
        for i in 0..n {
            for j in (i + 1)..n {
                let (lo, hi) = self.ships.split_at_mut(j);
                let (a, b) = (&mut lo[i], &mut hi[0]);
                if !(a.active() && b.active()) || same_entity(a, b) {
                    continue;
                }
                let (ha, hb) = (cat.hull(a.hull), cat.hull(b.hull));
                let (wa, wb) = (inv_mass(ha), inv_mass(hb));
                if wa + wb == 0.0 {
                    continue;
                }
                let Some(c) = deepest_contact(a, ha, b, hb) else {
                    continue;
                };
                // Bearings from the pre-correction poses the contact was found in.
                let (bear_a, bear_b) = (impact_bearing(a, c.point), impact_bearing(b, c.point));
                let vn = resolve(a, wa, b, wb, c);
                let base = collision_base_damage(vn, wa, wb);
                if base <= 0.0 {
                    continue;
                }
                for (ship, hull, bearing) in [(&mut *a, ha, bear_a), (&mut *b, hb, bear_b)] {
                    if hull.is_static {
                        continue;
                    }
                    let d = apply_collision_damage(ship, hull, base, bearing, tick);
                    let s = ship.slot as usize;
                    self.collision_damage[s] += d.hull;
                    self.collision_shield_damage[s] += d.shield;
                }
                self.events.push(Event::Collision {
                    a: a.slot,
                    b: b.slot,
                    pos: c.point,
                    normal: c.normal,
                    closing: -vn,
                });
            }
        }
    }
}
