//! WP1 acceptance: loading, derived fields, and one failing fixture per §4.4 rule.
//!
//! Real assets are pulled in with `include_str!` so these tests also run under
//! wasm32-wasip1, which cannot see the host filesystem; only the `load_dir` tests
//! touch the disk.

use sim::data::{Catalogue, DataError, WeaponKind};
use sim::math::PI;

const WEAPONS: &str = include_str!("../../../assets/weapons.yaml");
const FIGHTER: &str = include_str!("../../../assets/hulls/fighter/hull.yaml");
const STRAFER: &str = include_str!("../../../assets/hulls/strafer/hull.yaml");
const GUNSHIP: &str = include_str!("../../../assets/hulls/gunship/hull.yaml");

const DEG: f32 = PI / 180.0;

fn shipped() -> Catalogue {
    // Deliberately unsorted: from_yaml must sort by name.
    Catalogue::from_yaml(
        &[
            ("strafer", STRAFER),
            ("gunship", GUNSHIP),
            ("fighter", FIGHTER),
        ],
        WEAPONS,
    )
    .expect("shipped assets load")
}

fn approx(a: f32, b: f32) -> bool {
    (a - b).abs() <= 1e-5 * b.abs().max(1.0)
}

/// Load one fixture hull (as directory `bad`) next to the shipped weapons and return
/// every error message.
fn hull_errors(text: &str) -> Vec<String> {
    let err = Catalogue::from_yaml(&[("bad", text)], WEAPONS).expect_err("fixture must fail");
    messages(&err)
}

fn weapon_errors(text: &str) -> Vec<String> {
    let err = Catalogue::from_yaml(&[], text).expect_err("fixture must fail");
    messages(&err)
}

fn messages(err: &DataError) -> Vec<String> {
    err.issues()
        .iter()
        .map(|e| match e {
            DataError::Invalid { msg, .. } | DataError::Parse { msg, .. } => msg.clone(),
            DataError::Multiple(_) => panic!("Multiple must not nest"),
        })
        .collect()
}

/// Every error comes from `rule`, and there are exactly `count` of them (so a
/// fixture checks that all its problems are collected, not just the first).
fn assert_rule(errors: &[String], rule: u32, count: usize) {
    let prefix = format!("rule {rule}:");
    assert!(
        errors.iter().all(|m| m.starts_with(&prefix)),
        "expected only {prefix} errors, got {errors:#?}"
    );
    assert_eq!(errors.len(), count, "{errors:#?}");
}

#[test]
fn shipped_hulls_sorted_by_name() {
    let cat = shipped();
    let names: Vec<&str> = cat.hulls.iter().map(|h| h.name.as_str()).collect();
    assert_eq!(names, ["fighter", "gunship", "strafer"]);
    assert_eq!(cat.hull_id("fighter"), Some(0));
    assert_eq!(cat.hull_id("gunship"), Some(1));
    assert_eq!(cat.hull_id("strafer"), Some(2));
    assert_eq!(cat.hull_id("bomber"), None);
}

#[test]
fn weapons_in_file_order_with_resolved_units() {
    let cat = shipped();
    let names: Vec<&str> = cat.weapons.iter().map(|w| w.name.as_str()).collect();
    assert_eq!(names, ["gauss", "laser", "flak", "torpedo"]);

    let gauss = &cat.weapons[0];
    assert_eq!(gauss.kind, WeaponKind::Bullet);
    assert!(approx(gauss.spread, 0.6 * DEG));
    assert_eq!(gauss.life_ticks, 38); // 300 / 240 * 30 = 37.5 -> 38
    assert_eq!(gauss.life_factor, 1.0);
    assert_eq!(gauss.burst_radius, 0.0);

    let laser = &cat.weapons[1];
    assert_eq!(laser.kind, WeaponKind::Beam);
    assert_eq!(laser.life_ticks, 0);

    let flak = &cat.weapons[2];
    assert_eq!(flak.kind, WeaponKind::Flak);
    assert_eq!(flak.life_ticks, 38); // 230 / 180 * 30 = 38.33
    assert_eq!(flak.burst_radius, 14.0);
    assert_eq!(flak.fuse_jitter, 0.4);

    let torpedo = &cat.weapons[3];
    assert_eq!(torpedo.kind, WeaponKind::Torpedo);
    assert_eq!(torpedo.life_ticks, 140); // 340 / 95 * 30 * 1.3 = 139.58
    assert!(approx(torpedo.turn_rate, 40.0 * DEG));
    assert!(approx(torpedo.lock_cone, 30.0 * DEG));
}

