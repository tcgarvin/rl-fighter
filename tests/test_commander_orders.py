"""The commander eval's order clock (spacefight/commander/eval.py) on a scripted env."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from spacefight.commander.eval import OrderClock, OrderStats

STRIKE = np.array([[True, True, False]])
TEAM = np.array([[0, 1, 0]], dtype=np.int8)
# Team 0 is commander 1 and team 1 commander 0.
SIDE = np.array([[1, 0]], dtype=np.int64)


def env_at(kind, start, alive=(True, True, True), flying=(True, True, True)):
    """One env of three slots (two strike craft and a capital ship) at one tick."""
    tracks = {
        "standing_kind": np.array([kind], dtype=np.int8),
        "instance_start": np.array([start], dtype=np.uint32),
    }
    return SimpleNamespace(
        order_tracks=lambda: tracks,
        raw=SimpleNamespace(alive=np.array([alive])),
        act_mask=np.array([flying]),
    )


def play(frames) -> list[OrderStats]:
    clock = OrderClock(STRIKE, TEAM, SIDE, 2)
    running = np.array([True])
    for frame in frames:
        clock.observe(frame, running)
    return clock.stats


def test_an_order_is_timed_from_its_start_to_the_next_change() -> None:
    frames = (
        [env_at((0, 0, 0), (0, 0, 0))]
        + [env_at((1, 0, 0), (30, 0, 0))] * 150
        + [env_at((3, 0, 0), (180, 0, 0))] * 60
        + [env_at((0, 0, 0), (240, 0, 0))]
    )
    by_commander = play(frames)
    stats = by_commander[1]
    assert stats.given == 2
    assert stats.lengths == [5.0, 2.0]
    summary = stats.summary()
    assert summary["order_seconds_median"] == 3.5
    assert summary["orders_under_5s"] == 0.5
    # Slot 0 flew 211 ticks after the first look, 210 of them under an order.
    assert stats.flying_s == pytest.approx(211 / 30)
    assert summary["ordered_share"] == pytest.approx(210 / 211)
    assert summary["orders_per_ship_min"] == pytest.approx(60 * 2 / (211 / 30))
    # The other side's ship was never ordered, and the capital ship is not counted.
    assert by_commander[0].given == 0
    assert by_commander[0].summary()["order_seconds_median"] is None
    assert by_commander[0].flying_s == pytest.approx(211 / 30)


def test_a_dead_ship_or_a_finished_match_gives_no_order() -> None:
    clock = OrderClock(STRIKE, TEAM, SIDE, 2)
    clock.observe(env_at((1, 0, 0), (10, 0, 0)), np.array([True]))
    # The ship dies on the tick its order would have changed: nothing is counted.
    clock.observe(
        env_at((2, 0, 0), (40, 0, 0), alive=(False, True, True)), np.array([True])
    )
    # The match is over and the env already holds the next one.
    clock.observe(env_at((3, 3, 0), (0, 0, 0)), np.array([False]))
    assert [s.given for s in clock.stats] == [0, 0]
    assert [s.lengths for s in clock.stats] == [[], []]


def test_a_docked_ship_adds_no_flying_time() -> None:
    frames = [env_at((0, 0, 0), (0, 0, 0), flying=(False, True, True))] * 31
    assert play(frames)[1].flying_s == 0.0
