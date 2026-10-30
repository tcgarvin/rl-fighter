"""The mission survey (tools/mission_survey.py, WP-S2): aggregation helpers on
hand-built records, the default-roster API, and a tiny script-mode run end to end."""

from __future__ import annotations

import json

import pytest
import rlf_sim

from tools import mission_survey as ms


def _record(**kw: object) -> ms.MatchRecord:
    base: dict[str, object] = {
        "roster": "r",
        "length": 300,
        "winner": 0,
        "end_reason": "carrier_destroyed",
    }
    base.update(kw)
    return ms.MatchRecord(**base)  # type: ignore[arg-type]


def test_quantile_of_nothing_is_zero() -> None:
    assert ms.quantile([], 0.5) == 0.0
    assert ms.quantile([1.0, 3.0], 0.5) == 2.0


def test_launch_histogram_bins_launches_per_match() -> None:
    # Two matches: launches at 2 s and 40 s, and one at 70 s; 30 s bins over 90 s.
    hist = ms.launch_histogram([[60, 1200], [2100]], horizon_s=90.0)
    assert hist == [0.5, 0.5, 0.5]
    # Launches past the horizon land in the last bin.
    assert ms.launch_histogram([[30 * 500]], horizon_s=60.0) == [0.0, 1.0]


def test_summarise_counts_draws_half_and_end_reasons() -> None:
    records = [
        _record(winner=0),
        _record(winner=1),
        _record(winner=-1, end_reason="time_limit", length=4500),
        _record(winner=0, end_reason="time_limit", length=4500),
    ]
    s = ms.summarise("r", records, horizon_s=150.0)
    assert s.n == 4
    assert s.team0_win == pytest.approx(0.625)
    assert s.team1_win == pytest.approx(0.375)
    assert s.draw_rate == pytest.approx(0.25)
    assert s.time_limit_rate == pytest.approx(0.5)
    assert s.end_reasons == {"time_limit": 0.5, "carrier_destroyed": 0.5}
    assert s.length_median_s == pytest.approx(150.0 / 2 + 5.0)


def test_summarise_convoy_escapes_in_defender_wins() -> None:
    records = [
        _record(winner=0, end_reason="convoy_through", transports=4, escaped=3),
        _record(winner=0, end_reason="eliminated", transports=4, escaped=0),
        _record(winner=1, end_reason="convoy_destroyed", transports=4, destroyed=2),
    ]
    s = ms.summarise("c", records, horizon_s=120.0)
    assert s.defender_wins_with_escape == pytest.approx(0.5)
    assert s.escaped_mean == pytest.approx(1.0)
    assert s.destroyed_mean == pytest.approx(2 / 3, abs=0.01)


def test_summarise_refuses_no_records() -> None:
    with pytest.raises(ValueError):
        ms.summarise("empty", [], horizon_s=1.0)


def test_end_state_sample_counts_strike_craft_and_hangar() -> None:
    rec = _record()
    ships = [
        {"team": 0, "alive": True, "role": "carrier", "hp": 750.0, "max_hp": 1500.0, "docked": False},
        {"team": 0, "alive": True, "role": "fighter", "docked": True},
        {"team": 0, "alive": True, "role": "fighter", "docked": False},
        {"team": 1, "alive": False, "role": "fighter", "docked": False},
        {"team": 1, "alive": True, "role": "transport", "docked": False},
        {"team": 1, "alive": True, "role": "skirmisher", "docked": False, "escaped": False},
        {"team": -1, "alive": False, "role": "", "docked": False},
    ]
    ms._sample_end_state(rec, ships)
    assert rec.strike_left == (1, 1)
    assert rec.hangar_left == (1, 0)
    assert rec.carrier_hp == (0.5, 0.0)


def test_default_rosters_fit_the_ship_cap_and_their_mission() -> None:
    roles = ms.load_roles()
    for mission in ms.MISSIONS:
        rosters = ms.default_rosters(mission)
        assert len(rosters) >= 2, mission
        assert len({r.name for r in rosters}) == len(rosters)
        for r in rosters:
            assert r.n_ships <= rlf_sim.MAX_SHIPS
            assert all(h in roles for f in r.fleets for h in f)
    assert rlf_sim.mission_rosters("deathmatch") == []
    with pytest.raises(ValueError):
        rlf_sim.mission_rosters("duel")


def test_script_survey_runs_both_missions_end_to_end() -> None:
    result = ms.survey("script", n_per_roster=1, seed=7, checkpoint=None)
    data = json.loads(json.dumps(result.to_dict()))
    assert data["schema"] == ms.SCHEMA
    assert [m["mission"] for m in data["missions"]] == list(ms.MISSIONS)
    for m in result.missions:
        assert m.overall.n == len(ms.default_rosters(m.mission))
        assert sum(m.overall.end_reasons.values()) == pytest.approx(1.0)
    carrier = result.missions[0].overall
    assert carrier.launches_per_match > 0
    assert "carrier_battle" in ms.markdown(result)


def test_live_mode_needs_a_checkpoint() -> None:
    with pytest.raises(ValueError):
        ms.survey("live", n_per_roster=1, seed=0, checkpoint=None)
    with pytest.raises(ValueError):
        ms.survey("bogus", n_per_roster=1, seed=0, checkpoint=None)
