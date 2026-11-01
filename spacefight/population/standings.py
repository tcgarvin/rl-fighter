"""Pairwise win matrices and the transitivity summary (pure functions).

This answers the question a round robin asks: is there variety to protect, or does one
pilot beat everyone?

``a`` *beats* ``b`` when ``a``'s score rate is above one half by more than a margin. A
*cyclic triad* is three members with A beats B, B beats C and C beats A. Its strength is
its weakest edge's margin over one half, because a cycle is only as real as its weakest
link. ``z`` is that edge's margin in standard errors of a coin-flip over its matches, so
a small run can't pass noise off as a cycle. The cycle count alone would invite that.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations
from math import sqrt
from typing import Any, Final

from spacefight.population.culling import BehaviourFeatures
from spacefight.population.rating import PairScore, Rating

# How far over one half a score rate must be to count as beating someone.
DEFAULT_BEAT_MARGIN: Final = 0.05
# Cycles kept in a summary, strongest first.
MAX_CYCLES_LISTED: Final = 10


@dataclass(frozen=True)
class WinMatrix:
    """Score rates between members, for one mission or overall.

    Attributes:
        members: Members, in display order.
        rate: ``(a, b)`` -> ``a``'s score rate against ``b``, both ways round. Pairs
            not played are absent.
        n: ``(a, b)`` -> matches, both ways round.
    """

    members: tuple[str, ...]
    rate: dict[tuple[str, str], float]
    n: dict[tuple[str, str], int]

    def beats(self, a: str, b: str, margin: float) -> bool:
        """Whether ``a`` has a played result over ``b`` beyond ``margin``."""
        return self.rate.get((a, b), 0.5) > 0.5 + margin

    def pair_scores(self) -> list[PairScore]:
        """The matrix as rating input, one entry per pair."""
        return [
            PairScore(a, b, self.rate[(a, b)] * self.n[(a, b)], self.n[(a, b)])
            for a, b in combinations(self.members, 2)
            if (a, b) in self.rate
        ]


def make_matrix(
    results: Mapping[tuple[str, str], tuple[float, int]],
    members: Sequence[str] = (),
) -> WinMatrix:
    """Build a matrix from ``(a, b)`` -> ``(a's score rate, matches)``.

    Args:
        results: One direction per pair.
        members: Display order; members only in ``results`` follow, sorted.

    Raises:
        ValueError: A rate outside 0..=1, no matches, a self-pair, or a pair given both
            ways round.
    """
    rate: dict[tuple[str, str], float] = {}
    n: dict[tuple[str, str], int] = {}
    for (a, b), (score_rate, matches) in results.items():
        if a == b:
            raise ValueError(f"a member cannot play itself: {a!r}")
        if not 0.0 <= score_rate <= 1.0:
            raise ValueError(f"{a} v {b}: rate {score_rate} outside 0..=1")
        if matches <= 0:
            raise ValueError(f"{a} v {b}: matches must be positive, got {matches}")
        if (b, a) in rate:
            raise ValueError(f"pair {a} v {b} given both ways round")
        rate[(a, b)] = score_rate
        rate[(b, a)] = 1.0 - score_rate
        n[(a, b)] = n[(b, a)] = matches
    seen = {name for pair in rate for name in pair}
    extra = sorted(seen - set(members))
    return WinMatrix((*members, *extra), rate, n)


@dataclass(frozen=True)
class CyclicTriad:
    """A beats B, B beats C, C beats A.

    Attributes:
        cycle: ``(A, B, C)``, led by the alphabetically first member.
        strength: The weakest edge's score rate minus one half.
        z: The weakest edge's margin in coin-flip standard errors.
    """

    cycle: tuple[str, str, str]
    strength: float
    z: float


@dataclass(frozen=True)
class Transitivity:
    """How far a matrix is from a strict ladder.

    Attributes:
        margin: The beat margin used.
        triads: Triads whose three pairs all have a result beyond the margin.
        cyclic: How many of those are cyclic.
        cyclic_share: ``cyclic / triads`` (0 with no decided triads).
        cycles: The strongest cycles, at most ``MAX_CYCLES_LISTED``.
        undefeated: Members nobody beats, who played someone.
        beats_everyone: Members who beat every other member, which needs all pairs
            played.
        record: Member -> ``(beaten, beaten by, even)``.
    """

    margin: float
    triads: int
    cyclic: int
    cyclic_share: float
    cycles: tuple[CyclicTriad, ...]
    undefeated: tuple[str, ...]
    beats_everyone: tuple[str, ...]
    record: dict[str, tuple[int, int, int]]


def _coin_flip_z(rate: float, n: int) -> float:
    return (rate - 0.5) / (0.5 / sqrt(n))


def _cyclic_triad(
    matrix: WinMatrix, a: str, b: str, c: str, margin: float
) -> tuple[bool, CyclicTriad | None]:
    """Whether the triad is decided and, if it is cyclic, the cycle."""
    edges = {}
    for x, y in ((a, b), (b, c), (a, c)):
        if matrix.beats(x, y, margin):
            edges[(x, y)] = matrix.rate[(x, y)]
        elif matrix.beats(y, x, margin):
            edges[(y, x)] = matrix.rate[(y, x)]
        else:
            return False, None
    for order in ((a, b, c), (a, c, b)):
        x, y, z = order
        loop = ((x, y), (y, z), (z, x))
        if all(edge in edges for edge in loop):
            weakest = min(loop, key=lambda edge: edges[edge])
            return True, CyclicTriad(
                cycle=order,
                strength=edges[weakest] - 0.5,
                z=_coin_flip_z(edges[weakest], matrix.n[weakest]),
            )
    return True, None


def transitivity(
    matrix: WinMatrix, margin: float = DEFAULT_BEAT_MARGIN
) -> Transitivity:
    """Summarise cycles and dominance in ``matrix`` (module docstring).

    Raises:
        ValueError: A negative margin.
    """
    if margin < 0.0:
        raise ValueError(f"margin must be >= 0, got {margin}")
    members = sorted(matrix.members)
    triads = 0
    cycles: list[CyclicTriad] = []
    for a, b, c in combinations(members, 3):
        decided, cycle = _cyclic_triad(matrix, a, b, c, margin)
        triads += int(decided)
        if cycle is not None:
            cycles.append(cycle)
    cycles.sort(key=lambda t: (-t.strength, t.cycle))

    record: dict[str, tuple[int, int, int]] = {}
    for name in members:
        others = [o for o in members if o != name and (name, o) in matrix.rate]
        beaten = sum(matrix.beats(name, o, margin) for o in others)
        beaten_by = sum(matrix.beats(o, name, margin) for o in others)
        record[name] = (beaten, beaten_by, len(others) - beaten - beaten_by)
    undefeated = tuple(m for m in members if record[m][1] == 0 and sum(record[m]) > 0)
    beats_all = tuple(
        m for m in members if len(members) > 1 and record[m][0] == len(members) - 1
    )
    return Transitivity(
        margin=margin,
        triads=triads,
        cyclic=len(cycles),
        cyclic_share=len(cycles) / triads if triads else 0.0,
        cycles=tuple(cycles[:MAX_CYCLES_LISTED]),
        undefeated=undefeated,
        beats_everyone=beats_all,
        record=record,
    )


def overall_matrix(
    by_mission: Mapping[str, WinMatrix], members: Sequence[str] = ()
) -> WinMatrix:
    """Each pair's mean rate over the missions they played; each mission weighs the same.

    ``n`` is the pair's total matches.

    Raises:
        ValueError: No missions, or a pair played in only some missions, which would
            let mission difficulty leak into the overall rate.
    """
    if not by_mission:
        raise ValueError("no missions to combine")
    pairs = {(a, b) for matrix in by_mission.values() for a, b in matrix.rate if a < b}
    results: dict[tuple[str, str], tuple[float, int]] = {}
    for a, b in sorted(pairs):
        rates = []
        total = 0
        for mission, matrix in by_mission.items():
            if (a, b) not in matrix.rate:
                raise ValueError(f"{a} v {b} has no results for {mission}")
            rates.append(matrix.rate[(a, b)])
            total += matrix.n[(a, b)]
        results[(a, b)] = (sum(rates) / len(rates), total)
    return make_matrix(results, members)


@dataclass(frozen=True)
class RoundRobinResults:
    """What a round robin's finished pairs add up to.

    Attributes:
        members: Members the results cover, sorted.
        by_mission: Mission -> win matrix.
        overall: Each pair's mean over missions.
        transitivity_by_mission: Mission -> transitivity.
        transitivity_overall: Transitivity of ``overall``.
        ratings: Combat ratings from ``overall``, strongest first.
        behaviour: Member -> features, pooled over its ships in all its matches.
        pairs: Pairs read.
        matches: Matches read.
        secs: Total play time recorded.
    """

    members: tuple[str, ...]
    by_mission: dict[str, WinMatrix]
    overall: WinMatrix
    transitivity_by_mission: dict[str, Transitivity]
    transitivity_overall: Transitivity
    ratings: tuple[Rating, ...]
    behaviour: dict[str, BehaviourFeatures]
    pairs: int
    matches: int
    secs: float

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict; each matrix is nested ``a -> b -> rate``."""
        return {
            "members": list(self.members),
            "pairs": self.pairs,
            "matches": self.matches,
            "secs": self.secs,
            "win_matrix": {
                "overall": matrix_to_dict(self.overall),
                **{m: matrix_to_dict(x) for m, x in self.by_mission.items()},
            },
            "transitivity": {
                "overall": asdict(self.transitivity_overall),
                **{m: asdict(t) for m, t in self.transitivity_by_mission.items()},
            },
            "ratings": [asdict(r) for r in self.ratings],
            "behaviour": {m: asdict(f) for m, f in self.behaviour.items()},
        }


def matrix_to_dict(matrix: WinMatrix) -> dict[str, dict[str, float]]:
    """``a -> b -> a's score rate``, played pairs only."""
    return {
        a: {b: matrix.rate[(a, b)] for b in matrix.members if (a, b) in matrix.rate}
        for a in matrix.members
    }
