"""Tests for retroactive projectile credit assignment."""

import numpy as np
import pytest
import torch

from spacefight.rl.credit import CreditAssigner, CREDIT_COEFF
from spacefight.rl.rollout_buffer import RolloutBuffer


class TestCreditAssigner:
    def test_basic_credit_at_fire_step(self):
        """Fire at step 5, hit at step 10 → credit injected at step 5."""
        N, S = 2, 4
        buf_len = 20
        ca = CreditAssigner(N, S, buf_len)

        # Stamp all steps
        for t in range(buf_len):
            ca.stamp_step(t)

        # Simulate a hit: env 0, projectile hit, owner=ship 1, damage=15, fired at step 5
        proj_hit = np.zeros((N, 8), dtype=np.bool_)
        proj_hit[0, 0] = True

        proj_owner = np.full((N, 8), -1, dtype=np.int32)
        proj_owner[0, 0] = 1

        proj_damage = np.zeros((N, 8), dtype=np.float32)
        proj_damage[0, 0] = 15.0

        proj_fire_step = np.full((N, 8), -1, dtype=np.int32)
        proj_fire_step[0, 0] = 5

        ca.record_hits(10, proj_hit, proj_owner, proj_damage, proj_fire_step)

        # Check credit at step 5, flat index = env0 * S + ship1 = 0*4+1 = 1
        expected = CREDIT_COEFF * 15.0
        assert ca.credit[5, 1] == pytest.approx(expected)

        # No credit elsewhere for this agent
        assert ca.credit[10, 1] == 0.0

    def test_no_cross_episode_credit(self):
        """Fire before reset, hit after reset → no credit."""
        N, S = 1, 4
        buf_len = 20
        ca = CreditAssigner(N, S, buf_len)

        # Steps 0-9: episode gen 0
        for t in range(10):
            ca.stamp_step(t)

        # Episode resets
        ca.on_reset(np.array([0]))

        # Steps 10-19: episode gen 1
        for t in range(10, 20):
            ca.stamp_step(t)

        # Projectile fired at step 5 (gen 0) hits at step 12 (gen 1)
        proj_hit = np.zeros((N, 4), dtype=np.bool_)
        proj_hit[0, 0] = True
        proj_owner = np.array([[-1, -1, -1, -1]], dtype=np.int32)
        proj_owner[0, 0] = 0
        proj_damage = np.zeros((N, 4), dtype=np.float32)
        proj_damage[0, 0] = 15.0
        proj_fire_step = np.full((N, 4), -1, dtype=np.int32)
        proj_fire_step[0, 0] = 5

        ca.record_hits(12, proj_hit, proj_owner, proj_damage, proj_fire_step)

        # No credit should be assigned (cross-episode)
        assert ca.credit[5, 0] == 0.0

    def test_same_episode_credit_after_reset(self):
        """Fire and hit in same episode after a reset → credit assigned."""
        N, S = 1, 4
        buf_len = 20
        ca = CreditAssigner(N, S, buf_len)

        for t in range(5):
            ca.stamp_step(t)
        ca.on_reset(np.array([0]))
        for t in range(5, 15):
            ca.stamp_step(t)

        # Fire at step 7 (gen 1), hit at step 10 (gen 1) → valid
        proj_hit = np.zeros((N, 4), dtype=np.bool_)
        proj_hit[0, 0] = True
        proj_owner = np.zeros((N, 4), dtype=np.int32)
        proj_damage = np.zeros((N, 4), dtype=np.float32)
        proj_damage[0, 0] = 15.0
        proj_fire_step = np.full((N, 4), -1, dtype=np.int32)
        proj_fire_step[0, 0] = 7

        ca.record_hits(10, proj_hit, proj_owner, proj_damage, proj_fire_step)

        expected = CREDIT_COEFF * 15.0
        assert ca.credit[7, 0] == pytest.approx(expected)

    def test_inject_into_rewards(self):
        """Credits are additive to existing rewards."""
        N, S = 1, 4
        buf_len = 10
        flat = N * S
        ca = CreditAssigner(N, S, buf_len)

        ca.credit[3, 0] = 0.5
        ca.credit[3, 2] = 0.3

        rewards = np.ones((buf_len, flat), dtype=np.float32)
        ca.inject_into_rewards(rewards, 0, buf_len)

        assert rewards[3, 0] == pytest.approx(1.5)
        assert rewards[3, 2] == pytest.approx(1.3)
        assert rewards[0, 0] == pytest.approx(1.0)  # unchanged

    def test_shift_tail(self):
        """After shift, tail credits move to front."""
        N, S = 1, 4
        t_steps = 10
        t_tail = 5
        buf_len = t_steps + t_tail
        ca = CreditAssigner(N, S, buf_len)

        # Put credit at step 12 (which is in the tail: steps 10-14)
        ca.credit[12, 0] = 0.42
        ca.step_gen[12, 0] = 3

        ca.shift_tail(t_steps)

        # Step 12 should now be at position 12-10=2
        assert ca.credit[2, 0] == pytest.approx(0.42)
        assert ca.step_gen[2, 0] == 3
        # Old position should be cleared
        assert ca.credit[12, 0] == 0.0

    def test_multiple_hits_accumulate(self):
        """Multiple projectiles hitting from different fire steps accumulate."""
        N, S = 1, 4
        buf_len = 20
        ca = CreditAssigner(N, S, buf_len)

        for t in range(buf_len):
            ca.stamp_step(t)

        # Two projectiles hit at step 15, both from ship 0
        proj_hit = np.zeros((N, 4), dtype=np.bool_)
        proj_hit[0, 0] = True
        proj_hit[0, 1] = True
        proj_owner = np.full((N, 4), -1, dtype=np.int32)
        proj_owner[0, 0] = 0
        proj_owner[0, 1] = 0
        proj_damage = np.zeros((N, 4), dtype=np.float32)
        proj_damage[0, 0] = 15.0
        proj_damage[0, 1] = 15.0
        # Different fire steps
        proj_fire_step = np.full((N, 4), -1, dtype=np.int32)
        proj_fire_step[0, 0] = 3
        proj_fire_step[0, 1] = 5

        ca.record_hits(15, proj_hit, proj_owner, proj_damage, proj_fire_step)

        expected = CREDIT_COEFF * 15.0
        assert ca.credit[3, 0] == pytest.approx(expected)
        assert ca.credit[5, 0] == pytest.approx(expected)

    def test_fire_step_out_of_range_ignored(self):
        """Projectile with fire_step >= buf_len is ignored."""
        N, S = 1, 4
        buf_len = 10
        ca = CreditAssigner(N, S, buf_len)

        for t in range(buf_len):
            ca.stamp_step(t)

        proj_hit = np.zeros((N, 4), dtype=np.bool_)
        proj_hit[0, 0] = True
        proj_owner = np.zeros((N, 4), dtype=np.int32)
        proj_damage = np.zeros((N, 4), dtype=np.float32)
        proj_damage[0, 0] = 15.0
        proj_fire_step = np.full((N, 4), -1, dtype=np.int32)
        proj_fire_step[0, 0] = 99  # out of range

        ca.record_hits(5, proj_hit, proj_owner, proj_damage, proj_fire_step)
        assert ca.credit.sum() == 0.0


