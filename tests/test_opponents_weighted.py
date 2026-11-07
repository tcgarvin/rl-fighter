"""Weighted enemy sampling: the distribution, the floor, and uniform staying uniform."""

from __future__ import annotations

import dataclasses
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.rl.opponents import (
    NO_SNAPSHOT,
    SAMPLING_PFSP,
    EnemyResults,
    OpponentAssigner,
    OpponentKind,
    OpponentSchedule,
    pfsp_probabilities,
)
from spacefight.rl.spike_ppo import (
    PPOConfig,
    SpikeTrainer,
    latest_checkpoint,
    reseed_pool,
)

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
ALL_SNAPSHOT = OpponentSchedule([[0, 0.0, 0.0, 1.0]])


def assigner(n_envs: int = 64, seed: int = 0, **kwargs: object) -> OpponentAssigner:
    return OpponentAssigner(
        n_envs, ALL_SNAPSHOT, np.random.default_rng(seed), **kwargs  # type: ignore[arg-type]
    )


def draw_shares(
    chooser: OpponentAssigner, pool: int, draws: int = 20_000
) -> np.ndarray:
    counts = Counter(chooser._draw_snapshot(pool) for _ in range(draws))
    return np.array([counts[i] for i in range(pool)]) / draws


def test_harder_opponents_get_more_of_the_draws() -> None:
    probabilities = pfsp_probabilities([0.9, 0.5, 0.1], power=2.0, floor=0.1)
    assert probabilities.sum() == pytest.approx(1.0)
    assert probabilities[2] > probabilities[1] > probabilities[0]


def test_the_distribution_is_the_power_of_the_loss_rate_mixed_with_the_floor() -> None:
    probabilities = pfsp_probabilities([0.5, 0.0], power=2.0, floor=0.2)
    weights = np.array([0.25, 1.0]) / 1.25
    np.testing.assert_allclose(probabilities, 0.8 * weights + 0.2 * 0.5)


def test_the_floor_keeps_an_opponent_the_learner_always_beats() -> None:
    probabilities = pfsp_probabilities([1.0, 0.0, 0.0, 0.0], power=2.0, floor=0.2)
    assert probabilities[0] == pytest.approx(0.2 / 4)
    assert probabilities[1] == pytest.approx(0.8 / 3 + 0.2 / 4)


def test_beating_everyone_every_time_falls_back_to_even() -> None:
    np.testing.assert_allclose(pfsp_probabilities([1.0, 1.0]), [0.5, 0.5])


def test_a_floor_of_one_is_uniform() -> None:
    np.testing.assert_allclose(pfsp_probabilities([1.0, 0.0], floor=1.0), [0.5, 0.5])


