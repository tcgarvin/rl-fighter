//! Load-time validation rules for hulls and weapons (SIM_SPEC §4.4).
//!
//! Rules run on the authored (raw) structs and push every failure into `errs`, so a
//! broken data file reports all of its problems at once. Each message starts with
//! `rule N:` so tests and humans can tell which rule fired.
//!
//! Comparisons are written `!(x > 0.0)` on purpose: NaN fails every rule.
#![allow(clippy::neg_cmp_op_on_partial_ord)]

use crate::data::raw::{RawHull, RawKind, RawWeapon};
use crate::data::{DataError, life_ticks};
use crate::math::Vec2;

/// Mirrors `state::MAX_THRUSTERS` (SIM_SPEC §3); state.rs is owned by another work
/// package, so the validator keeps its own copy until both land.
pub const MAX_THRUSTERS: usize = 8;
/// Mirrors `state::MAX_TURRETS` (SIM_SPEC §3).
pub const MAX_TURRETS: usize = 6;
/// Rule 3: largest allowed `bound_radius`, metres.
pub const MAX_BOUND_RADIUS: f32 = 60.0;
/// Rule 4: accepted range for authored direction lengths before renormalising.
const DIR_LEN_MIN: f32 = 0.99;
const DIR_LEN_MAX: f32 = 1.01;

/// The `hull` field of `DataError::Invalid` for weapon-file errors.
pub const WEAPONS_FILE: &str = "weapons.yaml";

/// `[a-z0-9_]+`.
pub fn is_valid_name(name: &str) -> bool {
    !name.is_empty()
        && name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_')
}

pub(crate) fn vec2(a: [f32; 2]) -> Vec2 {
    Vec2::new(a[0], a[1])
}

/// `max(|c.pos| + c.r)`, matching `HullDef::derive`.
pub(crate) fn bound_radius(raw: &RawHull) -> f32 {
    raw.collision
        .iter()
        .map(|c| vec2(c.pos).length() + c.r)
        .fold(0.0, f32::max)
}

struct HullErrors<'a> {
    hull: &'a str,
    errs: &'a mut Vec<DataError>,
}

impl HullErrors<'_> {
    fn push(&mut self, msg: String) {
        self.errs.push(DataError::Invalid {
            hull: self.hull.to_string(),
            msg,
        });
    }
}

/// Rules 1–7 for one hull. `dir_name` is the directory (or `from_yaml` key) the hull
/// came from; `weapons` is `None` when the weapon file failed to parse, in which case
/// turret weapon references are not checked (that would only add noise).
pub(crate) fn validate_hull(
    dir_name: &str,
    raw: &RawHull,
    weapons: Option<&[String]>,
    errs: &mut Vec<DataError>,
) {
    let mut e = HullErrors {
        hull: dir_name,
        errs,
    };
    check_name(&mut e, dir_name, raw);
    check_scalars(&mut e, raw);
    let bound = check_collision(&mut e, raw);
    check_mounts(&mut e, raw);
    check_turrets(&mut e, raw, weapons);
    check_shield(&mut e, raw, bound);
    check_authority(&mut e, raw);
}

fn check_name(e: &mut HullErrors, dir_name: &str, raw: &RawHull) {
    if raw.name != dir_name {
        e.push(format!(
            "rule 1: name {:?} does not match directory {dir_name:?}",
            raw.name
        ));
    }
    if !is_valid_name(&raw.name) {
        e.push(format!("rule 1: name {:?} must match [a-z0-9_]+", raw.name));
    }
}

fn check_scalars(e: &mut HullErrors, raw: &RawHull) {
    for (field, value) in [("hp", raw.hp), ("mass", raw.mass), ("inertia", raw.inertia)] {
        if !(value > 0.0) {
            e.push(format!("rule 2: {field} must be > 0, got {value}"));
        }
    }
    if !(raw.speed_cap >= 0.0) {
        e.push(format!(
            "rule 2: speed_cap must be >= 0, got {}",
            raw.speed_cap
        ));
    } else if raw.speed_cap == 0.0 && !raw.is_static {
        e.push("rule 2: speed_cap may be 0 only for static hulls".to_string());
    }
}

/// Returns the bound radius for the shield check.
fn check_collision(e: &mut HullErrors, raw: &RawHull) -> f32 {
    if raw.collision.is_empty() {
        e.push("rule 3: needs at least one collision circle".to_string());
    }
    for (i, c) in raw.collision.iter().enumerate() {
        if !(c.r > 0.0) {
            e.push(format!(
                "rule 3: collision circle {i} has r = {}, must be > 0",
                c.r
            ));
        }
    }
    let bound = bound_radius(raw);
    if !(bound <= MAX_BOUND_RADIUS) {
        e.push(format!(
            "rule 3: bound_radius {bound} exceeds {MAX_BOUND_RADIUS}"
        ));
    }
    bound
}

fn check_dir(e: &mut HullErrors, id: &str, dir: [f32; 2]) {
    let len = vec2(dir).length();
    if !(DIR_LEN_MIN..=DIR_LEN_MAX).contains(&len) {
        e.push(format!(
            "rule 4: {id} dir has length {len}, must be in [{DIR_LEN_MIN}, {DIR_LEN_MAX}]"
        ));
    }
}

