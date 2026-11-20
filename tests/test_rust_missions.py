"""rlf_sim v4 missions from Python: carrier battle and convoy escort with the stub
commander, the end-reason buffer, External commands, and the commander views
(SIM_SPEC §5.9, §5.10, §10.1); v9's station assault and its obs mapping; v10's citadel,
dreadnought and hardpoints."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rlf_sim

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")

CARRIER_FLEET = [
    "carrier",
    "fighter",
    "strafer",
    "fighter",
    "gunship",
    "fighter",
    "fighter",
]
CONVOY = [
    ["freighter"] * 4 + ["fighter", "strafer", "fighter"],
    ["fighter", "fighter", "strafer", "gunship", "fighter", "strafer"],
]
REASONS = list(rlf_sim.END_REASONS)


def _run_to_end(env: rlf_sim.VecEnv, max_steps: int) -> tuple[np.ndarray, np.ndarray]:
    """Step with scripted pilots until every match has finished once."""
    n = env.n_envs
    winner = np.full(n, -2, dtype=np.int8)
    reason = np.zeros(n, dtype=np.int8)
    for _ in range(max_steps):
        env.scripted_actions()
        env.step()
        new = env.dones & (winner == -2)
        winner[new] = env.winner[new]
        reason[new] = env.end_reason[new]
        if (winner != -2).all():
            return winner, reason
    raise AssertionError(f"matches did not end within {max_steps} steps")


def test_mission_constants() -> None:
    # v9 appends the station assault; the first three keep their codes.
    assert list(rlf_sim.MISSIONS) == [
        "deathmatch",
        "carrier_battle",
        "convoy_escort",
        "station_assault",
    ]
    assert REASONS[0] == "not_over"
    assert REASONS[6:] == ["station_destroyed", "assault_repelled"]
    assert list(rlf_sim.STATION_READS_AS) == ["carrier", "convoy"]
    assert rlf_sim.mission_time_limit_s("station_assault") == 150.0
    assert rlf_sim.COMMAND_TICKS == 60
    assert rlf_sim.mission_time_limit_s("carrier_battle") == 150.0
    assert rlf_sim.arena_radius_for_mission("convoy_escort", 13) == 450.0
    with pytest.raises(ValueError):
        rlf_sim.mission_time_limit_s("duel")


def test_deathmatch_default_reports_its_end_reason() -> None:
    env = rlf_sim.VecEnv(ASSETS, 4, [["fighter"], ["fighter"]], 3, n_threads=2)
    _, reason = _run_to_end(env, 3000)
    assert set(REASONS[r] for r in reason) <= {"eliminated", "time_limit"}
    assert env.mission_state(0)["mission"] == "deathmatch"


def test_carrier_battle_ends_with_a_carrier_kill_deterministically() -> None:
    def run() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        env = rlf_sim.VecEnv(
            ASSETS,
            4,
            [CARRIER_FLEET, CARRIER_FLEET],
            23,
            time_limit_s=rlf_sim.mission_time_limit_s("carrier_battle"),
            n_threads=2,
            mission="carrier_battle",
            record_events=True,
        )
        assert env.n_ships == 14
        state = env.mission_state(0)
        assert all(c >= 0 for c in state["carrier"])
        assert [len(h) for h in state["hangar"]] == [4, 4]
        winner, reason = _run_to_end(env, 4600)
        return winner, reason, env.state_hash()

    a, b = run(), run()
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)
    reasons = {REASONS[r] for r in a[1]}
    assert reasons <= {"carrier_destroyed", "time_limit"}
    assert "carrier_destroyed" in reasons


def test_convoy_escort_ends_with_the_convoy() -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        4,
        CONVOY,
        29,
        time_limit_s=rlf_sim.mission_time_limit_s("convoy_escort"),
        n_threads=2,
        mission={"kind": "convoy_escort", "charge_ticks": 45},
    )
    convoy = env.mission_state(0)["convoy"]
    assert convoy["total"] == 4 and convoy["charge_ticks"] == 45
    winner, reason = _run_to_end(env, 3700)
    for w, r in zip(winner, reason):
        name = REASONS[r]
        assert name in {
            "convoy_through",
            "convoy_destroyed",
            "eliminated",
            "time_limit",
        }
        assert w == (0 if name in {"convoy_through", "eliminated"} else 1)


def test_external_commander_launches_and_orders() -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        2,
        [CARRIER_FLEET, CARRIER_FLEET],
        5,
        mission="carrier_battle",
        commanders=["external", "scripted"],
    )
    while not env.command_due()[0]:
        env.step()
    carrier1 = env.mission_state(0)["carrier"][1]
    env.submit_command(
        0,
        0,
        [
            {"kind": "launch", "hull": "gunship"},
            {"kind": "launch", "bay": 9},
            {
                "kind": "squad",
                "squad": 1,
                "members": [1, 2],
                "order": {"kind": "attack", "target": carrier1},
            },
            {"kind": "waypoint", "ship": 0, "pos": [-200.0, 50.0]},
        ],
    )
    env.step()
    results = env.command_results(0, 0)
    assert [r["outcome"] for r in results] == [
        "launched",
        "refused",
        "applied",
        "applied",
    ]
    assert results[1]["reason"] == "no_such_bay"
    launched = results[0]["ship"]
    ship = env.render_state(0)["ships"][launched]
    assert ship["hull"] == "gunship" and ship["present"] and not ship["docked"]
    state = env.mission_state(0)
    assert state["squads"][0][1]["members"] == [1, 2]
    assert state["squads"][0][1]["order"] == {"kind": "attack", "target": carrier1}
    assert state["ships"][0]["waypoint"] == [-200.0, 50.0]
    # The scripted team 1 commanded too; env 1 got no external commands.
    assert env.command_results(1, 0) == []
    assert any(r["outcome"] == "launched" for r in env.command_results(0, 1))
    obs = env.commander_obs(0, 0)
    assert obs["mission"] == "carrier_battle"
    assert obs["reserves"] == {"fighter": 3}
    assert obs["own_carrier"]["hull"] == "carrier"
    with pytest.raises(ValueError, match="unknown hull"):
        env.submit_command(0, 0, {"kind": "launch", "hull": "battlecruiser"})
    with pytest.raises(ValueError):
        env.submit_command(0, 0, {"kind": "teleport"})
    with pytest.raises(ValueError, match="team"):
        env.submit_command(0, 2, {"kind": "launch"})


def test_missions_can_be_queued_per_env() -> None:
    env = rlf_sim.VecEnv(ASSETS, 2, [["fighter"], ["fighter"]], 1, max_ships=14)
    env.set_next_roster(
        1, [CARRIER_FLEET, CARRIER_FLEET], 450.0, mission="carrier_battle"
    )
    with pytest.raises(ValueError, match="carrier"):
        env.set_next_roster(
            0, [["fighter"], ["fighter"]], 450.0, mission="carrier_battle"
        )
    env.reset()
    assert env.mission_state(0)["mission"] == "deathmatch"
    assert env.mission_state(1)["mission"] == "carrier_battle"
    roles = [s["role"] for s in env.render_state(1)["ships"]]
    assert roles.count("carrier") == 2


# -- SIM_VERSION 5: the order block, the order reward, the random commander, and
# -- per-roster commanders and clocks (SIM_SPEC §0.3, §5.9, §7.2, §8, §10.1).

ORDER_OFF, ORDER_W = rlf_sim.OBS_LAYOUT["order"]
TRAIN_CARRIER = ["carrier", "fighter", "fighter", "strafer", "gunship"]


def test_v5_constants_and_pilot_obs_dims() -> None:
    assert rlf_sim.SIM_VERSION == 11
    assert (ORDER_OFF, ORDER_W) == (385, 18)
    assert rlf_sim.OBS_DIM_V5 == ORDER_OFF + ORDER_W
    assert rlf_sim.PILOT_OBS_DIMS == {
        3: 385,
        4: 385,
        5: 403,
        6: 583,
        7: 583,
        8: 587,
        9: 587,
        10: 587,
        11: 587,
    }
    assert set(rlf_sim.PILOT_OBS_DIMS) == set(rlf_sim.PILOT_COMPAT_VERSIONS)
    assert rlf_sim.MAX_TRAIN_SHIPS == 12


def test_random_commander_gives_orders_that_pilots_see() -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        4,
        [TRAIN_CARRIER, TRAIN_CARRIER],
        9,
        mission="carrier_battle",
        commanders=["random", "random"],
        time_limit_s=rlf_sim.mission_time_limit_s("carrier_battle"),
        max_ships=rlf_sim.MAX_TRAIN_SHIPS,
        n_threads=2,
    )
    assert env.mission_state(0)["commanders"] == ["random", "random"]
    order_rewards = env.order_rewards
    assert order_rewards.shape == (4, 12) and order_rewards.dtype == np.float32
    seen_kinds: set[int] = set()
    nonzero = False
    for _ in range(900):
        env.scripted_actions()
        env.step()
        assert env.order_rewards is order_rewards
        block = env.obs[..., ORDER_OFF : ORDER_OFF + ORDER_W]
        has = block[..., 0] == 1.0
        # A ship with an order has exactly one kind; one without has an all-zero block.
        assert np.all(block[has][:, 1:4].sum(axis=1) == 1.0)
        assert np.all(block[~has] == 0.0)
        for k in range(3):
            if np.any(block[has][:, 1 + k] == 1.0):
                seen_kinds.add(k)
        nonzero |= bool(np.any(env.order_rewards != 0.0))
        # Padding slots earn nothing.
        assert np.all(env.order_rewards[env.team < 0] == 0.0)
    assert seen_kinds == {0, 1, 2}
    assert nonzero


def test_random_commander_is_deterministic() -> None:
    def run() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        env = rlf_sim.VecEnv(
            ASSETS,
            3,
            CONVOY,
            4,
            mission="convoy_escort",
            commanders=["random", "random"],
            n_threads=2,
        )
        obs, order_rewards = [], []
        for _ in range(400):
            env.scripted_actions()
            env.step()
            obs.append(env.obs[..., ORDER_OFF:].copy())
            order_rewards.append(env.order_rewards.copy())
        return np.stack(obs), np.stack(order_rewards), env.state_hash()

    a, b = run(), run()
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)


def test_set_next_roster_takes_commanders_and_a_clock() -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        3,
        [["fighter"], ["fighter"]],
        2,
        time_limit_s=60.0,
        max_ships=12,
    )
    env.set_next_roster(
        0,
        [TRAIN_CARRIER, TRAIN_CARRIER],
        450.0,
        mission="carrier_battle",
        commanders=["random", "scripted"],
    )
    env.set_next_roster(
        1, [["fighter"], ["fighter", "strafer"]], 450.0, time_limit_s=30.0
    )
    env.set_next_roster(
        2, [["fighter"], ["fighter"]], 450.0, commanders=["random", "random"]
    )
    with pytest.raises(ValueError, match="commander"):
        env.set_next_roster(
            2, [["fighter"], ["fighter"]], 450.0, commanders=["robot", "scripted"]
        )
    with pytest.raises(ValueError, match="two"):
        env.set_next_roster(2, [["fighter"], ["fighter"]], 450.0, commanders=["random"])
    with pytest.raises(ValueError, match="time_limit_s"):
        env.set_next_roster(2, [["fighter"], ["fighter"]], 450.0, time_limit_s=-1.0)
    env.reset()
    s0, s1, s2 = (env.mission_state(i) for i in range(3))
    # A mission without a clock gets the mission's own; none at all, the env's.
    assert s0["commanders"] == ["random", "scripted"]
    assert s0["time_limit_ticks"] == round(
        rlf_sim.mission_time_limit_s("carrier_battle") * 30
    )
    assert (s1["commanders"], s1["time_limit_ticks"]) == (["scripted", "scripted"], 900)
    assert (s2["commanders"], s2["time_limit_ticks"]) == (["random", "random"], 1800)
    # The roster's commanders and clock stick through auto-resets: env 1 ends at 30 s.
    for _ in range(901):
        env.scripted_actions()
        env.step()
    assert env.episode_count[1] >= 1
    assert env.mission_state(1)["time_limit_ticks"] == 900
    assert env.mission_state(0)["commanders"] == ["random", "scripted"]
    explicit = rlf_sim.VecEnv(ASSETS, 1, [["fighter"], ["fighter"]], 2, max_ships=12)
    explicit.set_next_roster(
        0,
        [TRAIN_CARRIER, TRAIN_CARRIER],
        450.0,
        mission="carrier_battle",
        time_limit_s=20.0,
    )
    explicit.reset()
    assert explicit.mission_state(0)["time_limit_ticks"] == 600


STATION = rlf_sim.mission_rosters("station_assault")[0]["fleets"]


def _mission_one_hot(env: rlf_sim.VecEnv, slot: int) -> list[float]:
    """The order block's mission one-hot of ``slot`` in env 0 (zero without an order)."""
    offset, _ = rlf_sim.OBS_LAYOUT["order"]
    return [float(x) for x in env.obs[0, slot, offset + 15 : offset + 18]]


