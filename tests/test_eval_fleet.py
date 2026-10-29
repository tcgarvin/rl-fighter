"""Fleet eval harness (spacefight.eval.fleet)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from spacefight.env.rosters import Roster
from spacefight.eval import duel, fleet
from spacefight.eval.controllers import RandomController, Scripted

TINY = (
    fleet.SuiteEntry("1v1 F v F", "1v1", Roster.of(["fighter"], ["fighter"])),
    fleet.SuiteEntry(
        "2v3 FG v FSS",
        "2v3",
        Roster.of(["fighter", "gunship"], ["fighter"] * 2 + ["strafer"]),
    ),
)


@pytest.fixture
def tiny_suite(monkeypatch: pytest.MonkeyPatch) -> fleet.FleetEvalConfig:
    monkeypatch.setitem(fleet.SUITES, "tiny", TINY)
    return fleet.FleetEvalConfig(
        suite="tiny", n_per_roster=4, seed=11, time_limit_s=30.0
    )


def test_suites_are_well_formed() -> None:
    for name, entries in fleet.SUITES.items():
        names = [e.name for e in entries]
        assert len(names) == len(set(names)), name
        assert all(e.roster.n_ships <= 8 for e in entries)
    classes = {e.klass for e in fleet.SUITES["fleet_v1"]}
    assert {"1v1", "2v2", "3v3", "2v3", "4v4"} <= classes
    singles = {e.roster.teams[0] for e in fleet.SUITES["fleet_v1"] if e.klass == "1v1"}
    assert singles == {("fighter",), ("strafer",), ("gunship",)}


def test_a_flies_each_side_of_every_roster_equally(
    tiny_suite: fleet.FleetEvalConfig,
) -> None:
    env, entry = fleet.build_env(tiny_suite, n_threads=2)
    tracker = fleet._FleetTracker(env, entry)
    for k in range(len(TINY)):
        block = entry == k
        assert tracker.records.a_team[block].tolist() == [0, 1, 0, 1]
        # In the uneven roster a has 2 ships on team 0 and 3 on team 1.
        sizes = tracker.a_rows[block].sum(axis=1).tolist()
        if k == 1:
            assert sizes == [2, 3, 2, 3]
    assert not (tracker.a_rows & tracker.b_rows).any()
    assert ((tracker.a_rows | tracker.b_rows) == (env.team >= 0)).all()


def test_eval_is_deterministic_and_thread_independent(
    tiny_suite: fleet.FleetEvalConfig,
) -> None:
    one = fleet.evaluate(Scripted(), Scripted(), tiny_suite, n_threads=1)
    two = fleet.evaluate(Scripted(), Scripted(), tiny_suite, n_threads=3)
    assert one.to_dict() == two.to_dict()


def test_json_round_trip(tiny_suite: fleet.FleetEvalConfig) -> None:
    result = fleet.evaluate(Scripted(), RandomController(0), tiny_suite, n_threads=2)
    again = fleet.FleetResult.from_json(result.to_json())
    assert again == result
    data = json.loads(result.to_json())
    assert data["schema"] == "rlf.eval.fleet/1"
    data["schema"] = "rlf.eval.fleet/0"
    with pytest.raises(ValueError, match="schema"):
        fleet.FleetResult.from_dict(data)
    assert "| class |" in result.markdown()


def test_script_beats_random(tiny_suite: fleet.FleetEvalConfig) -> None:
    result = fleet.evaluate(Scripted(), RandomController(0), tiny_suite, n_threads=2)
    assert result.side_a.win_rate > 0.7
    assert result.side_a.all_ships.damage_dealt > result.side_b.all_ships.damage_dealt
    assert set(result.side_a.hulls) == {"fighter", "gunship", "strafer"}


def test_fighter_duel_numbers_match_the_duel_eval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 1v1 fighter suite with the duel's seeds reproduces the duel eval exactly."""
    monkeypatch.setitem(fleet.SUITES, "duel", TINY[:1])
    cfg = fleet.FleetEvalConfig(suite="duel", n_per_roster=8, seed=100_000)
    f = fleet.evaluate(Scripted(), Scripted(), cfg, n_threads=2)
    d = duel.evaluate(Scripted(), Scripted(), n=8, seed=100_000, n_threads=2)
    a = f.side_a.all_ships
    assert f.side_a.win_rate == pytest.approx(d.side_a.win_rate)
    assert a.shots == pytest.approx(d.side_a.shots)
    assert a.hits == pytest.approx(d.side_a.hits)
    assert a.hit_rate == pytest.approx(d.side_a.hit_rate)
    assert a.damage_dealt == pytest.approx(d.side_a.damage_dealt)
    assert a.engagement_rate == pytest.approx(d.side_a.engagement_rate)
    assert a.engine_duty == pytest.approx(d.side_a.main_engine_duty)
    assert a.passes == pytest.approx(d.side_a.passes)
    assert a.fire_rate == pytest.approx(d.side_a.fire_rate)
    assert f.match.length_median == pytest.approx(d.match.length_median)
    assert f.match.draw_rate == pytest.approx(d.match.draw_rate)


def test_survival_and_time_limit_are_consistent(
    tiny_suite: fleet.FleetEvalConfig,
) -> None:
    records = fleet.run_matches(Scripted(), Scripted(), tiny_suite, n_threads=2)
    real = records.team >= 0
    for i in range(records.length.size):
        alive = real[i] & ~records.died[i]
        teams_alive = {int(t) for t in records.team[i][alive]}
        if records.timed_out[i]:
            assert teams_alive == {0, 1}
        else:
            assert len(teams_alive) <= 1
            if records.winner[i] >= 0:
                assert teams_alive == {int(records.winner[i])}
    assert np.all(records.length > 0)
