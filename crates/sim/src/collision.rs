//! Ship-ship compound-circle collision impulses (SIM_SPEC §5.5).
//!
//! Pairs `(i < j)` of active ships are resolved in slot order, each against the
//! positions left by the previous pair. Only the deepest overlapping circle pair of a
//! ship pair is resolved. Static hulls have zero inverse mass, so they never move.
//! No torque transfer, no damage, no events.

use crate::damage::same_entity;
use crate::data::{Catalogue, HullDef};
use crate::math::Vec2;
use crate::state::{Match, Ship};

/// Coefficient of restitution for the normal impulse.
pub const RESTITUTION: f32 = 0.2;

/// Deepest overlapping circle pair of two ships: unit normal from `a` to `b`
/// and penetration depth.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Contact {
    pub normal: Vec2,
    pub pen: f32,
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
            let delta = b.to_world(cb.pos) - pa;
            let d = delta.length();
            let pen = ca.r + cb.r - d;
            if pen <= 0.0 || best.is_some_and(|c| pen <= c.pen) {
                continue;
            }
            let normal = if d > 0.0 { delta / d } else { Vec2::X };
            best = Some(Contact { normal, pen });
        }
    }
    best
}

/// Positional correction and restitution impulse for one contact. Operations are
/// evaluated left to right exactly as written in the spec (f32 determinism).
fn resolve(a: &mut Ship, wa: f32, b: &mut Ship, wb: f32, c: Contact) {
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
}

impl Match {
    /// Stage 10 (SIM_SPEC §5): resolve every overlapping pair of active ships.
    /// Not-yet-present and dead ships are skipped, as are parent/child pairs.
    pub fn resolve_collisions(&mut self, cat: &Catalogue) {
        let n = self.ships.len();
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
                if let Some(c) = deepest_contact(a, ha, b, hb) {
                    resolve(a, wa, b, wb, c);
                }
            }
        }
    }
}
