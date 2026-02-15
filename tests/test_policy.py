"""Tests for MAPPO MLP actor-critic policy."""

import torch

from spacefight.rl.policy import ActorCritic, OBS_DIM, CRITIC_OBS_DIM


class TestActorCritic:
    def test_output_shapes(self):
        model = ActorCritic()
        obs = torch.randn(8, OBS_DIM)
        critic_obs = torch.randn(8, CRITIC_OBS_DIM)
        actions, log_prob, entropy, value = model.get_action_and_value(obs, critic_obs)

        assert actions.shape == (8, 5)
        assert log_prob.shape == (8,)
        assert entropy.shape == (8,)
        assert value.shape == (8,)

    def test_action_ranges(self):
        """Turn should be in {-1,0,1}, others in {0,1}."""
        model = ActorCritic()
        obs = torch.randn(256, OBS_DIM)
        critic_obs = torch.randn(256, CRITIC_OBS_DIM)
        actions, _, _, _ = model.get_action_and_value(obs, critic_obs)

        turn = actions[:, 0]
        assert torch.all((turn == -1) | (turn == 0) | (turn == 1))

        for i in range(1, 5):
            col = actions[:, i]
            assert torch.all((col == 0) | (col == 1))

    def test_evaluate_actions_matches(self):
        """evaluate_actions should return valid log_probs for sampled actions."""
        model = ActorCritic()
        obs = torch.randn(16, OBS_DIM)
        critic_obs = torch.randn(16, CRITIC_OBS_DIM)

        dists, values = model(obs, critic_obs)
        raw_actions = torch.stack([d.sample() for d in dists], dim=-1)

        log_prob, entropy, value = model.evaluate_actions(obs, critic_obs, raw_actions)

        assert log_prob.shape == (16,)
        assert entropy.shape == (16,)
        assert value.shape == (16,)
        assert torch.all(torch.isfinite(log_prob))
        assert torch.all(entropy >= 0)

    def test_batched_shapes(self):
        """Should handle multi-dimensional batch shapes."""
        model = ActorCritic()
        obs = torch.randn(4, 4, OBS_DIM)
        critic_obs = torch.randn(4, 4, CRITIC_OBS_DIM)
        actions, log_prob, entropy, value = model.get_action_and_value(obs, critic_obs)

        assert actions.shape == (4, 4, 5)
        assert log_prob.shape == (4, 4)
        assert value.shape == (4, 4)

    def test_gradient_flow(self):
        """Ensure gradients flow through both actor and critic."""
        model = ActorCritic()
        obs = torch.randn(8, OBS_DIM)
        critic_obs = torch.randn(8, CRITIC_OBS_DIM)

        _, log_prob, entropy, value = model.get_action_and_value(obs, critic_obs)
        loss = -log_prob.mean() + value.mean() - 0.01 * entropy.mean()
        loss.backward()

        actor_grads = any(
            p.grad is not None and p.grad.abs().sum() > 0
            for p in model.actor.parameters()
        )
        critic_grads = any(
            p.grad is not None and p.grad.abs().sum() > 0
            for p in model.critic.parameters()
        )
        assert actor_grads
        assert critic_grads

    def test_critic_uses_different_input(self):
        """Critic should produce different values for different critic_obs."""
        model = ActorCritic()
        obs = torch.randn(8, OBS_DIM)
        critic_obs_a = torch.randn(8, CRITIC_OBS_DIM)
        critic_obs_b = torch.randn(8, CRITIC_OBS_DIM)

        _, values_a = model(obs, critic_obs_a)
        _, values_b = model(obs, critic_obs_b)

        # Values should differ when critic input differs
        assert not torch.allclose(values_a, values_b)
