//! Shared test fixtures: the M1 catalogue built by hand (SIM_SPEC §4.1, §4.2), so
//! integration tests do not depend on the YAML loader. `tests/fixtures_match_assets.rs`
//! checks it against the shipped asset files, so the two cannot drift apart.
//!
//! Numbers are ported from `prototypes/story/hulls.js` and the spec tables. Hulls
//! are in the loader's order (v4: carrier = 0, fighter = 1, freighter = 2,
//! gunship = 3, strafer = 4; v9 appends bomber = 5, station = 6, after the legacy
//! hulls, `sim::data::hull_order`);
//! weapons are in `weapons.yaml` file order (gauss, laser, flak, torpedo).

// Each test binary uses a different subset of these helpers.
#![allow(dead_code)]

use sim::data::{
    ArmourArc, BayDef, Catalogue, Circle, DEFAULT_HARDPOINT_HIT_RADIUS, HullDef, HullId, ShieldDef,
    ThrusterDef, TurretDef, WeaponDef, WeaponId, WeaponKind,
};
use sim::setup::MatchConfig;
use sim::state::Match;
use sim::{TICK_HZ, Vec2};

pub const GAUSS: WeaponId = 0;
pub const LASER: WeaponId = 1;
pub const FLAK: WeaponId = 2;
pub const TORPEDO: WeaponId = 3;
/// v10.
pub const RAIL: WeaponId = 4;
pub const LANCE: WeaponId = 5;

pub const CARRIER: HullId = 0;
pub const FIGHTER: HullId = 1;
pub const FREIGHTER: HullId = 2;
pub const GUNSHIP: HullId = 3;
pub const STRAFER: HullId = 4;
/// v9.
pub const BOMBER: HullId = 5;
pub const STATION: HullId = 6;
/// v10.
pub const CITADEL: HullId = 7;
pub const DREADNOUGHT: HullId = 8;

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
        hp: 0.0,
        hit_radius: DEFAULT_HARDPOINT_HIT_RADIUS,
    }
}

/// v10: a turret hardpoint of `hp` hit points (default hit radius).
#[allow(clippy::too_many_arguments)]
fn hard_turret(
    id: &str,
    pos: (f32, f32),
    rest_deg: f32,
    arc_deg: f32,
    slew_deg_s: f32,
    weapon: WeaponId,
    hp: f32,
) -> TurretDef {
    TurretDef {
        hp,
        ..turret(id, pos, rest_deg, arc_deg, slew_deg_s, weapon)
    }
}

/// A bay; `hp` 0 is not a hardpoint.
fn bay(id: &str, pos: (f32, f32), dir: (f32, f32), hp: f32, hit_radius: f32) -> BayDef {
    BayDef {
        id: id.to_string(),
        pos: v(pos.0, pos.1),
        dir: v(dir.0, dir.1).normalized(),
        hp,
        hit_radius,
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
        armour: Vec::new(),
        impact: Vec::new(),
        bound_radius: 0.0,
        shield_radius: 0.0,
        n_power_systems: 0,
        arrival_speed: 0.0,
    }
}

pub fn fighter_hull() -> HullDef {
    let mut h = hull("fighter", "fighter", 80.0, 10.0, 55.0, 60.0);
    h.collision = vec![circle(2.0, 0.0, 2.4), circle(-2.2, 0.0, 2.6)];
    h.thrusters = vec![
        thruster("thruster.main.0", (-4.6, 0.0), (1.0, 0.0), 900.0),
        thruster("thruster.rcs.fl", (2.2, 2.3), (0.0, -1.0), 160.0),
        thruster("thruster.rcs.fr", (2.2, -2.3), (0.0, 1.0), 160.0),
        thruster("thruster.rcs.rl", (-2.8, 2.3), (0.0, -1.0), 160.0),
        thruster("thruster.rcs.rr", (-2.8, -2.3), (0.0, 1.0), 160.0),
    ];
    h.turrets = vec![turret("turret.nose", (3.8, 0.0), 0.0, 0.0, 0.0, GAUSS)];
    h.armour = fighter_armour();
    h.impact = nose_impact();
    h.derive();
    h
}

