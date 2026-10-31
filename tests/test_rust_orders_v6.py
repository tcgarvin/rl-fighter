"""SIM_VERSION 6 (M3 stage B3) bindings: orders redesigned (attack / defend / go-to),
the threat obs blocks, hidden-order mode, the transit flag, threat sets, hull loss and
order tracks (docs/SIM_SPEC.md §0.4, §5.9, §7.2, §8, §10.1).

The extension must be built into the venv first:

    uv run maturin develop -m crates/sim-py/Cargo.toml --release
"""

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

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
LAYOUT = rlf_sim.OBS_LAYOUT
ORDER_OFF, ORDER_W = LAYOUT["order"]
EXTRAS_OFF, EXTRAS_W = LAYOUT["ship_extras"]
ORDER_SHIPS_OFF, ORDER_SHIPS_W = LAYOUT["order_ships"]
TRAIN_CARRIER = ["carrier", "fighter", "fighter", "strafer", "gunship"]
CONVOY = [
    ["freighter", "freighter", "freighter", "fighter", "fighter", "strafer"],
    ["fighter", "fighter", "strafer", "gunship", "fighter"],
]
KIND_CODES = {"none": 0, "attack": 1, "defend": 2, "goto": 3}


def carrier_env(n: int = 4, seed: int = 9, **kwargs) -> "rlf_sim.VecEnv":
    return rlf_sim.VecEnv(
        ASSETS,
        n,
        [TRAIN_CARRIER, TRAIN_CARRIER],
        seed,
        mission="carrier_battle",
        commanders=["random", "random"],
        time_limit_s=rlf_sim.mission_time_limit_s("carrier_battle"),
        max_ships=rlf_sim.MAX_TRAIN_SHIPS,
        n_threads=2,
        **kwargs,
    )


def run(env: "rlf_sim.VecEnv", steps: int) -> None:
    for _ in range(steps):
        env.scripted_actions()
        env.step()


def test_v6_constants_and_layout() -> None:
    assert rlf_sim.SIM_VERSION == 6
    assert rlf_sim.OBS_DIM == 583
    assert rlf_sim.OBS_DIM_V5 == 403 and rlf_sim.OBS_DIM_V4 == 385
    assert rlf_sim.PILOT_OBS_DIMS == {3: 385, 4: 385, 5: 403, 6: 583}
    assert list(rlf_sim.PILOT_COMPAT_VERSIONS) == [3, 4, 5, 6]
    assert rlf_sim.SHIP_EXTRA_W == 10 and rlf_sim.N_ORDER_SHIPS == 5
    assert list(rlf_sim.ORDER_KINDS) == ["attack", "defend", "goto"]
    assert (EXTRAS_OFF, EXTRAS_W) == (403, 7 * 10)
    assert (ORDER_SHIPS_OFF, ORDER_SHIPS_W) == (473, 5 * 22)
    assert rlf_sim.OBS_SLOTS["ship_extras"] == 7
    assert rlf_sim.OBS_SLOTS["order_ships"] == 5


def test_v6_buffers_shapes_and_order_tracks() -> None:
    env = carrier_env()
    n, s = env.n_envs, env.n_ships
    assert env.order_transit.shape == (n, s) and env.order_transit.dtype == np.bool_
    assert env.ward_threat.shape == (n, s, s) and env.ward_threat.dtype == np.bool_
    assert env.ward_hull_lost.shape == (n, s)
    assert env.ward_hull_lost.dtype == np.float32
    run(env, 600)
    tracks = env.order_tracks()
    assert set(tracks) == {
        "standing_kind",
        "effective_kind",
        "target",
        "point",
        "radius",
        "arrived",
        "instance_start",
    }
    assert tracks["standing_kind"].shape == (n, s)
    assert tracks["standing_kind"].dtype == np.int8
    assert tracks["target"].dtype == np.int16
    assert tracks["point"].shape == (n, s, 2)
    assert tracks["instance_start"].dtype == np.uint32
    eff = tracks["effective_kind"]
    # The obs's has_order is exactly "an effective order".
    has = env.obs[..., ORDER_OFF] == 1.0
    np.testing.assert_array_equal(has, eff > 0)
    # The kind one-hot matches the effective kind.
    for code in (1, 2, 3):
        rows = eff == code
        assert np.all(env.obs[..., ORDER_OFF + code][rows] == 1.0)
    # A completed go-to: standing go-to, arrived, effective none.
    done = (tracks["standing_kind"] == 3) & tracks["arrived"]
    assert np.all(eff[done] == 0)
    # Padding slots.
    pad = env.team < 0
    assert np.all(tracks["standing_kind"][pad] == 0)
    assert np.all(tracks["target"][pad] == -1)
    assert not env.order_transit[pad].any()


def test_mission_state_names_the_v6_order_kinds() -> None:
    env = carrier_env(n=2)
    seen: set[str] = set()
    for _ in range(40):
        run(env, 60)
        for i in range(env.n_envs):
            for team in env.mission_state(i)["squads"]:
                for squad in team:
                    seen.add(squad["order"]["kind"])
    assert seen <= {"none", "attack", "defend", "goto"}
    assert {"attack", "defend", "goto"} <= seen


