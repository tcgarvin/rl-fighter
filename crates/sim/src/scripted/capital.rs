//! Capital-ship pilots (v4, SIM_SPEC §11): `carrier` and `transport` roles fly to
//! the waypoint their commander set (`Match.command.waypoints`). Actuator-level like
//! every script: a heading controller through the thruster allocator and rate heads;
//! no autopilot action, no teleporting (a convoy's jump-out is a mission rule, not a
//! pilot action).
//!
//! - **Carrier** (WP-S2): a ponderous ship. It turns toward the waypoint on a
//!   rate profile sized to its own yaw authority (the turn rate it wants falls off
//!   as `sqrt(2 · α/2 · |err|)`, so it starts braking the turn in time) and holds
//!   heading with hysteresis: the RCS only switches on for a clear request
//!   (`RCS_ON_REQUEST`) and, once on, runs until the request falls into the
//!   allocator's dead zone, so it no longer chatters on and off around a held
//!   heading. The mains burn while it roughly faces the waypoint and is slower than
//!   the approach speed (`APPROACH_GAIN` per metre beyond `ARRIVE_RADIUS`, capped),
//!   with a `MAIN_HYSTERESIS` band so they do not flicker at the speed it wants. It
//!   has no reverse thrust and stops on drag (≈ 10 s time constant). Inside the
//!   arrive radius, or without a waypoint, it holds heading and coasts; it turns back
//!   from the arena edge like the strike craft. Its flak tracks the nearest enemy
//!   strike craft in reach, the enemy capital ship only when none is; power follows
//!   the shared rules.
//! - **Transport** (final, user 2026-10-30): a sitting duck. It points at its
//!   waypoint (the jump point), throttles the mains to `TRANSPORT_CRUISE_FRAC` of its
//!   speed cap and holds heading with its weak RCS (the PD below); inside
//!   `ARRIVE_RADIUS` it cuts the mains and holds heading (no orbiting a point it
//!   overshot). It never evades, never reacts to threats, keeps the balanced power
//!   split and has no guns.

use super::{
    Manoeuvre, aim_turrets, allocate_thrusters, choose_power, levels_to_throttle_heads,
    lookahead_ticks, nearest_enemy, predict, projected_levels, weapons_multiplier_after_slew,
};
use crate::DT;
use crate::actions::ShipAction;
use crate::command::Waypoint;
use crate::data::{Catalogue, HullDef};
use crate::math::{Vec2, clamp, wrap_angle};
use crate::mission::TRANSPORT_CRUISE_FRAC;
use crate::physics::ANGULAR_DRAG;
use crate::state::{MAX_THRUSTERS, Match, Ship};

/// Transport PD heading gains (torque request in `[-1, 1]`): softer and more damped
/// than the strike craft's, for hulls with ~1000× their inertia.
pub const CAPITAL_TURN_GAIN: f32 = 4.0;
pub const CAPITAL_TURN_DAMPING: f32 = 8.0;
/// A capital ship inside this distance of its waypoint has arrived: it coasts and
/// holds heading.
pub const ARRIVE_RADIUS: f32 = 25.0;
/// Approach speed per metre of distance beyond `ARRIVE_RADIUS`, 1/s. A carrier cannot
/// brake (its mains only push forward), so it stops on drag alone, which coasts
/// `v · 10 s` (`LINEAR_DRAG`); below 0.1 /s it comes to rest short of the point.
pub const APPROACH_GAIN: f32 = 0.08;
/// Burn the mains only while the waypoint is within this many radians of the nose.
pub const BURN_CONE: f32 = 0.6;
/// Beyond this fraction of the arena radius a carrier turns for the centre.
const ARENA_TURN_BACK: f32 = 0.85;

