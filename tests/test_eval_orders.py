"""Order-following eval metrics on synthetic traces, the mission eval, the order
gates and the export of pilots narrower than the sim (M3 stage B)."""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest
import rlf_sim
import torch

from spacefight.env.rosters import CARRIER_BATTLE, CONVOY_ESCORT, SCRIPTED
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval import order_gates as G
from spacefight.eval.controllers import Scripted
from spacefight.eval.fleet import FleetResult
from spacefight.eval.missions import (
    MissionEvalConfig,
    MissionResult,
    MissionSummary,
    SideMetrics,
    build_mission_env,
    evaluate as evaluate_missions,
)
from spacefight.eval.orders import (
    ATTACK,
    GUARD,
    HOLD,
    NO_TARGET,
    NONE,
    FollowSummary,
    KindSummary,
    OrdersEvalConfig,
    OrdersResult,
    OrderTracker,
    Timing,
    censored_median,
    ship_orders,
    summarise,
)
from spacefight.rl.spike_policy import (
    OBS_DIM,
    ORDER_OBS_DIM,
    SpikeActor,
    SpikeCritic,
    save_policy,
    widen_actor,
)
from tools.export_policy import ExportError, export

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"
FLEET_EVAL = REPO / "lab/runs/2026-10-30-fleet-pilot/eval"


# ------------------------------------------------------------------ tracker


def _tick(
    tracker: OrderTracker,
    n_slots: int,
    *,
    live: tuple[bool, ...] | None = None,
    dist: float = 500.0,
    margin: float = 400.0,
    angle_deg: float = 90.0,
    gun_range: float = 200.0,
    level: float = 0.5,
    kind: int = NONE,
) -> None:
    """One tick where slot 0 measures the given values (other slots idle)."""
    shape = (1, n_slots)
    alive = np.ones(shape, dtype=bool) if live is None else np.array([live])
    tracker.step(
        alive,
        np.full(shape, dist),
        np.full(shape, margin),
        np.full(shape, math.radians(angle_deg)),
        np.full(shape, gun_range),
        np.full(shape, level),
        np.full(shape, kind),
    )


def _begin(tracker: OrderTracker, kind: int, target: int = NO_TARGET) -> None:
    changed = np.array([[True, False, False]])
    tracker.begin(
        changed, np.full((1, 3), kind), np.full((1, 3), target, dtype=np.int64)
    )


def test_attack_instance_measures_close_response_and_damage_share() -> None:
    measured = np.array([[True, False, False]])
    tracker = OrderTracker(measured, np.array([[3, 3, 3]]))
    _begin(tracker, ATTACK, target=1)
    # Ticks 0-4: closing from 240 m, the nose comes round at tick 2, in gun range
    # (200 m) at tick 3.
    for t, (dist, angle) in enumerate(
        [(240, 80), (230, 50), (220, 20), (190, 5), (180, 5)]
    ):
        _tick(tracker, 3, dist=dist, margin=dist, angle_deg=angle, kind=ATTACK)
        if t == 3:
            env = np.array([0, 0, 0])
            tracker.add_damage(
                env,
                np.array([0, 0, 1]),
                np.array([1, 2, 0]),
                np.array([30.0, 10.0, 99.0]),
            )
    _begin(tracker, GUARD, target=2)  # the attack instance ends here
    for margin in (20.0, -5.0, -1.0, 3.0):
        _tick(tracker, 3, margin=margin, angle_deg=10.0, kind=GUARD)
    tracker.finish()
    d = tracker.done.arrays()
    assert d["kind"].tolist() == [ATTACK, GUARD]
    assert d["close_tick"].tolist()[0] == 3
    assert d["response_tick"].tolist() == [2, 0]
    assert d["live_ticks"].tolist() == [5, 4]
    assert d["inside_ticks"].tolist() == [0, 2]
    assert d["damage_total"].tolist()[0] == pytest.approx(40.0)
    assert d["damage_target"].tolist()[0] == pytest.approx(30.0)
    out = summarise(tracker.done, tracker.duty_sum, tracker.duty_ticks, {3: "fighter"})
    assert out.attack.damage_share == pytest.approx(0.75)
    assert out.attack.close == Timing(1, 3.0, 1.0)
    assert out.attack.target_damage_per_min == pytest.approx(30.0 / (5 / 30 / 60))
    assert out.guard.time_inside == pytest.approx(0.5)
    assert out.response.n == 2  # both start outside their radius
    assert out.engine_duty["fighter"] == {"attack": 0.5, "guard": 0.5}