def test_transit_flag_matches_effective_orders_and_threat_sets() -> None:
    env = carrier_env(seed=21)
    saw_goto = saw_defend_quiet = False
    for _ in range(900):
        env.scripted_actions()
        env.step()
        if env.tick[0] % 30:
            continue
        tracks = env.order_tracks()
        eff = tracks["effective_kind"]
        transit = env.order_transit
        # Attack and no-order rows are never in transit; go-to rows always are.
        assert not transit[(eff == 0) | (eff == 1)].any()
        assert transit[eff == 3].all()
        saw_goto |= bool((eff == 3).any())
        saw_defend_quiet |= bool((transit & (eff == 2)).any())
    assert saw_goto and saw_defend_quiet


def test_ward_threat_and_hull_lost_follow_damage() -> None:
    env = carrier_env(seed=5)
    saw_threat = saw_loss = False
    for _ in range(1200):
        env.scripted_actions()
        env.step()
        threat = env.ward_threat
        team = env.team
        # Only enemies are threats; never oneself; padding has none.
        same = team[:, :, None] == team[:, None, :]
        assert not (threat & same).any()
        assert not threat[team < 0].any()
        lost = env.ward_hull_lost
        assert (lost >= 0).all() and (lost <= 1.0 + 1e-6).all()
        saw_threat |= bool(threat.any())
        saw_loss |= bool((lost > 0).any())
    assert saw_threat and saw_loss


def test_hidden_orders_zero_the_order_features_only_for_that_team() -> None:
    def build(hide: list[bool] | None) -> "rlf_sim.VecEnv":
        kw = {} if hide is None else {"hide_orders": hide}
        return carrier_env(n=3, seed=13, **kw)

    shown, hidden = build(None), build([True, False])
    any_order = False
    for _ in range(300):
        for env in (shown, hidden):
            env.scripted_actions()
            env.step()
        # Same matches: hiding changes no state, reward or script.
        np.testing.assert_array_equal(shown.state_hash(), hidden.state_hash())
        np.testing.assert_array_equal(shown.rewards, hidden.rewards)
        np.testing.assert_array_equal(shown.order_rewards, hidden.order_rewards)
        team0 = shown.team == 0
        team1 = shown.team == 1
        a, b = shown.obs, hidden.obs
        np.testing.assert_array_equal(a[team1], b[team1])
        np.testing.assert_array_equal(a[..., :ORDER_OFF], b[..., :ORDER_OFF])
        h = b[team0]
        assert np.all(h[:, ORDER_OFF : ORDER_OFF + ORDER_W] == 0.0)
        assert np.all(h[:, ORDER_SHIPS_OFF:] == 0.0)
        ext = h[:, EXTRAS_OFF : EXTRAS_OFF + EXTRAS_W].reshape(-1, 7, 10)
        assert np.all(ext[..., 7:] == 0.0)
        np.testing.assert_array_equal(
            ext[..., :7],
            a[team0][:, EXTRAS_OFF : EXTRAS_OFF + EXTRAS_W].reshape(-1, 7, 10)[..., :7],
        )
        any_order |= bool((a[team0][:, ORDER_OFF] == 1.0).any())
    assert any_order


def test_set_next_roster_takes_hide_orders() -> None:
    env = carrier_env(n=2, seed=3)
    env.set_next_roster(
        1,
        [TRAIN_CARRIER, TRAIN_CARRIER],
        450.0,
        mission="carrier_battle",
        hide_orders=[False, True],
    )
    env.reset()
    run(env, 400)
    team1 = env.team[1] == 1
    assert np.all(env.obs[1][team1][:, ORDER_OFF : ORDER_OFF + ORDER_W] == 0.0)
    assert (env.obs[0][env.team[0] == 1][:, ORDER_OFF] == 1.0).any()
    with pytest.raises(ValueError):
        env.set_next_roster(
            0, [TRAIN_CARRIER, TRAIN_CARRIER], 450.0, hide_orders=[True]
        )


def test_submit_command_takes_defend_and_goto() -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        1,
        CONVOY,
        4,
        mission="convoy_escort",
        commanders=["external", "external"],
        n_threads=1,
    )
    env.submit_command(
        0,
        0,
        [
            {
                "kind": "squad",
                "squad": 0,
                "members": [3],
                "order": {"kind": "defend", "ward": 0},
            },
            {
                "kind": "squad",
                "squad": 1,
                "members": [4, 5],
                "order": {"kind": "goto", "point": [50.0, 0.0], "radius": 40.0},
            },
        ],
    )
    while not env.command_due()[0]:
        env.step()
    env.step()
    squads = env.mission_state(0)["squads"][0]
    assert squads[0]["order"] == {"kind": "defend", "ward": 0}
    assert squads[1]["order"]["kind"] == "goto"
    tracks = env.order_tracks()
    assert tracks["standing_kind"][0, 3] == KIND_CODES["defend"]
    assert tracks["standing_kind"][0, 4] == KIND_CODES["goto"]
    assert tracks["radius"][0, 4] == pytest.approx(40.0)
    with pytest.raises(ValueError):
        env.submit_command(
            0,
            0,
            {
                "kind": "squad",
                "squad": 0,
                "members": [3],
                "order": {"kind": "guard", "ward": 0},
            },
        )


