"""Opponent schedule, per-env opponent assignment and the frozen-snapshot pool.

Spec: ``lab/runs/2026-10-28-learnability-spike/plan.md`` §4.2. The learner is team 0
in every env; team 1 is played by one of three opponent kinds:

* ``SCRIPTED``: the Rust scripted pilot (``env.scripted_actions()``).
* ``SELF``: mirror self-play, the learner's current weights; team 1 rows join the
  PPO batch.
* ``SNAPSHOT``: a frozen actor from the pool, sampled uniformly; its rows do not
  join the batch. The pool holds the run's ``pool_seed`` checkpoints (e.g. frozen
  fleet pilot v1) first, then periodic checkpoints. With ``seed_p`` > 0 a snapshot env
  plays a seed entry with that probability (uniform among seeds) and a periodic
  checkpoint otherwise, so a seed keeps its share as the pool grows. Each entry
  flies on ``obs[..., :actor.obs_dim]`` (a 385-wide v1 in a 403-wide sim).

Weighted enemy sampling (``docs/PILOT_TRAINING.md`` section 3, off by default). With
``enemy_sampling="pfsp"``, prioritized fictitious self-play (Vinyals et al. 2019) draws
snapshots in proportion to ``(1 - learner's win rate) ** power``, so opponents that beat
the learner come up more, and a ``floor`` share of draws stays even across the entries so
none drop out. It replaces the uniform draw inside each group: ``seed_p`` still splits
seeds from periodic checkpoints first, so a seed keeps its share. Win rates are tracked
per pool entry from finished matches (``record_results``) with a fading memory, or passed
in with ``EnemyResults.seed``. An opponent with no results counts as even. ``SCRIPTED``
and ``SELF`` keep their band shares; only frozen-pool draws are weighted. The default
``"uniform"`` draws exactly what it always did from the same generator, so old configs
and resumes are unchanged.

Order drills (``docs/PILOT_TRAINING.md`` section 2) always fight the script. A drill env is
held out of the quota (``force_scripted``), so the band shares still describe the matches.

Each env keeps its opponent for a whole episode and is reassigned when it resets.
Assignment is by quota, not by independent draws: a resetting env takes the kind
whose count is furthest below its target for the current update band, so once every
env has reset inside a band the counts equal the band's shares rounded to whole
envs (largest remainder), i.e. within ±1 env of ``share * n_envs``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from spacefight.rl.spike_policy import SpikeActor, load_policy


class OpponentKind(IntEnum):
    """Who plays team 1 of an env."""

    SCRIPTED = 0
    SELF = 1
    SNAPSHOT = 2


KIND_NAMES: dict[OpponentKind, str] = {
    OpponentKind.SCRIPTED: "scripted",
    OpponentKind.SELF: "self",
    OpponentKind.SNAPSHOT: "snapshot",
}

# Snapshot index of an env that does not play a snapshot.
NO_SNAPSHOT = -1

SAMPLING_UNIFORM = "uniform"
SAMPLING_PFSP = "pfsp"
ENEMY_SAMPLINGS: tuple[str, ...] = (SAMPLING_UNIFORM, SAMPLING_PFSP)
# AlphaStar's "hard" weighting uses power 2.
DEFAULT_PFSP_POWER = 2.0
# Share of frozen-pool draws spread evenly, so every entry keeps floor / K at least.
DEFAULT_PFSP_FLOOR = 0.2
# Pseudo-matches at an even score behind every tracked win rate.
RESULT_PRIOR_MATCHES = 2.0
# Each new result fades an opponent's older ones by this: a memory of about 100 matches,
# since the learner keeps changing and an old result says less about it.
RESULT_DECAY = 0.99


@dataclass(frozen=True)
class OpponentBand:
    """Opponent shares from ``start_update`` (inclusive) until the next band.

    Attributes:
        start_update: First update index (0-based) of the band.
        scripted: Share of envs against the scripted pilot.
        self_play: Share of envs in mirror self-play.
        snapshot: Share of envs against a frozen pool snapshot.
    """

    start_update: int
    scripted: float
    self_play: float
    snapshot: float

    def __post_init__(self) -> None:
        shares = (self.scripted, self.self_play, self.snapshot)
        if self.start_update < 0:
            raise ValueError(f"start_update must be >= 0, got {self.start_update}")
        if any(s < 0.0 for s in shares) or abs(sum(shares) - 1.0) > 1e-6:
            raise ValueError(f"shares must be >= 0 and sum to 1, got {shares}")

    @property
    def shares(self) -> tuple[float, float, float]:
        """Shares indexed by ``OpponentKind``."""
        return (self.scripted, self.self_play, self.snapshot)


# Plan §4.2 schedule: (start update, scripted, self, snapshot).
DEFAULT_BANDS: tuple[tuple[int, float, float, float], ...] = (
    (0, 1.0, 0.0, 0.0),
    (600, 0.5, 0.3, 0.2),
    (1200, 0.3, 0.4, 0.3),
)


class OpponentSchedule:
    """Piecewise-constant opponent shares by update band.

    Args:
        bands: ``(start_update, scripted, self, snapshot)`` rows; the first must
            start at 0 and starts must increase.

    Raises:
        ValueError: Empty, unsorted or invalid bands.
    """

    def __init__(self, bands: Sequence[Sequence[float]]) -> None:
        if not bands:
            raise ValueError("at least one opponent band is required")
        parsed = []
        for row in bands:
            if len(row) != 4:
                raise ValueError(
                    f"band rows are (start, scripted, self, snapshot), got {row}"
                )
            parsed.append(
                OpponentBand(int(row[0]), float(row[1]), float(row[2]), float(row[3]))
            )
        starts = [b.start_update for b in parsed]
        if starts[0] != 0 or any(b <= a for a, b in zip(starts, starts[1:])):
            raise ValueError(f"band starts must begin at 0 and increase, got {starts}")
        self.bands: tuple[OpponentBand, ...] = tuple(parsed)

    def band(self, update: int) -> OpponentBand:
        """The band in force at ``update`` (0-based)."""
        current = self.bands[0]
        for band in self.bands:
            if band.start_update <= update:
                current = band
        return current

    def targets(self, update: int, n_envs: int, pool_size: int) -> NDArray[np.int64]:
        """Whole-env target counts per kind at ``update``.

        With an empty snapshot pool the snapshot share plays the current weights
        (mirror self-play) instead: the closest available stand-in.
        """
        shares = list(self.band(update).shares)
        if pool_size == 0:
            shares[OpponentKind.SELF] += shares[OpponentKind.SNAPSHOT]
            shares[OpponentKind.SNAPSHOT] = 0.0
        return quota_counts(shares, n_envs)


def quota_counts(shares: Sequence[float], n: int) -> NDArray[np.int64]:
    """Split ``n`` into whole counts proportional to ``shares`` (largest remainder).

    Each count is within 1 of ``share * n`` and the counts sum to ``n``.
    """
    exact = np.asarray(shares, dtype=np.float64) * n
    counts = np.floor(exact).astype(np.int64)
    remainder = n - int(counts.sum())
    order = np.argsort(-(exact - counts), kind="stable")
    counts[order[:remainder]] += 1
    return counts


def pfsp_probabilities(
    win_rates: Sequence[float] | NDArray[np.float64],
    power: float = DEFAULT_PFSP_POWER,
    floor: float = DEFAULT_PFSP_FLOOR,
) -> NDArray[np.float64]:
    """Draw probabilities over opponents from the learner's win rate against each.

    Args:
        win_rates: The learner's score rate against each opponent, in ``[0, 1]``.
        power: Exponent on ``1 - win_rate``; higher leans harder on the toughest.
        floor: Share of draws spread evenly, in ``(0, 1]``. Every opponent's
            probability is at least ``floor / len(win_rates)``.

    Returns:
        Probabilities summing to 1. If the learner beats every opponent every time the
        weights are all zero and the draw is even.

    Raises:
        ValueError: No opponents, or an argument out of range.
    """
    rates = np.asarray(win_rates, dtype=np.float64)
    if rates.size == 0:
        raise ValueError("no opponents to weight")
    if not np.all((rates >= 0.0) & (rates <= 1.0)):
        raise ValueError(f"win rates must be in [0, 1], got {rates}")
    check_pfsp_settings(power, floor)
    even = np.full(rates.size, 1.0 / rates.size)
    weights = (1.0 - rates) ** power
    total = weights.sum()
    hard = weights / total if total > 0.0 else even
    return (1.0 - floor) * hard + floor * even


def check_pfsp_settings(power: float, floor: float) -> None:
    """Raise ``ValueError`` for a negative ``power`` or a ``floor`` outside ``(0, 1]``.

    A floor of 0 is refused because it would let an opponent drop out, which the plan
    rules out.
    """
    if power < 0.0:
        raise ValueError(f"pfsp power must be >= 0, got {power}")
    if not 0.0 < floor <= 1.0:
        raise ValueError(f"pfsp floor must be in (0, 1], got {floor}")


class EnemyResults:
    """The learner's fading score against each frozen-pool entry.

    An entry's rate is ``(wins + prior / 2) / (matches + prior)``, where both counts
    fade by ``decay`` with each new result against that entry.

    Args:
        decay: Fade per result, in ``[0, 1)``.
        prior_matches: Pseudo-matches at an even score.

    Raises:
        ValueError: An argument out of range.
    """

    def __init__(
        self,
        decay: float = RESULT_DECAY,
        prior_matches: float = RESULT_PRIOR_MATCHES,
    ) -> None:
        if not 0.0 <= decay < 1.0:
            raise ValueError(f"decay must be in [0, 1), got {decay}")
        if prior_matches <= 0.0:
            raise ValueError(f"prior_matches must be positive, got {prior_matches}")
        self.decay = decay
        self.prior_matches = prior_matches
        self._counts: dict[int, tuple[float, float]] = {}

    def record(self, index: int, score: float) -> None:
        """Add one result against entry ``index``.

        Args:
            index: Pool index.
            score: 1 for a learner win, 0.5 for a draw, 0 for a loss.

        Raises:
            ValueError: ``score`` outside ``[0, 1]``.
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {score}")
        wins, matches = self._counts.get(index, (0.0, 0.0))
        self._counts[index] = (self.decay * wins + score, self.decay * matches + 1.0)

    def seed(self, index: int, win_rate: float, matches: float) -> None:
        """Set entry ``index`` from a rate measured elsewhere, as if over ``matches``.

        Raises:
            ValueError: ``win_rate`` outside ``[0, 1]`` or negative ``matches``.
        """
        if not 0.0 <= win_rate <= 1.0 or matches < 0.0:
            raise ValueError(f"bad seed: win rate {win_rate} over {matches} matches")
        self._counts[index] = (win_rate * matches, matches)

    def rate(self, index: int) -> float:
        """The learner's score rate against entry ``index``."""
        wins, matches = self._counts.get(index, (0.0, 0.0))
        return (wins + self.prior_matches / 2.0) / (matches + self.prior_matches)

    def state(self) -> list[list[float]]:
        """``[index, wins, matches]`` rows, for a checkpoint's train state."""
        return [[float(i), w, m] for i, (w, m) in sorted(self._counts.items())]

    def load_state(self, rows: Sequence[Sequence[float]]) -> None:
        """Replace the counts with ``state`` output."""
        self._counts = {int(i): (float(w), float(m)) for i, w, m in rows}