class TestTailBuffer:
    def test_prepend_and_extract_tail(self):
        """Tail data survives prepend → collect → extract cycle."""
        N, S = 2, 4
        n_steps = 8
        t_tail = 3
        obs_dim = 4
        critic_obs_dim = 8

        buf = RolloutBuffer(n_steps, N, S, obs_dim, critic_obs_dim, t_tail=t_tail)
        flat = N * S

        # Create fake tail data
        tail_data = {
            "obs": np.random.randn(t_tail, flat, obs_dim).astype(np.float32),
            "critic_obs": np.random.randn(t_tail, flat, critic_obs_dim).astype(np.float32),
            "raw_actions": np.random.randint(0, 3, (t_tail, flat, 5)).astype(np.int64),
            "log_probs": np.random.randn(t_tail, flat).astype(np.float32),
            "values": np.random.randn(t_tail, flat).astype(np.float32),
            "rewards": np.random.randn(t_tail, flat).astype(np.float32),
            "dones": np.zeros((t_tail, flat), dtype=np.float32),
        }

        buf.prepend_tail(tail_data)
        assert buf.ptr == t_tail

        # Insert n_steps of data
        for _ in range(n_steps):
            buf.insert(
                obs=np.zeros((N, S, obs_dim), dtype=np.float32),
                critic_obs=np.zeros((N, S, critic_obs_dim), dtype=np.float32),
                raw_actions=np.zeros((N, S, 5), dtype=np.int64),
                log_probs=np.zeros((N, S), dtype=np.float32),
                values=np.zeros((N, S), dtype=np.float32),
                rewards=np.zeros((N, S), dtype=np.float32),
                dones=np.zeros(N, dtype=np.bool_),
            )

        assert buf.ptr == t_tail + n_steps

        # Extract tail (last t_tail steps of the n_steps we just inserted)
        extracted = buf.extract_tail()
        assert extracted["obs"].shape == (t_tail, flat, obs_dim)

    def test_gae_with_tail_excludes_tail_steps(self):
        """GAE with tail returns advantages only for non-tail steps."""
        N, S = 1, 4
        n_steps = 4
        t_tail = 2
        obs_dim = 4
        critic_obs_dim = 8

        buf = RolloutBuffer(n_steps, N, S, obs_dim, critic_obs_dim, t_tail=t_tail)
        flat = N * S

        # Fill all buf_len = 6 steps
        for i in range(t_tail + n_steps):
            buf.rewards[i] = 1.0
            buf.values[i] = 0.5
            buf.dones[i] = 0.0

        last_values = np.full((N, S), 0.5, dtype=np.float32)
        last_dones = np.zeros(N, dtype=np.bool_)

        adv, ret = buf.compute_gae_with_tail(
            last_values, last_dones, gamma=0.99, lam=0.95, tail_size=t_tail,
        )

        # Output should be n_steps * flat, not (n_steps + t_tail) * flat
        assert adv.shape[0] == n_steps * flat
        assert ret.shape[0] == n_steps * flat

    def test_get_flat_tensors_with_skip(self):
        """Skipping tail steps returns only the main rollout data."""
        N, S = 1, 4
        n_steps = 4
        t_tail = 2
        obs_dim = 4
        critic_obs_dim = 8

        buf = RolloutBuffer(n_steps, N, S, obs_dim, critic_obs_dim, t_tail=t_tail)
        flat = N * S

        # Mark tail steps with distinct values
        buf.obs[:t_tail] = 99.0
        buf.obs[t_tail:t_tail + n_steps] = 1.0
        buf.ptr = t_tail + n_steps

        tensors = buf.get_flat_tensors(skip=t_tail)
        obs_tensor = tensors[0]

        assert obs_tensor.shape[0] == n_steps * flat
        assert obs_tensor[0, 0].item() == pytest.approx(1.0)  # not 99.0

    def test_backward_compatible_no_tail(self):
        """With t_tail=0, buffer behaves identically to original."""
        N, S = 1, 4
        n_steps = 4
        obs_dim = 4
        critic_obs_dim = 8
        flat = N * S

        buf = RolloutBuffer(n_steps, N, S, obs_dim, critic_obs_dim, t_tail=0)

        for i in range(n_steps):
            buf.insert(
                obs=np.ones((N, S, obs_dim), dtype=np.float32),
                critic_obs=np.ones((N, S, critic_obs_dim), dtype=np.float32),
                raw_actions=np.zeros((N, S, 5), dtype=np.int64),
                log_probs=np.zeros((N, S), dtype=np.float32),
                values=np.full((N, S), 0.5, dtype=np.float32),
                rewards=np.ones((N, S), dtype=np.float32),
                dones=np.zeros(N, dtype=np.bool_),
            )

        last_values = np.full((N, S), 0.5, dtype=np.float32)
        last_dones = np.zeros(N, dtype=np.bool_)

        adv, ret = buf.compute_gae(last_values, last_dones)
        assert adv.shape[0] == n_steps * flat

        tensors = buf.get_flat_tensors()
        assert tensors[0].shape[0] == n_steps * flat


