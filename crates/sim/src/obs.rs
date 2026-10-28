//! Observation layout constants and `Match::write_obs` (SIM_SPEC §7.2).
//!
//! The obs is a fixed 204-float vector in the observing ship's body frame (relative
//! vectors rotated by `-heading`, so forward = +x, port = +y). Every block is a
//! sequence of fixed-width records of one entity (self, thruster, turret, ship,
//! projectile); each record has its own writer so the later entity-token assembler
//! (DESIGN §7) reuses them rather than redefining features.
//!
//! Every writer clamps its record to `[-OBS_CLIP, OBS_CLIP]` after scaling, writes
//! every slot of its slice, and never allocates. Nearest-K selection uses fixed-size
//! arrays and breaks distance ties by the lower slot / pool index.
//!
//! Choices where §7.2 leaves the meaning open:
//! - `speed` is `|vel|`; `fwd_speed`/`lat_speed` are body-frame velocity x/y.
//! - `dir_to_centre` is the zero vector when the ship is exactly at the centre.
//! - `(R - |pos|)/R` goes negative outside the arena (clamped like everything else).
//! - `time_left` uses `cfg.time_limit_ticks` and is clamped (negative past the limit).
//! - `power` features are the current shares (not the target, not the multipliers).
//! - Thruster `(max_force/mass)/A` is the hull's mass, ignoring power.
//! - Turret `cooldown/interval` uses the weapon's base `interval` (the value cooldown
//!   is set to on fire), so it runs 1 → 0 regardless of power.
//! - Nearby ships exclude the observer and include allies and enemies; `rel_vel` is
//!   `other.vel - self.vel` in the body frame; `shield/max_shield` is 0 for
//!   shieldless hulls.
//! - Projectiles: any live pool entry; `hostile = team != observer.team` (own and
//!   allied shots both have `hostile = 0`); `rel_vel = proj.vel - self.vel`.
//! - Turret arc/range blocks (192, 198) are per turret slot and zero for absent
//!   slots; `write_turret_extras` writes them so a token record can append them.

use crate::data::{Catalogue, HullDef, ThrusterDef};
use crate::math::{TAU, Vec2, clamp, rot};
use crate::state::{MAX_THRUSTERS, MAX_TURRETS, Match, Projectile, Ship, ShipIdx};

/// Total obs width.
pub const OBS_DIM: usize = 204;
/// Every feature is clamped to `[-OBS_CLIP, OBS_CLIP]` after scaling.
pub const OBS_CLIP: f32 = 5.0;

// Scales (§7.2). `R` is the match's arena radius.
/// Speed scale, m/s.
pub const VS: f32 = 100.0;
/// Angular speed scale, rad/s.
pub const OM: f32 = 4.0;
/// Length scale, m.
pub const L: f32 = 20.0;
/// Acceleration scale, m/s².
pub const A: f32 = 100.0;
/// Hit-point scale.
pub const HP: f32 = 400.0;
/// Damage scale.
pub const DMG: f32 = 60.0;
/// Mass scale, kg (self feature 13).
pub const MASS_SCALE: f32 = 100.0;

// Record widths and slot counts.
pub const SELF_W: usize = 20;
pub const THRUSTER_W: usize = 6;
pub const N_THRUSTER_SLOTS: usize = MAX_THRUSTERS;
pub const TURRET_W: usize = 10;
pub const N_TURRET_SLOTS: usize = MAX_TURRETS;
pub const SHIP_W: usize = 12;
/// Nearest active other ships observed.
pub const N_NEAR_SHIPS: usize = 3;
pub const PROJ_W: usize = 7;
/// Nearest live projectiles observed.
pub const N_NEAR_PROJ: usize = 4;
/// Per-turret extras (arc, range), split across the two trailing blocks.
pub const TURRET_EXTRA_W: usize = 2;

