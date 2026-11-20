"""SIM_VERSION 11 dock block from the trainer's side: a 587-input pilot (v8 to v10)
widens to the 592-float obs with zero new columns (``--set obs_dim=592 --set
new_input_lr_mult=3``), and a 587-input pilot flies the v11 sim on its prefix, where a
dock order reads as a go-to to the bay."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

rlf_sim = pytest.importorskip(
    "rlf_sim",
    reason=(
        "rlf_sim extension not built; run "
        "`uv run maturin develop -m crates/sim-py/Cargo.toml --release`"
    ),
)

from spacefight.env import rust_env  # noqa: E402
from spacefight.env.drills import ORDER_TICK  # noqa: E402
from spacefight.rl.spike_policy import (  # noqa: E402
    PILOT_OBS_DIMS,
    V8_OBS_DIM,
    V11_OBS_DIM,
    FleetCritic,
    SpikeActor,
    SpikeCritic,
    fit_obs,
    save_policy,
)
from spacefight.rl.spike_ppo import (  # noqa: E402
    NewInputAdam,
    PPOConfig,
    SpikeTrainer,
    first_layer_weights,
)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
THREADS = 2
torch.set_num_threads(THREADS)
DOCK_OFF, DOCK_W = rust_env.OBS_LAYOUT["dock"]


@pytest.fixture
def v10_pilot(tmp_path: Path) -> Path:
    """A 587-wide checkpoint with a fleet critic: a pilot trained before docking."""
    torch.manual_seed(11)
    path = tmp_path / "v10.pt"
    critic = FleetCritic.from_spike(SpikeCritic(obs_dim=V8_OBS_DIM))
    save_policy(path, SpikeActor(obs_dim=V8_OBS_DIM), critic, {"sim_version": 10})
    return path


def test_the_v11_widths() -> None:
    assert PILOT_OBS_DIMS[10] == V8_OBS_DIM == rust_env.OBS_DIM_V10 == 587
    assert PILOT_OBS_DIMS[11] == V11_OBS_DIM == rust_env.OBS_DIM == 592
    assert (DOCK_OFF, DOCK_W) == (587, 5)
    # The trainer's table mirrors the sim's for every version the sim flies.
    for version, width in rust_env.PILOT_OBS_DIMS.items():
        assert PILOT_OBS_DIMS[version] == width, version


def test_a_587_wide_pilot_widens_to_592_with_the_dock_columns_zero(
    tmp_path: Path, v10_pilot: Path
) -> None:
    cfg = PPOConfig.preset(
        str(v10_pilot),
        seed=5,
        assets_dir=str(ASSETS),
        n_envs=8,
        n_steps=24,
        t_tail=8,
        n_updates=1,
        minibatch=128,
        epochs=1,
        sim_threads=THREADS,
        torch_threads=THREADS,
        env_warmup_steps=ORDER_TICK + 4,
        rosters="pilots_v1",
        critic="fleet",
        learner_side="random",
        opponent_bands=[[0, 0.5, 0.5, 0.0]],
        critic_warmup_updates=0,
        beta_start=0.0,
        checkpoint_every=100,
        obs_dim=V11_OBS_DIM,
        new_input_lr_mult=3.0,
    )
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    assert trainer.new_input_start == V8_OBS_DIM
    assert trainer.actor.obs_dim == trainer.critic.obs_dim == V11_OBS_DIM
    assert isinstance(trainer.actor_opt, NewInputAdam)
    weights = first_layer_weights(trainer.actor)[0].detach()
    assert not weights[:, V8_OBS_DIM:].any(), "update 0 is the init exactly"
    row = trainer.run_update()
    assert row["new_input_lr"] == pytest.approx(3.0 * float(row["actor_lr"]))  # type: ignore[arg-type]
    assert trainer.storage.obs.shape[-1] == V11_OBS_DIM


def test_a_587_wide_pilot_reads_a_dock_order_as_a_go_to_on_its_prefix() -> None:
    fleets = rlf_sim.mission_rosters("carrier_battle")[0]["fleets"]
    env = rlf_sim.VecEnv(
        str(ASSETS),
        4,
        fleets,
        61,
        time_limit_s=rlf_sim.mission_time_limit_s("carrier_battle"),
        mission="carrier_battle",
        n_threads=THREADS,
    )
    # The order record: has_order, then the kind one-hot (attack, defend, go-to).
    goto_col = (
        rust_env.OBS_LAYOUT["order"][0] + 1 + list(rlf_sim.ORDER_KINDS).index("goto")
    )
    for _ in range(3000):
        env.scripted_actions()
        env.step()
        docking = env.obs[..., DOCK_OFF] == 1.0
        if docking.any():
            rows = env.obs[docking]
            prefix = fit_obs(rows, V8_OBS_DIM)
            assert prefix.shape[-1] == 587
            assert (prefix[:, goto_col] == 1.0).all(), "a go-to in the prefix"
            assert np.abs(rows[:, DOCK_OFF + 3 : DOCK_OFF + 5]).max() <= 1.0 + 1e-5
            return
    raise AssertionError("no ship docked in 3000 steps")
