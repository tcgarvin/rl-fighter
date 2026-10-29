"""Tests for the masked multi-head spike policy (spacefight/rl/spike_policy.py).

Plan: lab/runs/2026-10-28-learnability-spike/plan.md §3 and §8 row B.
"""

from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.rl import spike_policy as sp
from spacefight.rl.spike_policy import (
    ACTION_WIDTH,
    HOLD_ROW,
    N_LOGITS,
    OBS_DIM,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    act_numpy,
    group_entropy,
    group_head_counts,
    load_policy,
    masked_mean,
    mean_head_entropy,
    save_policy,
)

torch.set_num_threads(4)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FIGHTER_1V1 = [["fighter"], ["fighter"]]
MIXED_2V2 = [["fighter", "strafer"], ["gunship", "fighter"]]

# Logit rows of each action column's head (layout in the module docstring).
_LOGIT_ROWS = (
    [list(range(3 * c, 3 * c + 3)) for c in range(14)]
    + [list(range(42 + 2 * j, 44 + 2 * j)) for j in range(6)]
    + [list(range(54, 61))]
)


def fighter_masks(batch: int) -> HeadMasks:
    """Masks of the fighter hull: 5 thrusters, one fixed gun."""
    thruster = np.zeros((batch, 8), dtype=bool)
    thruster[:, :5] = True
    turret = np.zeros((batch, 6), dtype=bool)
    turret[:, 0] = True
    return HeadMasks.from_numpy(thruster, turret, turret.copy())


def random_masks(batch: int, seed: int) -> HeadMasks:
    rng = np.random.default_rng(seed)
    turret = rng.random((batch, 6)) < 0.5
    fixed = turret & (rng.random((batch, 6)) < 0.5)
    return HeadMasks.from_numpy(rng.random((batch, 8)) < 0.6, turret, fixed)


def random_obs(batch: int, seed: int) -> torch.Tensor:
    gen = torch.Generator().manual_seed(seed)
    return torch.randn(batch, OBS_DIM, generator=gen)


def make_actor(seed: int = 0) -> SpikeActor:
    torch.manual_seed(seed)
    actor = SpikeActor()
    # Larger logits than the 0.01-gain init so heads are far from uniform.
    with torch.no_grad():
        actor.logits_layer.weight.mul_(100.0)
        actor.logits_layer.bias.normal_()
    return actor


def make_env(fleets=FIGHTER_1V1, n_envs=8):
    rust_env = pytest.importorskip("spacefight.env.rust_env")
    return rust_env, rust_env.RustVecEnv(ASSETS, n_envs, fleets, seed=0)


def env_masks(env) -> HeadMasks:
    return HeadMasks.from_numpy(env.thruster_mask, env.turret_mask, env.fixed_turret)


# ---------------------------------------------------------------------------
# Shapes, constants, init
# ---------------------------------------------------------------------------


def test_constants_match_the_sim():
    rust_env = pytest.importorskip("spacefight.env.rust_env")
    assert OBS_DIM == rust_env.OBS_DIM
    assert ACTION_WIDTH == rust_env.ACTION_WIDTH
    assert tuple(int(h) for h in rust_env.ACTION_HIGHS) == sp.ACTION_HIGHS
    for name, cols in sp.HEAD_GROUPS.items():
        offset, width = rust_env.ACTION_LAYOUT[name]
        assert (cols.start, cols.stop) == (offset, offset + width)
        assert sp.HEAD_CHOICES[name] == rust_env.ACTION_HEAD_CHOICES[name]
    assert N_LOGITS == sum(
        sp.HEAD_CHOICES[n] * (c.stop - c.start) for n, c in sp.HEAD_GROUPS.items()
    )


def test_param_count_and_output_shapes():
    actor, critic = SpikeActor(), SpikeCritic()
    assert sp.param_count(actor) == 180_285
    assert sp.param_count(critic) == 164_865
    obs = random_obs(5, 0)
    assert actor(obs).shape == (5, N_LOGITS)
    assert critic(obs).shape == (5,)


def test_init_gives_near_uniform_heads():
    torch.manual_seed(0)
    actor = SpikeActor()
    masks = fighter_masks(64)
    entropy = actor.head_entropy(random_obs(64, 1), masks)
    valid = masks.head_valid()
    uniform = torch.tensor(
        [np.log(3)] * 14 + [np.log(2)] * 6 + [np.log(7)], dtype=torch.float32
    ).expand(64, -1)
    assert torch.allclose(entropy[valid], uniform[valid], atol=1e-2)


def test_bad_inputs_raise():
    actor = SpikeActor()
    masks = fighter_masks(4)
    with pytest.raises(ValueError, match="obs must be"):
        actor(torch.zeros(4, OBS_DIM - 1))
    with pytest.raises(ValueError, match="masks have"):
        actor.sample(random_obs(3, 0), masks)
    with pytest.raises(ValueError, match="mask must be"):
        HeadMasks(
            thruster=torch.ones(4, 8, dtype=torch.bool),
            turret=torch.ones(3, 6, dtype=torch.bool),
            fixed_turret=torch.ones(4, 6, dtype=torch.bool),
        )
    actions = torch.tensor(HOLD_ROW).repeat(4, 1)
    actions[0, 0] = 3  # thruster 0 is present on the fighter
    with pytest.raises(ValueError, match="out of range"):
        actor.evaluate(random_obs(4, 0), masks, actions)
    with pytest.raises(ValueError, match="integer"):
        actor.evaluate(random_obs(4, 0), masks, actions.float())


