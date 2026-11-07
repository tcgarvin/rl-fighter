//! `rlf_sim`: Python bindings for the sim (SIM_SPEC §10.1): the batched `VecEnv`
//! plus the layout constants Python slices obs and action rows with.

mod batch;
mod vec_env;

use pyo3::prelude::*;
use pyo3::types::PyDict;
use sim::actions::{ACTION_WIDTH, FIRE_OFFSET, POWER_OFFSET, SLEW_OFFSET, THROTTLE_OFFSET};
use sim::command::{COMMAND_TICKS, CommanderMode, LEARNED_COMMAND_TICKS, MAX_SQUADS};
use sim::events;
use sim::mission::{EndReason, MissionKind};
use sim::obs::{N_NEAR_SHIPS, N_ORDER_SHIPS, SHIP_EXTRA_W};
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
    // v6.
    m.add("OBS_DIM_V5", sim::obs::OBS_DIM_V5)?;
    m.add("SHIP_EXTRA_W", SHIP_EXTRA_W)?;
    m.add("N_ORDER_SHIPS", N_ORDER_SHIPS)?;
    // Order kinds in the obs one-hot's order (kind codes 1, 2, 3; 0 is none).
    m.add("ORDER_KINDS", vec!["attack", "defend", "goto"])?;
    m.add("HULL_CLASSES", sim::order::HULL_CLASSES.to_vec())?;
    m.add("MAX_TRAIN_SHIPS", sim::setup::MAX_TRAIN_SHIPS)?;
    m.add(
        "COMMANDER_MODES",
        CommanderMode::ALL.map(CommanderMode::name).to_vec(),
    )?;
    m.add("N_NEAR_SHIPS", N_NEAR_SHIPS)?;
    m.add("COMMAND_TICKS", COMMAND_TICKS)?;
    m.add("LEARNED_COMMAND_TICKS", LEARNED_COMMAND_TICKS)?;
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

    m.add("ORDER_SHAPING_GAMMA", sim::reward::ORDER_SHAPING_GAMMA)?;
    m.add_class::<vec_env::VecEnv>()?;
    m.add_function(wrap_pyfunction!(arena_radius_for, m)?)?;
    m.add_function(wrap_pyfunction!(arena_radius_for_mission, m)?)?;
    m.add_function(wrap_pyfunction!(mission_time_limit_s, m)?)?;
    m.add_function(wrap_pyfunction!(pilot_compatible, m)?)?;
    m.add_function(wrap_pyfunction!(mission_rosters, m)?)?;
    m.add_function(wrap_pyfunction!(commander_io, m)?)?;
    Ok(())
}

