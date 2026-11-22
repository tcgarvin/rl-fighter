"""The commander trainer's pieces that need no sim (spacefight/commander/train.py)."""

from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from spacefight.commander.io import (
    ENTITY_DIM,
    ENTITY_SQUAD,
    GLOBAL_DIM,
    LAUNCH,
    MASK_SHAPES,
    MAX_ENTITIES,
    ORDER,
    ORDER_ATTACK,
    CommanderInputs,
)
from spacefight.commander.policy import (
    CommanderActor,
    CommanderCritic,
    sample_actions,
    save_commander,
)
from spacefight.commander.train import (
    LEARNER,
    NOT_LEARNED,
    OPP_RANDOM,
    OPP_SCRIPTED,
    OPP_SELF,
    OPP_SNAPSHOT,
    OPP_UNSEEN,
    Assignment,
    Results,
    TrainConfig,
    Trainer,
    Transition,
    initial_actor,
    train_rosters,
)
from spacefight.env.rosters import (
    STATION_AS_CARRIER,
    STATION_AS_CONVOY,
    STATION_ASSAULT,
)
from spacefight.eval.missions import default_rosters


def transition(key, value, reward, done=False, next_value=0.0) -> Transition:
    return Transition(
        key=key,
        features={},
        pilot=np.zeros(20, dtype=np.int64),
        action=np.zeros(40, dtype=np.int64),
        logp=0.0,
        value=value,
        phi=0.0,
        reward=reward,
        done=done,
        next_value=next_value,
    )


def advantages(batch, gamma=0.9, lam=0.5):
    fake = SimpleNamespace(cfg=TrainConfig(gamma=gamma, lam=lam))
    return Trainer._advantages(fake, batch)  # type: ignore[arg-type]


def test_gae_runs_along_each_match_and_stops_at_its_end() -> None:
    a = (0, 0, 0)
    b = (1, 1, 0)
    # Match a: two decisions then the end. Match b: one decision, still running.
    batch = [
        transition(a, value=0.5, reward=0.1, next_value=0.2),
        transition(b, value=0.3, reward=0.0, next_value=0.4),
        transition(a, value=0.2, reward=1.0, done=True),
    ]
    adv, ret = advantages(batch)
    last = 1.0 - 0.2
    first = (0.1 + 0.9 * 0.2 - 0.5) + 0.9 * 0.5 * last
    assert adv[2] == pytest.approx(last)
    assert adv[0] == pytest.approx(first)
    assert adv[1] == pytest.approx(0.0 + 0.9 * 0.4 - 0.3)
    assert ret == pytest.approx(adv + np.array([0.5, 0.3, 0.2]))


def test_matches_in_the_same_env_do_not_share_credit() -> None:
    old = (0, 0, 0)
    new = (0, 0, 1)
    batch = [
        transition(old, value=0.0, reward=-1.0, done=True),
        transition(new, value=0.0, reward=5.0, next_value=0.0),
    ]
    adv, _ = advantages(batch)
    assert adv[0] == pytest.approx(-1.0)


@pytest.mark.parametrize(
    ("opponent", "modes", "controllers"),
    [
        (OPP_SCRIPTED, ("learned", "scripted"), (LEARNER, NOT_LEARNED)),
        (OPP_RANDOM, ("learned", "random"), (LEARNER, NOT_LEARNED)),
        (OPP_SELF, ("learned", "learned"), (LEARNER, LEARNER)),
        (OPP_SNAPSHOT, ("learned", "learned"), (LEARNER, 2 + 3)),
        (OPP_UNSEEN, ("learned", "scripted"), (LEARNER, NOT_LEARNED)),
    ],
)
def test_an_assignment_names_each_side(opponent, modes, controllers) -> None:
    a = Assignment(learner_team=0, opponent=opponent, snapshot=3)
    assert a.modes() == modes
    assert a.controllers() == controllers
    flipped = Assignment(learner_team=1, opponent=opponent, snapshot=3)
    assert flipped.modes() == modes[::-1]
    assert flipped.controllers() == controllers[::-1]


