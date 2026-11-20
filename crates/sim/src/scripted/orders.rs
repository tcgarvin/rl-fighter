//! Squad orders for the scripted strike-craft pilots (WP-S2, v6 redesign; SIM_SPEC
//! §11): which enemy an order points a pilot at, and where it flies when its order
//! has nobody to fight (a defend whose ward has no threat, a go-to on its way). These
//! are the teachers of the order-following pilots (M3 stage B3).
//!
//! - **Attack** `target`: fly at the target. Self-defence: an enemy strike craft
//!   within `SELF_DEFENCE_FACTOR` × gun range is fought first while the target is
//!   more than twice that away (a strike run does not fly through an escort's guns
//!   without shooting back). A target that died since the slow tick falls back to the
//!   role's own choice until the commander re-tasks the squad.
//! - **Defend** `ward`: engage the ward's threat set (`order` module: enemies within
//!   their own reach + margin of the ward, or that hit it recently): the recent
//!   hitters of the ward first, nearest the ward, then the rest nearest the ward. With
//!   the set empty, keep station on the ward.
//! - **Go-to** `point, radius`: fly to the point (a station on a ring inside the
//!   radius, so a squad does not stack); once the ship has arrived the order is
//!   complete (`order::completed`) and it falls back to its role.
//! - **None**: the role's own choice, exactly as before orders existed.
//! - **Dock** (v11, a ship's own order, flown in every mission): fly a funnel along the
//!   bay axis into its dock point at the carrier's velocity (`dock_approach`), engines
//!   power, its own carrier left out of crash avoidance; the bay catches it (`dock`).
//!
//! Station keeping is velocity matching: the pilot wants the ward's velocity plus a
//! pull toward its station (a point on a ring round the ward or the go-to point,
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
use crate::order;
use crate::state::{Match, Ship, ShipIdx};

/// An attack-ordered pilot fights an enemy strike craft this close (× its gun range)
/// first, while its target is more than twice as far.
pub const SELF_DEFENCE_FACTOR: f32 = 0.4;
/// Defenders keep station this far outside the ward's bound radius, metres.
pub const DEFEND_STATION: f32 = 45.0;
/// Go-to stations sit at this fraction of the go-to radius from the point.
const GOTO_STATION_FRAC: f32 = 0.5;
/// Station-keeping pull toward the station, 1/s, and its speed cap as a fraction of
/// the hull's speed cap.
const STATION_GAIN: f32 = 0.5;
const STATION_SPEED_FRAC: f32 = 0.6;
/// A go-to flies at this fraction of the hull's speed cap (it is a transit, not a
/// station to hold).
const GOTO_SPEED_FRAC: f32 = 0.9;
/// Below this missing velocity (m/s) a station keeper coasts.
const STATION_DEADBAND: f32 = 4.0;
/// Burn the main engine while the missing velocity is within this angle of the nose.
const STATION_BURN_CONE: f32 = 0.5;
/// Angle between successive slots' stations on the ring, radians (golden angle).
const STATION_SPREAD: f32 = 2.399_963;
/// v11, docking: the station point sits this fraction of the ship's distance to the
/// dock point out along the bay direction, at most `DOCK_FUNNEL_MAX` m.
const DOCK_FUNNEL: f32 = 0.5;
const DOCK_FUNNEL_MAX: f32 = 80.0;
/// v11, docking: the pull toward the funnel point, 1/s (station keeping's is 0.5).
const DOCK_GAIN: f32 = 0.8;

