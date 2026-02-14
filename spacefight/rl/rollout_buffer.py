"""Rollout buffer for MAPPO training.

Stores transitions from parallel environments and computes GAE advantages.
Stores both per-agent obs and centralized critic obs.
"""

from __future__ import annotations

import torch
import numpy as np
from numpy.typing import NDArray


class RolloutBuffer:
    """Fixed-size buffer for one rollout phase (T steps x N envs x S ships).

    Stores observations, critic observations, actions (raw categorical indices),
    log_probs, values, rewards, and dones. Computes GAE returns on demand.
    """

    def __init__(
        self,
        n_steps: int,
        n_envs: int,
        n_ships: int,
        obs_dim: int,
        critic_obs_dim: int,
    ) -> None:
        self.n_steps = n_steps
        self.n_envs = n_envs
        self.n_ships = n_ships
        self.obs_dim = obs_dim
        self.critic_obs_dim = critic_obs_dim
        self.ptr = 0

        flat = n_envs * n_ships

        self.obs = np.zeros((n_steps, flat, obs_dim), dtype=np.float32)
        self.critic_obs = np.zeros((n_steps, flat, critic_obs_dim), dtype=np.float32)
        self.raw_actions = np.zeros((n_steps, flat, 4), dtype=np.int64)
        self.log_probs = np.zeros((n_steps, flat), dtype=np.float32)
        self.values = np.zeros((n_steps, flat), dtype=np.float32)
        self.rewards = np.zeros((n_steps, flat), dtype=np.float32)
        self.dones = np.zeros((n_steps, flat), dtype=np.float32)

    def insert(
        self,
        obs: NDArray[np.float32],
        critic_obs: NDArray[np.float32],
        raw_actions: NDArray[np.int64],
        log_probs: NDArray[np.float32],
        values: NDArray[np.float32],
        rewards: NDArray[np.float32],
        dones: NDArray[np.bool_],
    ) -> None:
        """Insert one timestep of data.

        Args:
            obs: [N, S, obs_dim]
            critic_obs: [N, S, critic_obs_dim]
            raw_actions: [N, S, 4] categorical indices
            log_probs: [N, S]
            values: [N, S]
            rewards: [N, S]
            dones: [N] broadcast to [N, S]
        """
        N, S = self.n_envs, self.n_ships
        # Broadcast dones [N] -> [N, S]
        if dones.ndim == 1:
            dones_flat = np.broadcast_to(
                dones[:, np.newaxis], (N, S)
            ).reshape(-1)
        else:
            dones_flat = dones.reshape(-1)

        t = self.ptr
        self.obs[t] = obs.reshape(-1, self.obs_dim)
        self.critic_obs[t] = critic_obs.reshape(-1, self.critic_obs_dim)
        self.raw_actions[t] = raw_actions.reshape(-1, 4)
        self.log_probs[t] = log_probs.reshape(-1)
        self.values[t] = values.reshape(-1)
        self.rewards[t] = rewards.reshape(-1)
        self.dones[t] = dones_flat.astype(np.float32)
        self.ptr += 1

    def compute_gae(
        self,
        last_values: NDArray[np.float32],
        last_dones: NDArray[np.bool_],
        gamma: float = 0.99,
        lam: float = 0.95,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Compute GAE advantages and returns.

        Args:
            last_values: [N, S] value estimates for the state after the last step.
            last_dones: [N] done flags for the last step.
            gamma: Discount factor.
            lam: GAE lambda.

        Returns:
            (advantages, returns) each shape [T * N * S].
        """
        N, S = self.n_envs, self.n_ships
        flat = N * S
        T = self.n_steps

        if last_dones.ndim == 1:
            last_dones_flat = np.broadcast_to(
                last_dones[:, np.newaxis], (N, S)
            ).reshape(-1)
        else:
            last_dones_flat = last_dones.reshape(-1)

        advantages = np.zeros((T, flat), dtype=np.float32)
        last_gae = np.zeros(flat, dtype=np.float32)
        next_values = last_values.reshape(-1)
        next_nonterminal = 1.0 - last_dones_flat.astype(np.float32)

        for t in reversed(range(T)):
            delta = (
                self.rewards[t]
                + gamma * next_values * next_nonterminal
                - self.values[t]
            )
            last_gae = delta + gamma * lam * next_nonterminal * last_gae
            advantages[t] = last_gae

            next_values = self.values[t]
            next_nonterminal = 1.0 - self.dones[t]

        returns = advantages + self.values

        return (
            torch.from_numpy(advantages.reshape(-1)),
            torch.from_numpy(returns.reshape(-1)),
        )

    def get_flat_tensors(self) -> tuple[torch.Tensor, ...]:
        """Return all stored data as flat tensors for minibatch sampling.

        Returns:
            (obs, critic_obs, raw_actions, log_probs, values) each flattened.
        """
        total = self.n_steps * self.n_envs * self.n_ships
        return (
            torch.from_numpy(self.obs.reshape(total, self.obs_dim)),
            torch.from_numpy(self.critic_obs.reshape(total, self.critic_obs_dim)),
            torch.from_numpy(self.raw_actions.reshape(total, 4)),
            torch.from_numpy(self.log_probs.reshape(total)),
            torch.from_numpy(self.values.reshape(total)),
        )

    def reset(self) -> None:
        """Reset pointer for next rollout."""
        self.ptr = 0
