"""Tests for the fixed duel eval harness (spacefight/eval, spike plan §6.1, §8 D)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch
import yaml
from numpy.typing import NDArray

from spacefight.env.rust_env import ACTION_WIDTH, RustVecEnv, action_block
from spacefight.eval import features as F
from spacefight.rl import spike_policy
from spacefight.eval.controllers import (
    Policy,
    RandomController,
    Scripted,
    idle_actions,
    make_controller,
)
from spacefight.eval.duel import (
    ASSETS,
    MARKDOWN_HEADER,
    SCHEMA,
    DuelResult,
    EvalConfig,
    evaluate,
    main,
    run_matches,
)

THREADS = 4


class RecordingScripted(Scripted):
    """Scripted controller that remembers every slot it was asked to drive."""

    def __init__(self) -> None:
        self.asked: NDArray[np.bool_] | None = None

    def act(self, env: RustVecEnv, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        self.asked = rows.copy() if self.asked is None else self.asked | rows
        return super().act(env, rows)


@pytest.fixture(scope="module")
def script_32() -> DuelResult:
    return evaluate(Scripted(), Scripted(), n=32, seed=100_000, n_threads=THREADS)


def test_script_vs_script_is_deterministic_across_calls(
    script_32: DuelResult,
) -> None:
    again = evaluate(Scripted(), Scripted(), n=32, seed=100_000, n_threads=THREADS)
    assert again == script_32


def test_script_vs_script_is_identical_across_thread_counts(
    script_32: DuelResult,
) -> None:
    single = evaluate(Scripted(), Scripted(), n=32, seed=100_000, n_threads=1)
    assert single == script_32


def test_random_controller_is_deterministic_per_seed() -> None:
    first = evaluate(RandomController(3), Scripted(), n=8, n_threads=THREADS)
    second = evaluate(RandomController(3), Scripted(), n=8, n_threads=THREADS)
    other = evaluate(RandomController(4), Scripted(), n=8, n_threads=THREADS)
    assert first == second
    assert first.side_a != other.side_a


def test_script_vs_script_metrics_are_plausible(script_32: DuelResult) -> None:
    m, a, b = script_32.match, script_32.side_a, script_32.side_b
    assert script_32.a == script_32.b == "script"
    assert a.wins + a.draws + a.losses == 32
    assert (a.wins, a.draws, a.losses) == (b.losses, b.draws, b.wins)
    assert a.win_rate + b.win_rate == pytest.approx(1.0)
    assert m.kill_rate + m.time_limit_rate == pytest.approx(1.0)
    assert m.length_p10 <= m.length_median <= m.length_p90
    for side in (a, b):
        assert 0.3 < side.hit_rate < 0.9
        assert side.passes >= 1.0
        assert 0.0 < side.engagement_rate <= 1.0
        assert 0.2 < side.main_engine_duty < 1.0
        assert 0.0 < side.fire_rate < 0.5
        assert side.mean_speed > 5.0
        assert side.nan_or_stuck == 0
        assert side.outside_share < 0.05


def test_random_controller_is_a_floor_against_the_script() -> None:
    result = evaluate(RandomController(0), Scripted(), n=16, n_threads=THREADS)
    assert result.side_a.win_rate < 0.2
    assert result.side_a.hit_rate < result.side_b.hit_rate


def test_sides_are_swapped_in_exactly_half_the_matches() -> None:
    a, b = RecordingScripted(), RecordingScripted()
    records = run_matches(a, b, EvalConfig(n=32), n_threads=THREADS)
    assert int((records.a_team == 0).sum()) == 16
    assert int((records.a_team == 1).sum()) == 16
    assert a.asked is not None and b.asked is not None
    a_rows = records.team == records.a_team[:, None]
    assert np.array_equal(a.asked, a_rows)
    assert np.array_equal(b.asked, ~a_rows)


def test_odd_n_is_rejected() -> None:
    with pytest.raises(ValueError, match="even"):
        evaluate(Scripted(), Scripted(), n=3)


def _hand_count_first_episode(seed: int) -> dict[str, Any]:
    """Count env 0's first episode with a plain per-tick loop over raw buffers."""
    gun_range = float(
        yaml.safe_load((ASSETS / "weapons.yaml").read_text())["gauss"]["range"]
    )
    env = RustVecEnv(
        ASSETS, 2, [["fighter"], ["fighter"]], seed, n_threads=1, record_events=True
    )
    shots, hit_events, hit_rows, passes = [0, 0], [0, 0], [0, 0], [0, 0]
    damage = [0.0, 0.0]
    in_range = [False, False]
    for step in range(1, 3000):
        env.scripted_actions()
        _, _, dones, info = env.step()
        for ev in env.events():
            if int(ev[F.EV_MATCH]) != 0:
                continue
            kind = int(ev[F.EV_KIND])
            if kind == F.KIND_FIRE:
                shots[int(ev[F.EV_A])] += 1
            elif kind in (F.KIND_HIT, F.KIND_SHIELD_HIT):
                hit_events[int(ev[F.EV_B])] += 1
        for k in range(int(info.hit_count[0])):
            row = info.hits[0, k]
            hit_rows[int(row[0])] += 1
            damage[int(row[0])] += float(row[3]) / 1000.0
        if dones[0]:
            return {
                "length": step,
                "winner": int(info.winner[0]),
                "shots": shots,
                "hit_events": hit_events,
                "hits": hit_rows,
                "damage": damage,
                "passes": passes,
            }
        for ship in (0, 1):
            obs = env.obs[0, ship]
            if obs[F.SELF_PRESENT] < 0.5 or obs[F.NEAREST_PRESENT] < 0.5:
                continue
            now_in = obs[F.NEAREST_DIST] * 450.0 < gun_range
            if now_in and not in_range[ship]:
                passes[ship] += 1
            in_range[ship] = bool(now_in)
    raise AssertionError("episode did not end")


