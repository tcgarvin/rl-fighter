"""Tests for the spike PPO loop (spacefight/rl/spike_ppo.py), the opponent schedule
(spacefight/rl/opponents.py) and ``train_spike.py ppo``.

Plan: lab/runs/2026-10-28-learnability-spike/plan.md §4.2, §4.3 and §8 row E.
Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest
import torch

pytest.importorskip("rlf_sim", reason="rlf_sim extension not built")

from spacefight import train_spike  # noqa: E402
from spacefight.env.rust_env import StepInfo  # noqa: E402
from spacefight.rl import credit  # noqa: E402
from spacefight.rl import spike_ppo  # noqa: E402
from spacefight.rl.opponents import (  # noqa: E402
    DEFAULT_BANDS,
    OpponentAssigner,
    OpponentKind,
    OpponentSchedule,
    quota_counts,
)
from spacefight.rl.spike_policy import (  # noqa: E402
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    load_policy,
    save_policy,
)
from spacefight.rl.spike_ppo import (  # noqa: E402
    LOG_KEYS,
    PPOConfig,
    SpikeTrainer,
    checkpoint_path,
    compute_gae,
    latest_checkpoint,
    read_config,
)

REPO = Path(__file__).resolve().parent.parent
ASSETS = str(REPO / "assets")

# Small, fast settings shared by the end-to-end tests (<= 2 threads each).
SMALL = {
    "assets_dir": ASSETS,
    "n_envs": 8,
    "n_steps": 16,
    "minibatch": 64,
    "sim_threads": 2,
    "torch_threads": 2,
    # Start past the arrival + control lock so 16-step rollouts have live rows.
    "env_warmup_steps": 60,
}


@pytest.fixture
def bc_checkpoint(tmp_path: Path) -> Path:
    torch.manual_seed(0)
    path = tmp_path / "bc.pt"
    save_policy(path, SpikeActor(), SpikeCritic(), {"kind": "test"})
    return path


def read_log(run_dir: Path) -> list[dict]:
    return [
        json.loads(line) for line in (run_dir / "log.jsonl").read_text().splitlines()
    ]


def actor_vector(actor: SpikeActor) -> torch.Tensor:
    return torch.cat([p.detach().reshape(-1).clone() for p in actor.parameters()])


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


def test_three_updates_from_bc_checkpoint(tmp_path, bc_checkpoint):
    config = PPOConfig.preset(
        str(bc_checkpoint), n_updates=3, critic_warmup_updates=1, **SMALL
    )
    trainer = SpikeTrainer(config, tmp_path / "run")
    before = actor_vector(trainer.actor)
    after_first: list[torch.Tensor] = []

    def hook(t: SpikeTrainer, row: dict) -> None:
        if row["update"] == 1:
            after_first.append(actor_vector(t.actor))

    assert trainer.train(on_update_end=hook) == 3
    rows = read_log(tmp_path / "run")
    assert [r["update"] for r in rows] == [1, 2, 3]
    for row in rows:
        assert list(row) == list(LOG_KEYS)
        assert row["samples"] > 0
    # Critic warm-up: the actor is frozen on update 1 and trains afterwards.
    assert rows[0]["actor_frozen"] and not rows[1]["actor_frozen"]
    assert torch.equal(after_first[0], before)
    assert not torch.equal(actor_vector(trainer.actor), before)
    assert rows[0]["clip_eps"] == 0.1 and rows[0]["beta"] == pytest.approx(0.1)
    assert rows[0]["opponents_scripted"] == 8
    assert np.isfinite(rows[-1]["aux_script_nll"])
    assert checkpoint_path(tmp_path / "run", "bc", 3).is_file()
    assert read_config(tmp_path / "run" / "config.yaml") == config


def test_three_updates_from_scratch(tmp_path):
    config = PPOConfig.preset("scratch", n_updates=3, **SMALL)
    trainer = SpikeTrainer(config, tmp_path / "run")
    before = actor_vector(trainer.actor)
    trainer.train(on_update_end=None)
    rows = read_log(tmp_path / "run")
    assert len(rows) == 3
    assert not any(r["actor_frozen"] for r in rows)
    assert all(r["beta"] == 0.0 and r["clip_eps"] == 0.2 for r in rows)
    assert all(set(r) == set(LOG_KEYS) for r in rows)
    assert not torch.equal(actor_vector(trainer.actor), before)
    # The checkpoint loads with the eval-side loader.
    actor, _, meta = load_policy(checkpoint_path(tmp_path / "run", "scratch", 3))
    assert meta["update"] == 3
    assert torch.equal(actor_vector(actor), actor_vector(trainer.actor))


def test_batch_holds_only_unmasked_learner_rows(tmp_path):
    config = PPOConfig.preset(
        "scratch", n_updates=1, opponent_bands=[[0, 0.5, 0.5, 0.0]], **SMALL
    )
    trainer = SpikeTrainer(config, tmp_path / "run")
    trainer._collect(0)
    batch, _ = trainer._prepare_batch()
    store = trainer.storage
    train = store.train_rows()
    assert batch.size == int(train.sum()) > 0
    # Team 1 rows join only from self-play envs; act_mask = 0 rows never do.
    # No env resets inside this short rollout, so kinds are those of every step.
    assert not store.dones[: config.n_steps].any()
    self_play = np.repeat(trainer.opponents.kinds == OpponentKind.SELF, 2)
    team1 = trainer.team == 1
    assert self_play.sum() == 8
    assert not (train & ~store.act_mask[: config.n_steps]).any()
    assert not (train[:, team1 & ~self_play]).any()
    assert train[:, team1 & self_play].any()
    assert (store.learner[: config.n_steps] == (~team1 | self_play)).all()


# ---------------------------------------------------------------------------
# Credit through the trainer's buffer, across the rollout boundary
# ---------------------------------------------------------------------------


class RecordingTrainer(SpikeTrainer):
    """Keeps every step's raw rewards and hits, and the rewards after credit."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.raw: list[np.ndarray] = []
        self.infos: list[StepInfo] = []
        self.snapshots: list[np.ndarray] = []

    def _record_step(self, b, rewards, dones, info) -> None:
        self.raw.append(rewards.reshape(-1).astype(np.float64).copy())
        self.infos.append(info.copy())
        super()._record_step(b, rewards, dones, info)

    def _prepare_batch(self):
        out = super()._prepare_batch()
        self.snapshots.append(self.storage.rewards.astype(np.float64).copy())
        return out


