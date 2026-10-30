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
//! v5: the **order reward** (SIM_SPEC §8 "Order reward") goes into its own buffer,
//! `Match.order_rewards`, which Python weights; `rewards` is unchanged. The same
//! ships earn it as earn `rewards`. Per ship and step, in this order:
//! - *attack*: `ORDER_HULL_WEIGHT` · hull + `ORDER_SHIELD_WEIGHT` · shield damage the
//!   ship dealt to its ordered target, when it lands (no retroactive credit);
//! - *guard*: the same weights on damage dealt to enemies within
//!   `ORDER_GUARD_DAMAGE_RADIUS` + the ward's bound radius of the ward;
//! - *guard and hold*: potential shaping `γΦ′ − Φ` with `Φ = −K · max(0, d −
//!   radius) / R` (`order::order_geometry` gives the point and radius), no shaping on
//!   the step an instance starts (Φ is reset, so a new order pays nothing for the
//!   jump); a one-shot `ORDER_ARRIVAL_BONUS` the first time inside the radius per
//!   instance; `ORDER_PRESENCE_REWARD` per tick inside, for at most
//!   `ORDER_PRESENCE_CAP_TICKS` ticks per instance.
//!
//! Hit credit uses the standing order (the squad's order during the step), so the
//! hit that kills an attack target is paid; shaping, arrival and presence use the
//! effective order at the step's end (`order` module docs). Why capped: an uncapped
//! presence term under the scripted commander's carrier guard pays more than
//! winning (M3 plan, stage B decisions).

use crate::command::Order;
use crate::data::Catalogue;
use crate::events::HitRecord;
use crate::order::{OrderTrack, effective_order, order_geometry, standing_order};
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

/// v5 order reward: per point of hull damage dealt to an attack target (or, for a
/// guard, to an enemy near the ward).
pub const ORDER_HULL_WEIGHT: f32 = 0.01;
/// v5 order reward: per point of raw shield damage dealt to the same ships.
pub const ORDER_SHIELD_WEIGHT: f32 = 0.005;
/// v5: a guard is paid for damage to enemies within this distance (m) of its ward,
/// plus the ward's bound radius: the scripted guard's engagement radius.
pub const ORDER_GUARD_DAMAGE_RADIUS: f32 = crate::scripted::orders::GUARD_RADIUS;
/// v5: shaping potential scale `K` (`Φ = −K · max(0, d − radius) / R`).
pub const ORDER_SHAPING_K: f32 = 1.0;
/// v5: discount of the shaping term `γΦ′ − Φ`: the trainer's PPO γ, so the shaping
/// leaves the optimal policy unchanged.
pub const ORDER_SHAPING_GAMMA: f32 = 0.99;
/// v5: paid once per order instance, the first time inside the order radius.
pub const ORDER_ARRIVAL_BONUS: f32 = 0.1;
/// v5: paid per tick inside the order radius, for at most `ORDER_PRESENCE_CAP_TICKS`
/// ticks per instance (≤ 0.09 per instance).
pub const ORDER_PRESENCE_REWARD: f32 = 0.0003;
pub const ORDER_PRESENCE_CAP_TICKS: u16 = 300;

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

    /// Distance from slot `s` to its order point and the order radius, for guard and
    /// hold (the orders with a place to be); `None` otherwise.
    fn order_distance(&self, cat: &Catalogue, s: usize, order: Order) -> Option<(f32, f32)> {
        match order {
            Order::Guard { .. } | Order::Hold { .. } => {
                let (point, radius) = order_geometry(self, cat, order)?;
                Some(((point - self.ships[s].pos).length(), radius))
            }
            Order::None | Order::Attack { .. } => None,
        }
    }

    /// v5, at setup: every ship's order instance starts at tick 0 with its effective
    /// order then (only capital ships' waypoints exist yet).
    pub(crate) fn init_order_tracks(&mut self, cat: &Catalogue) {
        let radius = self.cfg.arena_radius;
        for s in 0..self.ships.len() {
            let order = effective_order(self, s);
            let phi = self
                .order_distance(cat, s, order)
                .map_or(0.0, |(d, r)| order_potential(d, r, radius));
            self.order_tracks[s] = OrderTrack::start(order, self.tick, phi);
        }
    }

    /// Stage 13b (v5): refresh every ship's order instance and overwrite
    /// `order_rewards` (module docs). `earning` as for [`Match::compute_rewards`].
    pub fn compute_order_rewards(&mut self, cat: &Catalogue, earning: &[bool; MAX_SHIPS]) {
        let mut r = [0.0f32; MAX_SHIPS];
        let n = self.ships.len();
        for h in &self.hits {
            let (s, t) = (usize::from(h.shooter), usize::from(h.target));
            if s >= n || t >= n || !earning[s] {
                continue;
            }
            let paid = match standing_order(self, s) {
                Order::Attack { target } => target == h.target,
                Order::Guard { ward } => {
                    let w = &self.ships[usize::from(ward)];
                    let reach = ORDER_GUARD_DAMAGE_RADIUS + cat.hull(w.hull).bound_radius;
                    self.ships[t].team != self.ships[s].team
                        && (self.ships[t].pos - w.pos).length() <= reach
                }
                Order::None | Order::Hold { .. } => false,
            };
            if paid {
                let weight = if h.shield {
                    ORDER_SHIELD_WEIGHT
                } else {
                    ORDER_HULL_WEIGHT
                };
                r[s] += weight * h.damage;
            }
        }
        let radius = self.cfg.arena_radius;
        for (s, reward) in r.iter_mut().enumerate().take(n) {
            let order = effective_order(self, s);
            let place = self.order_distance(cat, s, order);
            let phi = place.map_or(0.0, |(d, rad)| order_potential(d, rad, radius));
            let tick = self.tick;
            let track = &mut self.order_tracks[s];
            if !track.same_instance(order) {
                // A new instance: Φ restarts here, so the jump pays nothing.
                *track = OrderTrack::start(order, tick, phi);
            } else {
                if earning[s] && place.is_some() {
                    *reward += ORDER_SHAPING_GAMMA * phi - track.last_phi;
                }
                track.last_phi = phi;
            }
            let inside = place.is_some_and(|(d, rad)| d <= rad);
            if earning[s] && inside {
                if !track.arrived {
                    track.arrived = true;
                    *reward += ORDER_ARRIVAL_BONUS;
                }
                if track.presence_ticks < ORDER_PRESENCE_CAP_TICKS {
                    track.presence_ticks += 1;
                    *reward += ORDER_PRESENCE_REWARD;
                }
            }
        }
        self.order_rewards = r;
    }
}
