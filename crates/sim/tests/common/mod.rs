//! Shared test fixtures: the M1 catalogue built by hand (SIM_SPEC §4.1, §4.2), so
//! integration tests do not depend on the YAML loader. `tests/fixtures_match_assets.rs`
//! checks it against the shipped asset files, so the two cannot drift apart.
//!
//! Numbers are ported from `prototypes/story/hulls.js` and the spec tables. Hulls
//! are sorted by name like the loader (fighter = 0, gunship = 1, strafer = 2);
//! weapons are in `weapons.yaml` file order (gauss, laser, flak, torpedo).

// Each test binary uses a different subset of these helpers.
#![allow(dead_code)]

use sim::data::{
    Catalogue, Circle, HullDef, HullId, ShieldDef, ThrusterDef, TurretDef, WeaponDef, WeaponId,
    WeaponKind,
};
use sim::setup::MatchConfig;
use sim::state::Match;
use sim::{TICK_HZ, Vec2};

pub const GAUSS: WeaponId = 0;
pub const LASER: WeaponId = 1;
pub const FLAK: WeaponId = 2;
pub const TORPEDO: WeaponId = 3;

pub const FIGHTER: HullId = 0;
pub const GUNSHIP: HullId = 1;
pub const STRAFER: HullId = 2;

fn v(x: f32, y: f32) -> Vec2 {
    Vec2::new(x, y)
}

fn circle(x: f32, y: f32, r: f32) -> Circle {
    Circle { pos: v(x, y), r }
}

fn thruster(id: &str, pos: (f32, f32), dir: (f32, f32), max_force: f32) -> ThrusterDef {
    ThrusterDef {
        id: id.to_string(),
        pos: v(pos.0, pos.1),
        dir: v(dir.0, dir.1),
        max_force,
    }
}

fn turret(
    id: &str,
    pos: (f32, f32),
    rest_deg: f32,
    arc_deg: f32,
    slew_deg_s: f32,
    weapon: WeaponId,
) -> TurretDef {
    TurretDef {
        id: id.to_string(),
        pos: v(pos.0, pos.1),
        rest: rest_deg.to_radians(),
        arc: arc_deg.to_radians(),
        slew_rate: slew_deg_s.to_radians(),
        weapon,
    }
}

/// Authored fields only; `derive()` fills the rest.
fn hull(name: &str, role: &str, hp: f32, mass: f32, inertia: f32, speed_cap: f32) -> HullDef {
    HullDef {
        name: name.to_string(),
        role: role.to_string(),
        hp,
        mass,
        inertia,
        speed_cap,
        is_static: false,
        shield: None,
        reaction_ticks: None,
        cost: 10,
        collision: Vec::new(),
        thrusters: Vec::new(),
        turrets: Vec::new(),
        bays: Vec::new(),
        bound_radius: 0.0,
        shield_radius: 0.0,
        n_power_systems: 0,
        arrival_speed: 0.0,
    }
}

pub fn fighter_hull() -> HullDef {
    let mut h = hull("fighter", "fighter", 60.0, 10.0, 55.0, 60.0);
    h.collision = vec![circle(2.0, 0.0, 2.4), circle(-2.2, 0.0, 2.6)];
    h.thrusters = vec![
        thruster("thruster.main.0", (-4.6, 0.0), (1.0, 0.0), 900.0),
        thruster("thruster.rcs.fl", (2.2, 2.3), (0.0, -1.0), 160.0),
        thruster("thruster.rcs.fr", (2.2, -2.3), (0.0, 1.0), 160.0),
        thruster("thruster.rcs.rl", (-2.8, 2.3), (0.0, -1.0), 160.0),
        thruster("thruster.rcs.rr", (-2.8, -2.3), (0.0, 1.0), 160.0),
    ];
    h.turrets = vec![turret("turret.nose", (3.8, 0.0), 0.0, 0.0, 0.0, GAUSS)];
    h.derive();
    h
}

