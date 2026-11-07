//! Browser bindings for the sim (SIM_SPEC §10.2): `WasmMatch` wraps one match.
//!
//! Bulk state is exposed as flat `f32` views into wasm memory: `*_ptr()` is a byte
//! offset into `wasm_memory().buffer` and `*_len()` a count of floats, so
//! `new Float32Array(wasm_memory().buffer, m.ships_ptr(), m.ships_len())` reads it with
//! no copy. Views are rebuilt by the constructor and every `step()`; re-create the
//! typed array after each step (the pointer may move, and memory growth detaches
//! old buffers). Record layouts are documented on the stride functions below.

pub mod bridge;

use wasm_bindgen::prelude::*;

use crate::bridge::MatchCore;

/// Lets the web client refuse a bundle built from a different sim version.
#[wasm_bindgen]
pub fn sim_version() -> u32 {
    sim::SIM_VERSION
}

/// v4: sim versions whose pilots fly in this build (`sim::PILOT_COMPAT_VERSIONS`);
/// a bundle's policy is accepted if its `sim_version` is in this list.
#[wasm_bindgen]
pub fn pilot_compat_versions() -> Vec<u32> {
    sim::PILOT_COMPAT_VERSIONS.to_vec()
}

/// v4: `pilot_compat_versions().includes(version)`.
#[wasm_bindgen]
pub fn pilot_compatible(version: u32) -> bool {
    sim::pilot_compatible(version)
}

/// v5: the obs width a pilot trained under sim `version` consumes (`obs[:width]`,
/// `sim::PILOT_OBS_DIMS`: 385 for v3 and v4 pilots, 403 for v5, 583 for v6); throws for
/// a version that does not fly in this build. The live page feeds a policy only that
/// prefix.
#[wasm_bindgen(js_name = pilotObsDim)]
pub fn pilot_obs_dim(version: u32) -> Result<usize, JsError> {
    sim::pilot_obs_dim(version).ok_or_else(|| {
        JsError::new(&format!(
            "a sim_version {version} pilot does not fly in this build (SIM_VERSION {})",
            sim::SIM_VERSION
        ))
    })
}

/// v5: `sim::PILOT_OBS_DIMS` as JSON, `{"3": 385, "4": 385, "5": 403, "6": 583}`.
#[wasm_bindgen(js_name = pilotObsDimsJson)]
pub fn pilot_obs_dims_json() -> String {
    let body: Vec<String> = sim::PILOT_OBS_DIMS
        .iter()
        .map(|(v, d)| format!("\"{v}\":{d}"))
        .collect();
    format!("{{{}}}", body.join(","))
}

/// v5: the obs layout as JSON, `{"blocks": [[name, offset, width], ...], "slots":
/// [[name, records], ...]}` (`sim::obs::OBS_LAYOUT` / `OBS_SLOTS`, in order).
#[wasm_bindgen(js_name = obsLayoutJson)]
pub fn obs_layout_json() -> String {
    let blocks: Vec<String> = sim::obs::OBS_LAYOUT
        .iter()
        .map(|(n, o, w)| format!("[\"{n}\",{o},{w}]"))
        .collect();
    let slots: Vec<String> = sim::obs::OBS_SLOTS
        .iter()
        .map(|(n, k)| format!("[\"{n}\",{k}]"))
        .collect();
    format!(
        "{{\"blocks\":[{}],\"slots\":[{}]}}",
        blocks.join(","),
        slots.join(",")
    )
}

/// v5: ship slots a training env pads its rosters to (`sim::setup::MAX_TRAIN_SHIPS`).
#[wasm_bindgen(js_name = MAX_TRAIN_SHIPS)]
pub fn max_train_ships() -> usize {
    sim::setup::MAX_TRAIN_SHIPS
}

fn mission_kind(name: &str) -> Result<sim::mission::MissionKind, JsError> {
    sim::mission::MissionKind::from_name(name)
        .ok_or_else(|| JsError::new(&format!("unknown mission {name:?}")))
}

/// v4: arena radius for mission `mission` (`"deathmatch"`, `"carrier_battle"`,
/// `"convoy_escort"`) with `n_ships` ships, the one per-mission rule.
#[wasm_bindgen(js_name = arenaRadiusForMission)]
pub fn arena_radius_for_mission(mission: &str, n_ships: u32) -> Result<f32, JsError> {
    Ok(sim::mission::arena_radius_for_mission(
        mission_kind(mission)?,
        n_ships as usize,
    ))
}

