"""The pilot draw: one pilot per ship (the default, as it always was), one per side
(each side a commander and a pilot), and pinning a side's pilot in the commander eval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

import spacefight.commander.pilots as pilots_module
from spacefight.commander import eval as commander_eval
from spacefight.commander.eval import ASSETS, DRAWN, Commander, MatchesPlayed
from spacefight.commander.pilots import (
    PILOT_DRAW_SHIP,
    PILOT_DRAW_SIDE,
    UNPINNED,
    PilotStable,
)
from spacefight.commander.train import TrainConfig
from spacefight.env.rosters import DEATHMATCH, SCRIPTED, capital_hull_ids

N_PILOTS = 4


class _Ships:
    """Just enough of an env for a draw: per match a carrier and three strike craft on
    team 0, four strike craft on team 1, and a padding slot."""

    def __init__(self, n_envs: int) -> None:
        capital = capital_hull_ids(ASSETS)[0]
        strike = next(h for h in range(10) if h not in capital_hull_ids(ASSETS))
        hulls = [capital, strike, strike, strike, strike, strike, strike, strike, -1]
        teams = [0, 0, 0, 0, 1, 1, 1, 1, -1]
        self.hull_id = np.array([hulls] * n_envs, dtype=np.int16)
        self.team = np.array([teams] * n_envs, dtype=np.int8)


def _stable(
    monkeypatch: pytest.MonkeyPatch, n_envs: int, mode: str = PILOT_DRAW_SHIP
) -> PilotStable:
    monkeypatch.setattr(pilots_module, "Policy", lambda path, sample: object())
    pilots = [(f"p{k}", Path(f"p{k}.pt")) for k in range(N_PILOTS)]
    return PilotStable(pilots, n_envs, 9, 5, ASSETS, mode=mode)


def _drawn(stable: PilotStable, env: _Ships, pinned: Any = None) -> NDArray[np.int64]:
    stable.draw(env, range(env.hull_id.shape[0]), pinned)  # type: ignore[arg-type]
    return stable.assign.copy()


def test_the_default_draw_is_ship_by_ship_and_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assign = _drawn(_stable(monkeypatch, 50), _Ships(50))
    rng = np.random.default_rng(5)
    expected = np.stack([rng.integers(0, N_PILOTS, 7) for _ in range(50)])
    np.testing.assert_array_equal(assign[:, 1:8], expected)
    assert len(set(assign[0, 1:8].tolist())) > 1, "ships of one side differ"


def test_a_side_draw_flies_one_pilot_per_side_evenly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = _Ships(4000)
    assign = _drawn(_stable(monkeypatch, 4000, PILOT_DRAW_SIDE), env)
    team0, team1 = assign[:, 1:4], assign[:, 4:8]
    assert (team0 == team0[:, :1]).all(), "team 0's strike craft fly one pilot"
    assert (team1 == team1[:, :1]).all(), "team 1's strike craft fly one pilot"
    assert (assign[:, 0] == N_PILOTS).all(), "the carrier flies its script"
    assert (assign[:, 8] == N_PILOTS).all(), "padding flies nothing"
    for side in (team0[:, 0], team1[:, 0]):
        shares = np.bincount(side, minlength=N_PILOTS) / side.size
        assert np.allclose(shares, 1 / N_PILOTS, atol=0.03), shares
    assert (team0[:, 0] != team1[:, 0]).mean() == pytest.approx(0.75, abs=0.03)
    again = _drawn(_stable(monkeypatch, 4000, PILOT_DRAW_SIDE), env)
    np.testing.assert_array_equal(assign, again, "the same seed draws the same sides")


@pytest.mark.parametrize("mode", [PILOT_DRAW_SHIP, PILOT_DRAW_SIDE])
def test_a_pinned_side_flies_its_pilot_and_the_other_side_is_drawn_as_without_pins(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    env = _Ships(30)
    free = _drawn(_stable(monkeypatch, 30, mode), env)
    pinned = np.tile([2, UNPINNED], (30, 1))
    pinned[::2] = [UNPINNED, 3]
    assign = _drawn(_stable(monkeypatch, 30, mode), env, pinned)
    odd, even = slice(1, None, 2), slice(0, None, 2)
    assert (assign[odd, 1:4] == 2).all()
    np.testing.assert_array_equal(assign[odd, 4:8], free[odd, 4:8])
    assert (assign[even, 4:8] == 3).all()
    np.testing.assert_array_equal(assign[even, 1:4], free[even, 1:4])
    np.testing.assert_array_equal(assign[:, [0, 8]], free[:, [0, 8]])


def test_a_bad_mode_or_pin_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="pilot draw"):
        _stable(monkeypatch, 2, "fleet")
    stable = _stable(monkeypatch, 2)
    with pytest.raises(ValueError, match="pinned must be"):
        _drawn(stable, _Ships(2), np.zeros((2, 3)))
    with pytest.raises(ValueError, match="pinned pilots"):
        _drawn(stable, _Ships(2), np.full((2, 2), N_PILOTS + 1))


def test_training_draws_ship_by_ship_unless_told_otherwise() -> None:
    assert TrainConfig().pilot_draw == PILOT_DRAW_SHIP
    assert TrainConfig(pilot_draw=PILOT_DRAW_SIDE).pilot_draw == PILOT_DRAW_SIDE
    with pytest.raises(ValueError, match="pilot_draw"):
        TrainConfig(pilot_draw="fleet")


def test_the_eval_flags_reach_evaluate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    def evaluate(*args: Any, **kwargs: Any) -> dict[str, Any]:
        seen.update(kwargs)
        orders = {"orders_ended": 0}
        return {
            "a": "x",
            "b": "y",
            "score_a": 0.5,
            "orders_a": orders,
            "orders_b": orders,
        }

    monkeypatch.setattr(commander_eval, "evaluate", evaluate)
    out = str(tmp_path / "e.json")
    base = ["--a", SCRIPTED, "--n-per-mission", "48", "--out", out]
    assert commander_eval.main(base) == 0
    assert (seen["pilot_draw"], seen["pilot_a"], seen["pilot_b"]) == (
        PILOT_DRAW_SHIP,
        DRAWN,
        DRAWN,
    )
    flags = ["--pilot-draw", "side", "--pilot-a", "p1", "--checkpoint-root", "/x"]
    assert commander_eval.main([*base, *flags]) == 0
    assert (seen["pilot_draw"], seen["pilot_a"], seen["pilot_b"]) == (
        PILOT_DRAW_SIDE,
        "p1",
        DRAWN,
    )
    assert seen["checkpoint_root"] == Path("/x")


def test_play_mission_pins_each_sides_pilot_on_whichever_team_it_plays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def play_matches(rosters: Any, *args: Any, **kwargs: Any) -> MatchesPlayed:
        seen.update(kwargs)
        n = len(rosters)
        none = np.zeros((n, 2))
        return MatchesPlayed(
            np.zeros(n, dtype=np.int64),
            np.zeros(n, dtype=np.int64),
            none.astype(np.int64),
            0,
            none.astype(bool),
            none.astype(np.int8),
            none.astype(np.int16),
            [commander_eval.OrderStats(), commander_eval.OrderStats()],
        )

    monkeypatch.setattr(commander_eval, "play_matches", play_matches)
    a, b = Commander.from_spec(SCRIPTED), Commander.from_spec(SCRIPTED)
    commander_eval.play_mission(a, b, DEATHMATCH, 96, 1, 1, [], PILOT_DRAW_SIDE, 7, -1)
    pinned = seen["pinned_pilots"]
    a_team = (np.arange(96) // 24) % 2
    np.testing.assert_array_equal(pinned[a_team == 0], [[7, -1]] * 48)
    np.testing.assert_array_equal(pinned[a_team == 1], [[-1, 7]] * 48)
    assert seen["pilot_draw"] == PILOT_DRAW_SIDE
    commander_eval.play_mission(a, b, DEATHMATCH, 48, 1, 1, [])
    assert seen["pinned_pilots"] is None, "no pins, no pinned draw"


def test_evaluate_refuses_a_pinned_pilot_not_on_the_list(tmp_path: Path) -> None:
    (tmp_path / "p.pt").write_bytes(b"")
    pilots = tmp_path / "pilots.json"
    entry = {"id": "p", "checkpoint": "p.pt"}
    pilots.write_text(json.dumps({"schema": "rlf.live_pilots/1", "pilots": [entry]}))
    with pytest.raises(ValueError, match="not on"):
        commander_eval.evaluate(
            SCRIPTED,
            SCRIPTED,
            48,
            live_pilots=pilots,
            pilot_a="nobody",
            checkpoint_root=tmp_path,
        )