# ---------------------------------------------------------------------------
# Env compatibility
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fleets", [FIGHTER_1V1, MIXED_2V2])
def test_sampled_actions_drive_the_real_env(fleets):
    rust_env, env = make_env(fleets)
    actor = make_actor()
    masks = env_masks(env)
    highs = rust_env.ACTION_HIGHS
    obs = env.reset()
    for _ in range(20):
        actions = act_numpy(actor, obs, masks)
        assert actions.shape == (env.n_envs, env.n_ships, ACTION_WIDTH)
        assert actions.dtype == np.int8
        assert ((actions >= 0) & (actions <= highs)).all()
        obs, rewards, _, _ = env.step(actions)
        assert np.isfinite(obs).all() and np.isfinite(rewards).all()


def test_masked_heads_are_overwritten_with_hold():
    _, env = make_env(MIXED_2V2)
    actor = make_actor()
    masks = env_masks(env)
    actions = act_numpy(actor, env.obs, masks).reshape(-1, ACTION_WIDTH)
    valid = masks.head_valid().numpy()
    hold = np.broadcast_to(np.array(HOLD_ROW, dtype=np.int8), actions.shape)
    assert (actions[~valid] == hold[~valid]).all()
    # The fighter's gun is fixed, so its slews are masked but its fire is not.
    fighter = env_masks(make_env(FIGHTER_1V1)[1])
    assert group_head_counts(fighter.head_valid()) == {
        "throttle": 5,
        "slew": 0,
        "fire": 1,
        "power": 1,
    }


def test_from_numpy_flattens_env_axes_in_obs_order():
    _, env = make_env(MIXED_2V2, n_envs=3)
    masks = env_masks(env)
    assert masks.batch_size == 3 * env.n_ships
    np.testing.assert_array_equal(
        masks.thruster.numpy(), env.thruster_mask.reshape(-1, 8)
    )


# ---------------------------------------------------------------------------
# Masking, log-prob, entropy
# ---------------------------------------------------------------------------


def test_masked_heads_have_exactly_zero_log_prob_and_entropy():
    actor = make_actor()
    masks = random_masks(256, 0)
    obs = random_obs(256, 0)
    # Arbitrary in-range values everywhere, including masked heads.
    actions = torch.randint(0, 2, (256, ACTION_WIDTH))
    log_prob, entropy = actor.evaluate_heads(obs, masks, actions)
    valid = masks.head_valid()
    assert (log_prob[~valid] == 0).all() and (entropy[~valid] == 0).all()
    assert (log_prob[valid] < 0).all() and (entropy[valid] > 0).all()
    assert (actor.head_entropy(obs, masks)[~valid] == 0).all()
    assert (actor.head_cross_entropy(obs, masks, actions, 0.02)[~valid] == 0).all()


def test_masked_head_values_do_not_matter():
    actor = make_actor()
    masks = fighter_masks(8)
    obs = random_obs(8, 0)
    sample = actor.sample(obs, masks)
    labels = sample.actions.clone()
    labels[~masks.head_valid()] = 0  # what sanitized env labels hold in unused slots
    torch.testing.assert_close(
        actor.evaluate(obs, masks, labels)[0], sample.log_prob, rtol=0, atol=1e-6
    )


def test_sample_log_prob_equals_evaluate():
    actor = make_actor()
    masks = random_masks(512, 1)
    obs = random_obs(512, 1)
    torch.manual_seed(3)
    out = actor.sample(obs, masks)
    log_prob, entropy = actor.evaluate(obs, masks, out.actions)
    torch.testing.assert_close(log_prob, out.log_prob, rtol=0, atol=1e-6)
    torch.testing.assert_close(entropy, out.entropy, rtol=0, atol=1e-6)
    assert out.actions.dtype == torch.int64 and out.actions.shape == (512, 21)


def test_log_prob_matches_independent_categoricals():
    actor = make_actor()
    masks = random_masks(64, 2)
    obs = random_obs(64, 2)
    out = actor.sample(obs, masks)
    logits = actor(obs)
    valid = masks.head_valid()
    expected_lp = torch.zeros(64)
    expected_ent = torch.zeros(64)
    for col, rows in enumerate(_LOGIT_ROWS):
        dist = torch.distributions.Categorical(logits=logits[:, rows])
        keep = valid[:, col]
        expected_lp += torch.where(keep, dist.log_prob(out.actions[:, col]), 0.0)
        expected_ent += torch.where(keep, dist.entropy(), 0.0)
    torch.testing.assert_close(out.log_prob, expected_lp, rtol=0, atol=1e-5)
    torch.testing.assert_close(out.entropy, expected_ent, rtol=0, atol=1e-5)