/// v4: default time limit of mission `mission`, ticks.
#[wasm_bindgen(js_name = missionTimeLimitTicks)]
pub fn mission_time_limit_ticks(mission: &str) -> Result<u32, JsError> {
    Ok(mission_kind(mission)?.default_time_limit_ticks())
}

/// WP-S2: the default rosters of mission `mission` as JSON, an array of
/// `{"name", "mission", "fleets": [[hull, ...], [hull, ...]]}` (slot order; empty for
/// deathmatch, whose rosters are budget drafts). The live page drafts among them.
#[wasm_bindgen(js_name = missionRostersJson)]
pub fn mission_rosters_json(mission: &str) -> Result<String, JsError> {
    Ok(sim::spec::to_json(&sim::spec::mission_rosters(
        mission_kind(mission)?,
    )))
}

/// v4: ships per match, docked reserves included.
#[wasm_bindgen(js_name = MAX_SHIPS)]
pub fn max_ships() -> usize {
    sim::state::MAX_SHIPS
}

/// v4: ticks between commander decisions.
#[wasm_bindgen(js_name = COMMAND_TICKS)]
pub fn command_ticks() -> u32 {
    sim::command::COMMAND_TICKS
}

/// Ticks between a learned commander's decisions (`docs/COMMANDER.md`).
#[wasm_bindgen(js_name = LEARNED_COMMAND_TICKS)]
pub fn learned_command_ticks() -> u32 {
    sim::command::LEARNED_COMMAND_TICKS
}

/// The learned commander's interface version (`sim::commander_io`).
#[wasm_bindgen(js_name = COMMANDER_IO_VERSION)]
pub fn commander_io_version() -> u32 {
    sim::commander_io::COMMANDER_IO_VERSION
}

/// Floats of `WasmMatch.commander_features(team)`.
#[wasm_bindgen(js_name = COMMANDER_FEATURES_LEN)]
pub fn commander_features_len() -> usize {
    sim::commander_io::FLAT_DIM
}

/// Integers of one decision for `WasmMatch.submit_commander_action`.
#[wasm_bindgen(js_name = COMMANDER_ACTION_DIM)]
pub fn commander_action_dim() -> usize {
    sim::commander_io::ACTION_DIM
}

/// The learned commander's interface as JSON: `{"version", "entity_dim",
/// "global_dim", "action_dim", "n_entities", "n_points", "command_ticks", "flat_dim",
/// "flat_layout": [[name, offset, width], ...]}` (the layout of `commander_features`,
/// in order; masks 0/1).
#[wasm_bindgen(js_name = commanderIoJson)]
pub fn commander_io_json() -> String {
    use sim::commander_io as io;
    let layout: Vec<String> = io::FLAT_LAYOUT
        .iter()
        .map(|(n, o, w)| format!("[\"{n}\",{o},{w}]"))
        .collect();
    format!(
        "{{\"version\":{},\"entity_dim\":{},\"global_dim\":{},\"action_dim\":{},\
         \"n_entities\":{},\"n_points\":{},\"command_ticks\":{},\"flat_dim\":{},\
         \"flat_layout\":[{}]}}",
        io::COMMANDER_IO_VERSION,
        io::ENTITY_DIM,
        io::GLOBAL_DIM,
        io::ACTION_DIM,
        io::N_ENTITIES,
        io::N_POINTS,
        sim::command::LEARNED_COMMAND_TICKS,
        io::FLAT_DIM,
        layout.join(",")
    )
}

/// v4: squads per team.
#[wasm_bindgen(js_name = MAX_SQUADS)]
pub fn max_squads() -> usize {
    sim::command::MAX_SQUADS
}

/// v4: floats per ship in `ship_ext_*` (layout in `bridge::SHIP_EXT_STRIDE`).
#[wasm_bindgen(js_name = SHIP_EXT_STRIDE)]
pub fn ship_ext_stride() -> usize {
    bridge::SHIP_EXT_STRIDE
}

/// v4: floats per squad in `squads()`.
#[wasm_bindgen(js_name = SQUAD_STRIDE)]
pub fn squad_stride() -> usize {
    bridge::SQUAD_STRIDE
}

