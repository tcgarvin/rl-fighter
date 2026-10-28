//! Fire gating, projectile spawning and beam resolution (SIM_SPEC §5 stage 7, §6).
//!
//! RNG draw order (determinism golden traces depend on it): within stage 7, ships
//! in slot order, turrets in hull order; for each shot actually fired:
//!   1. spread: `rng.range(-1, 1)` (always drawn, even for zero-spread weapons);
//!   2. flak only: fuse jitter `rng.uniform()`.
//!
//! Nothing else in stages 6–9 consumes the match rng.

use crate::damage::{apply_damage, can_hit};
use crate::data::{Catalogue, WeaponDef, WeaponId, WeaponKind};
use crate::events::Event;
use crate::math::{Vec2, wrap_angle};
use crate::projectiles::{BROAD_PHASE_SLACK, segment_circle_entry, segment_dist};
use crate::state::{MAX_PROJECTILES, Match, NONE, Projectile, ShipIdx};
use crate::turrets::muzzle_pose;

/// Flak fuse after jitter: `round(life_ticks * (1 - fuse_jitter * u))`, at least 1.
pub fn flak_fuse_ticks(life_ticks: u32, fuse_jitter: f32, u: f32) -> u32 {
    let ticks = (life_ticks as f32 * (1.0 - fuse_jitter * u)).round() as u32;
    ticks.max(1)
}

impl Match {
    /// Stage 7 of SIM_SPEC §5 (fire). For each active, not control-locked ship (slot
    /// order) and each turret (hull order) whose pending fire head is 1 and whose
    /// cooldown is 0: reset the cooldown to `interval`, draw the spread, emit `Fire`,
    /// count the shot in `shots_fired`, then spawn the projectile or resolve the beam.
    /// See the module docs for the rng draw order.
    pub fn step_fire(&mut self, cat: &Catalogue) {
        let tick = self.tick;
        for s in 0..self.ships.len() {
            let ship = &self.ships[s];
            if !ship.active() || ship.control_locked(tick) {
                continue;
            }
            let hull = cat.hull(ship.hull);
            let action = self.pending[s];
            for (j, t) in hull.turrets.iter().enumerate() {
                if action.fire[j] != 1 || self.ships[s].turret_cooldown[j] != 0.0 {
                    continue;
                }
                let w = cat.weapon(t.weapon);
                self.ships[s].turret_cooldown[j] = w.interval;
                let spread = self.rng.range(-1.0, 1.0) * w.spread * 0.5;
                let (muzzle, base) = muzzle_pose(&self.ships[s], t, j);
                let angle = base + spread;
                self.events.push(Event::Fire {
                    ship: s as u8,
                    turret: j as u8,
                    weapon: t.weapon,
                    pos: muzzle,
                    angle,
                });
                self.shots_fired[s] = self.shots_fired[s].saturating_add(1);
                if w.kind == WeaponKind::Beam {
                    self.fire_beam(cat, s as ShipIdx, w, muzzle, angle);
                } else {
                    self.spawn_projectile(cat, s as ShipIdx, t.weapon, muzzle, angle);
                }
            }
        }
    }

    /// Write a new projectile into pool slot `proj_next` (overwriting whatever is
    /// there: oldest-first recycling) and advance `proj_next`.
    fn spawn_projectile(
        &mut self,
        cat: &Catalogue,
        owner: ShipIdx,
        weapon: WeaponId,
        muzzle: Vec2,
        angle: f32,
    ) {
        let w = cat.weapon(weapon);
        let ship = &self.ships[owner as usize];
        let dir = Vec2::from_angle(angle);
        let (vel, life_ticks, target) = match w.kind {
            WeaponKind::Torpedo => (
                dir * w.speed,
                w.life_ticks,
                self.torpedo_lock(owner, w, muzzle, angle),
            ),
            WeaponKind::Flak => {
                let u = self.rng.uniform();
                let fuse = flak_fuse_ticks(w.life_ticks, w.fuse_jitter, u);
                (ship.vel + dir * w.speed, fuse, NONE)
            }
            WeaponKind::Bullet | WeaponKind::Beam => (ship.vel + dir * w.speed, w.life_ticks, NONE),
        };
        let ship = &self.ships[owner as usize];
        self.projectiles[self.proj_next] = Projectile {
            alive: true,
            kind: w.kind,
            weapon,
            team: ship.team,
            owner,
            pos: muzzle,
            vel,
            speed: w.speed,
            damage: w.damage,
            life_ticks,
            fire_tick: self.tick,
            target,
        };
        self.proj_next = (self.proj_next + 1) % MAX_PROJECTILES;
    }

    /// Torpedo target at spawn: the hittable enemy within `range` of the muzzle and
    /// within `lock_cone / 2` of the muzzle line with the smallest angular error
    /// (lowest slot on ties); `NONE` if there is none or `lock_cone == 0`.
    fn torpedo_lock(&self, owner: ShipIdx, w: &WeaponDef, muzzle: Vec2, angle: f32) -> ShipIdx {
        if w.lock_cone <= 0.0 {
            return NONE;
        }
        let shooter = &self.ships[owner as usize];
        let half_cone = 0.5 * w.lock_cone;
        let mut best = NONE;
        let mut best_err = f32::INFINITY;
        for s in self
            .ships
            .iter()
            .filter(|s| can_hit(shooter.team, shooter, s))
        {
            let rel = s.pos - muzzle;
            if rel.length() > w.range {
                continue;
            }
            let err = wrap_angle(rel.angle() - angle).abs();
            if err <= half_cone && err < best_err {
                best = s.slot;
                best_err = err;
            }
        }
        best
    }

    /// Hitscan beam from `muzzle` along `angle` for `range`: the nearest entry into
    /// any hittable enemy's collision circle (lowest slot on ties) takes the damage
    /// now. Emits `Beam` (to the hit point, or full range on a miss), then the hit.
    fn fire_beam(
        &mut self,
        cat: &Catalogue,
        owner: ShipIdx,
        w: &WeaponDef,
        muzzle: Vec2,
        angle: f32,
    ) {
        let end = muzzle + Vec2::from_angle(angle) * w.range;
        let shooter = &self.ships[owner as usize];
        let mut best: Option<(f32, ShipIdx)> = None;
        for s in self
            .ships
            .iter()
            .filter(|s| can_hit(shooter.team, shooter, s))
        {
            let hull = cat.hull(s.hull);
            if segment_dist(muzzle, end, s.pos) >= hull.bound_radius + BROAD_PHASE_SLACK {
                continue;
            }
            for c in &hull.collision {
                if let Some(t) = segment_circle_entry(muzzle, end, s.to_world(c.pos), c.r) {
                    if best.is_none_or(|(bt, _)| t < bt) {
                        best = Some((t, s.slot));
                    }
                }
            }
        }
        let to = best.map_or(end, |(t, _)| muzzle + (end - muzzle) * t);
        self.events.push(Event::Beam {
            ship: owner,
            from: muzzle,
            to,
            hit: best.is_some(),
        });
        if let Some((_, target)) = best {
            apply_damage(self, cat, target, w.damage, to, owner, self.tick);
        }
    }
}
