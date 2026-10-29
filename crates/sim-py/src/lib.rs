//! `rlf_sim`: Python bindings for the sim (SIM_SPEC §10.1): the batched `VecEnv`
//! plus the layout constants Python slices obs and action rows with.

mod batch;
mod vec_env;

use pyo3::prelude::*;
use pyo3::types::PyDict;
use sim::actions::{ACTION_WIDTH, FIRE_OFFSET, POWER_OFFSET, SLEW_OFFSET, THROTTLE_OFFSET};
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
    Ok(())
}

/// Arena radius in metres for a match of `n_ships` ships in total (both teams):
/// 450 m for a duel plus 25 m per extra ship (`sim::setup::arena_radius_for`, the
/// rule the live page uses too).
#[pyfunction]
fn arena_radius_for(n_ships: usize) -> f32 {
    sim::setup::arena_radius_for(n_ships)
}
