"""Parity of the browser policy (``web/duel/policy.js``) with ``SpikeActor``.

``tools/export_policy.py`` writes the weights; ``tools/web/policy_parity.mjs`` runs the
JS forward pass and head sampling on the same observations under Node. Logits must
agree to 1e-4 and the argmax action rows exactly (masks applied as in
``SpikeActor.sample``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.rl.spike_policy import (
    ACTION_WIDTH,
    HOLD_ROW,
    OBS_DIM,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    save_policy,
)
from tools.export_policy import ExportError, export

REPO = Path(__file__).resolve().parents[1]
PARITY_SCRIPT = REPO / "tools" / "web" / "policy_parity.mjs"
# Lab weights are gitignored, so a worktree points at a checkout that has them.
LAB_CHECKPOINT = Path(
    os.environ.get(
        "RLF_PARITY_CHECKPOINT",
        REPO / "lab/runs/2026-10-28-learnability-spike/bc_dagger/best.pt",
    )
)
LAB_EVAL = Path(
    os.environ.get(
        "RLF_PARITY_EVAL",
        REPO / "lab/runs/2026-10-28-learnability-spike/eval/bc_dagger_vs_script.json",
    )
)
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")


def _random_checkpoint(path: Path, seed: int) -> None:
    """A checkpoint with weights large enough that logits are far from uniform."""
    torch.manual_seed(seed)
    actor = SpikeActor()
    with torch.no_grad():
        for p in actor.parameters():
            p.normal_(0.0, 0.08)
    save_policy(path, actor, SpikeCritic(), {"kind": "test", "sim_version": 2})


def _masks(rng: np.random.Generator, n: int) -> HeadMasks:
    """Fighter masks for half the rows, random slot layouts for the rest."""
    thruster = np.zeros((n, 8), dtype=bool)
    turret = np.zeros((n, 6), dtype=bool)
    fixed = np.zeros((n, 6), dtype=bool)
    thruster[:, :5] = True
    turret[:, 0] = True
    fixed[:, 0] = True
    half = n // 2
    thruster[half:] = rng.random((n - half, 8)) < 0.6
    turret[half:] = rng.random((n - half, 6)) < 0.5
    fixed[half:] = turret[half:] & (rng.random((n - half, 6)) < 0.5)
    return HeadMasks.from_numpy(thruster, turret, fixed)


def _observations(rng: np.random.Generator, n: int) -> np.ndarray:
    """Clipped-normal observations, plus real ones from the Rust env if it is built."""
    obs = np.clip(rng.normal(0.0, 1.0, (n, OBS_DIM)), -5, 5).astype(np.float32)
    try:
        from spacefight.env.rust_env import RustVecEnv
    except ImportError:
        return obs
    env = RustVecEnv(
        REPO / "assets", n_envs=2, fleets=[["fighter"], ["fighter"]], seed=3
    )
    env.reset()
    real = []
    for _ in range(120):
        env.scripted_actions()
        env.step()
        real.append(np.asarray(env.obs).reshape(-1, OBS_DIM).copy())
    picked = np.concatenate(real)[:: max(1, len(real) * 4 // (n // 2))][: n // 2]
    obs[: len(picked)] = picked
    return obs


def _run_js(
    policy_dir: Path, obs: np.ndarray, valid: np.ndarray, tmp: Path
) -> dict[str, list[list[float]]]:
    obs_path, valid_path, out_path = tmp / "obs.f32", tmp / "valid.u8", tmp / "out.json"
    obs.astype("<f4").tofile(obs_path)
    valid.astype(np.uint8).tofile(valid_path)
    assert NODE is not None
    subprocess.run(
        [
            NODE,
            str(PARITY_SCRIPT),
            str(policy_dir),
            str(obs_path),
            str(valid_path),
            str(out_path),
        ],
        check=True,
        cwd=REPO,
    )
    result: dict[str, list[list[float]]] = json.loads(out_path.read_text())
    return result


def _check_parity(
    checkpoint: Path, tmp: Path, sim_version: int, eval_json: Path | None = None
) -> None:
    from spacefight.rl.spike_policy import load_policy

    policy_dir = tmp / "policy"
    export(
        checkpoint,
        policy_dir,
        wasm_sim_version=sim_version,
        wasm_obs_dim=OBS_DIM,
        eval_json=eval_json,
    )
    actor = load_policy(checkpoint)[0].eval()
    rng = np.random.default_rng(0)
    n = 64
    obs = _observations(rng, n)
    masks = _masks(rng, n)
    valid = masks.head_valid().numpy()
    with torch.no_grad():
        want_logits = actor(torch.from_numpy(obs)).numpy()
        want_argmax = actor.sample(
            torch.from_numpy(obs), masks, deterministic=True
        ).actions.numpy()

    got = _run_js(policy_dir, obs, valid, tmp)
    np.testing.assert_allclose(
        np.asarray(got["logits"]), want_logits, atol=1e-4, rtol=0
    )
    np.testing.assert_array_equal(np.asarray(got["argmax"]), want_argmax)
    sampled = np.asarray(got["sampled"])
    hold = np.broadcast_to(np.asarray(HOLD_ROW), sampled.shape)
    assert sampled.shape == (n, ACTION_WIDTH)
    np.testing.assert_array_equal(sampled[~valid], hold[~valid])


def test_js_policy_matches_torch_on_random_weights(tmp_path: Path) -> None:
    ckpt = tmp_path / "random.pt"
    _random_checkpoint(ckpt, seed=1)
    _check_parity(ckpt, tmp_path, sim_version=2)


@pytest.mark.skipif(not LAB_CHECKPOINT.is_file(), reason="lab checkpoint not present")
def test_js_policy_matches_torch_on_lab_checkpoint(tmp_path: Path) -> None:
    # Spike checkpoints predate the sim_version stamp; their v2 eval supplies it.
    _check_parity(LAB_CHECKPOINT, tmp_path, sim_version=2, eval_json=LAB_EVAL)


def test_export_refuses_an_unstamped_checkpoint_without_eval_json(
    tmp_path: Path,
) -> None:
    from spacefight.rl.spike_policy import SpikeActor, SpikeCritic, save_policy

    ckpt = tmp_path / "unstamped.pt"
    save_policy(ckpt, SpikeActor(), SpikeCritic(), {"kind": "test"})
    with pytest.raises(ExportError, match="no sim_version"):
        export(ckpt, tmp_path / "out", wasm_sim_version=3, wasm_obs_dim=OBS_DIM)


def test_export_refuses_a_sim_version_mismatch(tmp_path: Path) -> None:
    ckpt = tmp_path / "random.pt"
    _random_checkpoint(ckpt, seed=2)
    with pytest.raises(ExportError, match="sim_version"):
        export(ckpt, tmp_path / "out", wasm_sim_version=99, wasm_obs_dim=OBS_DIM)


def test_export_refuses_an_obs_dim_mismatch(tmp_path: Path) -> None:
    ckpt = tmp_path / "random.pt"
    _random_checkpoint(ckpt, seed=3)
    with pytest.raises(ExportError, match="obs_dim"):
        export(ckpt, tmp_path / "out", wasm_sim_version=2, wasm_obs_dim=OBS_DIM + 1)