// Block offsets and widths.
pub const SELF_OFF: usize = 0;
pub const SELF_WIDTH: usize = SELF_W;
pub const THRUSTERS_OFF: usize = SELF_OFF + SELF_WIDTH;
pub const THRUSTERS_WIDTH: usize = N_THRUSTER_SLOTS * THRUSTER_W;
pub const TURRETS_OFF: usize = THRUSTERS_OFF + THRUSTERS_WIDTH;
pub const TURRETS_WIDTH: usize = N_TURRET_SLOTS * TURRET_W;
pub const SHIPS_OFF: usize = TURRETS_OFF + TURRETS_WIDTH;
pub const SHIPS_WIDTH: usize = N_NEAR_SHIPS * SHIP_W;
pub const PROJ_OFF: usize = SHIPS_OFF + SHIPS_WIDTH;
pub const PROJ_WIDTH: usize = N_NEAR_PROJ * PROJ_W;
pub const TURRET_ARC_OFF: usize = PROJ_OFF + PROJ_WIDTH;
pub const TURRET_ARC_WIDTH: usize = N_TURRET_SLOTS;
pub const TURRET_RANGE_OFF: usize = TURRET_ARC_OFF + TURRET_ARC_WIDTH;
pub const TURRET_RANGE_WIDTH: usize = N_TURRET_SLOTS;

const _: () = assert!(TURRET_RANGE_OFF + TURRET_RANGE_WIDTH == OBS_DIM);

/// `(name, offset, width)` of every block, contiguous and in order; sim-py exports
/// it as `rlf_sim.OBS_LAYOUT`.
pub const OBS_LAYOUT: &[(&str, usize, usize)] = &[
    ("self", SELF_OFF, SELF_WIDTH),
    ("thrusters", THRUSTERS_OFF, THRUSTERS_WIDTH),
    ("turrets", TURRETS_OFF, TURRETS_WIDTH),
    ("ships", SHIPS_OFF, SHIPS_WIDTH),
    ("projectiles", PROJ_OFF, PROJ_WIDTH),
    ("turret_arc", TURRET_ARC_OFF, TURRET_ARC_WIDTH),
    ("turret_range", TURRET_RANGE_OFF, TURRET_RANGE_WIDTH),
];

/// Feature indices within the self record.
pub mod self_f {
    pub const PRESENT: usize = 0;
    pub const CONTROL_LOCKED: usize = 1;
    pub const SPEED: usize = 2;
    pub const FWD_SPEED: usize = 3;
    pub const LAT_SPEED: usize = 4;
    pub const OMEGA: usize = 5;
    pub const HP: usize = 6;
    pub const SHIELD: usize = 7;
    pub const TIME_LEFT: usize = 8;
    pub const HAS_SHIELD: usize = 9;
    pub const POWER_S: usize = 10;
    pub const POWER_E: usize = 11;
    pub const POWER_W: usize = 12;
    pub const MASS: usize = 13;
    pub const SPEED_CAP: usize = 14;
    pub const BOUND_RADIUS: usize = 15;
    pub const MAX_HP: usize = 16;
    pub const DIR_TO_CENTRE_X: usize = 17;
    pub const DIR_TO_CENTRE_Y: usize = 18;
    pub const ARENA_MARGIN: usize = 19;
}

/// Feature indices within a thruster record.
pub mod thruster_f {
    pub const PRESENT: usize = 0;
    pub const POS_X: usize = 1;
    pub const POS_Y: usize = 2;
    pub const DIR_X: usize = 3;
    pub const DIR_Y: usize = 4;
    pub const ACCEL: usize = 5;
}

/// Feature indices within a turret record.
pub mod turret_f {
    pub const PRESENT: usize = 0;
    pub const POS_X: usize = 1;
    pub const POS_Y: usize = 2;
    pub const SIN_ANGLE: usize = 3;
    pub const COS_ANGLE: usize = 4;
    pub const COOLDOWN: usize = 5;
    /// One-hot over `WeaponKind::index()`: bullet, beam, flak, torpedo.
    pub const KIND: usize = 6;
}

