"""Dock drills (SIM_VERSION 11, ``spacefight.env.drills``, ``DRILL_DOCK``): the generator,
the hand-laid carrier battle and station assault through the env, the ledger, the eval's
dock kinds and their gate, and dock drills in the training mix.

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

rlf_sim = pytest.importorskip(
    "rlf_sim",
    reason=(
        "rlf_sim extension not built; run "
        "`uv run maturin develop -m crates/sim-py/Cargo.toml --release`"
    ),
)

from spacefight.env.drills import (  # noqa: E402
    DOCK_ATTACKERS,
    DOCK_BASES,
    DOCK_CLOCK_MULT,
    DOCK_CLOCK_SLACK_S,
    DOCK_DISTANCE,
    DOCK_ENEMY_CLEARANCE,
    DOCK_HULL_FRAC,
    DOCK_HULLS,
    ORDER_TICK,
    SELF_HULL_COL,
    START_LIMIT,
    TICK_HZ,
    DrillGenerator,
    DrillLedger,
    DrillOutcome,
)
from spacefight.env.rosters import (  # noqa: E402
    CARRIER_BATTLE,
    DEATHMATCH,
    DOCK_COMMAND,
    DRILL_DOCK,
    EXTERNAL,
    STATION_ASSAULT,
    WAYPOINT_COMMAND,
    OpeningOrder,
    PilotsDistribution,
    PilotsRosterSampler,
    Roster,
    ShipStart,
)
from spacefight.env.rust_env import TRACK_DOCK, RustVecEnv  # noqa: E402
from spacefight.eval.controllers import Scripted  # noqa: E402
from spacefight.eval.drills import (  # noqa: E402
    BAR_PATHS,
    DOCK_BAR_PATHS,
    DOCK_CALM,
    DOCK_THREAT,
    PASS,
    REPORT_ONLY,
    DrillEvalConfig,
    apply_gate,
    evaluate,
    parse_bars,
    run_pass,
    summarise_dock,
)
from spacefight.rl.spike_ppo import EpisodeTally, PPOConfig  # noqa: E402

ASSETS = Path(__file__).resolve().parents[1] / "assets"
GEN = DrillGenerator(ASSETS)
THREADS = 2


def test_a_dock_drill_is_a_pure_function_of_its_seed() -> None:
    assert GEN.dock(7) == GEN.dock(7)
    assert GEN.dock(7) != GEN.dock(8)


def test_calm_and_threat_drills_of_a_seed_share_everything_but_the_attackers() -> None:
    calm, threat = GEN.dock(11, threat=False), GEN.dock(11, threat=True)
    assert calm.layout == threat.layout[:3]
    assert calm.teams[0] == threat.teams[0]
    assert calm.start_hull_frac == threat.start_hull_frac
    assert len(calm.teams[1]) == 1, "calm: team 1 is its carrier alone"
    lo, hi = DOCK_ATTACKERS
    assert lo <= len(threat.teams[1]) - 1 <= hi
    attack = [o for o in threat.enemy_orders if o.team == 1]
    assert len(attack) == 1 and attack[0].target == 1, "the attackers are on the pilot"


def test_the_drills_cover_every_base_and_hull_and_fit_their_ranges() -> None:
    specs = [GEN.dock(seed) for seed in range(400)]
    assert {s.base for s in specs} == set(DOCK_BASES)
    assert {s.teams[0][1] for s in specs} == set(DOCK_HULLS)
    assert 0.35 < np.mean([s.threat for s in specs]) < 0.65
    for spec in specs:
        assert spec.kind == DRILL_DOCK and spec.pilots == (1,) and spec.home_slot == 0
        assert spec.mission == (
            CARRIER_BATTLE if spec.base == "carrier" else STATION_ASSAULT
        )
        assert spec.teams[0][0] == spec.base
        assert DOCK_HULL_FRAC[0] <= spec.start_hull_frac <= DOCK_HULL_FRAC[1]
        assert spec.start_hull[1] == spec.start_hull_frac
        assert all(f == 1.0 for k, f in enumerate(spec.start_hull) if k != 1)
        home, pilot, enemy = spec.layout[:3]
        out = math.hypot(pilot.x - home.x, pilot.y - home.y)
        assert DOCK_DISTANCE[0] - 1e-6 <= out <= DOCK_DISTANCE[1] + 1e-6
        assert spec.distances == (pytest.approx(out),)
        assert math.hypot(pilot.x, pilot.y) <= START_LIMIT + 1e-6
        assert math.hypot(pilot.x - enemy.x, pilot.y - enemy.y) >= DOCK_ENEMY_CLEARANCE
        cap = GEN.speed_caps[spec.teams[0][1]]
        seconds = DOCK_CLOCK_MULT * out / cap + DOCK_CLOCK_SLACK_S
        assert spec.clock_ticks == ORDER_TICK + math.ceil(seconds * TICK_HZ)
        moving = math.hypot(home.vx, home.vy) > 0.0
        assert moving == (
            spec.base == "carrier"
        ), "a carrier is under way, a base still"
        waypoints = [o for o in spec.enemy_orders if o.kind == WAYPOINT_COMMAND]
        assert len(waypoints) == (spec.base == "carrier")


def test_twenty_thousand_threat_drills_all_find_room() -> None:
    for seed in range(20_000):
        GEN.dock(seed, threat=True)


def test_the_opening_commands_are_a_dock_order_and_a_waypoint() -> None:
    assert OpeningOrder(0, 0, (1,), DOCK_COMMAND).command() == {
        "kind": "dock",
        "ship": 1,
        "bay": None,
    }
    waypoint = OpeningOrder(0, 0, (0,), WAYPOINT_COMMAND, point=(10.0, -20.0))
    assert waypoint.command() == {"kind": "waypoint", "ship": 0, "pos": [10.0, -20.0]}
    with pytest.raises(ValueError, match="for one ship"):
        OpeningOrder(0, 0, (1, 2), DOCK_COMMAND)


def test_a_roster_takes_a_start_hull_only_with_a_layout_and_in_range() -> None:
    layout = (ShipStart(-100, 0, 0, 0, 0), ShipStart(100, 0, 0, 0, 0))
    ok = Roster(
        (("fighter",), ("fighter",)), start_layout=layout, start_hull=(0.5, 1.0)
    )
    assert ok.start_hull == (0.5, 1.0)
    with pytest.raises(ValueError, match="needs a layout"):
        Roster((("fighter",), ("fighter",)), start_hull=(0.5, 1.0))
    with pytest.raises(ValueError, match=r"\(0, 1\]"):
        Roster((("fighter",), ("fighter",)), start_layout=layout, start_hull=(0.0, 1.0))
    with pytest.raises(ValueError, match="places its own ships"):
        Roster(
            (("freighter",), ("fighter",)), mission="convoy_escort", start_layout=layout
        )


def _env(specs: list, seed: int = 3, hidden: bool = False) -> RustVecEnv:
    env = RustVecEnv(
        ASSETS,
        len(specs),
        specs[0].roster().fleets(),
        seed,
        max_ships=8,
        n_threads=THREADS,
        commanders=(EXTERNAL, EXTERNAL),
    )
    for i, spec in enumerate(specs):
        env.set_next_roster(i, spec.roster(hidden=hidden))
    env.reset()
    return env


def test_the_env_plays_the_layout_damaged_pilot_and_dock_order() -> None:
    specs = [GEN.dock(seed) for seed in (1, 2, 3, 4)]
    env = _env(specs)
    for i, spec in enumerate(specs):
        assert env.rosters[i].mission == spec.mission
        hull = env.obs[i, 1, SELF_HULL_COL]
        assert hull == pytest.approx(spec.start_hull_frac, abs=1e-5)
        assert env.obs[i, 0, SELF_HULL_COL] == 0.0 or env.obs[i, 0, 0] > 0
    for _ in range(ORDER_TICK + 2):
        env.scripted_actions()
        env.step()
    kinds = env.order_tracks()["standing_kind"]
    assert (kinds[:, 1] == TRACK_DOCK).all(), "the pilot holds a dock order"
    dock_flag = rlf_sim.OBS_LAYOUT["dock"][0]
    assert (
        env.obs[:, 1, dock_flag] == 1.0
    ).all(), "and a v11 pilot sees the dock block"


def test_hidden_orders_hide_the_dock_block_but_the_order_stands() -> None:
    env = _env([GEN.dock(5)], hidden=True)
    for _ in range(ORDER_TICK + 2):
        env.scripted_actions()
        env.step()
    assert env.order_tracks()["standing_kind"][0, 1] == TRACK_DOCK
    assert env.obs[0, 1, rlf_sim.OBS_LAYOUT["dock"][0]] == 0.0


def test_the_script_docks_most_calm_drills_and_the_ledger_books_them() -> None:
    specs = list(GEN.dock_many(24, 9000, threat=False))
    records = run_pass(Scripted(), specs, 5, n_threads=THREADS)
    outcomes = [r.outcome for r in records]
    assert all(o is not None for o in outcomes)
    docked = [o for o in outcomes if o is not None and o.docked]
    assert len(docked) >= 20, f"the script docked {len(docked)} of 24"
    for record in records:
        o = record.outcome
        assert o is not None and o.kind == DRILL_DOCK and not o.threat
        assert o.base == record.spec.base
        if o.docked:
            assert o.pilots_lost == 0, "a docked pilot was not lost"
            assert 0 < o.docked_ticks <= record.spec.clock_ticks - ORDER_TICK
            # Nobody shoots in a calm drill; a bump on the way in still costs hull.
            assert 0.0 < o.dock_hull <= record.spec.start_hull_frac + 1e-4
            # Read before each step, against the ordered bay (a citadel takes a craft
            # through any of its four): near it, not necessarily inside.
            assert o.closest_m <= 60.0
    summary = summarise_dock(records, [])
    assert summary["docked"]["successes"] == len(docked)
    rates = (summary[k]["successes"] for k in ("docked", "shot_down", "timed_out"))
    assert sum(rates) == 24
    assert sum(part["n"] for part in summary["by_base"].values()) == 24
    assert summary["hidden"] is None and summary["lift"] is None


def test_a_threat_drill_fights_and_its_attackers_hurt_the_pilot() -> None:
    specs = list(GEN.dock_many(16, 9100, threat=True))
    records = run_pass(Scripted(), specs, 5, n_threads=THREADS)
    summary = summarise_dock(records, [])
    assert summary["shot_down"]["successes"] > 0, "the attackers are dangerous"
    assert summary["docked"]["successes"] > 0, "and the script still gets home"


def test_the_ledger_tells_a_dock_from_a_death_on_the_last_step() -> None:
    ledger = DrillLedger(1, 4)
    spec = GEN.dock(3)
    ledger.begin(0, spec.roster().drill)
    assert ledger.any_dock_running()
    obs = np.zeros((1, 4, rlf_sim.OBS_DIM), dtype=np.float32)
    obs[0, 1, SELF_HULL_COL] = 0.31
    # Inside the capture circle too fast, then out again: one fly-through.
    for dist in (40.0, 8.0, 14.0, 6.0):
        ledger.see_dock(np.array([[-1.0, dist, -1.0, -1.0]]), np.zeros((1, 4)), obs)
    docked = np.array([[False, True, False, False]])
    ledger.see_docks(docked, np.array([ORDER_TICK + 99]))
    alive_before = np.array([[True, True, True, False]])
    ledger.see_deaths(
        alive_before,
        np.ones((1, 4), dtype=np.bool_),
        np.array([True]),
        np.array([True]),
        np.zeros((1, 1, 6), dtype=np.int32),
        np.zeros(1, dtype=np.int32),
        np.zeros((1, 4), dtype=np.float32),
    )
    out = ledger.finish(0)
    assert out.docked and out.docked_ticks == 100 and out.pilots_lost == 0
    assert out.fly_throughs == 1
    assert out.dock_hull == pytest.approx(0.31)
    assert out.closest_m == 6.0
    assert not ledger.any_dock_running()


def test_the_dock_eval_has_its_own_gate_and_leaves_the_order_gate_alone() -> None:
    cfg = DrillEvalConfig(n_per_kind=8, kinds=(DOCK_CALM, DOCK_THREAT))
    result = evaluate(Scripted(), "script", cfg, n_threads=THREADS)
    assert set(result.kinds) == {DOCK_CALM, DOCK_THREAT}
    assert result.overall["core"] is None
    assert result.gate.verdict == REPORT_ONLY, "no order kind was played"
    assert result.dock_gate is not None and result.dock_gate.verdict == REPORT_ONLY
    assert set(result.dock_gate.measured) == set(DOCK_BAR_PATHS)
    assert result.dock_gate.measured["dock_calm_lift"] is None, "no hidden pass"
    report = result.to_markdown()
    assert "## Dock, alone (8 drills)" in report and "## Dock bars" in report
    bars = parse_bars(dict.fromkeys(DOCK_BAR_PATHS, 0.1))
    every = {**result.kinds, DOCK_CALM: {**result.kinds[DOCK_CALM], "lift": 0.5}}
    assert apply_gate(every, bars, "x", bar_paths=DOCK_BAR_PATHS).verdict == PASS
    with pytest.raises(ValueError, match="kinds"):
        DrillEvalConfig(kinds=("dock",))
    assert set(BAR_PATHS).isdisjoint(DOCK_BAR_PATHS)


def test_drill_dock_share_zero_draws_nothing_and_a_share_draws_dock_drills() -> None:
    base = PilotsDistribution(drill_share=0.5)
    plain = PilotsRosterSampler(base, 3).sample_many(60)
    same = PilotsRosterSampler(replace(base, drill_dock_threat_share=0.9), 3)
    assert same.sample_many(60) == plain, "the threat share draws nothing here"
    docks = PilotsRosterSampler(replace(base, drill_dock_share=0.6), 3).sample_many(300)
    kinds = [r.drill.kind for r in docks if r.drill is not None]
    share = kinds.count(DRILL_DOCK) / len(kinds)
    assert 0.5 < share < 0.7
    dock = next(r for r in docks if r.drill is not None and r.drill.kind == DRILL_DOCK)
    assert dock.mission in (CARRIER_BATTLE, STATION_ASSAULT) and dock.start_hull
    assert dock.klass == "drill/dock"
    calm = PilotsRosterSampler(
        replace(base, drill_dock_share=1.0, drill_dock_threat_share=0.0), 5
    ).sample_many(40)
    assert all(r.drill is not None and not r.drill.threat for r in calm if r.drill)
    with pytest.raises(ValueError, match="drill_dock_share"):
        PilotsDistribution(drill_dock_share=1.5)
    assert DEATHMATCH not in {
        r.mission for r in docks if r.drill and r.drill.kind == DRILL_DOCK
    }


def test_dock_bonus_is_a_trainer_key_left_out_of_the_config_at_its_default() -> None:
    plain = PPOConfig(init="scratch", tag="scratch")
    assert plain.dock_bonus == pytest.approx(float(rlf_sim.DOCK["bonus"]))
    assert "dock_bonus" not in plain.to_dict()
    paid = PPOConfig(init="scratch", tag="scratch", dock_bonus=1.5)
    assert paid.to_dict()["dock_bonus"] == 1.5
    assert PPOConfig.from_dict(paid.to_dict()).dock_bonus == 1.5
    for bad in (-1.0, math.inf, math.nan):
        with pytest.raises(ValueError, match="dock_bonus"):
            PPOConfig(init="scratch", tag="scratch", dock_bonus=bad)


def test_the_env_pays_the_configured_dock_bonus() -> None:
    env = RustVecEnv(ASSETS, 1, [["fighter"], ["fighter"]], 1, dock_bonus=0.75)
    assert env.dock_bonus == pytest.approx(0.75)
    with pytest.raises(ValueError, match="dock_bonus"):
        RustVecEnv(ASSETS, 1, [["fighter"], ["fighter"]], 1, dock_bonus=-0.5)


def test_the_tally_logs_dock_drills_and_mission_docks() -> None:
    tally = EpisodeTally()
    tally.add_drill(
        DrillOutcome(
            DRILL_DOCK,
            1,
            1,
            pilots=1,
            threat=False,
            base="carrier",
            docked_ticks=300,
            fly_throughs=1,
            dock_hull=0.4,
        )
    )
    tally.add_drill(
        DrillOutcome(
            DRILL_DOCK, 0, 1, pilots=1, pilots_lost=1, threat=True, base="station"
        )
    )
    tally.add_drill(
        DrillOutcome(DRILL_DOCK, 0, 1, pilots=1, threat=True, base="station")
    )
    tally.add_mission_docks("carrier_battle", 4, 2, hidden=False)
    tally.add_mission_docks("carrier_battle", 2, 0, hidden=False)
    tally.add_mission_docks("carrier_battle", 3, 0, hidden=True)
    out = tally.log_fields()
    assert out["drill_success"] == {"dock": pytest.approx(1 / 3)}
    calm, threat = out["drill_dock"]["calm"], out["drill_dock"]["threat"]  # type: ignore[index]
    assert calm["docked"] == 1.0 and calm["seconds_to_dock"] == 10.0
    assert calm["hull_at_dock"] == pytest.approx(0.4) and calm["fly_throughs"] == 1.0
    assert threat["shot_down"] == 0.5 and threat["timed_out"] == 0.5
    assert threat["docked_of_survivors"] == 0.0
    carrier = out["mission_docks"]["carrier_battle"]  # type: ignore[index]
    assert carrier == {
        "episodes": 2,
        "recalls_per_match": 3.0,
        "docks_per_match": 1.0,
        "completion": pytest.approx(1 / 3),
    }
    assert out["mission_docks_hidden"]["recalls_per_match"] == 3.0  # type: ignore[index]
    assert "dock" not in out["drill_sides"]  # type: ignore[operator]