@pytest.mark.parametrize("fleet", [False, True], ids=["duel", "fleet"])
def test_credit_lands_on_decision_step_across_rollouts(tmp_path, fleet):
    """Each hit's shooter reward moves to the buffer step stamped with its
    decision_tick (3 ticks before the shot at reaction_ticks 2), including hits
    that land in a later rollout and move into the carried tail rows; with fleets,
    for every one of up to 8 shooters per match."""
    n_steps, t_tail, reaction = 16, 40, 2
    params = {**SMALL, "n_envs": 32, "env_warmup_steps": 200}
    if fleet:
        params.update({"rosters": "fleet_v1", "critic": "fleet"})
    config = PPOConfig.preset(
        "scratch", n_updates=3, t_tail=t_tail, reaction_ticks=reaction, **params
    )
    trainer = RecordingTrainer(config, tmp_path / "run")
    trainer.train(on_update_end=None)
    length = n_steps + t_tail
    n_ships = trainer.n_ships
    total = len(trainer.infos)
    assert total == length + 2 * n_steps

    def rollout_of(step: int) -> int:
        return 0 if step < length else (step - length) // n_steps + 1

    # Reward moves by the rollout in which the hit landed.
    moves = np.zeros((3, total, trainer.rows))
    n_hits = n_moved = n_into_tail = 0
    for step, info in enumerate(trainer.infos):
        k = rollout_of(step)
        window_start = n_steps * k
        for env in np.flatnonzero(info.hit_count):
            for rec in info.hits[env, : info.hit_count[env]]:
                shooter, fire_tick, milli, shield, decision_tick = rec[[0, 2, 3, 4, 5]]
                assert decision_tick == fire_tick - 1 - reaction
                n_hits += 1
                fired_on = step - (int(info.prev_tick[env]) + 1 - int(fire_tick))
                decided_on = fired_on - reaction
                if decided_on < window_start or not info.prev_alive[env, shooter]:
                    continue
                decided = trainer.infos[decided_on]
                if decided.prev_episode_count[env] != info.prev_episode_count[env]:
                    continue
                assert int(decided.prev_tick[env]) == int(decision_tick)
                weight = (
                    credit.SHIELD_DAMAGE_WEIGHT if shield else credit.HULL_DAMAGE_WEIGHT
                )
                row = env * n_ships + shooter
                moves[k, decided_on, row] += weight * milli / 1000.0
                moves[k, step, row] -= weight * milli / 1000.0
                n_moved += 1
                n_into_tail += int(k > 0 and decided_on < window_start + t_tail)
    assert n_hits > 10 and n_moved > 5 and n_into_tail > 0
    raw = np.stack(trainer.raw)
    for k, snapshot in enumerate(trainer.snapshots):
        steps = np.arange(n_steps * k, n_steps * k + length)
        expected = raw[steps] + moves[: k + 1].sum(0)[steps]
        np.testing.assert_allclose(snapshot, expected, atol=1e-5)


