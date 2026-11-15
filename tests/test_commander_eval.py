"""The commander eval's sides: the unseen commander, and the pilots both sides draw."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch

from spacefight.commander import eval as commander_eval
from spacefight.commander.eval import UNSEEN, Commander, play_matches
from spacefight.commander.pilots import LIVE_PILOTS
from spacefight.env.rosters import DEATHMATCH, RANDOM, SCRIPTED, Roster
from spacefight.env.rust_env import RustVecEnv
from spacefight.population.records import load_population, sha256_of

REPO = Path(__file__).resolve().parents[1]
SEASON = REPO / "lab" / "population" / "2026-11-sim6"
PILOTS = ("fighters_pay1_462", "transit_300")


def test_unseen_is_the_script_with_its_orders_hidden() -> None:
    unseen = Commander.from_spec(UNSEEN)
    assert (unseen.label, unseen.mode, unseen.hide_orders) == (UNSEEN, SCRIPTED, True)
    assert unseen.actor is None
    for spec in (SCRIPTED, RANDOM):
        shown = Commander.from_spec(spec)
        assert (shown.label, shown.mode, shown.hide_orders) == (spec, spec, False)


def _fake_evaluate(seen: dict[str, Any]):
    def evaluate(a: str, b: str, n: int, seed: int, threads: int, pilots: Path):
        seen.update(a=a, b=b, n=n, pilots=pilots)
        orders = {"orders_ended": 0}
        return {"a": a, "b": b, "score_a": 0.5, "orders_a": orders, "orders_b": orders}

    return evaluate


def test_the_pilots_option_names_the_list_both_sides_draw_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr(commander_eval, "evaluate", _fake_evaluate(seen))
    out = tmp_path / "eval.json"
    pool = tmp_path / "followers.json"
    args = ["--a", UNSEEN, "--n-per-mission", "48", "--out", str(out)]
    assert commander_eval.main([*args, "--pilots", str(pool)]) == 0
    assert seen == {"a": UNSEEN, "b": SCRIPTED, "n": 48, "pilots": pool}
    assert json.loads(out.read_text())["a"] == UNSEEN
    assert commander_eval.main(args) == 0
    assert seen["pilots"] == LIVE_PILOTS, "the live list unless another is named"


def _checkpoints() -> list[tuple[str, Path]]:
    population = load_population(SEASON)
    return [(p, REPO / population.member(p).checkpoint) for p in PILOTS]


def _checkpoints_present() -> bool:
    population = load_population(SEASON)
    return all(
        path.is_file() and sha256_of(path) == population.member(p).sha256
        for p, path in _checkpoints()
    )


needs_weights = pytest.mark.skipif(
    not _checkpoints_present(), reason="pilot weights are not in this checkout"
)


@needs_weights
def test_only_the_unseen_commanders_own_side_has_its_orders_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hidden: list[tuple[bool, bool]] = []
    queue = RustVecEnv.set_next_roster

    def spy(self: RustVecEnv, i: int, roster: Roster, **kwargs: Any) -> None:
        hidden.append(kwargs["hide_orders"])
        queue(self, i, roster, **kwargs)

    monkeypatch.setattr(RustVecEnv, "set_next_roster", spy)
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        played = play_matches(
            [Roster.of(["fighter"], ["fighter"])] * 2,
            DEATHMATCH,
            (Commander.from_spec(UNSEEN), Commander.from_spec(SCRIPTED)),
            np.array([[0, 1], [1, 0]]),
            seed=3,
            n_threads=1,
            pilots=_checkpoints(),
        )
    finally:
        torch.set_num_threads(threads)
    assert hidden == [(True, False), (False, True)]
    assert played.winner.shape == (2,)