@pytest.mark.parametrize(
    ("rates", "kwargs", "message"),
    [
        ([], {}, "no opponents"),
        ([1.5], {}, "win rates"),
        ([float("nan")], {}, "win rates"),
        ([0.5], {"power": -1.0}, "power"),
        ([0.5], {"floor": 0.0}, "floor"),
        ([0.5], {"floor": 1.5}, "floor"),
    ],
)
def test_bad_weighting_input_raises(
    rates: list[float], kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        pfsp_probabilities(rates, **kwargs)


def test_an_unseen_opponent_counts_as_even_and_results_move_the_rate() -> None:
    results = EnemyResults()
    assert results.rate(3) == 0.5
    results.record(3, 1.0)
    assert results.rate(3) == pytest.approx(2.0 / 3.0)
    for _ in range(50):
        results.record(3, 0.0)
    assert results.rate(3) < 0.1
    assert results.rate(0) == 0.5


def test_old_results_fade() -> None:
    fading = EnemyResults(decay=0.5)
    for _ in range(20):
        fading.record(0, 1.0)
    for _ in range(5):
        fading.record(0, 0.0)
    keeping = EnemyResults(decay=0.999)
    for _ in range(20):
        keeping.record(0, 1.0)
    for _ in range(5):
        keeping.record(0, 0.0)
    assert fading.rate(0) < keeping.rate(0)


def test_win_rates_can_be_passed_in() -> None:
    results = EnemyResults()
    results.seed(1, 0.25, matches=1000)
    assert results.rate(1) == pytest.approx(0.25, abs=1e-3)
    with pytest.raises(ValueError):
        results.seed(1, 1.5, matches=1)


def test_results_survive_a_round_trip_through_a_checkpoint_state() -> None:
    results = EnemyResults()
    results.record(2, 1.0)
    results.record(5, 0.0)
    other = EnemyResults()
    other.load_state(results.state())
    assert other.rate(2) == results.rate(2)
    assert other.rate(5) == results.rate(5)


def test_pfsp_draws_follow_the_tracked_results_and_none_drop_out() -> None:
    chooser = assigner(enemy_sampling=SAMPLING_PFSP, pfsp_floor=0.2)
    for _ in range(200):
        chooser.results.record(0, 1.0)  # always beaten by the learner
        chooser.results.record(1, 0.0)  # always beats the learner
    shares = draw_shares(chooser, 3)
    expected = pfsp_probabilities(
        [chooser.results.rate(i) for i in range(3)], floor=0.2
    )
    np.testing.assert_allclose(shares, expected, atol=0.015)
    assert shares[1] > shares[2] > shares[0]
    assert shares[0] >= 0.2 / 3 - 0.015


def test_pfsp_keeps_the_seed_share_and_weights_inside_each_group() -> None:
    chooser = assigner(
        enemy_sampling=SAMPLING_PFSP, n_seeds=2, seed_p=0.5, pfsp_floor=0.2
    )
    for _ in range(200):
        chooser.results.record(1, 0.0)
        chooser.results.record(0, 1.0)
        chooser.results.record(3, 0.0)
        chooser.results.record(2, 1.0)
    shares = draw_shares(chooser, 4)
    assert shares[:2].sum() == pytest.approx(0.5, abs=0.015)
    assert shares[1] > shares[0]
    assert shares[3] > shares[2]


def test_uniform_is_the_default_and_draws_exactly_what_it_always_did() -> None:
    """The draw sequence of the code before weighting existed, from the same seed."""

    def before(rng: np.random.Generator, pool: int, n_seeds: int, seed_p: float) -> int:
        seeds = min(n_seeds, pool)
        if seed_p == 0.0 or seeds == 0:
            return int(rng.integers(pool))
        if seeds == pool or rng.random() < seed_p:
            return int(rng.integers(seeds))
        return seeds + int(rng.integers(pool - seeds))

    for n_seeds, seed_p in ((0, 0.0), (2, 0.5), (3, 1.0), (5, 0.5)):
        chooser = assigner(seed=7, n_seeds=n_seeds, seed_p=seed_p)
        reference = np.random.default_rng(7)
        for step in range(500):
            pool = 3 + step % 5
            assert chooser._draw_snapshot(pool) == before(
                reference, pool, n_seeds, seed_p
            )


def test_uniform_stays_flat_whatever_results_are_offered() -> None:
    chooser = assigner()
    winner = np.zeros(64, dtype=np.int64)
    chooser.assign_all(0, 3)
    chooser.record_results(np.arange(64), winner, np.zeros(64, dtype=np.int8))
    assert chooser.results.state() == []
    np.testing.assert_allclose(draw_shares(chooser, 3), [1 / 3] * 3, atol=0.015)


def test_record_results_scores_wins_draws_and_losses_for_snapshot_envs_only() -> None:
    chooser = assigner(n_envs=4, enemy_sampling=SAMPLING_PFSP)
    chooser.kinds[:] = OpponentKind.SNAPSHOT
    chooser.kinds[3] = OpponentKind.SELF
    chooser.snapshot[:] = [0, 1, 2, NO_SNAPSHOT]
    learner_team = np.array([1, 0, 0, 0], dtype=np.int8)
    winner = np.array([1, 1, -1, 0], dtype=np.int64)
    chooser.record_results(np.arange(4), winner, learner_team)
    assert chooser.results.rate(0) > 0.5  # the learner won on team 1
    assert chooser.results.rate(1) < 0.5
    assert chooser.results.rate(2) == 0.5
    assert len(chooser.results.state()) == 3


def test_ppo_config_defaults_to_uniform_and_validates_weighting() -> None:
    assert PPOConfig.preset("scratch").enemy_sampling == "uniform"
    weighted = PPOConfig.preset("scratch", enemy_sampling="pfsp")
    assert weighted.enemy_pfsp_floor > 0.0
    with pytest.raises(ValueError, match="enemy_sampling"):
        PPOConfig.preset("scratch", enemy_sampling="elo")
    with pytest.raises(ValueError, match="floor"):
        PPOConfig.preset("scratch", enemy_sampling="pfsp", enemy_pfsp_floor=0.0)


def small_config(**overrides: object) -> PPOConfig:
    """Tiny matches on a short clock, so results reach the table within a few updates."""
    return PPOConfig.preset(
        "scratch",
        assets_dir=ASSETS,
        n_envs=8,
        n_steps=16,
        minibatch=64,
        sim_threads=2,
        torch_threads=2,
        time_limit_s=0.3,
        n_updates=4,
        checkpoint_every=1,
        opponent_bands=[[0, 1.0, 0.0, 0.0], [2, 0.0, 0.0, 1.0]],
        **overrides,  # type: ignore[arg-type]
    )


def test_the_trainer_feeds_results_live_and_keeps_them_across_a_resume(
    tmp_path: Path,
) -> None:
    run = tmp_path / "run"
    trainer = SpikeTrainer(small_config(enemy_sampling="pfsp"), run)
    trainer.train(on_update_end=None)
    state = trainer.opponents.results.state()
    assert state, "matches against snapshots ended but no result was recorded"
    assert all(0 <= int(index) < len(trainer.pool) for index, _, _ in state)

    resumed = SpikeTrainer(small_config(enemy_sampling="pfsp"), run, resume=True)
    assert resumed.opponents.results.state() == state


def test_the_uniform_trainer_tracks_nothing_and_adds_nothing_to_its_checkpoint(
    tmp_path: Path,
) -> None:
    run = tmp_path / "run"
    trainer = SpikeTrainer(small_config(), run)
    trainer.train(on_update_end=None)
    assert trainer.opponents.results.state() == []
    payload = torch.load(
        latest_checkpoint(run, trainer.config.tag),
        map_location="cpu",
        weights_only=True,
    )
    assert "enemy_results" not in payload["train"]


def test_reseeding_puts_the_config_seeds_first_and_moves_results_with_their_entry() -> (
    None
):
    entries = [(-1, "a.pt"), (50, "run/50.pt"), (100, "run/100.pt")]
    results = [[0.0, 3.0, 4.0], [1.0, 1.0, 2.0], [2.0, 0.5, 1.0]]
    new_entries, moved = reseed_pool(entries, ["a.pt", "b.pt"], results)
    assert new_entries == [
        (-1, "a.pt"),
        (-1, "b.pt"),
        (50, "run/50.pt"),
        (100, "run/100.pt"),
    ]
    assert moved == [[0.0, 3.0, 4.0], [2.0, 1.0, 2.0], [3.0, 0.5, 1.0]]


def test_reseeding_drops_results_against_a_seed_no_longer_named() -> None:
    entries = [(-1, "a.pt"), (-1, "b.pt"), (50, "run/50.pt")]
    results = [[0.0, 3.0, 4.0], [1.0, 1.0, 2.0], [2.0, 0.5, 1.0]]
    new_entries, moved = reseed_pool(entries, ["b.pt"], results)
    assert new_entries == [(-1, "b.pt"), (50, "run/50.pt")]
    assert moved == [[0.0, 1.0, 2.0], [1.0, 0.5, 1.0]]


def test_a_resume_that_adds_a_seed_draws_it_and_keeps_results_on_their_entry(
    tmp_path: Path,
) -> None:
    seeds = []
    for name in ("seed_a", "seed_b"):
        seed_run = tmp_path / name
        SpikeTrainer(small_config(), seed_run).train(on_update_end=None)
        seeds.append(str(latest_checkpoint(seed_run, "scratch")))

    run = tmp_path / "run"
    first = small_config(enemy_sampling="pfsp", pool_seed=seeds[:1], pool_seed_p=0.5)
    trainer = SpikeTrainer(first, run)
    trainer.train(on_update_end=None)
    before = trainer.pool.entries
    state = trainer.opponents.results.state()
    assert state

    widened = dataclasses.replace(first, pool_seed=seeds, n_updates=6)
    resumed = SpikeTrainer(widened, run, resume=True)
    assert resumed.pool.entries == [(-1, seeds[0]), (-1, seeds[1])] + before[1:]
    expected = sorted([float(i if i == 0 else i + 1), w, m] for i, w, m in state)
    assert resumed.opponents.results.state() == expected
