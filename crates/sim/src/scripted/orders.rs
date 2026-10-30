//! Squad orders for the scripted strike-craft pilots (WP-S2, SIM_SPEC §11): which
//! enemy an order points a pilot at, and where it flies when its order has nobody to
//! fight (a guard with no threat near its ward, a hold with nobody near its point).
//!
//! - **Attack** `target`: fly at the target. Self-defence: an enemy strike craft
//!   within `SELF_DEFENCE_FACTOR` × gun range is fought first while the target is
//!   more than twice that away (a strike run does not fly through an escort's guns
//!   without shooting back). A target that died since the slow tick falls back to the
//!   role's own choice until the commander re-tasks the squad.
//! - **Guard** `ward`: the enemy nearest the ward within `GUARD_RADIUS` (plus the
//!   ward's size) of it; with none, keep station on the ward.
//! - **Hold** `point, radius`: the enemy nearest the point within `radius +
//!   HOLD_REACH`; with none, keep station on the point.
//! - **None**: the role's own choice, exactly as before orders existed.
//!
//! Station keeping is velocity matching: the pilot wants the ward's velocity plus a
//! pull toward its station (a point on a ring round the ward or the hold point,
//! spread by slot so a squad does not stack), turns its nose along the velocity it
//! is missing and burns while roughly aligned.
//!
//! **Who follows orders.** Every scripted pilot whose squad has an order, except in a
//! deathmatch flown under the scripted commander: there the commander's orders are
//! advisory (the command overlay shows them), so the default deathmatch, the fleet
//! pilot's training and eval opponent and the v3 golden traces, is unchanged. An
//! external or (v5) random commander's orders are followed in every mission (stage B
//! trains on them).

use super::Manoeuvre;
use crate::command::{CommanderMode, Order};
use crate::data::{Catalogue, HullDef};
use crate::math::{Vec2, wrap_angle};
use crate::mission::{Mission, is_capital_ship};
use crate::state::{Match, Ship};

/// An attack-ordered pilot fights an enemy strike craft this close (× its gun range)
/// first, while its target is more than twice as far.
pub const SELF_DEFENCE_FACTOR: f32 = 0.4;
/// A guard engages enemies within this distance of its ward (plus the ward's bound
/// radius), metres.
pub const GUARD_RADIUS: f32 = 180.0;
/// A hold engages enemies within its radius plus this, metres.
pub const HOLD_REACH: f32 = 120.0;
/// Guards keep station this far outside the ward's bound radius, metres.
pub const GUARD_STATION: f32 = 45.0;
/// Hold stations sit at this fraction of the hold radius from the point.
const HOLD_STATION_FRAC: f32 = 0.5;
/// Station-keeping pull toward the station, 1/s, and its speed cap as a fraction of
/// the hull's speed cap.
const STATION_GAIN: f32 = 0.5;
const STATION_SPEED_FRAC: f32 = 0.6;
/// Below this missing velocity (m/s) a station keeper coasts.
const STATION_DEADBAND: f32 = 4.0;
/// Burn the main engine while the missing velocity is within this angle of the nose.
const STATION_BURN_CONE: f32 = 0.5;
/// Angle between successive slots' stations on the ring, radians (golden angle).
const STATION_SPREAD: f32 = 2.399_963;

/// The order `me` flies by: its squad's order if it follows orders (module docs),
/// else `Order::None`.
pub(crate) fn active_order(m: &Match, me: &Ship) -> Order {
    let team = usize::from(me.team & 1);
    if matches!(m.cfg.mission, Mission::Deathmatch)
        && m.cfg.commanders[team] == CommanderMode::Scripted
    {
        return Order::None;
    }
    let slot = usize::from(me.slot);
    m.command.squads[team]
        .iter()
        .find(|q| q.contains(slot))
        .map_or(Order::None, |q| q.order)
}

