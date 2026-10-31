//! Target-independent core of `WasmMatch`: catalogue and config parsing, the match,
//! and the flat f32 views the browser reads. Errors are plain strings here so this
//! module builds and tests natively; `lib.rs` turns them into `JsError`.

use serde::Deserialize;
use sim::actions::{self, ACTION_WIDTH, ShipAction};
use sim::command::{CommanderMode, MAX_SQUADS, Order, Waypoint};
use sim::data::{Catalogue, HullId};
use sim::mission::{JumpState, Mission, is_carrier, is_transport};
use sim::obs::OBS_DIM;
use sim::scripted;
use sim::setup::{
    DEFAULT_ARENA_RADIUS, DEFAULT_REACTION_TICKS, DEFAULT_TIME_LIMIT_TICKS, MatchConfig,
};
use sim::spec::{
    CommandSpec, CommanderObsView, MissionSpec, MissionStateView, OutcomeView, parse_commanders,
    to_json,
};
use sim::state::{Attach, MAX_THRUSTERS, MAX_TURRETS, Match, NONE, ShipIdx};

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

/// v4: floats per ship in the mission view (`ship_ext_*`), same ship order as the
/// ships view: `[role, docked, parent, jump, charge_until, has_waypoint, waypoint.x,
/// waypoint.y, squad, order_kind]`. `role` 0 strike craft (or any other role), 1
/// carrier, 2 transport; `parent` the carrier a docked ship waits in, else -1; `jump`
/// 0 idle, 1 charging (until tick `charge_until`), 2 jumped out (escaped); `squad`
/// its squad index in its team or -1, `order_kind` that squad's order (0 none, 1
/// attack, 2 defend, 3 go-to; v5: guard, hold).
pub const SHIP_EXT_STRIDE: usize = 10;
/// v4: floats per squad in `squads()`, team 0's `MAX_SQUADS` then team 1's:
/// `[team, index, n_members, members_mask, order_kind, target, point.x, point.y,
/// radius]`; `target` the attacked or defended slot or -1; `point` the go-to point or
/// the target's position now; `members_mask` bit `s` = slot `s` (exact in f32).
pub const SQUAD_STRIDE: usize = 9;
/// v4: floats in `team_state(team)`: `[carrier_slot, carrier_hp, carrier_max_hp,
/// carrier_shield, carrier_max_shield, hangar_count, bays, bays_ready]` (carrier
/// fields -1/0 without a carrier).
pub const TEAM_STRIDE: usize = 8;
/// v4: floats in `convoy()` during a convoy escort (empty otherwise): `[total,
/// en_route, charging, escaped, destroyed, to_destroy, to_escape, progress, start.x,
/// start.y, jump_point.x, jump_point.y, jump_radius, charge_ticks]`.
pub const CONVOY_STRIDE: usize = 14;

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
    /// v4: a kind name (`"carrier_battle"`) or a mission spec object (SIM_SPEC
    /// §10.3); absent is deathmatch.
    #[serde(default)]
    mission: Option<serde_json::Value>,
    /// v4: `["scripted", "external"]`; absent is both scripted.
    #[serde(default)]
    commanders: Option<Vec<String>>,
    /// v6: `[team 0, team 1]` hidden-order mode; absent is both false.
    #[serde(default)]
    hide_orders: [bool; 2],
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
    let mission = match &raw.mission {
        None => Mission::Deathmatch,
        Some(serde_json::Value::String(name)) => MissionSpec::parse(name)?.build(raw.arena_radius),
        Some(spec) => serde_json::from_value::<MissionSpec>(spec.clone())
            .map_err(|e| format!("config_json: mission: {e}"))?
            .build(raw.arena_radius),
    };
    let commanders = match &raw.commanders {
        None => [CommanderMode::Scripted; 2],
        Some(names) => parse_commanders(names).map_err(|e| format!("config_json: {e}"))?,
    };
    Ok(MatchConfig {
        seed: raw.seed,
        arena_radius: raw.arena_radius,
        time_limit_ticks: raw.time_limit_ticks,
        reaction_ticks: raw.reaction_ticks,
        fleets: [resolve(0)?, resolve(1)?],
        mission,
        commanders,
        hide_orders: raw.hide_orders,
    })
}

