"""The SIM_VERSION 6 order eval (``spacefight.eval.orders``, ``rlf.eval.orders/2``):
instance bookkeeping on synthetic traces, the summaries and the JSON, and (on a v6
sim) the paired followed / hidden passes."""

from __future__ import annotations

import numpy as np
import pytest

from spacefight.env import rust_env
from spacefight.env.rosters import CARRIER_BATTLE, CONVOY_ESCORT, RANDOM, SCRIPTED
from spacefight.eval.controllers import Scripted
from spacefight.eval.orders import (
    ATTACK,
    CENSORED,
    COMPLETED,
    DEFEND,
    ENDED,
    FOLLOWED,
    GOTO,
    GOTO_EXTRA_TICKS,
    GOTO_SLACK,
    HIDDEN,
    NONE,
    TICK_HZ,
    OrdersEvalConfig,
    OrdersResult,
    OrderTracker,
    Tally,
    Tracks,
    evaluate,
    summarise,
)

needs_v6 = pytest.mark.skipif(
    rust_env.SIM_VERSION < 6, reason="needs the SIM_VERSION 6 sim (order tracks)"
)
S = 4  # slots: 0 and 1 measured, 2 an ally (ward), 3 an enemy


def _tracks(
    effective: list[int],
    target: list[int] | None = None,
    standing: list[int] | None = None,
    point: list[tuple[float, float]] | None = None,
    radius: list[float] | None = None,
    arrived: list[bool] | None = None,
    start: list[int] | None = None,
) -> Tracks:
    def arr(values: list | None, default: object, dtype: type) -> np.ndarray:  # type: ignore[type-arg]
        return np.asarray([values if values is not None else [default] * S], dtype)

    return Tracks(
        standing=arr(standing if standing is not None else effective, 0, np.int64),
        effective=arr(effective, 0, np.int64),
        target=arr(target, -1, np.int64),
        point=np.asarray([point or [(0.0, 0.0)] * S], dtype=np.float64),
        radius=arr(radius, 0.0, np.float64),
        arrived=arr(arrived, False, bool),
        instance_start=arr(start, 0, np.int64),
    )


def _tracker() -> OrderTracker:
    measured = np.array([[True, True, False, False]])
    return OrderTracker(measured, np.array([[1, 1, 1, 2]]))


def _observe(
    tracker: OrderTracker,
    tracks: Tracks,
    pos: list[tuple[float, float]],
    live: list[bool] | None = None,
    gun: float = 220.0,
    cap: float = 60.0,
) -> None:
    tracker.observe(
        np.asarray([live or [True] * S]),
        tracks,
        np.asarray([pos], dtype=np.float64),
        np.array([True]),
        np.full((1, S), gun),
        np.full((1, S), cap),
        np.full((1, S), 0.5),
    )


def _hit(tracker: OrderTracker, shooter: int, target: int, amount: float) -> None:
    threat = np.zeros((1, S, S), dtype=bool)
    threat[0, 2, 3] = True  # the enemy threatens ward 2
    tracker.add_hits(
        np.array([0]),
        np.array([shooter]),
        np.array([target]),
        np.array([amount]),
        threat,
    )


def _arrays(tracker: OrderTracker) -> dict[str, np.ndarray]:
    return tracker.tally.instances.arrays()


# ------------------------------------------------------------------ attack


def test_attack_measures_ticks_to_gun_range_and_damage_share() -> None:
    tracker = _tracker()
    far = [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (300.0, 0.0)]
    attack = _tracks(
        [ATTACK, NONE, NONE, NONE], target=[3, -1, -1, -1], point=[(300.0, 0.0)] * S
    )
    for tick in range(10):
        x = 30.0 * tick  # closes 30 m a tick: inside 220 m from tick 3 on
        _observe(tracker, attack, [(x, 0.0), *far[1:]])
        _hit(tracker, 0, 3, 10.0)
        _hit(tracker, 0, 2, 5.0)  # friendly fire counts against the share
    dead = _tracks([NONE] * S, target=[3, -1, -1, -1], standing=[ATTACK, 0, 0, 0])
    _observe(tracker, dead, far)
    arr = _arrays(tracker)
    assert arr["outcome"].tolist() == [ENDED]
    assert arr["close_tick"].tolist() == [3]
    s = summarise(tracker.tally).attack
    assert s.instances == 1 and s.censored == 0
    assert s.close.median == 3 and s.close.reached == 1.0
    assert s.damage_share == pytest.approx(10.0 / 15.0)
    assert s.in_range_at_start == 0.0


