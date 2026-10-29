//! Per-ship step rewards from the step's HitRecords, shots and arena flags, plus the
//! terminal term (SIM_SPEC §8).
//!
//! Which ships earn the per-step terms: a ship earns damage, fire-cost and arena terms
//! only if it was active (alive and present) after stage 2 of this step. So a ship
//! killed this step still takes the penalty for the hit that killed it, while ships
//! that died on an earlier step or have not arrived yet get 0, including credit for
//! their own projectiles still in flight (the HitRecords keep that credit for the
//! Python `CreditAssigner`). The terminal term goes to every ship of a team, dead
//! ones too.

use crate::events::HitRecord;
use crate::state::{MAX_SHIPS, Match, MatchPhase, WINNER_DRAW};

/// Reward per point of hull damage dealt (shooter) and taken (target, negated).
pub const HULL_DAMAGE_WEIGHT: f32 = 0.01;
/// Reward per point of raw damage a shield took: half the hull weight, since shields
/// regenerate (SIM_SPEC §15 q2).
pub const SHIELD_DAMAGE_WEIGHT: f32 = 0.005;
/// Reward per shot actually fired (a trigger pull on cooldown costs nothing).
pub const FIRE_COST: f32 = -0.002;
/// Reward per tick spent outside the arena radius.
pub const ARENA_PENALTY: f32 = -0.002;
/// Terminal reward magnitude: `+WIN_REWARD` to the winners, `-WIN_REWARD` to the
/// losers, 0 to everyone on a draw.
pub const WIN_REWARD: f32 = 1.0;

/// Damage weight of one HitRecord.
#[inline]
pub fn hit_weight(h: &HitRecord) -> f32 {
    if h.shield {
        SHIELD_DAMAGE_WEIGHT
    } else {
        HULL_DAMAGE_WEIGHT
    }
}

/// Terminal reward of a ship on `team` for a match that ended with `winner`.
#[inline]
pub fn terminal_reward(winner: i8, team: u8) -> f32 {
    if winner == WINNER_DRAW {
        0.0
    } else if i16::from(winner) == i16::from(team) {
        WIN_REWARD
    } else {
        -WIN_REWARD
    }
}

impl Match {
    /// Stage 14: overwrite `rewards` from this step's outputs. `earning[s]` says
    /// whether slot `s` earns per-step terms (active after stage 2, see the module
    /// docs). Terms are summed per ship in a fixed order: hits in record order, then
    /// collision hull and shield damage taken (v3), fire cost, arena, terminal.
    pub fn compute_rewards(&mut self, earning: &[bool; MAX_SHIPS]) {
        let mut r = [0.0f32; MAX_SHIPS];
        for h in &self.hits {
            let delta = hit_weight(h) * h.damage;
            let (shooter, target) = (h.shooter as usize, h.target as usize);
            if shooter < MAX_SHIPS && earning[shooter] {
                r[shooter] += delta;
            }
            if target < MAX_SHIPS && earning[target] {
                r[target] -= delta;
            }
        }
        for s in 0..self.ships.len() {
            if earning[s] {
                // v3: collision damage is taken, never dealt: nobody is credited.
                r[s] -= HULL_DAMAGE_WEIGHT * self.collision_damage[s];
                r[s] -= SHIELD_DAMAGE_WEIGHT * self.collision_shield_damage[s];
                r[s] += FIRE_COST * f32::from(self.shots_fired[s]);
                if self.outside_arena[s] {
                    r[s] += ARENA_PENALTY;
                }
            }
        }
        if self.phase == MatchPhase::Over {
            for ship in &self.ships {
                r[ship.slot as usize] += terminal_reward(self.winner, ship.team);
            }
        }
        self.rewards = r;
    }
}
