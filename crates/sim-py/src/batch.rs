//! The batched env core, free of Python types: N matches with fixed fleets, stepped
//! in parallel on a dedicated rayon pool, writing into caller-owned flat buffers
//! (SIM_SPEC §8 episode semantics, §10.1).
//!
//! The pyo3 layer (`vec_env.rs`) borrows the numpy buffers as slices and hands them
//! here; keeping this file Python-free means the threading and auto-reset logic is
//! plain Rust that `cargo test` covers without an interpreter.

use rayon::prelude::*;
use sim::actions::{self, ACTION_WIDTH, ShipAction};
use sim::data::{Catalogue, HullId};
use sim::obs::OBS_DIM;
use sim::rng;
use sim::scripted;
use sim::setup::{MatchConfig, SetupError};
use sim::state::{MAX_HITS, MAX_THRUSTERS, MAX_TURRETS, Match, MatchPhase, WINNER_NONE};

/// Columns of one row of the hits buffer: shooter, target, fire_tick, damage*1000, shield.
pub const HIT_FIELDS: usize = 5;
/// Fixed-point scale of the damage column of the hits buffer.
pub const HIT_DAMAGE_SCALE: f32 = 1000.0;

/// Settings shared by every match of the batch.
#[derive(Clone, Debug)]
pub struct BatchConfig {
    pub n_envs: usize,
    pub base_seed: u64,
    pub arena_radius: f32,
    pub time_limit_ticks: u32,
    pub fleets: [Vec<HullId>; 2],
    pub n_threads: usize,
    pub record_events: bool,
}

/// Why a batch could not be built.
#[derive(Debug)]
pub enum BatchError {
    Setup(SetupError),
    ThreadPool(rayon::ThreadPoolBuildError),
}

impl std::fmt::Display for BatchError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BatchError::Setup(e) => write!(f, "invalid match config: {e}"),
            BatchError::ThreadPool(e) => write!(f, "could not build the thread pool: {e}"),
        }
    }
}

impl std::error::Error for BatchError {}

/// Per-step buffers, flat and C-ordered: `obs [N,S,OBS_DIM]`, `actions [N,S,21]`,
/// `rewards/act_mask/alive [N,S]`, `dones/winner/tick/episode_count/hit_count [N]`,
/// `hits [N,MAX_HITS,5]`.
pub struct StepBuffers<'a> {
    pub obs: &'a mut [f32],
    pub actions: &'a [i8],
    pub rewards: &'a mut [f32],
    pub dones: &'a mut [bool],
    pub winner: &'a mut [i8],
    pub act_mask: &'a mut [bool],
    pub alive: &'a mut [bool],
    pub tick: &'a mut [u32],
    pub episode_count: &'a mut [u32],
    pub hits: &'a mut [i32],
    pub hit_count: &'a mut [i32],
}

/// Buffers that only change when the fleets do (i.e. never after construction):
/// `thruster_mask [N,S,8]`, `turret_mask/fixed_turret [N,S,6]`, `team/hull_id [N,S]`.
pub struct StaticBuffers<'a> {
    pub thruster_mask: &'a mut [bool],
    pub turret_mask: &'a mut [bool],
    pub fixed_turret: &'a mut [bool],
    pub team: &'a mut [i8],
    pub hull_id: &'a mut [i16],
}

/// One match's rows of [`StepBuffers`].
struct MatchRows<'a> {
    obs: &'a mut [f32],
    actions: &'a [i8],
    rewards: &'a mut [f32],
    done: &'a mut bool,
    winner: &'a mut i8,
    act_mask: &'a mut [bool],
    alive: &'a mut [bool],
    tick: &'a mut u32,
    episode_count: &'a mut u32,
    hits: &'a mut [i32],
    hit_count: &'a mut i32,
}

/// One match plus the env-side state that travels with it.
struct Slot {
    m: Match,
    episode: u32,
    /// Flat `EVENT_STRIDE` encoding of the last step's events (record_events only).
    events: Vec<f32>,
}

pub struct Batch {
    cat: Catalogue,
    cfg: BatchConfig,
    n_ships: usize,
    slots: Vec<Slot>,
    pool: rayon::ThreadPool,
}

