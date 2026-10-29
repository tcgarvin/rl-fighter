"""Tests for behaviour cloning (spacefight/rl/bc.py) and ``train_spike bc``.

Plan: lab/runs/2026-10-28-learnability-spike/plan.md §4.1 and §8 row C.
"""

from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.env.rust_env import RustVecEnv
from spacefight.rl import bc
from spacefight.rl.spike_policy import ACTION_WIDTH, HEAD_GROUPS, load_policy
from spacefight.train_spike import main

torch.set_num_threads(4)
THREADS = 4
N_ENVS = 64


@pytest.fixture(scope="module")
def small_dataset() -> bc.BCDataset:
    return bc.collect(20_000, n_envs=N_ENVS, n_threads=THREADS, seed=3)


@pytest.fixture(scope="module")
def train_dataset() -> bc.BCDataset:
    return bc.collect(50_000, n_envs=256, n_threads=THREADS, seed=11)


def _valid(dataset: bc.BCDataset) -> np.ndarray:
    return bc.valid_heads(dataset.thruster, dataset.turret, dataset.fixed_turret)


def test_labels_replay_to_scripted_actions(small_dataset: bc.BCDataset) -> None:
    """Re-stepping a fresh env with the executed actions reproduces every label."""
    data = small_dataset
    env = RustVecEnv(
        bc.DEFAULT_ASSETS,
        N_ENVS,
        [["fighter"], ["fighter"]],
        3,
        n_threads=THREADS,
        reaction_ticks=2,
    )
    valid = _valid(data)
    n_ships = env.n_ships
    for step in range(int(data.step.max()) + 1):
        rows = np.flatnonzero(data.step == step)
        scripted = env.scripted_actions().reshape(-1, ACTION_WIDTH).copy()
        slots = data.env_index[rows] * n_ships + data.ship[rows]
        assert np.all(env.act_mask.reshape(-1)[slots])
        mismatch = (scripted[slots] != data.labels[rows]) & valid[rows]
        assert not mismatch.any(), f"label mismatch at step {step}"
        # Rows with act_mask false have no effect, so the script's own action
        # stands in for them.
        actions = scripted
        actions[slots] = data.executed[rows]
        env.step(actions.reshape(env.actions.shape))


def test_executed_equals_label_unless_noised(small_dataset: bc.BCDataset) -> None:
    data = small_dataset
    differs = (data.executed != data.labels) & _valid(data)
    assert not differs[~data.noised].any()
    assert differs[data.noised].sum(-1).max() <= 1
    assert abs(data.stats.noise_rate - 0.15) <= 0.02
    assert data.stats.noise_rate == pytest.approx(float(data.noised.mean()))
    assert data.stats.changed_rate < data.stats.noise_rate


def test_collect_shapes_and_holdout(small_dataset: bc.BCDataset) -> None:
    data = small_dataset
    assert data.n_rows == 20_000
    assert data.obs.dtype == np.float16
    assert data.labels.dtype == np.int8
    held = bc.holdout_envs(N_ENVS, 0.05)
    assert held.sum() == 4
    np.testing.assert_array_equal(data.holdout, held[data.env_index])
    assert 0 < data.stats.holdout_rows < data.n_rows // 5


def test_dart_noise_only_touches_valid_heads() -> None:
    rng = np.random.default_rng(0)
    labels = np.ones((5000, ACTION_WIDTH), dtype=np.int8)
    valid = np.zeros((5000, ACTION_WIDTH), dtype=bool)
    valid[:, [0, 3, 14, 20]] = True
    executed, noised = bc.apply_dart_noise(labels, valid, 1.0, rng)
    assert noised.all()
    changed = executed != labels
    assert not changed[:, ~valid[0]].any()
    assert changed[:, 20].any() and (executed[:, 20] > 2).any()
    assert executed[:, 14].max() <= 1


def test_bc_reaches_throttle_agreement(
    train_dataset: bc.BCDataset, tmp_path: Path
) -> None:
    config = bc.TrainConfig(epochs=2, batch_size=256, seed=0)
    actor, log = bc.train(train_dataset, config)
    assert len(log.epoch_loss) == 2
    assert log.epoch_loss[1] < log.epoch_loss[0]
    report = bc.bc_eval(actor, train_dataset)
    groups = report["groups"]
    assert isinstance(groups, dict)
    assert groups["throttle"]["agreement"] >= 0.9
    assert groups["slew"]["agreement"] is None
    assert groups["slew"]["heads"] == 0
    assert groups["throttle"]["heads"] == 5
    assert 0.0 < groups["fire"]["base_rate"] < 0.5


def test_head_weights() -> None:
    labels = torch.ones((2, ACTION_WIDTH), dtype=torch.int64)
    labels[0, 0] = 2
    labels[1, HEAD_GROUPS["fire"].start] = 1
    labels[0, HEAD_GROUPS["fire"].start] = 0
    weights = bc.head_weights(labels, fire_pos_weight=3.0, throttle_change_weight=2.0)
    assert weights[0, 0] == 2.0 and weights[1, 0] == 1.0
    assert weights[1, 14] == 3.0 and weights[0, 14] == 1.0
    assert weights[:, 20].tolist() == [1.0, 1.0]


def test_cli_writes_loadable_checkpoint(tmp_path: Path) -> None:
    main(
        [
            "bc",
            "--rows",
            "4000",
            "--out",
            str(tmp_path),
            "--seed",
            "1",
            "--threads",
            str(THREADS),
            "--n-envs",
            "32",
            "--epochs",
            "1",
            "--batch-size",
            "1024",
            "--fire-pos-weight",
            "2.0",
        ]
    )
    actor, critic, meta = load_policy(tmp_path / bc.CHECKPOINT_NAME)
    assert meta["source"] == "bc"
    assert (tmp_path / bc.EVAL_NAME).exists()
    obs = torch.zeros((3, 385))
    assert actor(obs).shape == (3, 61)
    assert critic(obs).shape == (3,)
