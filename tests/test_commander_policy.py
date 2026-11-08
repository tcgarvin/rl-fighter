"""The commander network (spacefight/commander/policy.py) on synthetic inputs."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from spacefight.commander.io import (
    ACTION_DIM,
    ATTACK_TARGET,
    DEFEND_WARD,
    ENTITY_DIM,
    GLOBAL_DIM,
    LAUNCH,
    MASK_SHAPES,
    MAX_ENTITIES,
    ORDER,
    ORDER_ATTACK,
    ORDER_KEEP,
    SQUAD_OF_SLOT,
    WAYPOINT,
    CommanderInputs,
)
from spacefight.commander.policy import (
    CommanderActor,
    CommanderCritic,
    act,
    evaluate,
    load_commander,
    n_params,
    sample_actions,
    save_commander,
)


def inputs(b: int = 8, seed: int = 0) -> CommanderInputs:
    rng = np.random.default_rng(seed)
    valid = np.zeros((b, MAX_ENTITIES), dtype=bool)
    valid[:, :10] = True
    arrays = {
        "globals": rng.normal(size=(b, GLOBAL_DIM)).astype(np.float32),
        "entities": rng.normal(size=(b, MAX_ENTITIES, ENTITY_DIM)).astype(np.float32),
        "valid": valid,
    }
    for name, shape in MASK_SHAPES.items():
        arrays[name] = rng.random((b, *shape)) < 0.6
    arrays["squad_mask"][..., 0] = True  # keep is always allowed
    arrays["order_mask"][..., 0] = True
    arrays["waypoint_mask"][..., 0] = True
    return CommanderInputs.from_numpy(arrays)


def test_a_decision_respects_every_mask() -> None:
    torch.manual_seed(0)
    actor = CommanderActor()
    x = inputs(64)
    for _ in range(5):
        actions, _ = act(actor, x)
        assert actions.shape == (64, ACTION_DIM)
        launch = actions[:, LAUNCH]
        assert not ((launch == 1) & ~x.launch_mask).any()
        wp = actions[:, WAYPOINT]
        assert x.waypoint_mask.gather(1, wp[:, None]).all()
        squad = actions[:, SQUAD_OF_SLOT]
        assert x.squad_mask.gather(2, squad[..., None]).all()
        order = actions[:, ORDER]
        assert x.order_mask.gather(2, order[..., None]).all()
        target = actions[:, ATTACK_TARGET]
        chose = order == ORDER_ATTACK
        assert x.target_mask.gather(1, target)[chose].all()


def test_evaluate_gives_the_log_prob_act_sampled_with() -> None:
    torch.manual_seed(1)
    actor = CommanderActor()
    x = inputs(32, seed=3)
    actions, logp = act(actor, x)
    again, entropy, per_head = evaluate(actor, x, actions)
    assert torch.allclose(logp, again, atol=1e-5)
    assert torch.isfinite(entropy).all() and (entropy >= 0).all()
    assert set(per_head) == {
        "launch",
        "waypoint",
        "squad",
        "order",
        "target",
        "ward",
        "point",
    }


def test_sample_actions_draws_act_s_decisions_under_the_same_seed() -> None:
    actor = CommanderActor()
    x = inputs(16, seed=4)
    for seed in (0, 1, 2):
        torch.manual_seed(seed)
        expected, _ = act(actor, x)
        torch.manual_seed(seed)
        assert torch.equal(sample_actions(actor, x), expected)


def test_a_target_counts_only_when_its_squad_attacks() -> None:
    torch.manual_seed(2)
    actor = CommanderActor()
    x = inputs(16, seed=4)
    actions, _ = act(actor, x)
    actions[:, ORDER] = ORDER_KEEP
    base, _, _ = evaluate(actor, x, actions)
    changed = actions.clone()
    changed[:, ATTACK_TARGET] = (changed[:, ATTACK_TARGET] + 1) % MAX_ENTITIES
    changed[:, DEFEND_WARD] = (changed[:, DEFEND_WARD] + 3) % MAX_ENTITIES
    after, _, _ = evaluate(actor, x, changed)
    assert torch.allclose(base, after)


def test_an_all_masked_head_stays_finite() -> None:
    actor = CommanderActor()
    x = inputs(4)
    x.target_mask[:] = False
    x.ward_mask[:] = False
    x.valid[:] = False
    actions, logp = act(actor, x)
    assert torch.isfinite(logp).all()


def test_sizes_and_a_round_trip(tmp_path) -> None:
    actor = CommanderActor()
    assert 50_000 < n_params(actor) < 200_000
    critic = CommanderCritic(n_pilots=10)
    x = inputs(5)
    v = critic(x, torch.randint(0, 11, (5, MAX_ENTITIES)))
    assert v.shape == (5,)
    path = tmp_path / "c.pt"
    save_commander(path, actor, {"update": 3})
    loaded, meta = load_commander(path)
    assert meta == {"update": 3}
    a1, _ = act(actor, x, deterministic=True)
    a2, _ = act(loaded, x, deterministic=True)
    assert torch.equal(a1, a2)


def test_inputs_reject_a_wrong_shape() -> None:
    x = inputs(2)
    arrays = {
        "globals": x.globals_.numpy()[:, :10],
        "entities": x.entities.numpy(),
        "valid": x.valid.numpy(),
    } | {k: getattr(x, k).numpy() for k in MASK_SHAPES}
    with pytest.raises(ValueError, match="globals"):
        CommanderInputs.from_numpy(arrays)