/// The learned commander's interface constants (`sim::commander_io`,
/// `docs/COMMANDER.md`), a new dict: `version`, the dims and scales, `lock_decisions`,
/// `goto_radius`, `vel_scale`, `point_radii`, `command_ticks` (the learned cadence),
/// the action heads as `actions` (`name -> (offset, width, choices)`), the entity and
/// global blocks as `entity_layout` / `global_layout` (`name -> (offset, width)`), and
/// the browser's flat feature layout as `flat_layout` (`name -> (offset, width)`).
#[pyfunction]
fn commander_io<'py>(py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
    use sim::commander_io as io;
    let d = PyDict::new(py);
    d.set_item("version", io::COMMANDER_IO_VERSION)?;
    d.set_item("entity_dim", io::ENTITY_DIM)?;
    d.set_item("global_dim", io::GLOBAL_DIM)?;
    d.set_item("action_dim", io::ACTION_DIM)?;
    d.set_item("n_entities", io::N_ENTITIES)?;
    d.set_item("n_points", io::N_POINTS)?;
    d.set_item("n_squads", MAX_SQUADS)?;
    d.set_item("n_launch_hulls", io::N_LAUNCH_HULLS)?;
    d.set_item("n_waypoint_choices", io::N_WAYPOINT_CHOICES)?;
    d.set_item("n_squad_choices", io::N_SQUAD_CHOICES)?;
    d.set_item("n_order_choices", io::N_ORDER_CHOICES)?;
    d.set_item("squad_globals", io::SQUAD_GLOBALS)?;
    d.set_item("lock_decisions", io::LOCK_DECISIONS)?;
    d.set_item("goto_radius", io::GOTO_RADIUS)?;
    d.set_item("vel_scale", io::VEL_SCALE)?;
    d.set_item("point_radii", io::POINT_RADII.to_vec())?;
    d.set_item("point_bearings", io::POINT_BEARINGS)?;
    d.set_item("command_ticks", LEARNED_COMMAND_TICKS)?;
    d.set_item("flat_dim", io::FLAT_DIM)?;
    let actions = PyDict::new(py);
    for (name, off, width) in [
        ("launch", io::act::LAUNCH, io::N_LAUNCH_HULLS),
        ("waypoint", io::act::WAYPOINT, 1),
        ("squad", io::act::SQUAD, io::N_ENTITIES),
        ("order", io::act::ORDER, MAX_SQUADS),
        ("target", io::act::TARGET, MAX_SQUADS),
        ("ward", io::act::WARD, MAX_SQUADS),
        ("point", io::act::POINT, MAX_SQUADS),
    ] {
        actions.set_item(name, (off, width, io::head_choices(off)))?;
    }
    d.set_item("actions", actions)?;
    let entity = PyDict::new(py);
    for (name, off, width) in [
        ("valid", io::ent::VALID, 1),
        ("own", io::ent::OWN, 1),
        ("class", io::ent::CLASS, sim::order::N_HULL_CLASSES),
        ("pos", io::ent::POS, 2),
        ("vel", io::ent::VEL, 2),
        ("heading", io::ent::HEADING, 2),
        ("hull", io::ent::HULL, 1),
        ("shield", io::ent::SHIELD, 1),
        ("on_field", io::ent::ON_FIELD, 1),
        ("arriving", io::ent::ARRIVING, 1),
        ("charging", io::ent::CHARGING, 1),
        ("squad", io::ent::SQUAD, 1 + MAX_SQUADS),
        ("order", io::ent::ORDER, 4),
        ("target_of", io::ent::TARGET_OF, MAX_SQUADS),
        ("ward_of", io::ent::WARD_OF, MAX_SQUADS),
        ("threat", io::ent::THREAT, 1),
        ("dist_own", io::ent::DIST_OWN, 1),
        ("dist_enemy", io::ent::DIST_ENEMY, 1),
        ("ship_lock", io::ent::SHIP_LOCK, 1),
    ] {
        entity.set_item(name, (off, width))?;
    }
    d.set_item("entity_layout", entity)?;
    let globals = PyDict::new(py);
    for (name, off, width) in [
        ("role", io::glob::ROLE, 4),
        ("time_left", io::glob::TIME_LEFT, 1),
        ("tick", io::glob::TICK, 1),
        ("reserves", io::glob::RESERVES, io::N_LAUNCH_HULLS),
        ("bays_ready", io::glob::BAYS_READY, 1),
        ("bays", io::glob::BAYS, 1),
        ("carrier", io::glob::CARRIER, 1),
        ("enemy_carrier", io::glob::ENEMY_CARRIER, 1),
        ("convoy", io::glob::CONVOY, 5),
        ("squads", io::glob::SQUADS, MAX_SQUADS * io::SQUAD_GLOBALS),
        ("own_strike", io::glob::OWN_STRIKE, 1),
        ("enemy_strike", io::glob::ENEMY_STRIKE, 1),
        ("launch_age", io::glob::LAUNCH_AGE, 1),
    ] {
        globals.set_item(name, (off, width))?;
    }
    d.set_item("global_layout", globals)?;
    let flat = PyDict::new(py);
    for (name, off, width) in io::FLAT_LAYOUT {
        flat.set_item(name, (off, width))?;
    }
    d.set_item("flat_layout", flat)?;
    Ok(d)
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
