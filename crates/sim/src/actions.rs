//! ShipAction, the flat i8 action row encoding, and action masks (SIM_SPEC §7.1).
//!
//! Row layout (`ACTION_WIDTH = 21` `i8` per ship slot):
//!
//! ```text
//! [0..8)   thruster throttle  {0,1,2}  off, half, full
//! [8..14)  turret slew        {0,1,2}  left (CCW), hold, right (CW)
//! [14..20) turret fire        {0,1}
//! [20]     power target       {0..6}   index into power::POWER_TARGETS
//! ```
//!
//! Out-of-range values are clamped, never errors: the policy samples from fixed
//! categorical heads and a bad row should degrade, not crash a batch.

use crate::data::{Catalogue, HullDef};
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

/// Slew head value that holds the turret still.
pub const SLEW_HOLD: u8 = 1;

/// One ship's decoded action. The all-zero default is "no thrust, slew left, no
/// fire, even power"; use [`ShipAction::IDLE`] for a turret-holding no-op.
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
    /// No thrust, turrets held, no fire, power index 0.
    pub const IDLE: ShipAction = ShipAction {
        throttle: [0; MAX_THRUSTERS],
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

    /// The action as the sim applies it in stage 3: every head clamped, slots beyond
    /// the hull's thrusters/turrets zeroed, and throttle/fire forced off when
    /// `locked` (control lock or static hull). Power and slew still apply.
    pub fn sanitized(&self, hull: &HullDef, locked: bool) -> ShipAction {
        let mut a = *self;
        for (i, t) in a.throttle.iter_mut().enumerate() {
            *t = if locked || i >= hull.thrusters.len() {
                0
            } else {
                (*t).min(THROTTLE_MAX)
            };
        }
        for (j, (s, f)) in a.slew.iter_mut().zip(a.fire.iter_mut()).enumerate() {
            let used = j < hull.turrets.len();
            *s = if used { (*s).min(SLEW_MAX) } else { SLEW_HOLD };
            *f = if locked || !used {
                0
            } else {
                (*f).min(FIRE_MAX)
            };
        }
        a.power = a.power.min(POWER_MAX);
        a
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

/// Whether the ship's action counts this tick: present, alive, not control-locked.
/// Actions of masked ships are ignored by the sim and should be excluded from the loss.
pub fn act_mask(ship: &Ship, tick: u32) -> bool {
    ship.active() && !ship.control_locked(tick)
}

impl Match {
    /// Set the action applied on the next step. Panics on an out-of-range slot.
    pub fn set_action(&mut self, ship: ShipIdx, a: ShipAction) {
        assert!(
            (ship as usize) < self.ships.len(),
            "ship slot {ship} out of range (match has {})",
            self.ships.len()
        );
        self.pending[ship as usize] = a;
    }

    /// Stage 3 (SIM_SPEC §5): for each active ship, sanitise the pending action
    /// (control lock / static hull force throttle and fire to 0), copy the throttles
    /// into the ship and set its power target. Inactive ships keep their state; their
    /// pending action is left untouched.
    pub fn apply_actions(&mut self, cat: &Catalogue) {
        let tick = self.tick;
        for ship in self.ships.iter_mut().filter(|s| s.active()) {
            let hull = cat.hull(ship.hull);
            let locked = ship.control_locked(tick) || hull.is_static;
            let slot = ship.slot as usize;
            let a = self.pending[slot].sanitized(hull, locked);
            self.pending[slot] = a;
            ship.throttle = a.throttle;
            ship.power_target = power::target_for(hull, a.power as usize);
        }
    }
}