@pytest.mark.parametrize(("reads_as", "index"), [("carrier", 1), ("convoy", 2)])
def test_station_assault_reads_as_its_mapping(reads_as: str, index: int) -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        2,
        STATION,
        43,
        time_limit_s=rlf_sim.mission_time_limit_s("station_assault"),
        n_threads=2,
        mission={"kind": "station_assault", "as": reads_as},
    )
    state = env.mission_state(0)
    assert state["mission"] == "station_assault"
    assert state["reads_as"] == (
        "carrier_battle" if reads_as == "carrier" else "convoy_escort"
    )
    assert state["carrier"][0] == 0  # the station is team 0's carrier
    # Two on picket, four in the station; three jump in, five wait in the carrier.
    assert [len(h) for h in state["hangar"]] == [4, 5]
    # After the first slow tick the defenders' orders show the mapped mission.
    for _ in range(rlf_sim.COMMAND_TICKS + 1):
        env.scripted_actions()
        env.step()
    want = [0.0, 0.0, 0.0]
    want[index] = 1.0
    picket = 1
    assert _mission_one_hot(env, picket) == want


def test_station_assault_ends_by_its_rules() -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        6,
        STATION,
        43,
        time_limit_s=rlf_sim.mission_time_limit_s("station_assault"),
        n_threads=2,
        mission="station_assault",
    )
    winner, reason = _run_to_end(env, 4600)
    for w, r in zip(winner, reason):
        name = REASONS[r]
        assert name in {"station_destroyed", "assault_repelled", "time_limit"}
        assert w == (1 if name == "station_destroyed" else 0)