/// `[from_deg, to_deg)` → `mult`, as in the fighter YAML (SIM_SPEC §4.1, v2).
fn armour_arc(from_deg: f32, to_deg: f32, mult: f32) -> ArmourArc {
    ArmourArc {
        from: from_deg.to_radians(),
        to: to_deg.to_radians(),
        mult,
    }
}

/// Fighter armour: engine 1.5x beyond ±135°, flanks 1x, nose 0.5x within ±45°.
pub fn fighter_armour() -> Vec<ArmourArc> {
    vec![
        armour_arc(-180.0, -135.0, 1.5),
        armour_arc(-135.0, -45.0, 1.0),
        armour_arc(-45.0, 45.0, 0.5),
        armour_arc(45.0, 135.0, 1.0),
        armour_arc(135.0, 180.0, 1.5),
    ]
}

/// Fighter and strafer impact arcs (v3): the nose (±45°) takes 1.5x collision
/// damage, everything else 1x.
pub fn nose_impact() -> Vec<ArmourArc> {
    vec![
        armour_arc(-180.0, -45.0, 1.0),
        armour_arc(-45.0, 45.0, 1.5),
        armour_arc(45.0, 180.0, 1.0),
    ]
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
    h.impact = nose_impact();
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
    h.impact = vec![armour_arc(-180.0, 180.0, 0.75)];
    h.derive();
    h
}

/// v4 carrier (SIM_SPEC §4.1): flak, two bays.
pub fn carrier_hull() -> HullDef {
    let mut h = hull("carrier", "carrier", 1000.0, 600.0, 90000.0, 8.0);
    h.cost = 120;
    h.shield = Some(ShieldDef {
        hp: 260.0,
        regen_rate: 15.0,
        regen_delay: 5.0,
        radius: 24.0,
    });
    h.collision = vec![
        circle(13.0, 0.0, 6.5),
        circle(0.0, 0.0, 8.5),
        circle(-13.0, 0.0, 7.5),
    ];
    h.thrusters = vec![
        thruster("thruster.main.l", (-19.5, 4.5), (1.0, 0.0), 300.0),
        thruster("thruster.main.c", (-20.0, 0.0), (1.0, 0.0), 300.0),
        thruster("thruster.main.r", (-19.5, -4.5), (1.0, 0.0), 300.0),
        thruster("thruster.rcs.fl", (15.0, 8.0), (0.0, -1.0), 450.0),
        thruster("thruster.rcs.fr", (15.0, -8.0), (0.0, 1.0), 450.0),
        thruster("thruster.rcs.rl", (-14.0, 8.5), (0.0, -1.0), 450.0),
        thruster("thruster.rcs.rr", (-14.0, -8.5), (0.0, 1.0), 450.0),
    ];
    h.turrets = vec![
        turret("turret.flak.fore", (12.0, 0.0), 0.0, 270.0, 90.0, FLAK),
        turret("turret.flak.port", (-6.0, 7.0), 90.0, 200.0, 90.0, FLAK),
        turret(
            "turret.flak.starboard",
            (-6.0, -7.0),
            -90.0,
            200.0,
            90.0,
            FLAK,
        ),
    ];
    h.bays = vec![
        bay("bay.port", (4.0, 9.0), (0.5, 0.87), 0.0, 8.0),
        bay("bay.starboard", (4.0, -9.0), (0.5, -0.87), 0.0, 8.0),
    ];
    h.impact = vec![armour_arc(-180.0, 180.0, 0.5)];
    h.derive();
    h
}

