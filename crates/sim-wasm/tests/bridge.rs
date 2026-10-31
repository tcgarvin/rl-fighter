//! Native tests of the target-independent `WasmMatch` core: input validation, view
//! layouts, and agreement with the sim's golden duel trace.

use sim_wasm::bridge::{
    CONVOY_STRIDE, MatchCore, PROJECTILE_STRIDE, SHIP_EXT_STRIDE, SHIP_STRIDE, SQUAD_STRIDE,
    TEAM_STRIDE,
};

/// Every shipped hull, as the bundle's catalogue hands them over (v4: carrier and
/// freighter too, so hull ids match the native golden traces).
fn hulls() -> Vec<(String, String)> {
    [
        (
            "carrier",
            include_str!("../../../assets/hulls/carrier/hull.yaml"),
        ),
        (
            "freighter",
            include_str!("../../../assets/hulls/freighter/hull.yaml"),
        ),
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
    // Ship 1 is team 1 (record slot 10), hull 1 = fighter (slot 11; v4 ids).
    assert_eq!(m.ships_view()[SHIP_STRIDE + 10], 1.0);
    assert_eq!(m.ships_view()[SHIP_STRIDE + 11], 1.0);
    assert_eq!(m.ship_ext_view().len(), 2 * SHIP_EXT_STRIDE);
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

#[test]
fn head_valid_masks_absent_slots_and_fixed_guns() {
    let m = duel();
    // Fighter: 5 thrusters, one fixed nose gun.
    let mut want = vec![1u8; 5];
    want.extend([0; 3]); // absent thrusters
    want.extend([0; 6]); // slew: the only turret is fixed
    want.push(1); // fire: nose gun
    want.extend([0; 5]);
    want.push(1); // power
    assert_eq!(m.head_valid(0).unwrap(), want);
    assert_eq!(m.head_valid(1).unwrap(), want);
    assert!(m.head_valid(2).is_err());
}

const CARRIER_BATTLE: &str = r#"{"seed": 23, "time_limit_ticks": 9000, "mission": "carrier_battle",
    "fleets": [["carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter"],
               ["carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter"]]}"#;

const CONVOY: &str = r#"{"seed": 29, "time_limit_ticks": 9000,
    "mission": {"kind": "convoy_escort"},
    "fleets": [["freighter", "freighter", "freighter", "freighter", "fighter", "strafer", "fighter"],
               ["fighter", "fighter", "strafer", "gunship", "fighter", "strafer"]]}"#;

fn scripted_all(m: &mut MatchCore, n: u32) {
    for ship in 0..n {
        let row = m.scripted_action(ship).unwrap();
        m.set_action(ship, &row).unwrap();
    }
    m.step();
}

/// The `end` and `reason` lines of a native mission golden trace.
fn golden_mission_end(golden: &str) -> (u32, String, i8, String) {
    let end: Vec<&str> = golden
        .lines()
        .find(|l| l.starts_with("end "))
        .unwrap()
        .split_whitespace()
        .collect();
    let reason = golden
        .lines()
        .find(|l| l.starts_with("reason "))
        .unwrap()
        .split_whitespace()
        .nth(1)
        .unwrap()
        .to_string();
    (
        end[1].parse().unwrap(),
        end[2].to_string(),
        end[5].parse().unwrap(),
        reason,
    )
}

#[test]
fn missions_through_the_bridge_match_the_native_goldens() {
    for (cfg, golden, n, kind) in [
        (
            CARRIER_BATTLE,
            include_str!("../../sim/tests/golden/carrier_battle_s23.txt"),
            14,
            1,
        ),
        (
            CONVOY,
            include_str!("../../sim/tests/golden/convoy_escort_s29.txt"),
            13,
            2,
        ),
    ] {
        let mut m = MatchCore::new(&hulls(), WEAPONS, cfg).expect("setup");
        assert_eq!(m.mission_kind(), kind);
        let mut launched = false;
        while m.phase() == 0 {
            scripted_all(&mut m, n);
            assert_eq!(m.ship_ext_view().len(), n as usize * SHIP_EXT_STRIDE);
            launched |= m
                .events_view()
                .chunks_exact(sim::events::EVENT_STRIDE)
                .any(|e| e[0] == f32::from(sim::events::KIND_LAUNCH));
        }
        let (tick, hash, winner, reason) = golden_mission_end(golden);
        assert_eq!(m.tick(), tick);
        assert_eq!(format!("{:016x}", m.state_hash()), hash);
        assert_eq!(m.winner(), winner);
        let names = [
            "not_over",
            "eliminated",
            "time_limit",
            "carrier_destroyed",
            "convoy_through",
            "convoy_destroyed",
        ];
        assert_eq!(names[usize::from(m.end_reason())], reason);
        assert_eq!(launched, kind == 1, "launches only in the carrier battle");
        assert!(m.mission_state_json().contains("\"end_reason\""));
    }
}