/// v4: floats in `team_state(team)`.
#[wasm_bindgen(js_name = TEAM_STRIDE)]
pub fn team_stride() -> usize {
    bridge::TEAM_STRIDE
}

/// v4: floats in `convoy()` (during a convoy escort).
#[wasm_bindgen(js_name = CONVOY_STRIDE)]
pub fn convoy_stride() -> usize {
    bridge::CONVOY_STRIDE
}

/// Arena radius (metres) for a match of `n_ships` ships in total, both teams: the
/// shared rule of `sim::setup::arena_radius_for` (450 m for every fleet size today),
/// so the live page's arenas match the ones the pilots trained in.
#[wasm_bindgen(js_name = arenaRadiusFor)]
pub fn arena_radius_for(n_ships: u32) -> f32 {
    sim::setup::arena_radius_for(n_ships as usize)
}

/// The module's linear memory, for building views from the `*_ptr()` offsets.
#[wasm_bindgen]
pub fn wasm_memory() -> JsValue {
    wasm_bindgen::memory()
}

/// Floats per ship in `ships_*`: `[pos.x, pos.y, vel.x, vel.y, heading, omega, hp,
/// shield, alive, present, team, hull, thrust_level[8], turret_angle[6], power[3]]`.
#[wasm_bindgen(js_name = SHIP_STRIDE)]
pub fn ship_stride() -> usize {
    bridge::SHIP_STRIDE
}

/// Offset of `thrust_level[8]` within a ship record (v2: levels in `[0, 1]`; the
/// export keeps its v1 name).
#[wasm_bindgen(js_name = SHIP_THROTTLE_OFFSET)]
pub fn ship_throttle_offset() -> usize {
    bridge::SHIP_THROTTLE_OFFSET
}

/// Offset of `turret_angle[6]` (body frame, radians) within a ship record.
#[wasm_bindgen(js_name = SHIP_TURRET_OFFSET)]
pub fn ship_turret_offset() -> usize {
    bridge::SHIP_TURRET_OFFSET
}

/// Offset of `power[3]` (shields, engines, weapons) within a ship record.
#[wasm_bindgen(js_name = SHIP_POWER_OFFSET)]
pub fn ship_power_offset() -> usize {
    bridge::SHIP_POWER_OFFSET
}

/// Floats per live projectile in `projectiles_*`:
/// `[pool_slot, kind, team, owner, pos.x, pos.y, vel.x, vel.y]`
/// (kind 0 bullet, 1 beam, 2 flak, 3 torpedo).
#[wasm_bindgen(js_name = PROJECTILE_STRIDE)]
pub fn projectile_stride() -> usize {
    bridge::PROJECTILE_STRIDE
}

/// Floats per event in `events_*`: `[kind, a, b, x, y, nx_or_x2, ny_or_y2, extra]`
/// (SIM_SPEC §9; kinds 0 fire, 1 beam, 2 hit, 3 shield hit, 4 burst, 5 death,
/// 6 arrival, 7 collision (v3), 8 launch, 9 order, 10 jump charge, 11 jump out,
/// 12 match end (v4)).
#[wasm_bindgen(js_name = EVENT_STRIDE)]
pub fn event_stride() -> usize {
    sim::events::EVENT_STRIDE
}

/// Length of an action row for `set_action` (SIM_SPEC §7.1).
#[wasm_bindgen(js_name = ACTION_WIDTH)]
pub fn action_width() -> usize {
    sim::actions::ACTION_WIDTH
}

/// Length of `obs(ship)` (SIM_SPEC §7.2).
#[wasm_bindgen(js_name = OBS_DIM)]
pub fn obs_dim() -> usize {
    sim::obs::OBS_DIM
}

/// One deterministic match, stepped from JS.
#[wasm_bindgen]
pub struct WasmMatch {
    core: MatchCore,
}

fn js_err(msg: String) -> JsError {
    JsError::new(&msg)
}

/// Read `[[name, yaml], ...]` into owned pairs.
fn hull_pairs(hull_yamls: &js_sys::Array) -> Result<Vec<(String, String)>, JsError> {
    hull_yamls
        .iter()
        .enumerate()
        .map(|(i, entry)| {
            let pair = entry
                .dyn_into::<js_sys::Array>()
                .map_err(|_| JsError::new(&format!("hull_yamls[{i}] is not an array")))?;
            let field = |k: u32| pair.get(k).as_string();
            match (pair.length(), field(0), field(1)) {
                (2, Some(name), Some(yaml)) => Ok((name, yaml)),
                _ => Err(JsError::new(&format!(
                    "hull_yamls[{i}] must be a [name, yaml] pair of strings"
                ))),
            }
        })
        .collect()
}