def test_instances_close_on_death_and_unlived_orders_are_dropped() -> None:
    tracker = OrderTracker(np.array([[True, False, False]]), np.zeros((1, 3), int))
    _begin(tracker, HOLD)
    _tick(tracker, 3, live=(False, True, True), margin=50.0)  # docked: not started
    _begin(tracker, ATTACK, target=1)  # replaces the hold, which is dropped
    _tick(tracker, 3, dist=100.0, margin=100.0, angle_deg=60.0)
    _tick(tracker, 3, live=(False, True, True))  # dies
    _tick(tracker, 3, live=(False, True, True))
    tracker.finish()
    d = tracker.done.arrays()
    assert d["kind"].tolist() == [ATTACK]
    assert d["live_ticks"].tolist() == [1]
    assert d["response_tick"].tolist() == [-1]
    assert d["close_tick"].tolist() == [0]  # 100 m < 200 m gun range


def test_unmeasured_slots_and_none_orders_open_nothing() -> None:
    tracker = OrderTracker(np.array([[True, False, False]]), np.zeros((1, 3), int))
    tracker.begin(
        np.ones((1, 3), bool), np.array([[NONE, ATTACK, GUARD]]), np.zeros((1, 3), int)
    )
    _tick(tracker, 3)
    tracker.finish()
    assert tracker.done.kind == []


def test_censored_medians_treat_never_as_last() -> None:
    assert censored_median(np.array([5, -1, 10])) == Timing(3, 10.0, 2 / 3)
    assert censored_median(np.array([-1, -1, 3])) == Timing(3, None, 1 / 3)
    assert censored_median(np.zeros(0, dtype=np.int64)) == Timing(0, None, 0.0)


def test_ship_orders_reads_squads_from_mission_state() -> None:
    roster = rlf_sim.mission_rosters(CONVOY_ESCORT)[0]
    env = rlf_sim.VecEnv(
        str(ASSETS),
        1,
        roster["fleets"],
        0,
        max_ships=18,
        mission=CONVOY_ESCORT,
        time_limit_s=120.0,
    )
    for _ in range(130):
        env.scripted_actions()
        env.step()
    state = env.mission_state(0)
    kind, target, keys = ship_orders(state, 18)
    for team in state["squads"]:
        for squad in team:
            for m in squad["members"]:
                order = squad["order"]
                assert kind[m] == ["none", "attack", "guard", "hold"].index(
                    order["kind"]
                )
                if order["kind"] in ("attack", "guard"):
                    assert target[m] == order.get("target", order.get("ward"))
    transports = [s["slot"] for s in state["ships"] if s["role"] == "transport"]
    assert all(kind[t] == NONE for t in transports)
    assert len(set(keys)) >= 2


def test_orders_result_round_trips_through_json() -> None:
    result = _orders_result(guard=0.6, hold=0.5, share=0.4, close=100.0, response=50.0)
    assert OrdersResult.from_json(result.to_json()) == result


# ------------------------------------------------------------------ missions


def test_mission_env_balances_rosters_and_sides() -> None:
    me = build_mission_env(CARRIER_BATTLE, 12, 0, SCRIPTED, n_threads=2)
    assert me.env.n_envs == 12
    for k in range(len(me.names)):
        sides = me.a_team[me.entry == k]
        assert sorted(sides.tolist()) == [0, 0, 1, 1]
    carrier_slots = me.capital.sum(axis=1)
    assert (carrier_slots == 2).all()
    with pytest.raises(ValueError, match="multiple"):
        build_mission_env(CARRIER_BATTLE, 8, 0, SCRIPTED, n_threads=2)


