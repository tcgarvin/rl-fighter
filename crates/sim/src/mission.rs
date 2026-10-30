//! Missions (SIM_SPEC §5.10, v4): what a match is for, how it is set up, the mission
//! rules stage (carrier loss, convoy jumps) and how it ends.
//!
//! - **Deathmatch** (the default) is the v3 match: everyone jumps in, the last team
//!   with ships wins, the time limit compares team values. With up to 8 ships its
//!   trajectories are bit-identical to SIM_VERSION 3.
//! - **Carrier battle**: each team has exactly one `carrier`-role ship, present at
//!   tick 0. The first `jump_in[team]` of its other ships (fleet order) jump in as
//!   usual; the rest wait docked in its hangar (`Match.reserves`) until the commander
//!   launches them (SIM_SPEC §5.9). Losing your carrier loses the match, and its
//!   docked ships die with it.
//! - **Convoy escort**: team 0's `transport`-role ships start present and moving in
//!   formation from `start` toward `jump_point`, with team 0's other ships (escorts)
//!   in formation around them. Team 1 jumps in. A transport inside `jump_radius` of
//!   the jump point charges for `charge_ticks` (it can still be killed) and then
//!   jumps out: it leaves the field, no longer counts for elimination and counts as
//!   escaped. Team 1 wins once `ceil(n / 2)` transports are destroyed; team 0 wins
//!   once so many have escaped that this can no longer happen; at the time limit the
//!   convoy has failed and team 1 wins.
//!
//! RNG draw order at setup (changing it is a `SIM_VERSION` bump): deathmatch draws
//! exactly as v3 (`arrival.rs`). A carrier battle draws, per team in order, the
//! carrier's `y` offset `range(-CARRIER_Y_JITTER, CARRIER_Y_JITTER)`, then the
//! jump-in schedule of the ships that jump in (`arrival.rs`, teams with no jump-in
//! ships draw nothing). A convoy escort places team 0 without drawing and then draws
//! team 1's jump-in schedule.

use crate::actions::ShipAction;
use crate::arrival;
use crate::data::{Catalogue, HullDef};
use crate::events::Event;
use crate::hash::{StateHash, StateHasher};
use crate::math::{PI, Vec2};
use crate::setup::{MatchConfig, SetupError, arena_radius_for};
use crate::state::{
    Attach, MAX_BAYS, MAX_REACTION_TICKS, MAX_SHIPS, MAX_THRUSTERS, Match, MatchPhase, NONE,
    ShipIdx, WINNER_DRAW,
};

/// Hull role of the ship a carrier battle is won and lost by (and that owns bays).
pub const ROLE_CARRIER: &str = "carrier";
/// Hull role of the ships a convoy escort is about.
pub const ROLE_TRANSPORT: &str = "transport";

/// A carrier sits this fraction of the arena radius from the centre, on its team's
/// side, clear of where its jump-in squads appear (`0.5 R + [0, 30)` m).
pub const CARRIER_X_FRAC: f32 = 0.72;
/// Uniform jitter of the carrier's `y`, metres.
pub const CARRIER_Y_JITTER: f32 = 40.0;
/// A carrier starts under way at this fraction of its speed cap, heading for the
/// arena centre.
pub const CARRIER_START_SPEED_FRAC: f32 = 0.4;
/// Its first waypoint (set at setup, "hold here") lies this far ahead of its start.
pub const CARRIER_HOLD_AHEAD: f32 = 60.0;
/// Strike craft of each team that jump in at the start of a carrier battle by
/// default; the rest start in the hangar.
pub const DEFAULT_CARRIER_JUMP_IN: u8 = 2;

