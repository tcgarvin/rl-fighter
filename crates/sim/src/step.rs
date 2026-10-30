//! Match::step in the SIM_SPEC §5 order, stage 12 deaths, and stage 13 termination
//! and winner (§5.8).
//!
//! This file only sequences the stages; each stage's logic lives in its own module
//! (named per stage below).

use crate::actions::ShipAction;
use crate::data::Catalogue;
use crate::events::Event;
use crate::state::{MAX_REACTION_TICKS, MAX_SHIPS, MAX_THRUSTERS, Match, MatchPhase, ShipIdx};

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

        // 1b. v4: the commanders' slow tick: squads, orders, waypoints, launches
        // (command.rs).
        self.step_commanders(cat);

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
        // 12b. v4: mission rules: a lost carrier's hangar, convoy jumps (mission.rs).
        self.step_mission_rules();
        // 13. Termination, winner and end reason per mission (mission.rs).
        self.check_termination(cat);
        // 14. Rewards, including the terminal term (reward.rs).
        self.compute_rewards(&earning);
    }

    /// Stage 12: every alive ship with `hp <= 0` dies (`alive = present = false`,
    /// `hp = 0`, thrust levels 0, reaction queue all `IDLE`) and emits `Death`, in slot order. Damage never
    /// flips `alive` itself, so kills within one tick are symmetric.
    pub fn resolve_deaths(&mut self) {
        for ship in self.ships.iter_mut() {
            if !ship.alive || ship.hp > 0.0 {
                continue;
            }
            ship.alive = false;
            ship.present = false;
            ship.hp = 0.0;
            ship.thrust_level = [0.0; MAX_THRUSTERS];
            ship.queue = [ShipAction::IDLE; MAX_REACTION_TICKS];
            self.events.push(Event::Death {
                ship: ship.slot,
                pos: ship.pos,
            });
        }
    }

    /// Time-limit tiebreak value per team: `Σ (hp + 0.5 * shield)` over the ships
    /// still in the match (alive, not jumped out; v4), slot order.
    pub fn team_values(&self) -> [f32; 2] {
        let mut v = [0.0f32; 2];
        for (i, s) in self.ships.iter().enumerate() {
            if self.in_match(i) {
                v[s.team as usize] += s.hp + VALUE_SHIELD_WEIGHT * s.shield;
            }
        }
        v
    }
}
