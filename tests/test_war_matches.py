"""The WAR runner: the script in the pilot draw, and a tiny real run that resumes."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

import spacefight.commander.pilots as pilots_module
from spacefight.commander.eval import ASSETS, Commander
from spacefight.commander.pilots import PilotStable
from spacefight.env.rosters import DEATHMATCH, RANDOM, SCRIPTED, capital_hull_ids
from spacefight.population import war_matches
from spacefight.population.records import SCRIPT_ID, load_population, sha256_of
from spacefight.population.war import read_war
from spacefight.population.war_matches import resolve_commanders, run_war

REPO = Path(__file__).resolve().parents[1]
SEASON = REPO / "lab" / "population" / "2026-11-sim6"
PILOTS = ("fighters_pay1_462", "transit_300")


class _Hulls:
    """Just enough of an env for a draw: strike craft, a capital ship, padding."""

    def __init__(self, n_envs: int) -> None:
        capital = capital_hull_ids(ASSETS)[0]
        strike = next(h for h in range(10) if h not in capital_hull_ids(ASSETS))
        row = [capital, *[strike] * 6, -1]
        self.hull_id = np.array([row] * n_envs, dtype=np.int16)


def _stable(
    monkeypatch: pytest.MonkeyPatch, n_envs: int, include_script: bool
) -> PilotStable:
    monkeypatch.setattr(pilots_module, "Policy", lambda path, sample: object())
    pilots = [("a", Path("a.pt")), ("b", Path("b.pt"))]
    return PilotStable(pilots, n_envs, 8, 5, ASSETS, include_script=include_script)


def test_the_script_flies_strike_craft_as_often_as_any_pilot_when_drawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = _Hulls(2000)
    stable = _stable(monkeypatch, 2000, include_script=True)
    stable.draw(env, range(2000))  # type: ignore[arg-type]
    strike = stable.assign[:, 1:7]
    shares = np.bincount(strike.ravel(), minlength=3) / strike.size
    assert np.allclose(shares, 1 / 3, atol=0.02), shares
    assert (stable.assign[:, 0] == stable.script).all(), "capital ships fly scripts"
    assert (stable.assign[:, 7] == stable.script).all(), "padding flies nothing"


def test_without_the_script_the_draw_is_what_it_always_was(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = _Hulls(50)
    stable = _stable(monkeypatch, 50, include_script=False)
    stable.draw(env, range(50))  # type: ignore[arg-type]
    rng = np.random.default_rng(5)
    expected = np.stack([rng.integers(0, 2, 6) for _ in range(50)])
    np.testing.assert_array_equal(stable.assign[:, 1:7], expected)


def _checkpoints_present() -> bool:
    population = load_population(SEASON)
    return all(
        (REPO / population.member(p).checkpoint).is_file()
        and sha256_of(REPO / population.member(p).checkpoint)
        == population.member(p).sha256
        for p in PILOTS
    )


needs_weights = pytest.mark.skipif(
    not _checkpoints_present(), reason="pilot weights are not in this checkout"
)


@pytest.fixture
def one_torch_thread():
    """Tiny batches on a busy machine crawl when torch spreads over every core."""
    before = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(before)


@needs_weights
def test_a_tiny_war_run_plays_resumes_and_refuses_another_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, one_torch_thread: None
) -> None:
    population = load_population(SEASON)
    commanders = [(Commander(SCRIPTED, SCRIPTED), ""), (Commander(RANDOM, RANDOM), "")]

    def run(seed: int = 11) -> object:
        return run_war(
            population,
            [*PILOTS, SCRIPT_ID],
            commanders,
            tmp_path,
            n_per_mission=2,
            seed=seed,
            n_threads=1,
            checkpoint_root=REPO,
            chunk=1,
            deathmatch_drafts=2,
            n_bootstrap=10,
            missions=(DEATHMATCH,),
        )

    run()
    document = read_war(tmp_path / "war.json")
    assert len(document.records) == 2
    assert sorted(p for p, _ in document.config["pilots"]) == sorted(PILOTS)
    assert {p.pilot for p in document.fit.pilots} <= {*PILOTS, SCRIPT_ID}
    for record in document.records:
        assert record.mission == DEATHMATCH
        assert set(record.commanders) <= {SCRIPTED, RANDOM}
        assert all(sum(record.pilot_ships(t).values()) > 0 for t in (0, 1))
        assert set(record.pilot_ships(0)) | set(record.pilot_ships(1)) <= {
            *PILOTS,
            SCRIPT_ID,
        }
    assert sorted(p.name for p in (tmp_path / "matches").iterdir()) == [
        "deathmatch-000.json",
        "deathmatch-001.json",
    ]
    assert (tmp_path / "war.md").read_text().startswith("# Wins above replacement")

    def no_more_matches(*args: object, **kwargs: object) -> None:
        raise AssertionError("a finished chunk was played again")

    monkeypatch.setattr(war_matches, "play_chunk", no_more_matches)
    run()
    assert read_war(tmp_path / "war.json").records == document.records
    with pytest.raises(ValueError, match="different config"):
        run(seed=12)


def test_the_live_commander_stable_resolves_and_labels_must_differ(
    tmp_path: Path,
) -> None:
    stable = tmp_path / "live.json"
    stable.write_text(
        json.dumps(
            {
                "schema": "rlf.live_commanders/1",
                "entry": "",
                "commanders": [{"id": "scripted", "kind": "scripted", "note": "x"}],
            }
        )
    )
    resolved = resolve_commanders(["live", RANDOM], stable)
    assert [(c.label, c.mode, sha) for c, sha in resolved] == [
        (SCRIPTED, SCRIPTED, ""),
        (RANDOM, RANDOM, ""),
    ]
    with pytest.raises(ValueError, match="distinct"):
        resolve_commanders(["live", SCRIPTED], stable)
    with pytest.raises(FileNotFoundError):
        resolve_commanders(["no/such/commander.pt"], stable)
