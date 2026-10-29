//! Target-independent core of `WasmMatch`: catalogue and config parsing, the match,
//! and the flat f32 views the browser reads. Errors are plain strings here so this
//! module builds and tests natively; `lib.rs` turns them into `JsError`.

use serde::Deserialize;
use sim::actions::{self, ACTION_WIDTH, ShipAction};
use sim::data::{Catalogue, HullId};
use sim::obs::OBS_DIM;
use sim::scripted;
use sim::setup::{
    DEFAULT_ARENA_RADIUS, DEFAULT_REACTION_TICKS, DEFAULT_TIME_LIMIT_TICKS, MatchConfig,
};
use sim::state::{MAX_THRUSTERS, MAX_TURRETS, Match, ShipIdx};

/// Floats per ship in the ships view:
/// `[pos.x, pos.y, vel.x, vel.y, heading, omega, hp, shield, alive, present, team,
/// hull, thrust_level[8], turret_angle[6], power[3]]` (bools as 0/1, thrust levels
/// in `[0, 1]` (v2; v1 wrote throttles 0/1/2), power shares shields, engines, weapons).
pub const SHIP_STRIDE: usize = 12 + MAX_THRUSTERS + MAX_TURRETS + 3;
/// Floats per live projectile in the projectiles view:
/// `[pool_slot, kind, team, owner, pos.x, pos.y, vel.x, vel.y]`. Only live pool
/// slots are listed, in pool order; `pool_slot` identifies a projectile across
/// ticks (a slot is reused only after its projectile dies or is overwritten).
pub const PROJECTILE_STRIDE: usize = 8;
/// Offset of the thrust-level block within a ship record.
pub const SHIP_THROTTLE_OFFSET: usize = 12;
/// Offset of the turret-angle block within a ship record.
pub const SHIP_TURRET_OFFSET: usize = SHIP_THROTTLE_OFFSET + MAX_THRUSTERS;
/// Offset of the power split within a ship record.
pub const SHIP_POWER_OFFSET: usize = SHIP_TURRET_OFFSET + MAX_TURRETS;

const _: () = assert!(SHIP_POWER_OFFSET + 3 == SHIP_STRIDE);
const _: () = assert!(SHIP_STRIDE == 29);

/// `config_json` schema (SIM_SPEC §10.2): `MatchConfig` with hull names.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ConfigJson {
    seed: u64,
    #[serde(default = "default_arena_radius")]
    arena_radius: f32,
    #[serde(default = "default_time_limit")]
    time_limit_ticks: u32,
    /// v2; range-checked by `Match::new` (`SetupError::ReactionTooLong`).
    #[serde(default = "default_reaction_ticks")]
    reaction_ticks: u8,
    fleets: [Vec<String>; 2],
}

fn default_arena_radius() -> f32 {
    DEFAULT_ARENA_RADIUS
}

fn default_time_limit() -> u32 {
    DEFAULT_TIME_LIMIT_TICKS
}

fn default_reaction_ticks() -> u8 {
    DEFAULT_REACTION_TICKS
}

/// Parse `config_json` and resolve hull names against `cat`.
pub fn parse_config(cat: &Catalogue, config_json: &str) -> Result<MatchConfig, String> {
    let raw: ConfigJson =
        serde_json::from_str(config_json).map_err(|e| format!("config_json: {e}"))?;
    let resolve = |team: usize| -> Result<Vec<HullId>, String> {
        raw.fleets[team]
            .iter()
            .map(|name| {
                cat.hull_id(name)
                    .ok_or_else(|| format!("config_json: team {team} names unknown hull {name:?}"))
            })
            .collect()
    };
    Ok(MatchConfig {
        seed: raw.seed,
        arena_radius: raw.arena_radius,
        time_limit_ticks: raw.time_limit_ticks,
        reaction_ticks: raw.reaction_ticks,
        fleets: [resolve(0)?, resolve(1)?],
    })
}

/// One match plus the flat views, refreshed after construction and every step.
pub struct MatchCore {
    cat: Catalogue,
    m: Match,
    ships: Vec<f32>,
    projectiles: Vec<f32>,
    events: Vec<f32>,
}

impl MatchCore {
    /// `hulls` are `(directory name, hull.yaml text)` pairs; see `Catalogue::from_yaml`.
    pub fn new(
        hulls: &[(String, String)],
        weapons_yaml: &str,
        config_json: &str,
    ) -> Result<MatchCore, String> {
        let pairs: Vec<(&str, &str)> = hulls
            .iter()
            .map(|(n, y)| (n.as_str(), y.as_str()))
            .collect();
        let cat = Catalogue::from_yaml(&pairs, weapons_yaml).map_err(|e| e.to_string())?;
        let cfg = parse_config(&cat, config_json)?;
        let m = Match::new(&cat, &cfg).map_err(|e| format!("config_json: {e}"))?;
        let mut core = MatchCore {
            cat,
            m,
            ships: Vec::new(),
            projectiles: Vec::new(),
            events: Vec::new(),
        };
        core.refresh_views();
        Ok(core)
    }

