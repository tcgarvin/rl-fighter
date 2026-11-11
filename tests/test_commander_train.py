"""The commander trainer's pieces that need no sim (spacefight/commander/train.py)."""

from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from spacefight.commander.train import (
    LEARNER,
    NOT_LEARNED,
    OPP_RANDOM,
    OPP_SCRIPTED,
    OPP_SELF,
    OPP_SNAPSHOT,
    Assignment,
    TrainConfig,
    Trainer,
    Transition,
)


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
    ],
)
def test_an_assignment_names_each_side(opponent, modes, controllers) -> None:
    a = Assignment(learner_team=0, opponent=opponent, snapshot=3)
    assert a.modes() == modes
    assert a.controllers() == controllers
    flipped = Assignment(learner_team=1, opponent=opponent, snapshot=3)
    assert flipped.modes() == modes[::-1]
    assert flipped.controllers() == controllers[::-1]


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
    entity = np.zeros((2, 4, 8), dtype=np.float32)
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
    entity = np.zeros((1, 2, 8), dtype=np.float32)
    entity[:, 0, [0, 1, 4]] = 1.0
    Trainer._behaviour(  # type: ignore[arg-type]
        fake, torch.zeros((1, 40), dtype=torch.int64), entity, np.array([0])
    )
    out = Trainer._summarise_matches(fake)  # type: ignore[arg-type]
    assert "order_seconds" not in out
    assert out["ordered_share"] == 0.0


def test_the_price_of_an_order_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="order_price"):
        TrainConfig(order_price=-0.001)