/// v4 freighter, the convoy transport: unarmed, weak heading-hold RCS.
pub fn freighter_hull() -> HullDef {
    let mut h = hull("freighter", "transport", 400.0, 300.0, 40000.0, 10.5);
    h.cost = 40;
    h.shield = Some(ShieldDef {
        hp: 80.0,
        regen_rate: 6.0,
        regen_delay: 5.0,
        radius: 15.0,
    });
    h.collision = vec![
        circle(8.0, 0.0, 4.0),
        circle(0.0, 0.0, 4.5),
        circle(-8.0, 0.0, 4.2),
    ];
    h.thrusters = vec![
        thruster("thruster.main.l", (-13.0, 2.0), (1.0, 0.0), 3000.0),
        thruster("thruster.main.r", (-13.0, -2.0), (1.0, 0.0), 3000.0),
        thruster("thruster.rcs.fl", (9.0, 4.2), (0.0, -1.0), 300.0),
        thruster("thruster.rcs.fr", (9.0, -4.2), (0.0, 1.0), 300.0),
        thruster("thruster.rcs.rl", (-9.0, 4.4), (0.0, -1.0), 300.0),
        thruster("thruster.rcs.rr", (-9.0, -4.4), (0.0, 1.0), 300.0),
    ];
    h.impact = vec![armour_arc(-180.0, 180.0, 0.75)];
    h.derive();
    h
}

/// v9 bomber: anchor role, fixed forward torpedo rack.
pub fn bomber_hull() -> HullDef {
    let mut h = hull("bomber", "anchor", 200.0, 22.0, 260.0, 34.0);
    h.cost = 25;
    h.shield = Some(ShieldDef {
        hp: 60.0,
        regen_rate: 8.0,
        regen_delay: 4.0,
        radius: 8.0,
    });
    h.collision = vec![circle(3.0, 0.0, 3.0), circle(-2.5, 0.0, 3.4)];
    h.thrusters = vec![
        thruster("thruster.main.l", (-6.0, 1.6), (1.0, 0.0), 900.0),
        thruster("thruster.main.r", (-6.0, -1.6), (1.0, 0.0), 900.0),
        thruster("thruster.rcs.fl", (3.5, 3.2), (0.0, -1.0), 260.0),
        thruster("thruster.rcs.fr", (3.5, -3.2), (0.0, 1.0), 260.0),
        thruster("thruster.rcs.rl", (-3.5, 3.8), (0.0, -1.0), 260.0),
        thruster("thruster.rcs.rr", (-3.5, -3.8), (0.0, 1.0), 260.0),
    ];
    h.turrets = vec![turret("turret.rack", (4.8, 0.0), 0.0, 0.0, 0.0, TORPEDO)];
    h.impact = vec![armour_arc(-180.0, 180.0, 0.75)];
    h.derive();
    h
}

/// v9 station: static carrier-role hull, six turrets, two bays.
pub fn station_hull() -> HullDef {
    let mut h = hull("station", "carrier", 1600.0, 5000.0, 1.0e6, 0.0);
    h.cost = 200;
    h.is_static = true;
    h.shield = Some(ShieldDef {
        hp: 300.0,
        regen_rate: 20.0,
        regen_delay: 5.0,
        radius: 27.0,
    });
    h.collision = vec![circle(0.0, 0.0, 21.0)];
    h.turrets = vec![
        turret("turret.flak.0", (16.0, 0.0), 0.0, 220.0, 90.0, FLAK),
        turret("turret.flak.1", (-8.0, 13.9), 120.0, 220.0, 90.0, FLAK),
        turret("turret.flak.2", (-8.0, -13.9), -120.0, 220.0, 90.0, FLAK),
        turret("turret.gauss.0", (8.0, 13.9), 60.0, 220.0, 120.0, GAUSS),
        turret("turret.gauss.1", (-16.0, 0.0), 180.0, 220.0, 120.0, GAUSS),
        turret("turret.gauss.2", (8.0, -13.9), -60.0, 220.0, 120.0, GAUSS),
    ];
    h.bays = vec![
        bay("bay.port", (0.0, 21.0), (0.0, 1.0), 0.0, 8.0),
        bay("bay.starboard", (0.0, -21.0), (0.0, -1.0), 0.0, 8.0),
    ];
    h.impact = vec![armour_arc(-180.0, 180.0, 0.5)];
    h.derive();
    h
}

