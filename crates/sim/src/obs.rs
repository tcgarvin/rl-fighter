//! Observation layout constants and `Match::write_obs` (SIM_SPEC §7.2, v2).
//!
//! The obs is a fixed 385-float vector in the observing ship's body frame (relative
//! vectors rotated by `-heading`, so forward = +x, port = +y). Every block is a
//! sequence of fixed-width records of one entity (self, thruster, turret, ship,
//! projectile, pending action); each record has its own writer so the later
//! entity-token assembler (DESIGN §7) reuses them rather than redefining features.
//!
//! Every writer clamps its record to `[-OBS_CLIP, OBS_CLIP]` after scaling, writes
//! every slot of its slice, and never allocates. Sorted-K selection uses fixed-size
//! arrays and breaks key ties by the lower slot / pool index.
//!
//! Choices where §7.2 leaves the meaning open:
//! - `speed` is `|vel|`; `fwd_speed`/`lat_speed` are body-frame velocity x/y.
//! - `dir_to_centre` is the zero vector when the ship is exactly at the centre.
//! - `(R - |pos|)/R` goes negative outside the arena (clamped like everything else).
//! - `time_left` uses `cfg.time_limit_ticks` and is clamped (negative past the limit).
//! - `lock_left` divides by `ARRIVAL_LOCK_TICKS` (21), so it reads 1 on the arrival
//!   tick and 0 once the lock is over.
//! - `power` features are the current shares (not the target, not the multipliers).
//! - Thruster `(max_force/mass)/A` is the hull's mass, ignoring power and level.
//! - Turret `cooldown/interval` uses the weapon's base `interval` (the value cooldown
//!   is set to on fire), so it runs 1 → 0 regardless of power.
//! - Other ships exclude the observer and include allies and enemies; `rel_vel` is
//!   `other.vel - self.vel` in the body frame; `shield/max_shield` is 0 for
//!   shieldless hulls.
//! - Projectiles: live pool entries with `team != observer.team` only; `rel_vel =
//!   proj.vel - self.vel` (body frame). The threat score is computed in the world
//!   frame (rotation does not change it); a NaN score sorts last.
//! - Pending records encode the queue as stored (sanitised at enqueue, so slots
//!   beyond the hull's thrusters/turrets read 0).
//! - Turret arc/range blocks are per turret slot and zero for absent slots;
//!   `write_turret_extras` writes them so a token record can append them.

use crate::actions::{POWER_MAX, ShipAction, THROTTLE_HOLD};
use crate::arrival::ARRIVAL_LOCK_TICKS;
use crate::data::{Catalogue, HullDef, ThrusterDef};
use crate::math::{TAU, Vec2, clamp, rot};
use crate::state::{
    MAX_REACTION_TICKS, MAX_SHIPS, MAX_THRUSTERS, MAX_TURRETS, Match, Projectile, Ship, ShipIdx,
};

/// Total obs width.
pub const OBS_DIM: usize = 385;
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
/// Threat horizon, s: closest-approach times are clamped to `[0, T_H]`.
pub const T_H: f32 = 2.0;

// Record widths and slot counts.
pub const SELF_W: usize = 21;
pub const THRUSTER_W: usize = 7;
pub const N_THRUSTER_SLOTS: usize = MAX_THRUSTERS;
pub const TURRET_W: usize = 10;
pub const N_TURRET_SLOTS: usize = MAX_TURRETS;
pub const SHIP_W: usize = 12;
/// Other active ships observed: every other slot of a full match.
pub const N_NEAR_SHIPS: usize = MAX_SHIPS - 1;
pub const PROJ_W: usize = 8;
/// Hostile live projectiles observed, most threatening first.
pub const N_NEAR_PROJ: usize = 8;
/// Pending-action record: present, throttle[8], slew[6], fire[6], power.
pub const PENDING_W: usize = 1 + MAX_THRUSTERS + 2 * MAX_TURRETS + 1;
/// Pending-action slots: the whole reaction queue.
pub const N_PENDING_SLOTS: usize = MAX_REACTION_TICKS;
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
pub const PENDING_OFF: usize = PROJ_OFF + PROJ_WIDTH;
pub const PENDING_WIDTH: usize = N_PENDING_SLOTS * PENDING_W;
pub const TURRET_ARC_OFF: usize = PENDING_OFF + PENDING_WIDTH;
pub const TURRET_ARC_WIDTH: usize = N_TURRET_SLOTS;
pub const TURRET_RANGE_OFF: usize = TURRET_ARC_OFF + TURRET_ARC_WIDTH;
pub const TURRET_RANGE_WIDTH: usize = N_TURRET_SLOTS;

