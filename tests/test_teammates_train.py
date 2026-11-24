"""Mixed teammates (``PPOConfig.teammate_share`` / ``teammate_pool``): in a match that
is not a drill, some of the learner side's strike craft are flown by frozen pool
pilots, drawn slot by slot when the match starts, as on the live page. Those rows train
nothing, and at least one slot of the side stays the learner's."""

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

from spacefight.rl.spike_policy import (  # noqa: E402
    V8_OBS_DIM,
    V11_OBS_DIM,
    FleetCritic,
    SpikeActor,
    SpikeCritic,
    save_policy,
)
from spacefight.rl.spike_ppo import (  # noqa: E402
    NO_TEAMMATE,
    PPOConfig,
    SpikeTrainer,
)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
THREADS = 2
torch.set_num_threads(THREADS)


def _pilot(path: Path, width: int, seed: int) -> Path:
    torch.manual_seed(seed)
    critic = FleetCritic.from_spike(SpikeCritic(obs_dim=width))
    save_policy(path, SpikeActor(obs_dim=width), critic, {"sim_version": 11})
    return path


@pytest.fixture
def learner(tmp_path: Path) -> Path:
    return _pilot(tmp_path / "learner.pt", V11_OBS_DIM, 3)


@pytest.fixture
def teammate(tmp_path: Path) -> Path:
    """A narrower (587-input) teammate, as most live pilots are."""
    return _pilot(tmp_path / "mate.pt", V8_OBS_DIM, 4)


def _config(init: Path, **overrides: object) -> PPOConfig:
    base: dict[str, object] = {
        "seed": 31,
        "assets_dir": str(ASSETS),
        "n_envs": 8,
        "n_steps": 24,
        "t_tail": 8,
        "n_updates": 1,
        "minibatch": 128,
        "epochs": 1,
        "sim_threads": THREADS,
        "torch_threads": THREADS,
        "rosters": "pilots_v1",
        "critic": "fleet",
        "learner_side": "random",
        "opponent_bands": [[0, 1.0, 0.0, 0.0]],
        "critic_warmup_updates": 0,
        "beta_start": 0.0,
        "checkpoint_every": 100,
    }
    base.update(overrides)
    return PPOConfig.preset(str(init), **base)


def test_a_teammate_share_needs_a_pool_and_a_share_in_range(learner: Path) -> None:
    with pytest.raises(ValueError, match="needs a teammate_pool"):
        _config(learner, teammate_share=0.3)
    with pytest.raises(ValueError, match=r"in \[0, 1\]"):
        _config(learner, teammate_share=1.5, teammate_pool=["x.pt"])
    with pytest.raises(ValueError, match="list of paths"):
        _config(learner, teammate_pool="x.pt")


def test_a_config_without_teammates_writes_what_it_did_before(
    learner: Path, teammate: Path
) -> None:
    assert "teammate_share" not in _config(learner).to_dict()
    data = _config(learner, teammate_share=0.3, teammate_pool=[str(teammate)]).to_dict()
    assert data["teammate_share"] == 0.3 and data["teammate_pool"] == [str(teammate)]
    assert PPOConfig.from_dict(data).teammate_share == 0.3


def test_teammates_fly_some_of_the_learners_side_and_train_nothing(
    tmp_path: Path, learner: Path, teammate: Path
) -> None:
    cfg = _config(learner, teammate_share=0.9, teammate_pool=[str(teammate)])
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    shape = (trainer.n_envs, trainer.n_ships)
    team = np.asarray(trainer.env.team, dtype=np.int64).reshape(shape)
    hull = np.asarray(trainer.env.hull_id, dtype=np.int64).reshape(shape)
    side = (team == trainer.learner_team[:, None]) & ~np.isin(hull, trainer.capital_ids)
    mates = trainer.teammate_of != NO_TEAMMATE
    assert mates.any(), "seed 31 draws teammates at 0.9"
    assert not (mates & ~side).any(), "only the learner's own strike craft"
    for k in np.flatnonzero(side.any(axis=1)):
        assert (side[k] & ~mates[k]).any(), f"env {k} keeps a slot for the learner"

    before = trainer.teammate_of.copy()
    row = trainer.run_update()
    assert 0.0 < float(row["teammate_rows_share"]) < 1.0  # type: ignore[arg-type]
    # 24 steps end no match, so the draw held for the whole rollout.
    np.testing.assert_array_equal(trainer.teammate_of, before)
    flat = (before != NO_TEAMMATE).reshape(-1)
    store = trainer.storage
    for b in trainer._collected:
        assert not (store.learner[b] & flat).any(), "a teammate's rows train nothing"
        assert not (store.side[b] & flat).any(), "nor count as the learner's"
        assert (store.learner[b] & side.reshape(-1)).any()


def test_without_a_share_the_learner_flies_its_whole_side(
    tmp_path: Path, learner: Path
) -> None:
    trainer = SpikeTrainer(_config(learner), tmp_path / "run")
    assert (trainer.teammate_of == NO_TEAMMATE).all()
    row = trainer.run_update()
    assert row["teammate_rows_share"] == 0.0


def test_a_drill_has_no_teammates(
    tmp_path: Path, learner: Path, teammate: Path
) -> None:
    cfg = _config(
        learner,
        teammate_share=1.0,
        teammate_pool=[str(teammate)],
        roster_overrides={"drill_share": 1.0},
        order_reward_weight=1.0,
    )
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    assert all(r.drill is not None for r in trainer.env.rosters)
    assert (trainer.teammate_of == NO_TEAMMATE).all()
