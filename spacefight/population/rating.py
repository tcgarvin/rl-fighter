"""Combat rating with uncertainty: Bradley-Terry with a Gaussian prior.

**The method.** Each member ``i`` has a strength ``r_i``, and ``i`` beats ``j`` with
probability ``logistic(r_i - r_j)``. This is the Bradley-Terry model (1952), the same
model Elo approximates online. We fit all results at once rather than playing them
through an update rule, so match order does not matter, which suits a round robin.
A draw counts as half a win.

**The prior** ``r_i ~ N(0, PRIOR_SD_LOGIT^2)`` makes it a maximum a posteriori fit:

- A pilot who won every match has a large but finite rating; the plain maximum
  likelihood fit diverges.
- Sparse or disconnected results still give an answer, and a pilot's uncertainty
  grows with how little it played. A pilot with no matches sits at the mean with the
  prior's width.

With hundreds of matches a pair, the prior barely moves anything.

**Uncertainty** is the Laplace approximation: the inverse of the negative Hessian at
the fit is the covariance. ``sd`` is that of the rating relative to the field's mean,
since only differences mean anything.

**Why written here rather than a dependency.** The fit is one concave problem, a few
lines of Newton's method on numpy. Libraries such as ``trueskill`` or ``openskill``
solve a harder problem, updating online from team results, and would add a dependency
and hide the prior.

**What it can't show.** The model is transitive: a pure cycle (A beats B beats C beats
A) rates all three equal, with nothing to say they differ from three coin-flippers.
Cycles are ``standings.transitivity``'s job, so read the two together.

Ratings are in Elo-scale points, centred on the field's mean each time. They compare
within one fit; comparing across phases needs a shared opponent.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

# Elo points per unit of logit: a 400-point gap means 10:1 odds.
POINTS_PER_LOGIT: Final = 400.0 / math.log(10.0)
# Width of the prior on strength, in logits: about 350 Elo points. Wide enough that the
# gap between the script and a strong pilot (0.9 win rate is about 2.2 logits) is not
# fought, narrow enough to keep an undefeated pilot finite.
PRIOR_SD_LOGIT: Final = 2.0
_MAX_NEWTON_STEPS: Final = 100
_GRADIENT_TOLERANCE: Final = 1e-8


@dataclass(frozen=True)
class PairScore:
    """Results between two members, from ``a``'s side.

    Attributes:
        a: One member.
        b: The other.
        score: ``a``'s points: wins + half draws.
        n: Matches.

    Raises:
        ValueError: A self-pair, or a score outside ``0..=n``.
    """

    a: str
    b: str
    score: float
    n: int

    def __post_init__(self) -> None:
        if self.a == self.b:
            raise ValueError(f"a member cannot play itself: {self.a!r}")
        if self.n <= 0:
            raise ValueError(f"{self.a} v {self.b}: n must be positive, got {self.n}")
        if not 0.0 <= self.score <= self.n:
            raise ValueError(
                f"{self.a} v {self.b}: score {self.score} outside 0..={self.n}"
            )


@dataclass(frozen=True)
class Rating:
    """A member's combat rating.

    Attributes:
        member: The member.
        rating: Points relative to the field's mean.
        sd: One standard deviation, in points.
        matches: Matches it played in this fit.
    """

    member: str
    rating: float
    sd: float
    matches: int


def _gradient_and_hessian(
    strength: NDArray[np.float64],
    first: NDArray[np.int64],
    second: NDArray[np.int64],
    scores: NDArray[np.float64],
    counts: NDArray[np.float64],
    prior_precision: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    win = 1.0 / (1.0 + np.exp(strength[second] - strength[first]))
    surprise = scores - counts * win
    curvature = counts * win * (1.0 - win)
    size = strength.size
    gradient = -prior_precision * strength
    np.add.at(gradient, first, surprise)
    np.add.at(gradient, second, -surprise)
    hessian = -prior_precision * np.eye(size)
    np.add.at(hessian, (first, first), -curvature)
    np.add.at(hessian, (second, second), -curvature)
    np.add.at(hessian, (first, second), curvature)
    np.add.at(hessian, (second, first), curvature)
    return gradient, hessian


def rate(
    results: Sequence[PairScore],
    members: Sequence[str] = (),
    prior_sd_logit: float = PRIOR_SD_LOGIT,
) -> list[Rating]:
    """Fit the rating of every member (module docstring).

    Args:
        results: Pair results. A pair may appear more than once; they add up.
        members: Members to rate even if they played nobody. Those in ``results`` are
            always rated.
        prior_sd_logit: Prior width in logits.

    Returns:
        One ``Rating`` per member, strongest first (ties by name).

    Raises:
        ValueError: No members, or a non-positive prior width.
        RuntimeError: Newton's method did not converge, which on this concave problem
            means bad input such as a non-finite score.
    """
    if prior_sd_logit <= 0.0:
        raise ValueError(f"prior_sd_logit must be positive, got {prior_sd_logit}")
    names = sorted({*members, *(r.a for r in results), *(r.b for r in results)})
    if not names:
        raise ValueError("nothing to rate: no results and no members")
    index = {name: k for k, name in enumerate(names)}
    first = np.array([index[r.a] for r in results], dtype=np.int64)
    second = np.array([index[r.b] for r in results], dtype=np.int64)
    scores = np.array([r.score for r in results], dtype=np.float64)
    counts = np.array([r.n for r in results], dtype=np.float64)
    precision = 1.0 / prior_sd_logit**2

    strength = np.zeros(len(names), dtype=np.float64)
    for _ in range(_MAX_NEWTON_STEPS):
        gradient, hessian = _gradient_and_hessian(
            strength, first, second, scores, counts, precision
        )
        if np.abs(gradient).max() < _GRADIENT_TOLERANCE:
            break
        step = np.linalg.solve(hessian, -gradient)
        # A full Newton step can overshoot when a pilot nearly always wins.
        biggest = np.abs(step).max()
        strength += step * min(1.0, 2.0 / biggest) if biggest > 0.0 else step
    else:
        raise RuntimeError(
            f"rating fit did not converge in {_MAX_NEWTON_STEPS} steps "
            f"(largest gradient {np.abs(gradient).max()})"
        )

    covariance = np.linalg.inv(-hessian)
    # Variance of r_i minus the field's mean.
    variance = (
        np.diag(covariance) - 2.0 * covariance.mean(axis=1) + covariance.mean()
    ).clip(min=0.0)
    centred = (strength - strength.mean()) * POINTS_PER_LOGIT
    sds = np.sqrt(variance) * POINTS_PER_LOGIT
    played = np.zeros(len(names), dtype=np.int64)
    np.add.at(played, first, counts.astype(np.int64))
    np.add.at(played, second, counts.astype(np.int64))
    ratings = [
        Rating(name, float(centred[k]), float(sds[k]), int(played[k]))
        for k, name in enumerate(names)
    ]
    return sorted(ratings, key=lambda r: (-r.rating, r.member))
