//! Gunship pilot (`role: anchor`, sim.js): close to a ~170 m standoff, then turn
//! broadside so both side turrets bear while the fore flak covers the bow.

use super::{Engagement, Manoeuvre};
use crate::math::{PI, Vec2};

/// Preferred range to the target, metres.
pub const STANDOFF: f32 = 170.0;
/// Forward thrust request while closing to standoff.
const CLOSE_THRUST: f32 = 0.8;
/// Request when inside `TOO_CLOSE * STANDOFF`. The gunship has no reverse thrusters,
/// so the allocator fires nothing for it: as in sim.js, it simply stops pushing in.
const BACK_OFF_THRUST: f32 = -0.3;
const TOO_CLOSE: f32 = 0.7;
/// Within this multiple of standoff the gunship turns its side to the target.
const BROADSIDE_RANGE: f32 = 1.2;

pub(crate) fn manoeuvre(eng: &Engagement) -> Manoeuvre {
    let go = if eng.dist > STANDOFF {
        CLOSE_THRUST
    } else if eng.dist < STANDOFF * TOO_CLOSE {
        BACK_OFF_THRUST
    } else {
        0.0
    };
    let bearing = eng.rel_pos.angle();
    // Heading = bearing + 90°: the target sits on the starboard beam.
    let heading = if eng.dist < STANDOFF * BROADSIDE_RANGE {
        bearing + 0.5 * PI
    } else {
        bearing
    };
    Manoeuvre {
        force_body: Vec2::new(go, 0.0),
        heading,
    }
}