class OpponentAssigner:
    """Per-env opponent kind and snapshot index, reassigned on reset by quota.

    Args:
        n_envs: Number of envs.
        schedule: Opponent shares per update band.
        rng: Generator for tie-breaks and snapshot draws.
        n_seeds: Pool entries that are seeds, at its start.
        seed_p: Chance a snapshot env plays a seed entry (module docstring).
        enemy_sampling: ``"uniform"`` or ``"pfsp"`` (module docstring).
        pfsp_power: ``pfsp_probabilities``'s power.
        pfsp_floor: ``pfsp_probabilities``'s floor.
    """

    def __init__(
        self,
        n_envs: int,
        schedule: OpponentSchedule,
        rng: np.random.Generator,
        n_seeds: int = 0,
        seed_p: float = 0.0,
        enemy_sampling: str = SAMPLING_UNIFORM,
        pfsp_power: float = DEFAULT_PFSP_POWER,
        pfsp_floor: float = DEFAULT_PFSP_FLOOR,
    ) -> None:
        if n_envs <= 0:
            raise ValueError(f"n_envs must be positive, got {n_envs}")
        if n_seeds < 0 or not 0.0 <= seed_p <= 1.0:
            raise ValueError(f"need n_seeds >= 0 and seed_p in [0, 1], got {seed_p}")
        if enemy_sampling not in ENEMY_SAMPLINGS:
            raise ValueError(
                f"enemy_sampling must be one of {ENEMY_SAMPLINGS}, got {enemy_sampling}"
            )
        check_pfsp_settings(pfsp_power, pfsp_floor)
        self.n_envs = n_envs
        self.schedule = schedule
        self.rng = rng
        self.n_seeds = n_seeds
        self.seed_p = seed_p
        self.enemy_sampling = enemy_sampling
        self.pfsp_power = pfsp_power
        self.pfsp_floor = pfsp_floor
        self.results = EnemyResults()
        self.kinds = np.full(n_envs, OpponentKind.SCRIPTED, dtype=np.int8)
        self.snapshot = np.full(n_envs, NO_SNAPSHOT, dtype=np.int64)
        # Envs held out of the quota, flying the script (drills).
        self.forced = np.zeros(n_envs, dtype=np.bool_)

    def assign_all(
        self,
        update: int,
        pool_size: int,
        forced_scripted: Sequence[int] | NDArray[np.integer] = (),
    ) -> None:
        """Assign every env from scratch (start of training or of a resume), the
        ``forced_scripted`` envs to the script, outside the quota."""
        self.kinds[:] = -1
        self.forced[:] = False
        self.force_scripted(forced_scripted)
        self.assign(np.flatnonzero(~self.forced), update, pool_size)

    def force_scripted(self, env_ids: Sequence[int] | NDArray[np.integer]) -> None:
        """``env_ids`` fight the script this episode, outside the quota. The next
        ``assign`` of an env puts it back in."""
        ids = np.asarray(env_ids, dtype=np.int64)
        self.kinds[ids] = OpponentKind.SCRIPTED
        self.snapshot[ids] = NO_SNAPSHOT
        self.forced[ids] = True

    def assign(self, env_ids: NDArray[np.integer], update: int, pool_size: int) -> None:
        """Reassign ``env_ids`` (envs that just reset) to the most-needed kinds.

        Args:
            env_ids: Indices of the envs to reassign.
            update: Current update index (selects the band).
            pool_size: Number of snapshots available to sample from.
        """
        if len(env_ids) == 0:
            return
        ids = np.asarray(env_ids, dtype=np.int64)
        self.forced[ids] = False
        n_quota = self.n_envs - int(self.forced.sum())
        targets = self.schedule.targets(update, n_quota, pool_size)
        self.kinds[ids] = -1
        counts = np.bincount(
            self.kinds[(self.kinds >= 0) & ~self.forced], minlength=len(OpponentKind)
        ).astype(np.int64)
        for env in self.rng.permutation(ids):
            deficit = targets - counts
            best = np.flatnonzero(deficit == deficit.max())
            kind = int(best[self.rng.integers(len(best))])
            self.kinds[env] = kind
            counts[kind] += 1
            if kind == OpponentKind.SNAPSHOT:
                self.snapshot[env] = self._draw_snapshot(pool_size)
            else:
                self.snapshot[env] = NO_SNAPSHOT

    def _draw_snapshot(self, pool_size: int) -> int:
        """A pool index: from the whole pool, or a seed entry with ``seed_p``."""
        seeds = min(self.n_seeds, pool_size)
        if self.seed_p == 0.0 or seeds == 0:
            return self._draw_among(0, pool_size)
        if seeds == pool_size or self.rng.random() < self.seed_p:
            return self._draw_among(0, seeds)
        return self._draw_among(seeds, pool_size)

    def _draw_among(self, start: int, stop: int) -> int:
        """One index of ``start..stop``, even or weighted (module docstring)."""
        size = stop - start
        if self.enemy_sampling == SAMPLING_UNIFORM:
            return start + int(self.rng.integers(size))
        probabilities = pfsp_probabilities(
            [self.results.rate(i) for i in range(start, stop)],
            self.pfsp_power,
            self.pfsp_floor,
        )
        return start + int(self.rng.choice(size, p=probabilities))

    def record_results(
        self,
        env_ids: NDArray[np.integer],
        winner: NDArray[np.integer],
        learner_team: NDArray[np.integer],
    ) -> None:
        """Track the matches just finished in ``env_ids``. Call before ``assign``.

        Does nothing under uniform sampling, which doesn't read the results.

        Args:
            env_ids: Envs whose match just ended.
            winner: ``[n_envs]`` winning team, -1 for a draw.
            learner_team: ``[n_envs]`` the learner's team.
        """
        if self.enemy_sampling == SAMPLING_UNIFORM:
            return
        for env in env_ids:
            if self.kinds[env] != OpponentKind.SNAPSHOT:
                continue
            won = winner[env]
            score = 0.5 if won < 0 else float(won == learner_team[env])
            self.results.record(int(self.snapshot[env]), score)

    def counts(self) -> dict[str, int]:
        """Envs per kind name, drills left out."""
        return {
            KIND_NAMES[kind]: int(((self.kinds == kind) & ~self.forced).sum())
            for kind in OpponentKind
        }