def test_station_assault_rejects_a_mobile_station() -> None:
    with pytest.raises(ValueError, match="static"):
        rlf_sim.VecEnv(
            ASSETS,
            1,
            [["carrier", "fighter"], ["carrier", "fighter"]],
            1,
            mission="station_assault",
        )


# -- v10: the citadel, the dreadnought and hardpoints (SIM_SPEC §0.8) ---------------

CITADEL = next(
    r for r in rlf_sim.mission_rosters("station_assault") if r["name"] == "citadel"
)["fleets"]


def _citadel_env(n: int, seed: int) -> rlf_sim.VecEnv:
    n_ships = len(CITADEL[0]) + len(CITADEL[1])
    return rlf_sim.VecEnv(
        ASSETS,
        n,
        CITADEL,
        seed,
        arena_radius=rlf_sim.arena_radius_for_mission("station_assault", n_ships),
        time_limit_s=rlf_sim.mission_time_limit_s("station_assault"),
        n_threads=2,
        record_events=True,
        mission="station_assault",
    )


def test_v10_constants_and_rosters() -> None:
    assert rlf_sim.SIM_VERSION >= 10
    assert 10 in rlf_sim.PILOT_COMPAT_VERSIONS
    assert rlf_sim.PILOT_OBS_DIMS[10] == rlf_sim.OBS_DIM == 587
    assert rlf_sim.MAX_TURRETS == 12 and rlf_sim.ACTION_TURRETS == 6
    assert rlf_sim.ACTION_LAYOUT["slew"][1] == 6 and rlf_sim.ACTION_WIDTH == 21
    assert rlf_sim.EVENT_KINDS["turret_destroyed"] == 13
    assert rlf_sim.EVENT_KINDS["bay_destroyed"] == 14
    # The v9 ids are frozen; the new hulls follow.
    assert list(rlf_sim.LEGACY_HULL_ORDER)[5:] == ["bomber", "station"]
    # The v9 roster stays the default, in a 450 m arena; the citadel's is 550 m.
    rosters = rlf_sim.mission_rosters("station_assault")
    assert [r["name"] for r in rosters] == ["strike of 8", "citadel"]
    assert CITADEL[0][0] == "citadel"
    assert CITADEL[1][:2] == ["carrier", "dreadnought"]
    assert rlf_sim.arena_radius_for_mission("station_assault", 16) == 450.0
    assert rlf_sim.arena_radius_for_mission("station_assault", 19) == 550.0


