//! Thruster forces, semi-implicit integration, drag and soft speed cap (SIM_SPEC §5.1).
//!
//! Ships have no autopilot: each thruster pushes at its mount with its throttle, and
//! turning comes only from the torque of off-centre thrusters.

use crate::DT;
use crate::data::{Catalogue, HullDef};
use crate::math::{Vec2, rot, wrap_angle};
use crate::power::{self, ENGINES};
use crate::state::Ship;

/// Per-tick linear velocity retention at 30 Hz.
pub const LINEAR_DRAG: f32 = 0.995;
/// Per-tick angular velocity retention at 30 Hz.
pub const ANGULAR_DRAG: f32 = 0.94;
/// Largest fraction of speed the soft cap removes in one tick.
pub const SOFT_CAP_MAX_CUT: f32 = 0.08;

/// Net world-frame force and torque from the ship's current throttles, scaled by the
/// engines multiplier `p_e`. Summed in thruster order.
pub fn thruster_wrench(ship: &Ship, hull: &HullDef, p_e: f32) -> (Vec2, f32) {
    let mut force_w = Vec2::ZERO;
    let mut torque = 0.0;
    for (t, &level) in hull.thrusters.iter().zip(&ship.throttle) {
        if level == 0 {
            continue;
        }
        let f = t.max_force * (f32::from(level) * 0.5) * p_e;
        let force_b = t.dir * f;
        torque += t.pos.cross(force_b);
        force_w += rot(ship.heading, force_b);
    }
    (force_w, torque)
}

/// Speed cap at engines multiplier `p_e`: `speed_cap * (0.6 + 0.4 * p_e)`.
#[inline]
pub fn speed_cap(hull: &HullDef, p_e: f32) -> f32 {
    hull.speed_cap * (0.6 + 0.4 * p_e)
}

/// Stage 5 for one ship: thrust, semi-implicit Euler, drag, soft cap, then position
/// and heading. Static hulls are never integrated; callers skip inactive ships.
pub fn integrate(ship: &mut Ship, hull: &HullDef) {
    if hull.is_static {
        return;
    }
    let p_e = power::ship_multipliers(ship, hull)[ENGINES];
    let (force_w, torque) = thruster_wrench(ship, hull, p_e);

    ship.vel += force_w / hull.mass * DT;
    ship.omega += torque / hull.inertia * DT;
    ship.vel *= LINEAR_DRAG;
    ship.omega *= ANGULAR_DRAG;

    let cap = speed_cap(hull, p_e);
    let speed = ship.vel.length();
    if speed > cap {
        let cut = ((speed - cap) / speed).min(SOFT_CAP_MAX_CUT);
        ship.vel *= 1.0 - cut;
    }

    ship.pos += ship.vel * DT;
    ship.heading = wrap_angle(ship.heading + ship.omega * DT);
}

impl crate::state::Match {
    /// Stages 3–5 of SIM_SPEC §5 for every active ship: actions, power slew, physics.
    pub fn step_motion(&mut self, cat: &Catalogue) {
        self.apply_actions(cat);
        for ship in self.ships.iter_mut().filter(|s| s.active()) {
            power::slew(&mut ship.power, ship.power_target);
            integrate(ship, cat.hull(ship.hull));
        }
    }
}