/// Most transports in one convoy.
pub const MAX_CONVOY: usize = 8;
/// Convoy route in the standard layout: from `(0, -CONVOY_START_FRAC R)` to the jump
/// point at `(0, +CONVOY_JUMP_FRAC R)` (the defenders cross the arena bottom to top;
/// team 1 jumps in on the `+x` side, so it hits the convoy's flank).
pub const CONVOY_START_FRAC: f32 = 0.55;
pub const CONVOY_JUMP_FRAC: f32 = 0.75;
/// Default jump-point radius, metres.
pub const DEFAULT_JUMP_RADIUS: f32 = 40.0;
/// Default jump charge, ticks (2 s).
pub const DEFAULT_CHARGE_TICKS: u32 = 60;
/// A transport cruises at this fraction of its speed cap (the transport script,
/// `scripted::capital`), and the convoy starts already moving at it: transports and
/// escorts at this fraction of the slowest transport's cap.
pub const TRANSPORT_CRUISE_FRAC: f32 = 0.8;
pub const CONVOY_START_SPEED_FRAC: f32 = TRANSPORT_CRUISE_FRAC;
/// Convoy formation: transports in two files, `CONVOY_SPACING` m apart along the
/// route and `CONVOY_FILE_OFFSET` m either side of it (the lead to port).
pub const CONVOY_SPACING: f32 = 32.0;
pub const CONVOY_FILE_OFFSET: f32 = 12.0;
/// Escorts in pairs (port first) `ESCORT_OFFSET` m either side of the route; the
/// first pair `ESCORT_LEAD` m ahead of the lead transport, each next pair
/// `ESCORT_SPACING` m further back.
pub const ESCORT_OFFSET: f32 = 45.0;
pub const ESCORT_LEAD: f32 = 20.0;
pub const ESCORT_SPACING: f32 = 40.0;

/// Default time limits per mission, ticks.
pub const DEATHMATCH_TIME_LIMIT_TICKS: u32 = 2700;
pub const CARRIER_BATTLE_TIME_LIMIT_TICKS: u32 = 4500;
pub const CONVOY_TIME_LIMIT_TICKS: u32 = 3600;

pub fn is_carrier(hull: &HullDef) -> bool {
    hull.role == ROLE_CARRIER
}

pub fn is_transport(hull: &HullDef) -> bool {
    hull.role == ROLE_TRANSPORT
}

/// Carriers and transports: flown to waypoints by the capital-ship script, never in
/// squads.
pub fn is_capital_ship(hull: &HullDef) -> bool {
    is_carrier(hull) || is_transport(hull)
}

/// Mission without its parameters; the code the bindings exchange.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum MissionKind {
    #[default]
    Deathmatch = 0,
    CarrierBattle = 1,
    ConvoyEscort = 2,
}

impl MissionKind {
    pub fn index(self) -> u8 {
        self as u8
    }

    /// `"deathmatch"`, `"carrier_battle"`, `"convoy_escort"`.
    pub fn name(self) -> &'static str {
        match self {
            MissionKind::Deathmatch => "deathmatch",
            MissionKind::CarrierBattle => "carrier_battle",
            MissionKind::ConvoyEscort => "convoy_escort",
        }
    }

    pub fn from_name(name: &str) -> Option<MissionKind> {
        match name {
            "deathmatch" => Some(MissionKind::Deathmatch),
            "carrier_battle" => Some(MissionKind::CarrierBattle),
            "convoy_escort" => Some(MissionKind::ConvoyEscort),
            _ => None,
        }
    }

    /// The default time limit of the mission (ticks).
    pub fn default_time_limit_ticks(self) -> u32 {
        match self {
            MissionKind::Deathmatch => DEATHMATCH_TIME_LIMIT_TICKS,
            MissionKind::CarrierBattle => CARRIER_BATTLE_TIME_LIMIT_TICKS,
            MissionKind::ConvoyEscort => CONVOY_TIME_LIMIT_TICKS,
        }
    }
}

/// The arena radius for a mission with `n_ships` ships in total: the one per-mission
/// rule (DESIGN §6). Every mission uses [`arena_radius_for`] (450 m) today: the pilot
/// obs scales distances by the radius, so pilot v1 sees the inputs it trained on, and
/// both mission layouts fit (a carrier at `0.72 R`, the convoy route from `-0.55 R` to
/// `+0.75 R` across the centre). The WP-S2 mission survey kept it: the missions balance at 450 m (lab/runs/2026-10-30-mission-survey); a change belongs here.
pub fn arena_radius_for_mission(kind: MissionKind, n_ships: usize) -> f32 {
    match kind {
        MissionKind::Deathmatch | MissionKind::CarrierBattle | MissionKind::ConvoyEscort => {
            arena_radius_for(n_ships)
        }
    }
}

