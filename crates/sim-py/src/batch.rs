//! The batched env core, free of Python types: N matches stepped in parallel on a
//! dedicated rayon pool, writing into caller-owned flat buffers (SIM_SPEC §8 episode
//! semantics, §10.1).
//!
//! Every match has `S = n_ships` buffer slots. A match with fewer ships fills slots
//! `0..k` (team 0 then team 1, as `Match` numbers them) and leaves `k..S` as padding:
//! zero obs, `act_mask`/`alive` false, team and hull id -1, empty masks, zero rewards.
//! Each env keeps its roster (fleets + arena radius) from match to match until
//! [`Batch::set_next_roster`] queues another for its next rebuild (auto-reset or
//! [`Batch::reset`]); the per-slot buffers (masks, team, hull id, arena radius) are
//! rewritten whenever a match is rebuilt, so they describe the current match.
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

/// Columns of one row of the hits buffer: shooter, target, fire_tick, damage*1000,
/// shield, decision_tick (SIM_SPEC §8, v2).
pub const HIT_FIELDS: usize = 6;
/// Fixed-point scale of the damage column of the hits buffer.
pub const HIT_DAMAGE_SCALE: f32 = 1000.0;
/// Team and hull id of a padding slot.
pub const PAD_SLOT: i8 = -1;

/// Who plays a match: each team's hulls in slot order, and the arena radius.
#[derive(Clone, Debug, PartialEq)]
pub struct Roster {
    pub fleets: [Vec<HullId>; 2],
    pub arena_radius: f32,
}

impl Roster {
    /// Ships in the match (both teams).
    pub fn n_ships(&self) -> usize {
        self.fleets[0].len() + self.fleets[1].len()
    }
}

/// Settings shared by every match of the batch.
#[derive(Clone, Debug)]
pub struct BatchConfig {
    pub n_envs: usize,
    pub base_seed: u64,
    pub time_limit_ticks: u32,
    /// Match-wide reaction delay `d` (hulls may override it).
    pub reaction_ticks: u8,
    /// The roster every env starts with.
    pub roster: Roster,
    /// Buffer slots per match (S); at least the roster's ship count.
    pub n_ships: usize,
    pub n_threads: usize,
    pub record_events: bool,
}

/// Why a batch could not be built, or a roster not queued.
#[derive(Debug)]
pub enum BatchError {
    Setup(SetupError),
    ThreadPool(rayon::ThreadPoolBuildError),
    /// The roster has more ships than the batch has slots.
    TooManyShips {
        count: usize,
        n_ships: usize,
    },
    /// Env index outside `0..n_envs`.
    EnvIndex {
        index: usize,
        n_envs: usize,
    },
}

impl std::fmt::Display for BatchError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BatchError::Setup(e) => write!(f, "invalid match config: {e}"),
            BatchError::ThreadPool(e) => write!(f, "could not build the thread pool: {e}"),
            BatchError::TooManyShips { count, n_ships } => write!(
                f,
                "roster has {count} ships but the env has {n_ships} slots per match"
            ),
            BatchError::EnvIndex { index, n_envs } => {
                write!(f, "env index {index} out of range for {n_envs} envs")
            }
        }
    }
}

impl std::error::Error for BatchError {}

/// Per-step buffers, flat and C-ordered: `obs [N,S,OBS_DIM]`, `actions [N,S,21]`,
/// `rewards/act_mask/alive/collision_damage/team/hull_id [N,S]`,
/// `dones/winner/tick/episode_count/hit_count/arena_radius [N]`,
/// `hits [N,MAX_HITS,HIT_FIELDS]`, `thruster_mask [N,S,8]`,
/// `turret_mask/fixed_turret [N,S,6]`.
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
    /// v3: hull damage each ship took from collisions in the step (SIM_SPEC §5.5).
    pub collision_damage: &'a mut [f32],
    // Per-match buffers, rewritten only when a match is rebuilt.
    pub thruster_mask: &'a mut [bool],
    pub turret_mask: &'a mut [bool],
    pub fixed_turret: &'a mut [bool],
    pub team: &'a mut [i8],
    pub hull_id: &'a mut [i16],
    pub arena_radius: &'a mut [f32],
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
    collision_damage: &'a mut [f32],
    thruster_mask: &'a mut [bool],
    turret_mask: &'a mut [bool],
    fixed_turret: &'a mut [bool],
    team: &'a mut [i8],
    hull_id: &'a mut [i16],
    arena_radius: &'a mut f32,
}

