//! Capital-ship pilots (v4, SIM_SPEC §11): `carrier` and `transport` roles fly to
//! the waypoint their commander set (`Match.command.waypoints`). Actuator-level like
//! every script: a PD heading controller through the shared thruster allocator and
//! rate heads; no autopilot action, no teleporting (a convoy's jump-out is a mission
//! rule, not a pilot action).
//!
//! - **Carrier**: turn toward the waypoint, burn the mains while roughly facing it and
//!   slower than the approach speed (`APPROACH_GAIN` per metre, capped), coast and
//!   hold heading inside `ARRIVE_RADIUS` or without a waypoint; turn back from the
//!   arena edge like the strike craft; flak tracks the nearest threat (the shared
//!   turret aim) and power follows the shared rules. WP-S2 refines it.
//! - **Transport** (final, user 2026-10-30): a sitting duck. It points at its
//!   waypoint (the jump point), throttles the mains to `TRANSPORT_CRUISE_FRAC` of its
//!   speed cap and holds heading with its weak RCS; inside `ARRIVE_RADIUS` it cuts the
//!   mains and holds heading (no orbiting a point it overshot). It never evades, never
//!   reacts to threats, keeps the balanced power split and has no guns.

use super::{
    Manoeuvre, aim_turrets, allocate_thrusters, choose_power, levels_to_throttle_heads,
    lookahead_ticks, nearest_enemy, predict, projected_levels, weapons_multiplier_after_slew,
};
use crate::actions::ShipAction;
use crate::command::Waypoint;
use crate::data::{Catalogue, HullDef};
use crate::math::{Vec2, clamp, wrap_angle};
use crate::mission::TRANSPORT_CRUISE_FRAC;
use crate::state::{MAX_THRUSTERS, Match, Ship};

/// Capital-ship PD heading gains (torque request in `[-1, 1]`): softer and more
/// damped than the strike craft's, for hulls with ~1000× their inertia.
pub const CAPITAL_TURN_GAIN: f32 = 4.0;
pub const CAPITAL_TURN_DAMPING: f32 = 8.0;
/// A carrier inside this distance of its waypoint has arrived: it coasts and holds
/// heading.
pub const ARRIVE_RADIUS: f32 = 25.0;
/// Approach speed per metre of distance beyond `ARRIVE_RADIUS`, 1/s. A carrier cannot
/// brake (its mains only push forward), so it stops on drag alone, which coasts
/// `v · 10 s` (`LINEAR_DRAG`); below 0.1 /s it comes to rest short of the point.
pub const APPROACH_GAIN: f32 = 0.08;
/// Burn the mains only while the waypoint is within this many radians of the nose.
pub const BURN_CONE: f32 = 0.6;
/// Beyond this fraction of the arena radius a carrier turns for the centre.
const ARENA_TURN_BACK: f32 = 0.85;

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

/// Target levels for a capital ship: the mains from the force request alone, every
/// other thruster from the torque request alone. The shared allocator would fire
/// one off-axis main to turn, which adds forward thrust a ship that cannot brake
/// does not want, and would give a transport a yaw authority it must not have.
fn capital_levels(hull: &HullDef, force_body: Vec2, torque: f32) -> [f32; MAX_THRUSTERS] {
    let push = allocate_thrusters(hull, force_body, 0.0);
    let turn = allocate_thrusters(hull, Vec2::ZERO, torque);
    let mut out = [0.0; MAX_THRUSTERS];
    for (i, t) in hull.thrusters.iter().enumerate() {
        out[i] = if t.dir.x > MAIN_DIR_X {
            push[i]
        } else {
            turn[i]
        };
    }
    out
}

/// Throttle heads for `plan` from the ship's projected levels.
fn throttle(m: &Match, me_now: &Ship, me: &Ship, hull: &HullDef, plan: Manoeuvre) -> ShipAction {
    let mut action = ShipAction::IDLE;
    let target = capital_levels(hull, plan.force_body, turn_torque(me, plan.heading));
    let projected = projected_levels(me_now, hull, m.tick);
    action.throttle = levels_to_throttle_heads(hull, &projected, &target);
    action
}

/// The carrier pilot's action (module docs).
pub(crate) fn carrier(m: &Match, cat: &Catalogue, me_now: &Ship, hull: &HullDef) -> ShipAction {
    let ahead = lookahead_ticks(me_now);
    let me = &predict(me_now, ahead, true);
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
            if facing && forward_speed(me) < want {
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
    let mut action = throttle(m, me_now, me, hull, plan);
    let dist = nearest_enemy(m, cat, me.team, me.pos, f32::INFINITY, |_| true)
        .map_or(f32::INFINITY, |e| (e.pos - me.pos).length());
    action.power = choose_power(m, cat, me, hull, dist);
    let p_w = weapons_multiplier_after_slew(me, hull, action.power);
    aim_turrets(m, cat, me, hull, p_w, ahead, &mut action);
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
    throttle(m, me_now, me, hull, plan)
}