/// Nearest active enemy of `me` to `from` within `reach` whose hull passes `keep`;
/// ties to the lower slot.
fn nearest_to<'a>(
    m: &'a Match,
    cat: &Catalogue,
    me: &Ship,
    from: Vec2,
    reach: f32,
    keep: impl Fn(&HullDef) -> bool,
) -> Option<&'a Ship> {
    let mut best = None;
    let mut best_d = reach;
    for s in &m.ships {
        if !s.active() || s.team == me.team || !keep(cat.hull(s.hull)) {
            continue;
        }
        let d = (s.pos - from).length();
        if d < best_d {
            best_d = d;
            best = Some(s);
        }
    }
    best
}

/// The enemy `order` points `me` at, or `None` when it has nobody to fight (keep
/// station, [`station_manoeuvre`]). `fallback` is the role's own choice, used when an
/// attack target died since the slow tick. Never called with `Order::None`.
pub(crate) fn order_target<'a>(
    m: &'a Match,
    cat: &Catalogue,
    me: &Ship,
    gun_range: f32,
    order: Order,
    fallback: impl FnOnce() -> Option<&'a Ship>,
) -> Option<&'a Ship> {
    match order {
        Order::None => fallback(),
        Order::Attack { target } => {
            let t = &m.ships[usize::from(target)];
            if !t.active() || t.team == me.team {
                return fallback();
            }
            let guard_dist = SELF_DEFENCE_FACTOR * gun_range;
            if (t.pos - me.pos).length() > 2.0 * guard_dist {
                let strike = |h: &HullDef| !is_capital_ship(h);
                if let Some(near) = nearest_to(m, cat, me, me.pos, guard_dist, strike) {
                    return Some(near);
                }
            }
            Some(t)
        }
        Order::Guard { ward } => {
            let w = &m.ships[usize::from(ward)];
            let reach = GUARD_RADIUS + cat.hull(w.hull).bound_radius;
            nearest_to(m, cat, me, w.pos, reach, |_| true)
        }
        Order::Hold { point, radius } => {
            nearest_to(m, cat, me, point, radius + HOLD_REACH, |_| true)
        }
    }
}

/// Where `me` keeps station under `order`, and the velocity of what it keeps station
/// on. `None` for orders without a station (none, attack).
fn station(m: &Match, cat: &Catalogue, me: &Ship, order: Order) -> Option<(Vec2, Vec2)> {
    let ring = Vec2::from_angle(f32::from(me.slot) * STATION_SPREAD);
    match order {
        Order::Guard { ward } => {
            let w = &m.ships[usize::from(ward)];
            let r = cat.hull(w.hull).bound_radius + GUARD_STATION;
            Some((w.pos + ring * r, w.vel))
        }
        Order::Hold { point, radius } => {
            Some((point + ring * (HOLD_STATION_FRAC * radius), Vec2::ZERO))
        }
        Order::None | Order::Attack { .. } => None,
    }
}

/// Station keeping for an order with nobody to fight (module docs). `me` is the
/// predicted ship. Coasts with the current heading when there is no station.
pub(crate) fn station_manoeuvre(
    m: &Match,
    cat: &Catalogue,
    me: &Ship,
    hull: &HullDef,
    order: Order,
) -> Manoeuvre {
    let coast = Manoeuvre {
        force_body: Vec2::ZERO,
        heading: me.heading,
    };
    let Some((at, base_vel)) = station(m, cat, me, order) else {
        return coast;
    };
    let pull = (at - me.pos) * STATION_GAIN;
    let cap = STATION_SPEED_FRAC * hull.speed_cap;
    let pull = if pull.length() > cap {
        pull.normalized() * cap
    } else {
        pull
    };
    let missing = base_vel + pull - me.vel;
    if missing.length() < STATION_DEADBAND {
        return coast;
    }
    let heading = missing.angle();
    let aligned = wrap_angle(heading - me.heading).abs() < STATION_BURN_CONE;
    Manoeuvre {
        force_body: Vec2::new(if aligned { 1.0 } else { 0.0 }, 0.0),
        heading,
    }
}