/// A default roster of a mission (WP-S2): what the live page drafts and the mission
/// survey measures. Hull names per team in slot order (fleet order: a carrier
/// battle's first `jump_in` strike craft jump in, the rest wait in the hangar in this
/// order; a convoy's transports form two files in this order).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct MissionRoster {
    /// Short label, unique within the mission ("wing of 8").
    pub name: &'static str,
    pub fleets: [&'static [&'static str]; 2],
}

const CARRIER_WING_8: &[&str] = &[
    "carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "strafer", "fighter",
    "gunship",
];
const CARRIER_WING_6: &[&str] = &[
    "carrier", "fighter", "fighter", "strafer", "fighter", "strafer", "gunship",
];
const CARRIER_WING_9: &[&str] = &[
    "carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "strafer", "fighter",
    "gunship", "fighter",
];
const CONVOY_4_3: &[&str] = &[
    "freighter",
    "freighter",
    "freighter",
    "freighter",
    "fighter",
    "strafer",
    "fighter",
];
const CONVOY_3: &[&str] = &[
    "freighter",
    "freighter",
    "freighter",
    "fighter",
    "strafer",
    "fighter",
    "gunship",
];
const CONVOY_5: &[&str] = &[
    "freighter",
    "freighter",
    "freighter",
    "freighter",
    "freighter",
    "fighter",
    "strafer",
    "fighter",
    "gunship",
];
const RAIDERS_8: &[&str] = &[
    "fighter", "fighter", "strafer", "gunship", "fighter", "strafer", "fighter", "fighter",
];
const RAIDERS_6: &[&str] = &[
    "fighter", "fighter", "strafer", "gunship", "fighter", "strafer",
];
const RAIDERS_5: &[&str] = &["fighter", "strafer", "fighter", "gunship", "fighter"];

const CARRIER_ROSTERS: &[MissionRoster] = &[
    MissionRoster {
        name: "wing of 8",
        fleets: [CARRIER_WING_8, CARRIER_WING_8],
    },
    MissionRoster {
        name: "wing of 6",
        fleets: [CARRIER_WING_6, CARRIER_WING_6],
    },
    MissionRoster {
        name: "wing of 9",
        fleets: [CARRIER_WING_9, CARRIER_WING_9],
    },
];
const CONVOY_ROSTERS: &[MissionRoster] = &[
    MissionRoster {
        name: "4 freighters",
        fleets: [CONVOY_4_3, RAIDERS_6],
    },
    MissionRoster {
        name: "3 freighters",
        fleets: [CONVOY_3, RAIDERS_5],
    },
    MissionRoster {
        name: "5 freighters",
        fleets: [CONVOY_5, RAIDERS_8],
    },
];

/// The default rosters of a mission, the first one the default of defaults (the
/// live page picks among them; the mission survey balances them). Deathmatch has
/// none: its rosters are budget drafts of 2–4 strike craft a side.
pub fn default_rosters(kind: MissionKind) -> &'static [MissionRoster] {
    match kind {
        MissionKind::Deathmatch => &[],
        MissionKind::CarrierBattle => CARRIER_ROSTERS,
        MissionKind::ConvoyEscort => CONVOY_ROSTERS,
    }
}

/// Carrier battle parameters.
#[derive(Clone, Debug, PartialEq)]
pub struct CarrierBattle {
    /// Per team: how many of its non-carrier ships (in fleet order) jump in at the
    /// start; the rest start docked. Clamped to the wing size.
    pub jump_in: [u8; 2],
}

impl Default for CarrierBattle {
    fn default() -> Self {
        CarrierBattle {
            jump_in: [DEFAULT_CARRIER_JUMP_IN; 2],
        }
    }
}

/// Convoy escort parameters; positions in metres, world frame.
#[derive(Clone, Debug, PartialEq)]
pub struct ConvoyEscort {
    /// Where the lead transport starts.
    pub start: Vec2,
    pub jump_point: Vec2,
    pub jump_radius: f32,
    /// Ticks a transport charges inside the jump radius before it jumps out.
    pub charge_ticks: u32,
    /// Starting speed as a fraction of the slowest transport's speed cap.
    pub start_speed_frac: f32,
}