#[wasm_bindgen]
impl WasmMatch {
    /// `hull_yamls`: `[[dir_name, hull_yaml_text], ...]`; `weapons_yaml`: the text of
    /// `weapons.yaml`; `config_json`: `{"seed": 7, "arena_radius": 450,
    /// "time_limit_ticks": 2700, "reaction_ticks": 2, "fleets": [["fighter"], ["fighter"]],
    /// "mission": "carrier_battle", "commanders": ["scripted", "learned"]}`
    /// (all but seed and fleets optional; v4 `mission` is a kind name or a spec
    /// object, SIM_SPEC §10.3). Throws on bad YAML, JSON, hull names, fleets or
    /// fleets that do not fit the mission.
    #[wasm_bindgen(constructor)]
    pub fn new(
        #[wasm_bindgen(unchecked_param_type = "Array<[string, string]>")] hull_yamls: js_sys::Array,
        weapons_yaml: &str,
        config_json: &str,
    ) -> Result<WasmMatch, JsError> {
        let pairs = hull_pairs(&hull_yamls)?;
        let core = MatchCore::new(&pairs, weapons_yaml, config_json).map_err(js_err)?;
        Ok(WasmMatch { core })
    }

    /// Advance one tick and rebuild the ship, projectile and event views.
    pub fn step(&mut self) {
        self.core.step();
    }

    /// Action for `ship` on the next step: `ACTION_WIDTH` values.
    pub fn set_action(&mut self, ship: u32, row: &[i8]) -> Result<(), JsError> {
        self.core.set_action(ship, row).map_err(js_err)
    }

    /// The scripted controller's action row for `ship` now.
    pub fn scripted_action(&self, ship: u32) -> Result<Vec<i8>, JsError> {
        self.core.scripted_action(ship).map_err(js_err)
    }

    pub fn ships_ptr(&self) -> *const f32 {
        self.core.ships_view().as_ptr()
    }

    /// v4: the per-ship mission view (`SHIP_EXT_STRIDE` floats per ship, ship order).
    pub fn ship_ext_ptr(&self) -> *const f32 {
        self.core.ship_ext_view().as_ptr()
    }

    /// v4: floats in the mission view (`n_ships * SHIP_EXT_STRIDE`).
    pub fn ship_ext_len(&self) -> usize {
        self.core.ship_ext_view().len()
    }

    /// v4: 0 deathmatch, 1 carrier battle, 2 convoy escort.
    pub fn mission_kind(&self) -> u8 {
        self.core.mission_kind()
    }

    /// v4: why the match ended: 0 not over, 1 eliminated, 2 time limit, 3 carrier
    /// destroyed, 4 convoy through, 5 convoy destroyed.
    pub fn end_reason(&self) -> u8 {
        self.core.end_reason()
    }

    /// v4: whether the next `step()` is a commander (slow) tick.
    pub fn command_due(&self) -> bool {
        self.core.command_due()
    }

    /// v4: queue commands (JSON object or array, SIM_SPEC §10.3) for `team`'s next
    /// slow tick; used only when that team's commander is `"external"`.
    pub fn submit_commands(&mut self, team: u32, json: &str) -> Result<(), JsError> {
        self.core.submit_commands(team, json).map_err(js_err)
    }

    /// The learned commander: whether the next `step()` is `team`'s slow tick (a
    /// `"learned"` team every `LEARNED_COMMAND_TICKS`, others every `COMMAND_TICKS`).
    pub fn commander_due(&self, team: u32) -> Result<bool, JsError> {
        self.core.commander_due(team).map_err(js_err)
    }

    /// The learned commander: `team`'s inputs and masks, `COMMANDER_FEATURES_LEN`
    /// floats in the `commanderIoJson()` layout: globals (53), entities (20 x 40),
    /// valid (20), launch mask (3), waypoint mask (26), squad mask (20 x 6), order mask
    /// (4 x 5), target mask (20), ward mask (20); masks 0/1.
    pub fn commander_features(&self, team: u32) -> Result<Vec<f32>, JsError> {
        self.core.commander_features(team).map_err(js_err)
    }

