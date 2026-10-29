//! apply_damage (shield, then hull), same_entity, and shield regen (SIM_SPEC §5.4,
//! §5 stage 9, §3.4).
//!
//! Damage only lowers `hp` / `shield`; it never flips `alive`. Deaths are resolved
//! in stage 12 so that simultaneous kills are symmetric.

use crate::DT;
use crate::TICK_HZ;
use crate::data::Catalogue;
use crate::events::{Event, HitRecord};
use crate::math::Vec2;
use crate::power::{self, SHIELDS};
use crate::state::{Match, NEVER, Ship, ShipIdx};

/// Whether `a` and `b` are the same physical entity: the same ship, or one is the
/// other's parent (a docked/mounted child, M5+). Every hit path and the collision
/// pass skip such pairs (SIM_SPEC §3.4). Always just `a.slot == b.slot` in M1.
#[inline]
pub fn same_entity(a: &Ship, b: &Ship) -> bool {
    a.slot == b.slot || a.parent == b.slot || b.parent == a.slot
}

/// Whether a hit from `shooter`'s side may land on `target`: target active, on the
/// other team (no friendly fire), and not the same entity as the shooter.
#[inline]
pub fn can_hit(shooter_team: u8, shooter: &Ship, target: &Ship) -> bool {
    target.active() && target.team != shooter_team && !same_entity(shooter, target)
}

/// Apply `amount` damage to `target` at world point `point` from `shooter`, fired
/// on `fire_tick` from an action chosen at `decision_tick` (SIM_SPEC §5.4). A raised
/// shield takes the whole hit (absorbed amount scaled by `1 / (0.7 + 0.3 * P_s)`, no overflow to hull) and emits
/// `ShieldHit`; otherwise hull `hp` drops and `Hit` is emitted. Either way one
/// `HitRecord` with the raw `amount` is recorded.
#[allow(clippy::too_many_arguments)]
pub fn apply_damage(
    m: &mut Match,
    cat: &Catalogue,
    target: ShipIdx,
    amount: f32,
    point: Vec2,
    shooter: ShipIdx,
    fire_tick: u32,
    decision_tick: u32,
) {
    let tick = m.tick;
    let ship = &mut m.ships[target as usize];
    let hull = cat.hull(ship.hull);
    ship.last_hit_tick = tick;
    let shield_hit = ship.shield > 0.0;
    let event = if shield_hit {
        let p_s = power::ship_multipliers(ship, hull)[SHIELDS];
        let absorbed = amount / (0.7 + 0.3 * p_s);
        ship.shield = (ship.shield - absorbed).max(0.0);
        let n = (point - ship.pos).normalized();
        let n = if n == Vec2::ZERO { Vec2::X } else { n };
        Event::ShieldHit {
            target,
            shooter,
            pos: ship.pos + n * hull.shield_radius,
            normal: n,
            depleted: ship.shield == 0.0,
        }
    } else {
        ship.hp -= amount;
        Event::Hit {
            target,
            shooter,
            pos: point,
            damage: amount,
        }
    };
    m.events.push(event);
    m.push_hit(HitRecord {
        shooter,
        target,
        damage: amount,
        fire_tick,
        decision_tick,
        shield: shield_hit,
    });
}

/// Ticks without hits before a shield regenerates: `round(regen_delay * 30 / P_s)`.
pub fn regen_delay_ticks(regen_delay: f32, p_s: f32) -> u32 {
    (regen_delay * TICK_HZ / p_s).round() as u32
}

impl Match {
    /// Stage 9 of SIM_SPEC §5 (shield regen). For each active ship with a shield:
    /// once `tick - last_hit_tick >= round(regen_delay * 30 / P_s)`, regenerate
    /// `regen_rate * P_s * DT`, capped at the shield's max. Never-hit ships regen.
    pub fn step_shield_regen(&mut self, cat: &Catalogue) {
        let tick = self.tick;
        for ship in self.ships.iter_mut().filter(|s| s.active()) {
            let hull = cat.hull(ship.hull);
            let Some(def) = hull.shield else { continue };
            let p_s = power::ship_multipliers(ship, hull)[SHIELDS];
            let since = if ship.last_hit_tick == NEVER {
                u32::MAX
            } else {
                tick.saturating_sub(ship.last_hit_tick)
            };
            if since >= regen_delay_ticks(def.regen_delay, p_s) {
                ship.shield = (ship.shield + def.regen_rate * p_s * DT).min(def.hp);
            }
        }
    }
}