# ---------------------------------------------------------------------------
# Opponents
# ---------------------------------------------------------------------------


def test_quota_counts_sum_and_round():
    counts = quota_counts([0.5, 0.3, 0.2], 255)
    assert counts.sum() == 255
    assert np.all(np.abs(counts - np.array([0.5, 0.3, 0.2]) * 255) <= 1)


@pytest.mark.parametrize("update", [0, 599, 600, 1199, 1200, 1999])
def test_opponent_shares_match_schedule_after_resets(update):
    n_envs = 256
    schedule = OpponentSchedule(DEFAULT_BANDS)
    rng = np.random.default_rng(update)
    assigner = OpponentAssigner(n_envs, schedule, rng)
    assigner.assign_all(0, pool_size=0)
    assert assigner.counts()["scripted"] == n_envs
    # Envs reset a few at a time (as episodes end) until every env has reset.
    pending = rng.permutation(n_envs)
    while pending.size:
        take = int(rng.integers(1, 9))
        assigner.assign(pending[:take], update, pool_size=6)
        pending = pending[take:]
    shares = schedule.band(update).shares
    counts = assigner.counts()
    for name, share in zip(("scripted", "self", "snapshot"), shares):
        assert abs(counts[name] - share * n_envs) <= 1, (name, counts)
    snap = assigner.kinds == OpponentKind.SNAPSHOT
    assert ((assigner.snapshot[snap] >= 0) & (assigner.snapshot[snap] < 6)).all()
    assert (assigner.snapshot[~snap] == -1).all()
    # Further resets keep the shares.
    assigner.assign(rng.choice(n_envs, 40, replace=False), update, pool_size=6)
    assert assigner.counts() == counts


def test_empty_pool_plays_snapshot_share_as_self():
    schedule = OpponentSchedule(DEFAULT_BANDS)
    assigner = OpponentAssigner(100, schedule, np.random.default_rng(0))
    assigner.assign_all(1500, pool_size=0)
    assert assigner.counts() == {"scripted": 30, "self": 70, "snapshot": 0}


def test_snapshot_opponents_play_from_the_pool(tmp_path):
    config = PPOConfig.preset(
        "scratch",
        n_updates=4,
        checkpoint_every=1,
        opponent_bands=[[0, 1.0, 0.0, 0.0], [2, 0.0, 0.0, 1.0]],
        **SMALL,
    )
    trainer = SpikeTrainer(config, tmp_path / "run")
    trainer.train(on_update_end=None)
    rows = read_log(tmp_path / "run")
    assert rows[-1]["snapshot_pool"] == [1, 2, 3]
    assert len(trainer.pool) == 4
    # Envs move to snapshots only when they reset; force it to check the forward.
    trainer.opponents.assign_all(3, len(trainer.pool))
    assert trainer.opponents.counts()["snapshot"] == 8
    trainer.config.n_updates = 5
    trainer.train(on_update_end=None)
    assert read_log(tmp_path / "run")[-1]["opponents_snapshot"] == 8