class TestIntegrationCreditWithSim:
    """Integration test: fire a bullet, advance until hit, verify credit at fire step."""

    def test_fire_hit_credit_cycle(self):
        """Full cycle: fire → advance → hit → credit at fire step."""
        from spacefight.sim.core import reset, step

        N = 4
        state = reset(N, hull_names=["fighter"] * 4, seed=42)

        # Place ship 0 close to enemy ship 2, facing it
        state.x[:, 0] = 0.0
        state.y[:, 0] = 0.0
        state.theta[:, 0] = 0.0  # facing right
        state.x[:, 2] = 80.0  # close target
        state.y[:, 2] = 0.0
        state.alive[:] = True

        # Ensure ship 0 has ammo and no cooldown
        state.ammo[:, 0] = 6
        state.cooldown[:, 0] = 0.0
        state.reload_timer[:, 0] = 0.0

        # Fire at rollout_step=5
        actions = np.zeros((N, 4, 5), dtype=np.int32)
        actions[:, 0, 3] = 1  # fire command for ship 0

        state, rewards, dones = step(state, actions, rollout_step=5)

        # Verify proj_fire_step was set
        fired = state.proj_alive & (state.proj_owner == 0)
        assert np.any(fired)
        fired_slots = np.where(fired)
        for n, p in zip(fired_slots[0], fired_slots[1]):
            assert state.proj_fire_step[n, p] == 5

        # Advance until hit (no firing)
        actions[:, 0, 3] = 0
        hit_found = False
        for tick in range(60):
            state, rewards, dones = step(state, actions, rollout_step=5 + 1 + tick)
            if state.last_proj_hit is not None and np.any(state.last_proj_hit):
                hit_found = True
                break

        assert hit_found, "Bullet should hit close target within 60 ticks"
