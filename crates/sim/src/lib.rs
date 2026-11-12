//! RL Fighter match simulation: deterministic, fixed-step, `f32` everywhere.
//!
//! `docs/SIM_SPEC.md` is the contract. Every module is declared here up front so
//! work packages can land in parallel without touching this file.

pub mod actions;
pub mod arena;
pub mod arrival;
pub mod collision;
pub mod command;
pub mod commander_io;
pub mod damage;
pub mod data;
pub mod events;
pub mod hash;
pub mod math;
pub mod mission;
pub mod obs;
pub mod order;
pub mod physics;
pub mod power;
pub mod projectiles;
pub mod reward;
pub mod rng;
pub mod scripted;
pub mod setup;
pub mod spec;
pub mod state;
pub mod step;
pub mod turrets;
pub mod weapons;

pub use hash::StateHasher;
pub use math::Vec2;
pub use rng::Pcg32;

/// Bumped whenever a golden determinism trace changes (SIM_SPEC §12).
/// v4 (M3 stage A): missions, carriers and hangars, convoy jumps, the commander layer,
/// `MAX_SHIPS` 20. Pilot obs and actions are unchanged from v3.
/// v5 (M3 stage B): the order block appended to the obs (`OBS_DIM` 403), order
/// instances and the order reward, the random commander. The first 385 obs floats
/// and every v4 trajectory are unchanged (SIM_SPEC §0.3).
/// v6 (M3 stage B3): orders redesigned (attack, defend, go-to), the defend and go-to
/// rewards, the threat blocks appended to the obs (`OBS_DIM` 583), hidden-order mode.
/// The first 403 obs floats and every deathmatch trajectory under the scripted
/// commander are unchanged (SIM_SPEC §0.4).
/// v7: crash damage by velocity change: each ship in a collision also takes hull damage,
/// past any shield, for its own velocity change above `collision::CRASH_DV_FREE`, so a
/// light ship ramming a heavy one pays far more, and scripted strike craft avoid
/// crashes with any ship. Obs and actions are unchanged (SIM_SPEC §0.5).
/// v8: a go-to order may carry a deadline tick: arriving by it pays the timed bonus,
/// missing it pays a penalty once and ends the order for that ship; an order instance
/// that starts with the ship already inside the radius is complete with no bonus; the
/// 4-float `order_time` block is appended to the obs (`OBS_DIM` 587). No commander in
/// the sim issues a deadline, so the first 583 obs floats and every trajectory are
/// v7's (SIM_SPEC §0.6).
pub const SIM_VERSION: u32 = 8;

/// Sim versions whose trained pilots fly correctly in this build: their obs prefix
/// and action layout are identical (SIM_SPEC §0.2–§0.5). Through v6 deathmatch
/// trajectories were identical too; v7 changes crashes and the script, and only the
/// fighter duel still replays bit for bit (`tests/determinism.rs::v*_compat_duel_*`). The bundle and the champion registry accept a pilot whose
/// `sim_version` is in this list; it reads the first [`pilot_obs_dim`] floats of the
/// obs.
pub const PILOT_COMPAT_VERSIONS: &[u32] = &[3, 4, 5, 6, 7, 8];

/// `(sim version, obs width)` for every pilot-compatible version: a pilot of that
/// version consumes `obs[..width]` (v3 and v4 pilots the 385-float prefix, v5 pilots
/// the 403-float one, v6 and v7 pilots the 583-float one).
pub const PILOT_OBS_DIMS: &[(u32, usize)] = &[
    (3, obs::OBS_DIM_V4),
    (4, obs::OBS_DIM_V4),
    (5, obs::OBS_DIM_V5),
    (6, obs::OBS_DIM_V7),
    (7, obs::OBS_DIM_V7),
    (8, obs::OBS_DIM),
];

/// Whether a pilot trained under sim `version` flies in this build.
pub fn pilot_compatible(version: u32) -> bool {
    PILOT_COMPAT_VERSIONS.contains(&version)
}

/// The obs width a pilot of sim `version` consumes, `None` if it does not fly here.
pub fn pilot_obs_dim(version: u32) -> Option<usize> {
    PILOT_OBS_DIMS
        .iter()
        .find(|&&(v, _)| v == version)
        .map(|&(_, d)| d)
}

/// Fixed simulation step, 30 Hz.
pub const DT: f32 = 1.0 / 30.0;

/// Ticks per simulated second; YAML durations convert with `(s * TICK_HZ).round()`.
pub const TICK_HZ: f32 = 30.0;