def test_attack_censored_before_closing_is_excluded_but_a_dead_target_is_never() -> (
    None
):
    tracker = _tracker()
    pos = [(0.0, 0.0), (0.0, 1.0), (0.0, 0.0), (300.0, 0.0)]
    attack = _tracks(
        [ATTACK, ATTACK, NONE, NONE], target=[3, 3, -1, -1], point=[(300.0, 0.0)] * S
    )
    for _ in range(4):
        _observe(tracker, attack, pos)
    # Ship 0 gets a new order (censored); ship 1's target dies (never closed).
    new = _tracks(
        [ATTACK, NONE, NONE, NONE],
        target=[3, 3, -1, -1],
        standing=[ATTACK, ATTACK, 0, 0],
        point=[(300.0, 0.0)] * S,
        start=[120, 0, 0, 0],
    )
    _observe(tracker, new, pos)
    tracker.finish()
    arr = _arrays(tracker)
    assert arr["outcome"].tolist() == [CENSORED, ENDED, CENSORED]
    s = summarise(tracker.tally).attack
    assert s.instances == 3 and s.censored == 2
    assert s.close.n == 1 and s.close.median is None and s.close.reached == 0.0


def test_death_and_match_end_censor_open_instances() -> None:
    tracker = _tracker()
    attack = _tracks([ATTACK, ATTACK, NONE, NONE], target=[3, 3, -1, -1])
    pos = [(0.0, 0.0)] * S
    _observe(tracker, attack, pos)
    _observe(tracker, attack, pos, live=[False, True, True, True])
    assert _arrays(tracker)["outcome"].tolist() == [CENSORED]
    tracker.end_matches(np.array([True]))
    assert _arrays(tracker)["outcome"].tolist() == [CENSORED, CENSORED]
    assert not tracker.open.any()


# ------------------------------------------------------------------ defend


def test_defend_pools_ward_hull_lost_threat_share_and_distance() -> None:
    tracker = _tracker()
    defend = _tracks(
        [DEFEND, NONE, NONE, NONE], target=[2, -1, -1, -1], point=[(40.0, 0.0)] * S
    )
    pos = [(0.0, 0.0), (0.0, 0.0), (40.0, 0.0), (200.0, 0.0)]
    running = np.array([True])
    loss = np.zeros((1, S), dtype=np.float32)
    loss[0, 2] = 0.01  # the ward loses 1 % a tick
    loss[0, 1] = 0.5  # an undefended ship's loss is not counted
    for _ in range(TICK_HZ * 60):  # one minute
        _observe(tracker, defend, pos)
        tracker.add_ward_loss(loss, running)
    _hit(tracker, 0, 3, 30.0)  # on the threat set
    _hit(tracker, 1, 3, 99.0)  # ship 1 has no order: not a defender's damage
    _observe(
        tracker,
        _tracks([NONE] * S, target=[2, -1, -1, -1], standing=[DEFEND, 0, 0, 0]),
        pos,
    )
    tracker.add_ward_loss(loss, running)  # no defender any more
    d = summarise(tracker.tally).defend
    assert d.instances == 1 and d.censored == 0
    assert d.ward_minutes == pytest.approx(1.0)
    assert d.hull_lost_per_ward_minute == pytest.approx(0.01 * TICK_HZ * 60)
    assert d.threat_share == pytest.approx(1.0)
    assert d.mean_distance_m == pytest.approx(40.0)


def test_two_defenders_of_one_ward_count_its_minutes_once() -> None:
    tracker = _tracker()
    defend = _tracks([DEFEND, DEFEND, NONE, NONE], target=[2, 2, -1, -1])
    loss = np.zeros((1, S), dtype=np.float32)
    loss[0, 2] = 0.1
    for _ in range(10):
        _observe(tracker, defend, [(0.0, 0.0)] * S)
        tracker.add_ward_loss(loss, np.array([True]))
    assert tracker.tally.ward_ticks == 10
    assert tracker.tally.ward_hull_lost == pytest.approx(1.0)
    tracker.add_ward_loss(loss, np.array([False]))  # a finished match adds nothing
    assert tracker.tally.ward_ticks == 10


# ------------------------------------------------------------------ go-to


def _goto_run(dist: float, arrive_after: int | None, cut_after: int | None) -> Tally:
    """One go-to of ``dist`` metres for ship 0 (speed cap 60 m/s, radius 25 m) that
    arrives after ``arrive_after`` ticks or is cut short after ``cut_after``."""
    tracker = _tracker()
    point = [(dist + 25.0, 0.0)] * S
    goto = _tracks([GOTO, NONE, NONE, NONE], point=point, radius=[25.0] * S)
    pos = [(0.0, 0.0)] * S
    steps = arrive_after if arrive_after is not None else cut_after
    assert steps is not None
    for _ in range(steps):
        _observe(tracker, goto, pos)
    if arrive_after is not None:
        done = _tracks(
            [NONE] * S,
            standing=[GOTO, 0, 0, 0],
            point=point,
            radius=[25.0] * S,
            arrived=[True, False, False, False],
        )
        _observe(tracker, done, pos)
    else:
        tracker.end_matches(np.array([True]))
    return tracker.tally


