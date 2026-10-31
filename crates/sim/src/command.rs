//! The commander layer (SIM_SPEC §5.9, v4; DESIGN §7 "Hierarchy"): squads, orders,
//! waypoints and launches, decided on a slow tick every `COMMAND_TICKS`.
//!
//! On every step whose tick is a multiple of `COMMAND_TICKS` (stage 1b), the sim
//! first sanitises each team's squads (drops members that died or jumped out, and
//! clears orders whose target or ward is gone) and waypoints, then gathers each
//! team's commands — from the scripted commander (`scripted::commander`) for a
//! `Scripted` team, or from the team's inbox for an `External` one — and applies team
//! 0's, then team 1's, in order. Both scripted commanders read the state before
//! either team's commands apply. No commands means the previous orders stand.
//!
//! Squads, orders and waypoints are sim state (hashed). Invalid commands never panic:
//! a launch that cannot happen and a waypoint for the wrong ship are refused; squad
//! members and orders that are not valid are sanitised (dropped, or the order
//! replaced by `Order::None`). Every command's outcome is reported in
//! `Match.command_results`. Pilots do not see orders in stage A; from v5 every
//! ship's own order is in its obs (`order` module, SIM_SPEC §7.2) and pays the order
//! reward (§8).

use crate::actions::ShipAction;
use crate::data::{Catalogue, HullId};
use crate::events::Event;
use crate::hash::{StateHash, StateHasher};
use crate::math::Vec2;
use crate::mission::{ConvoyStatus, JumpState, MissionKind, is_capital_ship, is_transport};
use crate::scripted;
use crate::state::{Attach, MAX_REACTION_TICKS, MAX_SHIPS, Match, NONE, Ship, ShipIdx};

/// Ticks between commander decisions (2 s at 30 Hz).
pub const COMMAND_TICKS: u32 = 60;
/// Squads per team.
pub const MAX_SQUADS: usize = 4;
/// A bay that launched may launch again this many ticks later (1.5 s).
pub const BAY_COOLDOWN_TICKS: u32 = 45;
/// Launch speed relative to the carrier along the bay direction, m/s.
pub const LAUNCH_SPEED: f32 = 30.0;
/// Control lock after a launch, ticks (0.5 s; longer than any reaction delay).
pub const LAUNCH_LOCK_TICKS: u32 = 15;
/// A launched ship appears this far beyond its own bound radius out of the bay
/// mouth, so it does not overlap the carrier's collision circles.
pub const LAUNCH_CLEARANCE: f32 = 1.0;
/// Go-to orders' radius is clamped to `[MIN_GOTO_RADIUS, arena radius]`.
pub const MIN_GOTO_RADIUS: f32 = 10.0;
/// Waypoints and go-to points are clamped inside this fraction of the arena radius.
pub const POINT_LIMIT_FRAC: f32 = 0.95;

const _: () = assert!(MAX_SHIPS <= 32, "squad member masks are u32");
const _: () = assert!(LAUNCH_LOCK_TICKS as usize > MAX_REACTION_TICKS);

/// Who commands a team.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum CommanderMode {
    /// `scripted::commander::commands` runs inside `step` on the slow tick (browser
    /// and training run identical code).
    #[default]
    Scripted,
    /// The caller submits commands (`Match::submit_command`) before a slow-tick step.
    External,
    /// v5: the scripted commander's logistics with random squads and orders, drawn
    /// from the commander's own rng streams (`scripted::random_commander`), for
    /// training pilots to follow any order.
    Random,
}

impl CommanderMode {
    pub fn name(self) -> &'static str {
        match self {
            CommanderMode::Scripted => "scripted",
            CommanderMode::External => "external",
            CommanderMode::Random => "random",
        }
    }

    pub fn from_name(name: &str) -> Option<CommanderMode> {
        match name {
            "scripted" => Some(CommanderMode::Scripted),
            "external" => Some(CommanderMode::External),
            "random" => Some(CommanderMode::Random),
            _ => None,
        }
    }
}

/// A squad's order.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub enum Order {
    #[default]
    None,
    /// Attack an active enemy ship.
    Attack { target: ShipIdx },
    /// v6 (was guard): defend an own ship that is still in the match against its
    /// threat set (`order::threat_set`).
    Defend { ward: ShipIdx },
    /// v6 (replaces hold): go to a point (inside `POINT_LIMIT_FRAC` of the arena),
    /// arriving within `radius`; completes per ship on arrival (`order` module).
    GoTo { point: Vec2, radius: f32 },
}

