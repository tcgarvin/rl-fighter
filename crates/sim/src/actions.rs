//! ShipAction, the flat i8 action row encoding, and action masks (SIM_SPEC §7.1).
//!
//! Row layout (`ACTION_WIDTH = 21` `i8` per ship slot):
//!
//! ```text
//! [0..8)   thruster throttle  {0,1,2}  decrease, hold, increase the thrust level (v2)
//! [8..14)  turret slew        {0,1,2}  left (CCW), hold, right (CW)
//! [14..20) turret fire        {0,1}
//! [20]     power target       {0..6}   index into power::POWER_TARGETS
//! ```
//!
//! Out-of-range values are clamped, never errors: the policy samples from fixed
//! categorical heads and a bad row should degrade, not crash a batch.
//!
//! Stage 3 (v2) runs every chosen action through a per-ship reaction FIFO of
//! `reaction_ticks` entries: an action set after the step that ends at tick `t` is
//! applied on the step that ends at tick `t + 1 + d`. Actions that would land in the
//! control lock, or that were chosen for a ship that is not present, are replaced by
//! `IDLE` on the way in, so a row with `act_mask == false` never touches the state.

use crate::data::{Catalogue, HullDef};
use crate::hash::{StateHash, StateHasher};
use crate::physics::ramp_level;
use crate::power::{self, N_POWER_TARGETS};
use crate::state::{MAX_THRUSTERS, MAX_TURRETS, Match, Ship, ShipIdx};

pub const THROTTLE_OFFSET: usize = 0;
pub const SLEW_OFFSET: usize = THROTTLE_OFFSET + MAX_THRUSTERS;
pub const FIRE_OFFSET: usize = SLEW_OFFSET + MAX_TURRETS;
pub const POWER_OFFSET: usize = FIRE_OFFSET + MAX_TURRETS;
pub const ACTION_WIDTH: usize = POWER_OFFSET + 1;

/// Highest valid value of each head.
pub const THROTTLE_MAX: u8 = 2;
pub const SLEW_MAX: u8 = 2;
pub const FIRE_MAX: u8 = 1;
pub const POWER_MAX: u8 = (N_POWER_TARGETS - 1) as u8;

/// Throttle head values (v2): a rate command on the thruster's `thrust_level`.
pub const THROTTLE_DECREASE: u8 = 0;
pub const THROTTLE_HOLD: u8 = 1;
pub const THROTTLE_INCREASE: u8 = 2;

/// Slew head value that holds the turret still.
pub const SLEW_HOLD: u8 = 1;

/// One ship's decoded action. The all-zero default is "every level down, slew left,
/// no fire, even power"; use [`ShipAction::IDLE`] for a no-op.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct ShipAction {
    pub throttle: [u8; MAX_THRUSTERS],
    pub slew: [u8; MAX_TURRETS],
    pub fire: [u8; MAX_TURRETS],
    pub power: u8,
}

fn clamp_head(v: i8, max: u8) -> u8 {
    // i8 → i16 so negative values clamp to 0 instead of wrapping.
    (v as i16).clamp(0, max as i16) as u8
}

impl ShipAction {
    /// Thrust levels held, turrets held, no fire, power index 0.
    pub const IDLE: ShipAction = ShipAction {
        throttle: [THROTTLE_HOLD; MAX_THRUSTERS],
        slew: [SLEW_HOLD; MAX_TURRETS],
        fire: [0; MAX_TURRETS],
        power: 0,
    };

    /// What a control-locked (or static, or not present) ship applies in stage 3:
    /// every level ramps down, turrets hold, no fire. Its power head means "keep":
    /// stage 3 leaves `power_target` unchanged for a locked ship, so the `0` here is
    /// never read. Sim-internal; never a policy or BC label.
    pub const LOCKED: ShipAction = ShipAction {
        throttle: [THROTTLE_DECREASE; MAX_THRUSTERS],
        slew: [SLEW_HOLD; MAX_TURRETS],
        fire: [0; MAX_TURRETS],
        power: 0,
    };

    /// Decode a row of `ACTION_WIDTH` values, clamping each head into range.
    ///
    /// Panics if `row.len() != ACTION_WIDTH` (a caller bug, not bad data).
    pub fn from_row(row: &[i8]) -> ShipAction {
        assert_eq!(row.len(), ACTION_WIDTH, "action row length");
        let mut a = ShipAction::default();
        for (i, t) in a.throttle.iter_mut().enumerate() {
            *t = clamp_head(row[THROTTLE_OFFSET + i], THROTTLE_MAX);
        }
        for (i, s) in a.slew.iter_mut().enumerate() {
            *s = clamp_head(row[SLEW_OFFSET + i], SLEW_MAX);
        }
        for (i, f) in a.fire.iter_mut().enumerate() {
            *f = clamp_head(row[FIRE_OFFSET + i], FIRE_MAX);
        }
        a.power = clamp_head(row[POWER_OFFSET], POWER_MAX);
        a
    }

    /// Encode into a row of `ACTION_WIDTH` values. Values are clamped first, so
    /// `from_row(to_row(a))` is `a` for any in-range action.
    ///
    /// Panics if `row.len() != ACTION_WIDTH`.
    pub fn to_row(&self, row: &mut [i8]) {
        assert_eq!(row.len(), ACTION_WIDTH, "action row length");
        for (i, &t) in self.throttle.iter().enumerate() {
            row[THROTTLE_OFFSET + i] = t.min(THROTTLE_MAX) as i8;
        }
        for (i, &s) in self.slew.iter().enumerate() {
            row[SLEW_OFFSET + i] = s.min(SLEW_MAX) as i8;
        }
        for (i, &f) in self.fire.iter().enumerate() {
            row[FIRE_OFFSET + i] = f.min(FIRE_MAX) as i8;
        }
        row[POWER_OFFSET] = self.power.min(POWER_MAX) as i8;
    }

