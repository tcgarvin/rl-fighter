"""MLP actor-critic policy for MAPPO space combat.

Separate actor (per-agent obs) and centralized critic (team obs) networks
with multi-head discrete action output.
"""

from __future__ import annotations

import torch
import torch.nn as nn
from torch.distributions import Categorical

OBS_DIM = 36
CRITIC_OBS_DIM = OBS_DIM * 2  # concatenated team observations for 2v2
HIDDEN = 256

# Action head sizes: turn(3), thrust(2), brake(2), fire(2)
ACTION_HEADS = [3, 2, 2, 2]

# Map turn categorical index {0,1,2} -> {-1,0,1}
TURN_MAP = torch.tensor([-1, 0, 1], dtype=torch.int32)


class Actor(nn.Module):
    """Multi-head actor producing 4 independent categorical distributions."""

    def __init__(self) -> None:
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Linear(OBS_DIM, HIDDEN),
            nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN),
            nn.ReLU(),
        )
        self.heads = nn.ModuleList(
            [nn.Linear(HIDDEN, n) for n in ACTION_HEADS]
        )

    def forward(self, obs: torch.Tensor) -> list[Categorical]:
        """Return a list of Categorical distributions, one per action head."""
        features = self.trunk(obs)
        return [Categorical(logits=head(features)) for head in self.heads]


class CentralizedCritic(nn.Module):
    """Centralized state-value critic V(s) for MAPPO.

    Takes concatenated observations from all teammates as input.
    """

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(CRITIC_OBS_DIM, HIDDEN),
            nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN),
            nn.ReLU(),
            nn.Linear(HIDDEN, 1),
        )

    def forward(self, critic_obs: torch.Tensor) -> torch.Tensor:
        """Return value estimate, shape [..., 1]."""
        return self.net(critic_obs)


class ActorCritic(nn.Module):
    """Combined actor-critic with MAPPO centralized critic."""

    def __init__(self) -> None:
        super().__init__()
        self.actor = Actor()
        self.critic = CentralizedCritic()

    def forward(
        self, obs: torch.Tensor, critic_obs: torch.Tensor
    ) -> tuple[list[Categorical], torch.Tensor]:
        """Return (distributions, values).

        Args:
            obs: Per-agent observations, shape [*, OBS_DIM].
            critic_obs: Team-concatenated observations, shape [*, CRITIC_OBS_DIM].
        """
        dists = self.actor(obs)
        values = self.critic(critic_obs).squeeze(-1)
        return dists, values

    def get_action_and_value(
        self, obs: torch.Tensor, critic_obs: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Sample actions, return (actions, log_prob, entropy, value).

        Args:
            obs: Per-agent observation tensor, shape [*, OBS_DIM].
            critic_obs: Team-concatenated observations, shape [*, CRITIC_OBS_DIM].

        Returns:
            actions: [*, 4] int32 tensor (turn already mapped to -1/0/1).
            log_prob: [*] total log probability.
            entropy: [*] total entropy.
            value: [*] value estimate.
        """
        dists, values = self(obs, critic_obs)
        raw_actions = [d.sample() for d in dists]
        log_probs = sum(d.log_prob(a) for d, a in zip(dists, raw_actions))
        entropies = sum(d.entropy() for d in dists)

        # Stack raw categorical indices: [*, 4]
        action_stack = torch.stack(raw_actions, dim=-1)

        # Map turn index {0,1,2} -> {-1,0,1}
        turn_mapped = TURN_MAP.to(obs.device)[action_stack[..., 0]]
        actions = action_stack.clone()
        actions[..., 0] = turn_mapped

        return actions.to(torch.int32), log_probs, entropies, values

    def evaluate_actions(
        self, obs: torch.Tensor, critic_obs: torch.Tensor, raw_actions: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Evaluate log_prob and entropy for given raw actions (categorical indices).

        Args:
            obs: [*, OBS_DIM]
            critic_obs: [*, CRITIC_OBS_DIM]
            raw_actions: [*, 4] categorical indices (turn as 0/1/2, not -1/0/1).

        Returns:
            log_prob: [*] total log probability.
            entropy: [*] total entropy.
            value: [*] value estimate.
        """
        dists, values = self(obs, critic_obs)
        log_probs = sum(
            d.log_prob(raw_actions[..., i]) for i, d in enumerate(dists)
        )
        entropies = sum(d.entropy() for d in dists)
        return log_probs, entropies, values