const _: () = assert!(TURRET_RANGE_OFF + TURRET_RANGE_WIDTH == OBS_DIM);
const _: () = assert!(OBS_DIM == 385);
const _: () = assert!(PENDING_W == 22);

/// `(name, offset, width)` of every block, contiguous and in order; sim-py exports
/// it as `rlf_sim.OBS_LAYOUT`.
pub const OBS_LAYOUT: &[(&str, usize, usize)] = &[
    ("self", SELF_OFF, SELF_WIDTH),
    ("thrusters", THRUSTERS_OFF, THRUSTERS_WIDTH),
    ("turrets", TURRETS_OFF, TURRETS_WIDTH),
    ("ships", SHIPS_OFF, SHIPS_WIDTH),
    ("projectiles", PROJ_OFF, PROJ_WIDTH),
    ("pending", PENDING_OFF, PENDING_WIDTH),
    ("turret_arc", TURRET_ARC_OFF, TURRET_ARC_WIDTH),
    ("turret_range", TURRET_RANGE_OFF, TURRET_RANGE_WIDTH),
];

/// `(name, records)` per block, in `OBS_LAYOUT` order; each block's width is
/// `records × record width`. sim-py exports it as `rlf_sim.OBS_SLOTS`.
pub const OBS_SLOTS: &[(&str, usize)] = &[
    ("self", 1),
    ("thrusters", N_THRUSTER_SLOTS),
    ("turrets", N_TURRET_SLOTS),
    ("ships", N_NEAR_SHIPS),
    ("projectiles", N_NEAR_PROJ),
    ("pending", N_PENDING_SLOTS),
    ("turret_arc", N_TURRET_SLOTS),
    ("turret_range", N_TURRET_SLOTS),
];

/// Feature indices within the self record.
pub mod self_f {
    pub const PRESENT: usize = 0;
    /// `max(0, control_lock_until - tick) / ARRIVAL_LOCK_TICKS` (v2; v1 was a bit).
    pub const LOCK_LEFT: usize = 1;
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
    /// `reaction_ticks / MAX_REACTION_TICKS` (v2).
    pub const REACTION_TICKS: usize = 20;
}

/// Feature indices within a thruster record.
pub mod thruster_f {
    pub const PRESENT: usize = 0;
    pub const POS_X: usize = 1;
    pub const POS_Y: usize = 2;
    pub const DIR_X: usize = 3;
    pub const DIR_Y: usize = 4;
    pub const ACCEL: usize = 5;
    /// Current `thrust_level` in `[0, 1]` (v2).
    pub const LEVEL: usize = 6;
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

/// Feature indices within an other-ship record.
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

/// Feature indices within a (hostile) projectile record.
pub mod proj_f {
    pub const PRESENT: usize = 0;
    pub const REL_POS_X: usize = 1;
    pub const REL_POS_Y: usize = 2;
    pub const REL_VEL_X: usize = 3;
    pub const REL_VEL_Y: usize = 4;
    pub const DAMAGE: usize = 5;
    /// Time to closest approach / `T_H`, in `[0, 1]`.
    pub const T_CA: usize = 6;
    /// Closest-approach distance / `L`.
    pub const MISS: usize = 7;
}

/// Feature indices within a pending-action record.
pub mod pending_f {
    use crate::state::{MAX_THRUSTERS, MAX_TURRETS};

