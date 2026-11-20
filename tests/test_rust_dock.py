"""rlf_sim v11 dock and repair from Python (SIM_SPEC §0.9, §5.11, §10.1): the constants
and event kinds, ``VecEnv.dock_state()``, the ``docking`` kwarg (off plays a v10 match),
recalls by the scripted commander only, the ``dock`` command, and the wrapper's
passthrough."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rlf_sim

from spacefight.env.rust_env import RustVecEnv

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
WING_8 = rlf_sim.mission_rosters("carrier_battle")[0]["fleets"]
CARRIER_S = rlf_sim.mission_time_limit_s("carrier_battle")
EV = rlf_sim.EVENT_KINDS


def _carrier_env(n: int, seed: int, **kw: object) -> rlf_sim.VecEnv:
    return rlf_sim.VecEnv(
        ASSETS,
        n,
        WING_8,
        seed,
        time_limit_s=CARRIER_S,
        n_threads=2,
        record_events=True,
        mission="carrier_battle",
        **kw,
    )


def _run(env: rlf_sim.VecEnv, steps: int) -> dict[int, int]:
    """Step with scripted pilots for ``steps`` (matches auto-reset); count events by
    kind."""
    counts: dict[int, int] = {}
    for _ in range(steps):
        env.scripted_actions()
        env.step()
        for k in env.events()[:, 1].astype(int):
            counts[k] = counts.get(k, 0) + 1
    return counts


def test_v11_constants_and_event_kinds() -> None:
    assert rlf_sim.SIM_VERSION == 11
    assert 11 in rlf_sim.PILOT_COMPAT_VERSIONS
    assert rlf_sim.PILOT_OBS_DIMS[11] == rlf_sim.OBS_DIM == 592
    assert rlf_sim.OBS_DIM_V10 == 587
    assert dict(rlf_sim.OBS_LAYOUT)["dock"] == (587, 5)
    assert [EV[k] for k in ("dock_ordered", "docked", "repaired", "relaunched")] == [
        15,
        16,
        17,
        18,
    ]
    assert EV["dock_aborted"] == 19
    assert list(rlf_sim.DOCK_PHASES) == ["none", "inbound", "repairing", "ready"]
    dock = rlf_sim.DOCK
    assert dock["capture_radius"] == 10.0 and dock["max_rel_speed"] == 15.0
    assert dock["turnaround_ticks"] == 120
    assert 0 < dock["recall_hull_frac"] < 1
    assert 0 < dock["repair_frac_per_s"] < 1


def test_dock_state_shapes_and_a_carrier_battle_docks_and_relaunches() -> None:
    env = _carrier_env(8, 61)
    assert env.docking
    ds = env.dock_state()
    s = env.n_ships
    assert ds["phase"].shape == (8, s) and ds["phase"].dtype == np.int8
    assert ds["point"].shape == (8, s, 2)
    assert ds["live"].all()
    assert (ds["bay"] == -1).all() and (ds["dist"] == -1).all()
    counts = _run(env, 3000)
    assert counts.get(EV["dock_ordered"], 0) > 0
    assert counts.get(EV["docked"], 0) > 0
    assert counts.get(EV["relaunched"], 0) > 0
    assert counts.get(EV["relaunched"], 0) <= counts.get(EV["docked"], 0)


def test_inbound_ships_report_their_bay_and_approach() -> None:
    env = _carrier_env(8, 7)
    for _ in range(3000):
        env.scripted_actions()
        env.step()
        ds = env.dock_state()
        inbound = ds["phase"] == rlf_sim.DOCK_PHASES.index("inbound")
        if inbound.any():
            assert (ds["bay"][inbound] >= 0).all()
            assert (ds["dist"][inbound] >= 0).all()
            assert (ds["rel_speed"][inbound] >= 0).all()
            assert (ds["since"][inbound] > 0).all()
            i, k = np.argwhere(inbound)[0]
            ship = env.render_state(int(i))["ships"][int(k)]
            assert ship["dock_phase"] == "inbound" and ship["present"]
            return
    raise AssertionError("no ship was recalled")


def test_docking_off_plays_the_v10_match_and_never_docks() -> None:
    env = _carrier_env(4, 61, docking=False)
    assert not env.docking
    assert not env.dock_state()["live"].any()
    counts = _run(env, 2000)
    for k in ("dock_ordered", "docked", "relaunched"):
        assert counts.get(EV[k], 0) == 0


def test_only_a_commander_recalls_and_an_external_dock_command_works() -> None:
    # A learned commander has no recall output: nobody is recalled, the sim recalls
    # nobody on its own.
    env = _carrier_env(4, 61, commanders=["learned", "learned"])
    assert env.docking
    counts = _run(env, 1500)
    assert counts.get(EV["dock_ordered"], 0) == 0
    # An external commander's dock command for a ship on the field.
    ext = _carrier_env(1, 61, commanders=["external", "external"])
    for _ in range(200):
        ext.step()
    phase = ext.dock_state()["phase"]
    state = ext.render_state(0)
    on_field = [
        s["slot"]
        for s in state["ships"]
        if s["team"] == 0 and s["present"] and s["role"] != "carrier"
    ]
    assert on_field, "a strike craft jumped in"
    ext.submit_command(0, 0, {"kind": "dock", "ship": on_field[0]})
    while not ext.command_due()[0]:
        ext.step()
    ext.step()
    result = ext.command_results(0, 0)[0]
    assert result["command"] == "dock" and result["outcome"] == "applied"
    phase = ext.dock_state()["phase"]
    assert phase[0, on_field[0]] == rlf_sim.DOCK_PHASES.index("inbound")
    view = ext.mission_state(0)["ships"][on_field[0]]
    assert view["dock"]["phase"] == "inbound" and view["dock"]["bay"] in (0, 1)
    with pytest.raises(ValueError):
        ext.submit_command(0, 0, {"kind": "dock"})


def test_a_deathmatch_has_no_dock_state() -> None:
    env = rlf_sim.VecEnv(ASSETS, 2, [["fighter"], ["fighter"]], 3, n_threads=1)
    assert not env.dock_state()["live"].any()
    assert "dock" not in env.mission_state(0)["ships"][0]


def test_the_wrapper_passes_the_dock_kwargs_through() -> None:
    env = RustVecEnv(
        ASSETS,
        2,
        WING_8,
        5,
        time_limit_s=CARRIER_S,
        n_threads=1,
        max_ships=len(WING_8[0]) + len(WING_8[1]),
        docking=False,
    )
    assert not env.docking
    ds = env.dock_state()
    assert set(ds) >= {
        "phase",
        "bay",
        "since",
        "docked_at",
        "ready_at",
        "live",
        "point",
    }


def test_there_is_no_recall_doctrine_switch() -> None:
    # The owner's call (2026-11-20): no sim-side recall of any kind, so no switch.
    with pytest.raises(TypeError):
        _carrier_env(1, 3, recall_doctrine=False)
    assert "relaunch_hull_frac" in rlf_sim.DOCK
