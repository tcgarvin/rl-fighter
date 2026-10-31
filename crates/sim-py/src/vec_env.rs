//! `rlf_sim.VecEnv`: numpy buffers owned by the env, borrowed as slices for each
//! call, with the GIL released around the parallel work (SIM_SPEC §10.1).

use std::path::Path;

use numpy::ndarray::{Array2, Dim};
use numpy::{
    Element, IntoPyArray, PyArray, PyArray1, PyArray2, PyArray3, PyArrayMethods, PyReadwriteArray,
    PyUntypedArrayMethods,
};
use pyo3::exceptions::{PyIndexError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAnyMethods, PyDict, PyList, PyString};
use sim::actions::ACTION_WIDTH;
use sim::actions::act_mask;
use sim::command::CommanderMode;
use sim::data::{Catalogue, HullId};
use sim::events::EVENT_STRIDE;
use sim::mission::Mission;
use sim::obs::OBS_DIM;
use sim::spec::{
    CommandSpec, CommanderObsView, MissionSpec, MissionStateView, OutcomeView, parse_commanders,
    to_json,
};
use sim::state::{MAX_HITS, MAX_REACTION_TICKS, MAX_SHIPS, MAX_THRUSTERS, MAX_TURRETS, MatchPhase};
use sim::{DT, TICK_HZ};

use crate::batch::{Batch, BatchConfig, HIT_FIELDS, Roster, StepBuffers};

/// JSON text of a Python object (`json.dumps`), for the shared serde specs.
fn json_dumps(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<String> {
    py.import("json")?
        .call_method1("dumps", (obj,))?
        .extract::<String>()
}

/// Python object from JSON text (`json.loads`).
fn json_loads<'py>(py: Python<'py>, text: &str) -> PyResult<Bound<'py, PyAny>> {
    py.import("json")?.call_method1("loads", (text,))
}

/// A mission from `None` (deathmatch), a kind name (`"carrier_battle"`) or a dict
/// spec (SIM_SPEC §10.3), defaults filled for `arena_radius`.
fn mission_from_py(
    py: Python<'_>,
    obj: Option<&Bound<'_, PyAny>>,
    arena_radius: f32,
) -> PyResult<Mission> {
    let Some(obj) = obj else {
        return Ok(Mission::Deathmatch);
    };
    let text = if obj.is_instance_of::<PyString>() {
        obj.extract::<String>()?
    } else {
        json_dumps(py, obj)?
    };
    MissionSpec::parse(&text)
        .map(|spec| spec.build(arena_radius))
        .map_err(PyValueError::new_err)
}

/// Ticks of a time limit in seconds; ValueError unless positive and finite.
fn time_limit_ticks(time_limit_s: f32) -> PyResult<u32> {
    if !(time_limit_s.is_finite() && time_limit_s > 0.0) {
        return Err(PyValueError::new_err(format!(
            "time_limit_s must be positive and finite, got {time_limit_s}"
        )));
    }
    Ok((time_limit_s * TICK_HZ).round().max(1.0) as u32)
}

/// Commander modes from `None` (`default`) or two names (`"scripted"`, `"random"`,
/// `"external"`).
fn commanders_from_py(
    names: Option<Vec<String>>,
    default: [CommanderMode; 2],
) -> PyResult<[CommanderMode; 2]> {
    match names {
        None => Ok(default),
        Some(names) => parse_commanders(&names).map_err(PyValueError::new_err),
    }
}

/// v6: hidden-order flags from `None` (`default`) or two bools.
fn hide_orders_from_py(flags: Option<Vec<bool>>, default: [bool; 2]) -> PyResult<[bool; 2]> {
    match flags.as_deref() {
        None => Ok(default),
        Some(&[a, b]) => Ok([a, b]),
        Some(other) => Err(PyValueError::new_err(format!(
            "hide_orders must be [team 0, team 1] bools, got {} values",
            other.len()
        ))),
    }
}

/// Borrow `arr` mutably as a flat slice, or explain why not (another Rust borrow is
/// live, or the user made the array read-only).
fn borrow_mut<'py, T: Element, D: numpy::ndarray::Dimension>(
    arr: &Bound<'py, PyArray<T, D>>,
    name: &str,
) -> PyResult<PyReadwriteArray<'py, T, D>> {
    arr.try_readwrite()
        .map_err(|e| PyValueError::new_err(format!("env.{name} cannot be written: {e}")))
}

fn as_slice<'a, T: Element, D: numpy::ndarray::Dimension>(
    rw: &'a mut PyReadwriteArray<'_, T, D>,
    name: &str,
) -> PyResult<&'a mut [T]> {
    rw.as_slice_mut()
        .map_err(|e| PyValueError::new_err(format!("env.{name} is not contiguous: {e}")))
}