impl ConvoyEscort {
    /// The standard layout for an arena of radius `arena_radius` (module docs).
    pub fn standard(arena_radius: f32) -> ConvoyEscort {
        ConvoyEscort {
            start: Vec2::new(0.0, -CONVOY_START_FRAC * arena_radius),
            jump_point: Vec2::new(0.0, CONVOY_JUMP_FRAC * arena_radius),
            jump_radius: DEFAULT_JUMP_RADIUS,
            charge_ticks: DEFAULT_CHARGE_TICKS,
            start_speed_frac: CONVOY_START_SPEED_FRAC,
        }
    }

    /// Unit vector from `start` to `jump_point`.
    pub fn route_dir(&self) -> Vec2 {
        (self.jump_point - self.start).normalized()
    }

    /// Fraction of the route from `start` to the jump radius covered at `pos`, in
    /// `[0, 1]` (projection onto the route).
    pub fn progress(&self, pos: Vec2) -> f32 {
        let route = self.jump_point - self.start;
        let usable = (route.length() - self.jump_radius).max(1e-3);
        (route.normalized().dot(pos - self.start) / usable).clamp(0.0, 1.0)
    }
}

/// What the match is for (SIM_SPEC §5.10).
#[derive(Clone, Debug, Default, PartialEq)]
pub enum Mission {
    #[default]
    Deathmatch,
    CarrierBattle(CarrierBattle),
    ConvoyEscort(ConvoyEscort),
}

impl Mission {
    pub fn kind(&self) -> MissionKind {
        match self {
            Mission::Deathmatch => MissionKind::Deathmatch,
            Mission::CarrierBattle(_) => MissionKind::CarrierBattle,
            Mission::ConvoyEscort(_) => MissionKind::ConvoyEscort,
        }
    }

    /// The mission of `kind` with default parameters for an arena of `arena_radius`.
    pub fn standard(kind: MissionKind, arena_radius: f32) -> Mission {
        match kind {
            MissionKind::Deathmatch => Mission::Deathmatch,
            MissionKind::CarrierBattle => Mission::CarrierBattle(CarrierBattle::default()),
            MissionKind::ConvoyEscort => {
                Mission::ConvoyEscort(ConvoyEscort::standard(arena_radius))
            }
        }
    }
}

/// Why a match ended; `NotOver` while it runs.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum EndReason {
    #[default]
    NotOver = 0,
    /// A team has no ships left (deathmatch; the attackers of a convoy).
    Eliminated = 1,
    TimeLimit = 2,
    CarrierDestroyed = 3,
    /// Enough transports escaped that the attackers can no longer win.
    ConvoyThrough = 4,
    /// At least half the convoy (rounded up) was destroyed.
    ConvoyDestroyed = 5,
}

impl EndReason {
    pub fn index(self) -> u8 {
        self as u8
    }

    pub fn name(self) -> &'static str {
        match self {
            EndReason::NotOver => "not_over",
            EndReason::Eliminated => "eliminated",
            EndReason::TimeLimit => "time_limit",
            EndReason::CarrierDestroyed => "carrier_destroyed",
            EndReason::ConvoyThrough => "convoy_through",
            EndReason::ConvoyDestroyed => "convoy_destroyed",
        }
    }
}

/// A transport's jump out of the convoy escort.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum JumpState {
    /// En route (every non-transport ship stays here).
    #[default]
    Idle,
    /// Inside the jump radius; jumps out on the step that reaches `until`.
    Charging { until: u32 },
    /// Jumped out: not present, alive but not counted for elimination, escaped.
    Departed,
}

impl JumpState {
    pub fn index(self) -> u8 {
        match self {
            JumpState::Idle => 0,
            JumpState::Charging { .. } => 1,
            JumpState::Departed => 2,
        }
    }
}

impl StateHash for JumpState {
    fn hash_into(&self, h: &mut StateHasher) {
        h.write_u8(self.index());
        h.write_u32(match *self {
            JumpState::Charging { until } => until,
            JumpState::Idle | JumpState::Departed => 0,
        });
    }
}

