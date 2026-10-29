//! Arena boundary: inward push and hull drain outside radius `R` (SIM_SPEC §5.7).
//!
//! The push is a velocity change only (applied after integration), so a fast ship
//! can overshoot for a few ticks. The drain can take hp to or below 0; death itself
//! is resolved in stage 12.

use crate::DT;
use crate::data::Catalogue;
use crate::state::{MAX_SHIPS, Match};

/// Inward acceleration outside the arena, m/s².
pub const ARENA_PUSH: f32 = 40.0;
/// Fraction of max hp drained per second outside the arena.
pub const ARENA_DRAIN_PER_S: f32 = 0.02;

impl Match {
    /// Stage 11 (SIM_SPEC §5): for each active, non-static ship with `|pos| > R`,
    /// push it inward and drain its hull. Rewrites `outside_arena` for every slot
    /// (true only for ships this stage pushed), which the reward stage reads.
    pub fn apply_arena(&mut self, cat: &Catalogue) {
        let radius = self.cfg.arena_radius;
        self.outside_arena = [false; MAX_SHIPS];
        for ship in self.ships.iter_mut() {
            if !ship.active() {
                continue;
            }
            let hull = cat.hull(ship.hull);
            if hull.is_static {
                continue;
            }
            let r = ship.pos.length();
            if r <= radius {
                continue;
            }
            ship.vel -= ship.pos / r * ARENA_PUSH * DT;
            ship.hp -= ARENA_DRAIN_PER_S * hull.hp * DT;
            self.outside_arena[ship.slot as usize] = true;
        }
    }
}
