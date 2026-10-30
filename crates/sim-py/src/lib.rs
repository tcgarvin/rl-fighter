//! `rlf_sim`: Python bindings for the sim (SIM_SPEC §10.1): the batched `VecEnv`
//! plus the layout constants Python slices obs and action rows with.

mod batch;
mod vec_env;

use pyo3::prelude::*;
use pyo3::types::PyDict;
use sim::actions::{ACTION_WIDTH, FIRE_OFFSET, POWER_OFFSET, SLEW_OFFSET, THROTTLE_OFFSET};
use sim::command::{COMMAND_TICKS, CommanderMode, MAX_SQUADS};
use sim::events;
use sim::mission::{EndReason, MissionKind};
use sim::obs::N_NEAR_SHIPS;
use sim::obs::{OBS_DIM, OBS_LAYOUT, OBS_SLOTS};
use sim::state::{MAX_HITS, MAX_REACTION_TICKS, MAX_SHIPS, MAX_THRUSTERS, MAX_TURRETS};

#[pymodule]
fn rlf_sim(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    m.add("SIM_VERSION", sim::SIM_VERSION)?;
    m.add("OBS_DIM", OBS_DIM)?;
    m.add("ACTION_WIDTH", ACTION_WIDTH)?;
    m.add("MAX_SHIPS", MAX_SHIPS)?;
    m.add("MAX_HITS", MAX_HITS)?;
    m.add("HIT_FIELDS", batch::HIT_FIELDS)?;
    m.add("HIT_DAMAGE_SCALE", batch::HIT_DAMAGE_SCALE)?;
    m.add("MAX_REACTION_TICKS", MAX_REACTION_TICKS)?;
    // v4.
    m.add("PILOT_COMPAT_VERSIONS", sim::PILOT_COMPAT_VERSIONS.to_vec())?;
    // v5: sim version -> the obs width a pilot of that version consumes (obs[..., :w]).
    let pilot_obs_dims = PyDict::new(py);
    for &(version, width) in sim::PILOT_OBS_DIMS {
        pilot_obs_dims.set_item(version, width)?;
    }
    m.add("PILOT_OBS_DIMS", pilot_obs_dims)?;
    m.add("OBS_DIM_V4", sim::obs::OBS_DIM_V4)?;
    m.add("MAX_TRAIN_SHIPS", sim::setup::MAX_TRAIN_SHIPS)?;
    m.add(
        "COMMANDER_MODES",
        [
            CommanderMode::Scripted,
            CommanderMode::External,
            CommanderMode::Random,
        ]
        .map(CommanderMode::name)
        .to_vec(),
    )?;
    m.add("N_NEAR_SHIPS", N_NEAR_SHIPS)?;
    m.add("COMMAND_TICKS", COMMAND_TICKS)?;
    m.add("MAX_SQUADS", MAX_SQUADS)?;
    m.add(
        "MISSIONS",
        [
            MissionKind::Deathmatch,
            MissionKind::CarrierBattle,
            MissionKind::ConvoyEscort,
        ]
        .map(MissionKind::name)
        .to_vec(),
    )?;
    // Indexed by the `end_reason` buffer's codes.
    m.add(
        "END_REASONS",
        [
            EndReason::NotOver,
            EndReason::Eliminated,
            EndReason::TimeLimit,
            EndReason::CarrierDestroyed,
            EndReason::ConvoyThrough,
            EndReason::ConvoyDestroyed,
        ]
        .map(EndReason::name)
        .to_vec(),
    )?;
    let event_kinds = PyDict::new(py);
    for (name, code) in [
        ("fire", events::KIND_FIRE),
        ("beam", events::KIND_BEAM),
        ("hit", events::KIND_HIT),
        ("shield_hit", events::KIND_SHIELD_HIT),
        ("burst", events::KIND_BURST),
        ("death", events::KIND_DEATH),
        ("arrival", events::KIND_ARRIVAL),
        ("collision", events::KIND_COLLISION),
        ("launch", events::KIND_LAUNCH),
        ("order", events::KIND_ORDER),
        ("jump_charge", events::KIND_JUMP_CHARGE),
        ("jump_out", events::KIND_JUMP_OUT),
        ("match_end", events::KIND_MATCH_END),
    ] {
        event_kinds.set_item(name, code)?;
    }
    m.add("EVENT_KINDS", event_kinds)?;

    // name -> (offset, width), in layout order (dicts keep insertion order).
    let obs_layout = PyDict::new(py);
    for &(name, off, width) in OBS_LAYOUT {
        obs_layout.set_item(name, (off, width))?;
    }
    m.add("OBS_LAYOUT", obs_layout)?;

    // name -> records per block, in layout order.
    let obs_slots = PyDict::new(py);
    for &(name, n) in OBS_SLOTS {
        obs_slots.set_item(name, n)?;
    }
    m.add("OBS_SLOTS", obs_slots)?;

    let action_layout = PyDict::new(py);
    action_layout.set_item("throttle", (THROTTLE_OFFSET, MAX_THRUSTERS))?;
    action_layout.set_item("slew", (SLEW_OFFSET, MAX_TURRETS))?;
    action_layout.set_item("fire", (FIRE_OFFSET, MAX_TURRETS))?;
    action_layout.set_item("power", (POWER_OFFSET, 1))?;
    m.add("ACTION_LAYOUT", action_layout)?;

    m.add_class::<vec_env::VecEnv>()?;
    m.add_function(wrap_pyfunction!(arena_radius_for, m)?)?;
    m.add_function(wrap_pyfunction!(arena_radius_for_mission, m)?)?;
    m.add_function(wrap_pyfunction!(mission_time_limit_s, m)?)?;
    m.add_function(wrap_pyfunction!(pilot_compatible, m)?)?;
    m.add_function(wrap_pyfunction!(mission_rosters, m)?)?;
    Ok(())
}