def test_only_an_unseen_enemys_pilots_are_kept_from_their_orders() -> None:
    assert Assignment(learner_team=0, opponent=OPP_UNSEEN).hide_orders() == (
        False,
        True,
    )
    assert Assignment(learner_team=1, opponent=OPP_UNSEEN).hide_orders() == (
        True,
        False,
    )
    for opponent in (OPP_SCRIPTED, OPP_RANDOM, OPP_SELF, OPP_SNAPSHOT):
        for team in (0, 1):
            a = Assignment(learner_team=team, opponent=opponent)
            assert a.hide_orders() == (False, False)


def test_the_default_enemies_include_the_side_with_no_orders() -> None:
    shares = TrainConfig().opponent_shares
    assert shares == (0.15, 0.05, 0.25, 0.25, 0.3)
    assert shares[OPP_UNSEEN] > 0 and sum(shares) == pytest.approx(1.0)


def test_four_opponent_shares_from_an_older_config_mean_no_unseen_enemy() -> None:
    old = TrainConfig(opponent_shares=(0.35, 0.1, 0.3, 0.25))
    assert old.opponent_shares == (0.35, 0.1, 0.3, 0.25, 0.0)
    assert TrainConfig(opponent_shares=(0, 0, 0.5, 0, 0.5)).opponent_shares[4] == 0.5
    for bad in ((1.0, 0.0, 0.0), (0.5, -0.1, 0.3, 0.3, 0.0), (0.0, 0.0, 0.0, 0.0, 0.0)):
        with pytest.raises(ValueError, match="opponent_shares"):
            TrainConfig(opponent_shares=bad)


def behaviour_trainer() -> SimpleNamespace:
    """The trainer's counting state, with entity columns laid out as: own, three strike
    classes, then none / attack / defend / go-to."""
    return SimpleNamespace(
        match_stats=defaultdict(float),
        own_col=0,
        strike_cols=slice(1, 4),
        ordered_cols=slice(5, 8),
        decision_s=1.0,
    )


def test_the_log_says_how_long_a_ship_keeps_an_order() -> None:
    fake = behaviour_trainer()
    # Two decisions, each seeing four entities: an own fighter attacking, an own
    # gunship with no order, an own carrier (no strike class) and an enemy fighter.
    entity = np.zeros((2, MAX_ENTITIES, ENTITY_DIM), dtype=np.float32)
    entity[:, 0, [0, 1, 5]] = 1.0
    entity[:, 1, [0, 3, 4]] = 1.0
    entity[:, 2, 0] = 1.0
    entity[:, 3, 1] = 1.0
    actions = torch.zeros((2, 40), dtype=torch.int64)
    Trainer._behaviour(fake, actions, entity, np.array([1, 0], dtype=np.int32))  # type: ignore[arg-type]
    out = Trainer._summarise_matches(fake)  # type: ignore[arg-type]
    # Four strike-craft decisions, one order change: a change every 4 seconds a ship.
    assert out["order_seconds"] == 4.0
    assert out["ordered_share"] == 0.5


def test_a_run_with_no_order_changes_logs_no_order_seconds() -> None:
    fake = behaviour_trainer()
    entity = np.zeros((1, MAX_ENTITIES, ENTITY_DIM), dtype=np.float32)
    entity[:, 0, [0, 1, 4]] = 1.0
    Trainer._behaviour(  # type: ignore[arg-type]
        fake, torch.zeros((1, 40), dtype=torch.int64), entity, np.array([0])
    )
    out = Trainer._summarise_matches(fake)  # type: ignore[arg-type]
    assert "order_seconds" not in out
    assert out["ordered_share"] == 0.0