/// One match plus the env-side state that travels with it.
struct Slot {
    m: Match,
    episode: u32,
    /// The roster of `m` (and of every later match until `next` is set).
    roster: Roster,
    /// Roster queued for the next rebuild.
    next: Option<Roster>,
    /// Flat `EVENT_STRIDE` encoding of the last step's events (record_events only).
    events: Vec<f32>,
}

pub struct Batch {
    cat: Catalogue,
    cfg: BatchConfig,
    slots: Vec<Slot>,
    pool: rayon::ThreadPool,
}

fn match_config(cfg: &BatchConfig, roster: &Roster, index: usize, episode: u32) -> MatchConfig {
    MatchConfig {
        seed: rng::split(cfg.base_seed, index as u64, u64::from(episode)),
        arena_radius: roster.arena_radius,
        time_limit_ticks: cfg.time_limit_ticks,
        reaction_ticks: cfg.reaction_ticks,
        fleets: roster.fleets.clone(),
    }
}

/// Build match `index` at `episode`; the roster was validated when it was accepted.
fn build_match(
    cat: &Catalogue,
    cfg: &BatchConfig,
    roster: &Roster,
    index: usize,
    episode: u32,
) -> Match {
    Match::new(cat, &match_config(cfg, roster, index, episode))
        .expect("roster was validated when the batch accepted it")
}

impl Batch {
    /// Build `n_envs` matches of `cfg.roster` at episode 0. The roster is validated
    /// here (and every later one by `set_next_roster`), so auto-resets cannot fail.
    pub fn new(cat: Catalogue, cfg: BatchConfig) -> Result<Batch, BatchError> {
        assert!(
            cfg.n_envs >= 1,
            "n_envs must be >= 1 (validated by the caller)"
        );
        validate_roster(&cat, &cfg, &cfg.roster)?;
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(cfg.n_threads)
            .build()
            .map_err(BatchError::ThreadPool)?;
        let slots = (0..cfg.n_envs)
            .map(|i| Slot {
                m: build_match(&cat, &cfg, &cfg.roster, i, 0),
                episode: 0,
                roster: cfg.roster.clone(),
                next: None,
                events: Vec::new(),
            })
            .collect();
        Ok(Batch {
            cat,
            cfg,
            slots,
            pool,
        })
    }

    pub fn n_envs(&self) -> usize {
        self.cfg.n_envs
    }