# -- The semantics the B3 training WP builds on (team lead, 2026-10-31).


def test_goto_reissued_within_40_m_keeps_its_instance() -> None:
    env = rlf_sim.VecEnv(
        ASSETS,
        1,
        CONVOY,
        4,
        mission="convoy_escort",
        commanders=["external", "external"],
        n_threads=1,
    )

    def order_goto(x: float) -> None:
        env.submit_command(
            0,
            0,
            {
                "kind": "squad",
                "squad": 1,
                "members": [4],
                "order": {"kind": "goto", "point": [x, -300.0], "radius": 20.0},
            },
        )
        while not env.command_due()[0]:
            env.step()
        env.step()

    order_goto(0.0)
    start = int(env.order_tracks()["instance_start"][0, 4])
    order_goto(35.0)
    tracks = env.order_tracks()
    assert tracks["instance_start"][0, 4] == start
    assert tracks["standing_kind"][0, 4] == KIND_CODES["goto"]
    order_goto(45.0)
    assert env.order_tracks()["instance_start"][0, 4] > start


def test_deaths_keep_instances_standing_orders_and_count_as_hull_lost() -> None:
    env = carrier_env(n=8, seed=17)
    deaths = kept = arrived_standing = 0
    for _ in range(2400):
        before = env.order_tracks()
        alive = env.alive.copy()
        env.scripted_actions()
        env.step()
        if env.dones.any():
            continue
        after = env.order_tracks()
        died = alive & ~env.alive
        # 3. A ship's death step counts in ward_hull_lost.
        assert np.all(env.ward_hull_lost[died] > 0.0)
        deaths += int(died.sum())
        if env.command_due().any() or (env.tick % rlf_sim.COMMAND_TICKS == 0).any():
            continue  # the slow tick may re-task the squad
        # 1, 2. A slot whose attack target or defend ward died this (non-slow) step
        # keeps its standing order, target and instance start.
        for i, s in zip(*np.nonzero(before["standing_kind"] > 0)):
            t = int(before["target"][i, s])
            if t < 0 or not died[i, t]:
                continue
            assert after["standing_kind"][i, s] == before["standing_kind"][i, s]
            assert after["target"][i, s] == t
            assert after["instance_start"][i, s] == before["instance_start"][i, s]
            assert after["effective_kind"][i, s] == 0
            kept += 1
        done = (after["standing_kind"] == KIND_CODES["goto"]) & after["arrived"]
        arrived_standing += int(done.sum())
        assert np.all(after["effective_kind"][done] == 0)
    assert deaths > 0 and kept > 0 and arrived_standing > 0, (
        deaths,
        kept,
        arrived_standing,
    )


def test_ward_threat_is_indexed_env_ward_enemy() -> None:
    env = carrier_env(n=1, seed=29)
    checked = 0
    for _ in range(900):
        env.scripted_actions()
        env.step()
        if env.dones[0]:
            continue
        ships = env.render_state(0)["ships"]
        pos = np.array([s["pos"] for s in ships])
        active = np.array([s["alive"] and s["present"] for s in ships])
        team = np.array([s["team"] for s in ships])
        threat = env.ward_threat[0]
        for w in np.nonzero(active)[0]:
            for e in np.nonzero(active & (team != team[w]))[0]:
                # Every weapon reaches at least 180 m; +40 m margin: anything within
                # 200 m of the ward is in its threat set, row = ward, column = enemy.
                if np.linalg.norm(pos[e] - pos[w]) < 200.0:
                    assert threat[w, e], (w, e)
                    checked += 1
    assert checked > 0


def test_set_next_roster_hide_orders_none_keeps_the_env_setting() -> None:
    env = carrier_env(n=2, seed=31, hide_orders=[True, False])
    env.set_next_roster(
        1, [TRAIN_CARRIER, TRAIN_CARRIER], 450.0, mission="carrier_battle"
    )
    env.reset()
    run(env, 400)
    for i in range(2):
        team0 = env.team[i] == 0
        assert np.all(env.obs[i][team0][:, ORDER_OFF : ORDER_OFF + ORDER_W] == 0.0)
    assert (env.obs[..., ORDER_OFF][env.team == 1] == 1.0).any()


def test_default_rosters_stay_three_per_mission() -> None:
    for mission in ("carrier_battle", "convoy_escort"):
        assert len(rlf_sim.mission_rosters(mission)) == 3
    assert rlf_sim.PILOT_OBS_DIMS[6] == 583