def test_mission_eval_script_vs_script_is_even_and_round_trips() -> None:
    cfg = MissionEvalConfig(missions=(CONVOY_ESCORT,), n_per_mission=12, seed=7)
    result = evaluate_missions(Scripted(), Scripted(), cfg, n_threads=2)
    m = result.missions[CONVOY_ESCORT]
    assert m.n == 12
    assert m.win_rate + m.side_b.win_rate == pytest.approx(1.0)
    assert sum(m.end_reasons.values()) == pytest.approx(1.0)
    assert set(m.side_a.hulls) <= {"fighter", "strafer", "gunship"}
    assert MissionResult.from_json(result.to_json()) == result


# ------------------------------------------------------------------ gates


def _kind(
    share: float = 0.0,
    close: float | None = None,
    inside: float = 0.0,
    response: float | None = 50.0,
) -> KindSummary:
    return KindSummary(
        instances=100,
        live_ticks=10_000,
        response=Timing(100, response, 0.9),
        close=Timing(80, close, 0.9),
        damage_share=share,
        target_damage_per_min=10.0,
        time_inside=inside,
    )


def _follow(
    guard: float, hold: float, share: float, close: float | None, response: float | None
) -> FollowSummary:
    return FollowSummary(
        attack=_kind(share=share, close=close, response=response),
        guard=_kind(inside=guard, response=response),
        hold=_kind(inside=hold, response=response),
        response=Timing(300, response, 0.9),
        engine_duty={"fighter": {"none": 0.2, "attack": 0.4}},
        duty_ticks={"fighter": {"none": 100, "attack": 100}},
    )


def _orders_result(**kw: float | None) -> OrdersResult:
    f = _follow(kw["guard"], kw["hold"], kw["share"], kw["close"], kw["response"])  # type: ignore[arg-type]
    return OrdersResult(
        a="x",
        b="script",
        config=OrdersEvalConfig(),
        scenarios={"carrier_battle/random": f},
        by_commander={"random": f, "scripted": f},
    )


def _mission_result(
    win: dict[str, float], time_limit: float = 0.0, stalemate: float = 0.0
) -> MissionResult:
    cfg = MissionEvalConfig()
    side = _side()
    missions = {
        name: dataclasses.replace(
            _MISSION_TEMPLATE,
            mission=name,
            win_rate=w,
            time_limit_rate=time_limit,
            stalemate_rate=stalemate,
            side_a=side,
            side_b=side,
        )
        for name, w in win.items()
    }
    return MissionResult("x", "v1", cfg, missions, float(np.mean(list(win.values()))))


def _side() -> SideMetrics:
    fleet = FleetResult.from_json(
        (FLEET_EVAL / "warm_400_fleet_vs_script.json").read_text()
    )
    return SideMetrics(0.5, fleet.side_a.all_ships, {}, 0, 0)


def _template() -> MissionSummary:
    side = _side()
    return MissionSummary(
        mission="",
        n=516,
        time_limit_s=150.0,
        win_rate=0.5,
        win_rate_team0=0.5,
        win_rate_team1=0.5,
        win_rate_by_roster={},
        draw_rate=0.0,
        time_limit_rate=0.0,
        stalemate_rate=0.0,
        end_reasons={},
        length_median_s=100.0,
        length_p90_s=140.0,
        side_a=side,
        side_b=side,
    )


_MISSION_TEMPLATE = _template()


@pytest.fixture(scope="module")
def baselines() -> G.Baselines:
    v1_fleet = FleetResult.from_json(
        (FLEET_EVAL / "warm_400_fleet_vs_script.json").read_text()
    )
    return G.Baselines(
        v1_orders=_orders_result(
            guard=0.30, hold=0.20, share=0.40, close=120.0, response=60.0
        ),
        v1_missions=_mission_result(
            {CARRIER_BATTLE: 0.5, CONVOY_ESCORT: 0.5}, time_limit=0.02, stalemate=0.01
        ),
        v1_fleet_vs_script=v1_fleet,
    )


def _evals(orders: OrdersResult, missions: MissionResult) -> G.Evals:
    fleet = FleetResult.from_json(
        (FLEET_EVAL / "warm_400_fleet_vs_script.json").read_text()
    )
    ref = FleetResult.from_json((FLEET_EVAL / "warm_600_fleet_vs_ref.json").read_text())
    return G.Evals(orders, missions, fleet, ref)


