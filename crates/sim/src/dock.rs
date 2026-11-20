//! Dock and repair (v11, SIM_SPEC §0.9, §5.11): strike craft fly back to their carrier
//! (or station), dock through a live bay, repair in the hangar and relaunch through the
//! ordinary launch.
//!
//! - **The dock order** (`Order::Dock { carrier, bay }`) is a ship's own order, kept
//!   here per slot (`DockState::bay`), not a squad's. It wins over the squad's order
//!   (`order::standing_order`) and takes the ship out of its squad when given. To the
//!   pilot nets it **reads as a go-to** (`order::read_as`) whose point is the ordered
//!   bay's [`Match::dock_point`] now (the carrier moves, so the point moves with it),
//!   radius [`DOCK_CAPTURE_RADIUS`], no deadline: no new input, `OBS_DIM` stays 587. It
//!   never completes on arrival like a go-to: it ends when the ship docks, or is
//!   dropped (`DockAborted`) when the carrier is lost or no bay is left.
//! - **Docking** is a sim rule, not an autopilot: the pilot flies the approach. At the
//!   end of every step (stage 12c) an active ship holding a dock order docks if it is
//!   within [`DOCK_CAPTURE_RADIUS`] of the dock point of **any** live bay of its carrier
//!   with a velocity within [`DOCK_MAX_REL_SPEED`] of that point's (the carrier's
//!   velocity plus its spin at the point). A bay that catches a slow pass is enough; no
//!   stop is needed. The ship leaves the field as a reserve does (`Attach::Docked`, not
//!   present, its thrust and queue cleared), its shield refills, its dock order clears
//!   and it joins the back of the hangar (`Match.reserves`): `Docked`.
//! - **Repair**: every step a returned ship is in a live carrier's hangar its hull gains
//!   [`REPAIR_FRAC_PER_S`] of its maximum a second (`Repaired` once full). It may launch
//!   again [`DOCK_TURNAROUND_TICKS`] after docking (`DockState::ready_at`), and while the
//!   recall doctrine runs for its team not before it is repaired past
//!   [`RECALL_HULL_FRAC`] (else it would be recalled as it left the bay); the launch
//!   takes the first *ready* reserve, so a fresh reserve, always ready, goes first. It
//!   relaunches as the same slot, so its pilot and identity are unchanged (`Relaunched`
//!   follows its `Launch`). If the carrier dies it dies with the hangar, as reserves do.
//! - **The recall doctrine** (`MatchConfig.recall_doctrine`, on by default): on each of
//!   its slow ticks, after its commands, a team whose orders its pilots see gives the
//!   dock order to every strike craft on the field below [`RECALL_HULL_FRAC`] of its
//!   hull, whatever its commander mode, while its carrier is up with a live bay, unless
//!   the craft is finishing a kill (its attack target within its reach and below
//!   [`RECALL_FINISH_FRAC`] of its hull) or under an enemy capital ship's guns (within
//!   its longest range plus [`RECALL_CLEAR_MARGIN`]), recalled once clear: recalled deep
//!   in the guns, most craft died on the way home (`lab/runs/2026-11-20-dock-repair`).
//!   The bay is the one whose dock point is nearest the craft. A stopgap until a learned commander decides recalls itself (stage 4 of
//!   the dock plan, `lab/runs/2026-11-20-dock-repair/plan.md`); training turns it off.
//!
//! Gating: all of this needs `MatchConfig.docking` (default true) and a carrier in the
//! match (a carrier battle or a station assault). With `docking = false` every match is
//! v10's bit for bit, and the state hash appends [`DockState`] only while docking is
//! live, so a deathmatch or a convoy hashes as before either way.

use crate::DT;
use crate::actions::ShipAction;
use crate::command::Order;
use crate::data::Catalogue;
use crate::events::Event;
use crate::hash::{StateHash, StateHasher};
use crate::math::Vec2;
use crate::mission::is_capital_ship;
use crate::order::effective_order;
use crate::state::{
    Attach, MAX_BAYS, MAX_REACTION_TICKS, MAX_SHIPS, MAX_THRUSTERS, Match, NONE, ShipIdx,
};