fn resolve_fleets(cat: &Catalogue, fleets: &[Vec<String>]) -> PyResult<[Vec<HullId>; 2]> {
    if fleets.len() != 2 {
        return Err(PyValueError::new_err(format!(
            "fleets must be [[team 0 hulls], [team 1 hulls]], got {} teams",
            fleets.len()
        )));
    }
    let known: Vec<&str> = cat.hulls.iter().map(|h| h.name.as_str()).collect();
    let mut out: [Vec<HullId>; 2] = [Vec::new(), Vec::new()];
    for (team, names) in fleets.iter().enumerate() {
        if names.is_empty() {
            return Err(PyValueError::new_err(format!("team {team} fleet is empty")));
        }
        for name in names {
            let id = cat.hull_id(name).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "unknown hull {name:?} in team {team} fleet; known hulls: {known:?}"
                ))
            })?;
            out[team].push(id);
        }
    }
    let total = out[0].len() + out[1].len();
    if total > MAX_SHIPS {
        return Err(PyValueError::new_err(format!(
            "fleets have {total} ships in total; at most {MAX_SHIPS} allowed"
        )));
    }
    Ok(out)
}

/// Batched env over `n_envs` matches. Every env starts with `fleets`; any env can
/// switch to another roster at its next rebuild (`set_next_roster`).
///
/// All buffer properties return the same numpy arrays on every call; `step()` and
/// `reset()` overwrite them in place. Write actions into `env.actions` (or pass an
/// array to `step`) before stepping. Every match has `n_ships` slots; a match with
/// fewer ships pads the rest (team and hull id -1, zero obs, masks and `alive` false).
/// `team`, `hull_id`, the three slot masks and `arena_radius` describe the current
/// match and change only when a match is rebuilt.
#[pyclass(module = "rlf_sim")]
pub struct VecEnv {
    batch: Batch,
    obs: Py<PyArray3<f32>>,
    actions: Py<PyArray3<i8>>,
    rewards: Py<PyArray2<f32>>,
    order_rewards: Py<PyArray2<f32>>,
    order_transit: Py<PyArray2<bool>>,
    ward_threat: Py<PyArray3<bool>>,
    ward_hull_lost: Py<PyArray2<f32>>,
    dones: Py<PyArray1<bool>>,
    winner: Py<PyArray1<i8>>,
    end_reason: Py<PyArray1<i8>>,
    act_mask: Py<PyArray2<bool>>,
    thruster_mask: Py<PyArray3<bool>>,
    turret_mask: Py<PyArray3<bool>>,
    fixed_turret: Py<PyArray3<bool>>,
    team: Py<PyArray2<i8>>,
    hull_id: Py<PyArray2<i16>>,
    alive: Py<PyArray2<bool>>,
    tick: Py<PyArray1<u32>>,
    episode_count: Py<PyArray1<u32>>,
    hits: Py<PyArray3<i32>>,
    hit_count: Py<PyArray1<i32>>,
    collision_damage: Py<PyArray2<f32>>,
    arena_radius: Py<PyArray1<f32>>,
    /// v5: what `set_next_roster` falls back to: the constructor's commanders and
    /// time limit.
    default_commanders: [CommanderMode; 2],
    default_time_limit_ticks: u32,
    /// v6: what `set_next_roster` falls back to for `hide_orders`.
    default_hide_orders: [bool; 2],
}

