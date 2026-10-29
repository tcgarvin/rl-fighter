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
use pyo3::types::{PyDict, PyList};
use sim::actions::ACTION_WIDTH;
use sim::data::{Catalogue, HullId};
use sim::events::EVENT_STRIDE;
use sim::obs::OBS_DIM;
use sim::state::{MAX_HITS, MAX_SHIPS, MAX_THRUSTERS, MAX_TURRETS, MatchPhase};
use sim::{DT, TICK_HZ};

use crate::batch::{Batch, BatchConfig, HIT_FIELDS, StaticBuffers, StepBuffers};

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

/// Batched env over `n_envs` matches with fixed fleets.
///
/// All buffer properties return the same numpy arrays on every call; `step()` and
/// `reset()` overwrite them in place. Write actions into `env.actions` (or pass an
/// array to `step`) before stepping.
#[pyclass(module = "rlf_sim")]
pub struct VecEnv {
    batch: Batch,
    obs: Py<PyArray3<f32>>,
    actions: Py<PyArray3<i8>>,
    rewards: Py<PyArray2<f32>>,
    dones: Py<PyArray1<bool>>,
    winner: Py<PyArray1<i8>>,
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
}

/// Borrow every per-step buffer and call `f` with the slices.
macro_rules! with_step_buffers {
    ($self:ident, $py:ident, |$bufs:ident| $body:expr) => {{
        let obs = $self.obs.bind($py);
        let actions = $self.actions.bind($py);
        let rewards = $self.rewards.bind($py);
        let dones = $self.dones.bind($py);
        let winner = $self.winner.bind($py);
        let act_mask = $self.act_mask.bind($py);
        let alive = $self.alive.bind($py);
        let tick = $self.tick.bind($py);
        let episode_count = $self.episode_count.bind($py);
        let hits = $self.hits.bind($py);
        let hit_count = $self.hit_count.bind($py);
        let mut obs = borrow_mut(obs, "obs")?;
        let actions = actions
            .try_readonly()
            .map_err(|e| PyValueError::new_err(format!("env.actions cannot be read: {e}")))?;
        let mut rewards = borrow_mut(rewards, "rewards")?;
        let mut dones = borrow_mut(dones, "dones")?;
        let mut winner = borrow_mut(winner, "winner")?;
        let mut act_mask = borrow_mut(act_mask, "act_mask")?;
        let mut alive = borrow_mut(alive, "alive")?;
        let mut tick = borrow_mut(tick, "tick")?;
        let mut episode_count = borrow_mut(episode_count, "episode_count")?;
        let mut hits = borrow_mut(hits, "hits")?;
        let mut hit_count = borrow_mut(hit_count, "hit_count")?;
        let $bufs = StepBuffers {
            obs: as_slice(&mut obs, "obs")?,
            actions: actions
                .as_slice()
                .map_err(|e| PyValueError::new_err(format!("env.actions: {e}")))?,
            rewards: as_slice(&mut rewards, "rewards")?,
            dones: as_slice(&mut dones, "dones")?,
            winner: as_slice(&mut winner, "winner")?,
            act_mask: as_slice(&mut act_mask, "act_mask")?,
            alive: as_slice(&mut alive, "alive")?,
            tick: as_slice(&mut tick, "tick")?,
            episode_count: as_slice(&mut episode_count, "episode_count")?,
            hits: as_slice(&mut hits, "hits")?,
            hit_count: as_slice(&mut hit_count, "hit_count")?,
        };
        $body
    }};
}

impl VecEnv {
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
    #[new]
    #[pyo3(signature = (assets_dir, n_envs, fleets, seed, arena_radius=450.0, time_limit_s=90.0, n_threads=0, record_events=false))]
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
        if !(time_limit_s.is_finite() && time_limit_s > 0.0) {
            return Err(PyValueError::new_err(format!(
                "time_limit_s must be positive and finite, got {time_limit_s}"
            )));
        }
        let time_limit_ticks = (time_limit_s * TICK_HZ).round().max(1.0) as u32;
        let cat = Catalogue::load_dir(Path::new(assets_dir))
            .map_err(|e| PyValueError::new_err(format!("loading {assets_dir:?}: {e}")))?;
        let fleets = resolve_fleets(&cat, &fleets)?;
        let n = n_envs as usize;
        let batch = Batch::new(
            cat,
            BatchConfig {
                n_envs: n,
                base_seed: seed,
                arena_radius,
                time_limit_ticks,
                fleets,
                n_threads: n_threads as usize,
                record_events,
            },
        )
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
        let s = batch.n_ships();
        let env = VecEnv {
            batch,
            obs: PyArray3::zeros(py, [n, s, OBS_DIM], false).unbind(),
            actions: PyArray3::zeros(py, [n, s, ACTION_WIDTH], false).unbind(),
            rewards: PyArray2::zeros(py, [n, s], false).unbind(),
            dones: PyArray1::zeros(py, [n], false).unbind(),
            winner: PyArray1::zeros(py, [n], false).unbind(),
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
        };
        {
            let thruster_mask = env.thruster_mask.bind(py);
            let turret_mask = env.turret_mask.bind(py);
            let fixed_turret = env.fixed_turret.bind(py);
            let team = env.team.bind(py);
            let hull_id = env.hull_id.bind(py);
            let mut thruster_mask = borrow_mut(thruster_mask, "thruster_mask")?;
            let mut turret_mask = borrow_mut(turret_mask, "turret_mask")?;
            let mut fixed_turret = borrow_mut(fixed_turret, "fixed_turret")?;
            let mut team = borrow_mut(team, "team")?;
            let mut hull_id = borrow_mut(hull_id, "hull_id")?;
            env.batch.write_static(StaticBuffers {
                thruster_mask: as_slice(&mut thruster_mask, "thruster_mask")?,
                turret_mask: as_slice(&mut turret_mask, "turret_mask")?,
                fixed_turret: as_slice(&mut fixed_turret, "fixed_turret")?,
                team: as_slice(&mut team, "team")?,
                hull_id: as_slice(&mut hull_id, "hull_id")?,
            });
        }
        let mut env = env;
        env.reset(py)?;
        Ok(env)
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
        let ships = PyList::empty(py);
        for s in m.ships() {
            let hull = cat.hull(s.hull);
            let d = PyDict::new(py);
            d.set_item("slot", s.slot)?;
            d.set_item("team", s.team)?;
            d.set_item("hull", hull.name.as_str())?;
            d.set_item("hull_id", s.hull)?;
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
            d.set_item("thrust_level", &s.thrust_level[..hull.thrusters.len()])?;
            d.set_item("turret_angle", &s.turret_angle[..hull.turrets.len()])?;
            d.set_item("power", s.power.to_vec())?;
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
    /// Ships per match (S): the fleet total.
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
}