/// Feature indices within a nearby-ship record.
pub mod ship_f {
    pub const PRESENT: usize = 0;
    pub const IS_ENEMY: usize = 1;
    pub const REL_POS_X: usize = 2;
    pub const REL_POS_Y: usize = 3;
    pub const REL_VEL_X: usize = 4;
    pub const REL_VEL_Y: usize = 5;
    pub const SIN_REL_HEADING: usize = 6;
    pub const COS_REL_HEADING: usize = 7;
    pub const HP: usize = 8;
    pub const SHIELD: usize = 9;
    pub const BOUND_RADIUS: usize = 10;
    pub const DIST: usize = 11;
}

/// Feature indices within a projectile record.
pub mod proj_f {
    pub const PRESENT: usize = 0;
    pub const HOSTILE: usize = 1;
    pub const REL_POS_X: usize = 2;
    pub const REL_POS_Y: usize = 3;
    pub const REL_VEL_X: usize = 4;
    pub const REL_VEL_Y: usize = 5;
    pub const DAMAGE: usize = 6;
}

#[inline]
fn bit(b: bool) -> f32 {
    if b { 1.0 } else { 0.0 }
}

fn clamp_record(out: &mut [f32]) {
    for x in out.iter_mut() {
        *x = clamp(*x, -OBS_CLIP, OBS_CLIP);
    }
}

/// World-frame vector into the observer's body frame.
#[inline]
fn to_body(observer: &Ship, v: Vec2) -> Vec2 {
    rot(-observer.heading, v)
}

fn shield_fraction(ship: &Ship, hull: &HullDef) -> f32 {
    match hull.shield {
        Some(s) => ship.shield / s.hp,
        None => 0.0,
    }
}

/// Self + arena record (`SELF_W` floats) for an active ship. `out.len() == SELF_W`.
pub fn write_self(m: &Match, cat: &Catalogue, ship: &Ship, out: &mut [f32]) {
    let out = &mut out[..SELF_W];
    let hull = cat.hull(ship.hull);
    let radius = m.cfg.arena_radius;
    let vel_b = to_body(ship, ship.vel);
    let dist_centre = ship.pos.length();
    let to_centre = to_body(ship, -ship.pos).normalized();
    let limit = m.cfg.time_limit_ticks as f32;

    out[self_f::PRESENT] = 1.0;
    out[self_f::CONTROL_LOCKED] = bit(ship.control_locked(m.tick));
    out[self_f::SPEED] = ship.vel.length() / VS;
    out[self_f::FWD_SPEED] = vel_b.x / VS;
    out[self_f::LAT_SPEED] = vel_b.y / VS;
    out[self_f::OMEGA] = ship.omega / OM;
    out[self_f::HP] = ship.hp / hull.hp;
    out[self_f::SHIELD] = shield_fraction(ship, hull);
    out[self_f::TIME_LEFT] = (limit - m.tick as f32) / limit;
    out[self_f::HAS_SHIELD] = bit(hull.has_shield());
    out[self_f::POWER_S] = ship.power[0];
    out[self_f::POWER_E] = ship.power[1];
    out[self_f::POWER_W] = ship.power[2];
    out[self_f::MASS] = hull.mass / MASS_SCALE;
    out[self_f::SPEED_CAP] = hull.speed_cap / VS;
    out[self_f::BOUND_RADIUS] = hull.bound_radius / L;
    out[self_f::MAX_HP] = hull.hp / HP;
    out[self_f::DIR_TO_CENTRE_X] = to_centre.x;
    out[self_f::DIR_TO_CENTRE_Y] = to_centre.y;
    out[self_f::ARENA_MARGIN] = (radius - dist_centre) / radius;
    clamp_record(out);
}

/// One thruster record (`THRUSTER_W` floats); body-frame already, so no rotation.
pub fn write_thruster(hull: &HullDef, t: &ThrusterDef, out: &mut [f32]) {
    let out = &mut out[..THRUSTER_W];
    out[thruster_f::PRESENT] = 1.0;
    out[thruster_f::POS_X] = t.pos.x / L;
    out[thruster_f::POS_Y] = t.pos.y / L;
    out[thruster_f::DIR_X] = t.dir.x;
    out[thruster_f::DIR_Y] = t.dir.y;
    out[thruster_f::ACCEL] = t.max_force / hull.mass / A;
    clamp_record(out);
}

