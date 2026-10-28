//! Fighter pilot (`role: fighter`, SIM_SPEC §11): point the nose at the lead point and
//! burn; ease off the throttle when close and on target, and while still turning.

use super::{Engagement, Manoeuvre};
use crate::math::{Vec2, wrap_angle};
use crate::state::Ship;

/// Closer than this (and roughly on target) the fighter drops to `CLOSE_THROTTLE`.
const CLOSE_RANGE: f32 = 60.0;
/// Heading error beyond which the fighter burns hard even when close.
const REACQUIRE_ERR: f32 = 1.2;
const CLOSE_THROTTLE: f32 = 0.3;
/// Heading error beyond which most thrust is held back until the nose comes round.
const ALIGNED_ERR: f32 = 0.9;
const TURNING_THROTTLE: f32 = 0.2;

pub(crate) fn manoeuvre(me: &Ship, eng: &Engagement) -> Manoeuvre {
    let err = wrap_angle(eng.lead_heading - me.heading).abs();
    let go = if eng.dist > CLOSE_RANGE || err > REACQUIRE_ERR {
        1.0
    } else {
        CLOSE_THROTTLE
    };
    let thrust = if err < ALIGNED_ERR {
        go
    } else {
        go * TURNING_THROTTLE
    };
    Manoeuvre {
        force_body: Vec2::new(thrust, 0.0),
        heading: eng.lead_heading,
    }
}