pub fn strafer_hull() -> HullDef {
    let mut h = hull("strafer", "skirmisher", 70.0, 11.0, 75.0, 50.0);
    h.shield = Some(ShieldDef {
        hp: 40.0,
        regen_rate: 8.0,
        regen_delay: 3.0,
        radius: 7.5,
    });
    h.collision = vec![
        circle(0.0, 0.0, 3.2),
        circle(0.0, 3.6, 2.4),
        circle(0.0, -3.6, 2.4),
    ];
    h.thrusters = vec![
        thruster("thruster.main.0", (-4.1, 0.0), (1.0, 0.0), 380.0),
        thruster("thruster.lateral.fl", (2.4, 4.7), (0.0, -1.0), 420.0),
        thruster("thruster.lateral.fr", (2.4, -4.7), (0.0, 1.0), 420.0),
        thruster("thruster.lateral.rl", (-2.4, 4.7), (0.0, -1.0), 420.0),
        thruster("thruster.lateral.rr", (-2.4, -4.7), (0.0, 1.0), 420.0),
    ];
    h.turrets = vec![turret("turret.nose", (3.4, 0.0), 0.0, 0.0, 0.0, LASER)];
    h.derive();
    h
}

pub fn gunship_hull() -> HullDef {
    let mut h = hull("gunship", "anchor", 320.0, 60.0, 2200.0, 24.0);
    h.cost = 30;
    h.shield = Some(ShieldDef {
        hp: 140.0,
        regen_rate: 12.0,
        regen_delay: 4.0,
        radius: 11.0,
    });
    h.collision = vec![
        circle(4.5, 0.0, 3.6),
        circle(0.0, 0.0, 4.6),
        circle(-4.5, 0.0, 3.8),
    ];
    h.thrusters = vec![
        thruster("thruster.main.l", (-7.0, 2.0), (1.0, 0.0), 1700.0),
        thruster("thruster.main.r", (-7.0, -2.0), (1.0, 0.0), 1700.0),
        thruster("thruster.rcs.fl", (4.0, 4.4), (0.0, -1.0), 500.0),
        thruster("thruster.rcs.fr", (4.0, -4.4), (0.0, 1.0), 500.0),
        thruster("thruster.rcs.rl", (-4.5, 4.6), (0.0, -1.0), 500.0),
        thruster("thruster.rcs.rr", (-4.5, -4.6), (0.0, 1.0), 500.0),
    ];
    h.turrets = vec![
        turret("turret.fore", (3.8, 0.0), 0.0, 240.0, 120.0, FLAK),
        turret("turret.port", (-2.7, 2.8), 90.0, 220.0, 90.0, GAUSS),
        turret("turret.starboard", (-2.7, -2.8), -90.0, 220.0, 90.0, GAUSS),
    ];
    h.derive();
    h
}

/// Synthetic immobile hull (SIM_SPEC §3.4): no thrusters, one fixed gun, shield.
pub fn static_hull() -> HullDef {
    let mut h = hull("teststation", "station", 500.0, 5000.0, 1.0e6, 0.0);
    h.is_static = true;
    h.shield = Some(ShieldDef {
        hp: 100.0,
        regen_rate: 10.0,
        regen_delay: 5.0,
        radius: 12.0,
    });
    h.collision = vec![circle(0.0, 0.0, 10.0)];
    h.turrets = vec![turret("turret.0", (5.0, 0.0), 0.0, 0.0, 0.0, GAUSS)];
    h.derive();
    h
}

#[allow(clippy::too_many_arguments)]
fn weapon(
    name: &str,
    kind: WeaponKind,
    speed: f32,
    range: f32,
    damage: f32,
    interval: f32,
    spread_deg: f32,
) -> WeaponDef {
    let mut w = WeaponDef {
        name: name.to_string(),
        kind,
        speed,
        range,
        damage,
        interval,
        spread: spread_deg.to_radians(),
        burst_radius: 0.0,
        fuse_jitter: 0.0,
        turn_rate: 0.0,
        lock_cone: 0.0,
        life_factor: 1.0,
        life_ticks: 0,
    };
    derive_life(&mut w);
    w
}