fn check_mounts(e: &mut HullErrors, raw: &RawHull) {
    if raw.thrusters.len() > MAX_THRUSTERS {
        e.push(format!(
            "rule 4: {} thrusters exceeds MAX_THRUSTERS = {MAX_THRUSTERS}",
            raw.thrusters.len()
        ));
    }
    if raw.turrets.len() > MAX_TURRETS {
        e.push(format!(
            "rule 4: {} turrets exceeds MAX_TURRETS = {MAX_TURRETS}",
            raw.turrets.len()
        ));
    }

    let ids = raw
        .thrusters
        .iter()
        .map(|t| &t.id)
        .chain(raw.turrets.iter().map(|t| &t.id))
        .chain(raw.bays.iter().map(|b| &b.id));
    let mut seen: Vec<&String> = Vec::new();
    for id in ids {
        if seen.contains(&id) {
            e.push(format!(
                "rule 4: mount id {id:?} is not unique within the hull"
            ));
        } else {
            seen.push(id);
        }
    }

    for t in &raw.thrusters {
        check_dir(e, &t.id, t.dir);
        if !(t.max_force > 0.0) {
            e.push(format!(
                "rule 4: {} max_force must be > 0, got {}",
                t.id, t.max_force
            ));
        }
    }
    for b in &raw.bays {
        check_dir(e, &b.id, b.dir);
    }
}

fn check_turrets(e: &mut HullErrors, raw: &RawHull, weapons: Option<&[String]>) {
    for t in &raw.turrets {
        let known = weapons.is_none_or(|names| names.contains(&t.weapon));
        if !known {
            e.push(format!(
                "rule 5: {} uses unknown weapon {:?}",
                t.id, t.weapon
            ));
        }
        if !(0.0..=360.0).contains(&t.arc_deg) {
            e.push(format!(
                "rule 5: {} arc_deg {} must be in [0, 360]",
                t.id, t.arc_deg
            ));
        }
        if t.arc_deg > 0.0 && !(t.slew_deg_s > 0.0) {
            e.push(format!(
                "rule 5: {} has arc_deg {} so slew_deg_s must be > 0, got {}",
                t.id, t.arc_deg, t.slew_deg_s
            ));
        }
    }
}

fn check_shield(e: &mut HullErrors, raw: &RawHull, bound: f32) {
    let Some(s) = raw.shield else { return };
    if !(s.hp > 0.0) {
        e.push(format!("rule 6: shield hp must be > 0, got {}", s.hp));
    }
    if !(s.regen_rate >= 0.0) {
        e.push(format!(
            "rule 6: shield regen_rate must be >= 0, got {}",
            s.regen_rate
        ));
    }
    if !(s.regen_delay >= 0.0) {
        e.push(format!(
            "rule 6: shield regen_delay must be >= 0, got {}",
            s.regen_delay
        ));
    }
    if !(s.radius >= bound) {
        e.push(format!(
            "rule 6: shield radius {} is smaller than bound_radius {bound}",
            s.radius
        ));
    }
}

/// Rule 7: a mobile hull must be able to push forward and turn both ways.
fn check_authority(e: &mut HullErrors, raw: &RawHull) {
    if raw.is_static {
        return;
    }
    if raw.thrusters.is_empty() {
        e.push("rule 7: non-static hull needs at least one thruster".to_string());
        return;
    }
    let mut forward = 0.0f32;
    let mut ccw = 0.0f32;
    let mut cw = 0.0f32;
    for t in &raw.thrusters {
        let dir = vec2(t.dir).normalized();
        let force = t.max_force.max(0.0);
        forward += dir.x.max(0.0) * force;
        let torque = vec2(t.pos).cross(dir) * force;
        if torque > 0.0 {
            ccw += torque;
        } else {
            cw -= torque;
        }
    }
    if !(forward > 0.0) {
        e.push("rule 7: thrusters cannot produce net +x force".to_string());
    }
    if !(ccw > 0.0) {
        e.push("rule 7: thrusters cannot produce counter-clockwise torque".to_string());
    }
    if !(cw > 0.0) {
        e.push("rule 7: thrusters cannot produce clockwise torque".to_string());
    }
}

/// Rules 8 and 9 for one weapon.
pub(crate) fn validate_weapon(name: &str, w: &RawWeapon, errs: &mut Vec<DataError>) {
    let mut push = |msg: String| {
        errs.push(DataError::Invalid {
            hull: WEAPONS_FILE.to_string(),
            msg: format!("{name}: {msg}"),
        })
    };
    for (field, value) in [
        ("damage", w.damage),
        ("interval", w.interval),
        ("range", w.range),
    ] {
        if !(value > 0.0) {
            push(format!("rule 8: {field} must be > 0, got {value}"));
        }
    }
    if w.kind == RawKind::Beam {
        return;
    }
    if !(w.speed > 0.0) {
        push(format!(
            "rule 8: speed must be > 0 for non-beam weapons, got {}",
            w.speed
        ));
        return;
    }
    if w.range > 0.0 {
        let ticks = life_ticks(w.range, w.speed, w.life_factor);
        if ticks < 1 {
            push(format!(
                "rule 9: life_ticks = round(range / speed * 30 * life_factor) = {ticks}, must be >= 1"
            ));
        }
    }
}