    /// Buffer slots per match (S), identical for every match.
    pub fn n_ships(&self) -> usize {
        self.cfg.n_ships
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

    /// Queue `roster` for env `index`'s next rebuild (its next auto-reset, or
    /// `reset`). Replaces a roster queued earlier; the current match is untouched.
    pub fn set_next_roster(&mut self, index: usize, roster: Roster) -> Result<(), BatchError> {
        let n_envs = self.cfg.n_envs;
        if index >= n_envs {
            return Err(BatchError::EnvIndex { index, n_envs });
        }
        validate_roster(&self.cat, &self.cfg, &roster)?;
        self.slots[index].next = Some(roster);
        Ok(())
    }

    /// Rebuild every match at episode 0 (with its queued roster, if any) and write
    /// the fresh observations and per-match buffers.
    pub fn reset(&mut self, bufs: StepBuffers<'_>) {
        let rows = split_rows(&self.cfg, bufs);
        let (cat, cfg) = (&self.cat, &self.cfg);
        self.pool.install(|| {
            self.slots
                .par_iter_mut()
                .zip(rows)
                .enumerate()
                .for_each(|(i, (slot, mut r))| {
                    if let Some(next) = slot.next.take() {
                        slot.roster = next;
                    }
                    slot.episode = 0;
                    slot.m = build_match(cat, cfg, &slot.roster, i, 0);
                    r.rewards.fill(0.0);
                    *r.done = false;
                    *r.winner = WINNER_NONE;
                    r.hits.fill(0);
                    *r.hit_count = 0;
                    r.collision_damage.fill(0.0);
                    slot.events.clear();
                    write_post_step(cat, slot, &mut r, true);
                });
        });
    }

    /// Apply each match's action rows, advance every match one tick, record rewards,
    /// hits and dones, auto-reset finished matches, then write observations.
    pub fn step(&mut self, bufs: StepBuffers<'_>) {
        let rows = split_rows(&self.cfg, bufs);
        let cat = &self.cat;
        let cfg = &self.cfg;
        self.pool.install(|| {
            self.slots
                .par_iter_mut()
                .zip(rows)
                .enumerate()
                .for_each(|(i, (slot, mut r))| step_one(cat, cfg, i, slot, &mut r));
        });
    }

    /// Write the scripted controller's action rows into `actions` (`[N,S,21]`) for
    /// every ship of `team`, or every ship when `team` is `None`. Padding rows and
    /// other teams' rows are untouched.
    pub fn scripted_actions(&self, team: Option<u8>, actions: &mut [i8]) {
        let row_len = self.cfg.n_ships * ACTION_WIDTH;
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
}

fn validate_roster(cat: &Catalogue, cfg: &BatchConfig, roster: &Roster) -> Result<(), BatchError> {
    let count = roster.n_ships();
    if count > cfg.n_ships {
        return Err(BatchError::TooManyShips {
            count,
            n_ships: cfg.n_ships,
        });
    }
    match_config(cfg, roster, 0, 0)
        .validate(cat)
        .map_err(BatchError::Setup)
}

fn split_rows<'a>(cfg: &BatchConfig, b: StepBuffers<'a>) -> Vec<MatchRows<'a>> {
    let s = cfg.n_ships;
    let n = cfg.n_envs;
    debug_assert_eq!(b.obs.len(), n * s * OBS_DIM);
    debug_assert_eq!(b.actions.len(), n * s * ACTION_WIDTH);
    debug_assert_eq!(b.hits.len(), n * MAX_HITS * HIT_FIELDS);
    debug_assert_eq!(b.thruster_mask.len(), n * s * MAX_THRUSTERS);
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
    let mut collision_damage = b.collision_damage.chunks_mut(s);
    let mut thruster_mask = b.thruster_mask.chunks_mut(s * MAX_THRUSTERS);
    let mut turret_mask = b.turret_mask.chunks_mut(s * MAX_TURRETS);
    let mut fixed_turret = b.fixed_turret.chunks_mut(s * MAX_TURRETS);
    let mut team = b.team.chunks_mut(s);
    let mut hull_id = b.hull_id.chunks_mut(s);
    let mut arena_radius = b.arena_radius.iter_mut();
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
            collision_damage: collision_damage.next().expect(SHORT),
            thruster_mask: thruster_mask.next().expect(SHORT),
            turret_mask: turret_mask.next().expect(SHORT),
            fixed_turret: fixed_turret.next().expect(SHORT),
            team: team.next().expect(SHORT),
            hull_id: hull_id.next().expect(SHORT),
            arena_radius: arena_radius.next().expect(SHORT),
        })
        .collect();
    assert_eq!(out.len(), n, "buffer row count does not match n_envs");
    out
}

/// Step one match and fill its rows (SIM_SPEC §8 episode semantics).
fn step_one(
    cat: &Catalogue,
    cfg: &BatchConfig,
    index: usize,
    slot: &mut Slot,
    r: &mut MatchRows<'_>,
) {
    let m = &mut slot.m;
    let k = m.ships.len();
    for s in 0..k {
        let row = &r.actions[s * ACTION_WIDTH..(s + 1) * ACTION_WIDTH];
        m.set_action(s as u8, ShipAction::from_row(row));
    }
    m.step(cat);

    r.rewards[..k].copy_from_slice(m.rewards());
    r.rewards[k..].fill(0.0);
    r.collision_damage[..k].copy_from_slice(&m.collision_damage[..k]);
    r.collision_damage[k..].fill(0.0);
    write_hits(m, r);
    if cfg.record_events {
        m.events.encode_into(&mut slot.events);
    }

    let done = m.phase() == MatchPhase::Over;
    *r.done = done;
    *r.winner = m.winner();
    if done {
        slot.episode += 1;
        if let Some(next) = slot.next.take() {
            slot.roster = next;
        }
        slot.m = build_match(cat, cfg, &slot.roster, index, slot.episode);
    }
    write_post_step(cat, slot, r, done);
}

