"""Pilot training under a commander stable (spacefight/commander/stable.py, decide.py,
and the ``commander_stable`` option of spacefight/rl/spike_ppo.py).

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
The ``live`` tests read the live stable's checkpoints from lab/runs (sha-checked).
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch

pytest.importorskip("rlf_sim", reason="rlf_sim extension not built")

from spacefight import train_spike  # noqa: E402
from spacefight.commander.decide import NOT_IN_STABLE, decide_learned  # noqa: E402
from spacefight.commander.eval import Commander  # noqa: E402
from spacefight.commander.io import (  # noqa: E402
    ACTION_DIM,
    ENTITY_DIM,
    GLOBAL_DIM,
    MASK_SHAPES,
    MAX_ENTITIES,
)
from spacefight.commander.policy import CommanderActor, save_commander  # noqa: E402
from spacefight.commander.stable import (  # noqa: E402
    NO_COMMANDER,
    CommanderStable,
    StableSampler,
    commander_label,
    resolve_stable,
)
from spacefight.env.drills import DrillGenerator  # noqa: E402
from spacefight.env.rosters import (  # noqa: E402
    CARRIER_BATTLE,
    LEARNED,
    RANDOM,
    SCRIPTED,
    Roster,
    live_mission_rosters,
    make_sampler,
    resolve_distribution,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402
from spacefight.rl.spike_ppo import PPOConfig, SpikeTrainer  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ASSETS = str(REPO / "assets")
LIVE_IDS = ("scripted", "c1_shaped", "c1_outcome", "c1_shaped_s1")


@pytest.fixture
def in_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """The live registry names its checkpoints relative to the repo root."""
    monkeypatch.chdir(REPO)


def _config(**overrides: object) -> PPOConfig:
    settings: dict[str, object] = {
        "tag": "stable",
        "seed": 5,
        "assets_dir": ASSETS,
        "n_envs": 4,
        "n_steps": 128,
        "t_tail": 40,
        "n_updates": 2,
        "minibatch": 512,
        "epochs": 1,
        "sim_threads": 2,
        "torch_threads": 2,
        "rosters": "pilots_v1",
        "roster_overrides": {"commander_p": 1.0},
        "critic": "fleet",
        "learner_side": "random",
        "opponent_bands": [[0, 0.5, 0.5, 0.0]],
        "checkpoint_every": 100,
    }
    settings.update(overrides)
    return PPOConfig.preset("scratch", **settings)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_the_stable_is_off_by_default_and_old_configs_load_unchanged() -> None:
    config = _config()
    assert config.commander_stable == [] and config.commander_weights == []
    old = config.to_dict()
    del old["commander_stable"], old["commander_weights"]
    # A config.yaml written before the option existed reads back equal, so a resume
    # does not see a changed config.
    assert PPOConfig.from_dict(old) == config


def test_the_stable_round_trips_through_the_config_dict() -> None:
    config = _config(commander_stable=["live", "random"], commander_weights=[3, 1])
    assert PPOConfig.from_dict(config.to_dict()) == config


def test_set_lines_parse_into_the_stable() -> None:
    args = argparse.Namespace(
        n_updates=None,
        n_envs=None,
        n_steps=None,
        seed=None,
        sim_threads=None,
        torch_threads=None,
        overrides=["commander_stable=[live, random]", "commander_weights=[3, 1]"],
    )
    overrides = train_spike._ppo_overrides(args)
    assert overrides == {
        "commander_stable": ["live", "random"],
        "commander_weights": [3, 1],
    }
    config = _config(**overrides)
    assert config.commander_stable == ["live", "random"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"commander_weights": [1.0]}, "needs a commander_stable"),
        ({"commander_stable": "live"}, "must be lists"),
        ({"commander_stable": ["live"], "rosters": ""}, "needs a rosters preset"),
        ({"commander_stable": ["live", "live"]}, "repeats"),
        ({"commander_stable": [""]}, "non-empty"),
        ({"commander_stable": ["live"], "commander_weights": [1, 2]}, "weights for"),
        ({"commander_stable": ["live"], "commander_weights": [-1]}, ">= 0"),
        ({"commander_stable": ["live", "random"], "commander_weights": [0, 0]}, ">= 0"),
    ],
)
def test_bad_stables_are_rejected(overrides: dict[str, object], message: str) -> None:
    if overrides.get("rosters") == "":
        overrides = {**overrides, "roster_overrides": {}}
    with pytest.raises(ValueError, match=message):
        _config(**overrides)


# ---------------------------------------------------------------------------
# The stable
# ---------------------------------------------------------------------------


def test_spec_weights_normalise_and_a_live_weight_splits_over_its_members(
    in_repo: None,
) -> None:
    keywords = resolve_stable([SCRIPTED, RANDOM], [3, 1])
    assert keywords.ids == (SCRIPTED, RANDOM)
    assert keywords.weights == pytest.approx((0.75, 0.25))
    assert keywords.learned() == []
    live = resolve_stable(["live", RANDOM], [1, 1])
    assert live.ids == (*LIVE_IDS, RANDOM)
    assert live.weights == pytest.approx((0.125,) * 4 + (0.5,))
    assert [k for k, _ in live.learned()] == [1, 2, 3]
    assert resolve_stable(["live"]).weights == pytest.approx((0.25,) * 4)


def test_a_commander_listed_twice_is_an_error(in_repo: None) -> None:
    with pytest.raises(ValueError, match="distinct"):
        resolve_stable(["live", SCRIPTED])


def test_a_checkpoint_spec_loads_its_network(tmp_path: Path) -> None:
    path = tmp_path / "arm" / "checkpoints" / "commander_7.pt"
    save_commander(path, CommanderActor(), {"update": 7})
    stable = resolve_stable([str(path), SCRIPTED])
    assert stable.ids == ("arm/commander_7", SCRIPTED)
    assert [k for k, _ in stable.learned()] == [0]
    with pytest.raises(FileNotFoundError):
        resolve_stable([str(tmp_path / "missing.pt")])


@dataclass
class ListSampler:
    """Hands out fixed rosters in turn."""

    rosters: list[Roster]
    max_ships: int = 20
    drawn: int = field(default=0)

    def sample(self) -> Roster:
        roster = self.rosters[self.drawn % len(self.rosters)]
        self.drawn += 1
        return roster


def _two(learned_weight: float = 0.5) -> CommanderStable:
    return CommanderStable(
        (Commander(SCRIPTED, SCRIPTED), Commander("net", LEARNED, CommanderActor())),
        (1.0 - learned_weight, learned_weight),
    )


def test_the_sampler_draws_shown_sides_and_leaves_hidden_sides_and_drills() -> None:
    shown = Roster.of(["fighter"], ["strafer"], mission=CARRIER_BATTLE)
    hidden = replace(shown, hide_orders=(True, True))
    drill = DrillGenerator().roster("attack", 3)
    sampler = StableSampler(ListSampler([shown, hidden, drill]), _two(1.0), seed=0)
    got = [sampler.sample() for _ in range(3)]
    assert got[0].commanders == (LEARNED, LEARNED)
    assert got[0].commander_ids == ("net", "net")
    assert got[0].teams == shown.teams and got[0].mission == shown.mission
    assert got[1] == hidden, "no commander: the script runs the logistics"
    assert got[2] == drill, "a drill keeps its external commanders"
    assert [commander_label(got[0], t) for t in (0, 1)] == ["net", "net"]
    assert commander_label(got[1], 0) == NO_COMMANDER
    assert commander_label(shown, 1) == SCRIPTED


def test_sides_draw_independently_by_weight_and_the_inner_draws_are_unchanged() -> None:
    distribution = resolve_distribution("pilots_v1")
    plain = make_sampler(distribution, 11)
    wrapped = StableSampler(make_sampler(distribution, 11), _two(0.25), seed=11)
    sides: Counter[tuple[str, str]] = Counter()
    for _ in range(800):
        a, b = plain.sample(), wrapped.sample()
        assert (a.teams, a.mission, a.hide_orders) == (
            b.teams,
            b.mission,
            b.hide_orders,
        )
        if not b.hide_orders[0]:
            sides[b.commander_ids] += 1
    total = sum(sides.values())
    learned = sum(n * ids.count("net") for ids, n in sides.items())
    assert learned / (2 * total) == pytest.approx(0.25, abs=0.05)
    assert sides["net", SCRIPTED] > 0 and sides[SCRIPTED, "net"] > 0


# ---------------------------------------------------------------------------
# decide_learned
# ---------------------------------------------------------------------------


class FakeRaw:
    """The commander bindings of ``rlf_sim.VecEnv``, scripted for one tick."""

    def __init__(self, due: dict[int, np.ndarray]) -> None:
        self.due = due
        self.n = len(due[0])
        self.feature_reads: list[int] = []
        self.submitted: list[tuple[int, list[int], tuple[int, ...]]] = []

    def commander_due(self, team: int) -> np.ndarray:
        return self.due[team]

    def commander_features(self, team: int) -> dict[str, np.ndarray]:
        self.feature_reads.append(team)
        n = self.n
        out: dict[str, np.ndarray] = {
            "globals": np.zeros((n, GLOBAL_DIM), np.float32),
            "entities": np.zeros((n, MAX_ENTITIES, ENTITY_DIM), np.float32),
            "valid": np.zeros((n, MAX_ENTITIES), np.bool_),
        }
        for name, shape in MASK_SHAPES.items():
            out[name] = np.zeros((n, *shape), np.bool_)
        return out

    def submit_commander_actions(
        self, team: int, rows: np.ndarray, actions: np.ndarray
    ) -> None:
        assert rows.dtype == np.int64 and actions.dtype == np.int32
        self.submitted.append((team, rows.tolist(), actions.shape))


@dataclass
class FakeEnv:
    raw: FakeRaw

    @property
    def n_envs(self) -> int:
        return self.raw.n


def test_only_due_envs_with_a_learned_commander_on_that_team_decide() -> None:
    torch.manual_seed(0)
    due = {
        0: np.array([True, True, True, False, True]),
        1: np.array([True, True, False, True, True]),
    }
    side = np.array(
        [[0, 1], [1, NOT_IN_STABLE], [2, 0], [1, 1], [1, 2]], dtype=np.int64
    )
    running = np.array([True, True, True, True, False])
    env = FakeEnv(FakeRaw(due))
    learned = [(1, CommanderActor()), (2, CommanderActor())]
    n = decide_learned(env, side, learned, running)  # type: ignore[arg-type]
    assert env.raw.submitted == [
        (0, [1], (1, ACTION_DIM)),
        (0, [2], (1, ACTION_DIM)),
        (1, [0, 3], (2, ACTION_DIM)),
    ]
    assert n == 4
    assert env.raw.feature_reads == [0, 1], "features read once per team"


def test_nothing_is_read_or_submitted_without_learned_commanders_or_due_envs() -> None:
    due = {0: np.zeros(3, np.bool_), 1: np.array([True, False, False])}
    env = FakeEnv(FakeRaw(due))
    side = np.array([[1, 0], [1, 1], [0, 1]], dtype=np.int64)
    running = np.ones(3, np.bool_)
    assert decide_learned(env, side, [], running) == 0  # type: ignore[arg-type]
    learned = [(1, CommanderActor())]
    assert decide_learned(env, side, learned, running) == 0  # type: ignore[arg-type]
    assert env.raw.feature_reads == [] and env.raw.submitted == []
    with pytest.raises(ValueError, match="one row per env|must be"):
        decide_learned(env, side[:2], learned, running)  # type: ignore[arg-type]


def _decisions(env: RustVecEnv, i: int, team: int) -> int:
    """Decisions team ``team`` of env ``i`` has taken in its current match."""
    count = env.commander_locks(i, team)["decisions"]
    assert isinstance(count, int)
    return count


def test_decisions_reach_the_sim_for_the_learned_team_only() -> None:
    torch.manual_seed(0)
    roster = replace(
        live_mission_rosters(CARRIER_BATTLE)[0], commanders=(LEARNED, SCRIPTED)
    )
    env = RustVecEnv(ASSETS, 2, roster.fleets(), 3, n_threads=1, max_ships=20)
    for i in range(2):
        env.set_next_roster(i, roster)
    env.reset()
    side = np.array([[0, 1], [0, 1]], dtype=np.int64)
    learned = [(0, CommanderActor())]
    running = np.ones(2, np.bool_)
    total = 0
    for _ in range(100):
        total += decide_learned(env, side, learned, running)  # type: ignore[arg-type]
        env.scripted_actions()
        env.step()
    assert total > 0
    assert all(_decisions(env, i, 0) > 0 for i in range(2))
    assert all(_decisions(env, i, 1) == 0 for i in range(2))


# ---------------------------------------------------------------------------
# The trainer
# ---------------------------------------------------------------------------


def test_training_smoke_under_the_live_stable_submits_learned_decisions(
    tmp_path: Path, in_repo: None
) -> None:
    trainer = SpikeTrainer(_config(commander_stable=["live"]), tmp_path)
    assert trainer.commander_ids == LIVE_IDS
    for i, roster in enumerate(trainer.env.rosters):
        assert roster.commander_ids != ("", ""), "commander_p 1: every side drawn"
        for team in (0, 1):
            k = int(trainer.side_commander[i, team])
            assert trainer.commander_ids[k] == roster.commander_ids[team]
            assert (roster.commanders[team] == LEARNED) == (k != 0)
    rows: list[dict[str, Any]] = []
    trainer.train(lambda _t, row: rows.append(row))
    assert len(rows) == 2 and rows[-1]["samples"] > 0
    assert sum(r["commander_decisions"] for r in rows) > 0
    learned_sides = [
        (i, team)
        for i, roster in enumerate(trainer.env.rosters)
        for team in (0, 1)
        if roster.commanders[team] == LEARNED
    ]
    assert learned_sides, "seed 5 draws a learned commander"
    for i, team in learned_sides:
        assert _decisions(trainer.env, i, team) > 0


def test_episode_logs_split_the_learner_s_results_by_commander(
    tmp_path: Path, in_repo: None
) -> None:
    trainer = SpikeTrainer(
        _config(commander_stable=["live"], n_steps=100, n_updates=1), tmp_path
    )
    # Short clocks, so every match ends inside one rollout.
    for i in range(trainer.n_envs):
        roster = trainer.env.rosters[i]
        trainer.env.set_next_roster(i, replace(roster, time_limit_s=2.0))
    trainer.env.reset()
    trainer._note_commanders(np.arange(trainer.n_envs))
    tally, _ = trainer._collect(0)
    fields = tally.log_fields()
    episodes = fields["episodes"]
    assert isinstance(episodes, int) and episodes >= trainer.n_envs
    by_commander = fields["episodes_by_commander"]
    assert isinstance(by_commander, dict) and sum(by_commander.values()) == episodes
    share = fields["commander_share"]
    assert isinstance(share, dict) and sum(share.values()) == pytest.approx(1.0)
    assert set(share) <= set(LIVE_IDS)
    wins = fields["win_by_commander"]
    assert isinstance(wins, dict) and set(wins) == set(by_commander)
    assert all(0.0 <= w <= 1.0 for w in wins.values())
    decisions = fields["commander_decisions"]
    assert isinstance(decisions, int) and decisions > 0


def test_without_a_stable_nothing_changes_and_logs_name_the_condition(
    tmp_path: Path,
) -> None:
    config = _config(roster_overrides={"commander_p": 0.5}, n_steps=100, n_updates=1)
    trainer = SpikeTrainer(config, tmp_path)
    assert trainer.learned_commanders == [] and trainer.commander_ids == ()
    assert (trainer.side_commander == NOT_IN_STABLE).all()
    plain = make_sampler(resolve_distribution(config.roster_distribution()), 5)
    for roster in trainer.env.rosters:
        assert roster.commander_ids == ("", "")
    # The env's first matches are exactly the plain sampler's first draws.
    expected = [plain.sample() for _ in range(trainer.n_envs)]
    assert list(trainer.env.rosters) == expected
    for i in range(trainer.n_envs):
        roster = trainer.env.rosters[i]
        trainer.env.set_next_roster(i, replace(roster, time_limit_s=2.0))
    trainer.env.reset()
    tally, _ = trainer._collect(0)
    fields = tally.log_fields()
    assert fields["commander_decisions"] == 0
    share = fields["commander_share"]
    assert isinstance(share, dict) and set(share) <= {SCRIPTED, NO_COMMANDER}