fn match_config(cfg: &BatchConfig, index: usize, episode: u32) -> MatchConfig {
    MatchConfig {
        seed: rng::split(cfg.base_seed, index as u64, u64::from(episode)),
        arena_radius: cfg.arena_radius,
        time_limit_ticks: cfg.time_limit_ticks,
        // No delay until WP13 adds the `reaction_ticks` kwarg (default 2) and moves the
        // credit adapter onto `decision_tick`; with d = 0 v1 credit placement holds.
        reaction_ticks: 0,
        fleets: cfg.fleets.clone(),
    }
}

impl Batch {
    /// Build `n_envs` matches at episode 0. The match config is validated once here
    /// (by building match 0), so later auto-resets cannot fail.
    pub fn new(cat: Catalogue, cfg: BatchConfig) -> Result<Batch, BatchError> {
        assert!(
            cfg.n_envs >= 1,
            "n_envs must be >= 1 (validated by the caller)"
        );
        Match::new(&cat, &match_config(&cfg, 0, 0)).map_err(BatchError::Setup)?;
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(cfg.n_threads)
            .build()
            .map_err(BatchError::ThreadPool)?;
        let n_ships = cfg.fleets[0].len() + cfg.fleets[1].len();
        let mut batch = Batch {
            cat,
            cfg,
            n_ships,
            slots: Vec::new(),
            pool,
        };
        batch.rebuild_all();
        Ok(batch)
    }

    fn new_match(&self, index: usize, episode: u32) -> Match {
        Match::new(&self.cat, &match_config(&self.cfg, index, episode))
            .expect("match config was validated in Batch::new")
    }

    fn rebuild_all(&mut self) {
        self.slots = (0..self.cfg.n_envs)
            .map(|i| Slot {
                m: self.new_match(i, 0),
                episode: 0,
                events: Vec::new(),
            })
            .collect();
    }

    pub fn n_envs(&self) -> usize {
        self.cfg.n_envs
    }

    /// Ships per match (S): the fleet total, identical for every match.
    pub fn n_ships(&self) -> usize {
        self.n_ships
    }

    pub fn catalogue(&self) -> &Catalogue {
        &self.cat
    }

    pub fn record_events(&self) -> bool {
        self.cfg.record_events
    }

    pub fn match_at(&self, i: usize) -> &Match {
        &self.slots[i].m
    }

    /// Flat encoded events of match `i`'s last step (empty unless record_events).
    pub fn events_of(&self, i: usize) -> &[f32] {
        &self.slots[i].events
    }

    pub fn state_hashes(&self, out: &mut [u64]) {
        for (o, s) in out.iter_mut().zip(&self.slots) {
            *o = s.m.state_hash();
        }
    }

    /// Rebuild every match at episode 0 and write the fresh observations.
    pub fn reset(&mut self, bufs: StepBuffers<'_>) {
        self.rebuild_all();
        let rows = self.split_rows(bufs);
        let (cat, n_ships) = (&self.cat, self.n_ships);
        self.pool.install(|| {
            self.slots
                .par_iter_mut()
                .zip(rows)
                .for_each(|(slot, mut r)| {
                    r.rewards.fill(0.0);
                    *r.done = false;
                    *r.winner = WINNER_NONE;
                    r.hits.fill(0);
                    *r.hit_count = 0;
                    slot.events.clear();
                    write_post_step(cat, n_ships, slot, &mut r);
                });
        });
    }

    /// Apply each match's action rows, advance every match one tick, record rewards,
    /// hits and dones, auto-reset finished matches, then write observations.
    pub fn step(&mut self, bufs: StepBuffers<'_>) {
        let rows = self.split_rows(bufs);
        let cat = &self.cat;
        let cfg = &self.cfg;
        let n_ships = self.n_ships;
        self.pool.install(|| {
            self.slots
                .par_iter_mut()
                .zip(rows)
                .enumerate()
                .for_each(|(i, (slot, mut r))| step_one(cat, cfg, n_ships, i, slot, &mut r));
        });
    }

    /// Write the scripted controller's action rows into `actions` (`[N,S,21]`) for
    /// every ship of `team`, or every ship when `team` is `None`.
    pub fn scripted_actions(&self, team: Option<u8>, actions: &mut [i8]) {
        let row_len = self.n_ships * ACTION_WIDTH;
        let cat = &self.cat;
        self.pool.install(|| {
            self.slots
                .par_iter()
                .zip(actions.par_chunks_mut(row_len))
                .for_each(|(slot, rows)| {
                    for (s, ship) in slot.m.ships.iter().enumerate() {
                        if team.is_some_and(|t| t != ship.team) {
                            continue;
                        }
                        let a = scripted::act(&slot.m, cat, ship.slot);
                        a.to_row(&mut rows[s * ACTION_WIDTH..(s + 1) * ACTION_WIDTH]);
                    }
                });
        });
    }