/// Turret slot `j` of `ship` (`TURRET_W` floats). `j` must be < the hull's turret count.
pub fn write_turret(cat: &Catalogue, ship: &Ship, j: usize, out: &mut [f32]) {
    let out = &mut out[..TURRET_W];
    let t = &cat.hull(ship.hull).turrets[j];
    let w = cat.weapon(t.weapon);
    let angle = ship.turret_angle[j];
    out.fill(0.0);
    out[turret_f::PRESENT] = 1.0;
    out[turret_f::POS_X] = t.pos.x / L;
    out[turret_f::POS_Y] = t.pos.y / L;
    out[turret_f::SIN_ANGLE] = libm::sinf(angle);
    out[turret_f::COS_ANGLE] = libm::cosf(angle);
    out[turret_f::COOLDOWN] = ship.turret_cooldown[j] / w.interval;
    out[turret_f::KIND + w.kind.index()] = 1.0;
    clamp_record(out);
}

/// Turret slot `j`'s `[arc/(2π), range/R]` (blocks at `TURRET_ARC_OFF`,
/// `TURRET_RANGE_OFF`). A token record appends these to `write_turret`'s output.
pub fn write_turret_extras(
    cat: &Catalogue,
    ship: &Ship,
    j: usize,
    arena_radius: f32,
    out: &mut [f32],
) {
    let out = &mut out[..TURRET_EXTRA_W];
    let t = &cat.hull(ship.hull).turrets[j];
    out[0] = t.arc / TAU;
    out[1] = cat.weapon(t.weapon).range / arena_radius;
    clamp_record(out);
}

/// Another active ship as seen from `observer` (`SHIP_W` floats).
pub fn write_ship(
    cat: &Catalogue,
    observer: &Ship,
    other: &Ship,
    arena_radius: f32,
    out: &mut [f32],
) {
    let out = &mut out[..SHIP_W];
    let hull = cat.hull(other.hull);
    let delta = other.pos - observer.pos;
    let rel_pos = to_body(observer, delta);
    let rel_vel = to_body(observer, other.vel - observer.vel);
    let rel_heading = other.heading - observer.heading;
    out[ship_f::PRESENT] = 1.0;
    out[ship_f::IS_ENEMY] = bit(other.team != observer.team);
    out[ship_f::REL_POS_X] = rel_pos.x / arena_radius;
    out[ship_f::REL_POS_Y] = rel_pos.y / arena_radius;
    out[ship_f::REL_VEL_X] = rel_vel.x / VS;
    out[ship_f::REL_VEL_Y] = rel_vel.y / VS;
    out[ship_f::SIN_REL_HEADING] = libm::sinf(rel_heading);
    out[ship_f::COS_REL_HEADING] = libm::cosf(rel_heading);
    out[ship_f::HP] = other.hp / hull.hp;
    out[ship_f::SHIELD] = shield_fraction(other, hull);
    out[ship_f::BOUND_RADIUS] = hull.bound_radius / L;
    out[ship_f::DIST] = delta.length() / arena_radius;
    clamp_record(out);
}

/// A live projectile as seen from `observer` (`PROJ_W` floats).
pub fn write_projectile(observer: &Ship, p: &Projectile, arena_radius: f32, out: &mut [f32]) {
    let out = &mut out[..PROJ_W];
    let rel_pos = to_body(observer, p.pos - observer.pos);
    let rel_vel = to_body(observer, p.vel - observer.vel);
    out[proj_f::PRESENT] = 1.0;
    out[proj_f::HOSTILE] = bit(p.team != observer.team);
    out[proj_f::REL_POS_X] = rel_pos.x / arena_radius;
    out[proj_f::REL_POS_Y] = rel_pos.y / arena_radius;
    out[proj_f::REL_VEL_X] = rel_vel.x / VS;
    out[proj_f::REL_VEL_Y] = rel_vel.y / VS;
    out[proj_f::DAMAGE] = p.damage / DMG;
    clamp_record(out);
}