#[test]
fn mission_views_have_documented_strides() {
    let m = MatchCore::new(&hulls(), WEAPONS, CARRIER_BATTLE).unwrap();
    assert_eq!(
        m.squads().len(),
        2 * sim::command::MAX_SQUADS * SQUAD_STRIDE
    );
    let team = m.team_state(0).unwrap();
    assert_eq!(team.len(), TEAM_STRIDE);
    assert_eq!(team[0], 0.0, "team 0's carrier is slot 0");
    assert_eq!((team[2], team[5], team[6]), (1000.0, 4.0, 2.0));
    assert!(m.team_state(2).is_err());
    assert!(m.convoy().is_empty());
    assert_eq!(m.hangar_hulls(1).unwrap().len(), 4);
    // Carrier: role 1, waypoint set at setup.
    let ext = m.ship_ext_view();
    assert_eq!((ext[0], ext[5]), (1.0, 1.0));
    // Slot 3 is docked in carrier 0.
    let docked = &ext[3 * SHIP_EXT_STRIDE..4 * SHIP_EXT_STRIDE];
    assert_eq!((docked[1], docked[2]), (1.0, 0.0));
    let c = MatchCore::new(&hulls(), WEAPONS, CONVOY).unwrap();
    let convoy = c.convoy();
    assert_eq!(convoy.len(), CONVOY_STRIDE);
    assert_eq!(convoy[0], 4.0);
    assert_eq!(c.ship_ext_view()[0], 2.0, "freighters are transports");
}

#[test]
fn external_commands_round_trip_as_json() {
    let cfg = CARRIER_BATTLE.replace(
        r#""mission": "carrier_battle","#,
        r#""mission": "carrier_battle", "commanders": ["external", "external"],"#,
    );
    let mut m = MatchCore::new(&hulls(), WEAPONS, &cfg).unwrap();
    while !m.command_due() {
        m.step();
    }
    m.submit_commands(
        0,
        r#"[{"kind": "launch", "hull": "fighter", "bay": 1},
            {"kind": "squad", "squad": 0, "members": [1, 2],
             "order": {"kind": "goto", "point": [0, 0], "radius": 50}}]"#,
    )
    .unwrap();
    assert!(
        m.submit_commands(0, r#"{"kind": "launch", "hull": "bomber"}"#)
            .is_err()
    );
    assert!(m.submit_commands(0, "[").is_err());
    m.step();
    let results = m.command_results_json(0).unwrap();
    assert!(results.contains("\"launched\""), "{results}");
    assert_eq!(m.command_results_json(1).unwrap(), "[]");
    let squads = m.squads();
    assert_eq!(squads[4], 3.0, "team 0 squad 0 goes to a point");
    assert_eq!(squads[2], 2.0, "two members");
    let obs = m.commander_obs_json(0).unwrap();
    assert!(obs.contains("\"reserves\""), "{obs}");
}

#[test]
fn bad_mission_configs_are_errors() {
    let wrong = r#"{"seed": 1, "mission": "carrier_battle", "fleets": [["fighter"], ["fighter"]]}"#;
    assert!(MatchCore::new(&hulls(), WEAPONS, wrong).is_err());
    let unknown = r#"{"seed": 1, "mission": "duel", "fleets": [["fighter"], ["fighter"]]}"#;
    assert!(MatchCore::new(&hulls(), WEAPONS, unknown).is_err());
    let field = r#"{"seed": 1, "mission": {"kind": "deathmatch", "x": 1}, "fleets": [["fighter"], ["fighter"]]}"#;
    assert!(MatchCore::new(&hulls(), WEAPONS, field).is_err());
    let cmd =
        r#"{"seed": 1, "commanders": ["robot", "scripted"], "fleets": [["fighter"], ["fighter"]]}"#;
    assert!(MatchCore::new(&hulls(), WEAPONS, cmd).is_err());
}
