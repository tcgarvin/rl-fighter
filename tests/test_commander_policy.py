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
    ENTITY_SQUAD,
    GLOBAL_DIM,
    GOTO_POINT,
    LAUNCH,
    MASK_SHAPES,
    MAX_ENTITIES,
    N_SQUADS,
    ORDER,
    ORDER_ATTACK,
    ORDER_GOTO,
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
    forbid_orders,
    lean_to_hold,
    lean_to_keep,
    load_commander,
    n_params,
    sample_actions,
    save_commander,
    squads_with_members,
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


def squad_inputs(b: int, members: dict[int, int], seed: int = 0) -> CommanderInputs:
    """``inputs`` with the squad one-hot written by hand: ``members`` maps a slot to
    its squad (1-4); every other slot is in none."""
    x = inputs(b, seed=seed)
    x.entities[..., ENTITY_SQUAD] = 0.0
    x.entities[..., ENTITY_SQUAD.start] = 1.0
    for slot, squad in members.items():
        x.entities[:, slot, ENTITY_SQUAD] = 0.0
        x.entities[:, slot, ENTITY_SQUAD.start + squad] = 1.0
    return x


def test_squads_with_members_follows_the_decisions_squad_moves() -> None:
    x = squad_inputs(1, {0: 1, 1: 1, 2: 3})
    moves = torch.zeros((1, MAX_ENTITIES), dtype=torch.int64)
    assert squads_with_members(x.entities, moves).tolist() == [
        [True, False, True, False]
    ]
    moves[0, 2] = 1  # squad 3's only member leaves for no squad
    moves[0, 0] = 5  # one of squad 1's two members moves to squad 4
    assert squads_with_members(x.entities, moves).tolist() == [
        [True, False, False, True]
    ]
    moves[0, 1] = 3  # and the other to squad 2: squad 1 ends empty
    assert squads_with_members(x.entities, moves).tolist() == [
        [False, True, False, True]
    ]


def test_an_empty_squads_order_is_not_part_of_the_decision() -> None:
    # The decoder gives no order to a squad that ends the decision empty, so what its
    # order, target and point heads sampled must not move the log-probability.
    torch.manual_seed(5)
    actor = CommanderActor()
    x = squad_inputs(16, {}, seed=6)
    actions, logp = act(actor, x)
    actions[:, SQUAD_OF_SLOT] = 0
    base, entropy, per_head = evaluate(actor, x, actions)
    changed = actions.clone()
    changed[:, ORDER] = ORDER_GOTO
    changed[:, GOTO_POINT] = (changed[:, GOTO_POINT] + 7) % 25
    after, _, _ = evaluate(actor, x, changed)
    assert torch.allclose(base, after)
    for name in ("order", "target", "ward", "point"):
        assert float(per_head[name].detach().abs().sum()) == 0.0, name
    assert (entropy > 0).all()  # the launch, waypoint and squad heads still count


def test_an_entropy_bonus_does_not_reach_an_empty_squads_order_head() -> None:
    torch.manual_seed(5)
    actor = CommanderActor()
    x = squad_inputs(16, {}, seed=6)
    actions = torch.zeros((16, ACTION_DIM), dtype=torch.int64)
    _, entropy, _ = evaluate(actor, x, actions)
    entropy.mean().backward()
    assert actor.order.weight.grad is None or not actor.order.weight.grad.any()
    assert actor.point.weight.grad is None or not actor.point.weight.grad.any()


def test_a_squads_order_counts_once_it_has_a_member() -> None:
    torch.manual_seed(5)
    actor = CommanderActor()
    x = squad_inputs(16, {3: 2}, seed=6)
    x.order_mask[:] = True
    actions = torch.zeros((16, ACTION_DIM), dtype=torch.int64)
    base, _, per_head = evaluate(actor, x, actions)
    # Only squad 2 is live, so the order entropy is that one head's.
    squad_2 = torch.distributions.Categorical(logits=actor(x).order[:, 1])
    assert torch.allclose(per_head["order"], squad_2.entropy())
    assert (per_head["order"] > 0).all()
    ordered = actions.clone()
    ordered[:, ORDER.start + 1] = ORDER_GOTO
    assert not torch.allclose(base, evaluate(actor, x, ordered)[0])
    # A ship that joins an empty squad in this decision makes that squad's order count.
    joined = actions.clone()
    joined[:, SQUAD_OF_SLOT.start + 7] = 2 + 3  # slot 7 to squad 4
    assert squads_with_members(x.entities, joined[:, SQUAD_OF_SLOT])[:, 3].all()
    with_order = joined.clone()
    with_order[:, ORDER.start + 3] = ORDER_GOTO
    assert not torch.allclose(
        evaluate(actor, x, joined)[0], evaluate(actor, x, with_order)[0]
    )
    assert N_SQUADS == 4


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


