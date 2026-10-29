//! Turret slew, cooldown and muzzle pose (SIM_SPEC §5 stage 6, stage 7 muzzle).

use crate::DT;
use crate::data::{Catalogue, TurretDef};
use crate::math::{Vec2, clamp};
use crate::power::{self, WEAPONS};
use crate::state::{Match, Ship};

/// Fraction of real time a turret's cooldown runs at, before the weapons multiplier:
/// cooldown drops by `DT * COOLDOWN_RATE * P_w` per tick.
pub const COOLDOWN_RATE: f32 = 0.65;

/// A turret cooldown after one stage-6 tick at weapons multiplier `p_w`:
/// `max(0, cooldown - DT * COOLDOWN_RATE * p_w)`. The single formula for both the
/// sim and the scripted controller's "ready to fire this tick" gate.
#[inline]
pub fn cooldown_after_tick(cooldown: f32, p_w: f32) -> f32 {
    (cooldown - DT * COOLDOWN_RATE * p_w).max(0.0)
}

/// `cooldown_after_tick` applied `ticks` times at a constant `p_w`: bit-exact with
/// the sim's per-tick update, so the scripted controller can ask whether a gun will be
/// ready on the tick its action applies (`d + 1` ticks ahead, v2).
#[inline]
pub fn cooldown_after_ticks(cooldown: f32, p_w: f32, ticks: u32) -> f32 {
    let mut c = cooldown;
    for _ in 0..ticks {
        if c == 0.0 {
            break;
        }
        c = cooldown_after_tick(c, p_w);
    }
    c
}

/// Turret-angle limits `[rest - arc/2, rest + arc/2]` (body frame, not wrapped).
#[inline]
pub fn arc_limits(t: &TurretDef) -> (f32, f32) {
    (t.rest - 0.5 * t.arc, t.rest + 0.5 * t.arc)
}

/// World-frame muzzle position and the un-spread firing angle of turret `j`.
#[inline]
pub fn muzzle_pose(ship: &Ship, t: &TurretDef, j: usize) -> (Vec2, f32) {
    (ship.to_world(t.pos), ship.heading + ship.turret_angle[j])
}

impl Match {
    /// Stage 6 of SIM_SPEC §5 (turrets), for every active ship: slewing turrets
    /// (`arc > 0`) move by `slew_sign * slew_rate * DT` from the applied action (v2:
    /// `LOCKED` while locked, so they hold) and clamp to their arc; every turret's
    /// cooldown drops by `DT * 0.65 * P_w`, floored at 0. Fixed guns ignore slew.
    pub fn step_turrets(&mut self, cat: &Catalogue) {
        for ship in self.ships.iter_mut().filter(|s| s.active()) {
            let hull = cat.hull(ship.hull);
            let action = self.applied[ship.slot as usize];
            let p_w = power::ship_multipliers(ship, hull)[WEAPONS];
            for (j, t) in hull.turrets.iter().enumerate() {
                if t.arc > 0.0 {
                    let (lo, hi) = arc_limits(t);
                    let angle = ship.turret_angle[j] + action.slew_sign(j) * t.slew_rate * DT;
                    ship.turret_angle[j] = clamp(angle, lo, hi);
                }
                ship.turret_cooldown[j] = cooldown_after_tick(ship.turret_cooldown[j], p_w);
            }
        }
    }
}
