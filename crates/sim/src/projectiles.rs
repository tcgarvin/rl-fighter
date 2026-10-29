//! Projectile advance, torpedo steering, swept hit tests and flak bursts
//! (SIM_SPEC §5 stage 8, §5.3), plus the segment/circle geometry shared with beams.

use crate::DT;
use crate::damage::{apply_damage, can_hit};
use crate::data::{Catalogue, WeaponKind};
use crate::events::Event;
use crate::math::{Vec2, clamp, wrap_angle};
use crate::state::{MAX_PROJECTILES, Match, NONE, Projectile, Ship, ShipIdx};

/// Slack added to `bound_radius` in the swept broad phase.
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

/// Swept test of a projectile moving `from → to` against `ship`'s compound circles:
/// broad phase on `bound_radius + 0.5`, then each collision circle in hull order.
/// Returns the hit point (closest point on the segment to the first circle hit).
pub fn swept_hit(cat: &Catalogue, ship: &Ship, from: Vec2, to: Vec2) -> Option<Vec2> {
    let hull = cat.hull(ship.hull);
    if segment_dist(from, to, ship.pos) >= hull.bound_radius + BROAD_PHASE_SLACK {
        return None;
    }
    hull.collision.iter().find_map(|c| {
        let centre = ship.to_world(c.pos);
        segment_hits_circle(from, to, centre, c.r).then(|| closest_point(from, to, centre))
    })
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
    /// ship with `|ship.pos - at| < burst_radius + bound_radius`, in slot order.
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
            let reach = burst_radius + cat.hull(s.hull).bound_radius;
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