def test_a_fresh_actor_leans_to_keep_on_its_order_and_squad_heads() -> None:
    torch.manual_seed(0)
    actor = CommanderActor()
    lean_to_keep(actor, 0.8)
    x = inputs(256)
    x.valid[:] = True
    x.order_mask[:] = True
    x.squad_mask[:] = True
    actions = sample_actions(actor, x)
    # Head weights start near zero, so the odds are the bias's: 1,024 order draws and
    # 5,120 squad draws at 0.8.
    assert (actions[:, ORDER] == ORDER_KEEP).float().mean() == pytest.approx(
        0.8, abs=0.05
    )
    assert (actions[:, SQUAD_OF_SLOT] == 0).float().mean() == pytest.approx(
        0.8, abs=0.03
    )
    # The choices other than keep stay even with each other.
    assert actor.order.bias[1:].abs().max() == 0


@pytest.mark.parametrize("prior", [0.0, 1.0, -0.2])
def test_lean_to_keep_refuses_odds_outside_zero_to_one(prior: float) -> None:
    with pytest.raises(ValueError, match="keep_prior"):
        lean_to_keep(CommanderActor(), prior)


def all_allowed(b: int, seed: int = 0) -> CommanderInputs:
    x = inputs(b, seed)
    for name in MASK_SHAPES:
        getattr(x, name)[:] = True
    x.valid[:] = True
    return x


def scramble(head: torch.nn.Linear, seed: int) -> None:
    """Weights of a head as large as a trained one's could be."""
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        head.weight.copy_(torch.randn(head.weight.shape, generator=g))
        head.bias.copy_(torch.randn(head.bias.shape, generator=g) * 3)


@pytest.mark.parametrize("prior", [0.03, 0.9])
def test_lean_to_hold_launches_each_hull_at_its_prior(prior: float) -> None:
    torch.manual_seed(1)
    actor = CommanderActor()
    scramble(actor.launch, 2)
    lean_to_hold(actor, prior)
    actions = sample_actions(actor, all_allowed(4096))
    # 4,096 draws per hull: a standard error of 0.003 at 0.03, 0.005 at 0.9.
    share = (actions[:, LAUNCH] == 1).float().mean(dim=0)
    assert share.numpy() == pytest.approx(
        [prior] * 3, abs=0.02 if prior > 0.5 else 0.01
    )


def test_lean_to_hold_leaves_the_other_heads_alone() -> None:
    torch.manual_seed(1)
    actor = CommanderActor()
    before = {k: v.clone() for k, v in actor.state_dict().items()}
    lean_to_hold(actor, 0.03)
    changed = {
        k for k, v in actor.state_dict().items() if not torch.equal(v, before[k])
    }
    assert changed == {"launch.weight", "launch.bias"}


@pytest.mark.parametrize("prior", [0.0, 1.0, -0.1])
def test_lean_to_hold_refuses_odds_outside_zero_to_one(prior: float) -> None:
    with pytest.raises(ValueError, match="launch_prior"):
        lean_to_hold(CommanderActor(), prior)


def test_a_forbidden_order_is_never_sampled() -> None:
    torch.manual_seed(0)
    actor = CommanderActor()
    lean_to_keep(actor, 0.8)
    scramble(actor.order, 3)
    forbid_orders(actor, ("attack",))
    order = torch.cat(
        [sample_actions(actor, all_allowed(1024, seed))[:, ORDER] for seed in range(20)]
    )
    # 81,920 order draws: none attacks, and the others are all still drawn.
    assert not (order == ORDER_ATTACK).any()
    assert set(order.unique().tolist()) == {0, 1, 3, 4}


def test_ppo_updates_do_not_undo_a_forbidden_order() -> None:
    # PPO-like steps (random advantages, an entropy bonus, Adam at 3x the trainer's
    # rate): a choice never sampled gets a gradient of about its probability, so its
    # odds stay near e^-30.
    torch.manual_seed(0)
    actor = CommanderActor()
    lean_to_keep(actor, 0.8)
    forbid_orders(actor, ("attack",))
    opt = torch.optim.Adam(actor.parameters(), lr=1e-3)
    for step in range(300):
        x = all_allowed(64, step)
        actions, _ = act(actor, x)
        logp, entropy, _ = evaluate(actor, x, actions)
        adv = torch.randn(64)
        loss = -(adv * logp).mean() - 0.01 * entropy.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        p = actor(all_allowed(256, 999)).order.softmax(dim=-1)[..., ORDER_ATTACK]
    assert float(p.max()) < 1e-10


@pytest.mark.parametrize("name", ["keep", "retreat"])
def test_forbid_orders_refuses_keep_and_unknown_orders(name: str) -> None:
    with pytest.raises(ValueError, match="cannot forbid"):
        forbid_orders(CommanderActor(), (name,))