    /// Fill the per-slot fleet buffers (masks, team, hull id).
    pub fn write_static(&self, bufs: StaticBuffers<'_>) {
        let s_n = self.n_ships;
        let m0 = &self.slots[0].m;
        for i in 0..self.cfg.n_envs {
            for (s, ship) in m0.ships.iter().enumerate() {
                let hull = self.cat.hull(ship.hull);
                let k = i * s_n + s;
                bufs.thruster_mask[k * MAX_THRUSTERS..(k + 1) * MAX_THRUSTERS]
                    .copy_from_slice(&actions::thruster_mask(hull));
                bufs.turret_mask[k * MAX_TURRETS..(k + 1) * MAX_TURRETS]
                    .copy_from_slice(&actions::turret_mask(hull));
                bufs.fixed_turret[k * MAX_TURRETS..(k + 1) * MAX_TURRETS]
                    .copy_from_slice(&actions::fixed_turret(hull));
                bufs.team[k] = ship.team as i8;
                bufs.hull_id[k] = ship.hull as i16;
            }
        }
    }

    fn split_rows<'a>(&self, b: StepBuffers<'a>) -> Vec<MatchRows<'a>> {
        let s = self.n_ships;
        let n = self.cfg.n_envs;
        debug_assert_eq!(b.obs.len(), n * s * OBS_DIM);
        debug_assert_eq!(b.actions.len(), n * s * ACTION_WIDTH);
        debug_assert_eq!(b.hits.len(), n * MAX_HITS * HIT_FIELDS);
        let mut obs = b.obs.chunks_mut(s * OBS_DIM);
        let mut actions = b.actions.chunks(s * ACTION_WIDTH);
        let mut rewards = b.rewards.chunks_mut(s);
        let mut dones = b.dones.iter_mut();
        let mut winner = b.winner.iter_mut();
        let mut act_mask = b.act_mask.chunks_mut(s);
        let mut alive = b.alive.chunks_mut(s);
        let mut tick = b.tick.iter_mut();
        let mut episode_count = b.episode_count.iter_mut();
        let mut hits = b.hits.chunks_mut(MAX_HITS * HIT_FIELDS);
        let mut hit_count = b.hit_count.iter_mut();
        const SHORT: &str = "buffer shorter than n_envs rows";
        let out: Vec<MatchRows<'a>> = (0..n)
            .map(|_| MatchRows {
                obs: obs.next().expect(SHORT),
                actions: actions.next().expect(SHORT),
                rewards: rewards.next().expect(SHORT),
                done: dones.next().expect(SHORT),
                winner: winner.next().expect(SHORT),
                act_mask: act_mask.next().expect(SHORT),
                alive: alive.next().expect(SHORT),
                tick: tick.next().expect(SHORT),
                episode_count: episode_count.next().expect(SHORT),
                hits: hits.next().expect(SHORT),
                hit_count: hit_count.next().expect(SHORT),
            })
            .collect();
        assert_eq!(out.len(), n, "buffer row count does not match n_envs");
        out
    }
}

/// Step one match and fill its rows (SIM_SPEC §8 episode semantics).
fn step_one(
    cat: &Catalogue,
    cfg: &BatchConfig,
    n_ships: usize,
    index: usize,
    slot: &mut Slot,
    r: &mut MatchRows<'_>,
) {
    let m = &mut slot.m;
    for s in 0..n_ships {
        let row = &r.actions[s * ACTION_WIDTH..(s + 1) * ACTION_WIDTH];
        m.set_action(s as u8, ShipAction::from_row(row));
    }
    m.step(cat);

    r.rewards.copy_from_slice(m.rewards());
    write_hits(m, r);
    if cfg.record_events {
        m.events.encode_into(&mut slot.events);
    }

    let done = m.phase() == MatchPhase::Over;
    *r.done = done;
    *r.winner = m.winner();
    if done {
        slot.episode += 1;
        slot.m = Match::new(cat, &match_config(cfg, index, slot.episode))
            .expect("match config was validated in Batch::new");
    }
    write_post_step(cat, n_ships, slot, r);
}

