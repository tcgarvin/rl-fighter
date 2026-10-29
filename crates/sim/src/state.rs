//! Match, Ship, Projectile, MatchPhase and the MAX_* capacity constants (SIM_SPEC §3).
//!
//! Layout is AoS per match: a match owns its ships, a fixed projectile pool and the
//! per-step outputs. Modules for later stages (weapons, events, rewards, obs) read and
//! write these fields directly; this file only defines the shapes, constructors and
//! the determinism hash.

use crate::actions::ShipAction;
use crate::data::{HullDef, HullId, WeaponId, WeaponKind};
use crate::events::{EventBuf, HitRecord};
use crate::hash::{StateHash, StateHasher};
use crate::math::Vec2;
use crate::power;
use crate::rng::Pcg32;
use crate::setup::MatchConfig;

/// Ships per match, both teams together.
pub const MAX_SHIPS: usize = 8;
/// Thrusters per hull (the carrier has 7).
pub const MAX_THRUSTERS: usize = 8;
/// Turrets per hull (the station has 6).
pub const MAX_TURRETS: usize = 6;
/// Projectile pool per match; spawning overwrites the oldest slot.
pub const MAX_PROJECTILES: usize = 256;
/// Events recorded per step; excess is dropped and counted.
pub const MAX_EVENTS: usize = 512;
/// HitRecords recorded per step; excess is dropped and counted.
pub const MAX_HITS: usize = 64;
/// Reaction-queue capacity: the largest allowed `reaction_ticks` (v2).
pub const MAX_REACTION_TICKS: usize = 4;

/// Ship slot within a match.
pub type ShipIdx = u8;
/// "No ship" for `ShipIdx` fields (parent, torpedo target, ...).
pub const NONE: ShipIdx = u8::MAX;

/// Ticks value meaning "never" (e.g. `last_hit_tick` before the first hit).
pub const NEVER: u32 = u32::MAX;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum MatchPhase {
    #[default]
    Running,
    Over,
}

impl MatchPhase {
    pub fn index(self) -> u8 {
        self as u8
    }
}

/// How a ship is attached to its `parent`. Reserved for M5+ (bays, mounts, tethers);
/// always `None` in M1. Ships with `attach != None` are not present.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Attach {
    #[default]
    None,
    Docked,
    Mounted,
    Tethered,
}

