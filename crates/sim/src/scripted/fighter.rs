//! Fighter pilot (`role: fighter`, SIM_SPEC §11): point the nose at the lead point and
//! burn, holding most thrust back while still turning; after a merge, extend.
//!
//! v2 (WP15): sim.js's fighter dropped to 0.3 throttle inside 60 m and always turned
//! straight back, so two of them parked nose to nose at 10–60 m (ship collisions kill
//! the merge) and never left gun range again. With directional armour that is a
//! nose-armour-only brawl and no passes. Now the fighter keeps full thrust when
//! aligned, and once both ships have their backs to each other it extends straight
//! out to `EXTEND_RANGE_FACTOR` × gun range before coming round: a duel becomes a
//! series of passes. A ship whose target is on its tail (pointing at it) still turns
//! to fight rather than fleeing in a straight line.

use super::{Engagement, Manoeuvre};
use crate::math::{Vec2, wrap_angle};
use crate::state::Ship;

/// Heading error beyond which most thrust is held back until the nose comes round.
const ALIGNED_ERR: f32 = 0.9;
const TURNING_THROTTLE: f32 = 0.2;
/// Extend while both the target's bearing from our nose and our bearing from its
/// nose exceed this (both ships facing away from each other).
const EXTEND_BEARING: f32 = core::f32::consts::FRAC_PI_2;
/// Extend until this multiple of the primary weapon's range, then turn back.
const EXTEND_RANGE_FACTOR: f32 = 1.2;

pub(crate) fn manoeuvre(me: &Ship, eng: &Engagement) -> Manoeuvre {
    let bearing = wrap_angle(eng.rel_pos.angle() - me.heading).abs();
    if bearing > EXTEND_BEARING
        && eng.target_aspect > EXTEND_BEARING
        && eng.dist < EXTEND_RANGE_FACTOR * eng.gun_range
    {
        return Manoeuvre {
            force_body: Vec2::X,
            heading: me.heading,
        };
    }
    let err = wrap_angle(eng.lead_heading - me.heading).abs();
    let thrust = if err < ALIGNED_ERR {
        1.0
    } else {
        TURNING_THROTTLE
    };
    Manoeuvre {
        force_body: Vec2::new(thrust, 0.0),
        heading: eng.lead_heading,
    }
}