fn write_hits(m: &Match, r: &mut MatchRows<'_>) {
    let hits = m.hits();
    for (row, h) in r.hits.chunks_exact_mut(HIT_FIELDS).zip(hits) {
        row[0] = i32::from(h.shooter);
        row[1] = i32::from(h.target);
        row[2] = h.fire_tick as i32;
        row[3] = (h.damage * HIT_DAMAGE_SCALE).round() as i32;
        row[4] = i32::from(h.shield);
    }
    r.hits[hits.len() * HIT_FIELDS..].fill(0);
    *r.hit_count = hits.len() as i32;
}

/// Rows that describe the (possibly just rebuilt) match after the step.
fn write_post_step(cat: &Catalogue, n_ships: usize, slot: &Slot, r: &mut MatchRows<'_>) {
    let m = &slot.m;
    for s in 0..n_ships {
        m.write_obs(cat, s as u8, &mut r.obs[s * OBS_DIM..(s + 1) * OBS_DIM]);
        let ship = &m.ships[s];
        r.act_mask[s] = actions::act_mask(ship, m.tick());
        r.alive[s] = ship.alive;
    }
    *r.tick = m.tick();
    *r.episode_count = slot.episode;
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    fn catalogue() -> Catalogue {
        let assets = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets");
        Catalogue::load_dir(&assets).expect("assets load")
    }

    struct Owned {
        obs: Vec<f32>,
        actions: Vec<i8>,
        rewards: Vec<f32>,
        dones: Vec<bool>,
        winner: Vec<i8>,
        act_mask: Vec<bool>,
        alive: Vec<bool>,
        tick: Vec<u32>,
        episode_count: Vec<u32>,
        hits: Vec<i32>,
        hit_count: Vec<i32>,
    }

    impl Owned {
        fn new(n: usize, s: usize) -> Owned {
            Owned {
                obs: vec![0.0; n * s * OBS_DIM],
                actions: vec![0; n * s * ACTION_WIDTH],
                rewards: vec![0.0; n * s],
                dones: vec![false; n],
                winner: vec![0; n],
                act_mask: vec![false; n * s],
                alive: vec![false; n * s],
                tick: vec![0; n],
                episode_count: vec![0; n],
                hits: vec![0; n * MAX_HITS * HIT_FIELDS],
                hit_count: vec![0; n],
            }
        }

        fn bufs(&mut self) -> StepBuffers<'_> {
            StepBuffers {
                obs: &mut self.obs,
                actions: &self.actions,
                rewards: &mut self.rewards,
                dones: &mut self.dones,
                winner: &mut self.winner,
                act_mask: &mut self.act_mask,
                alive: &mut self.alive,
                tick: &mut self.tick,
                episode_count: &mut self.episode_count,
                hits: &mut self.hits,
                hit_count: &mut self.hit_count,
            }
        }
    }

    fn batch(n_threads: usize) -> Batch {
        let cat = catalogue();
        let f = cat.hull_id("fighter").unwrap();
        Batch::new(
            cat,
            BatchConfig {
                n_envs: 8,
                base_seed: 3,
                arena_radius: 450.0,
                time_limit_ticks: 300,
                fleets: [vec![f], vec![f]],
                n_threads,
                record_events: false,
            },
        )
        .unwrap()
    }

    fn run(n_threads: usize, steps: usize) -> (Vec<u64>, Vec<u32>) {
        let mut b = batch(n_threads);
        let mut o = Owned::new(8, 2);
        b.reset(o.bufs());
        for _ in 0..steps {
            let mut actions = std::mem::take(&mut o.actions);
            b.scripted_actions(None, &mut actions);
            o.actions = actions;
            b.step(o.bufs());
        }
        let mut h = vec![0; 8];
        b.state_hashes(&mut h);
        (h, o.episode_count)
    }

    #[test]
    fn thread_count_does_not_change_results() {
        assert_eq!(run(1, 700), run(4, 700));
    }

    #[test]
    fn time_limit_auto_resets_with_next_episode_seed() {
        let (_, episodes) = run(2, 301);
        assert!(episodes.iter().all(|&e| e >= 1), "{episodes:?}");
    }
}