impl Attach {
    pub fn index(self) -> u8 {
        self as u8
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Ship {
    pub hull: HullId,
    pub team: u8,
    pub slot: ShipIdx,
    pub pos: Vec2,
    pub vel: Vec2,
    pub heading: f32,
    pub omega: f32,
    pub hp: f32,
    pub shield: f32,
    /// Tick of the most recent damage; `NEVER` before the first hit.
    pub last_hit_tick: u32,
    pub alive: bool,
    pub present: bool,
    pub arrive_tick: u32,
    /// Stage 3 applies `ShipAction::LOCKED` while `tick < control_lock_until`.
    pub control_lock_until: u32,
    /// Per thruster: continuous level in `[0, 1]`, ramped by the throttle heads (v2).
    /// Slots beyond the hull's thrusters stay 0.
    pub thrust_level: [f32; MAX_THRUSTERS],
    /// Body-frame turret angles, radians.
    pub turret_angle: [f32; MAX_TURRETS],
    /// Seconds until each turret may fire again.
    pub turret_cooldown: [f32; MAX_TURRETS],
    /// Current power shares `[shields, engines, weapons]`, summing to 1.
    pub power: [f32; 3],
    /// Split `power` slews toward (set from the action's power head).
    pub power_target: [f32; 3],
    /// Reserved for M5+: always `NONE` in M1.
    pub parent: ShipIdx,
    /// Reserved for M5+: always `Attach::None` in M1.
    pub attach: Attach,
    /// Effective reaction delay `d` in ticks (hull override or match config), at most
    /// `MAX_REACTION_TICKS` (v2).
    pub reaction_ticks: u8,
    /// Reaction FIFO (v2): `queue[0]` applies on the next step; slots `>= d` stay IDLE.
    pub queue: [ShipAction; MAX_REACTION_TICKS],
}

impl Ship {
    /// A full-health, not-yet-present ship at the origin with the initial power split
    /// (table index 0), turrets at rest, every thrust level 0 and an all-`IDLE`
    /// reaction queue of delay `reaction_ticks`. Placement fills `pos`, `heading`,
    /// `arrive_tick` and `present`.
    pub fn new(
        hull_def: &HullDef,
        hull: HullId,
        team: u8,
        slot: ShipIdx,
        reaction_ticks: u8,
    ) -> Ship {
        let mut turret_angle = [0.0; MAX_TURRETS];
        for (angle, t) in turret_angle.iter_mut().zip(&hull_def.turrets) {
            *angle = t.rest;
        }
        let split = power::target_for(hull_def, 0);
        Ship {
            hull,
            team,
            slot,
            pos: Vec2::ZERO,
            vel: Vec2::ZERO,
            heading: 0.0,
            omega: 0.0,
            hp: hull_def.hp,
            shield: hull_def.shield.map_or(0.0, |s| s.hp),
            last_hit_tick: NEVER,
            alive: true,
            present: false,
            arrive_tick: 0,
            control_lock_until: 0,
            thrust_level: [0.0; MAX_THRUSTERS],
            turret_angle,
            turret_cooldown: [0.0; MAX_TURRETS],
            power: split,
            power_target: split,
            parent: NONE,
            attach: Attach::None,
            reaction_ticks,
            queue: [ShipAction::IDLE; MAX_REACTION_TICKS],
        }
    }

    /// `alive && present`: the ship takes part in physics, hits, collisions and obs.
    #[inline]
    pub fn active(&self) -> bool {
        self.alive && self.present
    }

    #[inline]
    pub fn control_locked(&self, tick: u32) -> bool {
        tick < self.control_lock_until
    }

    /// Body-frame point to world frame.
    #[inline]
    pub fn to_world(&self, p: Vec2) -> Vec2 {
        p.rotated(self.heading) + self.pos
    }
}

impl StateHash for Ship {
    fn hash_into(&self, h: &mut StateHasher) {
        h.write_u16(self.hull);
        h.write_u8(self.team);
        h.write_u8(self.slot);
        h.write_vec2(self.pos);
        h.write_vec2(self.vel);
        h.write_f32(self.heading);
        h.write_f32(self.omega);
        h.write_f32(self.hp);
        h.write_f32(self.shield);
        h.write_u32(self.last_hit_tick);
        h.write_bool(self.alive);
        h.write_bool(self.present);
        h.write_u32(self.arrive_tick);
        h.write_u32(self.control_lock_until);
        self.thrust_level.hash_into(h);
        self.turret_angle.hash_into(h);
        self.turret_cooldown.hash_into(h);
        self.power.hash_into(h);
        self.power_target.hash_into(h);
        h.write_u8(self.parent);
        h.write_u8(self.attach.index());
        h.write_u8(self.reaction_ticks);
        self.queue.hash_into(h);
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Projectile {
    pub alive: bool,
    pub kind: WeaponKind,
    /// Catalogue weapon that fired it (flak burst radius, torpedo turn rate, ...).
    pub weapon: WeaponId,
    pub team: u8,
    pub owner: ShipIdx,
    pub pos: Vec2,
    pub vel: Vec2,
    pub speed: f32,
    pub damage: f32,
    pub life_ticks: u32,
    /// Tick the shot was fired.
    pub fire_tick: u32,
    /// Post-step tick of the obs the firing action was chosen from,
    /// `fire_tick - 1 - d_shooter` (v2); hit credit goes back to this step (§8).
    pub decision_tick: u32,
    /// Torpedo lock; `NONE` for other kinds or no lock.
    pub target: ShipIdx,
}

impl Projectile {
    /// An empty pool slot.
    pub const DEAD: Projectile = Projectile {
        alive: false,
        kind: WeaponKind::Bullet,
        weapon: 0,
        team: 0,
        owner: NONE,
        pos: Vec2::ZERO,
        vel: Vec2::ZERO,
        speed: 0.0,
        damage: 0.0,
        life_ticks: 0,
        fire_tick: 0,
        decision_tick: 0,
        target: NONE,
    };
}

impl Default for Projectile {
    fn default() -> Self {
        Projectile::DEAD
    }
}

impl StateHash for Projectile {
    fn hash_into(&self, h: &mut StateHasher) {
        h.write_bool(self.alive);
        h.write_u8(self.kind.index() as u8);
        h.write_u16(self.weapon);
        h.write_u8(self.team);
        h.write_u8(self.owner);
        h.write_vec2(self.pos);
        h.write_vec2(self.vel);
        h.write_f32(self.speed);
        h.write_f32(self.damage);
        h.write_u32(self.life_ticks);
        h.write_u32(self.fire_tick);
        h.write_u32(self.decision_tick);
        h.write_u8(self.target);
    }
}

/// One match: ships, projectile pool, pending actions and per-step outputs.
#[derive(Clone, Debug)]
pub struct Match {
    pub cfg: MatchConfig,
    pub tick: u32,
    pub rng: Pcg32,
    pub phase: MatchPhase,
    /// -1 draw, 0/1 winning team, -2 not over.
    pub winner: i8,
    /// Team 0 slots first, then team 1; `ships[i].slot == i`.
    pub ships: Vec<Ship>,
    pub projectiles: [Projectile; MAX_PROJECTILES],
    /// Next pool slot to (over)write.
    pub proj_next: usize,
    /// `set_action` input per slot: the action chosen now, enqueued (or, with no
    /// reaction delay, applied) by the next step's stage 3. Not hashed.
    pub pending: [ShipAction; MAX_SHIPS],
    /// Per slot, the action stages 5–7 used in the last step: dequeued, sanitised,
    /// `LOCKED` while locked (v2). Not hashed: output only.
    pub applied: [ShipAction; MAX_SHIPS],
    /// Events of the last step (not hashed: output only).
    pub events: EventBuf,
    /// Damage applications of the last step, at most `MAX_HITS` (not hashed).
    pub hits: Vec<HitRecord>,
    /// Shots actually fired per slot in the last step (fire-cost reward, §8).
    pub shots_fired: [u16; MAX_SHIPS],
    /// HitRecords that did not fit in the last step's `MAX_HITS`.
    pub dropped_hits: u32,
    /// Per-slot rewards of the last step.
    pub rewards: [f32; MAX_SHIPS],
    /// Per slot: pushed by the arena boundary in the last step (stage 11).
    pub outside_arena: [bool; MAX_SHIPS],
    /// v3, per slot: hull damage taken from ship-ship collisions in the last step
    /// (after impact arcs; stage 10). Output only, not hashed; read by rewards.
    pub collision_damage: [f32; MAX_SHIPS],
    /// v3, per slot: raw collision damage a raised shield took in the last step
    /// (before absorption scaling, like a shield `HitRecord`). Output only.
    pub collision_shield_damage: [f32; MAX_SHIPS],
    /// Reserved for bays: ships waiting to launch, per team (empty in M1).
    pub reserves: [Vec<ShipIdx>; 2],
}

/// `winner` before the match is over.
pub const WINNER_NONE: i8 = -2;
/// `winner` for a draw.
pub const WINNER_DRAW: i8 = -1;

impl Match {
    pub fn tick(&self) -> u32 {
        self.tick
    }

    pub fn phase(&self) -> MatchPhase {
        self.phase
    }

    pub fn winner(&self) -> i8 {
        self.winner
    }

    pub fn ships(&self) -> &[Ship] {
        &self.ships
    }

    pub fn projectiles(&self) -> &[Projectile] {
        &self.projectiles
    }

    /// Rewards of the last step, one per ship.
    pub fn rewards(&self) -> &[f32] {
        &self.rewards[..self.ships.len()]
    }

    /// FNV-1a 64 over the simulation state in SIM_SPEC §12 order: tick, rng state,
    /// every ship, every projectile pool slot, `proj_next`, phase, winner.
    pub fn state_hash(&self) -> u64 {
        let mut h = StateHasher::new();
        h.write_u32(self.tick);
        self.rng.hash_into(&mut h);
        self.ships.as_slice().hash_into(&mut h);
        self.projectiles.hash_into(&mut h);
        h.write_usize(self.proj_next);
        h.write_u8(self.phase.index());
        h.write_i8(self.winner);
        h.finish()
    }
}