# ---------------------------------------------------------------------------
# Checkpoints, resume, stop
# ---------------------------------------------------------------------------


def small_cli_args() -> list[str]:
    return [f"--set={k}={v}" for k, v in SMALL.items() if k != "n_envs"] + [
        "--n-envs",
        str(SMALL["n_envs"]),
    ]


def test_resume_continues_the_update_index(tmp_path):
    run_dir = tmp_path / "run"
    common = ["ppo", "--run-dir", str(run_dir), *small_cli_args()]
    assert train_spike.main([*common, "--init", "scratch", "--n-updates", "2"]) == 0
    first = torch.load(latest_checkpoint(run_dir, "scratch"), weights_only=True)
    assert first["train"]["next_update"] == 2
    assert train_spike.main([*common, "--resume", "--n-updates", "4"]) == 0
    rows = read_log(run_dir)
    assert [r["update"] for r in rows] == [1, 2, 3, 4]
    # The resumed segment uses fresh env seeds and continues the LR schedule.
    assert rows[2]["env_seed"] != rows[1]["env_seed"]
    assert rows[2]["actor_lr"] == pytest.approx(3e-4 * (1 - 2 / 4))
    assert latest_checkpoint(run_dir, "scratch").name == "ppo_scratch_4.pt"
    # The changed n_updates is recorded; the original config is kept.
    assert read_config(run_dir / "config.yaml").n_updates == 4
    assert read_config(run_dir / "config_before_2.yaml").n_updates == 2


def test_new_run_refuses_an_existing_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "config.yaml").write_text("{}")
    with pytest.raises(SystemExit):
        train_spike.main(["ppo", "--run-dir", str(run_dir), "--init", "scratch"])


def test_stop_request_saves_a_checkpoint(tmp_path):
    config = PPOConfig.preset("scratch", n_updates=50, **SMALL)
    trainer = SpikeTrainer(config, tmp_path / "run")

    def stop_after_first(t: SpikeTrainer, row: dict) -> None:
        if row["update"] == 1:
            t.request_stop()

    assert trainer.train(on_update_end=stop_after_first) == 1
    path = checkpoint_path(tmp_path / "run", "scratch", 1)
    payload = torch.load(path, weights_only=True)
    train = payload["train"]
    assert train["next_update"] == 1
    assert set(train) >= {"actor_opt", "critic_opt", "torch_rng", "numpy_rng", "pool"}
    assert train["pool"] == []
    assert len(read_log(tmp_path / "run")) == 1