/// "No dock order" in [`DockState::bay`].
pub const NO_BAY: u8 = u8::MAX;
/// A bay's dock point lies this far (m) outside its mouth along the bay direction: where
/// a launched light craft appears (its bound radius plus `LAUNCH_CLEARANCE`, 6 m for a
/// fighter), rounded out so a gunship's centre there clears the carrier's circles too.
pub const DOCK_POINT_OFFSET: f32 = 8.0;
/// A ship within this distance (m) of a live bay's dock point may dock. Also the radius
/// the dock order shows the pilot nets as a go-to.
pub const DOCK_CAPTURE_RADIUS: f32 = 10.0;
/// ... with its velocity within this (m/s) of the dock point's.
pub const DOCK_MAX_REL_SPEED: f32 = 15.0;
/// Hull repaired per second in the hangar, as a fraction of the hull's maximum.
pub const REPAIR_FRAC_PER_S: f32 = 0.05;
/// A docked ship may relaunch this many ticks after it docked (4 s).
pub const DOCK_TURNAROUND_TICKS: u32 = 120;
/// The recall doctrine recalls a strike craft below this fraction of its hull. Tuned
/// 0.3 → 0.6 → 0.5: at 0.3 most recalled craft were killed before they reached the bay,
/// at 0.6 the doctrine pulled so many out of the fight that the citadel assault moved
/// further from v10's balance (`lab/runs/2026-11-20-dock-repair/results.md`).
pub const RECALL_HULL_FRAC: f32 = 0.5;
/// ... unless it is finishing a kill: its attack target within its reach and below this
/// fraction of the target's hull.
pub const RECALL_FINISH_FRAC: f32 = 0.25;
/// ... or it is under an enemy capital ship's guns: within that ship's longest weapon
/// range plus this margin (m). It finishes its run and is recalled once clear.
pub const RECALL_CLEAR_MARGIN: f32 = 40.0;

/// `DockAborted` reasons.
pub const ABORT_CARRIER_LOST: u8 = 0;
pub const ABORT_NO_BAY: u8 = 1;

/// A bay of a team's carrier in the carrier's body frame (copied from its hull at
/// setup, like `Match.ship_reach`; not hashed).
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct BayMount {
    pub pos: Vec2,
    pub dir: Vec2,
}

/// Per-slot dock state (v11; hashed while docking is live, module docs).
#[derive(Clone, Debug, PartialEq)]
pub struct DockState {
    /// The bay of the ship's dock order, [`NO_BAY`] without one.
    pub bay: [u8; MAX_SHIPS],
    /// The tick the dock order was given, 0 without one.
    pub since: [u32; MAX_SHIPS],
    /// The tick a returned ship docked, 0 for a ship that is not back in the hangar (in
    /// space, or a reserve that never launched).
    pub docked_at: [u32; MAX_SHIPS],
    /// The first tick the ship may launch, 0 for always (a reserve that never launched).
    pub ready_at: [u32; MAX_SHIPS],
}

impl Default for DockState {
    fn default() -> Self {
        DockState {
            bay: [NO_BAY; MAX_SHIPS],
            since: [0; MAX_SHIPS],
            docked_at: [0; MAX_SHIPS],
            ready_at: [0; MAX_SHIPS],
        }
    }
}

impl DockState {
    /// Hash the first `n` slots of every array, in field order.
    pub fn hash_slots(&self, n: usize, h: &mut StateHasher) {
        h.write_bytes(&self.bay[..n]);
        self.since[..n].hash_into(h);
        self.docked_at[..n].hash_into(h);
        self.ready_at[..n].hash_into(h);
    }
}

/// What a ship is doing about docking, for the views.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DockPhase {
    /// Nothing: in space without a dock order, arriving, a fresh reserve, or dead.
    None = 0,
    /// In space under a dock order, flying to its bay.
    Inbound = 1,
    /// Back in the hangar, inside its turnaround.
    Repairing = 2,
    /// Back in the hangar, its turnaround over: the next launch may take it.
    Ready = 3,
}

impl DockPhase {
    pub fn name(self) -> &'static str {
        match self {
            DockPhase::None => "none",
            DockPhase::Inbound => "inbound",
            DockPhase::Repairing => "repairing",
            DockPhase::Ready => "ready",
        }
    }
}

impl Match {
    /// Whether the dock rules run in this match: `MatchConfig.docking` and a carrier
    /// on either side (a carrier battle or a station assault).
    pub fn docking_live(&self) -> bool {
        self.cfg.docking && (self.mission.carrier[0] != NONE || self.mission.carrier[1] != NONE)
    }

    /// Copy each team's carrier bays at setup.
    pub(crate) fn init_bay_mounts(&mut self, cat: &Catalogue) {
        for t in 0..2 {
            let c = self.mission.carrier[t];
            if c == NONE {
                continue;
            }
            let bays = &cat.hull(self.ships[usize::from(c)].hull).bays;
            self.bay_count[t] = bays.len() as u8;
            for (mount, b) in self.bay_mounts[t].iter_mut().zip(bays) {
                *mount = BayMount {
                    pos: b.pos,
                    dir: b.dir,
                };
            }
        }
    }

