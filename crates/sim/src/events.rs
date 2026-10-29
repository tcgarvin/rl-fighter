//! Event enum, EventBuf and the flat event encoding (SIM_SPEC §9), plus the per-hit
//! `HitRecord` attribution (§5.3, §8).
//!
//! Events are presentation and debugging output: nothing in the sim reads them back,
//! so dropping excess events never changes the simulation (they are not hashed).

use crate::math::Vec2;
use crate::state::{MAX_EVENTS, MAX_HITS, MAX_SHIPS, Match, ShipIdx};

/// Floats per event in the flat FFI encoding.
pub const EVENT_STRIDE: usize = 8;

/// Flat-encoding kind codes, in `Event` declaration order.
pub const KIND_FIRE: u8 = 0;
pub const KIND_BEAM: u8 = 1;
pub const KIND_HIT: u8 = 2;
pub const KIND_SHIELD_HIT: u8 = 3;
pub const KIND_BURST: u8 = 4;
pub const KIND_DEATH: u8 = 5;
pub const KIND_ARRIVAL: u8 = 6;

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Event {
    /// A turret fired (every weapon kind, beams included).
    Fire {
        ship: u8,
        turret: u8,
        weapon: u16,
        pos: Vec2,
        angle: f32,
    },
    /// A beam was drawn from the muzzle to its hit point (or full range on a miss).
    Beam {
        ship: u8,
        from: Vec2,
        to: Vec2,
        hit: bool,
    },
    /// Hull damage at `pos`. `damage` is after armour; `mult` is the armour
    /// multiplier that produced it (1.0 on uniform hulls; < 1 glancing, > 1 raking).
    Hit {
        target: u8,
        shooter: u8,
        pos: Vec2,
        damage: f32,
        mult: f32,
    },
    /// A shield absorbed a hit; `pos` is on the shield bubble, `normal` is unit and
    /// points outward from the target's centre.
    ShieldHit {
        target: u8,
        shooter: u8,
        pos: Vec2,
        normal: Vec2,
        depleted: bool,
    },
    /// Flak fuse burst or torpedo impact.
    Burst {
        team: u8,
        pos: Vec2,
        radius: f32,
    },
    Death {
        ship: u8,
        pos: Vec2,
    },
    Arrival {
        ship: u8,
        pos: Vec2,
        heading: f32,
    },
}

impl Event {
    /// Flat-encoding kind code (0..6 in declaration order).
    pub fn kind(&self) -> u8 {
        match self {
            Event::Fire { .. } => KIND_FIRE,
            Event::Beam { .. } => KIND_BEAM,
            Event::Hit { .. } => KIND_HIT,
            Event::ShieldHit { .. } => KIND_SHIELD_HIT,
            Event::Burst { .. } => KIND_BURST,
            Event::Death { .. } => KIND_DEATH,
            Event::Arrival { .. } => KIND_ARRIVAL,
        }
    }

