//! Collision avoidance for every strike craft (v7, SIM_SPEC §11).
//!
//! v7 makes a light ship pay for its own velocity change in a crash, so a fighter at
//! full speed into a freighter dies. The fighter's v3 deconfliction only watched its
//! target; scripted pilots kept ramming the freighters they strafed past, their own
//! capital ships and each other. Here every strike craft predicts its closest approach
//! (coasting, from the state its action applies on) to every other active ship, of
//! either team, and picks the soonest pass that would come within both bound radii
//! plus `MARGIN` while closing faster than `MIN_CLOSING`, within `HORIZON` (longer for
//! a slower pilot). The role's plan is then overridden:
//!
//! - early: sidestep along the miss direction (away from the other ship) at full
//!   lateral request, keep the role's heading, and cut the main engine while the nose
//!   points within `BURN_OFF` of the other ship (it would only add closing speed);
//! - inside `BREAK_TIME`: swing the nose halfway between the miss direction and
//!   straight away from the other ship, and burn the main engine once the nose is
//!   `BURN_OFF` off it.
//!
//! A fighter's strike-craft target keeps the v3 deconfliction (`fighter::deconflict`),
//! which knows to keep the gun bearing, and is left out here; a capital-ship target is
//! too big to sidestep that late on the RCS and is avoided here like any ship. Turret aim and fire are
//! unchanged: a pilot dodging still shoots.

use super::Manoeuvre;
use crate::DT;
use crate::damage::same_entity;
use crate::data::Catalogue;
use crate::math::{Vec2, wrap_angle};
use crate::state::{Match, Ship, ShipIdx};

/// Clearance (m) beyond both bound radii the closest approach must keep.
pub const MARGIN: f32 = 3.0;
/// Only passes closing faster than this (m/s) are avoided: slower contacts do no
/// damage (`collision::COLLISION_FREE_SPEED` is 10).
pub const MIN_CLOSING: f32 = 8.0;
/// Look this far ahead (s) for a closest approach, plus `DELAY_HORIZON_FACTOR` ×
/// the pilot's reaction delay.
pub const HORIZON: f32 = 2.5;
const DELAY_HORIZON_FACTOR: f32 = 4.0;
/// Inside this time to closest approach (s), plus `BREAK_PER_M` per metre of both
/// bound radii and `DELAY_BREAK_FACTOR` × the delay, the sidestep becomes a break. A
/// fighter cannot brake (mains forward, RCS sideways) and turns slowly, so against a
/// freighter (radii ≈ 17 m) it pulls away about 1.7 s out: a strafing run, not a ram.
pub const BREAK_TIME: f32 = 0.9;
pub const BREAK_PER_M: f32 = 0.05;
const DELAY_BREAK_FACTOR: f32 = 2.0;
/// The main engine burns only with the other ship at least this far off the nose.
const BURN_OFF: f32 = 1.0;
/// Below this miss distance (m) the side is a tie-break (starboard), not the miss.
const TIE_MISS: f32 = 0.5;

/// The soonest pass `me` (predicted `ticks` ahead) must avoid: the other ship's
/// relative position and velocity and the time to closest approach.
struct Threat {
    rel_pos: Vec2,
    rel_vel: Vec2,
    t_cpa: f32,
    miss: Vec2,
    /// Both bound radii (m).
    radii: f32,
}

/// The override for `plan` if `me` (the ship predicted `ticks` ahead) is about to
/// crash into any active ship but `skip` (the fighter's own target, or
/// `state::NONE`).
pub(crate) fn avoid(
    m: &Match,
    cat: &Catalogue,
    me: &Ship,
    ticks: u32,
    skip: ShipIdx,
    plan: Manoeuvre,
) -> Manoeuvre {
    let Some(threat) = soonest_threat(m, cat, me, ticks, skip) else {
        return plan;
    };
    let delay = f32::from(me.reaction_ticks) * DT;
    let miss_len = threat.miss.length();
    let away = if miss_len > TIE_MISS {
        -threat.miss / miss_len
    } else {
        threat.rel_vel.normalized().perp()
    };
    let off = wrap_angle(threat.rel_pos.angle() - me.heading).abs();
    let main = if off > BURN_OFF { 1.0 } else { 0.0 };
    let lateral_body = away.rotated(-me.heading).y;
    let side = if lateral_body > 0.0 { 1.0 } else { -1.0 };
    if threat.t_cpa < BREAK_TIME + BREAK_PER_M * threat.radii + DELAY_BREAK_FACTOR * delay {
        let back = -threat.rel_pos.normalized();
        return Manoeuvre {
            force_body: Vec2::new(main, side),
            heading: (away + back).angle(),
        };
    }
    let forward = if off > BURN_OFF {
        plan.force_body.x
    } else {
        0.0
    };
    Manoeuvre {
        force_body: Vec2::new(forward, side),
        heading: plan.heading,
    }
}

fn soonest_threat(
    m: &Match,
    cat: &Catalogue,
    me: &Ship,
    ticks: u32,
    skip: ShipIdx,
) -> Option<Threat> {
    let tau = ticks as f32 * DT;
    let delay = f32::from(me.reaction_ticks) * DT;
    let horizon = HORIZON + DELAY_HORIZON_FACTOR * delay;
    let my_radius = cat.hull(me.hull).bound_radius;
    let mut best: Option<Threat> = None;
    for other in m.ships.iter().filter(|o| o.active()) {
        if other.slot == skip || same_entity(me, other) {
            continue;
        }
        let rel_pos = other.pos + other.vel * tau - me.pos;
        let rel_vel = other.vel - me.vel;
        let dist = rel_pos.length().max(1e-3);
        let closing = -rel_pos.dot(rel_vel) / dist;
        if closing < MIN_CLOSING {
            continue;
        }
        let t_cpa = -rel_pos.dot(rel_vel) / rel_vel.length_sq().max(1e-6);
        if t_cpa > horizon || best.as_ref().is_some_and(|b| t_cpa >= b.t_cpa) {
            continue;
        }
        let miss = rel_pos + rel_vel * t_cpa;
        let radii = my_radius + cat.hull(other.hull).bound_radius;
        if miss.length() >= radii + MARGIN {
            continue;
        }
        best = Some(Threat {
            rel_pos,
            rel_vel,
            t_cpa,
            miss,
            radii,
        });
    }
    best
}