/// One match plus the flat views, refreshed after construction and every step.
pub struct MatchCore {
    cat: Catalogue,
    m: Match,
    ships: Vec<f32>,
    ship_ext: Vec<f32>,
    projectiles: Vec<f32>,
    events: Vec<f32>,
}

fn slot_f(s: ShipIdx) -> f32 {
    if s == NONE { -1.0 } else { f32::from(s) }
}

fn check_team(team: u32) -> Result<u8, String> {
    match team {
        0 | 1 => Ok(team as u8),
        t => Err(format!("team must be 0 or 1, got {t}")),
    }
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
            ship_ext: Vec::new(),
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
    /// v5: the last step's order reward per ship.
    pub fn order_rewards(&self) -> Vec<f32> {
        self.m.order_rewards().to_vec()
    }

    pub fn obs(&self, ship: u32) -> Result<Vec<f32>, String> {
        let slot = self.check_ship(ship)?;
        let mut out = vec![0.0; OBS_DIM];
        self.m.write_obs(&self.cat, slot, &mut out);
        Ok(out)
    }

    pub fn ships_view(&self) -> &[f32] {
        &self.ships
    }

    /// v4: the per-ship mission view (`SHIP_EXT_STRIDE` floats per ship).
    pub fn ship_ext_view(&self) -> &[f32] {
        &self.ship_ext
    }

    /// v4: `MissionKind` code (0 deathmatch, 1 carrier battle, 2 convoy escort).
    pub fn mission_kind(&self) -> u8 {
        self.m.cfg.mission.kind().index()
    }

    /// v4: `EndReason` code (0 not over, 1 eliminated, 2 time limit, 3 carrier
    /// destroyed, 4 convoy through, 5 convoy destroyed).
    pub fn end_reason(&self) -> u8 {
        self.m.mission.end_reason.index()
    }

    /// v4: whether the next `step` is a slow (command) tick.
    pub fn command_due(&self) -> bool {
        self.m.command_due()
    }

    /// v4: queue commands (a JSON command object or array, SIM_SPEC §10.3) for
    /// `team`'s next slow tick; only used if that team's commander is external.
    pub fn submit_commands(&mut self, team: u32, json: &str) -> Result<(), String> {
        let team = check_team(team)?;
        let cmds = CommandSpec::parse_list(json)?
            .iter()
            .map(|c| c.to_command(&self.cat))
            .collect::<Result<Vec<_>, _>>()?;
        for c in cmds {
            self.m.submit_command(team, c);
        }
        Ok(())
    }

    /// v4: JSON array of `team`'s command outcomes on the last slow tick.
    pub fn command_results_json(&self, team: u32) -> Result<String, String> {
        let views: Vec<OutcomeView> = self
            .m
            .command_results(check_team(team)?)
            .iter()
            .map(OutcomeView::of)
            .collect();
        Ok(to_json(&views))
    }

    /// v4: JSON of `team`'s commander observation.
    pub fn commander_obs_json(&self, team: u32) -> Result<String, String> {
        let obs = self.m.commander_obs(&self.cat, check_team(team)?);
        Ok(to_json(&CommanderObsView::of(&self.m, &self.cat, &obs)))
    }

    /// v4: JSON of the whole mission and command state (debugging, the log).
    pub fn mission_state_json(&self) -> String {
        to_json(&MissionStateView::of(&self.m, &self.cat))
    }

    /// v4: every squad, `SQUAD_STRIDE` floats each (team 0's then team 1's).
    pub fn squads(&self) -> Vec<f32> {
        let mut out = Vec::with_capacity(2 * MAX_SQUADS * SQUAD_STRIDE);
        for team in 0..2u8 {
            for (k, sq) in self.m.command.squads[usize::from(team)].iter().enumerate() {
                let (target, point, radius) = match sq.order {
                    Order::None => (NONE, [0.0, 0.0], 0.0),
                    Order::Attack { target } | Order::Defend { ward: target } => {
                        let p = self.m.ships()[usize::from(target)].pos;
                        (target, [p.x, p.y], 0.0)
                    }
                    Order::GoTo { point, radius } => (NONE, [point.x, point.y], radius),
                };
                out.extend_from_slice(&[
                    f32::from(team),
                    k as f32,
                    sq.len() as f32,
                    sq.members as f32,
                    f32::from(sq.order.kind()),
                    slot_f(target),
                    point[0],
                    point[1],
                    radius,
                ]);
            }
        }
        out
    }

    /// v4: `team`'s carrier and hangar, `TEAM_STRIDE` floats.
    pub fn team_state(&self, team: u32) -> Result<Vec<f32>, String> {
        let t = check_team(team)?;
        let c = self.m.carrier_of(t);
        let hangar = self.m.hangar(t).len() as f32;
        if c == NONE {
            return Ok(vec![-1.0, 0.0, 0.0, 0.0, 0.0, hangar, 0.0, 0.0]);
        }
        let ship = &self.m.ships()[usize::from(c)];
        let hull = self.cat.hull(ship.hull);
        let ready = (0..hull.bays.len())
            .filter(|&b| {
                ship.active() && self.m.tick() >= self.m.mission.bay_ready[usize::from(t)][b]
            })
            .count();
        Ok(vec![
            f32::from(c),
            ship.hp,
            hull.hp,
            ship.shield,
            hull.shield.map_or(0.0, |s| s.hp),
            hangar,
            hull.bays.len() as f32,
            ready as f32,
        ])
    }

    /// v4: hull ids of `team`'s docked reserves, in launch order.
    pub fn hangar_hulls(&self, team: u32) -> Result<Vec<u16>, String> {
        let t = check_team(team)?;
        Ok(self
            .m
            .hangar(t)
            .iter()
            .map(|&s| self.m.ships()[usize::from(s)].hull)
            .collect())
    }

    /// v4: the convoy, `CONVOY_STRIDE` floats (empty outside a convoy escort).
    pub fn convoy(&self) -> Vec<f32> {
        let Mission::ConvoyEscort(ce) = &self.m.cfg.mission else {
            return Vec::new();
        };
        let st = self.m.convoy_status();
        vec![
            f32::from(st.total),
            f32::from(st.en_route),
            f32::from(st.charging),
            f32::from(st.escaped),
            f32::from(st.destroyed),
            f32::from(st.to_destroy),
            f32::from(st.to_escape),
            st.progress,
            ce.start.x,
            ce.start.y,
            ce.jump_point.x,
            ce.jump_point.y,
            ce.jump_radius,
            ce.charge_ticks as f32,
        ]
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
        self.ship_ext.clear();
        for s in self.m.ships() {
            let hull = self.cat.hull(s.hull);
            let role = if is_carrier(hull) {
                1.0
            } else if is_transport(hull) {
                2.0
            } else {
                0.0
            };
            let (jump, until) = match self.m.jump_state(s.slot) {
                JumpState::Idle => (0.0, 0.0),
                JumpState::Charging { until } => (1.0, until as f32),
                JumpState::Departed => (2.0, 0.0),
            };
            let (has_wp, wp) = match self.m.command.waypoints[usize::from(s.slot)] {
                Waypoint::Unset => (0.0, [0.0, 0.0]),
                Waypoint::At(p) => (1.0, [p.x, p.y]),
            };
            let (squad, order) = match self.m.squad_of(s.slot) {
                Some(k) => {
                    let sq = &self.m.command.squads[usize::from(s.team)][usize::from(k)];
                    (f32::from(k), f32::from(sq.order.kind()))
                }
                None => (-1.0, 0.0),
            };
            self.ship_ext.extend_from_slice(&[
                role,
                b(s.attach == Attach::Docked),
                slot_f(s.parent),
                jump,
                until,
                has_wp,
                wp[0],
                wp[1],
                squad,
                order,
            ]);
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
