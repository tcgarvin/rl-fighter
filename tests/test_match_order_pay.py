"""Order pay in matches (PPOConfig.match_order_pay_scale, docs/PILOT_TRAINING.md): the
default leaves configs and rewards as they were; at 0 a match row earns its team reward
only while a drill row keeps its order pay; the logged split adds up.

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml  # type: ignore[import-untyped]

pytest.importorskip("rlf_sim", reason="rlf_sim extension not built")

from spacefight.env.drills import ORDER_TICK  # noqa: E402
from spacefight.rl.spike_ppo import PPOConfig, SpikeTrainer, read_config  # noqa: E402

ASSETS = Path(__file__).resolve().parents[1] / "assets"
THREADS = 2
torch.set_num_threads(THREADS)


def _config(**overrides: object) -> PPOConfig:
    """A tiny run: half drills (attack and defend, which pay on hits), half drafted
    matches with commanders, so both kinds of row earn order pay."""
    settings: dict[str, object] = {
        "seed": 5,
        "assets_dir": str(ASSETS),
        "n_envs": 16,
        "n_steps": 96,
        "t_tail": 8,
        "n_updates": 1,
        "minibatch": 256,
        "epochs": 1,
        "sim_threads": THREADS,
        "torch_threads": THREADS,
        "env_warmup_steps": ORDER_TICK + 4,
        "rosters": "pilots_v1",
        "roster_overrides": {
            "drill_share": 0.5,
            "drill_weights": [2, 1, 1],
            "commander_p": 1.0,
        },
        "critic": "fleet",
        "learner_side": "random",
        "opponent_bands": [[0, 0.5, 0.5, 0.0]],
        "order_reward_weight": 1.0,
        "critic_warmup_updates": 0,
        "beta_start": 0.0,
        "checkpoint_every": 100,
    }
    settings.update(overrides)
    return PPOConfig.preset("scratch", **settings)


@pytest.mark.parametrize("bad", [-0.25, -math.inf, math.inf, math.nan])
def test_the_scale_must_be_finite_and_not_negative(bad: float) -> None:
    with pytest.raises(ValueError, match="match_order_pay_scale"):
        _config(match_order_pay_scale=bad)


def test_the_default_is_left_out_of_the_config_and_a_set_scale_is_written(
    tmp_path: Path,
) -> None:
    assert _config().match_order_pay_scale == 1.0
    assert "match_order_pay_scale" not in _config().to_dict()
    assert "match_order_pay_scale" not in _config(match_order_pay_scale=1.0).to_dict()
    cfg = _config(match_order_pay_scale=0.25)
    assert cfg.to_dict()["match_order_pay_scale"] == 0.25
    SpikeTrainer(cfg, tmp_path)
    written = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert written["match_order_pay_scale"] == 0.25
    assert read_config(tmp_path / "config.yaml").match_order_pay_scale == 0.25
    # A config written before the key reads with the default.
    old = _config().to_dict()
    assert PPOConfig.from_dict(old).match_order_pay_scale == 1.0


def _rollout(tmp_path: Path, **overrides: object) -> SpikeTrainer:
    trainer = SpikeTrainer(_config(**overrides), tmp_path)
    trainer._collect(0)
    return trainer


def test_at_0_a_match_row_earns_its_team_reward_and_a_drill_row_its_order_pay(
    tmp_path: Path,
) -> None:
    full = _rollout(tmp_path / "full")
    none = _rollout(tmp_path / "none", match_order_pay_scale=0.0)
    a, b = full.storage, none.storage
    # The same seed flies the same rollout: rewards do not change actions in one.
    np.testing.assert_array_equal(a.drill, b.drill)
    np.testing.assert_array_equal(a.team_reward, b.team_reward)
    drill, match = a.drill & a.learner, ~a.drill & a.learner
    assert drill.any() and match.any()
    assert (a.order_reward[drill] != 0).any(), "drill rows earn order pay"
    assert (a.order_reward[match] != 0).any(), "match rows earn order pay at 1.0"
    # Default: team reward plus the weighted order pay, as before the key.
    np.testing.assert_array_equal(
        a.rewards, a.team_reward + np.float32(1.0) * a.order_reward
    )
    # At 0: a match row's reward is its team reward; a drill row keeps its pay.
    np.testing.assert_array_equal(b.rewards[match], b.team_reward[match])
    assert not b.order_reward[match].any()
    np.testing.assert_array_equal(b.order_reward[drill], a.order_reward[drill])
    np.testing.assert_array_equal(b.rewards[drill], a.rewards[drill])


def test_a_quarter_scale_pays_a_quarter_in_matches_and_the_log_splits_it(
    tmp_path: Path,
) -> None:
    full = _rollout(tmp_path / "full")
    part = _rollout(tmp_path / "part", match_order_pay_scale=0.25)
    a, b = full.storage, part.storage
    match = ~a.drill
    np.testing.assert_allclose(b.order_reward[match], 0.25 * a.order_reward[match])
    np.testing.assert_array_equal(b.order_reward[a.drill], a.order_reward[a.drill])
    new = slice(0, a.length)
    for trainer in (full, part):
        stats = trainer._rollout_stats(new)
        assert stats["reward_order_drill"] + stats["reward_order_match"] == (
            pytest.approx(stats["reward_order_weighted"])
        )
    sa, sb = full._rollout_stats(new), part._rollout_stats(new)
    assert sb["reward_order_drill"] == pytest.approx(sa["reward_order_drill"])
    assert sb["reward_order_match"] == pytest.approx(0.25 * sa["reward_order_match"])
    assert sa["reward_order_match"] != 0.0
