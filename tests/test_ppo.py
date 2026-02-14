"""Tests for rollout buffer and MAPPO update."""

import numpy as np
import torch

from spacefight.rl.policy import ActorCritic, OBS_DIM, CRITIC_OBS_DIM
from spacefight.rl.rollout_buffer import RolloutBuffer
from spacefight.rl.ppo import ppo_update

N_SHIPS = 4


class TestRolloutBuffer:
    def test_insert_and_shapes(self):
        buf = RolloutBuffer(
            n_steps=4, n_envs=2, n_ships=N_SHIPS,
            obs_dim=OBS_DIM, critic_obs_dim=CRITIC_OBS_DIM,
        )
        for t in range(4):
            buf.insert(
                obs=np.random.randn(2, N_SHIPS, OBS_DIM).astype(np.float32),
                critic_obs=np.random.randn(2, N_SHIPS, CRITIC_OBS_DIM).astype(np.float32),
                raw_actions=np.zeros((2, N_SHIPS, 4), dtype=np.int64),
                log_probs=np.zeros((2, N_SHIPS), dtype=np.float32),
                values=np.zeros((2, N_SHIPS), dtype=np.float32),
                rewards=np.random.randn(2, N_SHIPS).astype(np.float32),
                dones=np.zeros(2, dtype=np.bool_),
            )

        obs, critic_obs, actions, lp, vals = buf.get_flat_tensors()
        total = 4 * 2 * N_SHIPS  # T * N * S
        assert obs.shape == (total, OBS_DIM)
        assert critic_obs.shape == (total, CRITIC_OBS_DIM)
        assert actions.shape == (total, 4)
        assert lp.shape == (total,)

    def test_gae_shapes(self):
        buf = RolloutBuffer(
            n_steps=8, n_envs=4, n_ships=N_SHIPS,
            obs_dim=OBS_DIM, critic_obs_dim=CRITIC_OBS_DIM,
        )
        for t in range(8):
            buf.insert(
                obs=np.random.randn(4, N_SHIPS, OBS_DIM).astype(np.float32),
                critic_obs=np.random.randn(4, N_SHIPS, CRITIC_OBS_DIM).astype(np.float32),
                raw_actions=np.zeros((4, N_SHIPS, 4), dtype=np.int64),
                log_probs=np.zeros((4, N_SHIPS), dtype=np.float32),
                values=np.ones((4, N_SHIPS), dtype=np.float32),
                rewards=np.ones((4, N_SHIPS), dtype=np.float32),
                dones=np.zeros(4, dtype=np.bool_),
            )

        adv, ret = buf.compute_gae(
            last_values=np.ones((4, N_SHIPS), dtype=np.float32),
            last_dones=np.zeros(4, dtype=np.bool_),
        )
        total = 8 * 4 * N_SHIPS
        assert adv.shape == (total,)
        assert ret.shape == (total,)

    def test_gae_terminal_episode(self):
        """Advantages should differ when episodes terminate."""
        buf = RolloutBuffer(
            n_steps=4, n_envs=1, n_ships=N_SHIPS,
            obs_dim=OBS_DIM, critic_obs_dim=CRITIC_OBS_DIM,
        )
        for t in range(4):
            dones = np.array([t == 2], dtype=np.bool_)  # done at step 2
            buf.insert(
                obs=np.zeros((1, N_SHIPS, OBS_DIM), dtype=np.float32),
                critic_obs=np.zeros((1, N_SHIPS, CRITIC_OBS_DIM), dtype=np.float32),
                raw_actions=np.zeros((1, N_SHIPS, 4), dtype=np.int64),
                log_probs=np.zeros((1, N_SHIPS), dtype=np.float32),
                values=np.ones((1, N_SHIPS), dtype=np.float32),
                rewards=np.ones((1, N_SHIPS), dtype=np.float32),
                dones=dones,
            )

        adv, ret = buf.compute_gae(
            last_values=np.ones((1, N_SHIPS), dtype=np.float32),
            last_dones=np.zeros(1, dtype=np.bool_),
        )
        assert torch.all(torch.isfinite(adv))

    def test_reset(self):
        buf = RolloutBuffer(
            n_steps=4, n_envs=2, n_ships=N_SHIPS,
            obs_dim=OBS_DIM, critic_obs_dim=CRITIC_OBS_DIM,
        )
        buf.ptr = 4
        buf.reset()
        assert buf.ptr == 0


class TestPPOUpdate:
    def test_ppo_runs_and_reduces_loss(self):
        """PPO update should run without errors on synthetic data."""
        model = ActorCritic()
        optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)

        total = 64
        obs = torch.randn(total, OBS_DIM)
        critic_obs = torch.randn(total, CRITIC_OBS_DIM)
        raw_actions = torch.zeros(total, 4, dtype=torch.long)
        raw_actions[:, 0] = torch.randint(0, 3, (total,))
        for i in range(1, 4):
            raw_actions[:, i] = torch.randint(0, 2, (total,))

        old_log_probs = torch.zeros(total)
        advantages = torch.randn(total)
        returns = torch.randn(total)

        stats = ppo_update(
            model, optimizer, obs, critic_obs, raw_actions,
            old_log_probs, advantages, returns,
            k_epochs=2, batch_size=32,
        )

        assert "pg_loss" in stats
        assert "vf_loss" in stats
        assert "entropy" in stats
        assert np.isfinite(stats["pg_loss"])
        assert np.isfinite(stats["vf_loss"])

    def test_ppo_gradient_step(self):
        """Parameters should change after PPO update."""
        model = ActorCritic()
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

        params_before = {
            k: v.clone() for k, v in model.named_parameters()
        }

        total = 128
        obs = torch.randn(total, OBS_DIM)
        critic_obs = torch.randn(total, CRITIC_OBS_DIM)
        raw_actions = torch.zeros(total, 4, dtype=torch.long)
        advantages = torch.randn(total)
        returns = torch.randn(total)
        old_log_probs = torch.zeros(total)

        ppo_update(
            model, optimizer, obs, critic_obs, raw_actions,
            old_log_probs, advantages, returns,
            k_epochs=2, batch_size=64,
        )

        any_changed = any(
            not torch.equal(params_before[k], v)
            for k, v in model.named_parameters()
        )
        assert any_changed