/// Arena radius in metres for a match of `n_ships` ships in total (both teams):
/// `sim::setup::arena_radius_for`, the rule the live page uses too (450 m for
/// every fleet size today).
#[pyfunction]
fn arena_radius_for(n_ships: usize) -> f32 {
    sim::setup::arena_radius_for(n_ships)
}

fn mission_kind(name: &str) -> PyResult<MissionKind> {
    MissionKind::from_name(name).ok_or_else(|| {
        pyo3::exceptions::PyValueError::new_err(format!(
            "unknown mission {name:?} (deathmatch, carrier_battle, convoy_escort)"
        ))
    })
}

/// v4: arena radius for mission `mission` with `n_ships` ships
/// (`sim::mission::arena_radius_for_mission`, the one per-mission rule).
#[pyfunction]
fn arena_radius_for_mission(mission: &str, n_ships: usize) -> PyResult<f32> {
    Ok(sim::mission::arena_radius_for_mission(
        mission_kind(mission)?,
        n_ships,
    ))
}

/// v4: the default time limit of mission `mission`, seconds.
#[pyfunction]
fn mission_time_limit_s(mission: &str) -> PyResult<f32> {
    Ok(mission_kind(mission)?.default_time_limit_ticks() as f32 / sim::TICK_HZ)
}

/// v4: whether a pilot trained under sim version `version` flies in this build
/// (`version in PILOT_COMPAT_VERSIONS`).
#[pyfunction]
fn pilot_compatible(version: u32) -> bool {
    sim::pilot_compatible(version)
}

/// WP-S2: the default rosters of mission `mission` (`sim::mission::default_rosters`),
/// a list of `{"name", "mission", "fleets": [[hull, ...], [hull, ...]]}` dicts in slot
/// order; empty for deathmatch (its rosters are budget drafts).
#[pyfunction]
fn mission_rosters<'py>(py: Python<'py>, mission: &str) -> PyResult<Bound<'py, PyAny>> {
    let text = sim::spec::to_json(&sim::spec::mission_rosters(mission_kind(mission)?));
    py.import("json")?.call_method1("loads", (text,))
}
