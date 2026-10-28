"""Retroactive projectile credit assignment.

When a projectile hits an enemy, inject a bonus reward at the fire-time step
for the shooter. This bridges the temporal gap between the fire decision and
the impact reward, improving credit assignment for projectile weapons.

Uses episode generation tracking to prevent cross-episode credit leakage.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# Same as REWARD_DAMAGE_DEALT — effectively doubles signal for the shooter
CREDIT_COEFF = 0.01


class CreditAssigner:
    """Track in-flight projectiles and inject fire-time credit on hit.

    Args:
        n_envs: Number of parallel environments.
        n_ships: Ships per match.
        buf_len: Total buffer length (n_steps + t_tail).
        credit_coeff: Reward bonus per HP of damage at fire-time.
    """

    def __init__(
        self,
        n_envs: int,
        n_ships: int,
        buf_len: int,
        credit_coeff: float = CREDIT_COEFF,
    ) -> None:
        self.n_envs = n_envs
        self.n_ships = n_ships
        self.buf_len = buf_len
        self.flat = n_envs * n_ships
        self.credit_coeff = credit_coeff

        # Accumulated credits per (buf_step, flat_agent)
        self.credit = np.zeros((buf_len, self.flat), dtype=np.float32)

        # Episode generation counter per env (incremented on reset)
        self.episode_gen = np.zeros(n_envs, dtype=np.int32)

        # Snapshot of episode_gen at each buffer step [buf_len, N]
        self.step_gen = np.full((buf_len, n_envs), -1, dtype=np.int32)

    def reset_for_rollout(self) -> None:
        """Clear credits for a new rollout (tail credits preserved via shift_tail)."""
        self.credit[:] = 0.0
        self.step_gen[:] = -1

    def stamp_step(self, buf_step: int) -> None:
        """Record the current episode generation for this buffer step."""
        self.step_gen[buf_step] = self.episode_gen

    def on_reset(self, env_indices: NDArray[np.intp]) -> None:
        """Increment episode generation for auto-reset environments."""
        self.episode_gen[env_indices] += 1

    def record_hits(
        self,
        buf_step: int,
        proj_hit: NDArray[np.bool_],       # [N, P]
        proj_owner: NDArray[np.int32],      # [N, P]
        proj_damage: NDArray[np.float32],   # [N, P]
        proj_fire_step: NDArray[np.int32],  # [N, P]
    ) -> None:
        """Inject retroactive credit at fire-time for projectiles that hit.

        Vectorized using np.where + np.add.at. Only credits hits where:
        - proj_fire_step >= 0 (was tracked)
        - fire step is within current buffer range
        - same episode (episode_gen matches between fire step and hit step)
        """
        N = self.n_envs
        S = self.n_ships

        # Find hitting projectiles with valid fire steps
        valid = proj_hit & (proj_fire_step >= 0) & (proj_fire_step < self.buf_len)
        if not np.any(valid):
            return

        hit_n, hit_p = np.where(valid)
        fire_steps = proj_fire_step[hit_n, hit_p]
        owners = proj_owner[hit_n, hit_p]
        damages = proj_damage[hit_n, hit_p]

        # Episode boundary check: fire step must be same episode as current step
        fire_gen = self.step_gen[fire_steps, hit_n]
        hit_gen = self.step_gen[buf_step, hit_n]
        same_episode = (fire_gen == hit_gen) & (fire_gen >= 0)

        # Filter to valid same-episode hits
        mask = same_episode
        if not np.any(mask):
            return

        fire_steps = fire_steps[mask]
        env_ids = hit_n[mask]
        owners = owners[mask]
        damages = damages[mask]

        # Convert (env_id, owner_ship) to flat index
        flat_idx = env_ids * S + owners
        credit_amount = self.credit_coeff * damages

        np.add.at(self.credit, (fire_steps, flat_idx), credit_amount)

    def inject_into_rewards(
        self,
        rewards: NDArray[np.float32],  # [buf_len, flat]
        start: int = 0,
        end: int | None = None,
    ) -> None:
        """Add accumulated credits into the reward buffer."""
        if end is None:
            end = self.buf_len
        rewards[start:end] += self.credit[start:end]

    def shift_tail(self, t_steps: int) -> None:
        """Move last t_tail credits to front for next rollout.

        After a rollout of t_steps collected steps (starting after tail),
        shift the tail portion to the beginning of the buffer.
        """
        t_tail = self.buf_len - t_steps
        if t_tail <= 0:
            return

        # Move tail credits from end to front
        self.credit[:t_tail] = self.credit[t_steps:t_steps + t_tail]
        self.credit[t_tail:] = 0.0

        # Move tail step_gen
        self.step_gen[:t_tail] = self.step_gen[t_steps:t_steps + t_tail]
        self.step_gen[t_tail:] = -1


# ---------------------------------------------------------------------------
# Rust VecEnv (rlf_sim) adapter
# ---------------------------------------------------------------------------

# Reward weights mirrored from crates/sim/src/reward.rs (rlf_sim does not export
# them); tests/test_rust_env_wrapper.py asserts they match the Rust source.
HULL_DAMAGE_WEIGHT = 0.01
SHIELD_DAMAGE_WEIGHT = 0.005

# Columns of one row of rlf_sim's hits[N, MAX_HITS, 5] buffer (SIM_SPEC §8).
HIT_SHOOTER = 0
HIT_TARGET = 1
HIT_FIRE_TICK = 2
HIT_DAMAGE_MILLI = 3
HIT_SHIELD = 4
HIT_FIELDS = 5
# The damage column is fixed point: damage * HIT_DAMAGE_SCALE, rounded.
HIT_DAMAGE_SCALE = 1000.0

# Stamp value of a buffer step that has not been stepped in this rollout.
_UNSTAMPED = -1


class RustCreditAdapter:
    """Move each hit's shooter reward from the landing step to the firing step.

    The Rust sim already pays the shooter ``weight * damage`` on the step a hit
    lands (SIM_SPEC §8). This adapter does not add credit on top of that: for every
    hit it subtracts the shooter's reward at the landing buffer step and adds the
    same amount at the buffer step where the shot was fired, so the summed reward
    of every agent over the buffer is unchanged. The target's penalty stays where
    the hit landed.

    Mapping ``fire_tick`` to a buffer step: every buffer step is stamped with each
    env's ``tick`` and ``episode_count`` *before* that step. A step taken with
    pre-step tick ``t`` runs sim tick ``t + 1``, and a shot fired on that step has
    ``fire_tick == t + 1``. So a hit recorded at buffer step ``b`` was fired at
    ``b - (tick_before[b] + 1 - fire_tick)``, which is accepted only if that step is
    stamped with the same episode and ``tick == fire_tick - 1`` (one env step per
    buffer step, no ``reset()`` in between).

    Rules (following v1 ``CreditAssigner``, which only credits fire steps inside the
    buffer and in the same episode):

    * Fire step inside the buffer, same episode: the reward is moved.
    * Fire step before the buffer's first stamped step (a shot fired before the
      rollout started, or before the retained tail): nothing is moved; the reward
      stays on the landing step where the sim put it.
    * Cross-episode: cannot occur, because the Rust env rebuilds a finished match
      and its projectiles are discarded; the episode check is kept as a guard.
    * Shooter already dead when the hit lands: the sim paid nobody (the shooter
      was not active), so there is nothing to move. With
      ``credit_dead_shooters=True`` the reward is instead *added* at the fire step
      (v1-style injection); this breaks reward conservation by design.

    Usage per rollout, with ``buf_step`` the reward-buffer row of the step::

        info = env.step(actions)[3]
        adapter.record_step(buf_step, info.prev_tick, info.prev_episode_count,
                            info.prev_alive, info.hits, info.hit_count)
        ...
        adapter.inject_into_rewards(buf.rewards, 0, end)

    Call ``reset_for_rollout()`` before a rollout with no retained tail; with a
    tail of ``buf_len - t_steps`` steps call ``shift_tail(t_steps)`` instead, so
    hits in the new rollout can still reach fire steps in the tail.

    Args:
        n_envs: Number of parallel matches.
        n_ships: Ship slots per match.
        buf_len: Rows of the reward buffer (n_steps + t_tail).
        hull_weight: Reward per point of hull damage (reward.rs HULL_DAMAGE_WEIGHT).
        shield_weight: Reward per point of shield damage
            (reward.rs SHIELD_DAMAGE_WEIGHT).
        credit_dead_shooters: Add (rather than move) credit for hits whose
            shooter was dead when they landed.
    """

    def __init__(
        self,
        n_envs: int,
        n_ships: int,
        buf_len: int,
        hull_weight: float = HULL_DAMAGE_WEIGHT,
        shield_weight: float = SHIELD_DAMAGE_WEIGHT,
        credit_dead_shooters: bool = False,
    ) -> None:
        if n_envs <= 0 or n_ships <= 0 or buf_len <= 0:
            raise ValueError(
                f"n_envs, n_ships and buf_len must be positive, got "
                f"{n_envs}, {n_ships}, {buf_len}"
            )
        self.n_envs = n_envs
        self.n_ships = n_ships
        self.buf_len = buf_len
        self.hull_weight = hull_weight
        self.shield_weight = shield_weight
        self.credit_dead_shooters = credit_dead_shooters

        # Signed reward deltas per (buf_step, flat agent); summed over a move = 0.
        self.credit = np.zeros((buf_len, n_envs * n_ships), dtype=np.float64)
        # Pre-step tick and episode_count of each env at each buffer step.
        self.step_tick = np.full((buf_len, n_envs), _UNSTAMPED, dtype=np.int64)
        self.step_episode = np.full((buf_len, n_envs), _UNSTAMPED, dtype=np.int64)
        # Hits moved / left at their landing step / added for dead shooters.
        self.n_moved = 0
        self.n_kept = 0
        self.n_added = 0

    def reset_for_rollout(self) -> None:
        """Clear credits, stamps and counters (no tail carried over)."""
        self.credit[:] = 0.0
        self.step_tick[:] = _UNSTAMPED
        self.step_episode[:] = _UNSTAMPED
        self.n_moved = self.n_kept = self.n_added = 0

    def record_step(
        self,
        buf_step: int,
        tick_before: NDArray[np.integer],
        episode_before: NDArray[np.integer],
        alive_before: NDArray[np.bool_],
        hits: NDArray[np.int32],
        hit_count: NDArray[np.int32],
    ) -> None:
        """Stamp ``buf_step`` and move the credit of the hits that landed on it.

        Args:
            buf_step: Reward-buffer row of this env step.
            tick_before: [N] each env's tick before the step.
            episode_before: [N] each env's episode_count before the step.
            alive_before: [N, S] alive flags before the step (a shooter alive at
                the start of the step was paid by the sim for its hits).
            hits: [N, MAX_HITS, 5] hit rows of the step (rlf_sim ``hits``).
            hit_count: [N] valid rows of ``hits`` per env.
        """
        if not 0 <= buf_step < self.buf_len:
            raise IndexError(f"buf_step {buf_step} outside buffer of {self.buf_len}")
        n, s = self.n_envs, self.n_ships
        if hits.ndim != 3 or hits.shape[0] != n or hits.shape[2] != HIT_FIELDS:
            raise ValueError(
                f"hits must be [{n}, MAX_HITS, {HIT_FIELDS}], got {hits.shape}"
            )
        if alive_before.shape != (n, s):
            raise ValueError(
                f"alive_before must be [{n}, {s}], got {alive_before.shape}"
            )
        tick_before = np.asarray(tick_before, dtype=np.int64)
        episode_before = np.asarray(episode_before, dtype=np.int64)
        self.step_tick[buf_step] = tick_before
        self.step_episode[buf_step] = episode_before

        valid = np.arange(hits.shape[1])[None, :] < hit_count[:, None]
        env_ids, rows = np.nonzero(valid)
        if env_ids.size == 0:
            return
        rec = hits[env_ids, rows].astype(np.int64)
        shooter = rec[:, HIT_SHOOTER]
        fire_tick = rec[:, HIT_FIRE_TICK]
        weight = np.where(rec[:, HIT_SHIELD] != 0, self.shield_weight, self.hull_weight)
        amount = weight * rec[:, HIT_DAMAGE_MILLI] / HIT_DAMAGE_SCALE

        fire_step = buf_step - (tick_before[env_ids] + 1 - fire_tick)
        in_buffer = fire_step >= 0
        safe_step = np.where(in_buffer, fire_step, 0)
        stamped = (
            in_buffer
            & (self.step_tick[safe_step, env_ids] == fire_tick - 1)
            & (self.step_episode[safe_step, env_ids] == episode_before[env_ids])
        )
        paid = alive_before[env_ids, shooter]
        flat = env_ids * s + shooter

        move = stamped & paid
        np.add.at(self.credit, (fire_step[move], flat[move]), amount[move])
        np.add.at(
            self.credit, (np.full(int(move.sum()), buf_step), flat[move]), -amount[move]
        )
        self.n_moved += int(move.sum())

        add = stamped & ~paid & self.credit_dead_shooters
        np.add.at(self.credit, (fire_step[add], flat[add]), amount[add])
        self.n_added += int(add.sum())
        self.n_kept += int((~stamped & paid).sum())

    def inject_into_rewards(
        self, rewards: NDArray[np.float32], start: int, end: int
    ) -> None:
        """Apply the accumulated deltas to ``rewards[start:end]`` in place.

        Args:
            rewards: [buf_len, n_envs * n_ships] reward buffer (RolloutBuffer.rewards).
            start: First buffer row to apply.
            end: One past the last buffer row to apply.
        """
        if rewards.shape != self.credit.shape:
            raise ValueError(
                f"rewards must be {self.credit.shape}, got {rewards.shape}"
            )
        rewards[start:end] += self.credit[start:end].astype(rewards.dtype)

    def shift_tail(self, t_steps: int) -> None:
        """Carry the last ``buf_len - t_steps`` stamps to the front of the buffer.

        Credits are cleared, not shifted: the tail's rewards were extracted after
        ``inject_into_rewards`` and already contain them. Later hits whose fire
        step lies in the tail move their reward into the tail rows.
        """
        t_tail = self.buf_len - t_steps
        if not 0 <= t_tail < self.buf_len:
            raise ValueError(f"t_steps {t_steps} must be in (0, {self.buf_len}]")
        self.step_tick[:t_tail] = self.step_tick[t_steps:].copy()
        self.step_episode[:t_tail] = self.step_episode[t_steps:].copy()
        self.step_tick[t_tail:] = _UNSTAMPED
        self.step_episode[t_tail:] = _UNSTAMPED
        self.credit[:] = 0.0
        self.n_moved = self.n_kept = self.n_added = 0