def test_sigterm_checkpoints_and_exits_cleanly(tmp_path):
    run_dir = tmp_path / "run"
    cmd = [
        sys.executable,
        "-m",
        "spacefight.train_spike",
        "ppo",
        "--run-dir",
        str(run_dir),
        "--init",
        "scratch",
        "--n-updates",
        "100000",
        *small_cli_args(),
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    proc = subprocess.Popen(
        cmd, cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    try:
        log = run_dir / "log.jsonl"
        deadline = time.monotonic() + 120
        while not (log.exists() and log.read_text().count("\n") >= 1):
            assert proc.poll() is None, proc.communicate()[0].decode()
            assert time.monotonic() < deadline, "no update logged in time"
            time.sleep(0.2)
        proc.send_signal(signal.SIGTERM)
        out, _ = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 0, out.decode()
    path = latest_checkpoint(run_dir, "scratch")
    update = int(path.stem.rsplit("_", 1)[1])
    assert update >= 1
    assert len(read_log(run_dir)) == update
    _, _, meta = load_policy(path)
    assert meta["update"] == update


# ---------------------------------------------------------------------------
# Pieces
# ---------------------------------------------------------------------------


def test_preset_schedules_follow_the_plan():
    bc = PPOConfig.preset("bc.pt")
    assert (bc.tag, bc.actor_lr, bc.critic_lr) == ("bc", 1e-4, 3e-4)
    assert bc.clip(0) == bc.clip(199) == 0.1 and bc.clip(200) == 0.2
    assert bc.actor_frozen(29) and not bc.actor_frozen(30)
    assert bc.beta(0) == bc.beta(30) == pytest.approx(0.1)
    assert bc.beta(365) == pytest.approx(0.05)
    assert bc.beta(700) == bc.beta(2000) == 0.0
    assert bc.lr_scale(0) == 1.0 and bc.lr_scale(1000) == pytest.approx(0.5)
    scratch = PPOConfig.preset("scratch")
    assert (scratch.tag, scratch.actor_lr) == ("scratch", 3e-4)
    assert scratch.clip(0) == 0.2 and not scratch.actor_frozen(0)
    assert scratch.beta(0) == 0.0
    floored = PPOConfig.preset("bc.pt", beta_floor=0.02)
    assert floored.beta(1500) == 0.02


def test_config_yaml_round_trip(tmp_path):
    config = PPOConfig.preset("bc.pt", seed=3, opponent_bands=[[0, 1, 0, 0]])
    spike_ppo.write_config(config, tmp_path / "config.yaml")
    assert read_config(tmp_path / "config.yaml") == config
    with pytest.raises(ValueError):
        PPOConfig.from_dict({**config.to_dict(), "bogus": 1})


def test_compute_gae_matches_a_hand_rollout():
    rewards = np.array([[1.0], [0.0], [2.0]], dtype=np.float32)
    values = np.array([[0.5], [0.4], [0.3]], dtype=np.float32)
    dones = np.array([[False], [True], [False]])
    last = np.array([0.2], dtype=np.float32)
    gamma, lam = 0.9, 0.8
    adv, ret = compute_gae(rewards, values, dones, last, gamma, lam)
    d2 = 2.0 + gamma * 0.2 - 0.3
    d1 = 0.0 - 0.4  # the episode ends on step 1: no bootstrap from step 2
    d0 = 1.0 + gamma * 0.4 - 0.5
    expected = np.array([d0 + gamma * lam * d1, d1, d2])
    np.testing.assert_allclose(adv[:, 0], expected, rtol=1e-6)
    np.testing.assert_allclose(ret, adv + values)


def test_evaluate_heads_and_labels_matches_separate_calls():
    torch.manual_seed(0)
    actor = SpikeActor()
    thruster = np.zeros((16, 8), dtype=bool)
    thruster[:, :5] = True
    turret = np.zeros((16, 6), dtype=bool)
    turret[:, 0] = True
    masks = HeadMasks.from_numpy(thruster, turret, turret.copy())
    obs = torch.randn(16, 385)
    actions = actor.sample(obs, masks).actions
    labels = actor.sample(obs, masks).actions
    lp, ent, label_lp = actor.evaluate_heads_and_labels(obs, masks, actions, labels)
    ref_lp, ref_ent = actor.evaluate_heads(obs, masks, actions)
    torch.testing.assert_close(lp, ref_lp)
    torch.testing.assert_close(ent, ref_ent)
    torch.testing.assert_close(label_lp, actor.head_log_probs(obs, masks, labels))


def _rust_const(name: str) -> float:
    text = (REPO / "crates/sim/src/reward.rs").read_text()
    match = re.search(rf"pub const {name}: f32 = ([-0-9.eE]+);", text)
    assert match, f"{name} not found in reward.rs"
    return float(match.group(1))


def test_mirrored_reward_constants_match_rust():
    assert spike_ppo.FIRE_COST == _rust_const("FIRE_COST")
    assert spike_ppo.ARENA_PENALTY == _rust_const("ARENA_PENALTY")
