//! Strafer pilot (`role: skirmisher`, sim.js): circle the target at ~120 m on the
//! lateral thrusters while keeping the nose laser pointed at it.

use super::{Engagement, Manoeuvre};
use crate::math::{Vec2, clamp};
use crate::state::Ship;

/// Orbit radius, metres.
pub const ORBIT_RADIUS: f32 = 120.0;
/// Speed of the desired orbit velocity, both tangential and radial correction (m/s).
const ORBIT_SPEED: f32 = 45.0;
/// Velocity error (m/s) that asks for full thrust on an axis.
const VELOCITY_GAIN: f32 = 20.0;

/// Orbit direction: +1 (CCW around the target) for even slots, -1 for odd, so
/// wingmen split instead of stacking on one side.
pub fn orbit_sign(me: &Ship) -> f32 {
    if me.slot % 2 == 0 { 1.0 } else { -1.0 }
}

pub(crate) fn manoeuvre(me: &Ship, eng: &Engagement) -> Manoeuvre {
    // Unit vector from the target out to the ship, and the orbit tangent.
    let radial = -eng.rel_pos / eng.dist;
    let tangent = radial.perp() * orbit_sign(me);
    let radial_err = (eng.dist - ORBIT_RADIUS) / ORBIT_RADIUS;
    let want_vel = tangent * ORBIT_SPEED - radial * (radial_err * ORBIT_SPEED);
    let body = (want_vel - me.vel).rotated(-me.heading);
    Manoeuvre {
        force_body: Vec2::new(
            clamp(body.x / VELOCITY_GAIN, -1.0, 1.0),
            clamp(body.y / VELOCITY_GAIN, -1.0, 1.0),
        ),
        heading: eng.rel_pos.angle(),
    }
}
