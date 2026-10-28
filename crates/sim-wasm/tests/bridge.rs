//! Native tests of the target-independent `WasmMatch` core: input validation, view
//! layouts, and agreement with the sim's golden duel trace.

use sim_wasm::bridge::{MatchCore, PROJECTILE_STRIDE, SHIP_STRIDE};

fn hulls() -> Vec<(String, String)> {
    [
        (
            "fighter",
            include_str!("../../../assets/hulls/fighter/hull.yaml"),
        ),
        (
            "gunship",
            include_str!("../../../assets/hulls/gunship/hull.yaml"),
        ),
        (
            "strafer",
            include_str!("../../../assets/hulls/strafer/hull.yaml"),
        ),
    ]
    .iter()
    .map(|(n, y)| (n.to_string(), y.to_string()))
    .collect()
}

const WEAPONS: &str = include_str!("../../../assets/weapons.yaml");
const DUEL: &str = r#"{"seed": 7, "fleets": [["fighter"], ["fighter"]]}"#;

fn duel() -> MatchCore {
    MatchCore::new(&hulls(), WEAPONS, DUEL).expect("duel setup")
}

/// Step with the scripted controller on both sides.
fn scripted_step(m: &mut MatchCore) {
    for ship in 0..2 {
        let row = m.scripted_action(ship).unwrap();
        m.set_action(ship, &row).unwrap();
    }
    m.step();
}

/// The golden `end` line of the sim's scripted 1v1 trace: `(tick, hash hex, winner)`.
fn golden_duel_end() -> (u32, String, i8) {
    let golden = include_str!("../../sim/tests/golden/duel_fighter_s7.txt");
    let end = golden
        .lines()
        .find(|l| l.starts_with("end "))
        .expect("golden end line");
    let f: Vec<&str> = end.split_whitespace().collect();
    (
        f[1].parse().unwrap(),
        f[2].to_string(),
        f[5].parse().unwrap(),
    )
}

#[test]
fn scripted_duel_matches_native_golden_trace() {
    let mut m = duel();
    while m.phase() == 0 {
        scripted_step(&mut m);
    }
    let (tick, hash, winner) = golden_duel_end();
    assert_eq!(m.tick(), tick);
    assert_eq!(format!("{:016x}", m.state_hash()), hash);
    assert_eq!(m.winner(), winner);
}

#[test]
fn views_have_documented_strides() {
    let mut m = duel();
    assert_eq!(m.ships_view().len(), 2 * SHIP_STRIDE);
    assert!(m.projectiles_view().is_empty());
    let mut saw_projectile = false;
    let mut saw_event = false;
    while m.phase() == 0 {
        scripted_step(&mut m);
        assert_eq!(m.projectiles_view().len() % PROJECTILE_STRIDE, 0);
        assert_eq!(m.events_view().len() % sim::events::EVENT_STRIDE, 0);
        saw_projectile |= !m.projectiles_view().is_empty();
        saw_event |= !m.events_view().is_empty();
    }
    assert!(saw_projectile && saw_event);
    // Ship 1 is team 1 (record slot 10), hull 0 = fighter (slot 11).
    assert_eq!(m.ships_view()[SHIP_STRIDE + 10], 1.0);
    assert_eq!(m.ships_view()[SHIP_STRIDE + 11], 0.0);
    assert_eq!(m.obs(0).unwrap().len(), sim::obs::OBS_DIM);
}

#[test]
fn new_match_starts_running_at_tick_zero() {
    let m = duel();
    assert_eq!(m.tick(), 0);
    assert_eq!(m.phase(), 0);
    assert_eq!(m.winner(), -2);
}

#[test]
fn unknown_hull_name_is_an_error() {
    let cfg = r#"{"seed":1,"fleets":[["fighter"],["bomber"]]}"#;
    let err = MatchCore::new(&hulls(), WEAPONS, cfg).err().unwrap();
    assert!(err.contains("bomber"), "{err}");
}

#[test]
fn malformed_config_and_yaml_are_errors() {
    let bad_json = MatchCore::new(&hulls(), WEAPONS, "{").err().unwrap();
    assert!(bad_json.starts_with("config_json"), "{bad_json}");
    let unknown_field = r#"{"seed":1,"fleets":[["fighter"],["fighter"]],"speed":2}"#;
    assert!(MatchCore::new(&hulls(), WEAPONS, unknown_field).is_err());
    let empty_fleet = r#"{"seed":1,"fleets":[[],["fighter"]]}"#;
    assert!(MatchCore::new(&hulls(), WEAPONS, empty_fleet).is_err());
    assert!(MatchCore::new(&hulls(), "not: [weapons", DUEL).is_err());
}

#[test]
fn bad_ship_index_or_row_length_is_an_error() {
    let mut m = duel();
    assert!(m.set_action(0, &[0; 20]).is_err());
    assert!(m.set_action(2, &[0; 21]).is_err());
    assert!(m.set_action(1, &[0; 21]).is_ok());
    assert!(m.scripted_action(9).is_err());
    assert!(m.obs(2).is_err());
}
