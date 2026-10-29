//! MatchConfig and Match::new (SIM_SPEC §2.1).

use core::fmt;

use crate::actions::ShipAction;
use crate::arrival;
use crate::data::{Catalogue, HullId};
use crate::events::EventBuf;
use crate::rng::Pcg32;
use crate::state::{
    MAX_HITS, MAX_PROJECTILES, MAX_REACTION_TICKS, MAX_SHIPS, Match, MatchPhase, Projectile, Ship,
    WINNER_NONE,
};

pub const DEFAULT_ARENA_RADIUS: f32 = 450.0;
/// 90 s at 30 Hz.
pub const DEFAULT_TIME_LIMIT_TICKS: u32 = 2700;
/// Default reaction delay, ticks (≈ 67 ms; SIM_SPEC §5 stage 3, v2).
pub const DEFAULT_REACTION_TICKS: u8 = 2;

#[derive(Clone, Debug, PartialEq)]
pub struct MatchConfig {
    pub seed: u64,
    pub arena_radius: f32,
    pub time_limit_ticks: u32,
    /// Ticks between choosing an action and applying it, for hulls without their own
    /// `reaction_ticks`; at most `MAX_REACTION_TICKS`.
    pub reaction_ticks: u8,
    /// Hulls of team 0 and team 1; at most `MAX_SHIPS` in total.
    pub fleets: [Vec<HullId>; 2],
}

impl Default for MatchConfig {
    fn default() -> Self {
        MatchConfig {
            seed: 0,
            arena_radius: DEFAULT_ARENA_RADIUS,
            time_limit_ticks: DEFAULT_TIME_LIMIT_TICKS,
            reaction_ticks: DEFAULT_REACTION_TICKS,
            fleets: [Vec::new(), Vec::new()],
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum SetupError {
    /// A team has no ships.
    EmptyFleet { team: u8 },
    /// More than `MAX_SHIPS` ships in total.
    TooManyShips { count: usize },
    /// A fleet names a hull id the catalogue does not have.
    UnknownHull { team: u8, hull: HullId },
    /// `arena_radius` is not a positive finite number.
    InvalidArenaRadius { radius: f32 },
    /// `time_limit_ticks` is 0.
    ZeroTimeLimit,
    /// `reaction_ticks` exceeds `MAX_REACTION_TICKS`.
    ReactionTooLong { ticks: u8 },
}

impl fmt::Display for SetupError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SetupError::EmptyFleet { team } => write!(f, "team {team} has no ships"),
            SetupError::TooManyShips { count } => {
                write!(f, "{count} ships in the match; at most {MAX_SHIPS} allowed")
            }
            SetupError::UnknownHull { team, hull } => {
                write!(f, "team {team} fleet has unknown hull id {hull}")
            }
            SetupError::InvalidArenaRadius { radius } => {
                write!(f, "arena_radius must be positive and finite, got {radius}")
            }
            SetupError::ZeroTimeLimit => write!(f, "time_limit_ticks must be at least 1"),
            SetupError::ReactionTooLong { ticks } => write!(
                f,
                "reaction_ticks {ticks} exceeds MAX_REACTION_TICKS = {MAX_REACTION_TICKS}"
            ),
        }
    }
}

impl std::error::Error for SetupError {}

fn validate(cat: &Catalogue, cfg: &MatchConfig) -> Result<(), SetupError> {
    if !(cfg.arena_radius.is_finite() && cfg.arena_radius > 0.0) {
        return Err(SetupError::InvalidArenaRadius {
            radius: cfg.arena_radius,
        });
    }
    if cfg.time_limit_ticks == 0 {
        return Err(SetupError::ZeroTimeLimit);
    }
    if usize::from(cfg.reaction_ticks) > MAX_REACTION_TICKS {
        return Err(SetupError::ReactionTooLong {
            ticks: cfg.reaction_ticks,
        });
    }
    let count = cfg.fleets[0].len() + cfg.fleets[1].len();
    if count > MAX_SHIPS {
        return Err(SetupError::TooManyShips { count });
    }
    for (team, fleet) in cfg.fleets.iter().enumerate() {
        let team = team as u8;
        if fleet.is_empty() {
            return Err(SetupError::EmptyFleet { team });
        }
        if let Some(&hull) = fleet.iter().find(|&&h| h as usize >= cat.hulls.len()) {
            return Err(SetupError::UnknownHull { team, hull });
        }
    }
    Ok(())
}

impl Match {
    /// Build a match: ships in slot order (team 0 then team 1), full health, initial
    /// power split, empty projectile pool, RNG seeded from `cfg.seed`. Each ship's
    /// reaction delay is its hull's `reaction_ticks` override, else the config's.
    pub fn new(cat: &Catalogue, cfg: &MatchConfig) -> Result<Match, SetupError> {
        validate(cat, cfg)?;
        let mut ships = Vec::with_capacity(cfg.fleets[0].len() + cfg.fleets[1].len());
        for (team, fleet) in cfg.fleets.iter().enumerate() {
            for &hull in fleet {
                let slot = ships.len() as u8;
                let def = cat.hull(hull);
                let d = def.reaction_ticks.unwrap_or(cfg.reaction_ticks);
                ships.push(Ship::new(def, hull, team as u8, slot, d));
            }
        }
        let mut m = Match {
            cfg: cfg.clone(),
            tick: 0,
            rng: Pcg32::new(cfg.seed),
            phase: MatchPhase::Running,
            winner: WINNER_NONE,
            ships,
            projectiles: [Projectile::DEAD; MAX_PROJECTILES],
            proj_next: 0,
            pending: [ShipAction::IDLE; MAX_SHIPS],
            applied: [ShipAction::IDLE; MAX_SHIPS],
            events: EventBuf::new(),
            hits: Vec::with_capacity(MAX_HITS),
            shots_fired: [0; MAX_SHIPS],
            dropped_hits: 0,
            rewards: [0.0; MAX_SHIPS],
            outside_arena: [false; MAX_SHIPS],
            reserves: [Vec::new(), Vec::new()],
        };
        arrival::schedule_arrivals(&mut m.ships, &mut m.rng, m.cfg.arena_radius);
        Ok(m)
    }
}