impl Order {
    /// 0 none, 1 attack, 2 defend, 3 go-to.
    pub fn kind(&self) -> u8 {
        match self {
            Order::None => 0,
            Order::Attack { .. } => 1,
            Order::Defend { .. } => 2,
            Order::GoTo { .. } => 3,
        }
    }

    pub fn kind_name(&self) -> &'static str {
        match self {
            Order::None => "none",
            Order::Attack { .. } => "attack",
            Order::Defend { .. } => "defend",
            Order::GoTo { .. } => "goto",
        }
    }

    /// The ship the order is about, `NONE` for none and go-to.
    pub fn target(&self) -> ShipIdx {
        match *self {
            Order::Attack { target } => target,
            Order::Defend { ward } => ward,
            Order::None | Order::GoTo { .. } => NONE,
        }
    }
}

impl StateHash for Order {
    fn hash_into(&self, h: &mut StateHasher) {
        h.write_u8(self.kind());
        h.write_u8(self.target());
        let (point, radius) = match *self {
            Order::GoTo { point, radius } => (point, radius),
            _ => (Vec2::ZERO, 0.0),
        };
        h.write_vec2(point);
        h.write_f32(radius);
    }
}

/// A set of ship slots (bit `s` = slot `s`) under one order. A ship is in at most
/// one squad of its team; capital ships are never in squads.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct Squad {
    pub members: u32,
    pub order: Order,
}

impl Squad {
    pub fn contains(&self, slot: usize) -> bool {
        self.members & (1 << slot) != 0
    }

    pub fn len(&self) -> u32 {
        self.members.count_ones()
    }

    pub fn is_empty(&self) -> bool {
        self.members == 0
    }
}

/// Where a capital ship's script flies it.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub enum Waypoint {
    /// No waypoint: hold heading and coast.
    #[default]
    Unset,
    At(Vec2),
}

impl StateHash for Waypoint {
    fn hash_into(&self, h: &mut StateHasher) {
        match *self {
            Waypoint::Unset => {
                h.write_u8(0);
                h.write_vec2(Vec2::ZERO);
            }
            Waypoint::At(p) => {
                h.write_u8(1);
                h.write_vec2(p);
            }
        }
    }
}

/// Squads and waypoints (hashed in this order: team 0's squads, team 1's, then one
/// waypoint per slot).
#[derive(Clone, Debug, PartialEq)]
pub struct CommandState {
    pub squads: [[Squad; MAX_SQUADS]; 2],
    pub waypoints: [Waypoint; MAX_SHIPS],
}

impl Default for CommandState {
    fn default() -> Self {
        CommandState {
            squads: [[Squad::default(); MAX_SQUADS]; 2],
            waypoints: [Waypoint::Unset; MAX_SHIPS],
        }
    }
}

impl StateHash for CommandState {
    fn hash_into(&self, h: &mut StateHasher) {
        for team in &self.squads {
            for s in team {
                h.write_u32(s.members);
                s.order.hash_into(h);
            }
        }
        self.waypoints.hash_into(h);
    }
}

/// One commander action.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Command {
    /// Launch one reserve: the first in the hangar of `hull` (any hull if `None`),
    /// from `bay` (the sim picks the bay that has been ready longest if `None`).
    Launch {
        hull: Option<HullId>,
        bay: Option<u8>,
    },
    /// Set (or unset) a capital ship's waypoint.
    Waypoint { ship: ShipIdx, waypoint: Waypoint },
    /// Make squad `squad` exactly `members` (taking them out of the team's other
    /// squads) under `order`.
    Squad {
        squad: u8,
        members: u32,
        order: Order,
    },
}

/// Why a command was refused.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Refusal {
    /// The team has no carrier in this mission.
    NoCarrier,
    /// Its carrier is dead.
    CarrierLost,
    /// The hangar is empty.
    HangarEmpty,
    /// No reserve of the requested hull.
    NoReserveOfHull,
    /// The requested bay does not exist.
    NoSuchBay,
    /// The bay (or, with no bay requested, every bay) is cooling down.
    BayBusy,
    /// The ship is not a slot of this team.
    NotOwnShip,
    /// The ship died or jumped out.
    ShipLost,
    /// Waypoints are for capital ships (carrier, transport) only.
    NotCapital,
    /// A non-finite waypoint, go-to point or radius.
    BadPoint,
    /// Squad index `>= MAX_SQUADS`.
    NoSuchSquad,
}

