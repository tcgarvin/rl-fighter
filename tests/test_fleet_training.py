"""Fleet training: the centralised critic, fleet BC / DAgger rows, fleet PPO."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.env.rosters import hull_names_by_id
from spacefight.rl import bc
from spacefight.rl.opponents import OpponentKind
from spacefight.rl.spike_policy import (
    OBS_DIM,
    FleetCritic,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    as_critic_kind,
    load_policy,
    save_policy,
)
from spacefight.rl.spike_ppo import PPOBatch, PPOConfig, SpikeTrainer

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
THREADS = 2
FLEET_SMALL = {
    "assets_dir": ASSETS,
    "n_envs": 8,
    "n_steps": 16,
    "minibatch": 64,
    "sim_threads": THREADS,
    "torch_threads": THREADS,
    "env_warmup_steps": 60,
    "rosters": "fleet_v1",
    "critic": "fleet",
}
torch.set_num_threads(THREADS)


def random_match(groups: int, slots: int, seed: int) -> tuple[torch.Tensor, ...]:
    gen = torch.Generator().manual_seed(seed)
    obs = torch.randn(groups, slots, OBS_DIM, generator=gen)
    obs[..., 0] = 1.0  # present
    team = torch.tensor([[0, 0, 1, 1, -1][:slots]] * groups)
    obs[team < 0] = 0.0
    return obs, team


# ----------------------------------------------------------------- the critic


def test_fleet_critic_from_spike_starts_with_the_spike_values() -> None:
    torch.manual_seed(0)
    spike = SpikeCritic()
    critic = FleetCritic.from_spike(spike)
    obs, team = random_match(3, 5, 1)
    rows = torch.tensor([[0, 0], [1, 2], [2, 3]])
    expected = spike(obs[rows[:, 0], rows[:, 1]])
    torch.testing.assert_close(critic.forward_set(obs, team, rows), expected)
    torch.testing.assert_close(spike.forward_set(obs, team, rows), expected)


def _trained_critic() -> FleetCritic:
    torch.manual_seed(1)
    critic = FleetCritic()
    with torch.no_grad():
        for p in critic.mix.parameters():
            p.normal_(0.0, 0.3)
    return critic


def test_fleet_critic_pools_over_the_set_and_ignores_padding() -> None:
    critic = _trained_critic()
    obs, team = random_match(1, 5, 2)
    rows = torch.tensor([[0, 0]])
    base = critic.forward_set(obs, team, rows)
    # Teammates and enemies are a set: swapping the two enemies changes nothing.
    swapped = obs.clone()
    swapped[0, [2, 3]] = obs[0, [3, 2]]
    torch.testing.assert_close(critic.forward_set(swapped, team, rows), base)
    # Padding slots are ignored whatever they hold.
    noisy = obs.clone()
    noisy[0, 4] = torch.randn(OBS_DIM)
    torch.testing.assert_close(critic.forward_set(noisy, team, rows), base)
    # A dead enemy (present 0) is not pooled: it equals a one-enemy match.
    dead = obs.clone()
    dead[0, 3] = 0.0
    two_slots = obs[:, :4].clone()
    two_slots[0, 3] = 0.0
    one = critic.forward_set(dead, team, rows)
    torch.testing.assert_close(critic.forward_set(two_slots, team[:, :4], rows), one)
    # The context matters once the mix is non-zero.
    assert not torch.allclose(one, base)


def test_fleet_critic_checkpoints_round_trip(tmp_path: Path) -> None:
    critic = _trained_critic()
    path = tmp_path / "p.pt"
    save_policy(path, SpikeActor(), critic, {"k": 1})
    _, loaded, meta = load_policy(path)
    assert isinstance(loaded, FleetCritic) and meta == {"k": 1}
    obs, team = random_match(2, 5, 3)
    rows = torch.tensor([[0, 1], [1, 3]])
    torch.testing.assert_close(
        loaded.forward_set(obs, team, rows), critic.forward_set(obs, team, rows)
    )
    spike_path = tmp_path / "s.pt"
    save_policy(spike_path, SpikeActor(), SpikeCritic(), {})
    assert isinstance(load_policy(spike_path)[1], SpikeCritic)
    with pytest.raises(ValueError):
        as_critic_kind(critic, "spike")


def test_minibatches_keep_groups_whole_and_cover_every_row() -> None:
    obs, team = random_match(6, 5, 4)
    rows = torch.tensor([[0, 0], [0, 1], [1, 2], [2, 0], [2, 3], [4, 1], [5, 0]])
    b = rows.shape[0]
    masks = HeadMasks(
        thruster=torch.ones(b, 8, dtype=torch.bool),
        turret=torch.ones(b, 6, dtype=torch.bool),
        fixed_turret=torch.zeros(b, 6, dtype=torch.bool),
    )
    zeros = torch.zeros(b)
    batch = PPOBatch(
        obs=obs,
        team=team,
        rows=rows,
        masks=masks,
        actions=torch.ones(b, 21, dtype=torch.int64),
        labels=torch.ones(b, 21, dtype=torch.int64),
        old_log_prob=zeros,
        advantages=zeros,
        returns=zeros,
    )
    chunks = batch.minibatches(3)
    seen = torch.cat(chunks).sort().values
    assert seen.tolist() == list(range(b))
    groups = [set(rows[c, 0].tolist()) for c in chunks]
    for a, other in zip(groups, groups[1:]):
        assert not a & other
    group_obs, group_team, local = batch.group_view(chunks[0])
    torch.testing.assert_close(
        group_obs[local[:, 0], local[:, 1]], obs[rows[chunks[0], 0], rows[chunks[0], 1]]
    )


# ----------------------------------------------------------------- fleet BC


@pytest.fixture(scope="module")
def fleet_dataset() -> bc.BCDataset:
    return bc.collect(30_000, n_envs=32, n_threads=THREADS, seed=7, rosters="fleet_v1")


def test_fleet_labels_replay_and_rows_carry_their_hull(
    fleet_dataset: bc.BCDataset,
) -> None:
    data = fleet_dataset
    env = bc.make_env(32, THREADS, 7, 2, bc.DEFAULT_ASSETS, "fleet_v1")
    n_ships = env.n_ships
    valid = bc.valid_heads(data.thruster, data.turret, data.fixed_turret)
    for step in range(int(data.step.max()) + 1):
        rows = np.flatnonzero(data.step == step)
        scripted = env.scripted_actions().reshape(-1, 21).copy()
        slots = data.env_index[rows] * n_ships + data.ship[rows]
        assert np.all(env.act_mask.reshape(-1)[slots])
        np.testing.assert_array_equal(env.hull_id.reshape(-1)[slots], data.hull[rows])
        np.testing.assert_array_equal(
            env.thruster_mask.reshape(-1, 8)[slots], data.thruster[rows]
        )
        mismatch = (scripted[slots] != data.labels[rows]) & valid[rows]
        assert not mismatch.any(), f"label mismatch at step {step}"
        actions = scripted
        actions[slots] = data.executed[rows]
        env.step(actions.reshape(env.actions.shape))
    names = hull_names_by_id()
    assert {names[h] for h in np.unique(data.hull)} == {"fighter", "strafer", "gunship"}
    # The gunship's turrets give it valid slew heads; the fixed guns do not.
    gunship = data.hull == names.index("gunship")
    assert valid[gunship][:, 8:14].any(axis=1).all()
    assert not valid[~gunship][:, 8:14].any()


def test_fleet_bc_eval_reports_every_hull(fleet_dataset: bc.BCDataset) -> None:
    torch.manual_seed(0)
    report = bc.bc_eval(SpikeActor(), fleet_dataset)
    hulls = report["hulls"]
    assert isinstance(hulls, dict)
    assert set(hulls) == {"fighter", "strafer", "gunship"}
    assert hulls["gunship"]["slew"] is not None
    assert hulls["fighter"]["slew"] is None
    json.dumps(report)


def test_fleet_on_policy_rows_are_the_learner_team() -> None:
    torch.manual_seed(0)
    data = bc.collect_on_policy(
        SpikeActor(), 5000, n_envs=16, n_threads=THREADS, seed=4, rosters="fleet_v1"
    )
    env = bc.make_env(16, THREADS, 4, 2, bc.DEFAULT_ASSETS, "fleet_v1")
    team = env.team  # rows of the first step belong to the first matches
    first = data.step == 0
    rows_team = team[data.env_index[first], data.ship[first]]
    np.testing.assert_array_equal(rows_team, data.env_index[first] % 2)
    assert len(np.unique(data.hull)) == 3


# ----------------------------------------------------------------- fleet PPO


def test_fleet_ppo_rows_follow_each_steps_roster(tmp_path: Path) -> None:
    config = PPOConfig.preset(
        "scratch", n_updates=1, opponent_bands=[[0, 0.5, 0.5, 0.0]], **FLEET_SMALL
    )
    trainer = SpikeTrainer(config, tmp_path / "run")
    assert isinstance(trainer.critic, FleetCritic)
    assert trainer.n_ships == 8
    trainer._collect(0)
    batch, _ = trainer._prepare_batch()
    store = trainer.storage
    n = config.n_steps
    train = store.train_rows()
    assert batch.size == int(train.sum()) > 0
    team = store.team[:n]
    self_play = np.repeat(trainer.opponents.kinds == OpponentKind.SELF, 8)
    # Padding never trains; team 1 only in self-play envs (no resets so far).
    assert not (train & (team < 0)).any()
    assert not (train & (team == 1) & ~self_play).any()
    assert (train & (team == 1) & self_play).any()
    # Each training row's masks are those of its own hull at its own step.
    flat = np.flatnonzero(train.reshape(-1))
    np.testing.assert_array_equal(
        batch.masks.thruster.numpy(), store.thruster[:n].reshape(-1, 8)[flat]
    )
    hulls = set(np.unique(store.hull[:n].reshape(-1)[flat]).tolist())
    assert len(hulls) >= 2


def test_fleet_ppo_trains_logs_and_resumes(tmp_path: Path) -> None:
    torch.manual_seed(0)
    seed_ckpt = tmp_path / "seed.pt"
    save_policy(seed_ckpt, SpikeActor(), SpikeCritic(), {"kind": "test"})
    run = tmp_path / "run"
    config = PPOConfig.preset(
        str(seed_ckpt),
        n_updates=2,
        checkpoint_every=1,
        pool_seed=[str(seed_ckpt)],
        opponent_bands=[[0, 0.4, 0.3, 0.3]],
        critic_warmup_updates=1,
        **FLEET_SMALL,
    )
    trainer = SpikeTrainer(config, run)
    assert len(trainer.pool) == 1
    trainer.train(on_update_end=None)
    rows = [json.loads(line) for line in (run / "log.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    last = rows[-1]
    assert last["pg_loss"] is not None and last["value_loss"] is not None
    assert set(last["hull_samples"]) <= {"fighter", "strafer", "gunship"}
    assert isinstance(last["vs_scripted_win_by_class"], dict)
    _, critic, meta = load_policy(run / "checkpoints" / "ppo_bc_2.pt")
    assert isinstance(critic, FleetCritic)
    config.n_updates = 3
    resumed = SpikeTrainer(config, run, resume=True)
    assert resumed.next_update == 2
    assert [p for _, p in resumed.pool.entries][0] == str(seed_ckpt)
    resumed.train(on_update_end=None)
    assert resumed.next_update == 3


def test_fleet_dagger_scores_rounds_on_the_fleet_eval(tmp_path: Path) -> None:
    config = bc.DaggerConfig(
        rounds=1,
        rows_per_round=8000,
        base_rows=8000,
        n_envs=16,
        base_train=bc.TrainConfig(epochs=1, batch_size=1024),
        finetune_train=bc.TrainConfig(epochs=1, batch_size=1024),
        max_rows=16000,
        duel_n=4,
        rosters="fleet_v1",
        fleet_n_per_roster=2,
        best_from_round=1,
    )
    result = bc.dagger(tmp_path, config, n_threads=THREADS)
    assert result.best_round == 1
    assert (tmp_path / "best.pt").is_file()
    for row in result.rounds:
        summary = row["fleet"]["summary"]
        assert set(summary["hull_damage"]) == {"fighter", "strafer", "gunship"}
    report = json.loads((tmp_path / "dagger_eval.json").read_text())
    assert report["best_round"] == 1
    with pytest.raises(ValueError, match="best_from_round"):
        bc.DaggerConfig(rounds=1, best_from_round=2)
