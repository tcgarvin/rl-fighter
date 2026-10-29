"""Opponent schedule, per-env opponent assignment and the frozen-snapshot pool.

Spec: ``lab/runs/2026-10-28-learnability-spike/plan.md`` §4.2. The learner is team 0
in every env; team 1 is played by one of three opponent kinds:

* ``SCRIPTED``: the Rust scripted pilot (``env.scripted_actions()``).
* ``SELF``: mirror self-play, the learner's current weights; team 1 rows join the
  PPO batch.
* ``SNAPSHOT``: a frozen actor from the pool of periodic checkpoints, sampled
  uniformly; its rows do not join the batch.

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


class OpponentAssigner:
    """Per-env opponent kind and snapshot index, reassigned on reset by quota.

    Args:
        n_envs: Number of envs.
        schedule: Opponent shares per update band.
        rng: Generator for tie-breaks and snapshot draws.
    """

    def __init__(
        self, n_envs: int, schedule: OpponentSchedule, rng: np.random.Generator
    ) -> None:
        if n_envs <= 0:
            raise ValueError(f"n_envs must be positive, got {n_envs}")
        self.n_envs = n_envs
        self.schedule = schedule
        self.rng = rng
        self.kinds = np.full(n_envs, OpponentKind.SCRIPTED, dtype=np.int8)
        self.snapshot = np.full(n_envs, NO_SNAPSHOT, dtype=np.int64)

    def assign_all(self, update: int, pool_size: int) -> None:
        """Assign every env from scratch (start of training or of a resume)."""
        self.kinds[:] = -1
        self.assign(np.arange(self.n_envs), update, pool_size)

    def assign(self, env_ids: NDArray[np.integer], update: int, pool_size: int) -> None:
        """Reassign ``env_ids`` (envs that just reset) to the most-needed kinds.

        Args:
            env_ids: Indices of the envs to reassign.
            update: Current update index (selects the band).
            pool_size: Number of snapshots available to sample from.
        """
        if len(env_ids) == 0:
            return
        targets = self.schedule.targets(update, self.n_envs, pool_size)
        ids = np.asarray(env_ids, dtype=np.int64)
        self.kinds[ids] = -1
        counts = np.bincount(
            self.kinds[self.kinds >= 0], minlength=len(OpponentKind)
        ).astype(np.int64)
        for env in self.rng.permutation(ids):
            deficit = targets - counts
            best = np.flatnonzero(deficit == deficit.max())
            kind = int(best[self.rng.integers(len(best))])
            self.kinds[env] = kind
            counts[kind] += 1
            if kind == OpponentKind.SNAPSHOT:
                self.snapshot[env] = int(self.rng.integers(pool_size))
            else:
                self.snapshot[env] = NO_SNAPSHOT

    def counts(self) -> dict[str, int]:
        """Envs per kind name."""
        return {
            KIND_NAMES[kind]: int((self.kinds == kind).sum()) for kind in OpponentKind
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