    /// The carrier slot of `ship`'s team (`NONE` without one).
    fn own_carrier(&self, ship: usize) -> ShipIdx {
        self.mission.carrier[usize::from(self.ships[ship].team & 1)]
    }

    /// Bay `bay` of `carrier`'s dock point in world now: the mouth plus
    /// [`DOCK_POINT_OFFSET`] along the bay direction.
    pub fn dock_point(&self, carrier: ShipIdx, bay: u8) -> Vec2 {
        let c = &self.ships[usize::from(carrier)];
        let mount = self.bay_mounts[usize::from(c.team & 1)][usize::from(bay) % MAX_BAYS];
        c.to_world(mount.pos) + mount.dir.rotated(c.heading) * DOCK_POINT_OFFSET
    }

    /// The velocity of a point `p` riding on `carrier` (its velocity plus its spin).
    fn riding_velocity(&self, carrier: ShipIdx, p: Vec2) -> Vec2 {
        let c = &self.ships[usize::from(carrier)];
        c.vel + (p - c.pos).perp() * c.omega
    }

    /// For a ship under a dock order: its bay's dock point now, its distance to it and
    /// its speed relative to the point (what the docking rule measures). `None` without
    /// a dock order.
    pub fn dock_approach(&self, ship: usize) -> Option<(Vec2, f32, f32)> {
        if !self.has_dock_order(ship) {
            return None;
        }
        let carrier = self.own_carrier(ship);
        let p = self.dock_point(carrier, self.dock.bay[ship]);
        let me = &self.ships[ship];
        let rel = (me.vel - self.riding_velocity(carrier, p)).length();
        Some((p, (me.pos - p).length(), rel))
    }

    /// Whether bay `bay` of `carrier` exists and is not destroyed.
    fn bay_open(&self, carrier: ShipIdx, bay: u8) -> bool {
        let c = &self.ships[usize::from(carrier)];
        bay < self.bay_count[usize::from(c.team & 1)] && c.bay_alive(usize::from(bay))
    }

    /// The live bay of `carrier` whose dock point is nearest `pos` (ties to the lower
    /// bay), `None` with every bay destroyed or none.
    pub fn nearest_open_bay(&self, carrier: ShipIdx, pos: Vec2) -> Option<u8> {
        let t = usize::from(self.ships[usize::from(carrier)].team & 1);
        let mut best: Option<(f32, u8)> = None;
        for b in 0..self.bay_count[t] {
            if !self.bay_open(carrier, b) {
                continue;
            }
            let d = (self.dock_point(carrier, b) - pos).length();
            if best.is_none_or(|(bd, _)| d < bd) {
                best = Some((d, b));
            }
        }
        best.map(|(_, b)| b)
    }

    /// Whether `ship` holds a dock order.
    pub fn has_dock_order(&self, ship: usize) -> bool {
        self.dock.bay[ship] != NO_BAY
    }

    /// `ship`'s dock order as an `Order`, `Order::None` without one.
    pub fn dock_order(&self, ship: usize) -> Order {
        if !self.has_dock_order(ship) {
            return Order::None;
        }
        Order::Dock {
            carrier: self.own_carrier(ship),
            bay: self.dock.bay[ship],
        }
    }

    /// Whether `ship` may launch now (a reserve that never launched always may).
    pub fn launch_ready(&self, ship: ShipIdx) -> bool {
        self.tick >= self.dock.ready_at[usize::from(ship)]
    }

