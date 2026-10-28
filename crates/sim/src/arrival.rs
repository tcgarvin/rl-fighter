//! Jump-in scheduling at match start and stage 2 arrivals (SIM_SPEC §5.6).
//!
//! Each fleet is cut into squads of up to three, placed on its own side of the arena
//! and given a staggered arrival tick. Ships stay `present == false` until then, so
//! they are invisible to hits, obs, collisions and the arena.
//!
//! RNG draw order (golden traces depend on it; change it only with a `SIM_VERSION`
//! bump). All draws come from the match stream, in this exact sequence:
//!
//! ```text
//! for team in [0, 1]:
//!     team_offset = range(0, 0.6)
//!     for squad k in 0..K:                      # fleet order, squads of <= 3
//!         cy_jitter  = range(-15, 15)
//!         cx_jitter  = range(0, 30)
//!         stagger    = range(0.6, 1.4)          # drawn for k = 0 too
//!         for ship in squad:                    # fleet order
//!             arrive_jitter = range(0, 0.08)
//! ```

use crate::TICK_HZ;
use crate::data::Catalogue;
use crate::math::{PI, Vec2};
use crate::rng::Pcg32;
use crate::state::{Attach, Match, Ship, ShipIdx};

/// Ships per squad.
pub const SQUAD_SIZE: usize = 3;
/// Vertical spacing between squad centres, metres.
pub const SQUAD_SPACING: f32 = 70.0;
/// Vertical spacing between ships in a squad, metres.
pub const ROW_SPACING: f32 = 16.0;
/// Rearward step per row away from the squad centre, metres.
pub const ROW_STAGGER: f32 = 10.0;
/// Seconds before the first squad can arrive.
pub const BASE_ARRIVAL_S: f32 = 1.0;
/// Upper bound of the per-team offset, seconds.
pub const MAX_TEAM_OFFSET_S: f32 = 0.6;
/// Nominal gap between successive squads, seconds (scaled by `range(0.6, 1.4)`).
pub const SQUAD_GAP_S: f32 = 0.3;
/// Upper bound of the per-ship arrival jitter, seconds.
pub const MAX_SHIP_JITTER_S: f32 = 0.08;
/// Ticks of control lock after arriving (0.7 s).
pub const ARRIVAL_LOCK_TICKS: u32 = 21;

/// Place every ship and set its `arrive_tick` (SIM_SPEC §5.6). Ships keep
/// `present == false` and zero velocity; stage 2 brings them in.
///
/// `ships` must be in slot order (team 0 first); the draw order is documented in
/// the module docs.
pub fn schedule_arrivals(ships: &mut [Ship], rng: &mut Pcg32, arena_radius: f32) {
    for team in 0..2u8 {
        let side = if team == 0 { -1.0 } else { 1.0 };
        let heading = if team == 0 { 0.0 } else { PI };
        let slots: Vec<usize> = (0..ships.len())
            .filter(|&i| ships[i].team == team)
            .collect();
        let n_squads = slots.len().div_ceil(SQUAD_SIZE);
        let team_offset = rng.range(0.0, MAX_TEAM_OFFSET_S);
        for (k, squad) in slots.chunks(SQUAD_SIZE).enumerate() {
            let k_f = k as f32;
            let cy = (k_f - (n_squads as f32 - 1.0) * 0.5) * SQUAD_SPACING + rng.range(-15.0, 15.0);
            let cx = side * (0.5 * arena_radius + rng.range(0.0, 30.0));
            let squad_time = BASE_ARRIVAL_S + team_offset + k_f * SQUAD_GAP_S * rng.range(0.6, 1.4);
            let n = squad.len() as f32;
            for (i, &slot) in squad.iter().enumerate() {
                let row = i as f32 - (n - 1.0) * 0.5;
                let ship = &mut ships[slot];
                ship.pos = Vec2::new(cx + row.abs() * side * ROW_STAGGER, cy + row * ROW_SPACING);
                ship.heading = heading;
                ship.vel = Vec2::ZERO;
                ship.present = false;
                let t = squad_time + rng.range(0.0, MAX_SHIP_JITTER_S);
                ship.arrive_tick = libm::roundf(t * TICK_HZ) as u32;
            }
        }
    }
}

/// Earliest tick `schedule_arrivals` can assign.
pub fn earliest_arrive_tick() -> u32 {
    libm::roundf(BASE_ARRIVAL_S * TICK_HZ) as u32
}

/// Latest tick `schedule_arrivals` can assign to a team of `n_ships`.
pub fn latest_arrive_tick(n_ships: usize) -> u32 {
    let last_squad = n_ships.div_ceil(SQUAD_SIZE).saturating_sub(1) as f32;
    let t = BASE_ARRIVAL_S + MAX_TEAM_OFFSET_S + last_squad * SQUAD_GAP_S * 1.4 + MAX_SHIP_JITTER_S;
    libm::roundf(t * TICK_HZ) as u32
}

impl Match {
    /// Stage 2 (SIM_SPEC §5): every alive, unattached, not-yet-present ship whose
    /// `arrive_tick` has come becomes present, moving forward at its hull's
    /// `arrival_speed`, with control locked for `ARRIVAL_LOCK_TICKS`.
    ///
    /// Appends the arrived slots to `arrived` in slot order (it is not cleared), so
    /// the step assembly can emit `Arrival` events.
    pub fn process_arrivals(&mut self, cat: &Catalogue, arrived: &mut Vec<ShipIdx>) {
        let tick = self.tick;
        for ship in self.ships.iter_mut() {
            let due = !ship.present
                && ship.alive
                && ship.attach == Attach::None
                && tick >= ship.arrive_tick;
            if !due {
                continue;
            }
            let hull = cat.hull(ship.hull);
            ship.present = true;
            ship.vel = Vec2::from_angle(ship.heading) * hull.arrival_speed;
            ship.control_lock_until = tick + ARRIVAL_LOCK_TICKS;
            arrived.push(ship.slot);
        }
    }
}
