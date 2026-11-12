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
//!
//! v5, v6: the **order reward** (SIM_SPEC §8 "Order reward") goes into its own buffer,
//! `Match.order_rewards`, which Python weights; `rewards` is unchanged. The same
//! ships earn it as earn `rewards` (docked reserves earn nothing). Per ship and step,
//! in this order:
//! - *attack*: `ORDER_HULL_WEIGHT` · hull + `ORDER_SHIELD_WEIGHT` · shield damage the
//!   ship dealt to its ordered target, when it lands (no retroactive credit);
//! - *defend*: the same weights on damage dealt to the ward's **threat set**
//!   (`order` module; the enemies on the field this step), then
//!   `DEFEND_HULL_LOSS_WEIGHT` × the ward's hull fraction lost this step and
//!   `DEFEND_WARD_DEATH` once if the ward died this step. Every defender of the ward
//!   pays the whole of both (shared, not split). No location term;
//! - *go-to*: potential shaping `γΦ′ − Φ` with `Φ = −K · max(0, d − radius) / R` and
//!   `γ = MatchConfig.order_shaping_gamma` until arrival, no shaping on the step an
//!   instance starts (Φ is reset, so a new order pays nothing for the jump); a
//!   one-shot `ORDER_ARRIVAL_BONUS` the first time inside the radius per instance,
//!   which completes the order for that ship. No presence term (v5 had one).
//!   v8: an instance that starts with the ship already inside the radius is complete
//!   with no bonus. A go-to **with a deadline** has the same shaping until arrival or
//!   expiry, pays `MatchConfig.goto_timed_bonus` instead of `ORDER_ARRIVAL_BONUS` for
//!   arriving by the deadline tick, and charges `MatchConfig.goto_miss_penalty` once,
//!   at the end of the first step past the deadline, to a ship that has not arrived
//!   (a ship that does not earn this step, dead or absent, is marked missed but not
//!   charged). Time before the deadline costs nothing.
//!
//! Hit credit and both defend terms use the standing order (the squad's order during
//! the step: the effective order is already none on the tick an attack target or a
//! ward dies); instances, shaping and arrival use it at the step's end too (`order`
//! module docs).

use crate::command::Order;
use crate::data::Catalogue;
use crate::events::HitRecord;
use crate::order::{OrderTrack, order_geometry, standing_order};
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

/// Order reward: per point of hull damage dealt to an attack target (or, for a
/// defender, to its ward's threat set).
pub const ORDER_HULL_WEIGHT: f32 = 0.01;
/// Order reward: per point of raw shield damage dealt to the same ships.
pub const ORDER_SHIELD_WEIGHT: f32 = 0.005;
/// v6: a defender pays this × the hull fraction its ward lost each step (fractions,
/// so a freighter and a carrier weigh the same).
pub const DEFEND_HULL_LOSS_WEIGHT: f32 = -0.5;
/// v6: a defender pays this once, on the step its ward dies.
pub const DEFEND_WARD_DEATH: f32 = -0.3;
/// Go-to shaping potential scale `K` (`Φ = −K · max(0, d − radius) / R`).
pub const ORDER_SHAPING_K: f32 = 1.0;
/// Default discount of the shaping term `γΦ′ − Φ` (`MatchConfig.order_shaping_gamma`).
/// A trainer sets the match's value to its own PPO γ: only then does the shaping leave
/// the optimal policy unchanged. With γ too low for the trainer's discount, the term
/// pays a pilot to stay away from the point.
pub const ORDER_SHAPING_GAMMA: f32 = 0.99;
/// Paid once per go-to instance without a deadline, the first time inside its radius
/// (v6: 0.2, was 0.1 with a presence term on top).
pub const ORDER_ARRIVAL_BONUS: f32 = 0.2;
/// v8, default of `MatchConfig.goto_timed_bonus`: paid once per go-to instance with a
/// deadline, for being inside its radius by the deadline tick.
pub const ORDER_TIMED_ARRIVAL_BONUS: f32 = 1.0;
/// v8, default of `MatchConfig.goto_miss_penalty`: charged once per go-to instance
/// with a deadline, when the deadline passes before the ship has arrived.
pub const ORDER_MISS_PENALTY: f32 = 1.0;

/// The shaping potential of a ship `dist` metres from an order point with radius
/// `radius` in an arena of `arena_radius`.
#[inline]
pub fn order_potential(dist: f32, radius: f32, arena_radius: f32) -> f32 {
    -ORDER_SHAPING_K * (dist - radius).max(0.0) / arena_radius
}

/// Damage weight of one HitRecord.
#[inline]
pub fn hit_weight(h: &HitRecord) -> f32 {
    if h.shield {
        SHIELD_DAMAGE_WEIGHT
    } else {
        HULL_DAMAGE_WEIGHT
    }
}

