//! MatchConfig and Match::new (SIM_SPEC §2.1).

use core::fmt;

use crate::actions::ShipAction;
use crate::command::{CommandState, CommanderMode};
use crate::data::{Catalogue, HullId};
use crate::events::EventBuf;
use crate::mission::{self, Mission, MissionState};
use crate::order::{self, OrderTrack};
use crate::reward::ORDER_SHAPING_GAMMA;
use crate::rng::Pcg32;
use crate::scripted::random_commander::RandomCommander;
use crate::state::{
    MAX_HITS, MAX_PROJECTILES, MAX_REACTION_TICKS, MAX_SHIPS, Match, MatchPhase, Projectile, Ship,
    WINNER_NONE,
};

pub const DEFAULT_ARENA_RADIUS: f32 = 450.0;
/// 90 s at 30 Hz.
pub const DEFAULT_TIME_LIMIT_TICKS: u32 = 2700;
/// Default reaction delay, ticks (≈ 67 ms; SIM_SPEC §5 stage 3, v2).
pub const DEFAULT_REACTION_TICKS: u8 = 2;

/// v5: ship slots a training env pads its rosters to (M3 stage B: carrier battles
/// and convoys with 4–5 strike craft a side fit in 12; deathmatch drafts need 8).
/// Live rosters use up to `MAX_SHIPS`. Bindings export it; the trainer sizes its
/// buffers with it.
pub const MAX_TRAIN_SHIPS: usize = 12;
const _: () = assert!(MAX_TRAIN_SHIPS <= MAX_SHIPS);

/// Extra arena radius per ship beyond a duel's two, metres (0: one size for all).
pub const ARENA_RADIUS_PER_SHIP: f32 = 0.0;

/// The arena radius for a match of `n_ships` ships in total (both teams):
/// `DEFAULT_ARENA_RADIUS` plus `ARENA_RADIUS_PER_SHIP` per ship beyond two. Training
/// rosters, the fleet eval and the live page all size their arenas with this one
/// rule (DESIGN §6), so change it here and nowhere else.
///
/// It is 450 m for every fleet size up to 8 ships: script-vs-script fleets
/// (lab/runs/2026-10-30-fleet-pilot/plan.md §2) at a growing radius (+25 m per
/// ship, 600 m for 4v4) had the same engagement and crash damage as at 450 m but
/// reached the time limit more often in 4v4 (0.28 vs 0.19), and the obs scale
/// distances by the radius, so one radius keeps the duel pilots' inputs where
/// they trained.
pub fn arena_radius_for(n_ships: usize) -> f32 {
    let extra = n_ships.saturating_sub(2) as f32;
    DEFAULT_ARENA_RADIUS + ARENA_RADIUS_PER_SHIP * extra
}

#[derive(Clone, Debug, PartialEq)]
pub struct MatchConfig {
    pub seed: u64,
    pub arena_radius: f32,
    pub time_limit_ticks: u32,
    /// Ticks between choosing an action and applying it, for hulls without their own
    /// `reaction_ticks`; at most `MAX_REACTION_TICKS`.
    pub reaction_ticks: u8,
    /// Hulls of team 0 and team 1; at most `MAX_SHIPS` in total. How they enter the
    /// match (jump in, start present, start docked) is the mission's business.
    pub fleets: [Vec<HullId>; 2],
    /// v4: what the match is for (SIM_SPEC §5.10); `Deathmatch` is the v3 match.
    pub mission: Mission,
    /// v4: who commands each team on the slow tick (SIM_SPEC §5.9).
    pub commanders: [CommanderMode; 2],
    /// v6, per team: hidden-order mode. A hidden team's pilots see no order: their obs
    /// has the `order` block, `order_ships` and the order-dependent `ship_extras`
    /// zeroed, exactly as a ship without an order (SIM_SPEC §7.2). Rewards, scripts and
    /// the commander are unaffected (the order-following eval's control arm).
    pub hide_orders: [bool; 2],
    /// Discount of the go-to order reward's shaping term `γΦ′ − Φ` (SIM_SPEC §8), in
    /// (0, 1]: the trainer's discount. It only changes `order_rewards`, which no ship
    /// observes and no script reads, so it is not part of the state hash and not a
    /// SIM_VERSION matter.
    pub order_shaping_gamma: f32,
}

