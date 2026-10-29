//! RL Fighter match simulation: deterministic, fixed-step, `f32` everywhere.
//!
//! `docs/SIM_SPEC.md` is the contract. Every module is declared here up front so
//! work packages can land in parallel without touching this file.

pub mod actions;
pub mod arena;
pub mod arrival;
pub mod collision;
pub mod damage;
pub mod data;
pub mod events;
pub mod hash;
pub mod math;
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
pub const SIM_VERSION: u32 = 3;

/// Fixed simulation step, 30 Hz.
pub const DT: f32 = 1.0 / 30.0;

/// Ticks per simulated second; YAML durations convert with `(s * TICK_HZ).round()`.
pub const TICK_HZ: f32 = 30.0;