impl Refusal {
    pub fn name(self) -> &'static str {
        match self {
            Refusal::NoCarrier => "no_carrier",
            Refusal::CarrierLost => "carrier_lost",
            Refusal::HangarEmpty => "hangar_empty",
            Refusal::NoReserveOfHull => "no_reserve_of_hull",
            Refusal::NoSuchBay => "no_such_bay",
            Refusal::BayBusy => "bay_busy",
            Refusal::NotOwnShip => "not_own_ship",
            Refusal::ShipLost => "ship_lost",
            Refusal::NotCapital => "not_capital",
            Refusal::BadPoint => "bad_point",
            Refusal::NoSuchSquad => "no_such_squad",
        }
    }
}

/// What a command did.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Outcome {
    Applied,
    /// Applied after dropping invalid members or replacing an invalid order.
    Sanitized,
    Launched {
        ship: ShipIdx,
        bay: u8,
    },
    Refused(Refusal),
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CommandOutcome {
    pub command: Command,
    pub outcome: Outcome,
}

/// A capital ship as the commander sees it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CapitalStatus {
    pub slot: ShipIdx,
    pub hull: HullId,
    pub alive: bool,
    pub hp: f32,
    pub max_hp: f32,
    pub shield: f32,
    pub max_shield: f32,
    pub pos: Vec2,
    pub vel: Vec2,
    pub heading: f32,
}

/// The coarse commander observation of one team (DESIGN §7). Counts are indexed by
/// hull id (`len == catalogue hulls`). A learned commander will flatten this.
#[derive(Clone, Debug, PartialEq)]
pub struct CommanderObs {
    pub team: u8,
    pub tick: u32,
    pub ticks_left: u32,
    pub mission: MissionKind,
    /// Own ships on the field (active), by hull.
    pub in_space: Vec<u8>,
    /// Own ships still to jump in (alive, not present, not docked), by hull.
    pub arriving: Vec<u8>,
    /// Own docked reserves, by hull.
    pub reserves: Vec<u8>,
    /// Enemy ships on the field (active), by hull: what the team can see.
    pub enemy_visible: Vec<u8>,
    pub own_carrier: Option<CapitalStatus>,
    pub enemy_carrier: Option<CapitalStatus>,
    /// Per bay of the own carrier: ready to launch on this tick.
    pub bays_ready: Vec<bool>,
    /// Convoy counts (all zero outside a convoy escort; the attackers see them too).
    pub convoy: ConvoyStatus,
    /// Own transports (convoy escort), alive and on the field.
    pub transports: Vec<CapitalStatus>,
    pub squads: [Squad; MAX_SQUADS],
}

fn finite(p: Vec2) -> bool {
    p.x.is_finite() && p.y.is_finite()
}

/// `p` clamped to the disc of radius `r`.
fn clamp_to_disc(p: Vec2, r: f32) -> Vec2 {
    let len = p.length();
    if len > r { p * (r / len) } else { p }
}

impl Match {
    /// Whether the next `step` is a slow tick (commands submitted now apply then).
    pub fn command_due(&self) -> bool {
        (self.tick + 1) % COMMAND_TICKS == 0
    }

    /// Queue `cmd` for `team`'s next slow tick (`External` mode; a `Scripted` team's
    /// inbox is discarded on the slow tick).
    pub fn submit_command(&mut self, team: u8, cmd: Command) {
        self.inbox[usize::from(team & 1)].push(cmd);
    }

    /// Outcomes of `team`'s commands on the last slow tick.
    pub fn command_results(&self, team: u8) -> &[CommandOutcome] {
        &self.command_results[usize::from(team & 1)]
    }