#[test]
fn derived_fields() {
    let cat = shipped();
    let fighter = cat.hull(cat.hull_id("fighter").unwrap());
    assert!(approx(fighter.bound_radius, 4.8)); // |-2.2| + 2.6
    assert!(approx(fighter.shield_radius, fighter.bound_radius));
    assert!(!fighter.has_shield());
    assert_eq!(fighter.n_power_systems, 2);
    assert!(approx(fighter.arrival_speed, 84.0));

    let strafer = cat.hull(cat.hull_id("strafer").unwrap());
    assert!(approx(strafer.bound_radius, 6.0)); // 3.6 + 2.4
    assert!(approx(strafer.shield_radius, 7.5));
    assert_eq!(strafer.n_power_systems, 3);
    assert!(approx(strafer.arrival_speed, 70.0));

    let gunship = cat.hull(cat.hull_id("gunship").unwrap());
    assert!(approx(gunship.bound_radius, 8.3)); // 4.5 + 3.8
    assert!(approx(gunship.shield_radius, 11.0));
    assert_eq!(gunship.n_power_systems, 3);
    assert!(approx(gunship.arrival_speed, 33.6));
}

#[test]
fn hull_values_ported_from_prototype() {
    let cat = shipped();
    let gunship = cat.hull(cat.hull_id("gunship").unwrap());
    assert_eq!(gunship.hp, 320.0);
    assert_eq!(gunship.inertia, 2200.0);
    let shield = gunship.shield.unwrap();
    assert_eq!(
        (
            shield.hp,
            shield.regen_rate,
            shield.regen_delay,
            shield.radius
        ),
        (140.0, 12.0, 4.0, 11.0)
    );
    assert_eq!(gunship.thrusters.len(), 6);
    assert_eq!(gunship.thrusters[0].max_force, 1700.0);

    let port = &gunship.turrets[1];
    assert_eq!(port.id, "turret.port");
    assert!(approx(port.rest, 90.0 * DEG));
    assert!(approx(port.arc, 220.0 * DEG));
    assert!(approx(port.slew_rate, 90.0 * DEG));
    assert_eq!(cat.weapon(port.weapon).name, "gauss");
    assert_eq!(cat.weapon(gunship.turrets[0].weapon).name, "flak");

    let strafer = cat.hull(cat.hull_id("strafer").unwrap());
    assert_eq!(cat.weapon(strafer.turrets[0].weapon).name, "laser");
    assert_eq!(strafer.thrusters[1].id, "thruster.lateral.fl");
    assert_eq!(strafer.thrusters[1].max_force, 420.0);
}

#[test]
fn directions_are_renormalised() {
    let text = FIGHTER.replace(
        "dir: [1, 0], max_force: 900",
        "dir: [1.005, 0], max_force: 900",
    );
    let cat = Catalogue::from_yaml(&[("fighter", &text)], WEAPONS).unwrap();
    assert_eq!(cat.hulls[0].thrusters[0].dir.x, 1.0);
}

#[test]
fn static_hull_needs_no_thrusters() {
    let cat = Catalogue::from_yaml(&[("bad", include_str!("fixtures/static_ok.yaml"))], WEAPONS)
        .expect("static hull loads");
    assert!(cat.hulls[0].is_static);
    assert_eq!(cat.hulls[0].speed_cap, 0.0);
}

#[test]
fn rule1_name() {
    let errors = hull_errors(include_str!("fixtures/rule1_name.yaml"));
    assert_rule(&errors, 1, 2);
}

#[test]
fn rule2_scalars() {
    let errors = hull_errors(include_str!("fixtures/rule2_scalars.yaml"));
    assert_rule(&errors, 2, 3);
}

#[test]
fn rule3_collision() {
    let errors = hull_errors(include_str!("fixtures/rule3_collision.yaml"));
    assert_rule(&errors, 3, 2);
    let errors = hull_errors(include_str!("fixtures/rule3_no_collision.yaml"));
    assert_rule(&errors, 3, 1);
}

#[test]
fn rule4_mounts() {
    // duplicate id, short dir, zero force, long bay dir
    let errors = hull_errors(include_str!("fixtures/rule4_mounts.yaml"));
    assert_rule(&errors, 4, 4);
    let errors = hull_errors(include_str!("fixtures/rule4_counts.yaml"));
    assert_rule(&errors, 4, 2);
}

