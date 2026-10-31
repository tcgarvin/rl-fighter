"""Run B3's gates (``spacefight.eval.order_gates_b3``): the teacher-first O bounds,
the checks against the hidden pass, M against v1 and w1_400, and the pick."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest

from spacefight.env.rosters import CARRIER_BATTLE, CONVOY_ESCORT, RANDOM, SCRIPTED
from spacefight.eval import order_gates_b3 as G
from spacefight.eval.fleet import FleetResult
from spacefight.eval.missions import (
    MissionEvalConfig,
    MissionResult,
    MissionSummary,
    SideMetrics,
)
from spacefight.eval.orders import (
    FOLLOWED,
    HIDDEN,
    Arrivals,
    AttackSummary,
    DefendSummary,
    FollowSummary,
    GotoSummary,
    OrdersEvalConfig,
    OrdersResult,
    Timing,
)

REPO = Path(__file__).resolve().parent.parent
FLEET_EVAL = REPO / "lab/runs/2026-10-30-fleet-pilot/eval"


def _follow(
    share: float = 0.5,
    close: float | None = 100.0,
    hull_lost: float | None = 0.10,
    threat: float = 0.6,
    in_time: float = 0.8,
    minutes: float = 400.0,
    n: int = 100,
) -> FollowSummary:
    arrivals = Arrivals(n=n, in_time=in_time, excluded=5)
    return FollowSummary(
        attack=AttackSummary(n, 10, 10_000, Timing(80, close, 0.9), 0.6, share, 10.0),
        defend=DefendSummary(n, 10, 10_000, minutes, hull_lost, threat, 30.0, 60.0),
        goto=GotoSummary(n, 10, 10_000, 80, 0.5, arrivals, arrivals, arrivals),
        ship_minutes=1000.0,
        engine_duty={"fighter": {"none": 0.2, "goto": 0.6}},
        duty_ticks={"fighter": {"none": 100, "goto": 100}},
    )


def _orders(
    followed: FollowSummary, hidden: FollowSummary | None = None
) -> OrdersResult:
    passes = {FOLLOWED: followed}
    if hidden is not None:
        passes[HIDDEN] = hidden
    return OrdersResult(
        a="x",
        b="script",
        config=OrdersEvalConfig(),
        scenarios={},
        by_commander={RANDOM: passes, SCRIPTED: {FOLLOWED: followed}},
    )


def _side() -> SideMetrics:
    fleet = FleetResult.from_json(
        (FLEET_EVAL / "warm_400_fleet_vs_script.json").read_text()
    )
    return SideMetrics(0.5, fleet.side_a.all_ships, {}, 0, 0)


def _missions(win: dict[str, float], time_limit: float = 0.0) -> MissionResult:
    side = _side()
    template = MissionSummary(
        mission="",
        n=516,
        time_limit_s=150.0,
        win_rate=0.5,
        win_rate_team0=0.5,
        win_rate_team1=0.5,
        win_rate_by_roster={},
        draw_rate=0.0,
        time_limit_rate=time_limit,
        stalemate_rate=0.0,
        end_reasons={},
        length_median_s=100.0,
        length_p90_s=140.0,
        side_a=side,
        side_b=side,
    )
    missions = {
        name: dataclasses.replace(template, mission=name, win_rate=w)
        for name, w in win.items()
    }
    cfg = MissionEvalConfig()
    return MissionResult("x", "v1", cfg, missions, float(np.mean(list(win.values()))))


def _fleet(name: str) -> FleetResult:
    return FleetResult.from_json((FLEET_EVAL / name).read_text())


@pytest.fixture(scope="module")
def baselines() -> G.Baselines:
    # A teacher that meets every plan bound against w1_400 hidden.
    teacher = _orders(_follow(share=0.60, close=90.0, hull_lost=0.05, threat=0.80))
    w1 = _orders(_follow(), _follow(share=0.45, hull_lost=0.12, threat=0.60))
    return G.Baselines(
        o_bounds=G.teacher_bounds(teacher, w1),
        v1_missions=_missions({CARRIER_BATTLE: 0.5, CONVOY_ESCORT: 0.5}, 0.02),
        v1_fleet_vs_script=_fleet("warm_400_fleet_vs_script.json"),
    )


def _evals(orders: OrdersResult, vs_v1: MissionResult, vs_w1: float) -> G.Evals:
    return G.Evals(
        orders=orders,
        missions_vs_v1=vs_v1,
        missions_vs_w1=_missions({CARRIER_BATTLE: vs_w1, CONVOY_ESCORT: vs_w1}),
        fleet_vs_script=_fleet("warm_400_fleet_vs_script.json"),
        fleet_vs_v1=_fleet("warm_600_fleet_vs_ref.json"),
    )


def test_teacher_that_meets_every_bound_keeps_the_plans_bounds(
    baselines: G.Baselines,
) -> None:
    bounds = baselines.o_bounds.bounds
    assert not any(b.replaced for b in bounds.values())
    assert bounds[G.ATTACK_SHARE].relative == "plus"
    assert bounds[G.ATTACK_SHARE].need(0.40) == pytest.approx(0.45)
    assert bounds[G.DEFEND_HULL].need(0.20) == pytest.approx(0.16)
    assert bounds[G.GOTO_IN_TIME].need(None) == pytest.approx(0.7)
    assert bounds[G.ATTACK_CLOSE].need(None) == pytest.approx(150.0)


def test_bounds_the_teacher_cannot_meet_are_set_from_the_teacher() -> None:
    # Against w1_400 hidden: share 0.47 < 0.45 + 0.05 fails; hull lost 0.11 > 0.8 x
    # 0.12 fails; threat 0.62 < 0.60 + 0.05 fails; go-to 0.6 < 0.7 fails; close 160
    # > 150 fails.
    teacher = _orders(
        _follow(share=0.47, close=160.0, hull_lost=0.11, threat=0.62, in_time=0.6)
    )
    w1 = _orders(_follow(), _follow(share=0.45, hull_lost=0.12, threat=0.60))
    bounds = G.teacher_bounds(teacher, w1)
    b = bounds.bounds
    assert all(x.replaced and x.relative == "none" for x in b.values())
    assert b[G.ATTACK_SHARE].need(0.9) == pytest.approx(0.42)
    assert b[G.DEFEND_HULL].need(None) == pytest.approx(0.11 * 1.05)
    assert b[G.DEFEND_THREAT].need(None) == pytest.approx(0.57)
    assert b[G.GOTO_IN_TIME].need(None) == pytest.approx(0.55)
    assert b[G.ATTACK_CLOSE].need(None) == pytest.approx(168.0)
    assert G.OBounds.from_json(bounds.to_json()) == bounds
    assert "replaced" in bounds.markdown()


def test_a_following_candidate_passes_and_the_strongest_is_picked(
    baselines: G.Baselines,
) -> None:
    orders = _orders(
        _follow(share=0.55, hull_lost=0.08, threat=0.70),
        _follow(share=0.45, hull_lost=0.12, threat=0.60),
    )
    good = G.check(
        "good",
        _evals(orders, _missions({CARRIER_BATTLE: 0.6, CONVOY_ESCORT: 0.55}), 0.5),
        baselines,
    )
    assert G.failures(good) == []
    weaker = G.check(
        "weaker",
        _evals(orders, _missions({CARRIER_BATTLE: 0.53, CONVOY_ESCORT: 0.53}), 0.5),
        baselines,
    )
    assert G.pick([weaker, good]) == "good"
    assert "good" in G.markdown([good, weaker])


def test_gates_fail_against_the_candidates_own_hidden_pass(
    baselines: G.Baselines,
) -> None:
    orders = _orders(
        # share gain 0.03 < 0.05; hull lost 0.11 > 0.8 x 0.12; few ward-minutes
        _follow(share=0.48, hull_lost=0.11, threat=0.70, minutes=250.0),
        _follow(share=0.45, hull_lost=0.12, threat=0.60),
    )
    report = G.check(
        "bad",
        _evals(orders, _missions({CARRIER_BATTLE: 0.6, CONVOY_ESCORT: 0.5}), 0.40),
        baselines,
    )
    failed = {c.name for c in report.checks if not c.passed}
    assert failed == {
        G.ATTACK_SHARE,
        G.DEFEND_HULL,
        "defended ward-minutes",
        "mean mission win vs w1_400",
    }
    assert G.pick([report]) is None


def test_an_unjudgeable_defend_fails_and_a_missing_hidden_pass_is_an_error(
    baselines: G.Baselines,
) -> None:
    no_hidden_hull = _orders(_follow(), _follow(hull_lost=None))
    report = G.check(
        "x",
        _evals(no_hidden_hull, _missions({CARRIER_BATTLE: 0.6, CONVOY_ESCORT: 0.6}), 1),
        baselines,
    )
    assert G.DEFEND_HULL in {c.name for c in report.checks if not c.passed}
    with pytest.raises(ValueError, match="hidden"):
        G.check(
            "y",
            _evals(_orders(_follow()), _missions({CARRIER_BATTLE: 0.6}), 1),
            baselines,
        )
