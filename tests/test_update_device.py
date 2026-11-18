"""The PPO update on another device (PPOConfig.update_device, docs/PILOT_TRAINING.md):
the default, the same update on cuda as on the CPU, and checkpoints that cross devices.

The cuda tests skip without CUDA. Needs the extension:
``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from pathlib import Path

import pytest
import torch

pytest.importorskip("rlf_sim", reason="rlf_sim extension not built")

from spacefight.env.rust_env import OBS_DIM  # noqa: E402
from spacefight.rl.spike_policy import (  # noqa: E402
    SpikeActor,
    SpikeCritic,
    save_policy,
)
from spacefight.rl.spike_ppo import (  # noqa: E402
    PPOConfig,
    SpikeTrainer,
    checkpoint_path,
    read_config,
    write_config,
)

REPO = Path(__file__).resolve().parent.parent
SMALL = {
    "assets_dir": str(REPO / "assets"),
    "n_envs": 8,
    "n_steps": 16,
    "minibatch": 64,
    "sim_threads": 2,
    "torch_threads": 2,
    "env_warmup_steps": 60,
    "critic_warmup_updates": 0,
}
needs_cuda = pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA")
# One update of the same batch on cuda and on the CPU: float sums in another order.
# Measured on a 1080 Ti: weights within 6e-8, diagnostics within 8e-6 (relative);
# the bounds leave about 20x room.
WEIGHT_ATOL = 1e-6
METRIC_RTOL = 2e-4


def params(module: torch.nn.Module) -> torch.Tensor:
    return torch.cat([p.detach().reshape(-1).clone() for p in module.parameters()])


def all_cpu(obj: object) -> bool:
    if isinstance(obj, torch.Tensor):
        return obj.device.type == "cpu"
    if isinstance(obj, dict):
        return all(all_cpu(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(all_cpu(v) for v in obj)
    return True


@pytest.fixture
def narrow_init(tmp_path: Path) -> Path:
    """A BC-style init four inputs narrower than the sim, so the run widens it and
    NewInputAdam boosts the new columns (the path of a real v8 run)."""
    torch.manual_seed(0)
    path = tmp_path / "bc.pt"
    width = OBS_DIM - 4
    save_policy(
        path, SpikeActor(obs_dim=width), SpikeCritic(obs_dim=width), {"kind": "test"}
    )
    return path


def config_for(init: Path, **overrides: object) -> PPOConfig:
    base = {"n_updates": 1, "obs_dim": OBS_DIM, "new_input_lr_mult": 3.0, **SMALL}
    return PPOConfig.preset(str(init), **{**base, **overrides})


def test_default_is_cpu_and_left_out_of_the_config(tmp_path):
    config = PPOConfig.preset("scratch")
    assert config.update_device == "cpu"
    assert "update_device" not in config.to_dict()
    gpu = PPOConfig.preset("scratch", update_device="cuda:1")
    assert gpu.to_dict()["update_device"] == "cuda:1"
    write_config(gpu, tmp_path / "config.yaml")
    assert read_config(tmp_path / "config.yaml") == gpu
    for bad in ("tpu", "cuda:x", "mps"):
        with pytest.raises(ValueError, match="update_device"):
            PPOConfig.preset("scratch", update_device=bad)


@pytest.mark.skipif(torch.cuda.is_available(), reason="CUDA is available")
def test_cuda_update_device_without_cuda_says_so(tmp_path):
    config = PPOConfig.preset("scratch", update_device="cuda", **SMALL)
    with pytest.raises(RuntimeError, match="update_device=cpu"):
        SpikeTrainer(config, tmp_path / "run")


@needs_cuda
def test_one_update_on_cuda_matches_the_cpu(tmp_path, narrow_init):
    rows = {}
    nets = {}
    for device in ("cpu", "cuda:0"):
        trainer = SpikeTrainer(
            config_for(narrow_init, update_device=device), tmp_path / device
        )
        assert trainer.new_input_start == OBS_DIM - 4
        before = params(trainer.actor)
        rows[device] = trainer.run_update()
        nets[device] = (params(trainer.actor), params(trainer.critic))
        # Back on the CPU after the update: nets and optimiser state.
        assert all(p.device.type == "cpu" for p in trainer.actor.parameters())
        assert all(p.device.type == "cpu" for p in trainer.critic.parameters())
        assert all_cpu(trainer.actor_opt.state_dict())
        assert all_cpu(trainer.critic_opt.state_dict())
        assert not torch.equal(nets[device][0], before)
    cpu, gpu = rows["cpu"], rows["cuda:0"]
    assert cpu["samples"] == gpu["samples"] > 0
    for key in ("pg_loss", "value_loss", "approx_kl", "entropy_mean", "aux_script_nll"):
        assert gpu[key] == pytest.approx(cpu[key], rel=METRIC_RTOL, abs=1e-6), key
    for a, b in zip(nets["cpu"], nets["cuda:0"]):
        assert torch.allclose(a, b, rtol=0.0, atol=WEIGHT_ATOL)


@needs_cuda
def test_cuda_checkpoint_loads_on_cpu_and_resumes_on_either(tmp_path, narrow_init):
    run = tmp_path / "run"
    trainer = SpikeTrainer(config_for(narrow_init, update_device="cuda:0"), run)
    assert trainer.train(on_update_end=None) == 1
    path = checkpoint_path(run, "bc", 1)
    # Every tensor in the file is a CPU tensor, so a machine without CUDA reads it
    # with or without map_location.
    assert all_cpu(torch.load(path, weights_only=True))
    payload = torch.load(path, map_location="cpu", weights_only=True)
    assert payload["train"]["next_update"] == 1
    assert payload["meta"]["config"]["update_device"] == "cuda:0"
    # Resume on the CPU (the laptop), then back on cuda.
    for device, n_updates in (("cpu", 2), ("cuda:0", 3)):
        config = config_for(narrow_init, update_device=device, n_updates=n_updates)
        resumed = SpikeTrainer(config, run, resume=True)
        assert resumed.next_update == n_updates - 1
        assert resumed.train(on_update_end=None) == n_updates
        assert torch.isfinite(params(resumed.actor)).all()
    final = torch.load(checkpoint_path(run, "bc", 3), weights_only=True)
    assert all_cpu(final)
