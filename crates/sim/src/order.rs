//! A ship's own order (v5, SIM_SPEC §5.9 "Orders reach the pilots"): what the pilot
//! obs shows in its `order` block (§7.2) and what the order reward pays for (§8).
//!
//! - A strike craft's order is its squad's order. A capital ship with a waypoint has
//!   it as a hold of `CAPITAL_WAYPOINT_RADIUS` (for stage B′'s learned carrier); a
//!   waypoint wins over a squad (capital ships are never in squads anyway).
//! - The **effective** order drops an order that can no longer be followed at once,
//!   without waiting for the next slow tick's sanitising: an attack on a target that
//!   is no longer active (dead, jumped out) and a guard of a ward that is not on the
//!   field read as `Order::None`. The obs and the guard/hold shaping use it. The
//!   **standing** order ([`standing_order`], the squad's order as the slow tick left
//!   it) is what hit credit uses, so the hit that kills an attack target still pays.
//! - An **order instance** starts whenever a ship's effective order kind, target or
//!   point changes (a new squad order, a move to another squad, a target that died, a
//!   new waypoint). Its state, [`OrderTrack`], is per ship and hashed: the key (kind,
//!   target, point), the start tick, whether the ship has arrived, the presence ticks
//!   it has been paid for, and the last potential Φ of the shaping term.
//!
//! The tracks are refreshed at the end of every step (stage 13b, before rewards) and
//! once at setup, so the obs written after a step shows the order and its age as of
//! that step's end.

use crate::command::{Order, Waypoint};
use crate::data::Catalogue;
use crate::hash::{StateHash, StateHasher};
use crate::math::Vec2;
use crate::state::{MAX_SHIPS, Match, NONE, ShipIdx};

/// A capital ship's waypoint reads as a hold of this radius (m): the capital-ship
/// script's own arrive radius (`scripted::capital::ARRIVE_RADIUS`).
pub const CAPITAL_WAYPOINT_RADIUS: f32 = 25.0;
/// A guard is "with its ward" within this distance (m) plus the ward's bound radius:
/// the radius of the guard's obs feature, shaping, arrival and presence terms.
pub const GUARD_PRESENCE: f32 = 90.0;

/// The squad order of `slot`, or its waypoint as a hold, with no validity filter
/// (module docs): the order the ship flew under during the last step.
pub fn standing_order(m: &Match, slot: usize) -> Order {
    if let Waypoint::At(point) = m.command.waypoints[slot] {
        return Order::Hold {
            point,
            radius: CAPITAL_WAYPOINT_RADIUS,
        };
    }
    let ship = &m.ships[slot];
    m.command.squads[usize::from(ship.team & 1)]
        .iter()
        .find(|q| q.contains(slot))
        .map_or(Order::None, |q| q.order)
}

/// [`standing_order`] with orders that cannot be followed now replaced by
/// `Order::None` (module docs).
pub fn effective_order(m: &Match, slot: usize) -> Order {
    let order = standing_order(m, slot);
    let team = m.ships[slot].team;
    let ok = |s: ShipIdx, own: bool| {
        m.ships
            .get(usize::from(s))
            .is_some_and(|t| t.active() && (t.team == team) == own)
    };
    match order {
        Order::Attack { target } if !ok(target, false) => Order::None,
        Order::Guard { ward } if !ok(ward, true) => Order::None,
        o => o,
    }
}

/// Where an order points and how close counts as there: the target's position (the
/// ward's, the hold point) and the order radius (`0` for attack, `GUARD_PRESENCE` +
/// the ward's bound radius for guard, the hold radius for hold). `None` for
/// `Order::None`.
pub fn order_geometry(m: &Match, cat: &Catalogue, order: Order) -> Option<(Vec2, f32)> {
    match order {
        Order::None => None,
        Order::Attack { target } => Some((m.ships[usize::from(target)].pos, 0.0)),
        Order::Guard { ward } => {
            let w = &m.ships[usize::from(ward)];
            Some((w.pos, GUARD_PRESENCE + cat.hull(w.hull).bound_radius))
        }
        Order::Hold { point, radius } => Some((point, radius)),
    }
}

/// One ship's order instance (module docs). Hashed in field order.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct OrderTrack {
    /// `Order::kind` of the instance's order (0 none).
    pub kind: u8,
    /// Its target or ward, `NONE` for none and hold.
    pub target: ShipIdx,
    /// Its hold point, zero for the other kinds.
    pub point: Vec2,
    /// Tick the instance started.
    pub start_tick: u32,
    /// The ship has been inside the order radius during this instance (guard, hold).
    pub arrived: bool,
    /// Ticks inside the radius paid the presence term this instance.
    pub presence_ticks: u16,
    /// Potential Φ at the end of the last step (guard, hold; 0 otherwise).
    pub last_phi: f32,
}

impl Default for OrderTrack {
    fn default() -> Self {
        OrderTrack {
            kind: 0,
            target: NONE,
            point: Vec2::ZERO,
            start_tick: 0,
            arrived: false,
            presence_ticks: 0,
            last_phi: 0.0,
        }
    }
}

impl OrderTrack {
    /// Whether `order` is this instance's order (same kind, target and point; a
    /// hold's radius alone does not make a new instance).
    pub fn same_instance(&self, order: Order) -> bool {
        let point = match order {
            Order::Hold { point, .. } => point,
            _ => Vec2::ZERO,
        };
        self.kind == order.kind()
            && self.target == order.target()
            && self.point.x.to_bits() == point.x.to_bits()
            && self.point.y.to_bits() == point.y.to_bits()
    }

    /// A fresh instance of `order` starting at `tick` with potential `phi`.
    pub fn start(order: Order, tick: u32, phi: f32) -> OrderTrack {
        OrderTrack {
            kind: order.kind(),
            target: order.target(),
            point: match order {
                Order::Hold { point, .. } => point,
                _ => Vec2::ZERO,
            },
            start_tick: tick,
            arrived: false,
            presence_ticks: 0,
            last_phi: phi,
        }
    }
}

impl StateHash for OrderTrack {
    fn hash_into(&self, h: &mut StateHasher) {
        h.write_u8(self.kind);
        h.write_u8(self.target);
        h.write_vec2(self.point);
        h.write_u32(self.start_tick);
        h.write_bool(self.arrived);
        h.write_u16(self.presence_ticks);
        h.write_f32(self.last_phi);
    }
}

/// Per-slot order instances (hashed, slot order).
pub type OrderTracks = [OrderTrack; MAX_SHIPS];

impl Match {
    /// Slot `slot`'s order instance.
    pub fn order_track(&self, slot: ShipIdx) -> &OrderTrack {
        &self.order_tracks[usize::from(slot)]
    }

    /// Ticks since slot `slot`'s order instance started.
    pub fn order_age(&self, slot: ShipIdx) -> u32 {
        self.tick
            .saturating_sub(self.order_tracks[usize::from(slot)].start_tick)
    }
}