/// Fixed-capacity nearest-K: keeps the `K` smallest `(dist, index)` pairs in
/// ascending order. Ties keep the lower index because candidates arrive in index
/// order and only a strictly smaller distance displaces an earlier entry.
struct NearestK<const K: usize> {
    idx: [usize; K],
    dist: [f32; K],
    len: usize,
}

impl<const K: usize> NearestK<K> {
    fn new() -> Self {
        NearestK {
            idx: [0; K],
            dist: [0.0; K],
            len: 0,
        }
    }

    /// Offer candidate `i` at distance `d`; must be called in increasing `i`.
    fn offer(&mut self, i: usize, d: f32) {
        // Position = number of kept entries with dist <= d (stable for ties).
        let mut pos = 0;
        while pos < self.len && self.dist[pos] <= d {
            pos += 1;
        }
        if pos >= K {
            return;
        }
        let end = if self.len < K { self.len } else { K - 1 };
        let mut k = end;
        while k > pos {
            self.idx[k] = self.idx[k - 1];
            self.dist[k] = self.dist[k - 1];
            k -= 1;
        }
        self.idx[pos] = i;
        self.dist[pos] = d;
        if self.len < K {
            self.len += 1;
        }
    }

    fn indices(&self) -> &[usize] {
        &self.idx[..self.len]
    }
}

/// Distance used for nearest-K ordering. NaN (from a corrupt state) sorts last, so
/// selection stays deterministic.
#[inline]
fn order_dist(delta: Vec2) -> f32 {
    let d = delta.length();
    if d.is_nan() { f32::INFINITY } else { d }
}

impl Match {
    /// Write ship `ship`'s observation into `out` (`len == OBS_DIM`), overwriting
    /// every slot. A dead or not-present observer gets the all-zero vector
    /// (`present = 0`). Panics if `out.len() != OBS_DIM` or `ship` is out of range.
    pub fn write_obs(&self, cat: &Catalogue, ship: ShipIdx, out: &mut [f32]) {
        assert_eq!(
            out.len(),
            OBS_DIM,
            "write_obs: out must have OBS_DIM floats"
        );
        let me = &self.ships[ship as usize];
        out.fill(0.0);
        if !me.active() {
            return;
        }
        let hull = cat.hull(me.hull);
        let radius = self.cfg.arena_radius;

        write_self(self, cat, me, &mut out[SELF_OFF..SELF_OFF + SELF_WIDTH]);

        for (j, t) in hull.thrusters.iter().take(N_THRUSTER_SLOTS).enumerate() {
            let o = THRUSTERS_OFF + j * THRUSTER_W;
            write_thruster(hull, t, &mut out[o..o + THRUSTER_W]);
        }

        let mut extras = [0.0f32; TURRET_EXTRA_W];
        for j in 0..hull.turrets.len().min(N_TURRET_SLOTS) {
            let o = TURRETS_OFF + j * TURRET_W;
            write_turret(cat, me, j, &mut out[o..o + TURRET_W]);
            write_turret_extras(cat, me, j, radius, &mut extras);
            out[TURRET_ARC_OFF + j] = extras[0];
            out[TURRET_RANGE_OFF + j] = extras[1];
        }

        let mut near_ships = NearestK::<N_NEAR_SHIPS>::new();
        for (i, other) in self.ships.iter().enumerate() {
            if i != ship as usize && other.active() {
                near_ships.offer(i, order_dist(other.pos - me.pos));
            }
        }
        for (k, &i) in near_ships.indices().iter().enumerate() {
            let o = SHIPS_OFF + k * SHIP_W;
            write_ship(cat, me, &self.ships[i], radius, &mut out[o..o + SHIP_W]);
        }

        let mut near_proj = NearestK::<N_NEAR_PROJ>::new();
        for (i, p) in self.projectiles.iter().enumerate() {
            if p.alive {
                near_proj.offer(i, order_dist(p.pos - me.pos));
            }
        }
        for (k, &i) in near_proj.indices().iter().enumerate() {
            let o = PROJ_OFF + k * PROJ_W;
            write_projectile(me, &self.projectiles[i], radius, &mut out[o..o + PROJ_W]);
        }
    }
}