/// Convoy counts (SIM_SPEC §5.10).
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct ConvoyStatus {
    pub total: u8,
    /// Alive and on the field, not charging.
    pub en_route: u8,
    pub charging: u8,
    pub escaped: u8,
    pub destroyed: u8,
    /// Transports the attackers must destroy to win: `ceil(total / 2)`.
    pub to_destroy: u8,
    /// Transports that must escape for the defenders to win: `total - to_destroy + 1`.
    pub to_escape: u8,
    /// Mean route progress (`ConvoyEscort::progress`) of the transports not destroyed,
    /// escaped ones counting 1; 0 with none left.
    pub progress: f32,
}

/// Mission state on `Match` (hashed, v4).
#[derive(Clone, Debug, PartialEq)]
pub struct MissionState {
    pub end_reason: EndReason,
    /// Per team: the carrier's slot (carrier battle), else `NONE`.
    pub carrier: [ShipIdx; 2],
    /// Per team: the tick from which each bay of its carrier may launch again.
    pub bay_ready: [[u32; MAX_BAYS]; 2],
    /// Bit `s` set: slot `s` is a convoy transport (convoy escort).
    pub transports: u32,
    /// Per slot: jump-out state (only transports leave `Idle`).
    pub jump: [JumpState; MAX_SHIPS],
}

impl Default for MissionState {
    fn default() -> Self {
        MissionState {
            end_reason: EndReason::NotOver,
            carrier: [NONE; 2],
            bay_ready: [[0; MAX_BAYS]; 2],
            transports: 0,
            jump: [JumpState::Idle; MAX_SHIPS],
        }
    }
}

impl StateHash for MissionState {
    fn hash_into(&self, h: &mut StateHasher) {
        h.write_u8(self.end_reason.index());
        self.carrier.hash_into(h);
        for team in &self.bay_ready {
            team.hash_into(h);
        }
        h.write_u32(self.transports);
        self.jump.hash_into(h);
    }
}

fn mission_error(msg: String) -> SetupError {
    SetupError::Mission(msg)
}

/// Mission-specific checks of [`Match::new`] (after the generic ones).
pub(crate) fn validate(cat: &Catalogue, cfg: &MatchConfig) -> Result<(), SetupError> {
    let count = |team: usize, f: fn(&HullDef) -> bool| {
        cfg.fleets[team].iter().filter(|&&h| f(cat.hull(h))).count()
    };
    match &cfg.mission {
        Mission::Deathmatch => Ok(()),
        Mission::CarrierBattle(_) => {
            for team in 0..2 {
                let carriers = count(team, is_carrier);
                if carriers != 1 {
                    return Err(mission_error(format!(
                        "carrier battle: team {team} needs exactly one carrier, has {carriers}"
                    )));
                }
                if count(team, is_transport) > 0 {
                    return Err(mission_error(format!(
                        "carrier battle: team {team} has a transport (convoy ships only fly convoys)"
                    )));
                }
            }
            Ok(())
        }
        Mission::ConvoyEscort(c) => {
            let n = count(0, is_transport);
            if !(1..=MAX_CONVOY).contains(&n) {
                return Err(mission_error(format!(
                    "convoy escort: team 0 needs 1..={MAX_CONVOY} transports, has {n}"
                )));
            }
            if count(1, is_transport) > 0 {
                return Err(mission_error(
                    "convoy escort: team 1 (the attackers) cannot field transports".to_string(),
                ));
            }
            let finite = [c.start.x, c.start.y, c.jump_point.x, c.jump_point.y];
            if !finite.iter().all(|v| v.is_finite()) {
                return Err(mission_error(
                    "convoy escort: start and jump_point must be finite".to_string(),
                ));
            }
            if !(c.jump_radius.is_finite() && c.jump_radius > 0.0) {
                return Err(mission_error(format!(
                    "convoy escort: jump_radius must be positive, got {}",
                    c.jump_radius
                )));
            }
            if (c.jump_point - c.start).length() <= c.jump_radius {
                return Err(mission_error(
                    "convoy escort: the convoy must start outside the jump radius".to_string(),
                ));
            }
            if !(c.start_speed_frac.is_finite() && (0.0..=1.0).contains(&c.start_speed_frac)) {
                return Err(mission_error(format!(
                    "convoy escort: start_speed_frac must be in [0, 1], got {}",
                    c.start_speed_frac
                )));
            }
            Ok(())
        }
    }
}