def test_the_log_counts_only_the_orders_of_squads_with_a_member() -> None:
    fake = behaviour_trainer()
    entity = np.zeros((2, MAX_ENTITIES, ENTITY_DIM), dtype=np.float32)
    # Decision 0: slot 0 is in squad 1. Decision 1: nobody is in a squad.
    entity[0, 0, ENTITY_SQUAD.start + 1] = 1.0
    actions = torch.zeros((2, 40), dtype=torch.int64)
    actions[:, ORDER] = ORDER_ATTACK  # every squad's head sampled "attack"
    Trainer._behaviour(fake, actions, entity, np.array([0, 0], dtype=np.int32))  # type: ignore[arg-type]
    out = Trainer._summarise_matches(fake)  # type: ignore[arg-type]
    # One head of eight was read by the decoder, and it chose attack.
    assert fake.match_stats["order_heads"] == 1
    assert out["order_change_rate"] == 1.0 and out["order_attack"] == 1.0

    quiet = behaviour_trainer()
    Trainer._behaviour(quiet, actions[1:], entity[1:], np.array([0], dtype=np.int32))  # type: ignore[arg-type]
    assert "order_change_rate" not in Trainer._summarise_matches(quiet)  # type: ignore[arg-type]


def learn_trainer(cfg: TrainConfig, update: int, n: int = 64) -> SimpleNamespace:
    """What ``Trainer.learn`` needs, without a sim: nets, an optimiser and ``n``
    finished one-decision matches on synthetic inputs."""
    torch.manual_seed(0)
    actor, critic = CommanderActor(), CommanderCritic(n_pilots=3)
    x = all_allowed_inputs(n, seed=5)
    actions = sample_actions(actor, x)
    rng = np.random.default_rng(1)
    arrays = {"globals": x.globals_, "entities": x.entities, "valid": x.valid} | {
        name: getattr(x, name) for name in MASK_SHAPES
    }
    completed = [
        Transition(
            key=(i, 0, 0),
            features={k: v[i].numpy() for k, v in arrays.items()},
            pilot=np.zeros(MAX_ENTITIES, dtype=np.int64),
            action=actions[i].numpy(),
            logp=0.0,
            value=0.0,
            phi=0.0,
            reward=float(rng.normal()),
            done=True,
        )
        for i in range(n)
    ]
    fake = SimpleNamespace(
        cfg=cfg,
        update=update,
        actor=actor,
        critic=critic,
        opt=torch.optim.Adam(
            list(actor.parameters()) + list(critic.parameters()), lr=cfg.lr
        ),
        completed=completed,
    )
    fake._advantages = lambda batch: Trainer._advantages(fake, batch)  # type: ignore[arg-type]
    fake.actor_frozen = lambda: Trainer.actor_frozen(fake)  # type: ignore[arg-type]
    return fake


def weights(module: torch.nn.Module) -> list[torch.Tensor]:
    return [p.detach().clone() for p in module.parameters()]


def moved(module: torch.nn.Module, before: list[torch.Tensor]) -> bool:
    return any(
        not torch.equal(p, b) for p, b in zip(module.parameters(), before, strict=True)
    )


def test_a_run_from_a_start_trains_only_its_new_critic_at_first(tmp_path) -> None:
    _, path = saved_start(tmp_path)
    cfg = TrainConfig(init=str(path), critic_warmup=2, minibatch=32)
    fake = learn_trainer(cfg, update=1)
    actor, critic = weights(fake.actor), weights(fake.critic)
    out = Trainer.learn(fake)  # type: ignore[arg-type]
    assert out["actor_frozen"] == 1.0
    assert not moved(fake.actor, actor)
    assert moved(fake.critic, critic)
    # Once the warm-up is over the actor trains too.
    fake = learn_trainer(cfg, update=2)
    actor = weights(fake.actor)
    out = Trainer.learn(fake)  # type: ignore[arg-type]
    assert out["actor_frozen"] == 0.0
    assert moved(fake.actor, actor)


