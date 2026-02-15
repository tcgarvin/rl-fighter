"""Rollout buffer for MAPPO training.

Stores transitions from parallel environments and computes GAE advantages.
Stores both per-agent obs and centralized critic obs.
Supports tail buffer for deferred GAE finalization (credit assignment).
"""

from __future__ import annotations

import torch
import numpy as np
from numpy.typing import NDArray


class RolloutBuffer:
    """Fixed-size buffer for one rollout phase (T steps x N envs x S ships).

    Stores observations, critic observations, actions (raw categorical indices),
    log_probs, values, rewards, and dones. Computes GAE returns on demand.

    When t_tail > 0, internal arrays are sized (n_steps + t_tail) to hold
    prepended tail data from the previous rollout.
    """

    def __init__(
        self,
        n_steps: int,
        n_envs: int,
        n_ships: int,
        obs_dim: int,
        critic_obs_dim: int,
        t_tail: int = 0,
    ) -> None:
        self.n_steps = n_steps
        self.n_envs = n_envs
        self.n_ships = n_ships
        self.obs_dim = obs_dim
        self.critic_obs_dim = critic_obs_dim
        self.t_tail = t_tail
        self.ptr = 0

        flat = n_envs * n_ships
        buf_len = n_steps + t_tail

        self.obs = np.zeros((buf_len, flat, obs_dim), dtype=np.float32)
        self.critic_obs = np.zeros((buf_len, flat, critic_obs_dim), dtype=np.float32)
        self.raw_actions = np.zeros((buf_len, flat, 5), dtype=np.int64)
        self.log_probs = np.zeros((buf_len, flat), dtype=np.float32)
        self.values = np.zeros((buf_len, flat), dtype=np.float32)
        self.rewards = np.zeros((buf_len, flat), dtype=np.float32)
        self.dones = np.zeros((buf_len, flat), dtype=np.float32)

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
            raw_actions: [N, S, 5] categorical indices
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
        self.raw_actions[t] = raw_actions.reshape(-1, 5)
        self.log_probs[t] = log_probs.reshape(-1)
        self.values[t] = values.reshape(-1)
        self.rewards[t] = rewards.reshape(-1)
        self.dones[t] = dones_flat.astype(np.float32)
        self.ptr += 1

    def prepend_tail(self, tail_data: dict[str, NDArray]) -> None:
        """Copy saved tail data into the first t_tail slots.

        Args:
            tail_data: Dict with keys matching buffer arrays, each shaped
                       [t_tail, flat, ...].
        """
        t = self.t_tail
        self.obs[:t] = tail_data["obs"]
        self.critic_obs[:t] = tail_data["critic_obs"]
        self.raw_actions[:t] = tail_data["raw_actions"]
        self.log_probs[:t] = tail_data["log_probs"]
        self.values[:t] = tail_data["values"]
        self.rewards[:t] = tail_data["rewards"]
        self.dones[:t] = tail_data["dones"]
        self.ptr = t

    def extract_tail(self) -> dict[str, NDArray]:
        """Save the last t_tail steps for the next rollout.

        Returns:
            Dict with copies of the tail portion of each buffer array.
        """
        t = self.t_tail
        start = self.ptr - t
        return {
            "obs": self.obs[start:self.ptr].copy(),
            "critic_obs": self.critic_obs[start:self.ptr].copy(),
            "raw_actions": self.raw_actions[start:self.ptr].copy(),
            "log_probs": self.log_probs[start:self.ptr].copy(),
            "values": self.values[start:self.ptr].copy(),
            "rewards": self.rewards[start:self.ptr].copy(),
            "dones": self.dones[start:self.ptr].copy(),
        }

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
        return self.compute_gae_with_tail(
            last_values, last_dones, gamma, lam, tail_size=0,
        )

    def compute_gae_with_tail(
        self,
        last_values: NDArray[np.float32],
        last_dones: NDArray[np.bool_],
        gamma: float = 0.99,
        lam: float = 0.95,
        tail_size: int = 0,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Compute GAE over full range, return advantages/returns for non-tail steps only.

        Args:
            last_values: [N, S] value estimates for the state after the last step.
            last_dones: [N] done flags for the last step.
            gamma: Discount factor.
            lam: GAE lambda.
            tail_size: Number of prepended tail steps to exclude from output.

        Returns:
            (advantages, returns) each shape [(T - tail_size) * N * S].
        """
        N, S = self.n_envs, self.n_ships
        flat = N * S
        T = tail_size + self.n_steps  # total steps in buffer

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

        returns = advantages + self.values[:T]

        # Only return non-tail steps
        out_adv = advantages[tail_size:T]
        out_ret = returns[tail_size:T]

        return (
            torch.from_numpy(out_adv.reshape(-1).copy()),
            torch.from_numpy(out_ret.reshape(-1).copy()),
        )

    def get_flat_tensors(self, skip: int = 0) -> tuple[torch.Tensor, ...]:
        """Return stored data as flat tensors for minibatch sampling.

        Args:
            skip: Number of leading steps to skip (e.g., tail steps).

        Returns:
            (obs, critic_obs, raw_actions, log_probs, values) each flattened.
        """
        end = skip + self.n_steps
        total = self.n_steps * self.n_envs * self.n_ships
        return (
            torch.from_numpy(self.obs[skip:end].reshape(total, self.obs_dim).copy()),
            torch.from_numpy(self.critic_obs[skip:end].reshape(total, self.critic_obs_dim).copy()),
            torch.from_numpy(self.raw_actions[skip:end].reshape(total, 5).copy()),
            torch.from_numpy(self.log_probs[skip:end].reshape(total).copy()),
            torch.from_numpy(self.values[skip:end].reshape(total).copy()),
        )

    def reset(self) -> None:
        """Reset pointer for next rollout."""
        self.ptr = 0