    pub const PRESENT: usize = 0;
    /// Throttle heads as −1 (decrease) / 0 (hold) / +1 (increase), 8 slots.
    pub const THROTTLE: usize = 1;
    /// Slew heads as +1 (left, CCW) / 0 (hold) / −1 (right), 6 slots.
    pub const SLEW: usize = THROTTLE + MAX_THRUSTERS;
    /// Fire heads as 0/1, 6 slots.
    pub const FIRE: usize = SLEW + MAX_TURRETS;
    /// `power / POWER_MAX`.
    pub const POWER: usize = FIRE + MAX_TURRETS;
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

/// Self + arena record (`SELF_W` floats) for an active ship. `out.len() >= SELF_W`.
pub fn write_self(m: &Match, cat: &Catalogue, ship: &Ship, out: &mut [f32]) {
    let out = &mut out[..SELF_W];
    let hull = cat.hull(ship.hull);
    let radius = m.cfg.arena_radius;
    let vel_b = to_body(ship, ship.vel);
    let dist_centre = ship.pos.length();
    let to_centre = to_body(ship, -ship.pos).normalized();
    let limit = m.cfg.time_limit_ticks as f32;
    let lock_left = ship.control_lock_until.saturating_sub(m.tick);

    out[self_f::PRESENT] = 1.0;
    out[self_f::LOCK_LEFT] = lock_left as f32 / ARRIVAL_LOCK_TICKS as f32;
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
    out[self_f::REACTION_TICKS] = f32::from(ship.reaction_ticks) / MAX_REACTION_TICKS as f32;
    clamp_record(out);
}

/// One thruster record (`THRUSTER_W` floats) at thrust level `level`; body-frame
/// already, so no rotation.
pub fn write_thruster(hull: &HullDef, t: &ThrusterDef, level: f32, out: &mut [f32]) {
    let out = &mut out[..THRUSTER_W];
    out[thruster_f::PRESENT] = 1.0;
    out[thruster_f::POS_X] = t.pos.x / L;
    out[thruster_f::POS_Y] = t.pos.y / L;
    out[thruster_f::DIR_X] = t.dir.x;
    out[thruster_f::DIR_Y] = t.dir.y;
    out[thruster_f::ACCEL] = t.max_force / hull.mass / A;
    out[thruster_f::LEVEL] = level;
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

/// Closest-approach parts of a projectile relative to an observer (§7.2 threat score).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Threat {
    /// Time to closest approach, s, clamped to `[0, T_H]`.
    pub t_ca: f32,
    /// Distance at closest approach, m.
    pub miss: f32,
    /// `miss + L · t_ca`, m; lower is more threatening.
    pub score: f32,
}

/// The §7.2 threat score of `p` against `observer` (world frame, unscaled):
/// `t_ca = clamp(−r·v / |v|², 0, T_H)` (0 when `|v|² == 0`), `miss = |r + v·t_ca|`,
/// `score = miss + L·t_ca`, with `r = p.pos − me.pos`, `v = p.vel − me.vel`.
pub fn threat(observer: &Ship, p: &Projectile) -> Threat {
    let r = p.pos - observer.pos;
    let v = p.vel - observer.vel;
    let v2 = v.length_sq();
    let t_ca = if v2 == 0.0 {
        0.0
    } else {
        clamp(-r.dot(v) / v2, 0.0, T_H)
    };
    let miss = (r + v * t_ca).length();
    Threat {
        t_ca,
        miss,
        score: miss + L * t_ca,
    }
}

/// A hostile live projectile as seen from `observer` (`PROJ_W` floats), with its
/// precomputed [`threat`] parts.
pub fn write_projectile(
    observer: &Ship,
    p: &Projectile,
    threat: Threat,
    arena_radius: f32,
    out: &mut [f32],
) {
    let out = &mut out[..PROJ_W];
    let rel_pos = to_body(observer, p.pos - observer.pos);
    let rel_vel = to_body(observer, p.vel - observer.vel);
    out[proj_f::PRESENT] = 1.0;
    out[proj_f::REL_POS_X] = rel_pos.x / arena_radius;
    out[proj_f::REL_POS_Y] = rel_pos.y / arena_radius;
    out[proj_f::REL_VEL_X] = rel_vel.x / VS;
    out[proj_f::REL_VEL_Y] = rel_vel.y / VS;
    out[proj_f::DAMAGE] = p.damage / DMG;
    out[proj_f::T_CA] = threat.t_ca / T_H;
    out[proj_f::MISS] = threat.miss / L;
    clamp_record(out);
}

/// One queued action (`PENDING_W` floats): present, throttle as −1/0/+1, slew as
/// +1 (left) / 0 / −1, fire 0/1, power index / `POWER_MAX`.
pub fn write_pending(a: &ShipAction, out: &mut [f32]) {
    let out = &mut out[..PENDING_W];
    out[pending_f::PRESENT] = 1.0;
    for (i, &t) in a.throttle.iter().enumerate() {
        out[pending_f::THROTTLE + i] = f32::from(t) - f32::from(THROTTLE_HOLD);
    }
    for j in 0..MAX_TURRETS {
        out[pending_f::SLEW + j] = a.slew_sign(j);
        out[pending_f::FIRE + j] = f32::from(a.fire[j]);
    }
    out[pending_f::POWER] = f32::from(a.power) / f32::from(POWER_MAX);
    clamp_record(out);
}

/// Fixed-capacity smallest-K: keeps the `K` smallest `(key, index)` pairs in
/// ascending order. Ties keep the lower index because candidates arrive in index
/// order and only a strictly smaller key displaces an earlier entry.
struct SmallestK<const K: usize> {
    idx: [usize; K],
    key: [f32; K],
    len: usize,
}

impl<const K: usize> SmallestK<K> {
    fn new() -> Self {
        SmallestK {
            idx: [0; K],
            key: [0.0; K],
            len: 0,
        }
    }