impl Default for MatchConfig {
    fn default() -> Self {
        MatchConfig {
            seed: 0,
            arena_radius: DEFAULT_ARENA_RADIUS,
            time_limit_ticks: DEFAULT_TIME_LIMIT_TICKS,
            reaction_ticks: DEFAULT_REACTION_TICKS,
            fleets: [Vec::new(), Vec::new()],
            mission: Mission::Deathmatch,
            commanders: [CommanderMode::Scripted; 2],
            hide_orders: [false; 2],
            order_shaping_gamma: ORDER_SHAPING_GAMMA,
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
    /// `order_shaping_gamma` is not a finite number in (0, 1].
    InvalidOrderShapingGamma { gamma: f32 },
    /// v4: the fleets or parameters do not fit the mission.
    Mission(String),
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
            SetupError::InvalidOrderShapingGamma { gamma } => {
                write!(f, "order_shaping_gamma must be in (0, 1], got {gamma}")
            }
            SetupError::Mission(msg) => f.write_str(msg),
        }
    }
}

impl std::error::Error for SetupError {}

impl MatchConfig {
    /// Check the config against `cat` without building a match (the checks of
    /// [`Match::new`]).
    pub fn validate(&self, cat: &Catalogue) -> Result<(), SetupError> {
        validate(cat, self)
    }
}

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
    // The negated range also rejects NaN.
    if !(cfg.order_shaping_gamma > 0.0 && cfg.order_shaping_gamma <= 1.0) {
        return Err(SetupError::InvalidOrderShapingGamma {
            gamma: cfg.order_shaping_gamma,
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
    mission::validate(cat, cfg)
}

impl Match {
    /// Build a match: ships in slot order (team 0 then team 1), full health, initial
    /// power split, empty projectile pool, RNG seeded from `cfg.seed`. Each ship's
    /// reaction delay is its hull's `reaction_ticks` override, else the config's. The
    /// mission places the ships (SIM_SPEC §5.6, §5.10).
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
            collision_damage: [0.0; MAX_SHIPS],
            collision_shield_damage: [0.0; MAX_SHIPS],
            reserves: [Vec::new(), Vec::new()],
            mission: MissionState::default(),
            command: CommandState::default(),
            inbox: [Vec::new(), Vec::new()],
            command_results: [Vec::new(), Vec::new()],
            random_commander: RandomCommander::new(cfg.seed),
            order_tracks: [OrderTrack::default(); MAX_SHIPS],
            order_rewards: [0.0; MAX_SHIPS],
            hit_by: [[0; MAX_SHIPS]; MAX_SHIPS],
            ship_reach: [0.0; MAX_SHIPS],
            ship_class: [0; MAX_SHIPS],
            hp_mark: [0.0; MAX_SHIPS],
            alive_mark: [false; MAX_SHIPS],
            ward_threat: [0; MAX_SHIPS],
            hull_lost: [0.0; MAX_SHIPS],
        };
        for (s, ship) in m.ships.iter().enumerate() {
            let def = cat.hull(ship.hull);
            m.ship_reach[s] = order::hull_reach(cat, def);
            m.ship_class[s] = order::hull_class(def);
        }
        m.setup_mission(cat);
        m.init_order_tracks();
        Ok(m)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn arena_radius_rule_is_the_duel_arena_for_every_fleet_size() {
        for n in 0..=8 {
            assert_eq!(arena_radius_for(n), DEFAULT_ARENA_RADIUS);
        }
        assert_eq!(DEFAULT_ARENA_RADIUS, 450.0);
    }
}
