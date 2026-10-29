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

/// Arena radius (metres) for a match of `n_ships` ships in total, both teams: the
/// shared rule of `sim::setup::arena_radius_for` (450 m duel, +25 m per extra ship),
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
/// 6 arrival, 7 collision (v3)).
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
    /// "time_limit_ticks": 2700, "reaction_ticks": 2, "fleets": [["fighter"], ["fighter"]]}`
    /// (radius, time limit and reaction ticks optional). Throws on bad YAML, JSON, hull names or fleets.
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

    /// Ship `ship`'s observation (`OBS_DIM` floats, a copy).
    pub fn obs(&self, ship: u32) -> Result<Vec<f32>, JsError> {
        self.core.obs(ship).map_err(js_err)
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