class SnapshotPool:
    """Frozen actors from periodic checkpoints, loaded lazily and cached.

    Entries are ``(update, path)``; a snapshot index is a position in ``entries``.
    """

    def __init__(self, entries: Sequence[tuple[int, str]] = ()) -> None:
        self.entries: list[tuple[int, str]] = [(int(u), str(p)) for u, p in entries]
        self._cache: dict[str, SpikeActor] = {}

    def __len__(self) -> int:
        return len(self.entries)

    def add(self, update: int, path: Path) -> None:
        """Append the checkpoint written at ``update``."""
        self.entries.append((update, str(path)))

    def updates(self) -> list[int]:
        """Update numbers of the pool's checkpoints."""
        return [u for u, _ in self.entries]

    def actor(self, index: int) -> SpikeActor:
        """The frozen actor at ``index`` (eval mode, no grad).

        Raises:
            IndexError: ``index`` outside the pool.
        """
        if not 0 <= index < len(self.entries):
            raise IndexError(f"snapshot {index} outside pool of {len(self.entries)}")
        path = self.entries[index][1]
        if path not in self._cache:
            actor, _, _ = load_policy(Path(path))
            actor.eval()
            for param in actor.parameters():
                param.requires_grad_(False)
            self._cache[path] = actor
        return self._cache[path]


def snapshot_groups(
    kinds: NDArray[np.int8], snapshot: NDArray[np.int64]
) -> dict[int, NDArray[np.int64]]:
    """Env indices playing each snapshot index (one batched forward per group)."""
    envs = np.flatnonzero(kinds == OpponentKind.SNAPSHOT)
    groups: dict[int, NDArray[np.int64]] = {}
    for index in np.unique(snapshot[envs]):
        groups[int(index)] = envs[snapshot[envs] == index]
    return groups