/// `life_ticks = round(range / speed * 30 * life_factor)`; 0 for beams.
fn derive_life(w: &mut WeaponDef) {
    w.life_ticks = if w.kind == WeaponKind::Beam {
        0
    } else {
        (w.range / w.speed * TICK_HZ * w.life_factor).round() as u32
    };
}

pub fn test_weapons() -> Vec<WeaponDef> {
    let gauss = weapon("gauss", WeaponKind::Bullet, 240.0, 300.0, 6.0, 0.16, 0.6);
    let laser = weapon("laser", WeaponKind::Beam, 0.0, 180.0, 3.0, 0.10, 0.6);
    let mut flak = weapon("flak", WeaponKind::Flak, 180.0, 230.0, 4.0, 0.09, 3.5);
    flak.burst_radius = 14.0;
    flak.fuse_jitter = 0.4;
    let mut torpedo = weapon("torpedo", WeaponKind::Torpedo, 95.0, 340.0, 55.0, 3.2, 0.0);
    torpedo.turn_rate = 40f32.to_radians();
    torpedo.lock_cone = 30f32.to_radians();
    torpedo.life_factor = 1.3;
    derive_life(&mut torpedo);
    vec![gauss, laser, flak, torpedo]
}

/// The three M1 hulls and four weapons, ids as the loader would assign them.
pub fn test_catalogue() -> Catalogue {
    Catalogue {
        hulls: vec![fighter_hull(), gunship_hull(), strafer_hull()],
        weapons: test_weapons(),
    }
}

/// `test_catalogue()` plus `static_hull()` as the last hull id; returns that id.
pub fn catalogue_with_static() -> (Catalogue, HullId) {
    let mut cat = test_catalogue();
    cat.hulls.push(static_hull());
    let id = (cat.hulls.len() - 1) as HullId;
    (cat, id)
}

/// No reaction delay, so stage tests see an action on the very next step; tests of
/// the delay set `reaction_ticks` themselves.
pub fn config(seed: u64, team0: &[HullId], team1: &[HullId]) -> MatchConfig {
    MatchConfig {
        seed,
        reaction_ticks: 0,
        fleets: [team0.to_vec(), team1.to_vec()],
        ..MatchConfig::default()
    }
}

/// A match from `config(seed, team0, team1)`; panics on setup errors.
pub fn new_match(cat: &Catalogue, seed: u64, team0: &[HullId], team1: &[HullId]) -> Match {
    Match::new(cat, &config(seed, team0, team1)).expect("match setup")
}

/// Mark every ship present at its scheduled position, at rest and with no control
/// lock, skipping the jump-in: for tests of later stages that want ships in at t=0.
pub fn make_all_present(m: &mut Match) {
    for s in &mut m.ships {
        s.present = true;
    }
}

/// `new_match` with every ship already present (see `make_all_present`).
pub fn new_present_match(cat: &Catalogue, seed: u64, team0: &[HullId], team1: &[HullId]) -> Match {
    let mut m = new_match(cat, seed, team0, team1);
    make_all_present(&mut m);
    m
}

/// The catalogue loaded from the shipped `assets/` YAML (embedded, so wasip1 can run it).
pub fn asset_catalogue() -> Catalogue {
    let hulls = [
        (
            "fighter",
            include_str!("../../../../assets/hulls/fighter/hull.yaml"),
        ),
        (
            "gunship",
            include_str!("../../../../assets/hulls/gunship/hull.yaml"),
        ),
        (
            "strafer",
            include_str!("../../../../assets/hulls/strafer/hull.yaml"),
        ),
    ];
    let weapons = include_str!("../../../../assets/weapons.yaml");
    Catalogue::from_yaml(&hulls, weapons).expect("shipped assets load")
}
