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
//!
//! Deconfliction (v3, collision damage): pure pursuit of the lead point flies the two
//! noses into each other, and a head-on ram at ~100 m/s closing now costs both ships
//! most of their hull. So while the target is closing and the two ships would pass
//! within `SAFE_MISS` of each other within `DECONFLICT_HORIZON` (longer for a slower
//! pilot), the pilot sidesteps on its RCS toward the side the closest-approach
//! geometry already favours (starboard on an exact tie, which two scripted pilots
//! resolve as a starboard-to-starboard pass), cutting the main engine so it stops
//! pulling the pass back onto the target, and keeps the nose on the lead point so the
//! gun still bears. Inside `BREAK_TIME` of a pass that is still too close it breaks:
//! the nose swings `BREAK_ANGLE` off toward the safe side, and the main engine burns
//! once the nose is far enough off that it no longer adds closing speed.
//!
//! Meeting a target that faces it, the pilot also stops burning above
//! `HEAD_ON_SPEED`: passes at ~80 m/s closing instead of ~120 give each pass a longer
//! firing window, which a series of passes needs to get kills at the default and
//! longest reaction delays now that the nose-to-nose brawl is gone. After a pass the
//! extend is shorter (`EXTEND_RANGE_FACTOR` 0.6, was 1.2) so the pilots come round
//! inside gun range rather than leaving the fight.

use super::{Engagement, Manoeuvre};
use crate::DT;
use crate::math::{Vec2, wrap_angle};
use crate::state::Ship;

/// Heading error beyond which most thrust is held back until the nose comes round.
const ALIGNED_ERR: f32 = 0.9;
const TURNING_THROTTLE: f32 = 0.2;
/// Extend while both the target's bearing from our nose and our bearing from its
/// nose exceed this (both ships facing away from each other).
const EXTEND_BEARING: f32 = core::f32::consts::FRAC_PI_2;
/// Extend until this multiple of the primary weapon's range, then turn back (pub for
/// the scripted tests).
pub const EXTEND_RANGE_FACTOR: f32 = 0.6;

/// With a target that faces us inside this multiple of gun range, the main engine
/// stays off above `HEAD_ON_SPEED` (m/s): a slower pass is a longer firing window.
const HEAD_ON_RANGE_FACTOR: f32 = 1.5;
const HEAD_ON_SPEED: f32 = 40.0;

/// Centre-to-centre miss distance (m) the pilot wants at closest approach. Two
/// fighters touch nose to nose with centres ≈ 9 m apart, side by side ≈ 5 m.
const SAFE_MISS: f32 = 11.0;
/// Only passes whose closest approach is this soon (s) are deconflicted, plus
/// `DELAY_HORIZON_FACTOR` × the pilot's reaction delay: a slower pilot starts earlier.
const DECONFLICT_HORIZON: f32 = 1.0;
const DELAY_HORIZON_FACTOR: f32 = 4.0;
/// Only a target closing faster than this (m/s) is deconflicted.
const MIN_CLOSING: f32 = 5.0;
/// Inside this time to closest approach (s) a pass still too close becomes a break.
const BREAK_TIME: f32 = 0.35;
/// The break starts this many reaction delays earlier.
const DELAY_BREAK_FACTOR: f32 = 2.0;
/// How far the nose swings off the lead point toward the safe side in a break (rad).
const BREAK_ANGLE: f32 = 1.5;
/// In a break the main engine burns only with the target this far off the nose (rad).
const BREAK_BURN_OFF: f32 = 1.0;
/// Below this miss distance (m) the side is the tie-break, not the miss direction.
const TIE_MISS: f32 = 0.5;
/// Lateral acceleration (m/s²) a full RCS sidestep is taken to give, for scaling
/// the sidestep to what the pass needs (two pods of 160 N on 10 t at P_e ≈ 0.6).
const SIDESTEP_ACCEL: f32 = 19.0;

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
    if let Some(plan) = deconflict(me, eng) {
        return plan;
    }
    let err = wrap_angle(eng.lead_heading - me.heading).abs();
    let head_on =
        eng.target_aspect < EXTEND_BEARING && eng.dist < HEAD_ON_RANGE_FACTOR * eng.gun_range;
    let thrust = if head_on && me.vel.length() > HEAD_ON_SPEED {
        0.0
    } else if err < ALIGNED_ERR {
        1.0
    } else {
        TURNING_THROTTLE
    };
    Manoeuvre {
        force_body: Vec2::new(thrust, 0.0),
        heading: eng.lead_heading,
    }
}

/// The sidestep or break for a pass that would come within `SAFE_MISS`, if any.
///
/// Closest approach under current velocities: `t* = -(r·v) / |v|²`, miss vector
/// `r + v t*` (target relative to us). We move along `-miss`; both pilots see exactly
/// negated vectors, so they always pick opposite sides. On a tie the side is
/// `perp(v̂)`, our starboard in a head-on pass (and the target's starboard for it).
fn deconflict(me: &Ship, eng: &Engagement) -> Option<Manoeuvre> {
    let r = eng.rel_pos;
    let v = eng.rel_vel;
    let closing = -r.dot(v) / eng.dist;
    if closing < MIN_CLOSING {
        return None;
    }
    let t_cpa = -r.dot(v) / v.length_sq();
    let delay = f32::from(me.reaction_ticks) * DT;
    if t_cpa > DECONFLICT_HORIZON + DELAY_HORIZON_FACTOR * delay {
        return None;
    }
    let miss = r + v * t_cpa;
    let miss_len = miss.length();
    if miss_len >= SAFE_MISS {
        return None;
    }
    let away = if miss_len > TIE_MISS {
        -miss / miss_len
    } else {
        v.normalized().perp()
    };
    let fwd = Vec2::from_angle(me.heading);
    let side = sign_or_starboard(away.dot(fwd.perp()));
    if t_cpa < BREAK_TIME + DELAY_BREAK_FACTOR * delay {
        // The main engine only helps once the nose is well off the target; before that
        // it would add closing speed.
        let off = wrap_angle(r.angle() - me.heading).abs();
        let main = if off > BREAK_BURN_OFF { 1.0 } else { 0.0 };
        return Some(Manoeuvre {
            force_body: Vec2::new(main, side),
            heading: wrap_angle(eng.lead_heading + side * BREAK_ANGLE),
        });
    }
    // Each ship covers half the shortfall (d = a t² / 2): two scripted pilots split it.
    let need = (SAFE_MISS - miss_len) / (t_cpa * t_cpa).max(1e-3);
    let push = (need / SIDESTEP_ACCEL).min(1.0);
    Some(Manoeuvre {
        force_body: Vec2::new(0.0, side * push),
        heading: eng.lead_heading,
    })
}

/// `1` toward port (body +y) for positive `lateral`, else `-1` (starboard).
fn sign_or_starboard(lateral: f32) -> f32 {
    if lateral > 0.0 { 1.0 } else { -1.0 }
}
