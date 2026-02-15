"""MAPPO clipped objective update with centralized critic."""

from __future__ import annotations

import torch
import torch.nn as nn

from spacefight.rl.policy import ActorCritic


def ppo_update(
    model: ActorCritic,
    optimizer: torch.optim.Optimizer,
    obs: torch.Tensor,
    critic_obs: torch.Tensor,
    raw_actions: torch.Tensor,
    old_log_probs: torch.Tensor,
    advantages: torch.Tensor,
    returns: torch.Tensor,
    clip_eps: float = 0.2,
    vf_coeff: float = 0.5,
    ent_coeff: float = 0.01,
    max_grad_norm: float = 0.5,
    k_epochs: int = 4,
    batch_size: int = 512,
) -> dict[str, float]:
    """Run K epochs of MAPPO clipped updates on the given rollout data.

    Args:
        model: ActorCritic network.
        optimizer: Optimizer for model parameters.
        obs: [total, obs_dim] flattened per-agent observations.
        critic_obs: [total, critic_obs_dim] flattened centralized critic observations.
        raw_actions: [total, 4] raw categorical indices.
        old_log_probs: [total] log probs from collection policy.
        advantages: [total] GAE advantages.
        returns: [total] GAE returns (targets for value function).
        clip_eps: PPO clip epsilon.
        vf_coeff: Value function loss coefficient.
        ent_coeff: Entropy bonus coefficient.
        max_grad_norm: Max gradient norm for clipping.
        k_epochs: Number of passes over the data.
        batch_size: Minibatch size.

    Returns:
        Dict of mean loss components for logging.
    """
    total = obs.shape[0]
    device = next(model.parameters()).device

    # Move all data to GPU once (avoids per-minibatch H2D transfers)
    obs = obs.to(device)
    critic_obs = critic_obs.to(device)
    raw_actions = raw_actions.to(device)
    old_log_probs = old_log_probs.to(device)
    advantages = advantages.to(device)
    returns = returns.to(device)

    # Normalize advantages
    adv_mean = advantages.mean()
    adv_std = advantages.std()
    advantages = (advantages - adv_mean) / (adv_std + 1e-8)

    total_pg_loss = 0.0
    total_vf_loss = 0.0
    total_entropy = 0.0
    n_updates = 0

    for _ in range(k_epochs):
        indices = torch.randperm(total, device=device)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            mb_idx = indices[start:end]

            mb_obs = obs[mb_idx]
            mb_critic_obs = critic_obs[mb_idx]
            mb_actions = raw_actions[mb_idx]
            mb_old_lp = old_log_probs[mb_idx]
            mb_adv = advantages[mb_idx]
            mb_ret = returns[mb_idx]

            new_log_probs, entropy, values = model.evaluate_actions(
                mb_obs, mb_critic_obs, mb_actions
            )

            # Policy loss (clipped surrogate)
            ratio = torch.exp(new_log_probs - mb_old_lp)
            surr1 = ratio * mb_adv
            surr2 = torch.clamp(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * mb_adv
            pg_loss = -torch.min(surr1, surr2).mean()

            # Value loss
            vf_loss = nn.functional.mse_loss(values, mb_ret)

            # Entropy bonus
            ent_loss = entropy.mean()

            loss = pg_loss + vf_coeff * vf_loss - ent_coeff * ent_loss

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            optimizer.step()

            total_pg_loss += pg_loss.item()
            total_vf_loss += vf_loss.item()
            total_entropy += ent_loss.item()
            n_updates += 1

    return {
        "pg_loss": total_pg_loss / max(n_updates, 1),
        "vf_loss": total_vf_loss / max(n_updates, 1),
        "entropy": total_entropy / max(n_updates, 1),
    }