    /// `team`'s reserves a launch could take now, in the order launches take them.
    pub fn launchable(&self, team: u8) -> impl Iterator<Item = ShipIdx> + '_ {
        self.reserves[usize::from(team & 1)]
            .iter()
            .copied()
            .filter(|&s| self.launch_ready(s))
    }

    /// Whether `ship` is a returned ship in its hangar (it docked and has not launched).
    pub fn returned(&self, ship: usize) -> bool {
        self.dock.docked_at[ship] != 0 && self.ships[ship].attach == Attach::Docked
    }

    /// What `ship` is doing about docking (views).
    pub fn dock_phase(&self, ship: usize) -> DockPhase {
        if !self.ships[ship].alive {
            DockPhase::None
        } else if self.has_dock_order(ship) {
            DockPhase::Inbound
        } else if self.returned(ship) {
            if self.launch_ready(ship as ShipIdx) {
                DockPhase::Ready
            } else {
                DockPhase::Repairing
            }
        } else {
            DockPhase::None
        }
    }

    /// Give `ship` a dock order to `bay` of its carrier (the caller checked them): it
    /// leaves its squad, and `DockOrdered` is emitted.
    pub(crate) fn set_dock_order(&mut self, ship: usize, bay: u8, by_doctrine: bool) {
        let carrier = self.own_carrier(ship);
        let t = usize::from(self.ships[ship].team & 1);
        self.dock.bay[ship] = bay;
        self.dock.since[ship] = self.tick;
        for q in self.command.squads[t].iter_mut() {
            q.members &= !(1 << ship);
        }
        self.events.push(Event::DockOrdered {
            ship: ship as ShipIdx,
            carrier,
            bay,
            pos: self.dock_point(carrier, bay),
            by_doctrine,
        });
    }

    fn clear_dock_order(&mut self, ship: usize) {
        self.dock.bay[ship] = NO_BAY;
        self.dock.since[ship] = 0;
    }

    /// The recall doctrine (module docs) for `team`, after its slow tick's commands.
    pub(crate) fn apply_recall_doctrine(&mut self, cat: &Catalogue, team: u8) {
        let t = usize::from(team & 1);
        if !self.docking_live() || !self.doctrine_applies(t) {
            return;
        }
        let carrier = self.mission.carrier[t];
        if carrier == NONE || !self.ships[usize::from(carrier)].active() {
            return;
        }
        for s in 0..self.ships.len() {
            let ship = &self.ships[s];
            let hull = cat.hull(ship.hull);
            if ship.team != team
                || !ship.active()
                || is_capital_ship(hull)
                || self.has_dock_order(s)
                || ship.hp >= RECALL_HULL_FRAC * hull.hp
                || self.finishing_kill(cat, s)
                || self.under_capital_guns(cat, s)
            {
                continue;
            }
            let Some(bay) = self.nearest_open_bay(carrier, ship.pos) else {
                return;
            };
            self.set_dock_order(s, bay, true);
        }
    }

    /// Whether `ship`'s effective order is an attack on a target within its reach and
    /// below [`RECALL_FINISH_FRAC`] of its hull.
    fn finishing_kill(&self, cat: &Catalogue, ship: usize) -> bool {
        let Order::Attack { target } = effective_order(self, ship) else {
            return false;
        };
        let t = &self.ships[usize::from(target)];
        let near = (t.pos - self.ships[ship].pos).length() <= self.ship_reach[ship];
        near && t.hp < RECALL_FINISH_FRAC * cat.hull(t.hull).hp
    }

    /// Whether `ship` is within an active enemy capital ship's longest weapon range
    /// plus [`RECALL_CLEAR_MARGIN`].
    fn under_capital_guns(&self, cat: &Catalogue, ship: usize) -> bool {
        let me = &self.ships[ship];
        self.ships.iter().enumerate().any(|(e, o)| {
            o.active()
                && o.team != me.team
                && is_capital_ship(cat.hull(o.hull))
                && (o.pos - me.pos).length() <= self.ship_reach[e] + RECALL_CLEAR_MARGIN
        })
    }

    /// Stage 12c (v11, module docs): keep every dock order valid, dock the ships that
    /// reach a bay slowly enough, repair the hangars.
    pub(crate) fn step_docking(&mut self, cat: &Catalogue) {
        self.docked_now = 0;
        if !self.docking_live() {
            return;
        }
        for s in 0..self.ships.len() {
            if !self.has_dock_order(s) {
                continue;
            }
            let carrier = self.own_carrier(s);
            if !self.ships[s].alive {
                // Killed on the way in: the `Death` says so.
                self.clear_dock_order(s);
                continue;
            }
            if carrier == NONE || !self.ships[usize::from(carrier)].active() {
                self.abort_dock(s, carrier, ABORT_CARRIER_LOST);
                continue;
            }
            if !self.bay_open(carrier, self.dock.bay[s]) {
                match self.nearest_open_bay(carrier, self.ships[s].pos) {
                    Some(b) => self.dock.bay[s] = b,
                    None => {
                        self.abort_dock(s, carrier, ABORT_NO_BAY);
                        continue;
                    }
                }
            }
            if !self.ships[s].active() {
                continue;
            }
            if let Some(bay) = self.capturing_bay(carrier, s) {
                self.dock_ship(cat, s, carrier, bay);
            }
        }
        self.repair_hangars(cat);
    }

    fn abort_dock(&mut self, ship: usize, carrier: ShipIdx, reason: u8) {
        self.clear_dock_order(ship);
        self.events.push(Event::DockAborted {
            ship: ship as ShipIdx,
            carrier,
            reason,
        });
    }

    /// The live bay of `carrier` that catches `ship` now (within the capture radius of
    /// its dock point, slow enough relative to it), the nearest if several.
    fn capturing_bay(&self, carrier: ShipIdx, ship: usize) -> Option<u8> {
        let me = &self.ships[ship];
        let t = usize::from(me.team & 1);
        let mut best: Option<(f32, u8)> = None;
        for b in 0..self.bay_count[t] {
            if !self.bay_open(carrier, b) {
                continue;
            }
            let p = self.dock_point(carrier, b);
            let d = (me.pos - p).length();
            let rel = (me.vel - self.riding_velocity(carrier, p)).length();
            if d <= DOCK_CAPTURE_RADIUS
                && rel <= DOCK_MAX_REL_SPEED
                && best.is_none_or(|(bd, _)| d < bd)
            {
                best = Some((d, b));
            }
        }
        best.map(|(_, b)| b)
    }

    fn dock_ship(&mut self, cat: &Catalogue, s: usize, carrier: ShipIdx, bay: u8) {
        let t = usize::from(self.ships[s].team & 1);
        let tick = self.tick;
        let c = &self.ships[usize::from(carrier)];
        let (c_pos, c_heading) = (c.pos, c.heading);
        let hull = cat.hull(self.ships[s].hull);
        let ship = &mut self.ships[s];
        let pos = ship.pos;
        let hp_frac = ship.hp / hull.hp;
        ship.attach = Attach::Docked;
        ship.parent = carrier;
        ship.present = false;
        ship.pos = c_pos;
        ship.heading = c_heading;
        ship.vel = Vec2::ZERO;
        ship.omega = 0.0;
        ship.thrust_level = [0.0; MAX_THRUSTERS];
        ship.queue = [ShipAction::IDLE; MAX_REACTION_TICKS];
        ship.shield = hull.shield.map_or(0.0, |sh| sh.hp);
        self.clear_dock_order(s);
        self.dock.docked_at[s] = tick;
        self.dock.ready_at[s] = tick + self.turnaround_ticks(t, hp_frac);
        self.reserves[t].push(s as ShipIdx);
        for q in self.command.squads[t].iter_mut() {
            q.members &= !(1 << s);
        }
        self.docked_now |= 1 << s;
        self.events.push(Event::Docked {
            ship: s as ShipIdx,
            carrier,
            bay,
            pos,
            hp_frac,
        });
    }

    /// Whether the recall doctrine runs for team `t` (docking itself is live).
    fn doctrine_applies(&self, t: usize) -> bool {
        self.cfg.recall_doctrine && !self.cfg.hide_orders[t]
    }

    /// Ticks from docking to the first launch of a ship of team `t` that docked at
    /// `hp_frac` of its hull: [`DOCK_TURNAROUND_TICKS`], or longer while the doctrine runs
    /// for the team, until the hangar has repaired it to [`RECALL_HULL_FRAC`] (one tick
    /// spare for rounding), so a relaunched craft is never recalled on its first slow
    /// tick out of the bay.
    fn turnaround_ticks(&self, t: usize, hp_frac: f32) -> u32 {
        if !self.doctrine_applies(t) || hp_frac >= RECALL_HULL_FRAC {
            return DOCK_TURNAROUND_TICKS;
        }
        let per_tick = REPAIR_FRAC_PER_S * DT;
        let repair = ((RECALL_HULL_FRAC - hp_frac) / per_tick).ceil() as u32 + 1;
        repair.max(DOCK_TURNAROUND_TICKS)
    }

    /// Repair every returned ship in a live carrier's hangar.
    fn repair_hangars(&mut self, cat: &Catalogue) {
        for t in 0..2 {
            let carrier = self.mission.carrier[t];
            if carrier == NONE || !self.ships[usize::from(carrier)].active() {
                continue;
            }
            for k in 0..self.reserves[t].len() {
                let s = usize::from(self.reserves[t][k]);
                if self.dock.docked_at[s] == 0 {
                    continue;
                }
                let max = cat.hull(self.ships[s].hull).hp;
                let ship = &mut self.ships[s];
                if ship.hp >= max {
                    continue;
                }
                ship.hp = (ship.hp + REPAIR_FRAC_PER_S * max * DT).min(max);
                if ship.hp >= max {
                    self.events.push(Event::Repaired {
                        ship: s as ShipIdx,
                        carrier,
                    });
                }
            }
        }
    }
}
