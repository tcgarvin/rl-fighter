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
//! - **Station assault** (v9): team 0 defends a static `carrier`-role hull (the
//!   station: turrets, bays, no engines) placed on its side; its first `jump_in[0]`
//!   strike craft start on picket in front of it, the rest in its hangar. Team 1
//!   attacks from the far side with a mobile carrier, as in a carrier battle: its first
//!   `jump_in[1]` strike craft jump in, the rest wait docked. Team 1 wins by destroying
//!   the station; team 0 wins on the clock, or once the attacker's carrier and every
//!   one of its strike craft are gone. The station sits in `MissionState.carrier[0]`,
//!   so hangars, launches, the capital-ship script and both commanders treat it as
//!   team 0's carrier. `StationAssault.reads_as` picks what the nets read: a carrier
//!   battle for both sides, or a convoy escort (team 0 the defender). v10: the attacker
//!   may bring a `line`-role ship (the dreadnought) beside its carrier; it starts present
//!   at tick 0 next to the carrier, and the assault is repelled only once it is gone
//!   too. The defender may be any static carrier-role hull (the v10 `citadel`).
//!
//! RNG draw order at setup (changing it is a `SIM_VERSION` bump): deathmatch draws
//! exactly as v3 (`arrival.rs`). A carrier battle draws, per team in order, the
//! carrier's `y` offset `range(-CARRIER_Y_JITTER, CARRIER_Y_JITTER)`, then the
//! jump-in schedule of the ships that jump in (`arrival.rs`, teams with no jump-in
//! ships draw nothing). A convoy escort places team 0 without drawing and then draws
//! team 1's jump-in schedule. A station assault (v9) draws the station's `y`, then the
//! attacker carrier's `y` (both `range(-CARRIER_Y_JITTER, CARRIER_Y_JITTER)`), then team
//! 1's jump-in schedule; the picket is placed without drawing.

use crate::actions::ShipAction;
use crate::arrival;
use crate::command::{COMMAND_TICKS, Order};
use crate::data::{Catalogue, HullDef};
use crate::events::Event;
use crate::hash::{StateHash, StateHasher};
use crate::math::{PI, Vec2};
use crate::order::effective_order;
use crate::setup::{MatchConfig, SetupError, arena_radius_for};
use crate::state::{
    Attach, MAX_BAYS, MAX_REACTION_TICKS, MAX_SHIPS, MAX_THRUSTERS, Match, MatchPhase, NONE,
    ShipIdx, WINNER_DRAW,
};

/// Hull roles: `carrier`, the ship a carrier battle is won and lost by (and that owns
/// bays); `transport`, the ships a convoy escort is about; v10 `line`, a gun capital
/// ship (the dreadnought) with no bays. Defined with the hull data (rule 14).
pub use crate::data::hull::{ROLE_CARRIER, ROLE_LINE, ROLE_TRANSPORT};

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

/// Station assault (v9): the station sits this fraction of the arena radius out on
/// team 0's side (`x = -STATION_X_FRAC R`), heading `+x`, at rest.
pub const STATION_X_FRAC: f32 = 0.35;
/// The defender's picket: its first `jump_in[0]` strike craft start present at tick 0,
/// `PICKET_RANGE` m from the station's centre toward the attackers (`+x`), fanned
/// `PICKET_SPREAD` rad apart, at rest, heading `+x`.
pub const PICKET_RANGE: f32 = 70.0;
pub const PICKET_SPREAD: f32 = 0.45;
/// Default `jump_in` of a station assault: the defender's picket, the attacker's first
/// wave.
pub const DEFAULT_STATION_JUMP_IN: [u8; 2] = [2, 3];
/// v10: the attacker's line ship (the dreadnought) starts this far ahead of its carrier
/// (toward the station) and `LINE_START_SIDE` m to the side of it, toward the arena's
/// centre line, under way at `CARRIER_START_SPEED_FRAC` of its cap.
pub const LINE_START_AHEAD: f32 = 40.0;
pub const LINE_START_SIDE: f32 = 75.0;
/// v10: a station assault of more than this many ships (the v9 roster's 16; the v10
/// citadel roster has 19) fights in `BIG_STATION_ARENA_RADIUS`: the arena grows with
/// the fleets (DESIGN §6), and the dreadnought has to start outside the citadel's lance
/// range (430 m).
pub const STATION_SHIPS_V9: usize = 16;
pub const BIG_STATION_ARENA_RADIUS: f32 = 550.0;

