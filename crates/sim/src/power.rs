//! Power-split target table, slew, and per-system multipliers (SIM_SPEC §5.2).
//!
//! `power` is `[shields, engines, weapons]` and always sums to 1. The action's power
//! head picks a target split from a fixed menu; the sim only slews toward it, at
//! 0.45 share per second on the largest gap. Shieldless hulls use the two-way variant
//! of each entry and keep `power[0] == 0`.

use crate::DT;
use crate::data::HullDef;
use crate::state::Ship;

pub const SHIELDS: usize = 0;
pub const ENGINES: usize = 1;
pub const WEAPONS: usize = 2;

pub const N_POWER_TARGETS: usize = 7;

/// Share per second the largest component of the split moves toward its target.
pub const POWER_SLEW_RATE: f32 = 0.45;

/// Largest share a system may hold on a two-way hull (shares 0.2..0.8).
const TWO_WAY_CAP: f32 = 0.8;

const THIRD: f32 = 1.0 / 3.0;

/// Three-way targets `[shields, engines, weapons]`, by power head index.
pub const POWER_TARGETS: [[f32; 3]; N_POWER_TARGETS] = [
    [THIRD, THIRD, THIRD],
    [0.6, 0.2, 0.2],
    [0.2, 0.6, 0.2],
    [0.2, 0.2, 0.6],
    [0.4, 0.4, 0.2],
    [0.4, 0.2, 0.4],
    [0.2, 0.4, 0.4],
];

/// Two-way target for a shieldless hull: drop shields, renormalise engines/weapons,
/// clamp each to `[0.2, 0.8]`. Index 0 is the even split `(0, 0.5, 0.5)`.
///
/// Panics if `idx >= N_POWER_TARGETS`.
pub fn two_way_target(idx: usize) -> [f32; 3] {
    if idx == 0 {
        // Exact even split, rather than (1/3)/(2/3) which rounds off 0.5.
        return [0.0, 0.5, 0.5];
    }
    let [_, e, w] = POWER_TARGETS[idx];
    let e = (e / (e + w)).clamp(1.0 - TWO_WAY_CAP, TWO_WAY_CAP);
    [0.0, e, 1.0 - e]
}

/// The target split for `hull` at power head `idx` (three- or two-way by shield).
pub fn target_for(hull: &HullDef, idx: usize) -> [f32; 3] {
    if hull.n_power_systems == 3 {
        POWER_TARGETS[idx]
    } else {
        two_way_target(idx)
    }
}

/// Multiplier for one system: `0.2 + 0.8 * n_systems * share`. Even split → 1.0.
#[inline]
pub fn multiplier(n_systems: u8, share: f32) -> f32 {
    0.2 + 0.8 * f32::from(n_systems) * share
}

/// `[P_s, P_e, P_w]` for a split. On two-way hulls `P_s` is 0.2 and unused.
pub fn multipliers(n_systems: u8, power: [f32; 3]) -> [f32; 3] {
    power.map(|share| multiplier(n_systems, share))
}

/// `[P_s, P_e, P_w]` of a ship on its hull.
pub fn ship_multipliers(ship: &Ship, hull: &HullDef) -> [f32; 3] {
    multipliers(hull.n_power_systems, ship.power)
}

/// One tick of slew (stage 4): every component moves the same fraction `k` of its
/// gap, with `k` chosen so the largest gap closes at `POWER_SLEW_RATE` per second.
/// Moving all components by the same fraction keeps the shares summed to 1.
pub fn slew(power: &mut [f32; 3], target: [f32; 3]) {
    let gap = power
        .iter()
        .zip(&target)
        .map(|(p, t)| (t - p).abs())
        .fold(0.0, f32::max);
    if gap == 0.0 {
        return;
    }
    let k = (POWER_SLEW_RATE * DT / gap).min(1.0);
    if k >= 1.0 {
        *power = target;
        return;
    }
    for (p, t) in power.iter_mut().zip(&target) {
        *p += (t - *p) * k;
    }
}
