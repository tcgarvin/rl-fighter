//! RL Fighter match simulation: deterministic, fixed-step, `f32` everywhere.
//!
//! `docs/SIM_SPEC.md` is the contract. Every module is declared here up front so
//! work packages can land in parallel without touching this file.

pub mod actions;
pub mod arena;
pub mod arrival;
pub mod collision;
pub mod command;
pub mod damage;
pub mod data;
pub mod events;
pub mod hash;
pub mod math;
pub mod mission;
pub mod obs;
pub mod physics;
pub mod power;
pub mod projectiles;
pub mod reward;
pub mod rng;
pub mod scripted;
pub mod setup;
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
pub const SIM_VERSION: u32 = 4;

/// Sim versions whose trained pilots fly correctly in this build: their obs and
/// action layouts, and deathmatch trajectories with up to 8 ships, are identical
/// (SIM_SPEC §0.2; proven by `tests/determinism.rs::v3_compat_*`). The bundle and the
/// champion registry accept a pilot whose `sim_version` is in this list.
pub const PILOT_COMPAT_VERSIONS: &[u32] = &[3, 4];

/// Whether a pilot trained under sim `version` flies in this build.
pub fn pilot_compatible(version: u32) -> bool {
    PILOT_COMPAT_VERSIONS.contains(&version)
}

/// Fixed simulation step, 30 Hz.
pub const DT: f32 = 1.0 / 30.0;

/// Ticks per simulated second; YAML durations convert with `(s * TICK_HZ).round()`.
pub const TICK_HZ: f32 = 30.0;