def test_a_following_candidate_passes_and_is_picked(baselines: G.Baselines) -> None:
    good = _evals(
        _orders_result(guard=0.60, hold=0.50, share=0.55, close=100.0, response=40.0),
        _mission_result({CARRIER_BATTLE: 0.55, CONVOY_ESCORT: 0.53}),
    )
    report = G.check("good", good, baselines)
    assert G.failures(report) == []
    weaker = _evals(
        _orders_result(guard=0.60, hold=0.50, share=0.55, close=100.0, response=40.0),
        _mission_result({CARRIER_BATTLE: 0.53, CONVOY_ESCORT: 0.52}),
    )
    other = G.check("weaker", weaker, baselines)
    assert G.pick([other, report]) == "good"
    assert "good" in G.markdown([report, other])


def test_gates_fail_where_the_plan_says(baselines: G.Baselines) -> None:
    bad = _evals(
        # guard gain 0.10 < 0.15 (random), response never reached, no closing
        _orders_result(guard=0.40, hold=0.50, share=0.55, close=None, response=None),
        _mission_result(
            {CARRIER_BATTLE: 0.46, CONVOY_ESCORT: 0.60}, time_limit=0.20, stalemate=0.01
        ),
    )
    failed = {c.name for c in G.check("bad", bad, baselines).checks if not c.passed}
    assert {
        "random: guard time inside",
        "random: response median ticks",
        "random: attack median ticks to gun range",
        "carrier_battle: win vs v1",
        "carrier_battle: time-limit rate",
    } <= failed
    assert "mean mission win vs v1" not in failed  # 0.53 >= 0.52
    assert G.pick([G.check("bad", bad, baselines)]) is None


# ------------------------------------------------------------------ export


def _stamped(path: Path, actor: SpikeActor, version: int) -> None:
    save_policy(
        path, actor, SpikeCritic(obs_dim=actor.obs_dim), {"sim_version": version}
    )


def test_export_flies_a_v1_width_pilot_in_an_order_sim(tmp_path: Path) -> None:
    torch.manual_seed(0)
    _stamped(tmp_path / "v1.pt", SpikeActor(), 3)
    manifest = export(
        tmp_path / "v1.pt",
        tmp_path / "out",
        wasm_sim_version=5,
        wasm_obs_dim=ORDER_OBS_DIM,
        wasm_pilot_compat=[3, 4, 5],
    )
    assert manifest["obs_dim"] == OBS_DIM and manifest["sim_obs_dim"] == ORDER_OBS_DIM
    assert manifest["layers"][0]["in"] == OBS_DIM


def test_export_takes_a_403_wide_pilot_and_refuses_mismatches(tmp_path: Path) -> None:
    wide = widen_actor(SpikeActor(), ORDER_OBS_DIM)
    _stamped(tmp_path / "wide.pt", wide, 5)
    manifest = export(
        tmp_path / "wide.pt",
        tmp_path / "out",
        wasm_sim_version=5,
        wasm_obs_dim=ORDER_OBS_DIM,
        wasm_pilot_compat=[3, 4, 5],
    )
    assert manifest["obs_dim"] == ORDER_OBS_DIM
    with pytest.raises(ExportError, match="pilot-compatible"):  # a v5 pilot in v4
        export(
            tmp_path / "wide.pt",
            tmp_path / "o2",
            wasm_sim_version=4,
            wasm_obs_dim=OBS_DIM,
            wasm_pilot_compat=[3, 4],
        )
    _stamped(tmp_path / "odd.pt", SpikeActor(), 5)  # v5 stamp, 385 wide
    with pytest.raises(ExportError, match="obs_dim"):
        export(
            tmp_path / "odd.pt",
            tmp_path / "o3",
            wasm_sim_version=5,
            wasm_obs_dim=ORDER_OBS_DIM,
            wasm_pilot_compat=[3, 4, 5],
        )


def test_mission_env_takes_roster_commanders_on_v5_only() -> None:
    from spacefight.env import rust_env

    if rust_env.ORDERS_SUPPORTED:
        me = build_mission_env(CARRIER_BATTLE, 6, 0, "random", n_threads=2)
        assert isinstance(me.env, RustVecEnv)
    else:
        with pytest.raises(ValueError):
            build_mission_env(CARRIER_BATTLE, 6, 0, "random", n_threads=2)