    /// The learned commander: decode and queue `team`'s decision
    /// (`COMMANDER_ACTION_DIM` integers) for its coming slow tick; returns how many
    /// commands it made. Throws unless the team is `"learned"` (or `"external"`) and
    /// due, or for a value outside its head's choices.
    pub fn submit_commander_action(&mut self, team: u32, action: &[i32]) -> Result<u32, JsError> {
        self.core
            .submit_commander_action(team, action)
            .map_err(js_err)
    }

    /// `[team 0, team 1]` values now: hull + half shield of every ship still in the
    /// match.
    pub fn team_values(&self) -> Vec<f32> {
        self.core.team_values()
    }

    /// v4: JSON array of `team`'s command outcomes on the last slow tick.
    pub fn command_results_json(&self, team: u32) -> Result<String, JsError> {
        self.core.command_results_json(team).map_err(js_err)
    }

    /// v4: JSON of `team`'s commander observation.
    pub fn commander_obs_json(&self, team: u32) -> Result<String, JsError> {
        self.core.commander_obs_json(team).map_err(js_err)
    }

    /// v4: JSON of the mission and command state (squads, hangars, convoy, ships).
    pub fn mission_state_json(&self) -> String {
        self.core.mission_state_json()
    }

    /// v4: every squad and its order (`SQUAD_STRIDE` floats each; team 0 first).
    pub fn squads(&self) -> Vec<f32> {
        self.core.squads()
    }

    /// v4: `team`'s carrier HP/shield and hangar (`TEAM_STRIDE` floats).
    pub fn team_state(&self, team: u32) -> Result<Vec<f32>, JsError> {
        self.core.team_state(team).map_err(js_err)
    }

    /// v4: hull ids of `team`'s docked reserves in launch order.
    pub fn hangar_hulls(&self, team: u32) -> Result<Vec<u16>, JsError> {
        self.core.hangar_hulls(team).map_err(js_err)
    }

    /// v4: convoy progress (`CONVOY_STRIDE` floats; empty outside a convoy escort).
    pub fn convoy(&self) -> Vec<f32> {
        self.core.convoy()
    }

    /// Floats in the ships view (`n_ships * SHIP_STRIDE`).
    pub fn ships_len(&self) -> usize {
        self.core.ships_view().len()
    }

    pub fn projectiles_ptr(&self) -> *const f32 {
        self.core.projectiles_view().as_ptr()
    }

    /// Floats in the projectiles view (`n_live * PROJECTILE_STRIDE`).
    pub fn projectiles_len(&self) -> usize {
        self.core.projectiles_view().len()
    }

    /// Events of the last step, flat (SIM_SPEC §9).
    pub fn events_ptr(&self) -> *const f32 {
        self.core.events_view().as_ptr()
    }

    /// Floats in the events view (`n_events * EVENT_STRIDE`).
    pub fn events_len(&self) -> usize {
        self.core.events_view().len()
    }

    /// Ship `ship`'s `ACTION_WIDTH` head-validity flags (1 meaningful, 0 masked: the
    /// policy writes HOLD / no-fire there), derived from its hull.
    pub fn head_valid(&self, ship: u32) -> Result<Vec<u8>, JsError> {
        self.core.head_valid(ship).map_err(js_err)
    }

    /// Ship `ship`'s observation (`OBS_DIM` floats, a copy; a v3/v4/v5 pilot reads
    /// the first `pilotObsDim(version)`).
    pub fn obs(&self, ship: u32) -> Result<Vec<f32>, JsError> {
        self.core.obs(ship).map_err(js_err)
    }

    /// v5: the last step's order reward per ship (SIM_SPEC §8), ship order.
    pub fn order_rewards(&self) -> Vec<f32> {
        self.core.order_rewards()
    }

    pub fn tick(&self) -> u32 {
        self.core.tick()
    }

    /// 0 running, 1 over.
    pub fn phase(&self) -> u8 {
        self.core.phase()
    }

    /// -2 not over, -1 draw, 0 or 1 the winning team.
    pub fn winner(&self) -> i8 {
        self.core.winner()
    }

    /// `state_hash()` as 16 lowercase hex digits (u64 does not fit a JS number).
    pub fn state_hash_hex(&self) -> String {
        format!("{:016x}", self.core.state_hash())
    }
}