    /// `[kind, a, b, x, y, nx_or_x2, ny_or_y2, extra]` (SIM_SPEC §9). Fields a kind
    /// does not use are 0. `Fire` carries its weapon id in slot 5; `Beam` carries
    /// `to` in slots 5–6 and `hit` as 0/1 in `extra`; `Hit` carries `mult` in slot 5.
    pub fn encode(&self) -> [f32; EVENT_STRIDE] {
        let k = f32::from(self.kind());
        let b = |v: bool| if v { 1.0 } else { 0.0 };
        match *self {
            Event::Fire {
                ship,
                turret,
                weapon,
                pos,
                angle,
            } => [
                k,
                f32::from(ship),
                f32::from(turret),
                pos.x,
                pos.y,
                f32::from(weapon),
                0.0,
                angle,
            ],
            Event::Beam {
                ship,
                from,
                to,
                hit,
            } => [k, f32::from(ship), 0.0, from.x, from.y, to.x, to.y, b(hit)],
            Event::Hit {
                target,
                shooter,
                pos,
                damage,
                mult,
            } => [
                k,
                f32::from(target),
                f32::from(shooter),
                pos.x,
                pos.y,
                mult,
                0.0,
                damage,
            ],
            Event::ShieldHit {
                target,
                shooter,
                pos,
                normal,
                depleted,
            } => [
                k,
                f32::from(target),
                f32::from(shooter),
                pos.x,
                pos.y,
                normal.x,
                normal.y,
                b(depleted),
            ],
            Event::Burst { team, pos, radius } => {
                [k, f32::from(team), 0.0, pos.x, pos.y, 0.0, 0.0, radius]
            }
            Event::Death { ship, pos } => [k, f32::from(ship), 0.0, pos.x, pos.y, 0.0, 0.0, 0.0],
            Event::Arrival { ship, pos, heading } => {
                [k, f32::from(ship), 0.0, pos.x, pos.y, 0.0, 0.0, heading]
            }
        }
    }
}

/// Events of one step, at most `MAX_EVENTS`; excess is dropped and counted.
#[derive(Clone, Debug, Default)]
pub struct EventBuf {
    events: Vec<Event>,
    /// Events dropped because the buffer was full, since the last `clear`.
    pub dropped: u32,
}

impl EventBuf {
    pub fn new() -> Self {
        EventBuf {
            events: Vec::with_capacity(MAX_EVENTS),
            dropped: 0,
        }
    }

    /// Append `e`, or count it as dropped when `MAX_EVENTS` are already recorded.
    pub fn push(&mut self, e: Event) {
        if self.events.len() < MAX_EVENTS {
            self.events.push(e);
        } else {
            self.dropped += 1;
        }
    }

    pub fn clear(&mut self) {
        self.events.clear();
        self.dropped = 0;
    }

    pub fn as_slice(&self) -> &[Event] {
        &self.events
    }

    pub fn len(&self) -> usize {
        self.events.len()
    }

    pub fn is_empty(&self) -> bool {
        self.events.is_empty()
    }

    /// Replace `out` with the flat encoding, `EVENT_STRIDE` floats per event.
    pub fn encode_into(&self, out: &mut Vec<f32>) {
        out.clear();
        for e in &self.events {
            out.extend_from_slice(&e.encode());
        }
    }
}

/// One damage application, for reward and retroactive credit (SIM_SPEC §5.3, §8).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct HitRecord {
    pub shooter: ShipIdx,
    pub target: ShipIdx,
    /// Damage actually applied: the raw weapon damage for a shield hit (before
    /// absorption scaling), the armour-scaled amount for a hull hit (SIM_SPEC §5.3).
    pub damage: f32,
    /// Tick the shot was fired (the current tick for beams).
    pub fire_tick: u32,
    /// Post-step tick of the obs the firing action was chosen from (v2, §8).
    pub decision_tick: u32,
    /// The shield took it (no hull damage).
    pub shield: bool,
}

impl Match {
    /// Events of the last step.
    pub fn events(&self) -> &[Event] {
        self.events.as_slice()
    }

    /// Hits landed during the last step, in application order.
    pub fn hits(&self) -> &[HitRecord] {
        &self.hits
    }

    /// Record a hit, or count it in `dropped_hits` past `MAX_HITS`.
    pub fn push_hit(&mut self, h: HitRecord) {
        if self.hits.len() < MAX_HITS {
            self.hits.push(h);
        } else {
            self.dropped_hits += 1;
        }
    }

    /// Stage 1 helper (called by `Match::step`): clear the per-step combat outputs
    /// this module owns: events, hits and `shots_fired`. `dropped_hits` is a running
    /// total and is not reset.
    pub fn clear_combat_outputs(&mut self) {
        self.events.clear();
        self.hits.clear();
        self.shots_fired = [0; MAX_SHIPS];
    }
}