    /// Slew head of turret `j` as a signed rate factor: left (0) → +1 (CCW, toward
    /// port), hold (1) → 0, right (2) → -1.
    pub fn slew_sign(&self, j: usize) -> f32 {
        match self.slew[j] {
            0 => 1.0,
            SLEW_HOLD => 0.0,
            _ => -1.0,
        }
    }

    /// The action as it may enter the reaction queue: every head clamped, throttle
    /// slots beyond the hull's thrusters set to `HOLD`, turret slots beyond its
    /// turrets to `SLEW_HOLD` and no fire. Idempotent; `IDLE` sanitises to itself.
    pub fn sanitized(&self, hull: &HullDef) -> ShipAction {
        let mut a = *self;
        for (i, t) in a.throttle.iter_mut().enumerate() {
            *t = if i < hull.thrusters.len() {
                (*t).min(THROTTLE_MAX)
            } else {
                THROTTLE_HOLD
            };
        }
        for (j, (s, f)) in a.slew.iter_mut().zip(a.fire.iter_mut()).enumerate() {
            let used = j < hull.turrets.len();
            *s = if used { (*s).min(SLEW_MAX) } else { SLEW_HOLD };
            *f = if used { (*f).min(FIRE_MAX) } else { 0 };
        }
        a.power = a.power.min(POWER_MAX);
        a
    }
}

/// Hashed as its `ACTION_WIDTH` row values in row order (SIM_SPEC §12).
impl StateHash for ShipAction {
    fn hash_into(&self, h: &mut StateHasher) {
        h.write_bytes(&self.throttle);
        h.write_bytes(&self.slew);
        h.write_bytes(&self.fire);
        h.write_u8(self.power);
    }
}

/// Thruster slots the hull actually has.
pub fn thruster_mask(hull: &HullDef) -> [bool; MAX_THRUSTERS] {
    core::array::from_fn(|i| i < hull.thrusters.len())
}

/// Turret slots the hull actually has.
pub fn turret_mask(hull: &HullDef) -> [bool; MAX_TURRETS] {
    core::array::from_fn(|j| j < hull.turrets.len())
}

/// Turret slots that are fixed guns (arc 0): their slew head is meaningless.
pub fn fixed_turret(hull: &HullDef) -> [bool; MAX_TURRETS] {
    core::array::from_fn(|j| hull.turrets.get(j).is_some_and(|t| t.arc == 0.0))
}

/// SIM_SPEC §7.1 (v2): whether an action chosen now, with the match at post-step
/// tick `tick`, will be applied. It is applied on the step that ends at
/// `tick + 1 + d` (`d = ship.reaction_ticks`), so it counts iff the ship is alive
/// and present now and that tick is past the control lock. When this is false the
/// row has no effect on the simulation at all (stage 3 enqueues `IDLE` instead).
pub fn act_mask(ship: &Ship, tick: u32) -> bool {
    let applies_on = tick + 1 + u32::from(ship.reaction_ticks);
    ship.alive && ship.present && applies_on >= ship.control_lock_until
}

impl Match {
    /// Choose `ship`'s action now; stage 3 of the next step enqueues it (or applies it
    /// directly when the ship has no reaction delay). Panics on an out-of-range slot.
    pub fn set_action(&mut self, ship: ShipIdx, a: ShipAction) {
        assert!(
            (ship as usize) < self.ships.len(),
            "ship slot {ship} out of range (match has {})",
            self.ships.len()
        );
        self.pending[ship as usize] = a;
    }

    /// [`act_mask`] for slot `ship` at the current tick. Panics on an out-of-range slot.
    pub fn act_mask(&self, ship: ShipIdx) -> bool {
        act_mask(&self.ships[ship as usize], self.tick)
    }

    /// Stage 3 (SIM_SPEC §5, v2): for every alive ship in slot order, dequeue the
    /// action that applies this tick and enqueue the one chosen now (sanitised, or
    /// `IDLE` if it would land in the control lock or the ship is not present); a
    /// locked, static or not-present ship applies `LOCKED`, otherwise the action sets
    /// `power_target`; then ramp the thrust levels and record the action in
    /// `applied` for stages 6–7. Dead ships are skipped entirely.
    pub fn apply_actions(&mut self, cat: &Catalogue) {
        let tick = self.tick;
        for ship in self.ships.iter_mut().filter(|s| s.alive) {
            let hull = cat.hull(ship.hull);
            let slot = ship.slot as usize;
            let d = usize::from(ship.reaction_ticks);
            let lands_on = tick + u32::from(ship.reaction_ticks);
            let chosen = if ship.active() && lands_on >= ship.control_lock_until {
                self.pending[slot].sanitized(hull)
            } else {
                ShipAction::IDLE
            };
            let mut a = if d == 0 {
                chosen
            } else {
                let head = ship.queue[0];
                ship.queue.copy_within(1..d, 0);
                ship.queue[d - 1] = chosen;
                head
            };

            let locked = ship.control_locked(tick) || hull.is_static || !ship.active();
            if locked {
                a = ShipAction::LOCKED;
            } else {
                ship.power_target = power::target_for(hull, usize::from(a.power));
            }
            let n = hull.thrusters.len();
            for (level, &head) in ship.thrust_level[..n].iter_mut().zip(&a.throttle[..n]) {
                *level = ramp_level(*level, head);
            }
            self.applied[slot] = a;
        }
    }
}
