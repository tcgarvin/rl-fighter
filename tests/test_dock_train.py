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
from spacefight.env.rosters import (  # noqa: E402
    DRILL_DOCK,
    STATION_ASSAULT,
    citadel_roster,
    hull_names_by_id,
    make_sampler,
    resolve_distribution,
)
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


def test_a_widened_pilot_trains_on_dock_drills_and_logs_them(
    tmp_path: Path, v10_pilot: Path
) -> None:
    """The dock run's shape (lab/runs/2026-11-20-dock-pilot): a 587 pilot widened to
    592, dock drills in the mix, the dock bonus set, carrier battles under the scripted
    commander; the logs carry the dock drills and the matches' recalls."""
    cfg = PPOConfig.preset(
        str(v10_pilot),
        seed=9,
        assets_dir=str(ASSETS),
        n_envs=8,
        n_steps=900,
        t_tail=8,
        n_updates=2,
        minibatch=1024,
        epochs=1,
        sim_threads=THREADS,
        torch_threads=THREADS,
        rosters="pilots_v1",
        roster_overrides={
            "drill_share": 0.7,
            "drill_dock_share": 1.0,
            "commander_p": 1.0,
            "mission_weights": [0.0, 1.0, 0.0, 0.0],
        },
        critic="fleet",
        learner_side="random",
        critic_warmup_updates=0,
        beta_start=0.0,
        checkpoint_every=100,
        obs_dim=V11_OBS_DIM,
        new_input_lr_mult=3.0,
        order_reward_weight=1.0,
        dock_bonus=1.0,
        commander_stable=["scripted"],
    )
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    assert trainer.env.dock_bonus == pytest.approx(1.0)
    row = trainer.run_update()
    episodes = row["drill_episodes"]
    assert isinstance(episodes, dict) and episodes.get("dock", 0) > 0
    assert set(episodes) == {"dock"}, "every drill is a dock drill"
    dock = row["drill_dock"]
    assert isinstance(dock, dict) and dock
    for part in dock.values():
        assert part["docked"] + part["shot_down"] + part["timed_out"] == pytest.approx(
            1
        )
    assert "mission_docks" in row and "mission_docks_hidden" in row
    assert 0.0 < float(row["drill_rows_share"]) < 1.0  # type: ignore[arg-type]
    assert trainer.match_recalls.shape == (8,)


def test_a_default_pilots_run_trains_citadel_assaults_and_dock_drills(
    tmp_path: Path, v10_pilot: Path
) -> None:
    """The owner's rule (2026-11-21): a ``pilots_v1`` run that names only its drill
    share trains what the live page plays, the citadel's station assault among the
    missions, and dock drills among the drills, with no key of its own."""
    cfg = PPOConfig.preset(
        str(v10_pilot),
        seed=23,
        assets_dir=str(ASSETS),
        n_envs=8,
        n_steps=24,
        t_tail=8,
        n_updates=1,
        minibatch=256,
        epochs=1,
        sim_threads=THREADS,
        torch_threads=THREADS,
        env_warmup_steps=ORDER_TICK + 4,
        rosters="pilots_v1",
        roster_overrides={"drill_share": 0.5},
        critic="fleet",
        learner_side="random",
        opponent_bands=[[0, 0.5, 0.5, 0.0]],
        critic_warmup_updates=0,
        beta_start=0.0,
        checkpoint_every=100,
        obs_dim=V11_OBS_DIM,
        new_input_lr_mult=3.0,
        order_reward_weight=1.0,
    )
    dist = cfg.roster_distribution()
    assert dist["mission_weights"] == [0.3, 0.25, 0.25, 0.2]
    assert dist["citadel_share"] == 1.0 and dist["drill_dock_share"] == 0.25
    citadel = citadel_roster().teams
    drawn = make_sampler(resolve_distribution(dist), 1).sample_many(200)
    assaults = [r for r in drawn if r.drill is None and r.mission == STATION_ASSAULT]
    assert assaults and all(r.teams == citadel for r in assaults)
    assert any(r.drill is not None and r.drill.kind == DRILL_DOCK for r in drawn)

    trainer = SpikeTrainer(cfg, tmp_path / "run")
    rosters = trainer.env.rosters
    assert any(r.drill is None and r.teams == citadel for r in rosters), "seed 23"
    assert any(r.drill is not None and r.drill.kind == DRILL_DOCK for r in rosters)
    row = trainer.run_update()
    assert np.isfinite(float(row["value_loss"]))  # type: ignore[arg-type]
    store = trainer.storage
    assert not (store.learner & np.isin(store.hull, trainer.capital_ids)).any()
    citadel_id = hull_names_by_id(ASSETS).index("citadel")
    assert citadel_id in np.asarray(trainer.env.hull_id)
