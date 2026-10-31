//! A ship's own order (v5, v6 redesign; SIM_SPEC §5.9 "Orders reach the pilots"): what
//! the pilot obs shows in its `order` block (§7.2) and what the order reward pays for
//! (§8). v6 orders are attack, defend (was guard), go-to (replaces hold) and none.
//!
//! - A strike craft's order is its squad's order. A capital ship with a waypoint has
//!   it as a go-to of `CAPITAL_WAYPOINT_RADIUS` (for stage B′'s learned carrier); a
//!   waypoint wins over a squad (capital ships are never in squads anyway).
//! - The **standing** order ([`standing_order`]) is the squad's order as the slow tick
//!   left it. Hit credit and the defend penalties use it, so the hit that kills an
//!   attack target still pays and a defender pays for its ward's death.
//! - The **valid** order ([`valid_order`]) drops what can no longer be followed at
//!   once, without waiting for the next slow tick's sanitising: an attack on a target
//!   that is no longer active (dead, jumped out) and a defend of a ward that is not on
//!   the field read as `Order::None`.
//! - The **effective** order ([`effective_order`]) is the valid order, except that a
//!   go-to **completes per ship on arrival**: once the ship has been inside the radius
//!   during the instance, its effective order is none (obs `has_order = 0`, no order
//!   reward, the script falls back to its role) while the squad's standing order lasts
//!   until the commander changes it. The obs, the go-to shaping and the scripts use it.
//! - An **order instance** starts whenever a ship's standing order kind or target
//!   changes, or a go-to point moves more than `GOTO_SAME_POINT` from the instance's
//!   first point (a re-issued point within it is the same instance and pays nothing
//!   twice). v6 keys instances on the standing order, so a target or ward that dies
//!   does not start one (v5 keyed them on the valid order). Its state, [`OrderTrack`], is per ship and hashed: the key (kind, target,
//!   point), the start tick, whether the ship has arrived (go-to) and the last
//!   potential Φ of the shaping term.
//! - A ward's **threat set** ([`Match::threat_set`]): the enemies within their own
//!   longest weapon range + `THREAT_MARGIN` + the ward's bound radius of the ward, or
//!   that damaged the ward in the last `RECENT_HIT_TICKS` ticks (`Match.hit_by`,
//!   hashed). No fixed radius: a gunship's torpedo outranges any fixed guard ring.
//!
//! The tracks and `hit_by` are refreshed at the end of every step (stage 13b, before
//! rewards), the tracks also once at setup, so the obs written after a step shows the
//! order and its age as of that step's end.

use crate::command::{Order, Waypoint};
use crate::data::{Catalogue, HullDef};
use crate::hash::{StateHash, StateHasher};
use crate::math::Vec2;
use crate::mission::{ROLE_CARRIER, ROLE_TRANSPORT};
use crate::state::{MAX_SHIPS, Match, NONE, ShipIdx};

/// A capital ship's waypoint reads as a go-to of this radius (m): the capital-ship
/// script's own arrive radius (`scripted::capital::ARRIVE_RADIUS`).
pub const CAPITAL_WAYPOINT_RADIUS: f32 = 25.0;
/// A go-to point re-issued within this distance (m) of the instance's point is the
/// same instance (no second arrival bonus, still complete if arrived).
pub const GOTO_SAME_POINT: f32 = 40.0;
/// Threat set: an enemy within its own longest weapon range plus this (m) plus the
/// ward's bound radius threatens the ward.
pub const THREAT_MARGIN: f32 = 40.0;
/// Threat set: an enemy that damaged the ward within this many ticks (5 s) threatens
/// it wherever it is.
pub const RECENT_HIT_TICKS: u32 = 150;

/// Hull classes of the obs `ship_extras` one-hot, in its order (SIM_SPEC §7.2).
pub const HULL_CLASSES: [&str; 6] = [
    "fighter",
    "strafer",
    "gunship",
    "carrier",
    "freighter",
    "spare",
];
/// Number of hull classes (the one-hot's width).
pub const N_HULL_CLASSES: usize = HULL_CLASSES.len();

/// The obs hull class of `hull`, from its catalogue role (index into
/// [`HULL_CLASSES`]): fighter, skirmisher (strafer), anchor (gunship), carrier,
/// transport (freighter); any other role is the spare class.
pub fn hull_class(hull: &HullDef) -> u8 {
    match hull.role.as_str() {
        "fighter" => 0,
        "skirmisher" => 1,
        "anchor" => 2,
        ROLE_CARRIER => 3,
        ROLE_TRANSPORT => 4,
        _ => 5,
    }
}

/// The longest weapon range of `hull` (m), 0 without turrets.
pub fn hull_reach(cat: &Catalogue, hull: &HullDef) -> f32 {
    hull.turrets
        .iter()
        .map(|t| cat.weapon(t.weapon).range)
        .fold(0.0, f32::max)
}

