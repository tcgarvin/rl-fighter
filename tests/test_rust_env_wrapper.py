"""Tests for the Python wrapper over rlf_sim (spacefight/env/rust_env.py) and the
retroactive credit adapter (spacefight/rl/credit.py RustCreditAdapter), WP10.

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

import re
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

from spacefight.env.rust_env import (  # noqa: E402
    ACTION_HIGHS,
    ACTION_WIDTH,
    MAX_HITS,
    OBS_DIM,
    WINNER_NONE,
    RustVecEnv,
    StepInfo,
    action_block,
    obs_block,
)
from spacefight.rl import credit  # noqa: E402
from spacefight.rl.credit import RustCreditAdapter  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"
FIGHTER_1V1 = [["fighter"], ["fighter"]]
MIXED_2V2 = [["fighter", "strafer"], ["gunship", "fighter"]]


def make_env(n_envs=4, fleets=FIGHTER_1V1, seed=0, **kwargs):
    return RustVecEnv(ASSETS, n_envs, fleets, seed, **kwargs)


# ---------------------------------------------------------------------------
# Wrapper
# ---------------------------------------------------------------------------


def test_reset_and_step_shapes_and_types():
    env = make_env(n_envs=3, fleets=MIXED_2V2)
    n, s = 3, 4
    assert (env.n_envs, env.n_ships) == (n, s)
    assert env.dt == pytest.approx(1 / 30)
    obs = env.reset()
    assert obs.shape == (n, s, OBS_DIM) and obs.dtype == np.float32
    obs, rewards, dones, info = env.step(np.zeros((n, s, ACTION_WIDTH), dtype=np.int8))
    assert obs.shape == (n, s, OBS_DIM) and obs.dtype == np.float32
    assert rewards.shape == (n, s) and rewards.dtype == np.float32
    assert dones.shape == (n,) and dones.dtype == np.bool_
    assert isinstance(info, StepInfo)
    assert info.winner.shape == (n,) and (info.winner == WINNER_NONE).all()
    assert info.hits.shape == (n, MAX_HITS, 5) and info.hits.dtype == np.int32
    assert info.hit_count.shape == (n,)
    assert info.act_mask.shape == (n, s) and info.alive.shape == (n, s)
    assert info.thruster_mask.shape == (n, s, 8)
    assert (info.tick == 1).all() and (info.prev_tick == 0).all()
    assert (info.prev_episode_count == 0).all()


def test_outputs_are_views_unless_copy_requested():
    env = make_env()
    obs, rewards, _, info = env.step()
    assert obs is env.raw.obs and rewards is env.raw.rewards
    assert info.tick is env.raw.tick
    assert info.prev_tick is not env.raw.tick
    snapshot = info.copy()
    env.step()
    assert (info.tick == 2).all() and (snapshot.tick == 1).all()

    copying = make_env(copy_outputs=True)
    obs, _, _, info = copying.step()
    assert obs is not copying.raw.obs
    copying.step()
    assert (info.tick == 1).all()


def test_obs_and_action_blocks_by_name():
    env = make_env(fleets=MIXED_2V2)
    layout = env.obs_layout
    assert list(layout) == list(rlf_sim.OBS_LAYOUT)
    obs = env.obs
    ships = obs_block(obs, "ships", split_slots=True)
    assert ships.shape == (4, 4, 3, 12)
    assert np.shares_memory(ships, obs)
    off, width = layout["projectiles"]
    np.testing.assert_array_equal(
        obs_block(obs, "projectiles"), obs[..., off : off + width]
    )
    assert action_block(env.actions, "throttle").shape == (4, 4, 8)
    assert action_block(env.actions, "power").shape == (4, 4, 1)
    with pytest.raises(KeyError):
        obs_block(obs, "nope")
    with pytest.raises(ValueError, match="OBS_DIM|last axis"):
        obs_block(obs[..., :10], "self")


def test_done_and_auto_reset_surface_in_info():
    env = make_env(n_envs=4, seed=1, time_limit_s=3.0)
    for _ in range(89):
        _, _, dones, info = env.step()
        assert not dones.any()
    obs, _, dones, info = env.step()
    assert dones.all()
    assert np.isin(info.winner, [-1, 0, 1]).all()
    assert (info.prev_tick == 89).all() and (info.prev_episode_count == 0).all()
    assert (info.episode_count == 1).all() and (info.tick == 0).all()
    assert (obs == 0).all() and not info.act_mask.any()


def test_scripted_actions_passthrough():
    env = make_env(fleets=MIXED_2V2)
    for _ in range(120):
        env.scripted_actions()
        env.step()
    env.actions.fill(0)
    acts = env.scripted_actions(team=1)
    assert acts is env.actions
    team1 = env.team[0] == 1
    assert (acts[:, ~team1] == 0).all()
    with pytest.raises(ValueError, match="team"):
        env.scripted_actions(team=2)


def test_bad_args_raise():
    with pytest.raises(ValueError, match="unknown hull"):
        make_env(fleets=[["fighter"], ["nope"]])
    env = make_env(n_envs=2)
    with pytest.raises(ValueError, match="actions must"):
        env.step(np.zeros((2, 2, ACTION_WIDTH), dtype=np.int64))


# ---------------------------------------------------------------------------
# Reward weights mirrored from Rust
# ---------------------------------------------------------------------------


def _rust_const(name: str) -> float:
    text = (REPO / "crates/sim/src/reward.rs").read_text()
    match = re.search(rf"pub const {name}: f32 = ([-0-9.eE]+);", text)
    assert match, f"{name} not found in reward.rs"
    return float(match.group(1))


def test_mirrored_constants_match_rust():
    assert credit.HULL_DAMAGE_WEIGHT == _rust_const("HULL_DAMAGE_WEIGHT")
    assert credit.SHIELD_DAMAGE_WEIGHT == _rust_const("SHIELD_DAMAGE_WEIGHT")
    assert credit.HIT_FIELDS == rlf_sim.HIT_FIELDS
    assert credit.HIT_DAMAGE_SCALE == rlf_sim.HIT_DAMAGE_SCALE


# ---------------------------------------------------------------------------
# Credit adapter, synthetic hits
# ---------------------------------------------------------------------------

N, S, BUF = 2, 2, 20


def _hits(rows_per_env):
    hits = np.zeros((N, MAX_HITS, 5), dtype=np.int32)
    count = np.zeros(N, dtype=np.int32)
    for env_id, rows in rows_per_env.items():
        hits[env_id, : len(rows)] = rows
        count[env_id] = len(rows)
    return hits, count


def _run_synthetic(adapter, start_tick, n_steps, hit_at, rows, alive=True):
    """Stamp n_steps consecutive steps from start_tick, with hits on step hit_at."""
    no_hits = _hits({})
    alive_arr = np.full((N, S), alive)
    for b in range(n_steps):
        hits, count = _hits(rows) if b == hit_at else no_hits
        tick = np.full(N, start_tick + b, dtype=np.uint32)
        episode = np.zeros(N, dtype=np.uint32)
        adapter.record_step(b, tick, episode, alive_arr, hits, count)


def test_hit_is_moved_to_its_fire_step():
    adapter = RustCreditAdapter(N, S, BUF)
    # Rollout starts at tick 100: buffer step b runs tick 101 + b. Env 1, shooter 1
    # fires on step 4 (fire_tick 105); 15 hull damage lands on step 10.
    _run_synthetic(adapter, 100, 12, 10, {1: [[1, 0, 105, 15000, 0]]})
    amount = 0.01 * 15.0
    flat = 1 * S + 1
    assert adapter.credit[4, flat] == pytest.approx(amount)
    assert adapter.credit[10, flat] == pytest.approx(-amount)
    assert adapter.credit[:, flat].sum() == pytest.approx(0.0)
    assert np.count_nonzero(adapter.credit) == 2
    assert adapter.n_moved == 1

    rewards = np.zeros((BUF, N * S), dtype=np.float32)
    rewards[10, flat] = amount  # the sim paid the shooter on the landing step
    adapter.inject_into_rewards(rewards, 0, BUF)
    assert rewards[4, flat] == pytest.approx(amount)
    assert rewards[10, flat] == pytest.approx(0.0, abs=1e-7)


def test_shield_hit_uses_shield_weight():
    adapter = RustCreditAdapter(N, S, BUF)
    _run_synthetic(adapter, 0, 6, 5, {0: [[0, 1, 3, 20000, 1]]})
    assert adapter.credit[2, 0] == pytest.approx(0.005 * 20.0)


def test_shot_fired_before_rollout_stays_at_landing_step():
    adapter = RustCreditAdapter(N, S, BUF)
    # Rollout starts at tick 100; fire_tick 99 was a step before buffer row 0.
    _run_synthetic(adapter, 100, 6, 3, {0: [[0, 1, 99, 15000, 0]]})
    assert not adapter.credit.any()
    assert adapter.n_kept == 1 and adapter.n_moved == 0


def test_shot_fired_in_tail_is_moved_after_shift():
    adapter = RustCreditAdapter(N, S, BUF)
    _run_synthetic(adapter, 0, BUF, BUF + 1, {})  # stamp ticks 0..19
    adapter.shift_tail(15)  # rows 0..4 now hold ticks 15..19
    hits, count = _hits({0: [[0, 1, 18, 15000, 0]]})  # fired on old row 17 -> row 2
    tick = np.full(N, 20, dtype=np.uint32)
    adapter.record_step(
        5, tick, np.zeros(N, np.uint32), np.ones((N, S), bool), hits, count
    )
    assert adapter.credit[2, 0] == pytest.approx(0.15)
    assert adapter.credit[5, 0] == pytest.approx(-0.15)


def test_episode_mismatch_is_not_moved():
    adapter = RustCreditAdapter(N, S, BUF)
    alive = np.ones((N, S), bool)
    none = _hits({})
    for b in range(3):
        adapter.record_step(
            b, np.full(N, b, np.uint32), np.zeros(N, np.uint32), alive, *none
        )
    # Same ticks, but stamped as a later episode (e.g. reset() mid-rollout).
    hits, count = _hits({0: [[0, 1, 2, 15000, 0]]})
    adapter.record_step(
        3, np.full(N, 3, np.uint32), np.ones(N, np.uint32), alive, hits, count
    )
    assert not adapter.credit.any()


def test_dead_shooter_is_not_moved_unless_requested():
    rows = {0: [[0, 1, 3, 15000, 0]]}
    kept = RustCreditAdapter(N, S, BUF)
    _run_synthetic(kept, 0, 8, 6, rows, alive=False)
    assert not kept.credit.any()

    added = RustCreditAdapter(N, S, BUF, credit_dead_shooters=True)
    _run_synthetic(added, 0, 8, 6, rows, alive=False)
    assert added.credit[2, 0] == pytest.approx(0.15)
    assert added.credit[6, 0] == 0.0
    assert added.n_added == 1


def test_bad_adapter_inputs_raise():
    adapter = RustCreditAdapter(N, S, BUF)
    hits, count = _hits({})
    with pytest.raises(IndexError):
        adapter.record_step(
            BUF, np.zeros(N), np.zeros(N), np.ones((N, S), bool), hits, count
        )
    with pytest.raises(ValueError, match="rewards"):
        adapter.inject_into_rewards(np.zeros((BUF, 3), np.float32), 0, BUF)
    with pytest.raises(ValueError):
        RustCreditAdapter(0, S, BUF)


# ---------------------------------------------------------------------------
# Credit adapter, real env
# ---------------------------------------------------------------------------


def _rollout(env, adapter, n_steps):
    rewards = np.zeros((n_steps, env.n_envs * env.n_ships), dtype=np.float32)
    for b in range(n_steps):
        env.scripted_actions()
        _, step_rewards, _, info = env.step()
        rewards[b] = step_rewards.reshape(-1)
        adapter.record_step(
            b,
            info.prev_tick,
            info.prev_episode_count,
            info.prev_alive,
            info.hits,
            info.hit_count,
        )
    return rewards


@pytest.mark.parametrize("warmup", [0, 200])
def test_real_rollout_conserves_reward_and_moves_hits_earlier(warmup):
    env = make_env(n_envs=8, fleets=MIXED_2V2, seed=7)
    for _ in range(warmup):  # shots in flight when the rollout starts
        env.scripted_actions()
        env.step()
    n_steps = 1200
    adapter = RustCreditAdapter(env.n_envs, env.n_ships, n_steps)
    rewards = _rollout(env, adapter, n_steps)
    before = rewards.astype(np.float64).copy()
    adapter.inject_into_rewards(rewards, 0, n_steps)
    after = rewards.astype(np.float64)

    assert adapter.n_moved > 20
    np.testing.assert_allclose(after.sum(axis=0), before.sum(axis=0), atol=1e-4)
    assert after.sum() == pytest.approx(before.sum(), abs=1e-3)
    # Credit only ever moves backwards in time: cumulative sums never drop.
    cum = np.cumsum(adapter.credit, axis=0)
    assert (cum >= -1e-9).all()
    if warmup:
        assert adapter.n_kept > 0


# ---------------------------------------------------------------------------
# Behaviour-cloning dataset check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fleets", [MIXED_2V2, FIGHTER_1V1], ids=["2v2", "1v1"])
def test_scripted_bc_pairs_are_valid(fleets):
    env = make_env(n_envs=4, fleets=fleets, seed=5)
    obs = env.reset()
    ever_active = np.zeros((env.n_envs, env.n_ships), dtype=bool)
    n_pairs = 0
    episodes = 0
    for _ in range(10_000):
        mask = env.act_mask.copy()
        actions = env.scripted_actions()
        pairs_obs = obs[mask]
        pairs_act = actions[mask]
        assert np.isfinite(obs).all()
        assert (np.abs(obs) <= 5.0).all()
        assert (actions >= 0).all() and (actions <= ACTION_HIGHS).all()
        # Masked ships: absent (obs row zero) or present and control-locked.
        present = obs[..., 0] == 1
        locked = obs[..., 1] == 1
        assert not (mask & ~present).any()
        assert not (mask & locked).any()
        assert (obs[~present] == 0).all()
        ever_active |= mask
        n_pairs += len(pairs_obs)
        assert pairs_act.shape == (len(pairs_obs), ACTION_WIDTH)
        obs, rewards, dones, _ = env.step()
        assert np.isfinite(rewards).all()
        episodes += int(dones.sum())
    assert ever_active.all()
    assert episodes > 0
    assert n_pairs > 10_000


def _diverges(fleets, select, columns, n_steps=1500):
    """Step a scripted env and a copy whose `select`ed rows get random `columns`.

    Returns whether the state hashes ever differed and how many rows were patched.
    """
    a = make_env(n_envs=8, fleets=fleets, seed=3)
    b = make_env(n_envs=8, fleets=fleets, seed=3)
    rng = np.random.default_rng(0)
    patched_rows = 0
    for _ in range(n_steps):
        rows = select(a)
        patched_rows += int(rows.sum())
        a.scripted_actions()
        b.scripted_actions()
        noise = (rng.random(b.actions.shape) * (ACTION_HIGHS + 1)).astype(np.int8)
        patched = b.actions[rows]
        patched[:, columns] = noise[rows][:, columns]
        b.actions[rows] = patched
        a.step()
        b.step()
        if (a.raw.state_hash() != b.raw.state_hash()).any():
            return True, patched_rows
    return False, patched_rows


THROTTLE_AND_FIRE = np.r_[0:8, 14:20]
ALL_HEADS = np.arange(ACTION_WIDTH)


def test_dead_ships_actions_are_ignored():
    diverged, patched = _diverges(MIXED_2V2, lambda e: ~e.raw.alive, ALL_HEADS)
    assert patched > 1000 and not diverged


def test_absent_ships_throttle_and_fire_are_ignored():
    def absent(e):
        return ~e.act_mask & (e.obs[..., 0] == 0)

    diverged, patched = _diverges(MIXED_2V2, absent, THROTTLE_AND_FIRE)
    assert patched > 1000 and not diverged


@pytest.mark.xfail(
    strict=True,
    reason=(
        "sim gap: act_mask is evaluated at the post-step tick, so a ship on its last "
        "control-locked tick is masked although its next action applies, and slew and "
        "power apply during the lock (SIM_SPEC §5 stage 3/6 vs §7.1)"
    ),
)
def test_masked_ships_actions_are_fully_ignored():
    diverged, _ = _diverges(MIXED_2V2, lambda e: ~e.act_mask, ALL_HEADS)
    assert not diverged