/// The order `me` flies by: its squad's order if it follows orders (module docs) and
/// has not completed it (a go-to it arrived at), else `Order::None`.
pub(crate) fn active_order(m: &Match, me: &Ship) -> Order {
    let team = usize::from(me.team & 1);
    let slot = usize::from(me.slot);
    // v11: a dock order is the ship's own and always flown (`dock` module).
    if m.has_dock_order(slot) {
        return order::valid_order(m, slot);
    }
    if matches!(m.cfg.mission, Mission::Deathmatch)
        && m.cfg.commanders[team] == CommanderMode::Scripted
    {
        return Order::None;
    }
    let squad = m.command.squads[team]
        .iter()
        .find(|q| q.contains(slot))
        .map_or(Order::None, |q| q.order);
    order::completed(m, slot, squad)
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

/// The member of `set` nearest `from`, preferring the slots that pass `first`; ties
/// to the lower slot.
fn nearest_in(m: &Match, set: u32, from: Vec2, first: impl Fn(usize) -> bool) -> Option<&Ship> {
    let mut best: Option<(bool, f32, usize)> = None;
    for (s, ship) in m.ships.iter().enumerate() {
        if set & (1 << s) == 0 {
            continue;
        }
        let key = (!first(s), (ship.pos - from).length(), s);
        let better = best.is_none_or(|b| (key.0, key.1) < (b.0, b.1));
        if better {
            best = Some(key);
        }
    }
    best.map(|(_, _, s)| &m.ships[s])
}

/// The threat a defender of `ward` engages (module docs): of the ward's threat set
/// among the active ships, the recent hitters of the ward first, then the rest, each
/// nearest the ward first; `None` with the set empty.
pub fn defend_target<'a>(m: &'a Match, cat: &Catalogue, ward: usize) -> Option<&'a Ship> {
    let set = m.threat_set(cat, ward, m.active_mask());
    nearest_in(m, set, m.ships[ward].pos, |e| m.recently_hit(ward, e))
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
        Order::Defend { ward } => defend_target(m, cat, usize::from(ward)),
        Order::GoTo { .. } | Order::Dock { .. } => None,
    }
}

/// Where a pilot keeps station: the point, the velocity of what it keeps station on,
/// the fraction of its speed cap it may fly at and the pull toward the point (1/s).
struct Station {
    at: Vec2,
    vel: Vec2,
    speed_frac: f32,
    gain: f32,
}

/// Where `me` keeps station under `order` (`None` for orders without a station: none,
/// attack).
fn station(m: &Match, cat: &Catalogue, me: &Ship, order: Order) -> Option<Station> {
    let ring = Vec2::from_angle(f32::from(me.slot) * STATION_SPREAD);
    match order {
        Order::Defend { ward } => {
            let w = &m.ships[usize::from(ward)];
            let r = cat.hull(w.hull).bound_radius + DEFEND_STATION;
            Some(Station {
                at: w.pos + ring * r,
                vel: w.vel,
                speed_frac: STATION_SPEED_FRAC,
                gain: STATION_GAIN,
            })
        }
        Order::GoTo { point, radius, .. } => Some(Station {
            at: point + ring * (GOTO_STATION_FRAC * radius),
            vel: Vec2::ZERO,
            speed_frac: GOTO_SPEED_FRAC,
            gain: STATION_GAIN,
        }),
        Order::Dock { carrier, bay } => Some(dock_approach(m, me, carrier, bay)),
        Order::None | Order::Attack { .. } => None,
    }
}

/// v11: where a docking pilot keeps station: a point on the bay's axis that slides in to
/// the dock point as the ship closes (`DOCK_FUNNEL` of its distance out along the bay
/// direction), so it comes in from the open side of the bay, at the dock point's
/// velocity (the carrier's), at the transit speed while far.
fn dock_approach(m: &Match, me: &Ship, carrier: ShipIdx, bay: u8) -> Station {
    let point = m.dock_point(carrier, bay);
    let c = &m.ships[usize::from(carrier)];
    let mount = m.bay_mounts[usize::from(c.team & 1)][usize::from(bay)];
    let dir = mount.dir.rotated(c.heading);
    let out = DOCK_FUNNEL * (me.pos - point).length();
    Station {
        at: point + dir * out.min(DOCK_FUNNEL_MAX),
        vel: c.vel,
        speed_frac: GOTO_SPEED_FRAC,
        gain: DOCK_GAIN,
    }
}

/// Station keeping (defend with no threat) or transit (go-to), module docs. `me` is
/// the predicted ship. Coasts with the current heading when there is no station.
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
    let Some(Station {
        at,
        vel: base_vel,
        speed_frac,
        gain,
    }) = station(m, cat, me, order)
    else {
        return coast;
    };
    let pull = (at - me.pos) * gain;
    let cap = speed_frac * hull.speed_cap;
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
