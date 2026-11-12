"""The go-to deadline sweep (``spacefight.eval.goto_sweep``): its layouts, the levels'
deadlines and clocks, the measures, a tiny sweep flown by the script, and the controllers
that fly a pilot blind to the deadline.

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

rlf_sim = pytest.importorskip(
    "rlf_sim",
    reason=(
        "rlf_sim extension not built; run "
        "`uv run maturin develop -m crates/sim-py/Cargo.toml --release`"
    ),
)

from spacefight.env import rust_env  # noqa: E402
from spacefight.env.drills import (  # noqa: E402
    GOTO_TURN_S,
    NO_SLACK,
    ORDER_TICK,
    START_LIMIT,
    TICK_HZ,
    DrillGenerator,
    goto_deadline_tick,
    goto_order_deadline_tick,
)
from spacefight.env.rosters import (  # noqa: E402
    DRILL_ATTACK,
    EXTERNAL,
    NO_DEADLINE,
)
from spacefight.env.rust_env import OBS_LAYOUT, RustVecEnv  # noqa: E402
from spacefight.eval.controllers import (  # noqa: E402
    HIDE_DEADLINE,
    HIDE_ORDER_TIME,
    Policy,
    Scripted,
    make_controller,
)
from spacefight.eval.goto_sweep import (  # noqa: E402
    CLOCK_EXTRA_TICKS,
    NO_DEADLINE_LEVEL,
    ONE,
    OPPOSITIONS,
    PARKED,
    SCHEMA,
    THREE,
    Flight,
    SweepConfig,
    build_layouts,
    evaluate,
    headlines,
    level_name,
    main,
    measure,
    run_level,
)
from spacefight.rl.spike_policy import (  # noqa: E402
    SpikeActor,
    SpikeCritic,
    save_policy,
)

ASSETS = Path(__file__).resolve().parents[1] / "assets"
GEN = DrillGenerator(ASSETS)
TINY = SweepConfig(
    seeds_per_cell=2,
    hulls=("fighter", "gunship"),
    distances_m=(150.0, 300.0),
    radii_m=(60.0,),
    oppositions=(PARKED, ONE),
    slacks=(1.0, 1.5, 3.0, 8.0),
)
needs_v8 = pytest.mark.skipif(
    rust_env.SIM_VERSION < 8, reason="needs the SIM_VERSION 8 sim (go-to deadlines)"
)


# ------------------------------------------------------------------ the sweep's shape


def test_the_default_sweep_is_the_owner_s_grid() -> None:
    cfg = SweepConfig()
    assert cfg.hulls == ("fighter", "strafer", "gunship")
    assert cfg.distances_m == (150.0, 300.0, 500.0) and cfg.radii_m == (20.0, 60.0)
    assert cfg.oppositions == (PARKED, ONE, THREE) and cfg.seeds_per_cell == 6
    assert cfg.slacks == (0.8, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0)
    assert cfg.levels[-1] == NO_SLACK and len(cfg.levels) == 8
    assert [level_name(s) for s in (0.8, 1.0, 1.5, NO_SLACK)] == [
        "0.8",
        "1",
        "1.5",
        NO_DEADLINE_LEVEL,
    ]
    assert CLOCK_EXTRA_TICKS == 20 * TICK_HZ


@pytest.mark.parametrize(
    "bad",
    [
        {"seeds_per_cell": 0},
        {"hulls": ("freighter",)},
        {"hulls": ()},
        {"oppositions": ("swarm",)},
        {"distances_m": (0.0,)},
        {"slacks": (1.5, 3.0)},
        {"slacks": (-1.0, 1.5, 8.0)},
    ],
)
def test_a_sweep_that_cannot_be_flown_or_summarised_is_refused(
    bad: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        SweepConfig(**bad)  # type: ignore[arg-type]


def test_layouts_cover_the_grid_with_one_ship_at_the_cell_s_distance() -> None:
    layouts = build_layouts(TINY, ASSETS)
    assert len(layouts) == 2 * 2 * 1 * 2 * 2
    assert layouts == build_layouts(TINY, ASSETS), "a pure function of the config"
    cells = {(lay.hull, lay.distance_m, lay.opposition) for lay in layouts}
    assert len(cells) == 8
    for lay in layouts:
        spec = lay.spec
        assert spec.teams == ((lay.hull,), OPPOSITIONS[lay.opposition])
        assert spec.pilots == (0,) and spec.radius == lay.radius_m
        start = spec.layout[0]
        gap = math.hypot(start.x - spec.point[0], start.y - spec.point[1])
        assert gap - spec.radius == pytest.approx(lay.distance_m, abs=1e-6)
        assert spec.distances == (lay.distance_m,)
        assert math.hypot(start.vx, start.vy) <= 0.5 * GEN.speed_caps[lay.hull] + 1e-9
        assert spec.deadline_tick == NO_DEADLINE, "no deadline until with_slack"


def test_the_oppositions_of_a_cell_start_the_pilot_in_the_same_place() -> None:
    layouts = build_layouts(SweepConfig(seeds_per_cell=1), ASSETS)
    by_cell: dict[tuple[str, float, float], list[object]] = {}
    for lay in layouts:
        key = (lay.hull, lay.distance_m, lay.radius_m)
        by_cell.setdefault(key, []).append((lay.spec.layout[0], lay.spec.point))
    assert len(by_cell) == 18
    for starts in by_cell.values():
        assert len(starts) == 3 and starts[0] == starts[1] == starts[2]
    assert len({str(v[0]) for v in by_cell.values()}) == 18, "cells differ"


def test_a_parked_enemy_sits_at_rest_on_the_rim_far_from_the_route() -> None:
    for lay in build_layouts(SweepConfig(seeds_per_cell=1), ASSETS):
        spec = lay.spec
        enemies = spec.layout[1:]
        start = spec.layout[0]
        if lay.opposition != PARKED:
            assert len(enemies) == len(OPPOSITIONS[lay.opposition])
            assert spec.enemies_around
            continue
        (parked,) = enemies
        assert (parked.vx, parked.vy) == (0.0, 0.0)
        assert math.hypot(parked.x, parked.y) == pytest.approx(START_LIMIT)
        # Out of anyone's gun range (220 m) of both the start and the point.
        assert math.hypot(parked.x - start.x, parked.y - start.y) > 300.0
        assert math.hypot(parked.x - spec.point[0], parked.y - spec.point[1]) > 300.0


def test_single_goto_checks_its_arguments() -> None:
    with pytest.raises(ValueError):
        GEN.single_goto(1, "fighter", 0.0, 20.0, ("fighter",))
    with pytest.raises(ValueError):
        GEN.single_goto(1, "fighter", 150.0, 20.0, ())
    with pytest.raises(ValueError):
        GEN.single_goto(1, "fighter", 150.0, 20.0, ("fighter", "fighter"), parked=True)
    with pytest.raises(KeyError):
        GEN.single_goto(1, "interceptor", 150.0, 20.0, ("fighter",))


def test_with_slack_sets_the_order_s_deadline_and_the_clock() -> None:
    spec = GEN.single_goto(3, "gunship", 300.0, 20.0, ("fighter",), parked=True)
    cap = GEN.speed_caps["gunship"]
    timed = GEN.with_slack(spec, 2.0, 600)
    assert timed.deadline_tick == goto_order_deadline_tick(2.0, [300.0], [cap])
    assert timed.deadline_tick == ORDER_TICK + math.ceil(
        (2.0 * 300.0 / cap + GOTO_TURN_S) * TICK_HZ
    )
    assert timed.deadlines == (timed.deadline_tick,) and timed.slack == 2.0
    assert timed.clock_ticks == timed.deadline_tick + 600
    assert timed.order().deadline_tick == timed.deadline_tick
    assert timed.layout == spec.layout and timed.point == spec.point
    untimed = GEN.with_slack(spec, NO_SLACK, 600)
    assert untimed.deadline_tick == NO_DEADLINE and untimed.slack == NO_SLACK
    assert untimed.deadlines == (goto_deadline_tick(300.0, cap),)
    assert untimed.clock_ticks == untimed.deadlines[0] + 600
    with pytest.raises(ValueError):
        GEN.with_slack(spec, -1.0, 600)
    with pytest.raises(ValueError):
        GEN.with_slack(GEN.generate(DRILL_ATTACK, 1), 2.0, 600)


# ------------------------------------------------------------------ the measures


def _flight(**fields: object) -> Flight:
    layout = build_layouts(TINY, ASSETS)[1]  # fighter, 150 m, one enemy
    base: dict[str, object] = {"layout": layout, "slack": 2.0, "deadline": 360}
    base.update(fields)
    return Flight(**base)  # type: ignore[arg-type]


def test_a_flight_is_in_time_late_or_died_and_knows_its_times() -> None:
    in_time = _flight(arrived_tick=240, inside_tick=243, half_tick=150)
    assert in_time.outcome() == "arrived"
    assert in_time.allowance_s == pytest.approx(10.0)
    assert in_time.arrival_s == pytest.approx(6.0), "the sim's tick, not the read's"
    assert in_time.leave_s == pytest.approx(3.0)
    late = _flight(inside_tick=420, gone_tick=960)
    assert late.outcome() == "late" and late.arrival_s == pytest.approx(12.0)
    never = _flight(gone_tick=960)
    assert never.outcome() == "late"
    assert math.isinf(never.arrival_s) and math.isinf(never.leave_s)
    assert _flight(gone_tick=200).outcome() == "died"
    assert _flight(gone_tick=400).outcome() == "late", "killed after the deadline"


def test_measures_count_deaths_apart_and_a_median_most_never_reached_is_null() -> None:
    flights = [
        _flight(arrived_tick=240, half_tick=150, dealt=10.0, taken=4.0),
        _flight(inside_tick=420, half_tick=180, gone_tick=960, dealt=30.0),
        _flight(gone_tick=960),
        _flight(gone_tick=200, dealt=5.0, taken=70.0),
    ]
    out = measure(flights)
    assert (out["n"], out["died"]) == (4, 1)
    assert out["in_time"]["successes"] == 1 and out["in_time"]["n"] == 3
    assert out["reached"]["successes"] == 2 and out["reached"]["n"] == 3
    # Of the three not killed: 6 s, 12 s and never. The median is 12 s.
    assert out["arrival_s"] == pytest.approx(12.0)
    assert out["arrival_share"] == pytest.approx(1.2)
    # Of all four: left at 3 s, 4 s, never, never: no median.
    assert out["leave_s"] is None
    assert out["damage_dealt"]["mean"] == pytest.approx(45.0 / 4)
    assert out["damage_taken"]["mean"] == pytest.approx(74.0 / 4)
    assert measure([])["arrival_s"] is None


def test_the_headlines_read_both_levels_through_the_tight_level_s_allowance() -> None:
    # Slack 1.5 allows 10 s here (deadline 360); slack 8 allows 58 s.
    tight = [
        _flight(slack=1.5, arrived_tick=240, dealt=0.0),  # 6 s
        _flight(slack=1.5, arrived_tick=300, dealt=0.0),  # 8 s
        _flight(slack=1.5, inside_tick=420, gone_tick=960, dealt=10.0),  # late, 12 s
        _flight(slack=1.5, gone_tick=960, dealt=10.0),  # never
    ]
    loose = [
        _flight(slack=8.0, deadline=1800, arrived_tick=330, dealt=20.0),  # 9 s
        _flight(slack=8.0, deadline=1800, arrived_tick=900, dealt=40.0),  # 28 s
        _flight(slack=8.0, deadline=1800, arrived_tick=270, dealt=10.0),  # 7 s
        _flight(slack=8.0, deadline=1800, arrived_tick=900, dealt=10.0),  # 28 s
    ]
    out = headlines({1.0: [_flight(slack=1.0, gone_tick=960)], 1.5: tight, 8.0: loose})
    # Slack 1 is not "feasible": six of the eight flights at 1.5 and over were in time.
    assert out["in_time_feasible"]["successes"] == 6
    assert out["in_time_feasible"]["n"] == 8
    # Inside within 10 s: layouts 1 and 2 at slack 1.5, layouts 1 and 3 at slack 8.
    ratio = out["arrival_time_ratio"]
    assert ratio["early_tight"]["successes"] == 2 and ratio["early_tight"]["n"] == 4
    assert ratio["early_loose"]["successes"] == 2
    # Only the first layout made that window at both levels: 9 s over 6 s.
    assert ratio["layouts"] == 1
    assert ratio["ratio"] == pytest.approx(1.5)
    assert out["hits_bought"][ONE]["mean"] == pytest.approx(15.0)
    assert THREE not in out["hits_bought"], "no such layouts here"
    # Nothing inside the window at both: no ratio, and the shares still say why.
    none = headlines({1.5: tight[2:], 8.0: loose[2:]})["arrival_time_ratio"]
    assert none["ratio"] is None and none["layouts"] == 0
    assert none["early_tight"]["rate"] == 0.0 and none["early_loose"]["rate"] == 0.5


# ------------------------------------------------------------------ flown by the script


@needs_v8
def test_the_script_flies_straight_there_whatever_the_allowance() -> None:
    result = evaluate(Scripted(), "script", TINY, n_threads=2, assets_dir=ASSETS)
    assert result.n_layouts == 16 and result.schema == SCHEMA
    assert list(result.levels) == ["1", "1.5", "3", "8", NO_DEADLINE_LEVEL]
    parked = {
        level: summary["by_opposition"][PARKED]
        for level, summary in result.levels.items()
    }
    # Nobody to fight: with time to spare it always arrives, and deals and takes nothing.
    for level in ("3", "8", NO_DEADLINE_LEVEL):
        assert parked[level]["in_time"]["rate"] == 1.0
        assert parked[level]["died"] == 0
    assert all(part["damage_dealt"]["mean"] == 0.0 for part in parked.values())
    assert all(part["damage_taken"]["mean"] == 0.0 for part in parked.values())
    # The script does not read the deadline: it leaves and arrives at the same time.
    assert len({part["leave_s"] for part in parked.values()}) == 1
    assert parked["3"]["arrival_s"] == parked["8"]["arrival_s"]
    ratio = result.headline["arrival_time_ratio"]
    assert ratio["ratio"] == pytest.approx(1.0, abs=0.05) and ratio["layouts"] >= 8
    assert ratio["early_tight"] == ratio["early_loose"], "the same flights at both"
    assert result.headline["in_time_feasible"]["rate"] > 0.8
    assert set(result.levels["8"]["by_hull"]) == {"fighter", "gunship"}
    assert set(result.levels["8"]["by_distance"]) == {"150", "300"}
    # More time is a smaller share of it used.
    shares = [result.levels[level]["all"]["arrival_share"] for level in ("3", "8")]
    assert shares[0] > shares[1] > 0.0
    assert ONE in result.headline["hits_bought"]


@needs_v8
def test_a_layout_s_match_does_not_depend_on_the_level_it_is_flown_at() -> None:
    """The script ignores the deadline, so with the same match seed it arrives on the
    same tick at every level where it is in time."""
    layouts = [lay for lay in build_layouts(TINY, ASSETS) if lay.opposition == ONE]
    a = run_level(Scripted(), layouts, 3.0, TINY.seed, 2, ASSETS)
    b = run_level(Scripted(), layouts, 8.0, TINY.seed, 2, ASSETS)
    both = [
        (x, y)
        for x, y in zip(a, b, strict=True)
        if x.outcome() == "arrived" and y.outcome() == "arrived"
    ]
    assert len(both) >= 4
    for x, y in both:
        assert x.arrived_tick == y.arrived_tick and x.half_tick == y.half_tick
        assert x.dealt == y.dealt and x.taken == y.taken
        assert x.start_edge_m == y.start_edge_m > 0.0
        assert y.deadline > x.deadline
    with pytest.raises(ValueError):
        run_level(Scripted(), [], 3.0, 1)


@needs_v8
def test_the_cli_writes_the_json_and_a_report_with_a_row_per_level(
    tmp_path: Path,
) -> None:
    out = tmp_path / "sweep" / "script.json"
    code = main(
        ["--a", "script", "--seeds-per-cell", "1", "--threads", "2", "--out", str(out)]
    )
    assert code == 0
    data = json.loads(out.read_text())
    assert data["schema"] == SCHEMA == "rlf.eval.goto_sweep/1"
    assert data["name"] == "script" and data["n_layouts"] == 54
    assert data["config"]["seeds_per_cell"] == 1 and data["clock_extra_s"] == 20.0
    assert list(data["levels"]) == ["0.8", "1", "1.5", "2", "3", "5", "8", "none"]
    assert set(data["headline"]["hits_bought"]) == {ONE, THREE}
    report = out.with_suffix(".md").read_text()
    assert "# Go-to deadline sweep: script" in report
    assert "Arrival-time ratio, slack 8 over slack 1.5" in report
    assert "Inside the circle within the slack-1.5 allowance" in report
    for level in data["levels"]:
        assert f"\n| {level} | " in report
    assert "## Enemies: three" in report


# ------------------------------------------------------------------ blind to the deadline


def _sensitive_pilot(path: Path) -> Path:
    """A 587-input pilot whose first layer reads the ``order_time`` block loudly."""
    torch.manual_seed(4)
    actor = SpikeActor(obs_dim=rust_env.OBS_DIM)
    offset, width = OBS_LAYOUT["order_time"]
    with torch.no_grad():
        actor.net[0].weight[:, offset : offset + width].normal_(0.0, 3.0)
    critic = SpikeCritic(obs_dim=rust_env.OBS_DIM)
    save_policy(path, actor, critic, {"kind": "test", "sim_version": 8})
    return path


def _env_at_the_order(spec_slack: float) -> RustVecEnv:
    """A fighter 150 m from its circle, two ticks after the order landed. The clock is
    the same whatever the slack, so only the deadline differs between two of these."""
    spec = GEN.single_goto(9, "fighter", 150.0, 60.0, ("fighter",), parked=True)
    roster = replace(GEN.with_slack(spec, spec_slack, 600), clock_ticks=2400).roster()
    env = RustVecEnv(ASSETS, 1, roster.fleets(), 4, commanders=(EXTERNAL, EXTERNAL))
    env.set_next_roster(0, roster)
    env.reset()
    for _ in range(ORDER_TICK + 2):
        env.step(np.zeros_like(env.actions))
    return env


@needs_v8
def test_a_pilot_blind_to_the_deadline_flies_a_timed_go_to_as_an_untimed_one(
    tmp_path: Path,
) -> None:
    path = _sensitive_pilot(tmp_path / "v8.pt")
    timed, untimed = _env_at_the_order(2.0), _env_at_the_order(NO_SLACK)
    offset, width = OBS_LAYOUT["order_time"]
    block = timed.obs[0, 0, offset : offset + width]
    assert block[0] == 1.0 and block[1] > 0.0 and block[2] > 0.0, "it shows a deadline"
    # Closeness needs no deadline: the two obs differ in the deadline's floats only.
    plain = untimed.obs[0, 0, offset : offset + width]
    assert plain.tolist() == [0.0, 0.0, 0.0, block[3]]
    np.testing.assert_array_equal(timed.obs[0, 0, :offset], untimed.obs[0, 0, :offset])
    rows = np.zeros((1, timed.n_ships), dtype=np.bool_)
    rows[0, 0] = True
    seeing = Policy(path, sample=False)
    blind = make_controller(f"nodeadline:{path}", sample=False)
    blank = make_controller(f"notime:{path}", sample=False)
    assert isinstance(blind, Policy) and blind.hide_order_time == HIDE_DEADLINE
    assert isinstance(blank, Policy) and blank.hide_order_time == HIDE_ORDER_TIME
    assert blind.label.endswith(":no_deadline") and blank.label.endswith(
        ":no_order_time"
    )
    as_untimed = seeing.act(untimed, rows)
    np.testing.assert_array_equal(blind.act(timed, rows), as_untimed)
    assert not np.array_equal(seeing.act(timed, rows), as_untimed), "it does read it"
    with pytest.raises(ValueError, match="hide_order_time"):
        Policy(path, hide_order_time="everything")
    with pytest.raises(FileNotFoundError):
        make_controller("nodeadline:/no/such/pilot.pt")