/// Borrow every per-step buffer and call `f` with the slices.
macro_rules! with_step_buffers {
    ($self:ident, $py:ident, |$bufs:ident| $body:expr) => {{
        let obs = $self.obs.bind($py);
        let actions = $self.actions.bind($py);
        let rewards = $self.rewards.bind($py);
        let order_rewards = $self.order_rewards.bind($py);
        let order_transit = $self.order_transit.bind($py);
        let ward_threat = $self.ward_threat.bind($py);
        let ward_hull_lost = $self.ward_hull_lost.bind($py);
        let dones = $self.dones.bind($py);
        let winner = $self.winner.bind($py);
        let end_reason = $self.end_reason.bind($py);
        let act_mask = $self.act_mask.bind($py);
        let alive = $self.alive.bind($py);
        let tick = $self.tick.bind($py);
        let episode_count = $self.episode_count.bind($py);
        let hits = $self.hits.bind($py);
        let hit_count = $self.hit_count.bind($py);
        let collision_damage = $self.collision_damage.bind($py);
        let thruster_mask = $self.thruster_mask.bind($py);
        let turret_mask = $self.turret_mask.bind($py);
        let fixed_turret = $self.fixed_turret.bind($py);
        let team = $self.team.bind($py);
        let hull_id = $self.hull_id.bind($py);
        let arena_radius = $self.arena_radius.bind($py);
        let mut obs = borrow_mut(obs, "obs")?;
        let actions = actions
            .try_readonly()
            .map_err(|e| PyValueError::new_err(format!("env.actions cannot be read: {e}")))?;
        let mut rewards = borrow_mut(rewards, "rewards")?;
        let mut order_rewards = borrow_mut(order_rewards, "order_rewards")?;
        let mut order_transit = borrow_mut(order_transit, "order_transit")?;
        let mut ward_threat = borrow_mut(ward_threat, "ward_threat")?;
        let mut ward_hull_lost = borrow_mut(ward_hull_lost, "ward_hull_lost")?;
        let mut dones = borrow_mut(dones, "dones")?;
        let mut winner = borrow_mut(winner, "winner")?;
        let mut end_reason = borrow_mut(end_reason, "end_reason")?;
        let mut act_mask = borrow_mut(act_mask, "act_mask")?;
        let mut alive = borrow_mut(alive, "alive")?;
        let mut tick = borrow_mut(tick, "tick")?;
        let mut episode_count = borrow_mut(episode_count, "episode_count")?;
        let mut hits = borrow_mut(hits, "hits")?;
        let mut hit_count = borrow_mut(hit_count, "hit_count")?;
        let mut collision_damage = borrow_mut(collision_damage, "collision_damage")?;
        let mut thruster_mask = borrow_mut(thruster_mask, "thruster_mask")?;
        let mut turret_mask = borrow_mut(turret_mask, "turret_mask")?;
        let mut fixed_turret = borrow_mut(fixed_turret, "fixed_turret")?;
        let mut team = borrow_mut(team, "team")?;
        let mut hull_id = borrow_mut(hull_id, "hull_id")?;
        let mut arena_radius = borrow_mut(arena_radius, "arena_radius")?;
        let $bufs = StepBuffers {
            obs: as_slice(&mut obs, "obs")?,
            actions: actions
                .as_slice()
                .map_err(|e| PyValueError::new_err(format!("env.actions: {e}")))?,
            rewards: as_slice(&mut rewards, "rewards")?,
            order_rewards: as_slice(&mut order_rewards, "order_rewards")?,
            order_transit: as_slice(&mut order_transit, "order_transit")?,
            ward_threat: as_slice(&mut ward_threat, "ward_threat")?,
            ward_hull_lost: as_slice(&mut ward_hull_lost, "ward_hull_lost")?,
            dones: as_slice(&mut dones, "dones")?,
            winner: as_slice(&mut winner, "winner")?,
            end_reason: as_slice(&mut end_reason, "end_reason")?,
            act_mask: as_slice(&mut act_mask, "act_mask")?,
            alive: as_slice(&mut alive, "alive")?,
            tick: as_slice(&mut tick, "tick")?,
            episode_count: as_slice(&mut episode_count, "episode_count")?,
            hits: as_slice(&mut hits, "hits")?,
            hit_count: as_slice(&mut hit_count, "hit_count")?,
            collision_damage: as_slice(&mut collision_damage, "collision_damage")?,
            thruster_mask: as_slice(&mut thruster_mask, "thruster_mask")?,
            turret_mask: as_slice(&mut turret_mask, "turret_mask")?,
            fixed_turret: as_slice(&mut fixed_turret, "fixed_turret")?,
            team: as_slice(&mut team, "team")?,
            hull_id: as_slice(&mut hull_id, "hull_id")?,
            arena_radius: as_slice(&mut arena_radius, "arena_radius")?,
        };
        $body
    }};
}

fn check_team(team: i64) -> PyResult<u8> {
    match team {
        0 | 1 => Ok(team as u8),
        t => Err(PyValueError::new_err(format!(
            "team must be 0 or 1, got {t}"
        ))),
    }
}

impl VecEnv {
    fn check_index(&self, i: i64) -> PyResult<usize> {
        let n = self.batch.n_envs() as i64;
        if (0..n).contains(&i) {
            Ok(i as usize)
        } else {
            Err(PyIndexError::new_err(format!(
                "match index {i} out of range for {n} envs"
            )))
        }
    }

    fn copy_actions_in(&self, py: Python<'_>, src: &Bound<'_, PyAny>) -> PyResult<()> {
        let n = self.batch.n_envs();
        let s = self.batch.n_ships();
        let arr = src.cast::<PyArray3<i8>>().map_err(|_| {
            let dtype = src
                .getattr("dtype")
                .map(|d| d.to_string())
                .unwrap_or_else(|_| src.get_type().to_string());
            PyValueError::new_err(format!(
                "actions must be a numpy int8 array of shape ({n}, {s}, {ACTION_WIDTH}); got {dtype}"
            ))
        })?;
        if arr.shape() != [n, s, ACTION_WIDTH] {
            return Err(PyValueError::new_err(format!(
                "actions must have shape ({n}, {s}, {ACTION_WIDTH}); got {:?}",
                arr.shape()
            )));
        }
        let dst = self.actions.bind(py);
        if arr.is(dst) {
            return Ok(());
        }
        arr.copy_to(dst)
            .map_err(|e| PyValueError::new_err(format!("could not copy actions: {e}")))
    }
}