def test_only_a_run_from_a_start_warms_its_critic_up() -> None:
    fresh = learn_trainer(TrainConfig(critic_warmup=5, minibatch=32), update=0)
    assert not Trainer.actor_frozen(fresh)  # type: ignore[arg-type]
    resumed = SimpleNamespace(cfg=TrainConfig(init="start.pt"), update=1219)
    assert not Trainer.actor_frozen(resumed)  # type: ignore[arg-type]
    off = SimpleNamespace(cfg=TrainConfig(init="start.pt", critic_warmup=0), update=0)
    assert not Trainer.actor_frozen(off)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="critic_warmup"):
        TrainConfig(critic_warmup=-1)


def test_the_update_logs_how_well_the_critic_explains_the_returns() -> None:
    fake = learn_trainer(TrainConfig(minibatch=32), update=30)
    out = Trainer.learn(fake)  # type: ignore[arg-type]
    # The rollout's values were all 0, which explain none of the returns' variance.
    assert out["explained_variance"] == pytest.approx(0.0, abs=1e-6)
    assert 0.0 <= out["order_heads_live"] <= 4.0


def test_the_price_of_an_order_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="order_price"):
        TrainConfig(order_price=-0.001)


def test_the_station_convoy_share_must_be_a_probability() -> None:
    for bad in (-0.1, 1.5):
        with pytest.raises(ValueError, match="station_convoy_share"):
            TrainConfig(station_convoy_share=bad)


def assignment_drawer(**cfg) -> SimpleNamespace:
    return SimpleNamespace(
        cfg=TrainConfig(**cfg),
        rng=np.random.default_rng(0),
        pool=[],
        results=Results(),
    )


def test_a_station_assault_reads_as_a_convoy_at_its_share() -> None:
    fake = assignment_drawer(
        mission_weights=(0, 0, 0, 1),
        opponent_shares=(0, 0, 0, 0, 1),
        station_convoy_share=0.5,
    )
    draws = [Trainer._draw_assignment(fake) for _ in range(2000)]  # type: ignore[arg-type]
    assert all(a.mission == STATION_ASSAULT for a in draws)
    convoy = np.mean([a.station_as == STATION_AS_CONVOY for a in draws])
    assert convoy == pytest.approx(0.5, abs=0.05)


def test_no_convoy_share_draws_exactly_as_before() -> None:
    # The station's reading is drawn only when it can be convoy, so the rng stream
    # (and every later assignment) is the one a config without the setting gives.
    mixed = dict(mission_weights=(1, 1, 1, 1), opponent_shares=(0.5, 0, 0, 0, 0.5))
    plain = assignment_drawer(**mixed)
    off = assignment_drawer(**mixed, station_convoy_share=0.0)
    a = [Trainer._draw_assignment(plain) for _ in range(200)]  # type: ignore[arg-type]
    b = [Trainer._draw_assignment(off) for _ in range(200)]  # type: ignore[arg-type]
    assert a == b
    assert all(x.station_as == STATION_AS_CARRIER for x in a)
    assert plain.rng.random() == off.rng.random()


def test_a_run_can_start_from_a_saved_commander(tmp_path) -> None:
    torch.manual_seed(3)
    saved = CommanderActor()
    path = tmp_path / "start.pt"
    save_commander(path, saved, {"update": 7})
    actor = initial_actor(TrainConfig(init=str(path)))
    for name, value in saved.state_dict().items():
        assert torch.equal(actor.state_dict()[name], value), name
    fresh = initial_actor(TrainConfig())
    assert not torch.equal(
        fresh.state_dict()["order.bias"], saved.state_dict()["order.bias"]
    )


def all_allowed_inputs(b: int, seed: int = 0) -> CommanderInputs:
    rng = np.random.default_rng(seed)
    arrays = {
        "globals": rng.normal(size=(b, GLOBAL_DIM)).astype(np.float32),
        "entities": rng.normal(size=(b, MAX_ENTITIES, ENTITY_DIM)).astype(np.float32),
        "valid": np.ones((b, MAX_ENTITIES), dtype=bool),
    } | {name: np.ones((b, *shape), dtype=bool) for name, shape in MASK_SHAPES.items()}
    return CommanderInputs.from_numpy(arrays)