/// Carrier turn profile: it brakes a turn as if it had this fraction of its yaw
/// authority (margin for the 0.2 s ramp and the reaction delay).
const TURN_BRAKE_FRAC: f32 = 0.5;
/// Its turn rate stays under this fraction of the rate full RCS settles to.
const TURN_RATE_FRAC: f32 = 0.8;
/// A turn-rate error this many seconds of full yaw authority asks for full torque.
const TURN_RATE_TAU: f32 = 0.5;
/// Heading errors inside this band (rad) ask for no turn rate: the bearing to a
/// waypoint drifts as the ship moves, and chasing it to the last milliradian would
/// pulse the RCS every few seconds.
pub const HOLD_BAND: f32 = 0.02;
/// Turn rate wanted per radian of error beyond the hold band, 1/s (the linear part
/// of the profile near the goal heading).
const TURN_LINEAR_GAIN: f32 = 0.8;
/// With the RCS off, a torque request below this stays 0 (the allocator switches a
/// pod on above ≈ 0.21, so the band between is the hysteresis that stops the
/// on/off chatter while holding heading).
pub const RCS_ON_REQUEST: f32 = 0.4;
/// The mains come on below `want − MAIN_HYSTERESIS` (m/s) and, once on, stay on up to
/// `want`.
pub const MAIN_HYSTERESIS: f32 = 0.5;

fn turn_torque(me: &Ship, heading: f32) -> f32 {
    let err = wrap_angle(heading - me.heading);
    clamp(
        CAPITAL_TURN_GAIN * err - CAPITAL_TURN_DAMPING * me.omega,
        -1.0,
        1.0,
    )
}

/// Speed along the ship's nose.
fn forward_speed(me: &Ship) -> f32 {
    me.vel.dot(Vec2::from_angle(me.heading))
}

/// Thrusters whose push is mostly along the nose (`dir.x > MAIN_DIR_X`) are mains.
const MAIN_DIR_X: f32 = 0.5;

fn is_main(t: &crate::data::ThrusterDef) -> bool {
    t.dir.x > MAIN_DIR_X
}

/// Yaw acceleration (rad/s²) the hull's non-main thrusters give at full level and
/// the even power split, turning counter-clockwise (the RCS layouts are symmetric).
pub fn yaw_authority(hull: &HullDef) -> f32 {
    let torque: f32 = hull
        .thrusters
        .iter()
        .filter(|t| !is_main(t))
        .map(|t| (t.pos.cross(t.dir) * t.max_force).max(0.0))
        .sum();
    torque / hull.inertia
}

/// Target levels for a capital ship: the mains from the force request alone, every
/// other thruster from the torque request alone. The shared allocator would fire
/// one off-axis main to turn, which adds forward thrust a ship that cannot brake
/// does not want, and would give a transport a yaw authority it must not have.
fn capital_levels(hull: &HullDef, force_body: Vec2, torque: f32) -> [f32; MAX_THRUSTERS] {
    let push = allocate_thrusters(hull, force_body, 0.0);
    let turn = allocate_thrusters(hull, Vec2::ZERO, torque);
    let mut out = [0.0; MAX_THRUSTERS];
    for (i, t) in hull.thrusters.iter().enumerate() {
        out[i] = if is_main(t) { push[i] } else { turn[i] };
    }
    out
}

/// Throttle heads that move the projected levels to `target`.
fn heads(m: &Match, me_now: &Ship, hull: &HullDef, target: &[f32; MAX_THRUSTERS]) -> ShipAction {
    let mut action = ShipAction::IDLE;
    let projected = projected_levels(me_now, hull, m.tick);
    action.throttle = levels_to_throttle_heads(hull, &projected, target);
    action
}

/// Whether any thruster passing `which` will be firing when this action applies.
fn firing(
    m: &Match,
    me_now: &Ship,
    hull: &HullDef,
    which: fn(&crate::data::ThrusterDef) -> bool,
) -> bool {
    let projected = projected_levels(me_now, hull, m.tick);
    hull.thrusters
        .iter()
        .zip(&projected)
        .any(|(t, &level)| which(t) && level > 0.0)
}

