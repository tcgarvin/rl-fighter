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