#[test]
fn rule5_turrets() {
    let errors = hull_errors(include_str!("fixtures/rule5_turrets.yaml"));
    assert_rule(&errors, 5, 3);
}

#[test]
fn rule6_shield() {
    let errors = hull_errors(include_str!("fixtures/rule6_shield.yaml"));
    assert_rule(&errors, 6, 4);
}

#[test]
fn rule7_authority() {
    let errors = hull_errors(include_str!("fixtures/rule7_one_way_torque.yaml"));
    assert_rule(&errors, 7, 1);
    assert!(errors[0].contains("counter-clockwise"), "{errors:?}");
    let errors = hull_errors(include_str!("fixtures/rule7_no_forward.yaml"));
    assert_rule(&errors, 7, 1);
    assert!(errors[0].contains("+x"), "{errors:?}");
    let errors = hull_errors(include_str!("fixtures/rule7_no_thrusters.yaml"));
    assert_rule(&errors, 7, 1);
}

#[test]
fn rule8_weapons() {
    // gauss: damage, speed; flak: interval, range
    let errors = weapon_errors(include_str!("fixtures/rule8_weapons.yaml"));
    assert_eq!(errors.len(), 4, "{errors:#?}");
    assert!(errors.iter().all(|m| m.contains("rule 8:")), "{errors:#?}");
}

#[test]
fn rule9_weapons() {
    let errors = weapon_errors(include_str!("fixtures/rule9_weapons.yaml"));
    assert_eq!(errors.len(), 2, "{errors:#?}");
    assert!(errors[0].starts_with("gauss: rule 9:"), "{errors:#?}");
    assert!(errors[1].starts_with("torpedo: rule 9:"), "{errors:#?}");
}

#[test]
fn unknown_field_is_a_parse_error() {
    let err = Catalogue::from_yaml(
        &[("bad", include_str!("fixtures/parse_unknown_field.yaml"))],
        WEAPONS,
    )
    .unwrap_err();
    match &err {
        DataError::Parse { file, msg } => {
            assert_eq!(file, "hulls/bad/hull.yaml");
            assert!(msg.contains("wingspan"), "{msg}");
        }
        other => panic!("expected Parse, got {other:?}"),
    }
}

#[test]
fn errors_from_every_file_are_collected() {
    let err = Catalogue::from_yaml(
        &[
            ("bad", include_str!("fixtures/rule6_shield.yaml")),
            ("fighter", FIGHTER),
            ("other", include_str!("fixtures/parse_unknown_field.yaml")),
        ],
        include_str!("fixtures/rule9_weapons.yaml"),
    )
    .unwrap_err();
    let issues = err.issues();
    // 2 weapon errors + 4 shield errors + 1 parse error; fighter's laser-free weapons
    // file is fine for it (fighter uses gauss).
    assert_eq!(issues.len(), 7, "{err}");
    assert!(matches!(err, DataError::Multiple(_)));
    let text = err.to_string();
    assert!(text.starts_with("7 data errors:"), "{text}");
    assert!(text.contains("bad: rule 6:"), "{text}");
}

#[test]
fn duplicate_hull_names_rejected() {
    let err =
        Catalogue::from_yaml(&[("fighter", FIGHTER), ("fighter", FIGHTER)], WEAPONS).unwrap_err();
    assert!(err.to_string().contains("defined twice"), "{err}");
}

#[test]
fn duplicate_weapon_names_rejected() {
    let text = format!(
        "{WEAPONS}gauss: {{kind: bullet, speed: 1, range: 1, damage: 1, interval: 1, spread_deg: 0}}\n"
    );
    let err = Catalogue::from_yaml(&[], &text).unwrap_err();
    assert!(err.to_string().contains("gauss"), "{err}");
}

#[cfg(not(target_os = "wasi"))]
mod fs {
    use std::path::{Path, PathBuf};

    use sim::data::{Catalogue, DataError};

    fn assets() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../assets")
    }

    #[test]
    fn load_dir_matches_from_yaml() {
        let loaded = Catalogue::load_dir(&assets()).expect("assets load");
        assert_eq!(loaded, super::shipped());
    }

    #[test]
    fn load_dir_missing_dir_is_an_error() {
        let err = Catalogue::load_dir(Path::new("/nonexistent/rl-fighter-assets")).unwrap_err();
        assert!(matches!(err, DataError::Parse { .. }), "{err:?}");
    }
}