def test_deterministic_sample_is_argmax():
    actor = make_actor()
    masks = random_masks(128, 3)
    obs = random_obs(128, 3)
    out = actor.sample(obs, masks, deterministic=True)
    logits = actor(obs)
    valid = masks.head_valid()
    for col, rows in enumerate(_LOGIT_ROWS):
        expected = torch.where(
            valid[:, col], logits[:, rows].argmax(-1), torch.tensor(HOLD_ROW[col])
        )
        assert torch.equal(out.actions[:, col], expected)
    again = actor.sample(obs, masks, deterministic=True)
    assert torch.equal(out.actions, again.actions)


def test_stochastic_sample_frequencies_follow_the_policy():
    actor = make_actor()
    obs = random_obs(1, 4).expand(20_000, -1)
    masks = fighter_masks(20_000)
    torch.manual_seed(0)
    actions = actor.sample(obs, masks).actions
    power_probs = torch.softmax(actor(obs[:1])[0, 54:61], -1)
    freq = torch.bincount(actions[:, 20], minlength=7).float() / 20_000
    torch.testing.assert_close(freq, power_probs, rtol=0, atol=0.015)


def test_gradient_flows_only_through_unmasked_heads():
    actor = make_actor()
    masks = fighter_masks(32)
    obs = random_obs(32, 5)
    actions = actor.sample(obs, masks).actions
    log_prob, entropy = actor.evaluate_heads(obs, masks, actions)
    (log_prob.sum() + entropy.sum()).backward()
    grad = actor.logits_layer.weight.grad
    assert grad is not None
    row_norm = grad.abs().sum(-1)
    valid_cols = masks.head_valid()[0]
    for col, rows in enumerate(_LOGIT_ROWS):
        if valid_cols[col]:
            assert (row_norm[rows] > 0).all(), col
        else:
            assert (row_norm[rows] == 0).all(), col


# ---------------------------------------------------------------------------
# Loss helpers
# ---------------------------------------------------------------------------


def test_all_act_mask_false_batch_gives_zero_loss_and_grad():
    actor = make_actor()
    masks = fighter_masks(16)
    obs = random_obs(16, 6)
    actions = actor.sample(obs, masks).actions
    log_prob, _ = actor.evaluate(obs, masks, actions)
    act_mask = torch.zeros(16, dtype=torch.bool)
    loss = masked_mean(-log_prob, act_mask)
    assert loss.item() == 0.0
    loss.backward()
    assert all((p.grad == 0).all() for p in actor.parameters() if p.grad is not None)


def test_masked_mean_averages_selected_rows_only():
    values = torch.tensor([1.0, float("nan"), 3.0, 5.0])
    mask = torch.tensor([True, False, True, False])
    assert masked_mean(values, mask).item() == 2.0


def test_group_and_mean_head_entropy():
    actor = make_actor()
    masks = fighter_masks(10)
    obs = random_obs(10, 7)
    head_ent = actor.head_entropy(obs, masks)
    valid = masks.head_valid()
    rows = torch.ones(10, dtype=torch.bool)
    groups = group_entropy(head_ent, valid, rows)
    assert set(groups) == {"throttle", "slew", "fire", "power"}
    torch.testing.assert_close(groups["throttle"], head_ent[:, :5].mean())
    assert groups["slew"].item() == 0.0
    torch.testing.assert_close(groups["fire"], head_ent[:, 14].mean())
    torch.testing.assert_close(groups["power"], head_ent[:, 20].mean())
    torch.testing.assert_close(
        mean_head_entropy(head_ent, valid), head_ent.sum(-1) / 7.0
    )


def test_cross_entropy_without_smoothing_is_negative_log_prob():
    actor = make_actor()
    masks = random_masks(32, 8)
    obs = random_obs(32, 8)
    actions = actor.sample(obs, masks).actions
    ce = actor.head_cross_entropy(obs, masks, actions)
    torch.testing.assert_close(ce, -actor.head_log_probs(obs, masks, actions))
    smoothed = actor.head_cross_entropy(obs, masks, actions, label_smoothing=0.02)
    assert (smoothed[masks.head_valid()] > 0).all()


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


def test_save_load_round_trip(tmp_path):
    actor = make_actor(1)
    torch.manual_seed(2)
    critic = SpikeCritic()
    meta: dict[str, object] = {"phase": "bc", "update": 0, "sim_version": 2}
    path = tmp_path / "sub" / "bc.pt"
    save_policy(path, actor, critic, meta)
    actor2, critic2, meta2 = load_policy(path)
    assert meta2 == meta
    obs = random_obs(16, 9)
    masks = random_masks(16, 9)
    assert torch.equal(actor(obs), actor2(obs))
    assert torch.equal(critic(obs), critic2(obs))
    a = actor.sample(obs, masks, deterministic=True)
    b = actor2.sample(obs, masks, deterministic=True)
    assert torch.equal(a.actions, b.actions) and torch.equal(a.log_prob, b.log_prob)


def test_load_rejects_foreign_files(tmp_path):
    path = tmp_path / "other.pt"
    torch.save({"weights": torch.zeros(1)}, path)
    with pytest.raises(ValueError, match="not a"):
        load_policy(path)
