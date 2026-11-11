"""The learned commander's interface from Python (``docs/COMMANDER.md``): the
``"learned"`` commander mode and its cadence, ``commander_features``,
``submit_commander_actions`` with per-env hold state, ``team_values`` and the
``rlf_sim.commander_io()`` constants."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rlf_sim

from spacefight.env.rosters import COMMANDER_MODES, LEARNED, Roster
from spacefight.env.rust_env import RustVecEnv

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
IO = rlf_sim.commander_io()
ACT = IO["actions"]
E = IO["n_entities"]

CARRIER_FLEET = [
    "carrier",
    "fighter",
    "strafer",
    "fighter",
    "gunship",
    "fighter",
    "fighter",
]


def _carrier_env(n_envs: int, commanders: list[str]) -> rlf_sim.VecEnv:
    return rlf_sim.VecEnv(
        ASSETS,
        n_envs,
        [CARRIER_FLEET, CARRIER_FLEET],
        7,
        mission="carrier_battle",
        commanders=commanders,
        n_threads=2,
    )


def _duel_env(n_envs: int, time_limit_s: float = 90.0) -> rlf_sim.VecEnv:
    return rlf_sim.VecEnv(
        ASSETS,
        n_envs,
        [["fighter", "strafer"], ["fighter", "strafer"]],
        3,
        commanders=["learned", "scripted"],
        time_limit_s=time_limit_s,
        n_threads=2,
    )


def _step_until_due(env: rlf_sim.VecEnv, team: int) -> None:
    for _ in range(200):
        if env.commander_due(team).all():
            return
        env.scripted_actions()
        env.step()
    raise AssertionError("never due")


def _keep(k: int) -> np.ndarray:
    return np.zeros((k, IO["action_dim"]), dtype=np.int32)


def test_constants() -> None:
    assert IO["version"] == 1
    assert (IO["entity_dim"], IO["global_dim"], IO["action_dim"]) == (40, 53, 40)
    assert (IO["n_points"], IO["hold_decisions"]) == (25, 5)
    assert (IO["goto_radius"], IO["vel_scale"]) == (60.0, 100.0)
    assert IO["command_ticks"] == rlf_sim.LEARNED_COMMAND_TICKS == 30
    assert E == rlf_sim.MAX_SHIPS == 20
    assert ACT == {
        "launch": (0, 3, 2),
        "waypoint": (3, 1, 26),
        "squad": (4, 20, 6),
        "order": (24, 4, 5),
        "target": (28, 4, 20),
        "ward": (32, 4, 20),
        "point": (36, 4, 25),
    }
    flat = IO["flat_layout"]
    assert list(flat) == [
        "globals",
        "entities",
        "valid",
        "launch_mask",
        "waypoint_mask",
        "squad_mask",
        "order_mask",
        "target_mask",
        "ward_mask",
    ]
    end = max(off + width for off, width in flat.values())
    assert end == IO["flat_dim"] == 1082
    assert sum(w for _, w in IO["entity_layout"].values()) == IO["entity_dim"]
    assert sum(w for _, w in IO["global_layout"].values()) == IO["global_dim"]
    assert "learned" in rlf_sim.COMMANDER_MODES
    assert LEARNED in COMMANDER_MODES


def test_feature_shapes_and_masks_of_a_carrier_battle() -> None:
    env = _carrier_env(3, ["learned", "learned"])
    f = env.commander_features(0)
    shapes = {
        "globals": ((3, 53), np.float32),
        "entities": ((3, E, 40), np.float32),
        "valid": ((3, E), np.bool_),
        "launch_mask": ((3, 3), np.bool_),
        "waypoint_mask": ((3, 26), np.bool_),
        "squad_mask": ((3, E, 6), np.bool_),
        "order_mask": ((3, 4, 5), np.bool_),
        "target_mask": ((3, E), np.bool_),
        "ward_mask": ((3, E), np.bool_),
    }
    assert set(f) == set(shapes)
    for name, (shape, dtype) in shapes.items():
        assert f[name].shape == shape, name
        assert f[name].dtype == dtype, name
    # 14 ships: the padding slots are never entities and only keep is allowed.
    assert not f["valid"][:, 14:].any()
    assert (f["entities"][:, 14:] == 0).all()
    assert f["squad_mask"][:, :, 0].all() and not f["squad_mask"][:, 14:, 1:].any()
    # Hangar fighter, gunship, fighter, fighter: launch fighters and gunships.
    assert (f["launch_mask"] == [True, False, True]).all()
    assert f["waypoint_mask"].all()
    glob = IO["global_layout"]
    assert (f["globals"][:, glob["role"][0] + 1] == 1).all()
    # The docked reserves are not entities.
    state = env.mission_state(0)
    for s in state["hangar"][0]:
        assert not f["valid"][0, s]
    # Team frame: each commander's carrier is on its own -x side.
    pos = IO["entity_layout"]["pos"][0]
    f1 = env.commander_features(1)
    for team, feats in ((0, f), (1, f1)):
        c = state["carrier"][team]
        assert feats["entities"][0, c, pos] < -0.5


def test_a_learned_team_decides_every_30_ticks() -> None:
    env = _duel_env(2)
    due: list[list[int]] = [[], []]
    for _ in range(180):
        for team in (0, 1):
            if env.commander_due(team)[0]:
                due[team].append(int(env.tick[0]) + 1)
        env.scripted_actions()
        env.step()
    assert due[0] == [30, 60, 90, 120, 150, 180]
    assert due[1] == [60, 120, 180]
    assert env.commander_due(0).dtype == np.bool_


def test_submitted_decisions_move_squads_and_lock_them() -> None:
    env = _duel_env(2)
    _step_until_due(env, 0)
    a = _keep(1)
    a[0, ACT["squad"][0] + 0] = 2  # slot 0 -> squad 1
    a[0, ACT["squad"][0] + 1] = 2  # slot 1 -> squad 1
    a[0, ACT["order"][0]] = 4  # squad 1: go to map point 5 (toward home)
    a[0, ACT["point"][0]] = 5
    changed = env.submit_commander_actions(0, np.array([1], dtype=np.int64), a)
    assert changed.dtype == np.int32 and changed.tolist() == [2]
    env.scripted_actions()
    env.step()
    squads = env.mission_state(1)["squads"][0]
    assert sorted(squads[0]["members"]) == [0, 1]
    assert squads[0]["order"]["kind"] == "goto"
    point = squads[0]["order"]["point"]
    radius = float(env.arena_radius[1])
    assert point == pytest.approx([-0.3 * radius, 0.0], abs=1e-3)
    assert squads[0]["order"]["radius"] == pytest.approx(60.0)
    assert env.mission_state(0)["squads"][0][0]["members"] == []
    locks = env.commander_locks(1, 0)
    assert locks["decisions"] == 1
    assert locks["squad_hold_left"] == [4, 0, 0, 0]
    assert locks["ship_hold_left"][:3] == [4, 4, 0]
    assert locks["changed_ships"] == 2
    f = env.commander_features(0)
    assert not f["order_mask"][1, 0, 1:].any()
    # Env 0 never decided; its pilots are still jumping in, so attack and defend wait.
    assert (f["order_mask"][0, 0] == [True, True, False, False, True]).all()
    assert not f["squad_mask"][1, 0, 1:].any()
    hold = IO["entity_layout"]["ship_hold"][0]
    assert f["entities"][1, 0, hold] == pytest.approx(4 / 5)
    assert env.commander_locks(0, 0)["decisions"] == 0


def test_bad_submissions_raise_and_change_nothing() -> None:
    env = _duel_env(3)
    ids = np.array([0, 2], dtype=np.int64)
    with pytest.raises(ValueError, match="slow tick"):
        env.submit_commander_actions(0, ids, _keep(2))
    _step_until_due(env, 0)
    with pytest.raises(ValueError, match="takes no decisions"):
        env.submit_commander_actions(1, ids, _keep(2))
    bad = _keep(2)
    bad[1, ACT["order"][0]] = 5
    with pytest.raises(ValueError, match="outside"):
        env.submit_commander_actions(0, ids, bad)
    with pytest.raises(ValueError, match="twice"):
        env.submit_commander_actions(0, np.array([1, 1], dtype=np.int64), _keep(2))
    with pytest.raises(ValueError, match="shape"):
        env.submit_commander_actions(0, ids, _keep(3))
    with pytest.raises(ValueError, match="int32"):
        env.submit_commander_actions(0, ids, _keep(2).astype(np.int64))
    with pytest.raises(ValueError, match="int64"):
        env.submit_commander_actions(0, ids.astype(np.int32), _keep(2))
    with pytest.raises(IndexError):
        env.submit_commander_actions(0, np.array([0, 3], dtype=np.int64), _keep(2))
    with pytest.raises(ValueError):
        env.commander_features(2)
    for i in range(3):
        assert env.commander_locks(i, 0)["decisions"] == 0
    env.submit_commander_actions(0, ids, _keep(2))
    assert [env.commander_locks(i, 0)["decisions"] for i in range(3)] == [1, 0, 1]


def test_locks_reset_when_the_match_is_rebuilt() -> None:
    env = _duel_env(2, time_limit_s=2.0)
    _step_until_due(env, 0)
    a = _keep(2)
    a[:, ACT["squad"][0]] = 2
    a[:, ACT["order"][0]] = 4
    a[:, ACT["point"][0]] = 17
    env.submit_commander_actions(0, np.array([0, 1], dtype=np.int64), a)
    assert env.commander_locks(0, 0)["ship_hold_left"][0] == 4
    for _ in range(31):
        env.scripted_actions()
        env.step()
    assert (env.episode_count == 1).all()
    for i in range(2):
        locks = env.commander_locks(i, 0)
        assert locks["decisions"] == 0
        assert locks["ship_hold_left"] == [0] * E
        assert locks["changed_ships"] == 0
        assert locks["last_launch_tick"] is None


def test_team_values_match_the_ships() -> None:
    env = _carrier_env(2, ["learned", "scripted"])
    for _ in range(100):
        env.scripted_actions()
        env.step()
    values = env.team_values()
    assert values.shape == (2, 2) and values.dtype == np.float32
    for i in range(2):
        want = [0.0, 0.0]
        for s in env.render_state(i)["ships"]:
            if s["alive"] and not s["escaped"]:
                want[s["team"]] += s["hp"] + 0.5 * s["shield"]
        assert values[i] == pytest.approx(want, rel=1e-5)


def _random_legal(
    f: dict[str, np.ndarray], i: int, rng: np.random.Generator
) -> np.ndarray:
    """A decision drawn uniformly from the allowed choices of every head of env ``i``."""

    def pick(mask: np.ndarray) -> int:
        return int(rng.choice(np.flatnonzero(mask)))

    a = np.zeros(IO["action_dim"], dtype=np.int32)
    for h in range(3):
        a[ACT["launch"][0] + h] = int(f["launch_mask"][i, h] and rng.random() < 0.5)
    a[ACT["waypoint"][0]] = pick(f["waypoint_mask"][i])
    for s in range(E):
        a[ACT["squad"][0] + s] = pick(f["squad_mask"][i, s])
    for k in range(4):
        a[ACT["order"][0] + k] = pick(f["order_mask"][i, k])
        if f["target_mask"][i].any():
            a[ACT["target"][0] + k] = pick(f["target_mask"][i])
        if f["ward_mask"][i].any():
            a[ACT["ward"][0] + k] = pick(f["ward_mask"][i])
        a[ACT["point"][0] + k] = int(rng.integers(IO["n_points"]))
    return a


def test_random_legal_decisions_play_whole_carrier_battles() -> None:
    env = RustVecEnv(
        ASSETS,
        3,
        [CARRIER_FLEET, CARRIER_FLEET],
        seed=11,
        n_threads=2,
    )
    roster = Roster.of(
        CARRIER_FLEET,
        CARRIER_FLEET,
        mission="carrier_battle",
        commanders=("learned", "scripted"),
    )
    for i in range(env.n_envs):
        env.set_next_roster(i, roster)
    env.reset()
    rng = np.random.default_rng(0)
    decisions = 0
    launched = 0
    squads_used = 0
    for _ in range(1200):
        due = np.flatnonzero(env.commander_due(0))
        if due.size:
            f = env.commander_features(0)
            acts = np.stack([_random_legal(f, int(i), rng) for i in due])
            env.submit_commander_actions(0, due, acts)
            decisions += due.size
        env.scripted_actions()
        _, _, dones, _ = env.step()
        if due.size:
            for i in due:
                if dones[i]:
                    continue
                results = env.raw.command_results(int(i), 0)
                launched += sum(r["outcome"] == "launched" for r in results)
                squads_used += sum(r["command"] == "squad" for r in results)
    assert decisions >= 3 * 35  # every 30 ticks, an episode boundary or two aside
    assert launched > 0 and squads_used > 0