/// Default time limits per mission, ticks.
pub const DEATHMATCH_TIME_LIMIT_TICKS: u32 = 2700;
pub const CARRIER_BATTLE_TIME_LIMIT_TICKS: u32 = 4500;
pub const CONVOY_TIME_LIMIT_TICKS: u32 = 3600;
/// v9: the attacker has this long (150 s, a carrier battle's limit) to destroy the
/// station.
pub const STATION_TIME_LIMIT_TICKS: u32 = 4500;

pub fn is_carrier(hull: &HullDef) -> bool {
    hull.role == ROLE_CARRIER
}

pub fn is_transport(hull: &HullDef) -> bool {
    hull.role == ROLE_TRANSPORT
}

/// v10: a line ship (the dreadnought).
pub fn is_line(hull: &HullDef) -> bool {
    hull.role == ROLE_LINE
}

/// Carriers, transports and (v10) line ships: flown by the capital-ship scripts, never
/// in squads (a waypoint, not an order, steers them).
pub fn is_capital_ship(hull: &HullDef) -> bool {
    is_carrier(hull) || is_transport(hull) || is_line(hull)
}

/// Mission without its parameters; the code the bindings exchange.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum MissionKind {
    #[default]
    Deathmatch = 0,
    CarrierBattle = 1,
    ConvoyEscort = 2,
    /// v9.
    StationAssault = 3,
}

impl MissionKind {
    pub fn index(self) -> u8 {
        self as u8
    }

    /// Every mission, in code order.
    pub const ALL: [MissionKind; 4] = [
        MissionKind::Deathmatch,
        MissionKind::CarrierBattle,
        MissionKind::ConvoyEscort,
        MissionKind::StationAssault,
    ];

    /// `"deathmatch"`, `"carrier_battle"`, `"convoy_escort"`, `"station_assault"`.
    pub fn name(self) -> &'static str {
        match self {
            MissionKind::Deathmatch => "deathmatch",
            MissionKind::CarrierBattle => "carrier_battle",
            MissionKind::ConvoyEscort => "convoy_escort",
            MissionKind::StationAssault => "station_assault",
        }
    }

    pub fn from_name(name: &str) -> Option<MissionKind> {
        match name {
            "deathmatch" => Some(MissionKind::Deathmatch),
            "carrier_battle" => Some(MissionKind::CarrierBattle),
            "convoy_escort" => Some(MissionKind::ConvoyEscort),
            "station_assault" => Some(MissionKind::StationAssault),
            _ => None,
        }
    }

    /// The default time limit of the mission (ticks).
    pub fn default_time_limit_ticks(self) -> u32 {
        match self {
            MissionKind::Deathmatch => DEATHMATCH_TIME_LIMIT_TICKS,
            MissionKind::CarrierBattle => CARRIER_BATTLE_TIME_LIMIT_TICKS,
            MissionKind::ConvoyEscort => CONVOY_TIME_LIMIT_TICKS,
            MissionKind::StationAssault => STATION_TIME_LIMIT_TICKS,
        }
    }
}

