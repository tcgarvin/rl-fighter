//! Match::step in the SIM_SPEC §5 order, stage 12 deaths, and stage 13 termination
//! and winner (§5.8).
//!
//! This file only sequences the stages; each stage's logic lives in its own module
//! (named per stage below).

use crate::data::Catalogue;
use crate::events::Event;
use crate::state::{MAX_SHIPS, MAX_THRUSTERS, Match, MatchPhase, ShipIdx, WINNER_DRAW};

/// Team values closer than this at the time limit are a draw (§5.8).
pub const VALUE_TIE_EPS: f32 = 1e-3;
/// Weight of remaining shield in the time-limit team value (§5.8).
pub const VALUE_SHIELD_WEIGHT: f32 = 0.5;

impl Match {
    /// Advance one tick (SIM_SPEC §5). Fills `events`, `hits`, `shots_fired`,
    /// `outside_arena` and `rewards` for this tick.
    ///
    /// After the match is `Over`, a step still clears the per-step outputs and
    /// advances `tick` (stage 1), then returns: ships, projectiles, rng, phase and
    /// winner are untouched and rewards are all 0. The VecEnv never does this; the
    /// browser may, to keep an outro clock running.
    pub fn step(&mut self, cat: &Catalogue) {
        // 1. Clear per-step outputs; advance the clock.
        self.clear_combat_outputs();
        self.rewards = [0.0; MAX_SHIPS];
        self.outside_arena = [false; MAX_SHIPS];
        self.tick += 1;
        if self.phase == MatchPhase::Over {
            return;
        }

        // 2. Arrivals (arrival.rs); this file emits their events.
        let mut arrived: Vec<ShipIdx> = Vec::new();
        self.process_arrivals(cat, &mut arrived);
        for &slot in &arrived {
            let s = &self.ships[slot as usize];
            self.events.push(Event::Arrival {
                ship: slot,
                pos: s.pos,
                heading: s.heading,
            });
        }
        // Ships that earn per-step reward terms this tick (reward.rs).
        let mut earning = [false; MAX_SHIPS];
        for (e, s) in earning.iter_mut().zip(&self.ships) {
            *e = s.active();
        }

        // 3–5. Actions, power slew, physics (actions.rs, power.rs, physics.rs).
        self.step_motion(cat);
        // 6. Turret slew and cooldown (turrets.rs).
        self.step_turrets(cat);
        // 7. Fire (weapons.rs).
        self.step_fire(cat);
        // 8. Projectiles and hits (projectiles.rs, damage.rs).
        self.step_projectiles(cat);
        // 9. Shield regen (damage.rs).
        self.step_shield_regen(cat);
        // 10. Ship-ship collisions (collision.rs).
        self.resolve_collisions(cat);
        // 11. Arena push and drain (arena.rs).
        self.apply_arena(cat);
        // 12. Deaths.
        self.resolve_deaths();
        // 13. Termination and winner.
        self.check_termination();
        // 14. Rewards, including the terminal term (reward.rs).
        self.compute_rewards(&earning);
    }

    /// Stage 12: every alive ship with `hp <= 0` dies (`alive = present = false`,
    /// `hp = 0`, throttles off) and emits `Death`, in slot order. Damage never
    /// flips `alive` itself, so kills within one tick are symmetric.
    pub fn resolve_deaths(&mut self) {
        for ship in self.ships.iter_mut() {
            if !ship.alive || ship.hp > 0.0 {
                continue;
            }
            ship.alive = false;
            ship.present = false;
            ship.hp = 0.0;
            ship.throttle = [0; MAX_THRUSTERS];
            self.events.push(Event::Death {
                ship: ship.slot,
                pos: ship.pos,
            });
        }
    }

    /// Stage 13 (§5.8): the match is over when a team has no alive ships (pending
    /// arrivals count as alive) — winner the surviving team, or a draw if both are
    /// gone — or at the time limit, where the higher team value
    /// `Σ_alive (hp + 0.5 * shield)` wins and values within `VALUE_TIE_EPS` draw.
    pub fn check_termination(&mut self) {
        let mut alive = [0u32; 2];
        for s in self.ships.iter().filter(|s| s.alive) {
            alive[s.team as usize] += 1;
        }
        let winner = match alive {
            [0, 0] => WINNER_DRAW,
            [0, _] => 1,
            [_, 0] => 0,
            _ if self.tick >= self.cfg.time_limit_ticks => {
                let [v0, v1] = self.team_values();
                if (v0 - v1).abs() < VALUE_TIE_EPS {
                    WINNER_DRAW
                } else if v0 > v1 {
                    0
                } else {
                    1
                }
            }
            _ => return,
        };
        self.phase = MatchPhase::Over;
        self.winner = winner;
    }

    /// Time-limit tiebreak value per team: `Σ_alive (hp + 0.5 * shield)`, slot order.
    pub fn team_values(&self) -> [f32; 2] {
        let mut v = [0.0f32; 2];
        for s in self.ships.iter().filter(|s| s.alive) {
            v[s.team as usize] += s.hp + VALUE_SHIELD_WEIGHT * s.shield;
        }
        v
    }
}
