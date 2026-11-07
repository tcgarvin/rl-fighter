"""The commander trainer's pieces that need no sim (spacefight/commander/train.py)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

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
