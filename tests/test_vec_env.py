"""Tests for VecEnv wrapper with 2v2 matches."""

import numpy as np
import pytest

from spacefight.env.vec_env import VecEnv, build_critic_obs
from spacefight.rl.obs import OBS_DIM

N_SHIPS = 4


class TestVecEnv:
    def test_reset_returns_obs(self):
        env = VecEnv(n_envs=4, seed=0)
        obs = env.reset()

        assert obs.shape == (4, N_SHIPS, OBS_DIM)
        assert obs.dtype == np.float32

    def test_step_returns_correct_shapes(self):
        env = VecEnv(n_envs=4, seed=0)
        env.reset()

        actions = np.zeros((4, N_SHIPS, 5), dtype=np.int32)
        obs, rewards, dones, infos = env.step(actions)

        assert obs.shape == (4, N_SHIPS, OBS_DIM)
        assert rewards.shape == (4, N_SHIPS)
        assert dones.shape == (4,)

    def test_step_without_reset_raises(self):
        env = VecEnv(n_envs=4, seed=0)
        with pytest.raises(RuntimeError, match="not reset"):
            actions = np.zeros((4, N_SHIPS, 5), dtype=np.int32)
            env.step(actions)

    def test_n256_runs(self):
        """Verify N=256 parallel 2v2 matches work."""
        env = VecEnv(n_envs=256, seed=42)
        obs = env.reset()
        assert obs.shape == (256, N_SHIPS, OBS_DIM)

        actions = np.zeros((256, N_SHIPS, 5), dtype=np.int32)
        actions[:, :, 1] = 1  # thrust
        actions[:, 0, 3] = 1  # ship 0 fires

        for _ in range(10):
            obs, rewards, dones, infos = env.step(actions)

        assert obs.shape == (256, N_SHIPS, OBS_DIM)

    def test_deterministic_vec_env(self):
        """Same seed produces identical observations across runs."""
        def run_vec(seed):
            env = VecEnv(n_envs=8, seed=seed)
            obs = env.reset()
            actions = np.ones((8, N_SHIPS, 5), dtype=np.int32)
            actions[:, :, 0] = 0  # no turn
            for _ in range(50):
                obs, _, _, _ = env.step(actions)
            return obs

        obs_a = run_vec(seed=123)
        obs_b = run_vec(seed=123)
        np.testing.assert_array_equal(obs_a, obs_b)

    def test_auto_reset_on_done(self):
        """When a team is eliminated, the environment auto-resets."""
        env = VecEnv(n_envs=2, seed=0)
        env.reset()

        # Kill all of team 1 in env 0 (ships 2 and 3)
        env.state.hull[0, 2] = 0.0
        env.state.alive[0, 2] = False
        env.state.hull[0, 3] = 0.0
        env.state.alive[0, 3] = False

        actions = np.zeros((2, N_SHIPS, 5), dtype=np.int32)
        obs, rewards, dones, infos = env.step(actions)

        # Env 0 should be done
        assert dones[0]
        # After auto-reset, all ships should be restored
        assert env.state.hull[0, 2] > 0.0
        assert env.state.alive[0, 2]
        assert env.state.hull[0, 3] > 0.0
        assert env.state.alive[0, 3]

    def test_time_limit(self):
        """Episodes end after max_steps."""
        env = VecEnv(n_envs=1, seed=0, max_steps=5)
        env.reset()
        actions = np.zeros((1, N_SHIPS, 5), dtype=np.int32)

        for i in range(5):
            obs, rewards, dones, infos = env.step(actions)

        assert dones[0]

    def test_team_assignment(self):
        """Ships 0,1 should be team 0 and ships 2,3 should be team 1."""
        env = VecEnv(n_envs=2, seed=0)
        env.reset()

        assert env.state.team[0, 0] == 0
        assert env.state.team[0, 1] == 0
        assert env.state.team[0, 2] == 1
        assert env.state.team[0, 3] == 1

    def test_randomize_hulls(self):
        """With randomize_hulls=True, different hull types should appear."""
        env = VecEnv(n_envs=1, seed=42, randomize_hulls=True)
        # Run multiple resets to collect hull types
        hull_types_seen = set()
        for _ in range(20):
            env.reset()
            for s in range(N_SHIPS):
                hull_types_seen.add(float(env.state.max_hull[0, s]))

        # Should see more than one hull type
        assert len(hull_types_seen) > 1


class TestBuildCriticObs:
    def test_critic_obs_shape(self):
        obs = np.random.randn(4, N_SHIPS, OBS_DIM).astype(np.float32)
        critic_obs = build_critic_obs(obs, N_SHIPS)
        assert critic_obs.shape == (4, N_SHIPS, OBS_DIM * 2)

    def test_critic_obs_contains_own_and_teammate(self):
        """First half should be own obs, second half teammate obs."""
        obs = np.random.randn(2, N_SHIPS, OBS_DIM).astype(np.float32)
        critic_obs = build_critic_obs(obs, N_SHIPS)

        # Ship 0 should see [obs[0], obs[1]]
        np.testing.assert_array_equal(critic_obs[:, 0, :OBS_DIM], obs[:, 0])
        np.testing.assert_array_equal(critic_obs[:, 0, OBS_DIM:], obs[:, 1])

        # Ship 1 should see [obs[1], obs[0]]
        np.testing.assert_array_equal(critic_obs[:, 1, :OBS_DIM], obs[:, 1])
        np.testing.assert_array_equal(critic_obs[:, 1, OBS_DIM:], obs[:, 0])

        # Ship 2 should see [obs[2], obs[3]]
        np.testing.assert_array_equal(critic_obs[:, 2, :OBS_DIM], obs[:, 2])
        np.testing.assert_array_equal(critic_obs[:, 2, OBS_DIM:], obs[:, 3])
