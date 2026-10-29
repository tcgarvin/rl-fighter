//! Throttle ramp, thruster forces, semi-implicit integration, drag and soft speed cap
//! (SIM_SPEC §5.1).
//!
//! Ships have no autopilot: each thruster pushes at its mount with its current thrust
//! level, which the action ramps down/holds/up (stage 3), and turning comes only from
//! the torque of off-centre thrusters.

use crate::DT;
use crate::actions::THROTTLE_HOLD;
use crate::data::{Catalogue, HullDef};
use crate::math::{Vec2, clamp, rot, wrap_angle};
use crate::power::{self, ENGINES};
use crate::state::Ship;

/// Per-tick linear velocity retention at 30 Hz: `1 - 0.005 * 2/3` (v2; v1 0.995),
/// a time constant of about 10 s.
pub const LINEAR_DRAG: f32 = 0.996_666_7;
/// Per-tick angular velocity retention at 30 Hz: `1 - 0.06 * 2/3` (v2; v1 0.94),
/// a time constant of about 0.8 s.
pub const ANGULAR_DRAG: f32 = 0.96;
/// Thrust-level change per second of `INCREASE` / `DECREASE` (v2): 0 → 1 in 0.2 s.
pub const RAMP_RATE: f32 = 5.0;
/// Thrust-level change per tick, `RAMP_RATE * DT` (1/6).
pub const RAMP_STEP: f32 = RAMP_RATE * DT;
/// Largest fraction of speed the soft cap removes in one tick.
pub const SOFT_CAP_MAX_CUT: f32 = 0.08;

/// One tick of the throttle ramp (stage 3): `clamp(level + (head - 1) * RAMP_STEP,
/// 0, 1)` for throttle head `head` (decrease / hold / increase).
#[inline]
pub fn ramp_level(level: f32, head: u8) -> f32 {
    let delta = f32::from(head) - f32::from(THROTTLE_HOLD);
    clamp(level + delta * RAMP_STEP, 0.0, 1.0)
}

/// Net world-frame force and torque from the ship's current thrust levels, scaled by
/// the engines multiplier `p_e`: `f = max_force * level * p_e` per thruster, summed in
/// thruster order.
pub fn thruster_wrench(ship: &Ship, hull: &HullDef, p_e: f32) -> (Vec2, f32) {
    let mut force_w = Vec2::ZERO;
    let mut torque = 0.0;
    for (t, &level) in hull.thrusters.iter().zip(&ship.thrust_level) {
        if level == 0.0 {
            continue;
        }
        let f = t.max_force * level * p_e;
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
