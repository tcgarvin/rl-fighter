"""Order drills (``docs/PILOT_TRAINING.md`` §2): the generator, the sim's start layouts and
drill rules through the env, what script followers do in each drill, the pay, the gate, and
drills in training.

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml  # type: ignore[import-untyped]

rlf_sim = pytest.importorskip(
    "rlf_sim",
    reason=(
        "rlf_sim extension not built; run "
        "`uv run maturin develop -m crates/sim-py/Cargo.toml --release`"
    ),
)

from spacefight.env.drills import (  # noqa: E402
    GOTO_CLOCK_EXTRA_TICKS,
    GOTO_NO_DEADLINE_P,
    GOTO_SLACK,
    GOTO_SLACK_S,
    GOTO_TIME_MULT,
    GOTO_TURN_S,
    ORDER_TICK,
    TICK_HZ,
    DrillGenerator,
    DrillLedger,
    DrillOutcome,
    goto_deadline_tick,
    goto_order_deadline_tick,
)
from spacefight.env.rosters import (  # noqa: E402
    DRILL_ATTACK,
    DRILL_DEFEND,
    DRILL_GOTO,
    DRILL_KINDS,
    EXTERNAL,
    FLEET_HULLS,
    MAX_DRILL_SHIPS,
    NO_DEADLINE,
    DrillTag,
    OpeningOrder,
    PilotsDistribution,
    PilotsRosterSampler,
    Roster,
    ShipStart,
    resolve_distribution,
)
from spacefight.env.rust_env import (  # noqa: E402
    HAS_ORDER_COL,
    RustVecEnv,
)
from spacefight.eval.controllers import Scripted  # noqa: E402
from spacefight.eval.drills import (  # noqa: E402
    AT_ENEMY,
    BAR_PATHS,
    CHOSE_NAMED,
    CHOSE_OTHER,
    DEFAULT_BARS,
    ENEMY_NEAR_M,
    EXEMPT,
    FAIL,
    FATES,
    IN_TIME,
    KILLED,
    NEAR_MISS,
    NEAR_MISS_M,
    NEITHER,
    NO_CHOICE,
    PASS,
    REPORT_ONLY,
    SCHEMA,
    DrillEvalConfig,
    DrillRecord,
    Rate,
    ShipRun,
    _GotoWatch,
    _sides_summary,
    apply_gate,
    evaluate,
    load_bars,
    main,
    parse_bars,
    run_pass,
    slack_band,
    summarise_goto,
)
from spacefight.rl.opponents import (  # noqa: E402
    OpponentAssigner,
    OpponentKind,
    OpponentSchedule,
)
from spacefight.rl.spike_ppo import PPOConfig, SpikeTrainer  # noqa: E402

ASSETS = Path(__file__).resolve().parents[1] / "assets"
GEN = DrillGenerator(ASSETS)
SIDE_KINDS = (DRILL_ATTACK, DRILL_DEFEND)


def play(roster: Roster, seed: int = 3, steps: int = 0, **kwargs: object) -> RustVecEnv:
    """An env of one match of ``roster``, stepped ``steps`` times by the scripts."""
    env = RustVecEnv(
        ASSETS,
        1,
        roster.fleets(),
        seed,
        max_ships=20,
        n_threads=1,
        commanders=(EXTERNAL, EXTERNAL),
        **kwargs,  # type: ignore[arg-type]
    )
    env.set_next_roster(0, roster)
    env.reset()
    for _ in range(steps):
        env.scripted_actions()
        env.step()
    return env


# -- the generator ------------------------------------------------------------------------


@pytest.mark.parametrize("kind", DRILL_KINDS)
def test_generator_is_a_pure_function_of_kind_and_seed(kind: str) -> None:
    for seed in range(20):
        assert GEN.generate(kind, seed) == DrillGenerator(ASSETS).generate(kind, seed)
    assert GEN.generate(kind, 1) != GEN.generate(kind, 2)


@pytest.mark.parametrize("kind", DRILL_KINDS)
def test_unknown_kinds_and_every_drawn_layout_are_checked(kind: str) -> None:
    with pytest.raises(ValueError, match="unknown drill kind"):
        GEN.generate("patrol", 1)
    env = RustVecEnv(
        ASSETS, 1, [["fighter"], ["fighter"]], 0, max_ships=20, n_threads=1
    )
    # The sim refuses a layout with overlaps, ships off the map or over their speed cap,
    # which would take down a training run at its first bad draw.
    for seed in range(1500):
        spec = GEN.generate(kind, seed)
        assert spec.roster().n_ships <= MAX_DRILL_SHIPS
        env.set_next_roster(0, spec.roster())


@pytest.mark.parametrize("kind", SIDE_KINDS)
def test_swap_partners_differ_only_in_the_named_side(kind: str) -> None:
    for seed in range(40):
        spec = GEN.generate(kind, seed)
        partner = spec.swapped()
        assert partner.named_side == 1 - spec.named_side
        assert asdict(replace(partner, named_side=spec.named_side)) == asdict(spec)
        assert partner.swapped() == spec
        a, b = spec.roster(), partner.roster()
        assert a.start_layout == b.start_layout
        assert a.teams == b.teams
        assert a.opening_orders[1:] == b.opening_orders[1:], "enemy orders are the same"
        assert a.opening_orders[0].target != b.opening_orders[0].target
        assert a.drill is not None and b.drill is not None
        assert a.drill.named_group == b.drill.other_group


@pytest.mark.parametrize("kind", SIDE_KINDS)
def test_swap_partners_play_the_same_match_until_the_order_lands(kind: str) -> None:
    spec = GEN.generate(kind, 12)
    a = play(spec.roster(), steps=ORDER_TICK - 1)
    b = play(spec.swapped().roster(), steps=ORDER_TICK - 1)
    assert a.raw.state_hash()[0] == b.raw.state_hash()[0]
    a.scripted_actions()
    a.step()
    b.scripted_actions()
    b.step()
    assert a.raw.state_hash()[0] != b.raw.state_hash()[0], "now the order differs"


def test_a_go_to_has_no_swap_partner() -> None:
    with pytest.raises(ValueError, match="no side"):
        GEN.generate(DRILL_GOTO, 1).swapped()


def test_the_named_side_is_not_fixed_in_the_world_or_in_the_pilots_frame() -> None:
    specs = [GEN.generate(DRILL_DEFEND, seed) for seed in range(300)]
    axes = np.array([s.side_axis for s in specs])
    np.testing.assert_allclose(np.linalg.norm(axes, axis=1), 1.0)
    angles = np.arctan2(axes[:, 1], axes[:, 0])
    counts, _ = np.histogram(angles, bins=8, range=(-math.pi, math.pi))
    assert counts.min() >= 15, f"side axes are not spread round the circle: {counts}"
    # In the first pilot's own frame (nose = heading): is the named ward left or right?
    left = 0
    for spec in specs:
        pilot = spec.layout[spec.pilots[0]]
        ward = spec.layout[spec.named_slot]
        nose = (math.cos(pilot.heading), math.sin(pilot.heading))
        to_ward = (ward.x - pilot.x, ward.y - pilot.y)
        left += nose[0] * to_ward[1] - nose[1] * to_ward[0] > 0.0
        # The sides are across the pilot's nose, not ahead of or behind it.
        cos_off_nose = (nose[0] * to_ward[0] + nose[1] * to_ward[1]) / math.hypot(
            *to_ward
        )
        assert abs(cos_off_nose) < 0.75
    assert 110 <= left <= 190, f"{left}/300 named wards on the pilot's left"


def test_the_side_axis_points_from_side_0_to_side_1_under_any_rotation_or_mirror() -> (
    None
):
    for seed in range(50):
        spec = GEN.generate(DRILL_DEFEND, seed)
        pilot = spec.layout[0]
        for ward_slot, sign in zip(spec.side_targets, (-1.0, 1.0)):
            ward = spec.layout[ward_slot]
            along = (ward.x - pilot.x) * spec.side_axis[0] + (
                ward.y - pilot.y
            ) * spec.side_axis[1]
            assert sign * along > 150.0


def test_variety_covers_hulls_squad_sizes_and_go_to_distances() -> None:
    specs = [GEN.generate(DRILL_GOTO, seed) for seed in range(300)]
    assert {len(s.pilots) for s in specs} == {1, 2, 3, 4}
    assert {h for s in specs for h in s.teams[0]} == set(FLEET_HULLS)
    distances = [d for s in specs for d in s.distances]
    assert min(distances) < 150.0
    assert max(distances) > 600.0, "far go-tos cross the map"
    radii = [s.radius for s in specs]
    assert min(radii) < 20.0 and max(radii) > 70.0
    assert 90 <= sum(s.far for s in specs) <= 210
    assert 90 <= sum(s.enemies_around for s in specs) <= 210


def test_go_to_enemies_are_around_the_route_or_far_from_it() -> None:
    near_route: list[float] = []
    far_from_route: list[float] = []
    for seed in range(120):
        spec = GEN.generate(DRILL_GOTO, seed)
        n = len(spec.pilots)
        start = np.array([spec.layout[0].x, spec.layout[0].y])
        start += (np.array([spec.layout[n - 1].x, spec.layout[n - 1].y]) - start) / 2.0
        point = np.array(spec.point)
        route = point - start
        for enemy in spec.layout[n:]:
            at = np.array([enemy.x, enemy.y]) - start
            t = np.clip(at @ route / (route @ route), 0.0, 1.0)
            gap = float(np.linalg.norm(at - t * route))
            (near_route if spec.enemies_around else far_from_route).append(gap)
    assert np.median(near_route) < 200.0
    assert min(far_from_route) > 200.0, "far means far from the route"


def test_the_old_rule_deadline_is_twice_the_straight_line_plus_ten_seconds() -> None:
    assert goto_deadline_tick(600.0, 60.0) == ORDER_TICK + math.ceil(
        (GOTO_TIME_MULT * 600.0 / 60.0 + GOTO_SLACK_S) * TICK_HZ
    )
    with pytest.raises(ValueError):
        goto_deadline_tick(-1.0, 60.0)
    with pytest.raises(ValueError):
        goto_deadline_tick(10.0, 0.0)


def test_the_order_deadline_is_slack_times_the_slowest_ship_plus_the_turn() -> None:
    # The gunship is the slow one: 240 m at 24 m/s is 10 s; the fighter needs 5 s.
    tick = goto_order_deadline_tick(2.0, [300.0, 240.0], [60.0, 24.0])
    assert tick == ORDER_TICK + math.ceil((2.0 * 10.0 + GOTO_TURN_S) * TICK_HZ)
    assert goto_order_deadline_tick(1.0, [0.0], [60.0]) == ORDER_TICK + math.ceil(
        GOTO_TURN_S * TICK_HZ
    )
    bad: list[tuple[float, list[float], list[float]]] = [
        (0.0, [100.0], [60.0]),
        (math.inf, [100.0], [60.0]),
        (2.0, [], []),
        (2.0, [100.0], [60.0, 50.0]),
        (2.0, [-1.0], [60.0]),
        (2.0, [100.0], [0.0]),
    ]
    for slack, distances, caps in bad:
        with pytest.raises(ValueError):
            goto_order_deadline_tick(slack, distances, caps)


def test_go_to_distances_are_to_the_circle_s_edge() -> None:
    for seed in range(100):
        spec = GEN.generate(DRILL_GOTO, seed)
        assert len(spec.deadlines) == len(spec.pilots) == len(spec.distances)
        for slot, distance in zip(spec.pilots, spec.distances):
            start = spec.layout[slot]
            straight = math.hypot(start.x - spec.point[0], start.y - spec.point[1])
            assert distance == pytest.approx(max(0.0, straight - spec.radius), abs=1e-3)


def test_three_go_tos_in_four_carry_one_deadline_for_the_squad() -> None:
    caps = GEN.speed_caps
    specs = [GEN.generate(DRILL_GOTO, seed) for seed in range(400)]
    timed = [s for s in specs if s.timed]
    untimed = [s for s in specs if not s.timed]
    assert len(untimed) / len(specs) == pytest.approx(GOTO_NO_DEADLINE_P, abs=0.07)
    for spec in timed:
        hull_caps = [caps[spec.teams[0][slot]] for slot in spec.pilots]
        assert GOTO_SLACK[0] <= spec.slack <= GOTO_SLACK[1]
        assert spec.deadline_tick == goto_order_deadline_tick(
            spec.slack, spec.distances, hull_caps
        )
        assert spec.deadlines == (spec.deadline_tick,) * len(spec.pilots)
        assert spec.order().deadline_tick == spec.deadline_tick
        assert spec.roster().drill == DrillTag(
            DRILL_GOTO, spec.pilots, deadlines=spec.deadlines, timed=True
        )
        # The slowest ship's flat-out straight run fits, with the turn allowance over.
        flat_out = max(d / cap for d, cap in zip(spec.distances, hull_caps))
        assert spec.deadline_tick >= ORDER_TICK + (flat_out + GOTO_TURN_S) * TICK_HZ
    # Log-uniform: as many slacks under the geometric middle as over it.
    middle = math.sqrt(GOTO_SLACK[0] * GOTO_SLACK[1])
    below = sum(s.slack < middle for s in timed) / len(timed)
    assert below == pytest.approx(0.5, abs=0.09)
    assert min(s.slack for s in timed) < 1.15 * GOTO_SLACK[0]
    assert max(s.slack for s in timed) > 0.875 * GOTO_SLACK[1]


def test_a_go_to_without_a_deadline_is_judged_by_the_old_rule_ship_by_ship() -> None:
    caps = GEN.speed_caps
    untimed = [
        s for s in (GEN.generate(DRILL_GOTO, seed) for seed in range(60)) if not s.timed
    ]
    assert untimed
    for spec in untimed:
        assert spec.deadline_tick == NO_DEADLINE and spec.slack == 0.0
        assert spec.order().deadline_tick == NO_DEADLINE
        assert spec.deadlines == tuple(
            goto_deadline_tick(d, caps[spec.teams[0][slot]])
            for slot, d in zip(spec.pilots, spec.distances)
        )
        tag = spec.roster().drill
        assert tag is not None and not tag.timed and tag.deadlines == spec.deadlines


def test_the_go_to_clock_runs_a_drawn_one_to_twenty_seconds_past_the_last_deadline() -> (
    None
):
    low, high = GOTO_CLOCK_EXTRA_TICKS
    assert (low, high) == (1 * TICK_HZ, 20 * TICK_HZ)
    extras = []
    for seed in range(300):
        spec = GEN.generate(DRILL_GOTO, seed)
        extras.append(spec.clock_ticks - max(spec.deadlines))
        assert spec.roster().time_limit_s == pytest.approx(spec.clock_ticks / TICK_HZ)
    assert low <= min(extras) and max(extras) <= high
    # Spread over the range, so the match's time left does not give the deadline away.
    assert min(extras) < low + 60 and max(extras) > high - 60
    assert np.std(extras) > 120


# A go-to drill's layout for three seeds, computed before the order carried a deadline
# (SIM_VERSION 7): teams, point, radius, distances, the first pilot's start, the last
# enemy's start, and the old-rule deadlines.
_GOTO_LAYOUT_PINS: dict[int, dict[str, Any]] = {
    7: {
        "teams": (("gunship",), ("fighter", "gunship", "strafer")),
        "far": True,
        "around": False,
        "point": (122.8653811545024, 361.9769291672397),
        "radius": 47.34321924681465,
        "distances": (482.99796570108686,),
        "first": (
            -151.93939327663412,
            -91.61331367512614,
            -0.06641588950022648,
            -11.531780455381934,
            -1.5765556417093336,
        ),
        "last": (
            235.20201772356089,
            -142.49565206968862,
            -2.0296311167516583,
            2.2566870179993384,
            2.3032717080852567,
        ),
        "old_deadlines": (1568,),
    },
    500_000: {
        "teams": (("fighter", "fighter", "gunship"), ("strafer",)),
        "far": False,
        "around": False,
        "point": (277.3717324194038, -28.330800409043835),
        "radius": 57.664582849950015,
        "distances": (181.37356309645233, 179.48354642264945, 181.37356309645233),
        "first": (
            39.054289596541274,
            -46.8788909809921,
            15.697065518885047,
            4.8465345800605695,
            0.29946867580835246,
        ),
        "last": (
            17.09091474871945,
            354.58835377526435,
            3.6723611607718287,
            -9.766018394354882,
            -1.2111188880928836,
        ),
        "old_deadlines": (542, 540, 814),
    },
    500_123: {
        "teams": (("strafer", "gunship"), ("fighter", "gunship")),
        "far": False,
        "around": False,
        "point": (202.47083668798874, -288.95979013902075),
        "radius": 15.210934699625257,
        "distances": (171.75087066772474, 171.75087066772474),
        "first": (
            30.50480856302309,
            -362.3246443755173,
            -23.408393007187662,
            7.297858713884375,
            2.839379828339627,
        ),
        "last": (
            -99.96379863601629,
            298.7176576003802,
            0.2936088926088984,
            -0.8465832370786814,
            -1.2369605483216652,
        ),
        "old_deadlines": (567, 790),
    },
}


@pytest.mark.parametrize("seed", sorted(_GOTO_LAYOUT_PINS))
def test_a_seed_s_go_to_layout_is_what_it_was_before_deadlines(seed: int) -> None:
    pin = _GOTO_LAYOUT_PINS[seed]
    spec = GEN.generate(DRILL_GOTO, seed)
    exact = pytest.approx
    assert spec.teams == pin["teams"]
    assert (spec.far, spec.enemies_around) == (pin["far"], pin["around"])
    assert spec.point == exact(pin["point"], rel=1e-12)
    assert spec.radius == exact(pin["radius"], rel=1e-12)
    assert spec.distances == exact(pin["distances"], rel=1e-12)
    assert spec.layout[0].row() == exact(list(pin["first"]), rel=1e-12)
    assert spec.layout[-1].row() == exact(list(pin["last"]), rel=1e-12)
    caps = GEN.speed_caps
    old_rule = tuple(
        goto_deadline_tick(d, caps[spec.teams[0][slot]])
        for slot, d in zip(spec.pilots, spec.distances)
    )
    assert old_rule == pin["old_deadlines"]


def test_the_sim_holds_the_drill_s_deadline_once_the_order_lands() -> None:
    specs = [GEN.generate(DRILL_GOTO, seed) for seed in range(40)]
    timed = next(s for s in specs if s.timed)
    untimed = next(s for s in specs if not s.timed)
    for spec in (timed, untimed):
        env = play(spec.roster(), steps=ORDER_TICK + 1)
        tracks = env.order_tracks()
        for slot in spec.pilots:
            assert int(tracks["deadline"][0, slot]) == spec.deadline_tick
        has_deadline = env.obs[0, 0, rlf_sim.OBS_LAYOUT["order_time"][0]]
        assert has_deadline == (1.0 if spec.timed else 0.0)


def test_rosters_with_layouts_are_validated() -> None:
    at = ShipStart(0.0, 0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError, match="entries for"):
        Roster.of(["fighter"], ["fighter"]).__class__(
            (("fighter",), ("fighter",)), start_layout=(at,)
        )
    with pytest.raises(ValueError, match="places its own"):
        Roster(
            (("carrier",), ("carrier",)),
            mission="carrier_battle",
            start_layout=(at, at),
        )
    with pytest.raises(ValueError, match="needs a start_layout"):
        Roster((("fighter",), ("fighter",)), drill=DrillTag("goto", (0,)))
    with pytest.raises(ValueError, match="names slots"):
        Roster(
            (("fighter",), ("fighter",)),
            start_layout=(at, ShipStart(100.0, 0.0, 0.0, 0.0, 0.0)),
        ).swapped()
    with pytest.raises(ValueError, match="unknown order kind"):
        OpeningOrder(0, 0, (0,), "hold").command()


# -- start layouts and drill rules through the env ---------------------------------------


def test_ships_start_where_the_layout_says_through_the_env() -> None:
    spec = GEN.generate(DRILL_DEFEND, 8)
    env = play(spec.roster())
    state = env.raw.render_state(0)
    for slot, start in enumerate(spec.layout):
        ship = state["ships"][slot]
        assert ship["present"]
        assert ship["pos"] == pytest.approx((start.x, start.y))
        assert ship["vel"] == pytest.approx((start.vx, start.vy))
        assert ship["heading"] == pytest.approx(start.heading)


def test_a_bad_layout_is_a_value_error_at_the_boundary() -> None:
    env = RustVecEnv(ASSETS, 1, [["fighter"], ["fighter"]], 0, n_threads=1)
    start = ShipStart(0.0, 0.0, 0.0, 0.0, 0.0)
    roster = Roster(
        (("fighter",), ("fighter",)),
        start_layout=(start, ShipStart(5000.0, 0.0, 0.0, 0.0, 0.0)),
    )
    with pytest.raises(ValueError, match="outside the arena"):
        env.set_next_roster(0, roster)
    with pytest.raises(ValueError, match="2 entries for|3 entries"):
        env.raw.set_next_roster(
            0,
            [["fighter"], ["fighter"]],
            450.0,
            start_layout=[
                [0.0] * 5,
                [100.0, 0.0, 0.0, 0.0, 0.0],
                [200.0, 0.0, 0.0, 0.0, 0.0],
            ],
        )


def test_layout_does_not_change_a_match_without_one() -> None:
    plain = RustVecEnv(ASSETS, 2, [["fighter"], ["fighter"]], 11, n_threads=1)
    other = RustVecEnv(ASSETS, 2, [["fighter"], ["fighter"]], 11, n_threads=1)
    other.set_next_roster(1, Roster.of(["fighter"], ["fighter"]))
    plain.reset()
    other.reset()
    for _ in range(200):
        plain.scripted_actions()
        other.scripted_actions()
        plain.step()
        other.step()
    assert np.array_equal(plain.raw.state_hash(), other.raw.state_hash())


def test_the_orders_land_on_the_first_slow_tick_once_a_match_and_survive_auto_reset() -> (
    None
):
    spec = GEN.generate(DRILL_ATTACK, 2)
    env = play(replace(spec.roster(), time_limit_s=ORDER_TICK * 2 / TICK_HZ))
    assert int(env.order_tracks()["standing_kind"][0, 0]) == 0
    for _ in range(ORDER_TICK):
        assert not env.act_mask[0, 0], "nobody acts before the order"
        env.scripted_actions()
        env.step()
    tracks = env.order_tracks()
    assert int(tracks["target"][0, 0]) == spec.named_slot
    assert int(tracks["instance_start"][0, 0]) == ORDER_TICK
    assert env.act_mask[0, 0]
    assert env.obs[0, 0, HAS_ORDER_COL] > 0.5
    while int(env.raw.episode_count[0]) == 0:
        env.scripted_actions()
        env.step()
    # The sticky roster rebuilt: same drill, and its orders were queued again.
    assert env.rosters[0].drill is not None
    for _ in range(ORDER_TICK):
        env.scripted_actions()
        env.step()
    assert int(env.order_tracks()["target"][0, 0]) == spec.named_slot


def test_a_drill_is_a_deathmatch_to_the_sim() -> None:
    # The pilot obs carries the mission as a one-hot, so a drill must not be a mission of
    # its own (crates/sim/tests/drills.rs compares the obs float by float).
    drilled = play(GEN.generate(DRILL_DEFEND, 4).roster())
    assert drilled.raw.mission_state(0)["mission"] == "deathmatch"


# -- what the script does in each drill: the reference --------------------------------------


def test_script_followers_reach_their_go_to_point_shown_or_hidden() -> None:
    specs = GEN.generate_many(DRILL_GOTO, 16, 1000)
    shown = run_pass(Scripted(), specs, 7)
    outcomes = [ship.outcome() for r in shown for ship in r.ships]
    assert outcomes.count("late") == 0, "the script always gets there"
    assert outcomes.count("arrived") > len(outcomes) / 2
    # Known limitation, asserted: the script reads orders from the state, not the obs, so
    # a hidden pass of the script is the same flight. That is why evaluate() skips it.
    hidden = run_pass(Scripted(), specs, 7, hidden=True)
    assert [s.arrived_tick for r in hidden for s in r.ships] == [
        s.arrived_tick for r in shown for s in r.ships
    ]


def test_the_hidden_pass_shows_no_order_to_the_pilots_on_the_same_seeds() -> None:
    spec = GEN.generate(DRILL_GOTO, 3)
    shown = play(spec.roster(), steps=ORDER_TICK + 1)
    hidden = play(spec.roster(hidden=True), steps=ORDER_TICK + 1)
    assert shown.obs[0, 0, HAS_ORDER_COL] > 0.5
    assert hidden.obs[0, 0, HAS_ORDER_COL] == 0.0
    # The order stands for the sim all the same, and the matches are the same.
    assert hidden.order_tracks()["standing_kind"][0, 0] == 3
    assert hidden.raw.render_state(0)["ships"][0]["pos"] == pytest.approx(
        shown.raw.render_state(0)["ships"][0]["pos"]
    )


@pytest.mark.parametrize("kind", SIDE_KINDS)
def test_script_followers_go_for_the_named_side_and_flip_with_it(kind: str) -> None:
    specs = GEN.generate_many(kind, 16, 2000)
    partners = [s.swapped() for s in specs]
    first = run_pass(Scripted(), specs, 9)
    second = run_pass(Scripted(), partners, 9)
    summary = _sides_summary(first, second)
    assert summary["flip"]["rate"] >= 0.75, summary
    assert summary["chose_other"]["rate"] <= 0.15, summary
    # Which side was named is what moved them, on the same start and seed.
    assert any(
        a.named_group_damage != b.named_group_damage for a, b in zip(first, second)
    )


def test_the_script_lands_damage_on_the_named_target_and_on_the_named_ward_s_attackers() -> (
    None
):
    attack = run_pass(Scripted(), GEN.generate_many(DRILL_ATTACK, 16, 3000), 5)
    assert sum(r.target_damage > 0.0 for r in attack) >= 13
    defend = run_pass(Scripted(), GEN.generate_many(DRILL_DEFEND, 16, 4000), 5)
    assert sum(r.named_group_damage > r.other_group_damage for r in defend) >= 13


def test_each_ward_really_is_under_attack_even_if_the_pilots_do_nothing() -> None:
    specs = GEN.generate_many(DRILL_DEFEND, 12, 5000)
    env = RustVecEnv(
        ASSETS,
        len(specs),
        [["fighter"], ["fighter"]],
        3,
        max_ships=20,
        n_threads=2,
        commanders=(EXTERNAL, EXTERNAL),
    )
    for i, spec in enumerate(specs):
        env.set_next_roster(i, spec.roster())
    env.reset()
    full = [
        {
            w: (lambda s: s["hp"] + s["shield"])(env.raw.render_state(i)["ships"][w])
            for w in spec.side_targets
        }
        for i, spec in enumerate(specs)
    ]
    lowest = [dict(f) for f in full]
    threatened = np.zeros((len(specs), 2), dtype=bool)
    team = env.team.copy()
    for _ in range(600):
        env.scripted_actions()
        actions = env.actions.copy()
        actions[team == 0] = 0  # pilots and wards stay idle-ish
        env.step(actions)
        for i, spec in enumerate(specs):
            ships = env.raw.render_state(i)["ships"]
            for j, ward in enumerate(spec.side_targets):
                threatened[i, j] |= any(
                    env.ward_threat[i, ward, e] for e in spec.side_groups[j]
                )
                left = ships[ward]["hp"] + ships[ward]["shield"]
                lowest[i][ward] = min(lowest[i][ward], left)
    assert threatened.all(), "each group is in its own ward's threat set"
    # The lowest point, not the last: shields regenerate once an attack ends (v7: a
    # group can lose a fighter to a crash and stop landing hits).
    for i, spec in enumerate(specs):
        for ward in spec.side_targets:
            assert (
                lowest[i][ward] < full[i][ward]
            ), f"drill {spec.seed}: ward {ward} took no damage"


def test_charging_groups_fly_at_the_pilots_and_busy_groups_stay_on_their_side() -> None:
    busy = next(s for s in GEN.generate_many(DRILL_ATTACK, 50, 0) if not s.charging)
    charging = next(s for s in GEN.generate_many(DRILL_ATTACK, 50, 0) if s.charging)
    ax = np.array(busy.side_axis)
    env = play(busy.roster(), steps=ORDER_TICK + 150)
    ships = env.raw.render_state(0)["ships"]
    for side, sign in ((0, -1.0), (1, 1.0)):
        for slot in busy.side_groups[side]:
            assert (
                sign * (np.array(ships[slot]["pos"]) @ ax) > 100.0
            ), "stayed on its side"
    start = [
        np.array([charging.layout[s].x, charging.layout[s].y])
        for s in charging.side_groups[0]
    ]
    env = play(charging.roster(), steps=ORDER_TICK + 150)
    ships = env.raw.render_state(0)["ships"]
    pilot = np.array(ships[0]["pos"])
    moved = [
        np.linalg.norm(np.array(ships[s]["pos"]) - pilot) < np.linalg.norm(p - pilot)
        for s, p in zip(charging.side_groups[0], start)
    ]
    assert any(moved), "at least one charger closed on the pilots"


# -- pay ---------------------------------------------------------------------------------


def _shooter_drill() -> tuple[Roster, int, int]:
    """A fighter with an enemy right on its nose and the named target far away. Slot 0
    shoots; slot 1 is the enemy it hits; slot 2 is the named target."""
    layout = (
        ShipStart(0.0, 0.0, 0.0, 0.0, 0.0),
        ShipStart(60.0, 0.0, 0.0, 0.0, math.pi),
        ShipStart(-300.0, 200.0, 0.0, 0.0, 0.0),
    )
    roster = Roster(
        (("fighter",), ("gunship", "gunship")),
        commanders=(EXTERNAL, EXTERNAL),
        start_layout=layout,
        opening_orders=(OpeningOrder(0, 0, (0,), DRILL_ATTACK, target=2),),
        time_limit_s=20.0,
        drill=DrillTag(
            DRILL_ATTACK, (0,), named_slot=2, named_group=(2,), other_group=(1,)
        ),
    )
    return roster, 1, 2


def test_a_hit_on_a_non_named_enemy_pays_what_it_always_pays_and_no_penalty() -> None:
    roster, _, _ = _shooter_drill()
    env = play(roster)
    fire_col = rlf_sim.ACTION_LAYOUT["fire"][0]
    paid = 0
    seen_hit = 0
    for _ in range(ORDER_TICK + 120):
        actions = np.zeros_like(env.actions)
        actions[..., :8] = 1
        actions[..., fire_col] = 1
        _, rewards, dones, info = env.step(actions)
        rows = info.hits[0, : int(info.hit_count[0])]
        mine = rows[rows[:, 0] == 0]
        if mine.size:
            assert set(mine[:, 1].tolist()) == {1}, "this fighter only reaches slot 1"
            # The team reward has the usual damage weights in it...
            hull = mine[mine[:, 4] == 0, 3].sum() / 1000.0 * 0.01
            shield = mine[mine[:, 4] != 0, 3].sum() / 1000.0 * 0.005
            assert rewards[0, 0] >= hull + shield + 2 * -0.002 - 1e-3
            # ... and order pay neither pays nor charges for it.
            assert env.order_rewards[0, 0] == 0.0
            seen_hit += 1
            paid += 1
        assert not dones.any()
    assert seen_hit > 0 and paid > 0


def test_a_hit_on_the_named_target_pays_more_than_the_same_hit_on_another() -> None:
    layout = (
        ShipStart(0.0, 0.0, 0.0, 0.0, 0.0),
        ShipStart(60.0, 0.0, 0.0, 0.0, math.pi),
        ShipStart(-300.0, 200.0, 0.0, 0.0, 0.0),
    )
    named = Roster(
        (("fighter",), ("gunship", "gunship")),
        commanders=(EXTERNAL, EXTERNAL),
        start_layout=layout,
        opening_orders=(OpeningOrder(0, 0, (0,), DRILL_ATTACK, target=1),),
        time_limit_s=20.0,
        drill=DrillTag(DRILL_ATTACK, (0,), named_slot=1),
    )
    env = play(named)
    fire_col = rlf_sim.ACTION_LAYOUT["fire"][0]
    order_pay = 0.0
    for _ in range(ORDER_TICK + 120):
        actions = np.zeros_like(env.actions)
        actions[..., :8] = 1
        actions[..., fire_col] = 1
        env.step(actions)
        order_pay += float(env.order_rewards[0, 0])
    assert order_pay > 0.0


@pytest.mark.parametrize("kind", DRILL_KINDS)
def test_a_drill_pays_no_match_result(kind: str) -> None:
    spec = GEN.generate(kind, 21)
    # The pilots die at once, the match ends: a real match would pay -1 here.
    roster = replace(spec.roster(), time_limit_s=(ORDER_TICK + 3) / TICK_HZ)
    env = play(roster)
    rewards_at_end: np.ndarray | None = None
    for _ in range(ORDER_TICK + 4):
        env.scripted_actions()
        _, rewards, dones, info = env.step()
        if dones[0]:
            rewards_at_end = rewards[0].copy()
            assert int(info.winner[0]) == -1, "a drill ends as a draw"
            break
    assert rewards_at_end is not None
    assert np.abs(rewards_at_end).max() < 0.9, "no +/-1 in the last step"
    assert rlf_sim.END_REASONS[int(env.end_reason[0])] == "time_limit"


def test_the_ledger_books_hits_on_the_named_target_and_each_group() -> None:
    ledger = DrillLedger(2, 4)
    tag = DrillTag(DRILL_ATTACK, (0,), named_slot=2, named_group=(2,), other_group=(3,))
    ledger.begin(1, tag)
    hits = np.zeros((2, 3, 6), dtype=np.int32)
    hits[1, 0] = (0, 2, 0, 5000, 0, 0)  # pilot on the named target
    hits[1, 1] = (0, 3, 0, 2000, 0, 0)  # pilot on the other group
    hits[1, 2] = (3, 0, 0, 9000, 0, 0)  # an enemy on the pilot: not the pilots' damage
    ledger.add_hits(hits, np.array([0, 3], dtype=np.int32))
    assert ledger.target_damage[1] == pytest.approx(5.0)
    assert ledger.group_damage[1].tolist() == pytest.approx([5.0, 2.0])
    assert ledger.total_damage[1] == pytest.approx(7.0)
    assert ledger.finish(1) == DrillOutcome(DRILL_ATTACK, 1, 1)
    with pytest.raises(ValueError, match="not running"):
        ledger.finish(1)


def _tracks(**flags: list[bool]) -> dict[str, np.ndarray]:
    """One env of three slots: ``arrived``, ``missed`` and ``alive`` rows."""
    return {name: np.array([row], dtype=np.bool_) for name, row in flags.items()}


def test_the_ledger_counts_arrivals_in_time_and_missed_deadlines() -> None:
    ledger = DrillLedger(1, 3)
    tag = DrillTag(DRILL_GOTO, (0, 1, 2), deadlines=(500, 500, 500), timed=True)
    ledger.begin(0, tag)
    alive = [True, True, False]
    seen = _tracks(arrived=[True, False, False], missed=[False, False, False])
    ledger.see_tracks(
        seen["arrived"], seen["missed"], np.array([alive]), np.array([400])
    )
    # Past the deadline the sim marks the other two missed; the dead one is not counted.
    seen = _tracks(arrived=[True, False, False], missed=[False, True, True])
    ledger.see_tracks(
        seen["arrived"], seen["missed"], np.array([alive]), np.array([501])
    )
    assert ledger.finish(0) == DrillOutcome(DRILL_GOTO, 1, 3, timed_ships=3, missed=1)
    with pytest.raises(ValueError, match="deadlines for"):
        DrillTag(DRILL_GOTO, (0, 1), deadlines=(500,))


def test_the_ledger_judges_a_go_to_without_a_deadline_by_the_tick_it_is_given() -> None:
    ledger = DrillLedger(1, 3)
    ledger.begin(0, DrillTag(DRILL_GOTO, (0, 1), deadlines=(500, 800)))
    alive = np.array([[True, True, True]])
    nothing = np.zeros((1, 3), dtype=np.bool_)
    late = _tracks(arrived=[True, True, False])["arrived"]
    # Both first show as arrived at tick 600: in time for the second ship only.
    ledger.see_tracks(nothing, nothing, alive, np.array([500]))
    ledger.see_tracks(late, nothing, alive, np.array([600]))
    assert ledger.finish(0) == DrillOutcome(DRILL_GOTO, 1, 2)
    # With no deadlines on the tag (a hand-built drill) any arrival counts.
    ledger.begin(0, DrillTag(DRILL_GOTO, (0, 1)))
    ledger.see_tracks(late, nothing, alive, np.array([5000]))
    assert ledger.finish(0) == DrillOutcome(DRILL_GOTO, 2, 2)


# -- the eval's measurements --------------------------------------------------------------


def _record(choice: str) -> DrillRecord:
    return DrillRecord(GEN.generate(DRILL_DEFEND, 1), choice=choice)


def test_a_flip_needs_the_squad_to_go_where_it_was_told_both_times() -> None:
    pairs = [
        (CHOSE_NAMED, CHOSE_NAMED),  # flipped with the order
        (CHOSE_NAMED, CHOSE_OTHER),  # the same side both times: not understood
        (CHOSE_OTHER, CHOSE_NAMED),  # the same side both times
        (NO_CHOICE, CHOSE_NAMED),
    ]
    out = _sides_summary([_record(a) for a, _ in pairs], [_record(b) for _, b in pairs])
    assert out["flip"]["successes"] == 1
    assert out["same_side"]["successes"] == 2
    assert out["no_choice"]["successes"] == 1
    assert out["n_pairs"] == 4


def test_being_killed_on_the_way_is_censored_not_failed() -> None:
    assert ShipRun(deadline=600, arrived_tick=500).outcome() == "arrived"
    assert ShipRun(deadline=600, arrived_tick=601).outcome() == "late"
    assert ShipRun(deadline=600, gone_tick=300).outcome() == "censored"
    assert ShipRun(deadline=600, gone_tick=700).outcome() == "late"
    assert ShipRun(deadline=600).outcome() == "late"


def test_a_ship_that_was_not_in_time_was_a_near_miss_at_the_enemy_or_neither() -> None:
    assert ShipRun(600, arrived_tick=500, min_edge_m=0.0).fate() == IN_TIME
    assert ShipRun(600, gone_tick=300, min_edge_m=10.0).fate() == KILLED
    close = ShipRun(600, arrived_tick=700, min_edge_m=NEAR_MISS_M, near_enemy=True)
    assert close.fate() == NEAR_MISS, "a near miss whatever else it was near"
    assert ShipRun(600, min_edge_m=NEAR_MISS_M + 1, near_enemy=True).fate() == AT_ENEMY
    assert ShipRun(600, min_edge_m=NEAR_MISS_M + 1).fate() == NEITHER
    assert ShipRun(600).fate() == NEITHER


def _ship(x: float, y: float, alive: bool = True) -> dict[str, Any]:
    return {"pos": (x, y), "alive": alive}


def test_the_go_to_watch_reads_distances_up_to_each_ship_s_deadline() -> None:
    spec = replace(
        GEN.generate(DRILL_GOTO, 7),
        teams=(("fighter", "fighter"), ("fighter",)),
        layout=(ShipStart(0, 0, 0, 0, 0),) * 3,
        pilots=(0, 1),
        point=(300.0, 0.0),
        radius=50.0,
        deadlines=(100, 200),
        arena_radius=450.0,
    )
    watch = _GotoWatch(spec)
    # Tick 90: ship 0 is 150 m from the edge and 100 m from the enemy; ship 1 far off.
    watch.see([_ship(100, 0), _ship(-300, 0), _ship(100, 100)], 90)
    assert watch.min_edge.tolist() == pytest.approx([150.0, 550.0])
    assert watch.near_enemy.tolist() == [True, False]
    # Tick 150 is past ship 0's deadline: only ship 1 is read, 40 m from the edge.
    watch.see([_ship(290, 0), _ship(210, 0), _ship(100, 100, alive=False)], 150)
    assert watch.min_edge.tolist() == pytest.approx([150.0, 40.0])
    assert watch.near_enemy.tolist() == [True, True], "every enemy dead counts"
    assert not watch.settled(200) and watch.settled(201)
    assert ENEMY_NEAR_M == 150.0 and NEAR_MISS_M == 60.0


def test_slack_bands_are_tight_under_two_and_a_half_and_loose_over_four_and_a_half() -> (
    None
):
    assert [slack_band(x) for x in (1.5, 2.49, 2.5, 4.49, 4.5, 8.0)] == [
        "tight",
        "tight",
        "medium",
        "medium",
        "loose",
        "loose",
    ]
    with pytest.raises(ValueError):
        slack_band(0.0)


def test_the_go_to_summary_keeps_its_old_keys_and_splits_by_deadline_and_fate() -> None:
    specs = GEN.generate_many(DRILL_GOTO, 24, 2000)
    shown = run_pass(Scripted(), specs, 11)
    out = summarise_goto(shown, [])
    for key in ("n_drills", "shown", "shown_near", "shown_far", "shown_enemies_around"):
        assert key in out
    assert out["hidden"] is None and out["lift"] is None
    assert set(out["shown"]) == {"rate", "se", "arrived", "late", "censored", "n"}
    parts = (out["with_deadline"], out["no_deadline"])
    for key in ("arrived", "late", "censored", "n"):
        assert sum(part[key] for part in parts) == out["shown"][key]
    bands = out["by_slack"]
    assert set(bands) == {"tight", "medium", "loose"}
    assert sum(b["n"] for b in bands.values()) == out["with_deadline"]["n"]
    fates = out["fates"]
    assert fates["n"] == out["shown"]["n"] and fates[KILLED] == out["shown"]["censored"]
    assert sum(fates[f]["successes"] for f in FATES) == fates["n"]
    assert fates[IN_TIME]["successes"] == out["shown"]["arrived"]
    assert out["fates_with_deadline"]["n"] + out["fates_no_deadline"]["n"] == fates["n"]
    assert out["fates_solo"]["n"] == sum(
        ship.fate() != KILLED
        for r in shown
        if len(r.spec.pilots) == 1
        for ship in r.ships
    )
    assert "SIM_VERSION 8" in out["note"]
    # A ship in time was inside the circle at some read of its position.
    for record in shown:
        for ship in record.ships:
            if ship.fate() == IN_TIME:
                assert ship.min_edge_m <= NEAR_MISS_M


def test_rates_carry_counts_and_standard_errors() -> None:
    rate = Rate.of(3, 4)
    assert rate.rate == 0.75
    assert rate.se == pytest.approx(math.sqrt(0.75 * 0.25 / 4))
    assert Rate.of(0, 0).rate == 0.0


# -- the gate -----------------------------------------------------------------------------


def _summary(value: float) -> dict[str, object]:
    rate = {"rate": value}
    return {
        DRILL_GOTO: {"shown": rate, "lift": value},
        DRILL_ATTACK: {"target_hit": rate, "chose_named": rate, "flip": rate},
        DRILL_DEFEND: {"more_on_named": rate, "chose_named": rate, "flip": rate},
    }


def test_the_shipped_bars_are_all_set_and_judge_a_strong_and_a_weak_pilot() -> None:
    bars = load_bars(DEFAULT_BARS)
    assert set(bars) == set(BAR_PATHS)
    assert all(v is not None and 0.0 < v < 1.0 for v in bars.values())
    assert apply_gate(_summary(0.99), bars, "strong").verdict == PASS
    assert apply_gate(_summary(0.2), bars, "weak").verdict == FAIL


def test_the_gate_is_report_only_with_no_bars_and_says_so() -> None:
    result = apply_gate(_summary(1.0), parse_bars({}), "someone")
    assert result.verdict == REPORT_ONLY
    assert "Report only, not a pass" in result.statement
    assert set(result.unset) == set(BAR_PATHS)


def test_a_missing_bar_is_report_only_and_one_unset_bar_is_enough() -> None:
    every: dict[str, float | None] = dict.fromkeys(BAR_PATHS, 0.5)
    assert apply_gate(_summary(1.0), parse_bars(every), "x").verdict == PASS
    every["defend_flip"] = None
    assert apply_gate(_summary(1.0), parse_bars(every), "x").verdict == REPORT_ONLY
    del every["defend_flip"]
    assert apply_gate(_summary(1.0), parse_bars(every), "x").verdict == REPORT_ONLY


def test_a_set_bar_that_is_not_met_fails_even_with_others_unset() -> None:
    result = apply_gate(_summary(0.2), parse_bars({"attack_flip": 0.5}), "x")
    assert result.verdict == FAIL
    assert result.failed == ("attack_flip",)


def test_exempt_pilots_are_not_judged_and_a_script_has_no_lift_to_pass_on() -> None:
    bars = parse_bars(dict.fromkeys(BAR_PATHS, 0.5))
    result = apply_gate(_summary(0.1), bars, "f995_701", exempt=("f995_701",))
    assert result.verdict == EXEMPT
    assert result.failed
    summary = _summary(1.0)
    summary[DRILL_GOTO] = {"shown": {"rate": 1.0}, "lift": None}
    no_lift = apply_gate(summary, bars, "script")
    assert no_lift.verdict == REPORT_ONLY
    assert no_lift.measured["goto_lift"] is None


def test_bad_bar_files_are_errors(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown drill bars"):
        parse_bars({"goto_arival": 0.5})
    with pytest.raises(ValueError, match="must be a number"):
        parse_bars({"goto_arrival": "high"})
    path = tmp_path / "bars.yaml"
    path.write_text("[1, 2]\n")
    with pytest.raises(ValueError, match="mapping"):
        load_bars(path)
    with pytest.raises(FileNotFoundError):
        load_bars(tmp_path / "missing.yaml")
    path.write_text(yaml.safe_dump({"goto_arrival": 0.5}))
    assert load_bars(path)["goto_arrival"] == 0.5


def test_a_tiny_eval_runs_on_the_script_and_writes_its_report(tmp_path: Path) -> None:
    out = tmp_path / "script.json"
    unset_bars = tmp_path / "bars.yaml"
    unset_bars.write_text("goto_arrival: null\n")
    assert (
        main(
            [
                "--a",
                "script",
                "--n-per-kind",
                "4",
                "--threads",
                "2",
                "--bars",
                str(unset_bars),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    data = json.loads(out.read_text())
    assert data["schema"] == SCHEMA
    assert data["gate"]["verdict"] == REPORT_ONLY
    assert data["kinds"][DRILL_GOTO]["hidden"] is None, "the script has no hidden pass"
    assert data["kinds"][DRILL_ATTACK]["n_pairs"] == 4
    assert data["kinds"][DRILL_GOTO]["by_slack"].keys() == {"tight", "medium", "loose"}
    report = out.with_suffix(".md").read_text()
    assert "Report only, not a pass" in report
    assert "Swap test" in report
    assert "changed with SIM_VERSION 8" in report
    assert "| tight (under 2.5) |" in report
    assert "| Near miss (within 60 m) |" in report


def test_evaluate_uses_the_same_drills_and_seeds_every_time() -> None:
    cfg = DrillEvalConfig(n_per_kind=2)
    a = evaluate(Scripted(), "script", cfg)
    b = evaluate(Scripted(), "script", cfg)
    assert a.kinds == b.kinds


# -- drills in training -------------------------------------------------------------------


def test_drill_share_zero_changes_nothing_in_the_sampler() -> None:
    plain = PilotsRosterSampler(PilotsDistribution(), 5)
    off = PilotsRosterSampler(PilotsDistribution(drill_share=0.0), 5)
    assert plain.sample_many(100) == off.sample_many(100)
    assert "drill_share" in resolve_distribution("pilots_v1").to_dict()


def test_drill_share_draws_drills_of_every_kind_by_their_weights() -> None:
    sampler = PilotsRosterSampler(PilotsDistribution(drill_share=0.5), 5)
    rosters = sampler.sample_many(400)
    drills = [r for r in rosters if r.drill is not None]
    assert 150 <= len(drills) <= 250
    assert {r.drill.kind for r in drills} == set(DRILL_KINDS)  # type: ignore[union-attr]
    only_attack = PilotsRosterSampler(
        PilotsDistribution(drill_share=1.0, drill_weights=(0.0, 1.0, 0.0)), 6
    )
    assert {r.drill.kind for r in only_attack.sample_many(20)} == {DRILL_ATTACK}  # type: ignore[union-attr]
    assert sum(r.hide_orders[0] for r in drills) == 0, "a drill shows its order"


def test_bad_drill_parameters_are_rejected() -> None:
    with pytest.raises(ValueError, match="drill_share"):
        PilotsDistribution(drill_share=1.5)
    with pytest.raises(ValueError, match="drill_weights"):
        PilotsDistribution(drill_weights=(1.0, 1.0))
    with pytest.raises(ValueError, match="positive sum"):
        PilotsDistribution(drill_weights=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="max_ships"):
        PilotsDistribution(
            drill_share=0.1, mission_weights=(1.0, 0.0, 0.0), max_ships=8
        )


def test_config_refuses_drills_that_would_teach_the_wrong_thing() -> None:
    base = {
        "tag": "x",
        "rosters": "pilots_v1",
        "roster_overrides": {"drill_share": 0.2},
    }
    with pytest.raises(ValueError, match="order_reward_weight"):
        PPOConfig.preset("scratch", **base)
    with pytest.raises(ValueError, match="hide_damage_when_ordered"):
        PPOConfig.preset(
            "scratch",
            **base,
            order_reward_weight=1.0,
            hide_damage_when_ordered=True,
        )
    assert PPOConfig.preset("scratch", tag="x").drill_share == 0.0


def test_a_forced_env_is_outside_the_quota_and_the_next_assign_returns_it() -> None:
    schedule = OpponentSchedule([[0, 0.5, 0.5, 0.0]])
    assigner = OpponentAssigner(8, schedule, np.random.default_rng(0))
    assigner.assign_all(0, 0, forced_scripted=np.array([0, 1, 2, 3]))
    assert assigner.kinds[:4].tolist() == [OpponentKind.SCRIPTED] * 4
    counts = assigner.counts()
    assert counts == {"scripted": 2, "self": 2, "snapshot": 0}, "the shares are of 4"
    assigner.assign(np.array([0]), 0, 0)
    assert not assigner.forced[0]
    assert sum(assigner.counts().values()) == 5


def test_no_forced_envs_draw_exactly_what_they_always_drew() -> None:
    schedule = OpponentSchedule([[0, 0.3, 0.4, 0.3]])
    plain = OpponentAssigner(16, schedule, np.random.default_rng(4))
    plain.assign_all(0, 3)
    other = OpponentAssigner(16, schedule, np.random.default_rng(4))
    other.assign_all(0, 3, forced_scripted=())
    assert plain.kinds.tolist() == other.kinds.tolist()
    assert plain.snapshot.tolist() == other.snapshot.tolist()


def _drill_config(**overrides: object) -> PPOConfig:
    settings: dict[str, object] = {
        "tag": "drill",
        "seed": 3,
        "assets_dir": str(ASSETS),
        "n_envs": 8,
        "n_steps": 72,
        "t_tail": 40,
        "n_updates": 3,
        "minibatch": 256,
        "epochs": 1,
        "sim_threads": 2,
        "torch_threads": 2,
        "rosters": "pilots_v1",
        "roster_overrides": {"drill_share": 0.6},
        "critic": "fleet",
        "learner_side": "random",
        "opponent_bands": [[0, 0.5, 0.5, 0.0]],
        "order_reward_weight": 1.0,
        "checkpoint_every": 100,
    }
    settings.update(overrides)
    return PPOConfig.preset("scratch", **settings)


def test_training_smoke_with_drills_logs_them_and_keeps_them_apart(
    tmp_path: Path,
) -> None:
    trainer = SpikeTrainer(_drill_config(), tmp_path)
    assert trainer.drills_on
    drills, _ = trainer._split_drills(np.arange(trainer.n_envs))
    assert drills.size, "seed 3 draws some drills at share 0.6"
    for env_id in drills:
        env_id = int(env_id)
        assert trainer.opponents.kinds[env_id] == OpponentKind.SCRIPTED
        assert trainer.opponents.forced[env_id]
        assert trainer.learner_team[env_id] == 0
    rows: list[dict[str, Any]] = []
    trainer.train(lambda _t, row: rows.append(row))
    # A drill's freighters are never learner rows, and in a drill only team 0 learns.
    store = trainer.storage
    assert not (store.learner & np.isin(store.hull, trainer.capital_ids)).any()
    assert trainer.next_update == 3
    assert len(rows) == 3
    assert all(0.0 < r["drill_rows_share"] <= 1.0 for r in rows)
    assert rows[-1]["samples"] > 0, "the last update trained on something"
    assert rows[-1]["pg_loss"] is not None
    logged = [
        json.loads(line) for line in (tmp_path / "log.jsonl").read_text().splitlines()
    ]
    assert logged[-1]["drill_rows_share"] == rows[-1]["drill_rows_share"]
    assert (tmp_path / "checkpoints").is_dir()
    drills_now, _ = trainer._split_drills(np.arange(trainer.n_envs))
    team = np.asarray(trainer.env.team)
    capital = np.isin(trainer.env.hull_id, trainer.capital_ids)
    for env_id in drills_now:
        env_id = int(env_id)
        assert trainer.learner_team[env_id] == 0
        assert (team[env_id][capital[env_id]] == 0).all(), "wards fly for team 0"


def test_a_drill_finished_in_training_is_counted_as_a_drill_not_as_a_match(
    tmp_path: Path,
) -> None:
    fast: dict[str, object] = {
        "drill_share": 1.0,
        "drill_weights": [0.0, 1.0, 1.0],
    }
    trainer = SpikeTrainer(
        _drill_config(roster_overrides=fast, n_steps=64, n_updates=1), tmp_path
    )
    # Hold the matches to a short clock so that they end inside one rollout.
    for i in range(trainer.n_envs):
        roster = trainer.env.rosters[i]
        trainer.env.set_next_roster(i, replace(roster, time_limit_s=3.0))
    trainer.env.reset()
    trainer.env.roster_sampler = None
    trainer.opponents.assign_all(
        0, 0, forced_scripted=np.arange(trainer.n_envs, dtype=np.int64)
    )
    trainer._note_new_matches(np.arange(trainer.n_envs))
    tally, _ = trainer._collect(0)
    fields: dict[str, Any] = tally.log_fields()
    assert sum(fields["drill_episodes"].values()) > 0
    assert fields["episodes"] == 0, "drills are not in the match tallies"
    assert fields["vs_scripted_episodes"] == 0
    assert fields["drill_rows_share"] == 1.0
    assert set(fields["drill_success"]) <= set(SIDE_KINDS)
    store = trainer.storage
    assert not store.terminal.any(), "no match result in a drill's pay"
    done_rows = store.dones.reshape(-1)
    assert done_rows.any()
    assert np.abs(store.team_reward.reshape(-1)[done_rows]).max() < 0.9
    assert not store.order_hidden.any(), "a drill's order pay is never masked"