def test_metrics_match_a_hand_count_of_one_episode() -> None:
    seed = 100_000
    hand = _hand_count_first_episode(seed)
    records = run_matches(
        Scripted(), Scripted(), EvalConfig(n=2, seed=seed), n_threads=1
    )
    assert records.a_team[0] == 0
    assert hand["hits"] == hand["hit_events"]
    assert hand["passes"][0] >= 1 and sum(hand["shots"]) > 0
    assert records.length[0] == hand["length"]
    assert records.winner[0] == hand["winner"]
    assert records.shots[0].tolist() == hand["shots"]
    assert records.hits[0].tolist() == hand["hits"]
    assert records.passes[0].tolist() == hand["passes"]
    assert records.hull_damage[0] == pytest.approx(hand["damage"])


def test_json_round_trip_keeps_every_field(script_32: DuelResult) -> None:
    text = script_32.to_json()
    data = json.loads(text)
    assert data["schema"] == SCHEMA
    assert set(data) == {"schema", "a", "b", "config", "match", "side_a", "side_b"}
    assert DuelResult.from_json(text) == script_32


def test_json_with_another_schema_or_missing_keys_is_rejected(
    script_32: DuelResult,
) -> None:
    data = script_32.to_dict()
    with pytest.raises(ValueError, match="schema"):
        DuelResult.from_dict({**data, "schema": "rlf.eval.duel/0"})
    side = dict(data["side_a"])
    del side["hit_rate"]
    with pytest.raises(ValueError, match="hit_rate"):
        DuelResult.from_dict({**data, "side_a": side})


def test_markdown_row_has_one_cell_per_header_column(script_32: DuelResult) -> None:
    columns = MARKDOWN_HEADER.splitlines()[0].count("|")
    for side in ("a", "b"):
        row = script_32.markdown_row(side)
        assert "\n" not in row
        assert row.count("|") == columns
    with pytest.raises(ValueError):
        script_32.markdown_row("c")


def test_cli_writes_the_result_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "eval.json"
    assert (
        main(["--a", "random", "--n", "4", "--n-threads", "2", "--out", str(out)]) == 0
    )
    result = DuelResult.from_json(out.read_text())
    assert (result.a, result.b, result.config.n) == ("random", "script", 4)
    assert "| random | script | 4 |" in capsys.readouterr().out


def test_idle_actions_hold_every_head() -> None:
    rows = idle_actions(3)
    assert rows.shape == (3, ACTION_WIDTH)
    assert (action_block(rows, "throttle") == 1).all()
    assert (action_block(rows, "slew") == 1).all()
    assert (action_block(rows, "fire") == 0).all()
    assert (action_block(rows, "power") == 0).all()


# -- Policy, against a stub of WP-B's spacefight.rl.spike_policy -------------------


@pytest.fixture
def checkpoint(tmp_path: Path) -> Path:
    """A freshly initialised spike actor/critic saved with ``save_policy``."""
    torch.manual_seed(0)
    path = tmp_path / "init.pt"
    spike_policy.save_policy(
        path, spike_policy.SpikeActor(), spike_policy.SpikeCritic(), {"kind": "test"}
    )
    return path


def test_policy_controller_labels_and_row_shapes(checkpoint: Path) -> None:
    sampled = make_controller(str(checkpoint))
    argmax = Policy(checkpoint, sample=False)
    assert sampled.label == "policy:init.pt"
    assert argmax.label == "policy:init.pt:argmax"
    env = RustVecEnv(ASSETS, 2, [["fighter"], ["fighter"]], 0, n_threads=1)
    rows = np.zeros((2, 2), dtype=bool)
    rows[:, 1] = True
    none = np.zeros((2, 2), dtype=bool)
    for ctrl in (sampled, argmax):
        ctrl.reset(0)
        actions = ctrl.act(env, rows)
        assert actions.shape == (2, ACTION_WIDTH) and actions.dtype == np.int8
        assert ctrl.act(env, none).shape == (0, ACTION_WIDTH)


def test_argmax_policy_matches_act_numpy_on_the_same_rows(checkpoint: Path) -> None:
    env = RustVecEnv(ASSETS, 4, [["fighter"], ["fighter"]], 1, n_threads=1)
    for _ in range(120):  # past the arrival, so the obs are not all zero
        env.step(env.scripted_actions())
    rows = np.ones((4, 2), dtype=bool)
    policy = Policy(checkpoint, sample=False)
    masks = spike_policy.HeadMasks.from_numpy(
        env.thruster_mask, env.turret_mask, env.fixed_turret
    )
    expected = spike_policy.act_numpy(policy.actor, env.obs, masks, deterministic=True)
    assert np.array_equal(policy.act(env, rows), expected.reshape(-1, ACTION_WIDTH))


@pytest.mark.parametrize("sample", [True, False])
def test_policy_eval_is_deterministic(checkpoint: Path, sample: bool) -> None:
    def run() -> DuelResult:
        return evaluate(Policy(checkpoint, sample=sample), Scripted(), n=4, n_threads=2)

    first = run()
    assert first == run()
    assert first.a.startswith("policy:init.pt")
    assert first.side_a.wins + first.side_a.draws + first.side_a.losses == 4


def test_policy_controller_needs_an_existing_checkpoint(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Policy(tmp_path / "missing.pt")


def test_eval_config_records_the_scenario(script_32: DuelResult) -> None:
    cfg = script_32.config
    assert replace(cfg) == EvalConfig(n=32)
    assert cfg.fleets == (("fighter",), ("fighter",))
    assert cfg.reaction_ticks == 2