    /// Stage 1b (v4): on a slow tick, sanitise, gather and apply both teams'
    /// commands (module docs).
    pub(crate) fn step_commanders(&mut self, cat: &Catalogue) {
        if self.tick % COMMAND_TICKS != 0 {
            return;
        }
        let before = self.command.squads;
        for team in 0..2u8 {
            self.command_results[usize::from(team)].clear();
            self.sanitize_squads(team);
        }
        self.sanitize_waypoints();
        let mut batches: [Vec<Command>; 2] = [Vec::new(), Vec::new()];
        for team in 0..2u8 {
            let t = usize::from(team);
            let inbox = std::mem::take(&mut self.inbox[t]);
            batches[t] = match self.cfg.commanders[t] {
                CommanderMode::External => inbox,
                CommanderMode::Scripted => scripted::commander::commands(self, cat, team),
                CommanderMode::Random => {
                    // Its own streams (cloned out and back: `commands` reads the match).
                    let mut st = self.random_commander.clone();
                    let cmds = scripted::random_commander::commands(self, cat, team, &mut st);
                    self.random_commander = st;
                    cmds
                }
            };
        }
        for (team, batch) in batches.into_iter().enumerate() {
            for cmd in batch {
                let outcome = self.apply_command(cat, team as u8, cmd);
                self.command_results[team].push(CommandOutcome {
                    command: cmd,
                    outcome,
                });
            }
        }
        // One `Order` per squad whose order differs from the last slow tick's, so a
        // cleared-then-reissued order is a single event and an unchanged one none.
        for (t, old) in before.iter().enumerate() {
            for (k, old) in old.iter().enumerate() {
                if self.command.squads[t][k].order != old.order {
                    self.emit_order(t as u8, k);
                }
            }
        }
    }

    /// Whether slot `s` can be a squad member of `team`: own, in the match, not a
    /// capital ship.
    fn squad_eligible(&self, cat: &Catalogue, team: u8, s: usize) -> bool {
        let ship = &self.ships[s];
        ship.team == team && self.in_match(s) && !is_capital_ship(cat.hull(ship.hull))
    }

    /// `order` if it is valid for `team` now, else `Order::None`; go-to points are
    /// clamped into the arena and their radius into `[MIN_GOTO_RADIUS, R]`.
    fn sanitize_order(&self, team: u8, order: Order) -> Order {
        let n = self.ships.len();
        let radius = self.cfg.arena_radius;
        match order {
            Order::None => Order::None,
            Order::Attack { target } => {
                let t = usize::from(target);
                if t < n && self.ships[t].team != team && self.ships[t].active() {
                    order
                } else {
                    Order::None
                }
            }
            Order::Defend { ward } => {
                let w = usize::from(ward);
                if w < n && self.ships[w].team == team && self.in_match(w) {
                    order
                } else {
                    Order::None
                }
            }
            Order::GoTo { point, radius: r } => {
                if !finite(point) || !r.is_finite() {
                    return Order::None;
                }
                Order::GoTo {
                    point: clamp_to_disc(point, POINT_LIMIT_FRAC * radius),
                    radius: r.clamp(MIN_GOTO_RADIUS, radius),
                }
            }
        }
    }

    /// Emit `Order` for squad `k` of `team` (its current order).
    fn emit_order(&mut self, team: u8, k: usize) {
        let order = self.command.squads[usize::from(team)][k].order;
        let (point, radius) = match order {
            Order::GoTo { point, radius } => (point, radius),
            Order::Attack { target } => (self.ships[usize::from(target)].pos, 0.0),
            Order::Defend { ward } => (self.ships[usize::from(ward)].pos, 0.0),
            Order::None => (Vec2::ZERO, 0.0),
        };
        self.events.push(Event::Order {
            team,
            squad: k as u8,
            kind: order.kind(),
            target: order.target(),
            point,
            radius,
        });
    }

    /// Drop members that died or jumped out; clear orders that are no longer valid.
    fn sanitize_squads(&mut self, team: u8) {
        let t = usize::from(team);
        for k in 0..MAX_SQUADS {
            let mut members = self.command.squads[t][k].members;
            for s in 0..self.ships.len() {
                if members & (1 << s) != 0 && !self.in_match(s) {
                    members &= !(1 << s);
                }
            }
            self.command.squads[t][k].members = members;
            let old = self.command.squads[t][k].order;
            self.command.squads[t][k].order = self.sanitize_order(team, old);
        }
    }

    /// Unset the waypoints of ships that died or jumped out.
    fn sanitize_waypoints(&mut self) {
        for s in 0..self.ships.len() {
            if !self.in_match(s) {
                self.command.waypoints[s] = Waypoint::Unset;
            }
        }
    }