    /// Offer candidate `i` with key `k`; must be called in increasing `i`.
    fn offer(&mut self, i: usize, k: f32) {
        // Position = number of kept entries with key <= k (stable for ties).
        let mut pos = 0;
        while pos < self.len && self.key[pos] <= k {
            pos += 1;
        }
        if pos >= K {
            return;
        }
        let end = if self.len < K { self.len } else { K - 1 };
        let mut j = end;
        while j > pos {
            self.idx[j] = self.idx[j - 1];
            self.key[j] = self.key[j - 1];
            j -= 1;
        }
        self.idx[pos] = i;
        self.key[pos] = k;
        if self.len < K {
            self.len += 1;
        }
    }

    fn indices(&self) -> &[usize] {
        &self.idx[..self.len]
    }
}

/// Sort key that keeps selection deterministic on a corrupt state: NaN sorts last.
#[inline]
fn order_key(k: f32) -> f32 {
    if k.is_nan() { f32::INFINITY } else { k }
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
            write_thruster(hull, t, me.thrust_level[j], &mut out[o..o + THRUSTER_W]);
        }

        let mut extras = [0.0f32; TURRET_EXTRA_W];
        for j in 0..hull.turrets.len().min(N_TURRET_SLOTS) {
            let o = TURRETS_OFF + j * TURRET_W;
            write_turret(cat, me, j, &mut out[o..o + TURRET_W]);
            write_turret_extras(cat, me, j, radius, &mut extras);
            out[TURRET_ARC_OFF + j] = extras[0];
            out[TURRET_RANGE_OFF + j] = extras[1];
        }

        let mut near_ships = SmallestK::<N_NEAR_SHIPS>::new();
        for (i, other) in self.ships.iter().enumerate() {
            if i != ship as usize && other.active() {
                near_ships.offer(i, order_key((other.pos - me.pos).length()));
            }
        }
        for (k, &i) in near_ships.indices().iter().enumerate() {
            let o = SHIPS_OFF + k * SHIP_W;
            write_ship(cat, me, &self.ships[i], radius, &mut out[o..o + SHIP_W]);
        }

        let mut threats = SmallestK::<N_NEAR_PROJ>::new();
        for (i, p) in self.projectiles.iter().enumerate() {
            if p.alive && p.team != me.team {
                threats.offer(i, order_key(threat(me, p).score));
            }
        }
        for (k, &i) in threats.indices().iter().enumerate() {
            let o = PROJ_OFF + k * PROJ_W;
            let p = &self.projectiles[i];
            write_projectile(me, p, threat(me, p), radius, &mut out[o..o + PROJ_W]);
        }

        let d = usize::from(me.reaction_ticks).min(N_PENDING_SLOTS);
        for (k, a) in me.queue[..d].iter().enumerate() {
            let o = PENDING_OFF + k * PENDING_W;
            write_pending(a, &mut out[o..o + PENDING_W]);
        }
    }
}