#[pymethods]
impl VecEnv {
    /// Build `n_envs` matches of `fleets[0]` vs `fleets[1]` from the hull and weapon
    /// YAML under `assets_dir`, and reset them (episode 0, seeds
    /// `split(seed, i, 0)`). `n_threads = 0` uses rayon's default thread count.
    /// `reaction_ticks` is the match-wide action delay `d` in `0..=MAX_REACTION_TICKS`
    /// (a hull's own `reaction_ticks` overrides it). `max_ships` is the number of
    /// ship slots per match (default: the size of `fleets`, at most `MAX_SHIPS`);
    /// rosters queued later with `set_next_roster` must fit in it. v4: `mission` is
    /// `None` (deathmatch, the v3 match), a kind name or a dict spec (SIM_SPEC §10.3);
    /// `commanders` names each team's commander mode, `"scripted"` (default),
    /// `"external"` (commands via `submit_command`) or (v5) `"random"` (the scripted
    /// logistics with random squads and orders). v6: `hide_orders` is `[team 0,
    /// team 1]` hidden-order mode (default both false): a hidden team's obs shows no
    /// order (SIM_SPEC §7.2); rewards and scripts are unaffected.
    #[new]
    #[pyo3(signature = (assets_dir, n_envs, fleets, seed, arena_radius=450.0, time_limit_s=90.0, n_threads=0, record_events=false, reaction_ticks=2, max_ships=None, mission=None, commanders=None, hide_orders=None))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        py: Python<'_>,
        assets_dir: &str,
        n_envs: i64,
        fleets: Vec<Vec<String>>,
        seed: u64,
        arena_radius: f32,
        time_limit_s: f32,
        n_threads: i64,
        record_events: bool,
        reaction_ticks: i64,
        max_ships: Option<i64>,
        mission: Option<&Bound<'_, PyAny>>,
        commanders: Option<Vec<String>>,
        hide_orders: Option<Vec<bool>>,
    ) -> PyResult<Self> {
        if n_envs < 1 {
            return Err(PyValueError::new_err(format!(
                "n_envs must be >= 1, got {n_envs}"
            )));
        }
        if n_threads < 0 {
            return Err(PyValueError::new_err(format!(
                "n_threads must be >= 0 (0 = default), got {n_threads}"
            )));
        }
        let time_limit_ticks = time_limit_ticks(time_limit_s)?;
        let reaction_ticks = u8::try_from(reaction_ticks)
            .ok()
            .filter(|&d| usize::from(d) <= MAX_REACTION_TICKS)
            .ok_or_else(|| {
                PyValueError::new_err(format!(
                    "reaction_ticks must be in 0..={MAX_REACTION_TICKS}, got {reaction_ticks}"
                ))
            })?;
        let cat = Catalogue::load_dir(Path::new(assets_dir))
            .map_err(|e| PyValueError::new_err(format!("loading {assets_dir:?}: {e}")))?;
        let fleets = resolve_fleets(&cat, &fleets)?;
        let mission = mission_from_py(py, mission, arena_radius)?;
        let commanders = commanders_from_py(commanders, [CommanderMode::Scripted; 2])?;
        let hide_orders = hide_orders_from_py(hide_orders, [false; 2])?;
        let total = fleets[0].len() + fleets[1].len();
        let n_ships = match max_ships {
            None => total,
            Some(m) if (total as i64..=MAX_SHIPS as i64).contains(&m) => m as usize,
            Some(m) => {
                return Err(PyValueError::new_err(format!(
                    "max_ships must be in {total}..={MAX_SHIPS} (the fleets have {total} ships), got {m}"
                )));
            }
        };
        let n = n_envs as usize;
        let batch = Batch::new(
            cat,
            BatchConfig {
                n_envs: n,
                base_seed: seed,
                reaction_ticks,
                roster: Roster {
                    fleets,
                    arena_radius,
                    mission,
                    commanders,
                    time_limit_ticks,
                    hide_orders,
                },
                n_ships,
                n_threads: n_threads as usize,
                record_events,
            },
        )
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let s = batch.n_ships();
        let mut env = VecEnv {
            batch,
            obs: PyArray3::zeros(py, [n, s, OBS_DIM], false).unbind(),
            actions: PyArray3::zeros(py, [n, s, ACTION_WIDTH], false).unbind(),
            rewards: PyArray2::zeros(py, [n, s], false).unbind(),
            order_rewards: PyArray2::zeros(py, [n, s], false).unbind(),
            order_transit: PyArray2::zeros(py, [n, s], false).unbind(),
            ward_threat: PyArray3::zeros(py, [n, s, s], false).unbind(),
            ward_hull_lost: PyArray2::zeros(py, [n, s], false).unbind(),
            dones: PyArray1::zeros(py, [n], false).unbind(),
            winner: PyArray1::zeros(py, [n], false).unbind(),
            end_reason: PyArray1::zeros(py, [n], false).unbind(),
            act_mask: PyArray2::zeros(py, [n, s], false).unbind(),
            thruster_mask: PyArray3::zeros(py, [n, s, MAX_THRUSTERS], false).unbind(),
            turret_mask: PyArray3::zeros(py, [n, s, MAX_TURRETS], false).unbind(),
            fixed_turret: PyArray3::zeros(py, [n, s, MAX_TURRETS], false).unbind(),
            team: PyArray2::zeros(py, [n, s], false).unbind(),
            hull_id: PyArray2::zeros(py, [n, s], false).unbind(),
            alive: PyArray2::zeros(py, [n, s], false).unbind(),
            tick: PyArray1::zeros(py, [n], false).unbind(),
            episode_count: PyArray1::zeros(py, [n], false).unbind(),
            hits: PyArray3::zeros(py, [n, MAX_HITS, HIT_FIELDS], false).unbind(),
            hit_count: PyArray1::zeros(py, [n], false).unbind(),
            collision_damage: PyArray2::zeros(py, [n, s], false).unbind(),
            arena_radius: PyArray1::zeros(py, [n], false).unbind(),
            default_commanders: commanders,
            default_time_limit_ticks: time_limit_ticks,
            default_hide_orders: hide_orders,
        };
        env.reset(py)?;
        Ok(env)
    }

    /// Queue a roster for env `i`: its next match (after its next done, or the next
    /// `reset()`) and every match after that is `fleets[0]` vs `fleets[1]` in an
    /// arena of `arena_radius` metres. Replaces a roster queued earlier; the current
    /// match is untouched. Raises ValueError for unknown hulls, an empty team, more
    /// ships than `n_ships`, a bad radius or fleets that do not fit the mission, and
    /// IndexError for a bad `i`. v4: `mission` as in the constructor (default
    /// deathmatch). v5: `commanders` as in the constructor (default: the
    /// constructor's); `time_limit_s` the match's clock (default: the mission's own
    /// limit, `mission_time_limit_s`, when a mission is given, else the
    /// constructor's `time_limit_s`). v6: `hide_orders` as in the constructor
    /// (default: the constructor's). Every field sticks with the roster.
    #[pyo3(signature = (i, fleets, arena_radius, mission=None, commanders=None, time_limit_s=None, hide_orders=None))]
    #[allow(clippy::too_many_arguments)]
    fn set_next_roster(
        &mut self,
        py: Python<'_>,
        i: i64,
        fleets: Vec<Vec<String>>,
        arena_radius: f32,
        mission: Option<&Bound<'_, PyAny>>,
        commanders: Option<Vec<String>>,
        time_limit_s: Option<f32>,
        hide_orders: Option<Vec<bool>>,
    ) -> PyResult<()> {
        let n = self.batch.n_envs() as i64;
        if !(0..n).contains(&i) {
            return Err(PyIndexError::new_err(format!(
                "env index {i} out of range for {n} envs"
            )));
        }
        let fleets = resolve_fleets(self.batch.catalogue(), &fleets)?;
        let time_limit_ticks = match (time_limit_s, mission) {
            (Some(s), _) => time_limit_ticks(s)?,
            (None, None) => self.default_time_limit_ticks,
            (None, Some(_)) => mission_from_py(py, mission, arena_radius)?
                .kind()
                .default_time_limit_ticks(),
        };
        let mission = mission_from_py(py, mission, arena_radius)?;
        let commanders = commanders_from_py(commanders, self.default_commanders)?;
        let hide_orders = hide_orders_from_py(hide_orders, self.default_hide_orders)?;
        self.batch
            .set_next_roster(
                i as usize,
                Roster {
                    fleets,
                    arena_radius,
                    mission,
                    commanders,
                    time_limit_ticks,
                    hide_orders,
                },
            )
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    /// Rebuild every match at episode 0 and write the fresh observations. Rewards,
    /// dones, hits are cleared; winner is -2.
    fn reset(&mut self, py: Python<'_>) -> PyResult<()> {
        let batch = &mut self.batch;
        with_step_buffers!(self, py, |bufs| py.detach(|| batch.reset(bufs)));
        Ok(())
    }

    /// Advance every match one tick with the rows in `env.actions` (or `actions`,
    /// an int8 `[N, S, 21]` array copied into `env.actions` first). Finished matches
    /// report `dones[i] = True` with their final rewards and winner, then are rebuilt
    /// with `episode_count[i] + 1`; their obs row is the fresh match's first one.
    #[pyo3(signature = (actions=None))]
    fn step(&mut self, py: Python<'_>, actions: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        if let Some(a) = actions {
            self.copy_actions_in(py, a)?;
        }
        let batch = &mut self.batch;
        with_step_buffers!(self, py, |bufs| py.detach(|| batch.step(bufs)));
        Ok(())
    }

    /// Write the scripted controller's actions into `env.actions` for every ship of
    /// `team` (0 or 1), or for all ships when `team` is None. Other rows are untouched.
    #[pyo3(signature = (team=None))]
    fn scripted_actions(&self, py: Python<'_>, team: Option<i64>) -> PyResult<()> {
        let team = match team {
            None => None,
            Some(t @ (0 | 1)) => Some(t as u8),
            Some(t) => {
                return Err(PyValueError::new_err(format!(
                    "team must be 0, 1 or None, got {t}"
                )));
            }
        };
        let actions = self.actions.bind(py);
        let mut actions = borrow_mut(actions, "actions")?;
        let rows = as_slice(&mut actions, "actions")?;
        let batch = &self.batch;
        py.detach(|| batch.scripted_actions(team, rows));
        Ok(())
    }

    /// v4: queue commands for team `team` of match `i`, applied on that match's next
    /// slow tick (`command_due`). `commands` is one command dict or a list of them
    /// (SIM_SPEC §10.3). Only an `"external"` team's commands are used; the queue is
    /// dropped if the match ends first.
    fn submit_command(
        &mut self,
        py: Python<'_>,
        i: i64,
        team: i64,
        commands: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        let i = self.check_index(i)?;
        let team = check_team(team)?;
        let text = json_dumps(py, commands)?;
        let specs = CommandSpec::parse_list(&text).map_err(PyValueError::new_err)?;
        let cmds = specs
            .iter()
            .map(|c| c.to_command(self.batch.catalogue()))
            .collect::<Result<Vec<_>, _>>()
            .map_err(PyValueError::new_err)?;
        let m = self.batch.match_at_mut(i);
        for c in cmds {
            m.submit_command(team, c);
        }
        Ok(())
    }

    /// v4: `bool[N]`, whether each match's next step is a slow (command) tick.
    fn command_due<'py>(&self, py: Python<'py>) -> Bound<'py, PyArray1<bool>> {
        let out: Vec<bool> = (0..self.batch.n_envs())
            .map(|i| self.batch.match_at(i).command_due())
            .collect();
        out.into_pyarray(py)
    }

    /// v4: outcomes of team `team`'s commands on match `i`'s last slow tick, a list
    /// of dicts (`command`, `outcome`, and `ship`/`bay` or `reason`).
    fn command_results<'py>(
        &self,
        py: Python<'py>,
        i: i64,
        team: i64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let m = self.batch.match_at(self.check_index(i)?);
        let views: Vec<OutcomeView> = m
            .command_results(check_team(team)?)
            .iter()
            .map(OutcomeView::of)
            .collect();
        json_loads(py, &to_json(&views))
    }

    /// v4: team `team`'s commander observation of match `i` (a dict; SIM_SPEC §5.9).
    fn commander_obs<'py>(
        &self,
        py: Python<'py>,
        i: i64,
        team: i64,
    ) -> PyResult<Bound<'py, PyAny>> {
        let m = self.batch.match_at(self.check_index(i)?);
        let cat = self.batch.catalogue();
        let obs = m.commander_obs(cat, check_team(team)?);
        json_loads(py, &to_json(&CommanderObsView::of(m, cat, &obs)))
    }

    /// v4: match `i`'s mission and command state (a dict: mission, end reason,
    /// carriers, hangars, bay cooldowns, squads, convoy, per-ship mission fields).
    fn mission_state<'py>(&self, py: Python<'py>, i: i64) -> PyResult<Bound<'py, PyAny>> {
        let m = self.batch.match_at(self.check_index(i)?);
        json_loads(
            py,
            &to_json(&MissionStateView::of(m, self.batch.catalogue())),
        )
    }

    /// v6: every slot's order instance now (`order` module), a dict of new arrays:
    /// `standing_kind` and `effective_kind` (`[N,S] int8`: 0 none, 1 attack, 2
    /// defend, 3 goto; standing is the squad's order or a capital ship's waypoint,
    /// effective drops invalid and completed orders), `target` (`[N,S] int16`, the
    /// instance's target or ward slot, -1), `point` (`[N,S,2] f32`, the instance's
    /// go-to point), `radius` (`[N,S] f32`, the standing go-to radius, 0 otherwise),
    /// `arrived` (`[N,S] bool`) and `instance_start` (`[N,S] uint32`, its start
    /// tick). Padding slots read 0 / -1 / false.
    fn order_tracks<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let (n, s) = (self.batch.n_envs(), self.batch.n_ships());
        let mut standing = Array2::<i8>::zeros(Dim([n, s]));
        let mut effective = Array2::<i8>::zeros(Dim([n, s]));
        let mut target = Array2::<i16>::from_elem(Dim([n, s]), -1);
        let mut point = numpy::ndarray::Array3::<f32>::zeros(Dim([n, s, 2]));
        let mut radius = Array2::<f32>::zeros(Dim([n, s]));
        let mut arrived = Array2::<bool>::from_elem(Dim([n, s]), false);
        let mut start = Array2::<u32>::zeros(Dim([n, s]));
        for i in 0..n {
            let m = self.batch.match_at(i);
            for k in 0..m.ships.len() {
                let order = sim::order::standing_order(m, k);
                let track = &m.order_tracks[k];
                standing[[i, k]] = order.kind() as i8;
                effective[[i, k]] = sim::order::effective_order(m, k).kind() as i8;
                if track.target != sim::state::NONE {
                    target[[i, k]] = i16::from(track.target);
                }
                point[[i, k, 0]] = track.point.x;
                point[[i, k, 1]] = track.point.y;
                if let sim::command::Order::GoTo { radius: r, .. } = order {
                    radius[[i, k]] = r;
                }
                arrived[[i, k]] = track.arrived;
                start[[i, k]] = track.start_tick;
            }
        }
        let out = PyDict::new(py);
        out.set_item("standing_kind", standing.into_pyarray(py))?;
        out.set_item("effective_kind", effective.into_pyarray(py))?;
        out.set_item("target", target.into_pyarray(py))?;
        out.set_item("point", point.into_pyarray(py))?;
        out.set_item("radius", radius.into_pyarray(py))?;
        out.set_item("arrived", arrived.into_pyarray(py))?;
        out.set_item("instance_start", start.into_pyarray(py))?;
        Ok(out)
    }

    /// Per-match determinism hash (SIM_SPEC §12), a new `uint64[N]` array.
    fn state_hash<'py>(&self, py: Python<'py>) -> Bound<'py, PyArray1<u64>> {
        let mut out = vec![0u64; self.batch.n_envs()];
        self.batch.state_hashes(&mut out);
        out.into_pyarray(py)
    }

    /// Debug snapshot of match `i`: tick, phase, winner, episode, and lists of ship
    /// and live projectile dicts (world frame).
    fn render_state<'py>(&self, py: Python<'py>, i: i64) -> PyResult<Bound<'py, PyDict>> {
        let n = self.batch.n_envs() as i64;
        if !(0..n).contains(&i) {
            return Err(PyIndexError::new_err(format!(
                "match index {i} out of range for {n} envs"
            )));
        }
        let m = self.batch.match_at(i as usize);
        let cat = self.batch.catalogue();
        let out = PyDict::new(py);
        out.set_item("tick", m.tick())?;
        out.set_item(
            "phase",
            match m.phase() {
                MatchPhase::Running => "running",
                MatchPhase::Over => "over",
            },
        )?;
        out.set_item("winner", m.winner())?;
        out.set_item("arena_radius", m.cfg.arena_radius)?;
        out.set_item("mission", m.cfg.mission.kind().name())?;
        out.set_item("end_reason", m.mission.end_reason.name())?;
        let ships = PyList::empty(py);
        for s in m.ships() {
            let hull = cat.hull(s.hull);
            let d = PyDict::new(py);
            d.set_item("slot", s.slot)?;
            d.set_item("team", s.team)?;
            d.set_item("hull", hull.name.as_str())?;
            d.set_item("hull_id", s.hull)?;
            d.set_item("role", hull.role.as_str())?;
            d.set_item("docked", s.attach == sim::state::Attach::Docked)?;
            d.set_item(
                "escaped",
                m.jump_state(s.slot) == sim::mission::JumpState::Departed,
            )?;
            d.set_item("pos", (s.pos.x, s.pos.y))?;
            d.set_item("vel", (s.vel.x, s.vel.y))?;
            d.set_item("heading", s.heading)?;
            d.set_item("omega", s.omega)?;
            d.set_item("hp", s.hp)?;
            d.set_item("max_hp", hull.hp)?;
            d.set_item("shield", s.shield)?;
            d.set_item("alive", s.alive)?;
            d.set_item("present", s.present)?;
            d.set_item("arrive_tick", s.arrive_tick)?;
            d.set_item("control_lock_until", s.control_lock_until)?;
            d.set_item("reaction_ticks", s.reaction_ticks)?;
            d.set_item("act_mask", act_mask(s, m.tick()))?;
            d.set_item("thrust_level", &s.thrust_level[..hull.thrusters.len()])?;
            d.set_item("turret_angle", &s.turret_angle[..hull.turrets.len()])?;
            d.set_item("power", s.power.to_vec())?;
            // The reaction queue as `ACTION_WIDTH` rows, `queue[0]` applying next; only
            // the first `reaction_ticks` entries are live.
            let queue = PyList::empty(py);
            for a in &s.queue[..usize::from(s.reaction_ticks)] {
                let mut row = [0i8; ACTION_WIDTH];
                a.to_row(&mut row);
                queue.append(row.to_vec())?;
            }
            d.set_item("queue", queue)?;
            ships.append(d)?;
        }
        out.set_item("ships", ships)?;
        let projectiles = PyList::empty(py);
        for p in m.projectiles().iter().filter(|p| p.alive) {
            let d = PyDict::new(py);
            d.set_item("kind", p.kind.index())?;
            d.set_item("team", p.team)?;
            d.set_item("owner", p.owner)?;
            d.set_item("pos", (p.pos.x, p.pos.y))?;
            d.set_item("vel", (p.vel.x, p.vel.y))?;
            d.set_item("damage", p.damage)?;
            d.set_item("life_ticks", p.life_ticks)?;
            d.set_item("fire_tick", p.fire_tick)?;
            d.set_item("decision_tick", p.decision_tick)?;
            projectiles.append(d)?;
        }
        out.set_item("projectiles", projectiles)?;
        Ok(out)
    }

    /// Events of the last step of every match, copied into a new `float32[E, 9]`
    /// array: column 0 is the match index, columns 1..9 the flat event encoding
    /// (SIM_SPEC §9). Requires `record_events=True`.
    fn events<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyArray2<f32>>> {
        if !self.batch.record_events() {
            return Err(PyValueError::new_err(
                "events() needs the env to be built with record_events=True",
            ));
        }
        let n = self.batch.n_envs();
        let total: usize = (0..n)
            .map(|i| self.batch.events_of(i).len() / EVENT_STRIDE)
            .sum();
        let mut out = Array2::<f32>::zeros(Dim([total, EVENT_STRIDE + 1]));
        let mut row = 0;
        for i in 0..n {
            for e in self.batch.events_of(i).chunks_exact(EVENT_STRIDE) {
                out[[row, 0]] = i as f32;
                for (k, &v) in e.iter().enumerate() {
                    out[[row, k + 1]] = v;
                }
                row += 1;
            }
        }
        Ok(out.into_pyarray(py))
    }

    #[getter]
    fn n_envs(&self) -> usize {
        self.batch.n_envs()
    }
    /// Ship slots per match (S): `max_ships`, or the constructor's fleet total.
    #[getter]
    fn n_ships(&self) -> usize {
        self.batch.n_ships()
    }
    #[getter]
    fn dt(&self) -> f32 {
        DT
    }
    #[getter]
    fn obs(&self, py: Python<'_>) -> Py<PyArray3<f32>> {
        self.obs.clone_ref(py)
    }
    #[getter]
    fn actions(&self, py: Python<'_>) -> Py<PyArray3<i8>> {
        self.actions.clone_ref(py)
    }
    #[getter]
    fn rewards(&self, py: Python<'_>) -> Py<PyArray2<f32>> {
        self.rewards.clone_ref(py)
    }
    #[getter]
    fn dones(&self, py: Python<'_>) -> Py<PyArray1<bool>> {
        self.dones.clone_ref(py)
    }
    #[getter]
    fn winner(&self, py: Python<'_>) -> Py<PyArray1<i8>> {
        self.winner.clone_ref(py)
    }
    /// v4: `EndReason` code of the match that ended on the last step (`[N] i8`; 0
    /// while running; `rlf_sim.END_REASONS` names them).
    #[getter]
    fn end_reason(&self, py: Python<'_>) -> Py<PyArray1<i8>> {
        self.end_reason.clone_ref(py)
    }
    #[getter]
    fn act_mask(&self, py: Python<'_>) -> Py<PyArray2<bool>> {
        self.act_mask.clone_ref(py)
    }
    #[getter]
    fn thruster_mask(&self, py: Python<'_>) -> Py<PyArray3<bool>> {
        self.thruster_mask.clone_ref(py)
    }
    #[getter]
    fn turret_mask(&self, py: Python<'_>) -> Py<PyArray3<bool>> {
        self.turret_mask.clone_ref(py)
    }
    #[getter]
    fn fixed_turret(&self, py: Python<'_>) -> Py<PyArray3<bool>> {
        self.fixed_turret.clone_ref(py)
    }
    #[getter]
    fn team(&self, py: Python<'_>) -> Py<PyArray2<i8>> {
        self.team.clone_ref(py)
    }
    #[getter]
    fn hull_id(&self, py: Python<'_>) -> Py<PyArray2<i16>> {
        self.hull_id.clone_ref(py)
    }
    #[getter]
    fn alive(&self, py: Python<'_>) -> Py<PyArray2<bool>> {
        self.alive.clone_ref(py)
    }
    #[getter]
    fn tick(&self, py: Python<'_>) -> Py<PyArray1<u32>> {
        self.tick.clone_ref(py)
    }
    #[getter]
    fn episode_count(&self, py: Python<'_>) -> Py<PyArray1<u32>> {
        self.episode_count.clone_ref(py)
    }
    #[getter]
    fn hits(&self, py: Python<'_>) -> Py<PyArray3<i32>> {
        self.hits.clone_ref(py)
    }
    #[getter]
    fn hit_count(&self, py: Python<'_>) -> Py<PyArray1<i32>> {
        self.hit_count.clone_ref(py)
    }
    /// v5: the order reward of the last step (`[N,S] f32`, SIM_SPEC §8; v6): attack
    /// damage on the ordered target, defend damage on the ward's threat set and the
    /// ward's hull loss and death, go-to shaping and arrival. Separate from `rewards` (the trainer
    /// weights it); zero for padding and ships that do not earn.
    #[getter]
    fn order_rewards(&self, py: Python<'_>) -> Py<PyArray2<f32>> {
        self.order_rewards.clone_ref(py)
    }
    /// v6: `[N,S] bool`, the slot's effective order is a go-to not yet arrived, or a
    /// defend whose ward's threat set is empty (`Match::order_transit`), as of the
    /// current obs (the rebuilt match after a done). Raw: the trainer decides which
    /// rows to pull toward the scripts.
    #[getter]
    fn order_transit(&self, py: Python<'_>) -> Py<PyArray2<bool>> {
        self.order_transit.clone_ref(py)
    }
    /// v6: `[N,S,S] bool`, `[i, w, e]` = ship `e` was in ship `w`'s threat set in the
    /// last step (every ship `w` on the field that step; the finished match on a
    /// done step, like `rewards`). The threat set the defend reward pays on.
    #[getter]
    fn ward_threat(&self, py: Python<'_>) -> Py<PyArray3<bool>> {
        self.ward_threat.clone_ref(py)
    }
    /// v6: `[N,S] f32`, the hull fraction each ship lost in the last step (a death
    /// counts the rest of its hull).
    #[getter]
    fn ward_hull_lost(&self, py: Python<'_>) -> Py<PyArray2<f32>> {
        self.ward_hull_lost.clone_ref(py)
    }
    /// Arena radius of each env's current match (`[N] f32`, metres).
    #[getter]
    fn arena_radius(&self, py: Python<'_>) -> Py<PyArray1<f32>> {
        self.arena_radius.clone_ref(py)
    }
    /// v3: hull damage each ship took from ship-ship collisions in the last step,
    /// after impact arcs (`[N,S] f32`; SIM_SPEC §5.5). Shield-absorbed collision
    /// damage is not included.
    #[getter]
    fn collision_damage(&self, py: Python<'_>) -> Py<PyArray2<f32>> {
        self.collision_damage.clone_ref(py)
    }
}