    pub fn step(&mut self) {
        self.m.step(&self.cat);
        self.refresh_views();
    }

    fn check_ship(&self, ship: u32) -> Result<ShipIdx, String> {
        let n = self.m.ships().len();
        if (ship as usize) < n {
            Ok(ship as ShipIdx)
        } else {
            Err(format!("ship {ship} out of range (match has {n} ships)"))
        }
    }

    /// Set ship `ship`'s action for the next step from a row of `ACTION_WIDTH` i8
    /// (SIM_SPEC §7.1); out-of-range head values clamp.
    pub fn set_action(&mut self, ship: u32, row: &[i8]) -> Result<(), String> {
        let slot = self.check_ship(ship)?;
        if row.len() != ACTION_WIDTH {
            return Err(format!(
                "action row has {} values, expected {ACTION_WIDTH}",
                row.len()
            ));
        }
        self.m.set_action(slot, ShipAction::from_row(row));
        Ok(())
    }

    /// The scripted controller's action row for `ship` in the current state.
    pub fn scripted_action(&self, ship: u32) -> Result<Vec<i8>, String> {
        let slot = self.check_ship(ship)?;
        let mut row = vec![0i8; ACTION_WIDTH];
        scripted::act(&self.m, &self.cat, slot).to_row(&mut row);
        Ok(row)
    }

    /// Which of ship `ship`'s `ACTION_WIDTH` action heads are meaningful (1) or masked
    /// (0), from its hull: throttle heads of present thrusters, slew heads of present
    /// non-fixed turrets, fire heads of present turrets, and the power head (always 1).
    /// Same rule as the trained policy's `HeadMasks.head_valid()`.
    pub fn head_valid(&self, ship: u32) -> Result<Vec<u8>, String> {
        let slot = self.check_ship(ship)?;
        let hull = self.cat.hull(self.m.ships()[slot as usize].hull);
        let thruster = actions::thruster_mask(hull);
        let turret = actions::turret_mask(hull);
        let fixed = actions::fixed_turret(hull);
        let mut out = Vec::with_capacity(ACTION_WIDTH);
        out.extend(thruster.iter().map(|&t| u8::from(t)));
        out.extend((0..MAX_TURRETS).map(|j| u8::from(turret[j] && !fixed[j])));
        out.extend(turret.iter().map(|&t| u8::from(t)));
        out.push(1);
        debug_assert_eq!(out.len(), ACTION_WIDTH);
        Ok(out)
    }

    /// Ship `ship`'s observation, `OBS_DIM` floats (SIM_SPEC §7.2).
    pub fn obs(&self, ship: u32) -> Result<Vec<f32>, String> {
        let slot = self.check_ship(ship)?;
        let mut out = vec![0.0; OBS_DIM];
        self.m.write_obs(&self.cat, slot, &mut out);
        Ok(out)
    }

    pub fn ships_view(&self) -> &[f32] {
        &self.ships
    }

    pub fn projectiles_view(&self) -> &[f32] {
        &self.projectiles
    }

    pub fn events_view(&self) -> &[f32] {
        &self.events
    }

    pub fn tick(&self) -> u32 {
        self.m.tick()
    }

    pub fn phase(&self) -> u8 {
        self.m.phase().index()
    }

    pub fn winner(&self) -> i8 {
        self.m.winner()
    }

    pub fn state_hash(&self) -> u64 {
        self.m.state_hash()
    }

    fn refresh_views(&mut self) {
        let b = |v: bool| if v { 1.0 } else { 0.0 };
        self.ships.clear();
        for s in self.m.ships() {
            self.ships.extend_from_slice(&[
                s.pos.x,
                s.pos.y,
                s.vel.x,
                s.vel.y,
                s.heading,
                s.omega,
                s.hp,
                s.shield,
                b(s.alive),
                b(s.present),
                f32::from(s.team),
                f32::from(s.hull),
            ]);
            self.ships.extend_from_slice(&s.thrust_level);
            self.ships.extend_from_slice(&s.turret_angle);
            self.ships.extend_from_slice(&s.power);
        }
        self.projectiles.clear();
        for (slot, p) in self.m.projectiles().iter().enumerate() {
            if !p.alive {
                continue;
            }
            self.projectiles.extend_from_slice(&[
                slot as f32,
                p.kind.index() as f32,
                f32::from(p.team),
                f32::from(p.owner),
                p.pos.x,
                p.pos.y,
                p.vel.x,
                p.vel.y,
            ]);
        }
        self.m.events.encode_into(&mut self.events);
    }
}