/// The arena radius for a mission with `n_ships` ships in total: the one per-mission
/// rule (DESIGN §6). Every mission uses [`arena_radius_for`] (450 m): the pilot obs
/// scales distances by the radius, so pilot v1 sees the inputs it trained on, and both
/// mission layouts fit (a carrier at `0.72 R`, the convoy route from `-0.55 R` to
/// `+0.75 R` across the centre). The WP-S2 mission survey kept it: the missions balance
/// at 450 m (lab/runs/2026-10-30-mission-survey); a change belongs here. v10: a station
/// assault of more than `STATION_SHIPS_V9` ships (the citadel's) uses
/// `BIG_STATION_ARENA_RADIUS` (550 m).
pub fn arena_radius_for_mission(kind: MissionKind, n_ships: usize) -> f32 {
    match kind {
        MissionKind::StationAssault if n_ships > STATION_SHIPS_V9 => BIG_STATION_ARENA_RADIUS,
        MissionKind::Deathmatch
        | MissionKind::CarrierBattle
        | MissionKind::ConvoyEscort
        | MissionKind::StationAssault => arena_radius_for(n_ships),
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
// Convoys are balanced for the 2026-11-01 champion, a far deadlier pilot than the v1 they
// were first tuned for (lab/runs/2026-11-01-fighters-v2/convoy_balance.md): four escorts
// against six raiders, and enough freighters that the raid needs three or four kills.
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
const CONVOY_6: &[&str] = &[
    "freighter",
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
const CONVOY_7: &[&str] = &[
    "freighter",
    "freighter",
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
const RAIDERS_6: &[&str] = &[
    "fighter", "fighter", "strafer", "gunship", "fighter", "strafer",
];
// Station assault (v9), balanced script against script
// (lab/runs/2026-11-19-station-bomber/results.md). The defender's first two strike craft
// start on picket, the attacker's first three jump in.
const STATION_GARRISON_6: &[&str] = &[
    "station", "fighter", "strafer", "fighter", "gunship", "fighter", "strafer",
];
const STATION_STRIKE_8: &[&str] = &[
    "carrier", "fighter", "bomber", "fighter", "bomber", "strafer", "bomber", "fighter", "gunship",
];
// Station assault v10 (the citadel; lab/runs/2026-11-19-citadel-dreadnought/plan.md and
// results.md): the citadel and seven against a carrier, a dreadnought and nine. 19 ships,
// so a 550 m arena (`arena_radius_for_mission`).
const CITADEL_GARRISON_7: &[&str] = &[
    "citadel", "fighter", "strafer", "fighter", "gunship", "fighter", "strafer", "fighter",
];
const CITADEL_STRIKE_9: &[&str] = &[
    "carrier",
    "dreadnought",
    "fighter",
    "bomber",
    "fighter",
    "bomber",
    "strafer",
    "bomber",
    "fighter",
    "gunship",
    "fighter",
];

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
const STATION_ROSTERS: &[MissionRoster] = &[
    MissionRoster {
        name: "strike of 8",
        fleets: [STATION_GARRISON_6, STATION_STRIKE_8],
    },
    // v10.
    MissionRoster {
        name: "citadel",
        fleets: [CITADEL_GARRISON_7, CITADEL_STRIKE_9],
    },
];
const CONVOY_ROSTERS: &[MissionRoster] = &[
    MissionRoster {
        name: "5 freighters",
        fleets: [CONVOY_5, RAIDERS_6],
    },
    MissionRoster {
        name: "6 freighters",
        fleets: [CONVOY_6, RAIDERS_6],
    },
    MissionRoster {
        name: "7 freighters",
        fleets: [CONVOY_7, RAIDERS_6],
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
        MissionKind::StationAssault => STATION_ROSTERS,
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

/// What the nets read a station assault as (v9): the mission one-hot of the pilot obs
/// and the commander's role one-hot have no station entry (`OBS_DIM` and
/// `COMMANDER_IO_VERSION` are unchanged), so the mission is shown as one they know.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum StationReadsAs {
    /// A carrier battle for both sides: symmetric, the station is "my carrier" or "the
    /// enemy carrier".
    #[default]
    Carrier,
    /// A convoy escort: team 0 reads as the convoy's defender, team 1 as its attacker,
    /// so the nets see the asymmetry (and, from the convoy, a clock on the defender's
    /// side), but no transports.
    Convoy,
}

impl StationReadsAs {
    /// `"carrier"`, `"convoy"`.
    pub fn name(self) -> &'static str {
        match self {
            StationReadsAs::Carrier => "carrier",
            StationReadsAs::Convoy => "convoy",
        }
    }

    pub fn from_name(name: &str) -> Option<StationReadsAs> {
        match name {
            "carrier" => Some(StationReadsAs::Carrier),
            "convoy" => Some(StationReadsAs::Convoy),
            _ => None,
        }
    }

    /// The mission the nets read.
    pub fn kind(self) -> MissionKind {
        match self {
            StationReadsAs::Carrier => MissionKind::CarrierBattle,
            StationReadsAs::Convoy => MissionKind::ConvoyEscort,
        }
    }
}

/// Station assault parameters (v9).
#[derive(Clone, Debug, PartialEq)]
pub struct StationAssault {
    /// Team 0: strike craft (fleet order) on picket at tick 0, the rest docked in the
    /// station. Team 1: strike craft that jump in, the rest docked in its carrier.
    /// Clamped to the wing size.
    pub jump_in: [u8; 2],
    /// What the pilot obs and the commander inputs show the mission as.
    pub reads_as: StationReadsAs,
}

impl Default for StationAssault {
    fn default() -> Self {
        StationAssault {
            jump_in: DEFAULT_STATION_JUMP_IN,
            reads_as: StationReadsAs::Carrier,
        }
    }
}

/// What the match is for (SIM_SPEC §5.10).
#[derive(Clone, Debug, Default, PartialEq)]
pub enum Mission {
    #[default]
    Deathmatch,
    CarrierBattle(CarrierBattle),
    ConvoyEscort(ConvoyEscort),
    /// v9.
    StationAssault(StationAssault),
}

impl Mission {
    pub fn kind(&self) -> MissionKind {
        match self {
            Mission::Deathmatch => MissionKind::Deathmatch,
            Mission::CarrierBattle(_) => MissionKind::CarrierBattle,
            Mission::ConvoyEscort(_) => MissionKind::ConvoyEscort,
            Mission::StationAssault(_) => MissionKind::StationAssault,
        }
    }

    /// The mission the nets read (v9): the kind, except that a station assault reads
    /// as its `reads_as`. Indexes the pilot obs's mission one-hot and the commander's
    /// role one-hot, which have one entry per mission before v9.
    pub fn obs_kind(&self) -> MissionKind {
        match self {
            Mission::StationAssault(sa) => sa.reads_as.kind(),
            other => other.kind(),
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
            MissionKind::StationAssault => Mission::StationAssault(StationAssault::default()),
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
    /// v9: the attackers destroyed the station.
    StationDestroyed = 6,
    /// v9: the attacker's carrier and every one of its strike craft are gone.
    AssaultRepelled = 7,
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
            EndReason::StationDestroyed => "station_destroyed",
            EndReason::AssaultRepelled => "assault_repelled",
        }
    }

    /// Every reason, in code order (the bindings' `END_REASONS`).
    pub const ALL: [EndReason; 8] = [
        EndReason::NotOver,
        EndReason::Eliminated,
        EndReason::TimeLimit,
        EndReason::CarrierDestroyed,
        EndReason::ConvoyThrough,
        EndReason::ConvoyDestroyed,
        EndReason::StationDestroyed,
        EndReason::AssaultRepelled,
    ];
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
    /// Per team: the carrier's slot (carrier battle; v9 station assault: team 0's is the
    /// station), else `NONE`.
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
    let lines = |team: usize| count(team, is_line);
    match &cfg.mission {
        Mission::Deathmatch => Ok(()),
        Mission::CarrierBattle(_) | Mission::ConvoyEscort(_) if lines(0) + lines(1) > 0 => {
            Err(mission_error(format!(
                "{}: line ships (the dreadnought) fight only in a deathmatch or a station \
                 assault",
                cfg.mission.kind().name()
            )))
        }
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
        Mission::StationAssault(_) => {
            for team in 0..2 {
                let carriers = count(team, is_carrier);
                if carriers != 1 {
                    return Err(mission_error(format!(
                        "station assault: team {team} needs exactly one carrier-role ship \
                         (team 0 its station), has {carriers}"
                    )));
                }
                if count(team, is_transport) > 0 {
                    return Err(mission_error(format!(
                        "station assault: team {team} has a transport (convoy ships only fly convoys)"
                    )));
                }
            }
            let stations = |team: usize| count(team, |h| is_carrier(h) && h.is_static);
            if stations(0) != 1 {
                return Err(mission_error(
                    "station assault: team 0's carrier-role ship must be static (the station)"
                        .to_string(),
                ));
            }
            if stations(1) != 0 {
                return Err(mission_error(
                    "station assault: team 1 attacks with a mobile carrier, not a station"
                        .to_string(),
                ));
            }
            if lines(0) != 0 || lines(1) > 1 {
                return Err(mission_error(format!(
                    "station assault: only the attacker may bring a line ship, at most one \
                     (team 0 has {}, team 1 {})",
                    lines(0),
                    lines(1)
                )));
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
        if let Some(layout) = self.cfg.start_layout.clone() {
            // Validated: a deathmatch, a carrier battle or a station assault, one start
            // per slot. No jump-in, so no rng draw.
            let hull = self.cfg.start_hull.clone();
            for (s, (ship, start)) in self.ships.iter_mut().zip(&layout).enumerate() {
                ship.pos = start.pos;
                ship.vel = start.vel;
                ship.heading = start.heading;
                ship.present = true;
                if let Some(frac) = &hull {
                    ship.hp = frac[s] * cat.hull(ship.hull).hp;
                }
                if self.cfg.drill {
                    // Nobody acts before the orders land, so the first action any ship
                    // chooses comes from an obs that shows them (`act_mask`).
                    ship.control_lock_until = COMMAND_TICKS + 1 + u32::from(ship.reaction_ticks);
                }
            }
            // v11 (the dock drills): a carrier battle or a station assault laid out by
            // hand has every ship on the field and nobody in a hangar; each team's
            // carrier-role ship (validated: exactly one) is its carrier, the station
            // team 0's. No waypoint is set: a commander gives one.
            if matches!(
                self.cfg.mission,
                Mission::CarrierBattle(_) | Mission::StationAssault(_)
            ) {
                for team in 0..2u8 {
                    let carrier = (0..self.ships.len())
                        .find(|&i| {
                            self.ships[i].team == team && is_carrier(cat.hull(self.ships[i].hull))
                        })
                        .expect("validated: one carrier per team");
                    self.mission.carrier[usize::from(team)] = carrier as ShipIdx;
                }
            }
            return;
        }
        match self.cfg.mission.clone() {
            Mission::Deathmatch => {
                arrival::schedule_arrivals(&mut self.ships, &mut self.rng, self.cfg.arena_radius);
            }
            Mission::CarrierBattle(cb) => self.setup_carrier_battle(cat, &cb),
            Mission::ConvoyEscort(ce) => self.setup_convoy(cat, &ce),
            Mission::StationAssault(sa) => self.setup_station_assault(cat, &sa),
        }
    }

    /// v9 (module docs): the station and its picket for team 0, a carrier battle side
    /// for team 1.
    fn setup_station_assault(&mut self, cat: &Catalogue, sa: &StationAssault) {
        let radius = self.cfg.arena_radius;
        let mut jumps = [false; MAX_SHIPS];
        for team in 0..2u8 {
            let t = usize::from(team);
            let attacker = team == 1;
            let heading = if attacker { PI } else { 0.0 };
            let x = if attacker {
                CARRIER_X_FRAC * radius
            } else {
                -STATION_X_FRAC * radius
            };
            let y = self.rng.range(-CARRIER_Y_JITTER, CARRIER_Y_JITTER);
            let pos = Vec2::new(x, y);
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
            c.present = true;
            if attacker {
                c.vel = fwd * (CARRIER_START_SPEED_FRAC * cat.hull(c.hull).speed_cap);
                self.command.waypoints[carrier] =
                    crate::command::Waypoint::At(pos + fwd * CARRIER_HOLD_AHEAD);
            }
            self.mission.carrier[t] = carrier as ShipIdx;

            // v10: the attacker's line ship starts beside its carrier, under way, with no
            // waypoint (its script closes on the station; the scripted commander may hold
            // it back). Validated: at most one, and only on team 1.
            let line = slots
                .iter()
                .copied()
                .find(|&i| is_line(cat.hull(self.ships[i].hull)));
            if let Some(i) = line {
                let side = if y >= 0.0 { -1.0 } else { 1.0 };
                let s = &mut self.ships[i];
                s.pos = pos + fwd * LINE_START_AHEAD + Vec2::new(0.0, side * LINE_START_SIDE);
                s.heading = heading;
                s.vel = fwd * (CARRIER_START_SPEED_FRAC * cat.hull(s.hull).speed_cap);
                s.present = true;
            }

            let wing: Vec<usize> = slots
                .into_iter()
                .filter(|&i| i != carrier && Some(i) != line)
                .collect();
            let n_first = usize::from(sa.jump_in[t]).min(wing.len());
            for (j, &i) in wing[..n_first].iter().enumerate() {
                if attacker {
                    jumps[i] = true;
                } else {
                    let off = (j as f32 - (n_first as f32 - 1.0) * 0.5) * PICKET_SPREAD;
                    let s = &mut self.ships[i];
                    s.pos = pos + Vec2::from_angle(off) * PICKET_RANGE;
                    s.heading = 0.0;
                    s.vel = Vec2::ZERO;
                    s.present = true;
                }
            }
            for &i in &wing[n_first..] {
                let s = &mut self.ships[i];
                s.attach = Attach::Docked;
                s.parent = carrier as ShipIdx;
                s.pos = pos;
                s.heading = heading;
                self.reserves[t].push(i as ShipIdx);
            }
        }
        arrival::schedule_arrivals_where(
            &mut self.ships,
            &mut self.rng,
            self.cfg.arena_radius,
            |s| jumps[usize::from(s.slot)],
        );
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

    /// Stage 12b (v4): mission rules after deaths. A carrier battle (v9: and a station
    /// assault, the station counting as a carrier) kills the docked reserves of a
    /// carrier that died (no `Death` events: they were never on the
    /// field) and empties its hangar. A convoy escort starts the jump charge of every
    /// active transport inside the jump radius (`JumpCharge`) and jumps out those whose
    /// charge is complete (`JumpOut`: not present, levels 0, queue idle, waypoint unset).
    pub(crate) fn step_mission_rules(&mut self) {
        match &self.cfg.mission {
            Mission::Deathmatch => {}
            Mission::CarrierBattle(_) | Mission::StationAssault(_) => {
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
        if self.cfg.drill {
            return self.drill_outcome(cat);
        }
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
            Mission::StationAssault(_) => {
                let station = usize::from(self.mission.carrier[0]);
                if !self.ships[station].alive {
                    Some((1, EndReason::StationDestroyed))
                } else if alive[1] == 0 {
                    Some((0, EndReason::AssaultRepelled))
                } else if time_up {
                    Some((0, EndReason::TimeLimit))
                } else {
                    None
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

    /// Stage 13 under drill rules (`MatchConfig.drill`): always a draw, since a drill has
    /// no result to pay. It ends on the clock, when team 0 has no strike craft left on
    /// the field (v11: a craft that docked has left it), or when team 1 is gone and
    /// nobody on team 0 still has a go-to (or a dock order) to finish, so killing the
    /// enemies on the way does not cut a go-to short. A dock drill thus ends on the step
    /// its pilot docks, as `Eliminated`; no deathmatch drill has a hangar.
    fn drill_outcome(&self, cat: &Catalogue) -> Option<(i8, EndReason)> {
        let strike = |s: usize| {
            let ship = &self.ships[s];
            ship.team == 0
                && self.in_match(s)
                && ship.attach != Attach::Docked
                && !is_capital_ship(cat.hull(ship.hull))
        };
        let pilots: Vec<usize> = (0..self.ships.len()).filter(|&s| strike(s)).collect();
        if pilots.is_empty() {
            return Some((WINNER_DRAW, EndReason::Eliminated));
        }
        if self.tick >= self.cfg.time_limit_ticks {
            return Some((WINNER_DRAW, EndReason::TimeLimit));
        }
        let enemies_left =
            (0..self.ships.len()).any(|s| self.ships[s].team == 1 && self.in_match(s));
        let going = pilots.iter().any(|&s| {
            matches!(
                effective_order(self, s),
                Order::GoTo { .. } | Order::Dock { .. }
            )
        });
        if enemies_left || going {
            None
        } else {
            Some((WINNER_DRAW, EndReason::Eliminated))
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