/// The carrier's torque request toward `heading` (module docs): a turn-rate profile
/// sized to its yaw authority, with the RCS hysteresis.
fn carrier_torque(me: &Ship, hull: &HullDef, heading: f32, rcs_on: bool) -> f32 {
    let alpha = yaw_authority(hull).max(1e-6);
    let err = wrap_angle(heading - me.heading);
    // Full RCS settles where the per-tick drag loss equals the per-tick push.
    let settle = alpha * DT / (1.0 - ANGULAR_DRAG);
    // Inside the hold band it wants no turn at all; beyond it, the slower of a
    // linear ramp and the braking profile, capped.
    let off = (err.abs() - HOLD_BAND).max(0.0);
    let rate = (2.0 * TURN_BRAKE_FRAC * alpha * off)
        .sqrt()
        .min(TURN_LINEAR_GAIN * off)
        .min(TURN_RATE_FRAC * settle);
    let want = if err < 0.0 { -rate } else { rate };
    let request = clamp((want - me.omega) / (alpha * TURN_RATE_TAU), -1.0, 1.0);
    if !rcs_on && request.abs() < RCS_ON_REQUEST {
        0.0
    } else {
        request
    }
}

/// The carrier pilot's action (module docs).
pub(crate) fn carrier(m: &Match, cat: &Catalogue, me_now: &Ship, hull: &HullDef) -> ShipAction {
    let ahead = lookahead_ticks(me_now);
    let me = &predict(me_now, ahead, true);
    let mains_on = firing(m, me_now, hull, is_main);
    let rcs_on = firing(m, me_now, hull, |t| !is_main(t));
    let mut plan = Manoeuvre {
        force_body: Vec2::ZERO,
        heading: me.heading,
    };
    if let Waypoint::At(goal) = m.command.waypoints[usize::from(me.slot)] {
        let rel = goal - me.pos;
        let dist = rel.length();
        if dist > ARRIVE_RADIUS {
            plan.heading = rel.angle();
            let want = (APPROACH_GAIN * (dist - ARRIVE_RADIUS)).min(hull.speed_cap);
            let facing = wrap_angle(plan.heading - me.heading).abs() < BURN_CONE;
            let below = if mains_on {
                want
            } else {
                want - MAIN_HYSTERESIS
            };
            // At cruise the soft speed cap holds the speed, so the mains stay lit
            // rather than pulse.
            let cruise = want >= hull.speed_cap;
            if facing && (cruise || forward_speed(me) < below) {
                plan.force_body = Vec2::X;
            }
        }
    }
    if me.pos.length() > ARENA_TURN_BACK * m.cfg.arena_radius {
        plan = Manoeuvre {
            force_body: Vec2::X,
            heading: (-me.pos).angle(),
        };
    }
    let torque = carrier_torque(me, hull, plan.heading, rcs_on);
    let mut action = heads(
        m,
        me_now,
        hull,
        &capital_levels(hull, plan.force_body, torque),
    );
    let dist = nearest_enemy(m, cat, me.team, me.pos, f32::INFINITY, |_| true)
        .map_or(f32::INFINITY, |e| (e.pos - me.pos).length());
    action.power = choose_power(m, cat, me, hull, dist);
    let p_w = weapons_multiplier_after_slew(me, hull, action.power);
    aim_turrets(m, cat, me, hull, p_w, ahead, true, &mut action);
    action
}

/// The transport pilot's action (module docs): cruise at the waypoint, hold heading.
pub(crate) fn transport(m: &Match, me_now: &Ship, hull: &HullDef) -> ShipAction {
    let ahead = lookahead_ticks(me_now);
    let me = &predict(me_now, ahead, true);
    let mut plan = Manoeuvre {
        force_body: Vec2::ZERO,
        heading: me.heading,
    };
    if let Waypoint::At(goal) = m.command.waypoints[usize::from(me.slot)] {
        let rel = goal - me.pos;
        if rel.length() > ARRIVE_RADIUS {
            plan.heading = rel.angle();
            if forward_speed(me) < TRANSPORT_CRUISE_FRAC * hull.speed_cap {
                plan.force_body = Vec2::X;
            }
        }
    }
    let target = capital_levels(hull, plan.force_body, turn_torque(me, plan.heading));
    heads(m, me_now, hull, &target)
}