def saved_start(tmp_path, seed: int = 3):
    torch.manual_seed(seed)
    saved = CommanderActor()
    with torch.no_grad():
        for head in (saved.launch, saved.order):
            head.weight.normal_()
            head.bias.normal_(std=3.0)
    path = tmp_path / "start.pt"
    save_commander(path, saved, {"update": 7})
    return saved, path


def test_a_launch_prior_resets_the_launch_head_of_a_loaded_start(tmp_path) -> None:
    saved, path = saved_start(tmp_path)
    actor = initial_actor(TrainConfig(init=str(path), launch_prior=0.03))
    for name, value in saved.state_dict().items():
        if not name.startswith("launch."):
            assert torch.equal(actor.state_dict()[name], value), name
    launches = sample_actions(actor, all_allowed_inputs(4096))[:, LAUNCH] == 1
    assert launches.float().mean() == pytest.approx(0.03, abs=0.006)


def test_forbidden_orders_hold_on_a_loaded_start(tmp_path) -> None:
    _, path = saved_start(tmp_path)
    actor = initial_actor(TrainConfig(init=str(path), forbid_orders=("attack",)))
    order = sample_actions(actor, all_allowed_inputs(4096))[:, ORDER]
    assert not (order == ORDER_ATTACK).any()


def test_the_new_start_settings_default_to_the_old_start(tmp_path) -> None:
    saved, path = saved_start(tmp_path)
    actor = initial_actor(TrainConfig(init=str(path)))
    for name, value in saved.state_dict().items():
        assert torch.equal(actor.state_dict()[name], value), name


@pytest.mark.parametrize(
    "bad",
    [
        dict(launch_prior=1.0),
        dict(launch_prior=-0.1),
        dict(learner_team=2),
        dict(forbid_orders=("keep",)),
        dict(forbid_orders=("retreat",)),
    ],
)
def test_new_settings_refuse_bad_values(bad) -> None:
    with pytest.raises(ValueError):
        TrainConfig(**bad)


def test_a_pinned_learner_plays_its_team_in_every_match() -> None:
    shares = dict(mission_weights=(0, 0, 0, 1), opponent_shares=(0.25, 0, 0, 0, 0.75))
    pinned = assignment_drawer(**shares, learner_team=0)
    free = assignment_drawer(**shares)
    a = [Trainer._draw_assignment(pinned) for _ in range(500)]  # type: ignore[arg-type]
    b = [Trainer._draw_assignment(free) for _ in range(500)]  # type: ignore[arg-type]
    assert all(x.learner_team == 0 for x in a)
    assert {x.learner_team for x in b} == {0, 1}
    # Everything else is drawn as an unpinned run draws it.
    assert [(x.opponent, x.mission) for x in a] == [(x.opponent, x.mission) for x in b]
    for x in a:
        assert x.controllers()[0] == LEARNER and x.controllers()[1] == NOT_LEARNED


@pytest.mark.parametrize("shares", [(0, 0, 1, 0, 0), (0.5, 0, 0, 0.5, 0)])
def test_a_pinned_learner_refuses_self_play(shares) -> None:
    with pytest.raises(ValueError, match="pinned learner_team"):
        TrainConfig(learner_team=0, opponent_shares=shares)


def test_a_station_roster_picks_that_roster_for_the_station_draws() -> None:
    rosters = train_rosters(TrainConfig(station_roster="strike of 8"))
    assert [name for name, _ in rosters[STATION_ASSAULT]] == ["strike of 8"]
    default = train_rosters(TrainConfig())
    names = [name for name, _ in default[STATION_ASSAULT]]
    assert names == [name for name, _ in default_rosters(STATION_ASSAULT)]
    # The other missions are untouched.
    for mission, options in default.items():
        if mission != STATION_ASSAULT:
            assert [n for n, _ in rosters[mission]] == [n for n, _ in options]


def test_an_unknown_station_roster_is_refused() -> None:
    with pytest.raises(ValueError, match="no roster 'strike of 9'"):
        TrainConfig(station_roster="strike of 9")