impl Match {
    /// Place the ships for the mission and fill the mission and command state
    /// (called by `Match::new` with every ship built, not present, at the origin).
    pub(crate) fn setup_mission(&mut self, cat: &Catalogue) {
        match self.cfg.mission.clone() {
            Mission::Deathmatch => {
                arrival::schedule_arrivals(&mut self.ships, &mut self.rng, self.cfg.arena_radius);
            }
            Mission::CarrierBattle(cb) => self.setup_carrier_battle(cat, &cb),
            Mission::ConvoyEscort(ce) => self.setup_convoy(cat, &ce),
        }
    }

    fn setup_carrier_battle(&mut self, cat: &Catalogue, cb: &CarrierBattle) {
        let radius = self.cfg.arena_radius;
        let mut jumps = [false; MAX_SHIPS];
        for team in 0..2u8 {
            let side = if team == 0 { -1.0 } else { 1.0 };
            let heading = if team == 0 { 0.0 } else { PI };
            let y = self.rng.range(-CARRIER_Y_JITTER, CARRIER_Y_JITTER);
            let pos = Vec2::new(side * CARRIER_X_FRAC * radius, y);
            let slots: Vec<usize> = (0..self.ships.len())
                .filter(|&i| self.ships[i].team == team)
                .collect();
            let carrier = *slots
                .iter()
                .find(|&&i| is_carrier(cat.hull(self.ships[i].hull)))
                .expect("validated: one carrier per team");
            let fwd = Vec2::from_angle(heading);
            let c = &mut self.ships[carrier];
            c.pos = pos;
            c.heading = heading;
            c.vel = fwd * (CARRIER_START_SPEED_FRAC * cat.hull(c.hull).speed_cap);
            c.present = true;
            self.mission.carrier[usize::from(team)] = carrier as ShipIdx;
            self.command.waypoints[carrier] =
                crate::command::Waypoint::At(pos + fwd * CARRIER_HOLD_AHEAD);

            let wing: Vec<usize> = slots.into_iter().filter(|&i| i != carrier).collect();
            let n_jump = usize::from(cb.jump_in[usize::from(team)]).min(wing.len());
            for &i in &wing[..n_jump] {
                jumps[i] = true;
            }
            for &i in &wing[n_jump..] {
                let s = &mut self.ships[i];
                s.attach = Attach::Docked;
                s.parent = carrier as ShipIdx;
                s.pos = pos;
                s.heading = heading;
                self.reserves[usize::from(team)].push(i as ShipIdx);
            }
        }
        arrival::schedule_arrivals_where(
            &mut self.ships,
            &mut self.rng,
            self.cfg.arena_radius,
            |s| jumps[usize::from(s.slot)],
        );
    }

    fn setup_convoy(&mut self, cat: &Catalogue, ce: &ConvoyEscort) {
        let fwd = ce.route_dir();
        let port = fwd.perp();
        let heading = fwd.angle();
        let slowest = self
            .ships
            .iter()
            .filter(|s| s.team == 0 && is_transport(cat.hull(s.hull)))
            .map(|s| cat.hull(s.hull).speed_cap)
            .fold(f32::INFINITY, f32::min);
        let speed = ce.start_speed_frac * slowest;
        let (mut n_transport, mut n_escort) = (0usize, 0usize);
        for s in self.ships.iter_mut().filter(|s| s.team == 0) {
            if is_transport(cat.hull(s.hull)) {
                let i = n_transport;
                n_transport += 1;
                self.mission.transports |= 1 << s.slot;
                self.command.waypoints[usize::from(s.slot)] =
                    crate::command::Waypoint::At(ce.jump_point);
                let file = if i % 2 == 0 { 1.0 } else { -1.0 };
                s.pos = ce.start - fwd * (i as f32 * CONVOY_SPACING)
                    + port * (file * CONVOY_FILE_OFFSET);
                // Each transport points straight at the jump point: its script never
                // needs to turn (it barely can).
                let to_jump = (ce.jump_point - s.pos).normalized();
                s.heading = to_jump.angle();
                s.vel = to_jump * speed;
            } else {
                let j = n_escort;
                n_escort += 1;
                let side = if j % 2 == 0 { 1.0 } else { -1.0 };
                let along = ESCORT_LEAD - (j / 2) as f32 * ESCORT_SPACING;
                s.pos = ce.start + fwd * along + port * (side * ESCORT_OFFSET);
                s.heading = heading;
                s.vel = fwd * speed;
            }
            s.present = true;
        }
        arrival::schedule_arrivals_where(
            &mut self.ships,
            &mut self.rng,
            self.cfg.arena_radius,
            |s| s.team == 1,
        );
    }