/// v10 citadel: static carrier-role ring, twelve turret and four bay hardpoints
/// (`lab/runs/2026-11-19-citadel-dreadnought/plan.md`).
pub fn citadel_hull() -> HullDef {
    let mut h = hull("citadel", "carrier", 3200.0, 20000.0, 1.0e7, 0.0);
    h.cost = 320;
    h.is_static = true;
    h.shield = Some(ShieldDef {
        hp: 600.0,
        regen_rate: 30.0,
        regen_delay: 5.0,
        radius: 56.0,
    });
    h.collision = vec![
        circle(0.0, 0.0, 20.0),
        circle(38.0, 0.0, 11.0),
        circle(19.0, 32.91, 11.0),
        circle(-19.0, 32.91, 11.0),
        circle(-38.0, 0.0, 11.0),
        circle(-19.0, -32.91, 11.0),
        circle(19.0, -32.91, 11.0),
    ];
    let lance = |id, pos, rest| hard_turret(id, pos, rest, 240.0, 20.0, LANCE, 250.0);
    let flak = |id, pos, rest| hard_turret(id, pos, rest, 200.0, 90.0, FLAK, 120.0);
    let gauss = |id, pos, rest| hard_turret(id, pos, rest, 200.0, 120.0, GAUSS, 100.0);
    h.turrets = vec![
        lance("turret.lance.0", (44.0, 0.0), 0.0),
        flak("turret.flak.0", (41.59, -5.85), 0.0),
        flak("turret.flak.1", (25.86, 33.1), 60.0),
        gauss("turret.gauss.0", (15.73, 38.94), 60.0),
        flak("turret.flak.2", (-15.73, 38.94), 120.0),
        gauss("turret.gauss.1", (-25.86, 33.1), 120.0),
        lance("turret.lance.1", (-44.0, 0.0), 180.0),
        flak("turret.flak.3", (-41.59, 5.85), 180.0),
        flak("turret.flak.4", (-25.86, -33.1), -120.0),
        gauss("turret.gauss.2", (-15.73, -38.94), -120.0),
        flak("turret.flak.5", (15.73, -38.94), -60.0),
        gauss("turret.gauss.3", (25.86, -33.1), -60.0),
    ];
    h.bays = vec![
        bay("bay.0", (19.05, 11.0), (0.866, 0.5), 200.0, 7.0),
        bay("bay.1", (-19.05, 11.0), (-0.866, 0.5), 200.0, 7.0),
        bay("bay.2", (-19.05, -11.0), (-0.866, -0.5), 200.0, 7.0),
        bay("bay.3", (19.05, -11.0), (0.866, -0.5), 200.0, 7.0),
    ];
    h.impact = vec![armour_arc(-180.0, 180.0, 0.5)];
    h.derive();
    h
}