def test_goto_deadline_scores_arrivals_and_judges_censored_ones_only_when_late() -> (
    None
):
    dist = 120.0  # 60 ticks at 60 m/s -> deadline 1.5 * (60 + 60) = 180 ticks
    deadline = GOTO_SLACK * (dist / 60.0 * TICK_HZ + GOTO_EXTRA_TICKS)
    assert deadline == pytest.approx(180.0)
    pooled = Tally()
    for arrive, cut in ((100, None), (200, None), (None, 90), (None, 300)):
        pooled.merge(_goto_run(dist, arrive, cut))
    arr = pooled.instances.arrays()
    assert arr["outcome"].tolist() == [COMPLETED, COMPLETED, CENSORED, CENSORED]
    g = summarise(pooled).goto
    # In time; late; cut at 90 (unknown: excluded); cut at 300 (late: a failure).
    assert g.all.n == 3 and g.all.excluded == 1
    assert g.all.in_time == pytest.approx(1 / 3)
    assert g.arrivals == 2 and g.instances == 4 and g.censored == 2
    assert g.near.n == 3 and g.far.n == 0


def test_far_goto_points_are_reported_apart() -> None:
    pooled = Tally()
    pooled.merge(_goto_run(120.0, 100, None))
    pooled.merge(_goto_run(300.0, 150, None))
    g = summarise(pooled).goto
    assert (g.near.n, g.far.n) == (1, 1)
    assert g.near.in_time == 1.0 and g.far.in_time == 1.0


def test_a_new_instance_start_censors_and_reopens() -> None:
    tracker = _tracker()
    a = _tracks([GOTO, NONE, NONE, NONE], point=[(500.0, 0.0)] * S, start=[60, 0, 0, 0])
    b = _tracks(
        [GOTO, NONE, NONE, NONE], point=[(-500.0, 0.0)] * S, start=[120, 0, 0, 0]
    )
    pos = [(0.0, 0.0)] * S
    _observe(tracker, a, pos)
    _observe(tracker, a, pos)
    _observe(tracker, b, pos)
    assert _arrays(tracker)["outcome"].tolist() == [CENSORED]
    assert tracker.open[0, 0] and tracker.instance_start[0, 0] == 120


def test_positions_are_needed_at_openings_and_periodically_while_chasing() -> None:
    tracker = _tracker()
    live = np.ones((1, S), dtype=bool)
    attack = _tracks(
        [ATTACK, NONE, NONE, NONE], target=[3, -1, -1, -1], point=[(900.0, 0.0)] * S
    )
    assert tracker.position_envs(live, attack, periodic=False).tolist() == [True]
    _observe(tracker, attack, [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (900.0, 0.0)])
    assert tracker.position_envs(live, attack, periodic=False).tolist() == [False]
    assert tracker.position_envs(live, attack, periodic=True).tolist() == [True]


# ------------------------------------------------------------------ results


def test_engine_duty_is_binned_by_effective_kind() -> None:
    tracker = _tracker()
    tracker.tally.hull_names = {1: "fighter", 2: "strafer"}
    _observe(
        tracker,
        _tracks([ATTACK, NONE, NONE, NONE], target=[3, -1, -1, -1]),
        [(0.0, 0.0)] * S,
    )
    f = summarise(tracker.tally)
    assert f.engine_duty == {"fighter": {"none": 0.5, "attack": 0.5}}
    assert f.duty_ticks == {"fighter": {"none": 1, "attack": 1}}


def test_orders_result_round_trips_through_json() -> None:
    pooled = Tally()
    pooled.merge(_goto_run(120.0, 100, None))
    follow = summarise(pooled)
    cfg = OrdersEvalConfig(n_per_scenario=12)
    result = OrdersResult(
        "a",
        "script",
        cfg,
        {f"{CARRIER_BATTLE}/{RANDOM}/{FOLLOWED}": follow},
        {RANDOM: {FOLLOWED: follow, HIDDEN: follow}},
    )
    assert OrdersResult.from_json(result.to_json()) == result
    assert "go-to" in result.markdown()


def test_the_hidden_pass_runs_only_under_the_named_commanders() -> None:
    cfg = OrdersEvalConfig(n_scripted=48)
    assert cfg.passes_for(RANDOM) == (FOLLOWED, HIDDEN)
    assert cfg.passes_for(SCRIPTED) == (FOLLOWED,)
    assert cfg.n_for(SCRIPTED) == 48 and cfg.n_for(RANDOM) == cfg.n_per_scenario


# ------------------------------------------------------------------ the sim


@needs_v6
def test_hidden_pass_replays_the_same_matches_for_a_script() -> None:
    """A script flies orders it cannot see, so its hidden pass is the same matches
    tick for tick: the pairing of the passes is exact."""
    cfg = OrdersEvalConfig(
        missions=(CONVOY_ESCORT,), commanders=(RANDOM,), n_per_scenario=6, seed=3
    )
    result = evaluate(Scripted(), Scripted(), cfg, n_threads=2)
    passes = result.by_commander[RANDOM]
    assert passes[FOLLOWED] == passes[HIDDEN]
    f = passes[FOLLOWED]
    assert f.attack.instances + f.defend.instances + f.goto.instances > 0
    assert OrdersResult.from_json(result.to_json()) == result