    /// Whether slot `s` is still in the match for elimination: alive and not jumped
    /// out (pending arrivals and docked reserves count).
    pub fn in_match(&self, s: usize) -> bool {
        self.ships[s].alive && self.mission.jump[s] != JumpState::Departed
    }

    /// Stage 12b (v4): mission rules after deaths. A carrier battle kills the docked
    /// reserves of a carrier that died (no `Death` events: they were never on the
    /// field) and empties its hangar. A convoy escort starts the jump charge of every
    /// active transport inside the jump radius (`JumpCharge`) and jumps out those whose
    /// charge is complete (`JumpOut`: not present, levels 0, queue idle, waypoint unset).
    pub(crate) fn step_mission_rules(&mut self) {
        match &self.cfg.mission {
            Mission::Deathmatch => {}
            Mission::CarrierBattle(_) => {
                for team in 0..2 {
                    let carrier = self.mission.carrier[team];
                    if carrier == NONE || self.ships[usize::from(carrier)].alive {
                        continue;
                    }
                    for &slot in &self.reserves[team] {
                        let s = &mut self.ships[usize::from(slot)];
                        s.alive = false;
                        s.hp = 0.0;
                    }
                    self.reserves[team].clear();
                }
            }
            Mission::ConvoyEscort(ce) => {
                let (jump_point, radius, charge) = (ce.jump_point, ce.jump_radius, ce.charge_ticks);
                for slot in 0..self.ships.len() {
                    if self.mission.transports & (1 << slot) == 0 || !self.ships[slot].active() {
                        continue;
                    }
                    let ship = &mut self.ships[slot];
                    match self.mission.jump[slot] {
                        JumpState::Idle => {
                            if (ship.pos - jump_point).length() <= radius {
                                let until = self.tick + charge;
                                self.mission.jump[slot] = JumpState::Charging { until };
                                self.events.push(Event::JumpCharge {
                                    ship: slot as ShipIdx,
                                    pos: ship.pos,
                                    until,
                                });
                            }
                        }
                        JumpState::Charging { until } => {
                            if self.tick >= until {
                                self.mission.jump[slot] = JumpState::Departed;
                                ship.present = false;
                                ship.thrust_level = [0.0; MAX_THRUSTERS];
                                ship.queue = [ShipAction::IDLE; MAX_REACTION_TICKS];
                                self.command.waypoints[slot] = crate::command::Waypoint::Unset;
                                self.events.push(Event::JumpOut {
                                    ship: slot as ShipIdx,
                                    pos: ship.pos,
                                    heading: ship.heading,
                                });
                            }
                        }
                        JumpState::Departed => {}
                    }
                }
            }
        }
    }

