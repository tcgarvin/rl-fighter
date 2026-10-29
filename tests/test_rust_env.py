"""Tests for the Rust batched env `rlf_sim.VecEnv` (docs/SIM_SPEC.md §8, §10.1, WP9).

The extension must be built into the venv first:

    uv run maturin develop -m crates/sim-py/Cargo.toml --release

(`scripts/check.sh` does this before running these tests.)
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
OBS_DIM = 385
ACTION_WIDTH = 21
MAX_HITS = 64
HIT_FIELDS = 6
MAX_REACTION_TICKS = 4

# Indices into the self block of the obs (SIM_SPEC §7.2).
OBS_PRESENT = 0
OBS_LOCK_LEFT = 1
OBS_SPEED = 2
OBS_ARENA_MARGIN = 19

# Reward weights (SIM_SPEC §8, crates/sim/src/reward.rs).
HULL_W = 0.01
SHIELD_W = 0.005
FIRE_COST = -0.002
ARENA_PENALTY = -0.002

EVENT_FIRE = 0

FIGHTER_1V1 = [["fighter"], ["fighter"]]
MIXED_2V2 = [["fighter", "strafer"], ["fighter", "strafer"]]


def make_env(n_envs=4, fleets=FIGHTER_1V1, seed=0, **kwargs):
    return rlf_sim.VecEnv(ASSETS, n_envs, fleets, seed, **kwargs)


def random_actions(rng, shape):
    """Uniform valid actions: throttle/slew in 0..2, fire 0..1, power 0..6."""
    highs = np.array([3] * 8 + [3] * 6 + [2] * 6 + [7], dtype=np.int64)
    return (rng.random(shape) * highs).astype(np.int8)


def test_module_constants():
    assert rlf_sim.OBS_DIM == OBS_DIM
    assert rlf_sim.ACTION_WIDTH == ACTION_WIDTH
    assert isinstance(rlf_sim.SIM_VERSION, int)
    layout = rlf_sim.OBS_LAYOUT
    assert list(layout) == [
        "self",
        "thrusters",
        "turrets",
        "ships",
        "projectiles",
        "pending",
        "turret_arc",
        "turret_range",
    ]
    offset = 0
    for off, width in layout.values():
        assert off == offset
        offset += width
    assert offset == OBS_DIM
    assert layout["ships"] == (137, 84)
    assert layout["projectiles"] == (221, 64)
    assert layout["pending"] == (285, 88)
    assert rlf_sim.OBS_SLOTS == {
        "self": 1,
        "thrusters": 8,
        "turrets": 6,
        "ships": 7,
        "projectiles": 8,
        "pending": 4,
        "turret_arc": 6,
        "turret_range": 6,
    }
    for name, (_, width) in layout.items():
        assert width % rlf_sim.OBS_SLOTS[name] == 0, name
    assert rlf_sim.MAX_HITS == MAX_HITS
    assert rlf_sim.HIT_FIELDS == HIT_FIELDS
    assert rlf_sim.MAX_REACTION_TICKS == MAX_REACTION_TICKS
    assert rlf_sim.ACTION_LAYOUT == {
        "throttle": (0, 8),
        "slew": (8, 6),
        "fire": (14, 6),
        "power": (20, 1),
    }


def test_buffer_shapes_and_dtypes():
    n = 3
    env = make_env(n_envs=n, fleets=MIXED_2V2)
    s = env.n_ships
    assert s == 4
    assert env.n_envs == n
    expected = {
        "obs": ((n, s, OBS_DIM), np.float32),
        "actions": ((n, s, ACTION_WIDTH), np.int8),
        "rewards": ((n, s), np.float32),
        "dones": ((n,), np.bool_),
        "winner": ((n,), np.int8),
        "act_mask": ((n, s), np.bool_),
        "thruster_mask": ((n, s, 8), np.bool_),
        "turret_mask": ((n, s, 6), np.bool_),
        "fixed_turret": ((n, s, 6), np.bool_),
        "team": ((n, s), np.int8),
        "hull_id": ((n, s), np.int16),
        "alive": ((n, s), np.bool_),
        "tick": ((n,), np.uint32),
        "episode_count": ((n,), np.uint32),
        "hits": ((n, MAX_HITS, HIT_FIELDS), np.int32),
        "hit_count": ((n,), np.int32),
    }
    for name, (shape, dtype) in expected.items():
        arr = getattr(env, name)
        assert isinstance(arr, np.ndarray), name
        assert arr.shape == shape, name
        assert arr.dtype == dtype, name
        assert arr.flags.c_contiguous, name
    hashes = env.state_hash()
    assert hashes.shape == (n,) and hashes.dtype == np.uint64


def test_static_buffers_describe_the_fleet():
    env = make_env(n_envs=2, fleets=MIXED_2V2)
    np.testing.assert_array_equal(env.team, [[0, 0, 1, 1]] * 2)
    hull_names = [s["hull"] for s in env.render_state(0)["ships"]]
    assert hull_names == ["fighter", "strafer", "fighter", "strafer"]
    assert env.hull_id[0, 0] == env.hull_id[0, 2] != env.hull_id[0, 1]
    # Fighter: main + 4 RCS, one fixed nose gun. Strafer: main + 4 laterals, one laser.
    assert env.thruster_mask[0, 0].tolist() == [True] * 5 + [False] * 3
    assert env.turret_mask[0, 0].tolist() == [True] + [False] * 5
    assert env.fixed_turret[0, 0, 0]


def test_properties_return_the_same_arrays_across_steps():
    env = make_env()
    names = ["obs", "actions", "rewards", "dones", "winner", "act_mask", "alive"]
    names += ["tick", "episode_count", "hits", "hit_count", "team", "hull_id"]
    before = {name: getattr(env, name) for name in names}
    obs_view = env.obs
    for _ in range(5):
        env.scripted_actions()
        env.step()
    env.reset()
    for name in names:
        assert getattr(env, name) is before[name], name
    np.testing.assert_array_equal(obs_view, env.obs)
    assert (env.tick == 0).all()


def test_tick_advances_and_winner_is_unset_while_running():
    env = make_env()
    for t in range(1, 11):
        env.step()
        assert (env.tick == t).all()
        assert not env.dones.any()
        assert (env.winner == -2).all()


def test_actions_written_into_buffer_take_effect():
    idle = make_env(n_envs=2, seed=5)
    thrust = make_env(n_envs=2, seed=5)
    for _ in range(150):
        idle.actions.fill(0)
        thrust.actions.fill(0)
        thrust.actions[:, :, 0] = 2  # fighter thruster 0 is the main engine
        idle.step()
        thrust.step()
    assert idle.act_mask.all() and thrust.act_mask.all()
    speed_idle = idle.obs[:, :, OBS_SPEED]
    speed_thrust = thrust.obs[:, :, OBS_SPEED]
    assert (speed_thrust > speed_idle + 0.05).all()
    assert (idle.state_hash() != thrust.state_hash()).all()


def test_step_accepts_an_actions_argument():
    a = make_env(seed=2)
    b = make_env(seed=2)
    rng = np.random.default_rng(0)
    for _ in range(80):
        acts = random_actions(rng, a.actions.shape)
        a.actions[:] = acts
        a.step()
        b.step(acts)
    np.testing.assert_array_equal(a.state_hash(), b.state_hash())
    np.testing.assert_array_equal(b.actions, acts)


def test_done_auto_resets_to_a_fresh_match():
    # A 3 s time limit forces every match to end at tick 90 by tiebreak.
    env = make_env(n_envs=4, seed=1, time_limit_s=3.0)
    first_hashes = None
    for t in range(1, 91):
        env.step()
        if t < 90:
            assert not env.dones.any()
        if t == 1:
            first_hashes = env.state_hash()
    assert env.dones.all()
    assert np.isin(env.winner, [-1, 0, 1]).all()
    assert (env.episode_count == 1).all()
    assert (env.tick == 0).all()
    # Fresh match: ships have not arrived, so the obs rows are empty.
    assert (env.obs == 0).all()
    assert not env.act_mask.any()
    assert env.alive.all()
    env.step()
    assert not env.dones.any()
    assert (env.winner == -2).all()
    assert (env.tick == 1).all()
    # Episode 1 is reseeded, so it is not a replay of episode 0.
    assert (env.state_hash() != first_hashes).all()


def test_reset_restores_episode_zero():
    env = make_env(n_envs=3, seed=4, time_limit_s=1.0)
    start = env.state_hash()
    for _ in range(40):
        env.step()
    assert (env.episode_count == 1).all()
    env.reset()
    assert (env.episode_count == 0).all()
    assert (env.tick == 0).all()
    assert not env.dones.any()
    np.testing.assert_array_equal(env.state_hash(), start)


def test_thread_count_does_not_change_state():
    rng = np.random.default_rng(3)
    env1 = make_env(n_envs=32, fleets=MIXED_2V2, seed=9, n_threads=1)
    env16 = make_env(n_envs=32, fleets=MIXED_2V2, seed=9, n_threads=16)
    for t in range(600):
        if t % 2:
            env1.scripted_actions()
            env16.scripted_actions()
        else:
            acts = random_actions(rng, env1.actions.shape)
            env1.actions[:] = acts
            env16.actions[:] = acts
        env1.step()
        env16.step()
        if t % 50 == 0:
            np.testing.assert_array_equal(env1.state_hash(), env16.state_hash())
    np.testing.assert_array_equal(env1.state_hash(), env16.state_hash())
    np.testing.assert_array_equal(env1.obs, env16.obs)
    np.testing.assert_array_equal(env1.rewards, env16.rewards)
    np.testing.assert_array_equal(env1.episode_count, env16.episode_count)


def test_hits_are_plausible_under_scripted_play():
    env = make_env(n_envs=16, fleets=MIXED_2V2, seed=7)
    team = env.team
    shielded = np.array([s["hull"] == "strafer" for s in env.render_state(0)["ships"]])
    total_hits = 0
    shield_hits = 0
    for _ in range(1500):
        step_tick = env.tick.astype(np.int64) + 1
        env.scripted_actions()
        env.step()
        for i in np.flatnonzero(env.hit_count):
            n_hits = env.hit_count[i]
            assert 0 < n_hits <= MAX_HITS
            rows = env.hits[i, :n_hits]
            shooter, target, fire_tick, damage, shield, decision_tick = rows.T
            assert (shooter >= 0).all() and (shooter < env.n_ships).all()
            assert (target >= 0).all() and (target < env.n_ships).all()
            assert (team[i, shooter] != team[i, target]).all()
            assert (fire_tick >= 1).all() and (fire_tick <= step_tick[i]).all()
            # Default reaction delay d = 2 (SIM_SPEC §8).
            np.testing.assert_array_equal(decision_tick, fire_tick - 3)
            assert (damage > 0).all()
            assert np.isin(shield, [0, 1]).all()
            assert shielded[target[shield == 1]].all()
            assert (env.hits[i, n_hits:] == 0).all()
            total_hits += n_hits
            shield_hits += int(shield.sum())
    assert total_hits > 50
    assert shield_hits > 0


def test_scripted_actions_per_team_match_all_ships():
    env = make_env(n_envs=8, fleets=MIXED_2V2, seed=3)
    for _ in range(120):
        env.scripted_actions()
        env.step()
    env.actions.fill(0)
    env.scripted_actions()
    all_ships = env.actions.copy()
    assert all_ships.any()

    env.actions.fill(7)
    env.scripted_actions(team=0)
    team0 = env.team[0] == 0
    np.testing.assert_array_equal(env.actions[:, team0], all_ships[:, team0])
    assert (env.actions[:, ~team0] == 7).all()
    env.scripted_actions(team=1)
    np.testing.assert_array_equal(env.actions, all_ships)


def test_scripted_actions_are_in_range():
    env = make_env(n_envs=8, fleets=MIXED_2V2, seed=1)
    highs = np.array([2] * 8 + [2] * 6 + [1] * 6 + [6])
    for _ in range(200):
        env.scripted_actions()
        assert (env.actions >= 0).all() and (env.actions <= highs).all()
        env.step()


def test_rewards_sum_to_the_terms_over_an_episode():
    """Per ship, an episode's rewards equal hit terms + fire costs + arena penalties
    + the terminal ±1 (1v1, so every hit lands while both ships are active)."""
    n = 8
    env = make_env(n_envs=n, seed=11, record_events=True)
    team = env.team
    episode_reward = np.zeros((n, 2), dtype=np.float64)
    expected = np.zeros((n, 2), dtype=np.float64)
    finished = 0
    decisive = 0
    for _ in range(3000):
        env.scripted_actions()
        env.step()
        rewards = env.rewards.astype(np.float64)
        episode_reward += rewards
        step_expected = np.zeros((n, 2))
        for i in np.flatnonzero(env.hit_count):
            for shooter, target, _, damage, shield, _ in env.hits[
                i, : env.hit_count[i]
            ]:
                delta = (SHIELD_W if shield else HULL_W) * damage / 1000.0
                step_expected[i, shooter] += delta
                step_expected[i, target] -= delta
        events = env.events()
        for row in events[events[:, 1] == EVENT_FIRE]:
            step_expected[int(row[0]), int(row[2])] += FIRE_COST
        # Arena flags are only visible in the obs of a match that did not just reset.
        running = ~env.dones
        outside = (env.obs[:, :, OBS_PRESENT] == 1) & (
            env.obs[:, :, OBS_ARENA_MARGIN] < 0
        )
        step_expected[running[:, None] & outside] += ARENA_PENALTY
        np.testing.assert_allclose(rewards[running], step_expected[running], atol=1e-5)
        expected += step_expected
        for i in np.flatnonzero(env.dones):
            winner = env.winner[i]
            assert winner in (-1, 0, 1)
            terminal = np.where(team[i] == winner, 1.0, -1.0) if winner >= 0 else 0.0
            expected[i] += terminal
            # The done step can also carry an arena penalty the obs no longer shows.
            gap = episode_reward[i] - expected[i]
            assert ((np.abs(gap) < 1e-3) | (np.abs(gap - ARENA_PENALTY) < 1e-3)).all()
            if winner >= 0:
                decisive += 1
                winners = team[i] == winner
                assert (episode_reward[i, winners] > 0).all()
                assert (episode_reward[i, ~winners] < 0).all()
            episode_reward[i] = 0
            expected[i] = 0
            finished += 1
    assert finished >= n
    assert decisive > 0


def test_events_have_a_match_index_column():
    env = make_env(n_envs=4, seed=2, record_events=True)
    seen = set()
    for _ in range(200):
        env.scripted_actions()
        env.step()
        ev = env.events()
        assert ev.dtype == np.float32 and ev.ndim == 2 and ev.shape[1] == 9
        seen.update(ev[:, 0].astype(int).tolist())
        assert ((ev[:, 1] >= 0) & (ev[:, 1] <= 6)).all()
    assert seen == {0, 1, 2, 3}


def test_render_state_lists_ships_and_projectiles():
    env = make_env(n_envs=2, seed=2)
    for _ in range(120):
        env.scripted_actions()
        env.step()
    state = env.render_state(1)
    assert state["tick"] == env.tick[1]
    assert len(state["ships"]) == env.n_ships
    keys = {"pos", "vel", "heading", "hp", "team", "hull", "alive", "thrust_level"}
    keys |= {"queue", "reaction_ticks", "control_lock_until", "act_mask"}
    for ship in state["ships"]:
        assert keys <= set(ship)
        assert ship["reaction_ticks"] == 2
        assert len(ship["queue"]) == 2
        assert all(len(row) == ACTION_WIDTH for row in ship["queue"])
        assert all(0.0 <= lvl <= 1.0 for lvl in ship["thrust_level"])
    for proj in state["projectiles"]:
        assert {"pos", "vel", "team", "owner", "kind", "decision_tick"} <= set(proj)
        assert proj["decision_tick"] == proj["fire_tick"] - 3


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"fleets": [["fighter"], ["nope"]]}, "unknown hull"),
        ({"fleets": [["fighter"]]}, "fleets must be"),
        ({"fleets": [["fighter"], []]}, "empty"),
        ({"fleets": [["fighter"] * 5, ["fighter"] * 4]}, "at most 8"),
        ({"n_envs": 0}, "n_envs"),
        ({"n_threads": -1}, "n_threads"),
        ({"time_limit_s": 0.0}, "time_limit_s"),
        ({"arena_radius": -1.0}, "arena_radius"),
        ({"reaction_ticks": 5}, "reaction_ticks"),
        ({"reaction_ticks": -1}, "reaction_ticks"),
        ({"assets_dir": "/nonexistent/assets"}, "loading"),
    ],
)
def test_bad_constructor_args_raise(kwargs, match):
    args = {"assets_dir": ASSETS, "n_envs": 2, "fleets": FIGHTER_1V1, "seed": 0}
    args.update(kwargs)
    with pytest.raises(ValueError, match=match):
        rlf_sim.VecEnv(**args)


@pytest.mark.parametrize(
    "actions",
    [
        np.zeros((2, 2, ACTION_WIDTH), dtype=np.int64),
        np.zeros((2, 2, ACTION_WIDTH), dtype=np.float32),
        np.zeros((2, 2, ACTION_WIDTH - 1), dtype=np.int8),
        np.zeros((3, 2, ACTION_WIDTH), dtype=np.int8),
        np.zeros((2, 2 * ACTION_WIDTH), dtype=np.int8),
        [[0] * ACTION_WIDTH] * 4,
    ],
)
def test_bad_actions_raise(actions):
    env = make_env(n_envs=2)
    with pytest.raises(ValueError, match="actions must"):
        env.step(actions)
    assert (env.tick == 0).all()


def test_other_bad_calls_raise():
    env = make_env(n_envs=2)
    with pytest.raises(ValueError, match="team"):
        env.scripted_actions(team=2)
    with pytest.raises(IndexError):
        env.render_state(2)
    with pytest.raises(IndexError):
        env.render_state(-1)
    with pytest.raises(ValueError, match="record_events"):
        env.events()


def test_read_only_output_buffer_is_reported():
    env = make_env(n_envs=2)
    env.obs.flags.writeable = False
    with pytest.raises(ValueError, match="obs"):
        env.step()


def _ship_act_mask(ship: dict, tick: int) -> bool:
    """SIM_SPEC §7.1: alive && present && tick + 1 + d >= control_lock_until."""
    applies_on = tick + 1 + ship["reaction_ticks"]
    return bool(
        ship["alive"] and ship["present"] and applies_on >= ship["control_lock_until"]
    )


@pytest.mark.parametrize("reaction_ticks", [0, 2, 4])
def test_act_mask_matches_the_sim_definition(reaction_ticks):
    env = make_env(n_envs=4, fleets=MIXED_2V2, seed=6, reaction_ticks=reaction_ticks)
    saw_masked_present = False
    for _ in range(400):
        env.scripted_actions()
        env.step()
        for i in range(env.n_envs):
            state = env.render_state(i)
            for s, ship in enumerate(state["ships"]):
                assert ship["reaction_ticks"] == reaction_ticks
                assert len(ship["queue"]) == reaction_ticks
                expected = _ship_act_mask(ship, state["tick"])
                assert ship["act_mask"] == expected
                assert env.act_mask[i, s] == expected
                saw_masked_present |= ship["present"] and not expected
    # The 21-tick arrival lock outlasts every allowed delay, so present ships are
    # masked for a while after arriving.
    assert saw_masked_present


def test_lock_left_counts_down_after_arrival():
    env = make_env(n_envs=2, seed=3)
    history = []
    for _ in range(120):
        env.step()
        history.append(env.obs[:, :, OBS_LOCK_LEFT].copy())
    lock = np.stack(history)  # [T, N, S]
    for i in range(2):
        for s in range(env.n_ships):
            series = lock[:, i, s]
            first = int(np.flatnonzero(series > 0)[0])
            expected = np.clip(21 - np.arange(len(series) - first), 0, None) / 21.0
            np.testing.assert_allclose(series[first:], expected, atol=1e-6)


def test_pending_block_shows_chosen_action_after_one_step():
    env = make_env(n_envs=2, seed=4)
    off, width = rlf_sim.OBS_LAYOUT["pending"]
    rec = width // rlf_sim.OBS_SLOTS["pending"]
    # Wait until the action chosen now will be applied.
    for _ in range(200):
        if env.act_mask.all():
            break
        env.step()
    assert env.act_mask.all()
    env.actions.fill(1)  # hold everything
    env.actions[:, :, 0] = 2  # increase the main engine
    env.actions[:, :, 20] = 0
    env.step()
    pending = env.obs[..., off : off + width].reshape(2, 2, -1, rec)
    # Slot d - 1 = 1 holds the action chosen from the previous obs, slots >= d are 0.
    assert (pending[:, :, 1, 0] == 1).all() and (pending[:, :, 1, 1] == 1).all()
    assert (pending[:, :, 1, 2:9] == 0).all()
    assert (pending[:, :, 2:] == 0).all()