/// v10 dreadnought: role `line`, armoured bow, five turret hardpoints, no bays.
pub fn dreadnought_hull() -> HullDef {
    let mut h = hull("dreadnought", "line", 1800.0, 900.0, 150000.0, 7.0);
    h.cost = 180;
    h.shield = Some(ShieldDef {
        hp: 350.0,
        regen_rate: 18.0,
        regen_delay: 5.0,
        radius: 36.0,
    });
    h.armour = vec![
        armour_arc(-180.0, -135.0, 1.3),
        armour_arc(-135.0, -60.0, 0.7),
        armour_arc(-60.0, 60.0, 0.4),
        armour_arc(60.0, 135.0, 0.7),
        armour_arc(135.0, 180.0, 1.3),
    ];
    h.impact = vec![armour_arc(-180.0, 180.0, 0.5)];
    h.collision = vec![
        circle(20.0, 0.0, 7.0),
        circle(6.0, 0.0, 9.0),
        circle(-10.0, 0.0, 9.0),
        circle(-24.0, 0.0, 7.0),
    ];
    h.thrusters = vec![
        thruster("thruster.main.l", (-31.0, 5.0), (1.0, 0.0), 420.0),
        thruster("thruster.main.c", (-31.0, 0.0), (1.0, 0.0), 420.0),
        thruster("thruster.main.r", (-31.0, -5.0), (1.0, 0.0), 420.0),
        thruster("thruster.rcs.fl", (22.0, 7.0), (0.0, -1.0), 600.0),
        thruster("thruster.rcs.fr", (22.0, -7.0), (0.0, 1.0), 600.0),
        thruster("thruster.rcs.rl", (-22.0, 8.0), (0.0, -1.0), 600.0),
        thruster("thruster.rcs.rr", (-22.0, -8.0), (0.0, 1.0), 600.0),
    ];
    h.turrets = vec![
        hard_turret(
            "turret.rail.fore",
            (14.0, 0.0),
            0.0,
            300.0,
            25.0,
            RAIL,
            220.0,
        ),
        hard_turret(
            "turret.rail.aft",
            (-14.0, 0.0),
            180.0,
            300.0,
            25.0,
            RAIL,
            220.0,
        ),
        hard_turret(
            "turret.flak.port",
            (0.0, 9.0),
            90.0,
            200.0,
            90.0,
            FLAK,
            120.0,
        ),
        hard_turret(
            "turret.flak.starboard",
            (0.0, -9.0),
            -90.0,
            200.0,
            90.0,
            FLAK,
            120.0,
        ),
        hard_turret(
            "turret.gauss.bow",
            (26.0, 0.0),
            0.0,
            180.0,
            120.0,
            GAUSS,
            100.0,
        ),
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
        capital_only: false,
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
    let gauss = weapon("gauss", WeaponKind::Bullet, 200.0, 220.0, 5.0, 0.20, 1.0);
    let laser = weapon("laser", WeaponKind::Beam, 0.0, 180.0, 3.0, 0.10, 0.6);
    let mut flak = weapon("flak", WeaponKind::Flak, 180.0, 230.0, 4.0, 0.09, 3.5);
    flak.burst_radius = 14.0;
    flak.fuse_jitter = 0.4;
    // v9: retuned for the bomber's rack (v4-v8: 95 m/s, 340 m, 55, 3.2 s, 40 deg/s).
    let mut torpedo = weapon("torpedo", WeaponKind::Torpedo, 90.0, 240.0, 150.0, 4.5, 0.0);
    torpedo.turn_rate = 30f32.to_radians();
    torpedo.lock_cone = 30f32.to_radians();
    torpedo.life_factor = 1.3;
    derive_life(&mut torpedo);
    // v10, appended.
    let rail = weapon("rail", WeaponKind::Bullet, 260.0, 380.0, 22.0, 1.6, 0.3);
    let mut lance = weapon("lance", WeaponKind::Bullet, 300.0, 430.0, 130.0, 2.2, 0.2);
    lance.capital_only = true;
    vec![gauss, laser, flak, torpedo, rail, lance]
}

/// The five v4 hulls, v9's bomber and station, and four weapons, ids as the loader
/// would assign them.
pub fn test_catalogue() -> Catalogue {
    Catalogue {
        hulls: vec![
            carrier_hull(),
            fighter_hull(),
            freighter_hull(),
            gunship_hull(),
            strafer_hull(),
            bomber_hull(),
            station_hull(),
            citadel_hull(),
            dreadnought_hull(),
        ],
        weapons: test_weapons(),
    }
}

/// `test_catalogue()` with every hull's armour removed (uniform 1x), for tests that pin
/// concrete damage numbers which should not depend on hit bearings (WP14 moved every
/// other test back to the real arcs; only `step.rs::reward_terms_sum_as_spec` uses it).
pub fn uniform_catalogue() -> Catalogue {
    let mut cat = test_catalogue();
    for h in &mut cat.hulls {
        h.armour.clear();
    }
    cat
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
            "carrier",
            include_str!("../../../../assets/hulls/carrier/hull.yaml"),
        ),
        (
            "freighter",
            include_str!("../../../../assets/hulls/freighter/hull.yaml"),
        ),
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
        // v9: listed first among these on purpose, they still take ids 5 and 6.
        (
            "station",
            include_str!("../../../../assets/hulls/station/hull.yaml"),
        ),
        (
            "bomber",
            include_str!("../../../../assets/hulls/bomber/hull.yaml"),
        ),
        // v10: names that sort among the v9 hulls; they take ids 7 and 8.
        (
            "dreadnought",
            include_str!("../../../../assets/hulls/dreadnought/hull.yaml"),
        ),
        (
            "citadel",
            include_str!("../../../../assets/hulls/citadel/hull.yaml"),
        ),
    ];
    let weapons = include_str!("../../../../assets/weapons.yaml");
    Catalogue::from_yaml(&hulls, weapons).expect("shipped assets load")
}