fn write_hits(m: &Match, r: &mut MatchRows<'_>) {
    let hits = m.hits();
    for (row, h) in r.hits.chunks_exact_mut(HIT_FIELDS).zip(hits) {
        row[0] = i32::from(h.shooter);
        row[1] = i32::from(h.target);
        row[2] = h.fire_tick as i32;
        row[3] = (h.damage * HIT_DAMAGE_SCALE).round() as i32;
        row[4] = i32::from(h.shield);
        row[5] = h.decision_tick as i32;
    }
    r.hits[hits.len() * HIT_FIELDS..].fill(0);
    *r.hit_count = hits.len() as i32;
}

/// Rows that describe the (possibly just rebuilt) match after the step. A rebuilt
/// match also rewrites its per-match buffers and clears its padding slots.
fn write_post_step(cat: &Catalogue, slot: &Slot, r: &mut MatchRows<'_>, rebuilt: bool) {
    let m = &slot.m;
    let k = m.ships.len();
    for s in 0..k {
        m.write_obs(cat, s as u8, &mut r.obs[s * OBS_DIM..(s + 1) * OBS_DIM]);
        let ship = &m.ships[s];
        r.act_mask[s] = actions::act_mask(ship, m.tick());
        r.alive[s] = ship.alive;
    }
    *r.tick = m.tick();
    *r.episode_count = slot.episode;
    if !rebuilt {
        return;
    }
    r.obs[k * OBS_DIM..].fill(0.0);
    r.act_mask[k..].fill(false);
    r.alive[k..].fill(false);
    for (s, ship) in m.ships.iter().enumerate() {
        let hull = cat.hull(ship.hull);
        r.thruster_mask[s * MAX_THRUSTERS..(s + 1) * MAX_THRUSTERS]
            .copy_from_slice(&actions::thruster_mask(hull));
        r.turret_mask[s * MAX_TURRETS..(s + 1) * MAX_TURRETS]
            .copy_from_slice(&actions::turret_mask(hull));
        r.fixed_turret[s * MAX_TURRETS..(s + 1) * MAX_TURRETS]
            .copy_from_slice(&actions::fixed_turret(hull));
        r.team[s] = ship.team as i8;
        r.hull_id[s] = ship.hull as i16;
    }
    r.thruster_mask[k * MAX_THRUSTERS..].fill(false);
    r.turret_mask[k * MAX_TURRETS..].fill(false);
    r.fixed_turret[k * MAX_TURRETS..].fill(false);
    r.team[k..].fill(PAD_SLOT);
    r.hull_id[k..].fill(i16::from(PAD_SLOT));
    *r.arena_radius = m.cfg.arena_radius;
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
        collision_damage: Vec<f32>,
        thruster_mask: Vec<bool>,
        turret_mask: Vec<bool>,
        fixed_turret: Vec<bool>,
        team: Vec<i8>,
        hull_id: Vec<i16>,
        arena_radius: Vec<f32>,
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
                collision_damage: vec![0.0; n * s],
                thruster_mask: vec![false; n * s * MAX_THRUSTERS],
                turret_mask: vec![false; n * s * MAX_TURRETS],
                fixed_turret: vec![false; n * s * MAX_TURRETS],
                team: vec![0; n * s],
                hull_id: vec![0; n * s],
                arena_radius: vec![0.0; n],
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
                collision_damage: &mut self.collision_damage,
                thruster_mask: &mut self.thruster_mask,
                turret_mask: &mut self.turret_mask,
                fixed_turret: &mut self.fixed_turret,
                team: &mut self.team,
                hull_id: &mut self.hull_id,
                arena_radius: &mut self.arena_radius,
            }
        }
    }

    fn duel(cat: &Catalogue) -> Roster {
        let f = cat.hull_id("fighter").unwrap();
        Roster {
            fleets: [vec![f], vec![f]],
            arena_radius: 450.0,
        }
    }

    fn batch(n_threads: usize, n_ships: usize) -> Batch {
        let cat = catalogue();
        let roster = duel(&cat);
        Batch::new(
            cat,
            BatchConfig {
                n_envs: 8,
                base_seed: 3,
                time_limit_ticks: 300,
                reaction_ticks: 2,
                roster,
                n_ships,
                n_threads,
                record_events: false,
            },
        )
        .unwrap()
    }

    fn scripted_steps(b: &mut Batch, o: &mut Owned, steps: usize) {
        for _ in 0..steps {
            let mut actions = std::mem::take(&mut o.actions);
            b.scripted_actions(None, &mut actions);
            o.actions = actions;
            b.step(o.bufs());
        }
    }

    fn run(n_threads: usize, steps: usize) -> (Vec<u64>, Vec<u32>) {
        let mut b = batch(n_threads, 2);
        let mut o = Owned::new(8, 2);
        b.reset(o.bufs());
        scripted_steps(&mut b, &mut o, steps);
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

    #[test]
    fn padding_slots_do_not_change_the_matches() {
        let mut padded = batch(2, 5);
        let mut o = Owned::new(8, 5);
        padded.reset(o.bufs());
        scripted_steps(&mut padded, &mut o, 400);
        let mut h = vec![0; 8];
        padded.state_hashes(&mut h);
        assert_eq!(h, run(2, 400).0);
        for i in 0..8 {
            assert_eq!(&o.team[i * 5..(i + 1) * 5], &[0, 1, -1, -1, -1]);
            assert!(!o.alive[i * 5 + 2..(i + 1) * 5].iter().any(|&a| a));
            assert!(
                o.obs[(i * 5 + 2) * OBS_DIM..(i + 1) * 5 * OBS_DIM]
                    .iter()
                    .all(|&x| x == 0.0)
            );
        }
    }

    #[test]
    fn queued_roster_applies_at_the_next_rebuild() {
        let mut b = batch(2, 4);
        let cat = catalogue();
        let (f, g) = (
            cat.hull_id("fighter").unwrap(),
            cat.hull_id("gunship").unwrap(),
        );
        let mut o = Owned::new(8, 4);
        b.reset(o.bufs());
        let roster = Roster {
            fleets: [vec![g], vec![f, f, f]],
            arena_radius: 500.0,
        };
        b.set_next_roster(3, roster.clone()).unwrap();
        assert_eq!(&o.team[12..16], &[0, 1, -1, -1], "current match untouched");
        b.reset(o.bufs());
        assert_eq!(&o.team[12..16], &[0, 1, 1, 1]);
        assert_eq!(o.hull_id[12], g as i16);
        assert_eq!(o.arena_radius[3], 500.0);
        assert_eq!(o.arena_radius[2], 450.0);
        // The roster sticks through auto-resets (time limit 300 ticks).
        scripted_steps(&mut b, &mut o, 301);
        assert!(o.episode_count[3] >= 1);
        assert_eq!(&o.team[12..16], &[0, 1, 1, 1]);
        assert_eq!(b.match_at(3).ships.len(), 4);
    }

    #[test]
    fn rosters_that_do_not_fit_are_rejected() {
        let mut b = batch(1, 2);
        let cat = catalogue();
        let f = cat.hull_id("fighter").unwrap();
        let big = Roster {
            fleets: [vec![f, f], vec![f]],
            arena_radius: 450.0,
        };
        assert!(matches!(
            b.set_next_roster(0, big),
            Err(BatchError::TooManyShips { count: 3, .. })
        ));
        let empty = Roster {
            fleets: [vec![], vec![f]],
            arena_radius: 450.0,
        };
        assert!(matches!(
            b.set_next_roster(0, empty),
            Err(BatchError::Setup(_))
        ));
        assert!(matches!(
            b.set_next_roster(9, duel(&cat)),
            Err(BatchError::EnvIndex { index: 9, .. })
        ));
    }
}