    /// Convoy counts; all zero outside a convoy escort.
    pub fn convoy_status(&self) -> ConvoyStatus {
        let Mission::ConvoyEscort(ce) = &self.cfg.mission else {
            return ConvoyStatus::default();
        };
        let mut st = ConvoyStatus::default();
        let mut progress_sum = 0.0f32;
        for (slot, ship) in self.ships.iter().enumerate() {
            if self.mission.transports & (1 << slot) == 0 {
                continue;
            }
            st.total += 1;
            match self.mission.jump[slot] {
                JumpState::Departed => {
                    st.escaped += 1;
                    progress_sum += 1.0;
                }
                _ if !ship.alive => st.destroyed += 1,
                JumpState::Charging { .. } => {
                    st.charging += 1;
                    progress_sum += ce.progress(ship.pos);
                }
                JumpState::Idle => {
                    st.en_route += 1;
                    progress_sum += ce.progress(ship.pos);
                }
            }
        }
        st.to_destroy = st.total.div_ceil(2);
        st.to_escape = st.total - st.to_destroy + 1;
        let left = st.total - st.destroyed;
        st.progress = if left > 0 {
            progress_sum / f32::from(left)
        } else {
            0.0
        };
        st
    }

    /// Stage 13 outcome for the mission, or `None` while the match goes on.
    pub(crate) fn mission_outcome(&self, cat: &Catalogue) -> Option<(i8, EndReason)> {
        let mut alive = [0u32; 2];
        for (s, ship) in self.ships.iter().enumerate() {
            if self.in_match(s) {
                alive[usize::from(ship.team)] += 1;
            }
        }
        let time_up = self.tick >= self.cfg.time_limit_ticks;
        match &self.cfg.mission {
            Mission::Deathmatch => match alive {
                [0, 0] => Some((WINNER_DRAW, EndReason::Eliminated)),
                [0, _] => Some((1, EndReason::Eliminated)),
                [_, 0] => Some((0, EndReason::Eliminated)),
                _ if time_up => Some((self.value_winner(), EndReason::TimeLimit)),
                _ => None,
            },
            Mission::CarrierBattle(_) => {
                let up = |team: usize| self.ships[usize::from(self.mission.carrier[team])].alive;
                match (up(0), up(1)) {
                    (false, false) => Some((WINNER_DRAW, EndReason::CarrierDestroyed)),
                    (false, true) => Some((1, EndReason::CarrierDestroyed)),
                    (true, false) => Some((0, EndReason::CarrierDestroyed)),
                    _ if time_up => Some((self.carrier_tiebreak(cat), EndReason::TimeLimit)),
                    _ => None,
                }
            }
            Mission::ConvoyEscort(_) => {
                let c = self.convoy_status();
                if c.destroyed >= c.to_destroy {
                    Some((1, EndReason::ConvoyDestroyed))
                } else if c.escaped >= c.to_escape {
                    Some((0, EndReason::ConvoyThrough))
                } else if alive[1] == 0 {
                    Some((0, EndReason::Eliminated))
                } else if time_up {
                    Some((1, EndReason::TimeLimit))
                } else {
                    None
                }
            }
        }
    }

    /// Time-limit winner of a carrier battle: the carrier with the larger hull
    /// fraction, if the fractions differ by at least `VALUE_TIE_EPS`; else the
    /// deathmatch team value; else a draw.
    fn carrier_tiebreak(&self, cat: &Catalogue) -> i8 {
        let frac = |team: usize| {
            let c = &self.ships[usize::from(self.mission.carrier[team])];
            c.hp / cat.hull(c.hull).hp
        };
        let (f0, f1) = (frac(0), frac(1));
        if (f0 - f1).abs() >= crate::step::VALUE_TIE_EPS {
            if f0 > f1 { 0 } else { 1 }
        } else {
            self.value_winner()
        }
    }

    /// Winner by team value (`team_values`), or a draw within `VALUE_TIE_EPS`.
    fn value_winner(&self) -> i8 {
        let [v0, v1] = self.team_values();
        if (v0 - v1).abs() < crate::step::VALUE_TIE_EPS {
            WINNER_DRAW
        } else if v0 > v1 {
            0
        } else {
            1
        }
    }

    /// Stage 13: end the match if the mission says so: set `phase`, `winner` and the
    /// end reason, and emit `MatchEnd`.
    pub fn check_termination(&mut self, cat: &Catalogue) {
        if self.phase == MatchPhase::Over {
            return;
        }
        let Some((winner, reason)) = self.mission_outcome(cat) else {
            return;
        };
        self.phase = MatchPhase::Over;
        self.winner = winner;
        self.mission.end_reason = reason;
        self.events.push(Event::MatchEnd { winner, reason });
    }
}