/// The squad order of `slot`, or its waypoint as a go-to, with no validity filter
/// (module docs): the order the ship flew under during the last step.
pub fn standing_order(m: &Match, slot: usize) -> Order {
    if let Waypoint::At(point) = m.command.waypoints[slot] {
        return Order::GoTo {
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
/// `Order::None` (module docs). Order instances are keyed on it.
pub fn valid_order(m: &Match, slot: usize) -> Order {
    let order = standing_order(m, slot);
    let team = m.ships[slot].team;
    let ok = |s: ShipIdx, own: bool| {
        m.ships
            .get(usize::from(s))
            .is_some_and(|t| t.active() && (t.team == team) == own)
    };
    match order {
        Order::Attack { target } if !ok(target, false) => Order::None,
        Order::Defend { ward } if !ok(ward, true) => Order::None,
        o => o,
    }
}

/// [`valid_order`] with a go-to the ship has completed (arrived during its instance)
/// replaced by `Order::None` (module docs).
pub fn effective_order(m: &Match, slot: usize) -> Order {
    let order = valid_order(m, slot);
    completed(m, slot, order)
}

/// `order` (the slot's valid or squad order), or `Order::None` if it is a go-to whose
/// current instance the ship has arrived in.
pub fn completed(m: &Match, slot: usize, order: Order) -> Order {
    let track = &m.order_tracks[slot];
    match order {
        Order::GoTo { .. } if track.arrived && track.same_instance(order) => Order::None,
        o => o,
    }
}

/// Where an order points: the target's position (the ward's, the go-to point), and
/// its radius (the go-to radius; `0` for attack and defend). `None` for
/// `Order::None`.
pub fn order_geometry(m: &Match, order: Order) -> Option<(Vec2, f32)> {
    match order {
        Order::None => None,
        Order::Attack { target } => Some((m.ships[usize::from(target)].pos, 0.0)),
        Order::Defend { ward } => Some((m.ships[usize::from(ward)].pos, 0.0)),
        Order::GoTo { point, radius } => Some((point, radius)),
    }
}

/// One ship's order instance (module docs). Hashed in field order.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct OrderTrack {
    /// `Order::kind` of the instance's order (0 none).
    pub kind: u8,
    /// Its target or ward, `NONE` for none and go-to.
    pub target: ShipIdx,
    /// Its go-to point when the instance started, zero for the other kinds.
    pub point: Vec2,
    /// Tick the instance started.
    pub start_tick: u32,
    /// Go-to: the ship has been inside the radius during this instance (it is
    /// complete).
    pub arrived: bool,
    /// Potential Φ at the end of the last step (go-to; 0 otherwise).
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
            last_phi: 0.0,
        }
    }
}

impl OrderTrack {
    /// Whether `order` is this instance's order: same kind and target and, for a
    /// go-to, a point within `GOTO_SAME_POINT` of the instance's (a radius alone does
    /// not make a new instance).
    pub fn same_instance(&self, order: Order) -> bool {
        if self.kind != order.kind() || self.target != order.target() {
            return false;
        }
        match order {
            Order::GoTo { point, .. } => (point - self.point).length() <= GOTO_SAME_POINT,
            _ => true,
        }
    }

    /// A fresh instance of `order` starting at `tick` with potential `phi`.
    pub fn start(order: Order, tick: u32, phi: f32) -> OrderTrack {
        OrderTrack {
            kind: order.kind(),
            target: order.target(),
            point: match order {
                Order::GoTo { point, .. } => point,
                _ => Vec2::ZERO,
            },
            start_tick: tick,
            arrived: false,
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
        h.write_f32(self.last_phi);
    }
}

/// Per-slot order instances (hashed, slot order).
pub type OrderTracks = [OrderTrack; MAX_SHIPS];

/// v6, `[ward][hitter]`: the tick `hitter` last damaged `ward` (hull or shield), 0 for
/// never (hashed). Hits land on ticks ≥ 1, so 0 is free as the sentinel.
pub type HitBy = [[u32; MAX_SHIPS]; MAX_SHIPS];

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

    /// Whether `hitter` damaged `ward` in the last `RECENT_HIT_TICKS` ticks.
    pub fn recently_hit(&self, ward: usize, hitter: usize) -> bool {
        let t = self.hit_by[ward][hitter];
        t != 0 && self.tick.saturating_sub(t) < RECENT_HIT_TICKS
    }

    /// The threat set of ship `ward` (bit `e` = slot `e`) among `candidates`, the
    /// slots that may count (the caller's notion of "on the field"): enemies of the
    /// ward within their own reach + `THREAT_MARGIN` + the ward's bound radius of it,
    /// or that hit it recently (module docs). `ship_reach` is the per-slot longest
    /// weapon range (`Match.ship_reach`).
    pub fn threat_set(&self, cat: &Catalogue, ward: usize, candidates: u32) -> u32 {
        let w = &self.ships[ward];
        let bound = cat.hull(w.hull).bound_radius;
        let mut set = 0u32;
        for (e, ship) in self.ships.iter().enumerate() {
            if candidates & (1 << e) == 0 || ship.team == w.team {
                continue;
            }
            let reach = self.ship_reach[e] + THREAT_MARGIN + bound;
            if (ship.pos - w.pos).length() <= reach || self.recently_hit(ward, e) {
                set |= 1 << e;
            }
        }
        set
    }

    /// Slots of the active ships (alive and present).
    pub fn active_mask(&self) -> u32 {
        self.ships
            .iter()
            .enumerate()
            .filter(|(_, s)| s.active())
            .fold(0, |a, (i, _)| a | 1 << i)
    }

    /// v6, for the trainer's script pull: whether slot `slot` is in transit now, its
    /// effective order a go-to not yet arrived, or a defend whose ward's threat set
    /// (among the active ships) is empty.
    pub fn order_transit(&self, cat: &Catalogue, slot: usize) -> bool {
        match effective_order(self, slot) {
            Order::GoTo { .. } => true,
            Order::Defend { ward } => {
                self.threat_set(cat, usize::from(ward), self.active_mask()) == 0
            }
            Order::None | Order::Attack { .. } => false,
        }
    }
}