    fn apply_command(&mut self, cat: &Catalogue, team: u8, cmd: Command) -> Outcome {
        match cmd {
            Command::Launch { hull, bay } => match self.launch(cat, team, hull, bay) {
                Ok((ship, bay)) => Outcome::Launched { ship, bay },
                Err(r) => Outcome::Refused(r),
            },
            Command::Waypoint { ship, waypoint } => {
                let s = usize::from(ship);
                if s >= self.ships.len() || self.ships[s].team != team {
                    return Outcome::Refused(Refusal::NotOwnShip);
                }
                if !self.in_match(s) {
                    return Outcome::Refused(Refusal::ShipLost);
                }
                if !is_capital_ship(cat.hull(self.ships[s].hull)) {
                    return Outcome::Refused(Refusal::NotCapital);
                }
                let limit = POINT_LIMIT_FRAC * self.cfg.arena_radius;
                self.command.waypoints[s] = match waypoint {
                    Waypoint::Unset => Waypoint::Unset,
                    Waypoint::At(p) if finite(p) => Waypoint::At(clamp_to_disc(p, limit)),
                    Waypoint::At(_) => return Outcome::Refused(Refusal::BadPoint),
                };
                Outcome::Applied
            }
            Command::Squad {
                squad,
                members,
                order,
            } => {
                let k = usize::from(squad);
                if k >= MAX_SQUADS {
                    return Outcome::Refused(Refusal::NoSuchSquad);
                }
                let mut kept = 0u32;
                for s in 0..self.ships.len() {
                    if members & (1 << s) != 0 && self.squad_eligible(cat, team, s) {
                        kept |= 1 << s;
                    }
                }
                let clean = self.sanitize_order(team, order);
                let t = usize::from(team);
                for (j, other) in self.command.squads[t].iter_mut().enumerate() {
                    if j != k {
                        other.members &= !kept;
                    }
                }
                self.command.squads[t][k] = Squad {
                    members: kept,
                    order: clean,
                };
                if kept != members || clean != order {
                    Outcome::Sanitized
                } else {
                    Outcome::Applied
                }
            }
        }
    }

    /// Launch one reserve of `team` (SIM_SPEC §5.9). On success the ship is present
    /// at the bay mouth (pushed out by its bound radius plus `LAUNCH_CLEARANCE`),
    /// heading along the bay direction at the carrier's velocity plus `LAUNCH_SPEED`,
    /// controls locked for `LAUNCH_LOCK_TICKS`; the bay cools down for
    /// `BAY_COOLDOWN_TICKS`; `Launch` is emitted.
    pub fn launch(
        &mut self,
        cat: &Catalogue,
        team: u8,
        hull: Option<HullId>,
        bay: Option<u8>,
    ) -> Result<(ShipIdx, u8), Refusal> {
        let t = usize::from(team & 1);
        let carrier = self.mission.carrier[t];
        if carrier == NONE {
            return Err(Refusal::NoCarrier);
        }
        let c = &self.ships[usize::from(carrier)];
        if !c.active() {
            return Err(Refusal::CarrierLost);
        }
        let c_hull = cat.hull(c.hull);
        if self.reserves[t].is_empty() {
            return Err(Refusal::HangarEmpty);
        }
        let pick = match hull {
            None => 0,
            Some(h) => self.reserves[t]
                .iter()
                .position(|&s| self.ships[usize::from(s)].hull == h)
                .ok_or(Refusal::NoReserveOfHull)?,
        };
        let n_bays = c_hull.bays.len();
        let ready = |b: usize| self.tick >= self.mission.bay_ready[t][b];
        let b = match bay {
            Some(b) => {
                let b = usize::from(b);
                if b >= n_bays {
                    return Err(Refusal::NoSuchBay);
                }
                if !ready(b) {
                    return Err(Refusal::BayBusy);
                }
                b
            }
            None => (0..n_bays)
                .filter(|&b| ready(b))
                .min_by_key(|&b| (self.mission.bay_ready[t][b], b))
                .ok_or(if n_bays == 0 {
                    Refusal::NoSuchBay
                } else {
                    Refusal::BayBusy
                })?,
        };
        let bay_def = &c_hull.bays[b];
        let mouth = c.to_world(bay_def.pos);
        let dir = bay_def.dir.rotated(c.heading);
        let c_vel = c.vel;
        let slot = self.reserves[t].remove(pick);
        let tick = self.tick;
        let ship: &mut Ship = &mut self.ships[usize::from(slot)];
        let reach = cat.hull(ship.hull).bound_radius + LAUNCH_CLEARANCE;
        ship.attach = Attach::None;
        ship.parent = NONE;
        ship.present = true;
        ship.pos = mouth + dir * reach;
        ship.heading = dir.angle();
        ship.vel = c_vel + dir * LAUNCH_SPEED;
        ship.omega = 0.0;
        ship.arrive_tick = tick;
        ship.control_lock_until = tick + LAUNCH_LOCK_TICKS;
        ship.queue = [ShipAction::IDLE; MAX_REACTION_TICKS];
        self.mission.bay_ready[t][b] = tick + BAY_COOLDOWN_TICKS;
        self.events.push(Event::Launch {
            ship: slot,
            carrier,
            bay: b as u8,
            pos: mouth,
            dir,
        });
        Ok((slot, b as u8))
    }

