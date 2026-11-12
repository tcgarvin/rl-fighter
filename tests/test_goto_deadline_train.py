"""Training under SIM_VERSION 8 go-to deadlines: the trainer's pay keys, the 583 -> 587
warm start, a pilot left blind to ``order_time``, and the drill log's go-to counts.

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch
import yaml  # type: ignore[import-untyped]

rlf_sim = pytest.importorskip(
    "rlf_sim",
    reason=(
        "rlf_sim extension not built; run "
        "`uv run maturin develop -m crates/sim-py/Cargo.toml --release`"
    ),
)

from spacefight.env import rust_env  # noqa: E402
from spacefight.env.drills import (  # noqa: E402
    ORDER_TICK,
    DrillGenerator,
    DrillLedger,
)
from spacefight.env.rosters import (  # noqa: E402
    DRILL_GOTO,
    EXTERNAL,
    DrillTag,
    OpeningOrder,
    Roster,
    ShipStart,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402
from spacefight.eval.controllers import Scripted, idle_actions  # noqa: E402
from spacefight.eval.drills import run_pass  # noqa: E402
from spacefight.rl.spike_policy import (  # noqa: E402
    FleetCritic,
    SpikeActor,
    SpikeCritic,
    save_policy,
)
from spacefight.rl.spike_ppo import (  # noqa: E402
    NewInputAdam,
    PPOConfig,
    SpikeTrainer,
    first_layer_weights,
    read_config,
)
from spacefight.train_spike import _ppo_overrides  # noqa: E402

ASSETS = Path(__file__).resolve().parents[1] / "assets"
V7_OBS_DIM = int(rust_env.OBS_DIM_V7)
V8_OBS_DIM = int(rust_env.PILOT_OBS_DIMS[8])
THREADS = 2
torch.set_num_threads(THREADS)
needs_v8 = pytest.mark.skipif(
    rust_env.SIM_VERSION < 8, reason="needs the SIM_VERSION 8 sim (go-to deadlines)"
)


@pytest.fixture
def v7_pilot(tmp_path: Path) -> Path:
    """A 583-wide checkpoint with a fleet critic: a pilot trained before deadlines."""
    torch.manual_seed(8)
    path = tmp_path / "v7.pt"
    critic = FleetCritic.from_spike(SpikeCritic(obs_dim=V7_OBS_DIM))
    save_policy(path, SpikeActor(obs_dim=V7_OBS_DIM), critic, {"sim_version": 7})
    return path


def _config(init: str, **overrides: object) -> PPOConfig:
    """A tiny run on go-to drills and drafted matches."""
    settings: dict[str, object] = {
        "seed": 3,
        "assets_dir": str(ASSETS),
        "n_envs": 8,
        "n_steps": 24,
        "t_tail": 8,
        "n_updates": 1,
        "minibatch": 128,
        "epochs": 1,
        "sim_threads": THREADS,
        "torch_threads": THREADS,
        "env_warmup_steps": ORDER_TICK + 4,
        "rosters": "pilots_v1",
        "roster_overrides": {"drill_share": 0.75, "drill_weights": [1, 0, 0]},
        "critic": "fleet",
        "learner_side": "random",
        "opponent_bands": [[0, 0.5, 0.5, 0.0]],
        "order_reward_weight": 1.0,
        "critic_warmup_updates": 0,
        "beta_start": 0.0,
        "checkpoint_every": 100,
    }
    settings.update(overrides)
    return PPOConfig.preset(init, **settings)


# ------------------------------------------------------------------ config keys


@pytest.mark.parametrize("key", ["goto_timed_bonus", "goto_miss_penalty"])
@pytest.mark.parametrize("bad", [-0.1, math.inf, math.nan, "1", True])
def test_go_to_pay_must_be_a_finite_number_that_is_not_negative(
    key: str, bad: object
) -> None:
    with pytest.raises(ValueError, match=key):
        _config("scratch", **{key: bad})


def test_go_to_pay_defaults_to_the_sim_s() -> None:
    cfg = _config("scratch")
    assert cfg.goto_timed_bonus == rust_env.DEFAULT_GOTO_TIMED_BONUS == 1.0
    assert cfg.goto_miss_penalty == rust_env.DEFAULT_GOTO_MISS_PENALTY == 1.0


@needs_v8
def test_go_to_pay_reaches_the_env_and_the_run_s_config_file(tmp_path: Path) -> None:
    cfg = _config("scratch", goto_timed_bonus=0.5, goto_miss_penalty=2.0)
    trainer = SpikeTrainer(cfg, tmp_path)
    assert trainer.env.goto_timed_bonus == 0.5
    assert trainer.env.goto_miss_penalty == 2.0
    written = yaml.safe_load((tmp_path / "config.yaml").read_text())
    assert written["goto_timed_bonus"] == 0.5 and written["goto_miss_penalty"] == 2.0
    assert read_config(tmp_path / "config.yaml").goto_miss_penalty == 2.0


def test_a_config_written_before_the_keys_existed_reads_with_the_defaults() -> None:
    old = _config("scratch").to_dict()
    del old["goto_timed_bonus"], old["goto_miss_penalty"]
    assert PPOConfig.from_dict(old).goto_timed_bonus == 1.0


def test_the_cli_sets_go_to_pay_with_set() -> None:
    args = argparse.Namespace(
        n_updates=None,
        n_envs=None,
        n_steps=None,
        seed=None,
        sim_threads=None,
        torch_threads=None,
        overrides=["goto_timed_bonus=0.6", "goto_miss_penalty=0"],
    )
    assert _ppo_overrides(args) == {"goto_timed_bonus": 0.6, "goto_miss_penalty": 0}


# ------------------------------------------------------------------ widths


@needs_v8
def test_a_583_wide_pilot_widens_to_587_and_trains_on_drills_with_deadlines(
    tmp_path: Path, v7_pilot: Path
) -> None:
    cfg = _config(str(v7_pilot), obs_dim=V8_OBS_DIM, new_input_lr_mult=3.0)
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    assert trainer.new_input_start == V7_OBS_DIM
    assert trainer.actor.obs_dim == trainer.critic.obs_dim == V8_OBS_DIM == 587
    assert isinstance(trainer.actor_opt, NewInputAdam)
    before = first_layer_weights(trainer.actor)[0].detach().clone()
    assert not before[:, V7_OBS_DIM:].any(), "update 0 is the init exactly"
    timed = [r for r in trainer.env.rosters if r.drill is not None and r.drill.timed]
    assert timed, "seed 3 draws go-to drills with a deadline"
    row = trainer.run_update()
    assert row["new_input_lr"] == pytest.approx(3.0 * float(row["actor_lr"]))  # type: ignore[arg-type]
    assert row["pg_loss"] is not None and row["reward_order"] is not None
    after = first_layer_weights(trainer.actor)[0].detach()
    assert (after[:, V7_OBS_DIM:] != 0).any(), "the order_time columns learn"
    # The learner saw the order_time block: has_deadline is 1 on a timed go-to's rows.
    offset = rust_env.OBS_LAYOUT["order_time"][0]
    assert trainer.storage.obs.shape[-1] == V8_OBS_DIM
    assert (trainer.storage.obs[..., offset] == 1.0).any()


@needs_v8
def test_a_583_wide_pilot_trains_blind_to_order_time_under_the_v8_sim(
    tmp_path: Path, v7_pilot: Path
) -> None:
    trainer = SpikeTrainer(_config(str(v7_pilot), obs_dim=V7_OBS_DIM), tmp_path / "run")
    assert trainer.new_input_start == 0, "nothing to widen"
    assert trainer.actor.obs_dim == trainer.critic.obs_dim == V7_OBS_DIM
    assert trainer.storage.obs.shape[-1] == V7_OBS_DIM
    assert any(r.drill is not None and r.drill.timed for r in trainer.env.rosters)
    row = trainer.run_update()
    assert row["pg_loss"] is not None and row["new_input_lr"] is None
    assert first_layer_weights(trainer.actor)[0].shape[1] == V7_OBS_DIM


# ------------------------------------------------------------------ the drill log


def _quick_goto(deadline_tick: int, clock_ticks: int) -> Roster:
    """A go-to no ship can make: a fighter at rest 500 m from the circle."""
    order = OpeningOrder(
        0,
        0,
        (0,),
        DRILL_GOTO,
        point=(250.0, 0.0),
        radius=20.0,
        deadline_tick=deadline_tick,
    )
    return Roster(
        (("fighter",), ("fighter",)),
        commanders=(EXTERNAL, EXTERNAL),
        start_layout=(
            ShipStart(-270.0, 0.0, 0.0, 0.0, 0.0),
            ShipStart(0.0, 330.0, 0.0, 0.0, 0.0),
        ),
        opening_orders=(order,),
        time_limit_s=clock_ticks / 30.0,
        drill=DrillTag(DRILL_GOTO, (0,), deadlines=(deadline_tick,), timed=True),
    )


@needs_v8
def test_a_missed_deadline_in_training_is_logged_as_missed_and_not_as_a_success(
    tmp_path: Path,
) -> None:
    trainer = SpikeTrainer(
        _config("scratch", n_steps=128, env_warmup_steps=0), tmp_path
    )
    for i in range(trainer.n_envs):
        trainer.env.set_next_roster(i, _quick_goto(ORDER_TICK + 10, ORDER_TICK + 40))
    trainer.env.reset()
    trainer.env.roster_sampler = None
    trainer.opponents.assign_all(
        0, 0, forced_scripted=np.arange(trainer.n_envs, dtype=np.int64)
    )
    trainer.learner_team[:] = 0
    trainer._note_new_matches(np.arange(trainer.n_envs))
    tally, _ = trainer._collect(0)
    fields: dict[str, Any] = tally.log_fields()
    assert fields["drill_episodes"] == {DRILL_GOTO: trainer.n_envs}
    assert fields["drill_success"] == {DRILL_GOTO: 0.0}
    assert fields["drill_goto_timed_ships"] == trainer.n_envs
    assert fields["drill_goto_missed"] == 1.0
    # The sim charged each ship the miss once, and the trainer stored it as order pay.
    assert trainer.storage.order_reward.min() == pytest.approx(-1.0, abs=0.05)


def test_no_go_to_drills_logs_no_missed_share() -> None:
    from spacefight.rl.spike_ppo import EpisodeTally

    fields = EpisodeTally().log_fields()
    assert fields["drill_goto_timed_ships"] == 0 and fields["drill_goto_missed"] is None


@needs_v8
def test_the_training_ledger_counts_the_arrivals_the_eval_counts() -> None:
    """Script pilots in real go-to drills: the ledger read before every step, as the
    trainer reads it, gives the eval's count of ships in time."""
    specs = DrillGenerator(ASSETS).generate_many(DRILL_GOTO, 12, 3000)
    records = run_pass(Scripted(), specs, 5, n_threads=THREADS)
    in_time = [
        sum(ship.outcome() == "arrived" for ship in record.ships) for record in records
    ]
    env = RustVecEnv(
        ASSETS,
        len(specs),
        specs[0].roster().fleets(),
        5,
        n_threads=THREADS,
        max_ships=max(s.roster().n_ships for s in specs),
        commanders=(EXTERNAL, EXTERNAL),
    )
    for i, spec in enumerate(specs):
        env.set_next_roster(i, spec.roster())
    env.reset()
    ledger = DrillLedger(env.n_envs, env.n_ships)
    for i in range(env.n_envs):
        ledger.begin(i, env.rosters[i].drill)
    running = np.ones(env.n_envs, dtype=np.bool_)
    counted = [-1] * env.n_envs
    missed = [0] * env.n_envs
    for _ in range(max(s.clock_ticks for s in specs) + 2):
        tracks = env.order_tracks()
        ledger.see_tracks(
            tracks["arrived"] & running[:, None],
            tracks["missed"] & running[:, None],
            np.asarray(env.raw.alive, dtype=np.bool_),
            np.asarray(env.raw.tick),
        )
        actions = idle_actions(env.n_envs * env.n_ships).reshape(
            env.n_envs, env.n_ships, -1
        )
        live = running[:, None] & env.act_mask
        actions[live] = env.scripted_actions()[live]
        _, _, dones, _ = env.step(actions)
        for i in np.flatnonzero(running & dones):
            outcome = ledger.finish(int(i))
            counted[int(i)], missed[int(i)] = outcome.successes, outcome.missed
        running &= ~dones
        if not running.any():
            break
    assert counted == in_time
    assert sum(in_time) > 0
    for spec, n_missed, n_in_time in zip(specs, missed, in_time):
        if not spec.timed:
            assert n_missed == 0
        else:
            assert n_missed <= len(spec.pilots) - n_in_time