def test_v10_hardpoints_view_and_destruction_events() -> None:
    env = _citadel_env(4, 53)
    hp = env.hardpoints()
    s = env.n_ships
    assert hp["turret_alive"].shape == (4, s, rlf_sim.MAX_TURRETS)
    assert hp["bay_alive"].shape == (4, s, rlf_sim.MAX_BAYS)
    # The citadel (slot 0): twelve turret and four bay hardpoints, all up.
    assert hp["turret_alive"][0, 0].all()
    assert (hp["turret_max_hp"][0, 0] > 0).all()
    assert hp["bay_alive"][0, 0].all() and (hp["bay_max_hp"][0, 0] == 200).all()
    # A fighter's turret is not a hardpoint.
    assert hp["turret_max_hp"][0, 1, 0] == 0 and hp["turret_alive"][0, 1, 0]
    kinds = {
        rlf_sim.EVENT_KINDS["turret_destroyed"],
        rlf_sim.EVENT_KINDS["bay_destroyed"],
    }
    destroyed = 0
    done = np.zeros(4, dtype=bool)
    for _ in range(4600):
        env.scripted_actions()
        env.step()
        ev = env.events()
        rows = ev[np.isin(ev[:, 1], list(kinds)) & ~done[ev[:, 0].astype(int)]]
        destroyed += len(rows)
        done |= env.dones
        if done.all():
            break
    assert destroyed > 0, "hardpoints were destroyed"
    assert done.all()


def test_v10_dreadnought_is_a_capital_ship_for_python() -> None:
    from spacefight.env.rosters import CAPITAL_ROLES, capital_hull_ids, hull_names_by_id

    assert "line" in CAPITAL_ROLES
    names = hull_names_by_id(Path(ASSETS))
    assert names[:7] == list(rlf_sim.LEGACY_HULL_ORDER)
    assert names[7:] == ["citadel", "dreadnought"]
    capital = {names[i] for i in capital_hull_ids(Path(ASSETS))}
    assert {"carrier", "freighter", "station", "citadel", "dreadnought"} <= capital


def test_v10_render_state_shows_hardpoints_and_weapons() -> None:
    env = _citadel_env(1, 7)
    for _ in range(30 * 40):
        env.scripted_actions()
        env.step()
    state = env.render_state(0)
    citadel = state["ships"][0]
    assert len(citadel["turret_alive"]) == 12 and len(citadel["bay_hp"]) == 4
    assert all("weapon" in p for p in state["projectiles"])
    view = env.mission_state(0)["ships"]
    assert "hardpoints" in view[0] and "hardpoints" not in view[1]