    fn capital_status(&self, cat: &Catalogue, slot: ShipIdx) -> CapitalStatus {
        let s = &self.ships[usize::from(slot)];
        let hull = cat.hull(s.hull);
        CapitalStatus {
            slot,
            hull: s.hull,
            alive: s.alive,
            hp: s.hp,
            max_hp: hull.hp,
            shield: s.shield,
            max_shield: hull.shield.map_or(0.0, |sh| sh.hp),
            pos: s.pos,
            vel: s.vel,
            heading: s.heading,
        }
    }

    /// `team`'s commander observation now (DESIGN §7; fields in [`CommanderObs`]).
    pub fn commander_obs(&self, cat: &Catalogue, team: u8) -> CommanderObs {
        let t = usize::from(team & 1);
        let n_hulls = cat.hulls.len();
        let mut obs = CommanderObs {
            team: team & 1,
            tick: self.tick,
            ticks_left: self.cfg.time_limit_ticks.saturating_sub(self.tick),
            mission: self.cfg.mission.kind(),
            in_space: vec![0; n_hulls],
            arriving: vec![0; n_hulls],
            reserves: vec![0; n_hulls],
            enemy_visible: vec![0; n_hulls],
            own_carrier: None,
            enemy_carrier: None,
            bays_ready: Vec::new(),
            convoy: self.convoy_status(),
            transports: Vec::new(),
            squads: self.command.squads[t],
        };
        for (s, ship) in self.ships.iter().enumerate() {
            let h = usize::from(ship.hull);
            if ship.team == obs.team {
                if ship.active() {
                    obs.in_space[h] += 1;
                } else if ship.alive && ship.attach == Attach::Docked {
                    obs.reserves[h] += 1;
                } else if self.in_match(s) {
                    obs.arriving[h] += 1;
                }
                if ship.active() && is_transport(cat.hull(ship.hull)) {
                    obs.transports.push(self.capital_status(cat, s as ShipIdx));
                }
            } else if ship.active() {
                obs.enemy_visible[h] += 1;
            }
        }
        let own = self.mission.carrier[t];
        if own != NONE {
            obs.own_carrier = Some(self.capital_status(cat, own));
            let c = &self.ships[usize::from(own)];
            obs.bays_ready = (0..cat.hull(c.hull).bays.len())
                .map(|b| c.active() && self.tick >= self.mission.bay_ready[t][b])
                .collect();
        }
        let enemy = self.mission.carrier[1 - t];
        if enemy != NONE && self.ships[usize::from(enemy)].active() {
            obs.enemy_carrier = Some(self.capital_status(cat, enemy));
        }
        obs
    }

    /// Slots of `team`'s docked reserves, in launch order.
    pub fn hangar(&self, team: u8) -> &[ShipIdx] {
        &self.reserves[usize::from(team & 1)]
    }

    /// The squad `slot` belongs to (its team's index), if any.
    pub fn squad_of(&self, slot: ShipIdx) -> Option<u8> {
        let s = usize::from(slot);
        let team = usize::from(self.ships.get(s)?.team);
        self.command.squads[team]
            .iter()
            .position(|q| q.contains(s))
            .map(|k| k as u8)
    }

    /// The carrier slot of `team`, `NONE` without one.
    pub fn carrier_of(&self, team: u8) -> ShipIdx {
        self.mission.carrier[usize::from(team & 1)]
    }

    /// `slot`'s jump state (convoy transports; `Idle` for every other ship).
    pub fn jump_state(&self, slot: ShipIdx) -> JumpState {
        self.mission.jump[usize::from(slot)]
    }
}