/// Order-reward weight of one HitRecord.
#[inline]
fn order_hit_weight(h: &HitRecord) -> f32 {
    if h.shield {
        ORDER_SHIELD_WEIGHT
    } else {
        ORDER_HULL_WEIGHT
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

    /// Distance from slot `s` to its go-to point and the radius; `None` for the other
    /// kinds (only a go-to has a place to be).
    fn goto_distance(&self, s: usize, order: Order) -> Option<(f32, f32)> {
        match order {
            Order::GoTo { .. } => {
                let (point, radius) = order_geometry(self, order)?;
                Some(((point - self.ships[s].pos).length(), radius))
            }
            Order::None | Order::Attack { .. } | Order::Defend { .. } => None,
        }
    }

    /// At setup: every ship's order instance starts at tick 0 with its standing order
    /// then (only capital ships' waypoints exist yet), and the hull marks start at
    /// the full hulls. v8: a ship on the field and already inside its go-to radius
    /// starts with the instance complete (no bonus, as in a step).
    pub(crate) fn init_order_tracks(&mut self) {
        let radius = self.cfg.arena_radius;
        for s in 0..self.ships.len() {
            let order = standing_order(self, s);
            let place = self.goto_distance(s, order);
            let phi = place.map_or(0.0, |(d, r)| order_potential(d, r, radius));
            let mut track = OrderTrack::start(order, self.tick, phi);
            track.arrived = self.ships[s].active() && place.is_some_and(|(d, r)| d <= r);
            self.order_tracks[s] = track;
        }
        self.mark_hulls();
    }

    /// Remember every ship's hp and alive flag: the next step's hull loss and deaths
    /// are measured from here.
    fn mark_hulls(&mut self) {
        for (s, ship) in self.ships.iter().enumerate() {
            self.hp_mark[s] = ship.hp;
            self.alive_mark[s] = ship.alive;
        }
    }

    /// Stage 13b (v5, v6): record who hit whom, measure each ship's hull loss and
    /// every ward's threat set, refresh every ship's order instance and overwrite
    /// `order_rewards` (module docs). `earning` as for [`Match::compute_rewards`].
    pub fn compute_order_rewards(&mut self, cat: &Catalogue, earning: &[bool; MAX_SHIPS]) {
        let n = self.ships.len();
        let tick = self.tick;
        for h in &self.hits {
            let (s, t) = (usize::from(h.shooter), usize::from(h.target));
            if s < n && t < n && self.ships[s].team != self.ships[t].team {
                self.hit_by[t][s] = tick;
            }
        }
        let on_field = (0..n).filter(|&s| earning[s]).fold(0u32, |a, s| a | 1 << s);
        let mut died = [false; MAX_SHIPS];
        for s in 0..n {
            let ship = &self.ships[s];
            let max_hp = cat.hull(ship.hull).hp;
            self.hull_lost[s] = (self.hp_mark[s] - ship.hp).max(0.0) / max_hp;
            died[s] = self.alive_mark[s] && !ship.alive;
            self.ward_threat[s] = if earning[s] {
                self.threat_set(cat, s, on_field)
            } else {
                0
            };
        }
        self.hull_lost[n..].fill(0.0);
        self.ward_threat[n..].fill(0);

        let mut r = [0.0f32; MAX_SHIPS];
        for h in &self.hits {
            let (s, t) = (usize::from(h.shooter), usize::from(h.target));
            if s >= n || t >= n || !earning[s] || self.ships[t].team == self.ships[s].team {
                continue;
            }
            let paid = match standing_order(self, s) {
                Order::Attack { target } => target == h.target,
                Order::Defend { ward } => self.ward_threat[usize::from(ward)] & (1 << t) != 0,
                Order::None | Order::GoTo { .. } => false,
            };
            if paid {
                r[s] += order_hit_weight(h) * h.damage;
            }
        }
        let radius = self.cfg.arena_radius;
        let gamma = self.cfg.order_shaping_gamma;
        let timed_bonus = self.cfg.goto_timed_bonus;
        let miss_penalty = self.cfg.goto_miss_penalty;
        for (s, reward) in r.iter_mut().enumerate().take(n) {
            if earning[s]
                && let Order::Defend { ward } = standing_order(self, s)
            {
                let w = usize::from(ward);
                *reward += DEFEND_HULL_LOSS_WEIGHT * self.hull_lost[w];
                if died[w] {
                    *reward += DEFEND_WARD_DEATH;
                }
            }
            let order = standing_order(self, s);
            let place = self.goto_distance(s, order);
            let phi = place.map_or(0.0, |(d, rad)| order_potential(d, rad, radius));
            let inside = place.is_some_and(|(d, rad)| d <= rad);
            let track = &mut self.order_tracks[s];
            if !track.same_instance(order) {
                // A new instance: Φ restarts here, so the jump pays nothing. v8: a ship
                // already inside the radius has nothing to do and earns no bonus.
                *track = OrderTrack::start(order, tick, phi);
                track.arrived = earning[s] && inside;
            } else {
                if earning[s] && place.is_some() && !track.over() {
                    *reward += gamma * phi - track.last_phi;
                }
                track.last_phi = phi;
            }
            // v8: the first step past the deadline; arrival on the deadline tick itself
            // is in time. Expiry is checked first, so a late ship cannot arrive.
            if place.is_some() && track.has_deadline() && tick > track.deadline && !track.over() {
                track.missed = true;
                if earning[s] {
                    *reward -= miss_penalty;
                }
            }
            if earning[s] && inside && !track.over() {
                track.arrived = true;
                *reward += if track.has_deadline() {
                    timed_bonus
                } else {
                    ORDER_ARRIVAL_BONUS
                };
            }
        }
        self.order_rewards = r;
        self.mark_hulls();
    }
}
