"""Shadow culling: who would go, and why (``docs/PILOT_TRAINING.md`` sections 5, 6).

**Nothing here changes a record.** ``shadow_cull`` is a pure function that returns a
report. The owner reviews several phases of these before the rule goes live.

The rule, in order:

1. Each active member's *adjusted* rating is its combat rating plus a diversity bonus:
   ``DIVERSITY_BONUS_PER_EDGE`` per tree edge to the nearest other member of the top
   ``TOP_N`` on combat, up to ``DIVERSITY_BONUS_CAP``. The bonus is for survival only,
   never enemy sampling or deployment.
2. The script's rule replaces the bonus for the script. It stays until it is the worst
   on raw combat **and** another active pilot has matched its drill results. A protected
   script is skipped, so the next-lowest member takes its place at the bottom.
3. The bottom ``BOTTOM_N`` by adjusted rating would be culled. If that would take every
   eligible pilot, nobody is named and the report says so: the rule ranks pilots against
   each other, and with so few it would only be naming whoever is there.
4. Fallback: while one founder holds more than ``FOUNDER_CAP`` of the survivors, its
   lowest survivor would also be culled. The report lists these separately, because
   whether the bonus alone was enough is what shadow mode is meant to show.

Behaviour distance is logged next to tree distance so a later review can check whether
the tree is a good proxy for how differently pilots fly. It plays no part in the rule.

The constants are starting guesses in rating points and have not been tuned on real
results: a 60-point cap is about a 0.58 win rate.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from math import isfinite, sqrt
from pathlib import Path
from typing import Any, Final

import numpy as np

from spacefight.population.rating import Rating
from spacefight.population.records import (
    SCRIPT_ID,
    UNRELATED,
    Member,
    Population,
)

SHADOW_SCHEMA: Final = "rlf.population.shadow/1"
SHADOW_DIRNAME: Final = "shadow"

BOTTOM_N: Final = 2
TOP_N: Final = 10
# The population the rule is meant for; below this it still names culls, flagged.
POPULATION_TARGET: Final = 10
FOUNDER_CAP: Final = 4
DIVERSITY_BONUS_PER_EDGE: Final = 15.0
DIVERSITY_BONUS_CAP: Final = 60.0

RULE_BOTTOM: Final = "bottom_on_combat"
RULE_FOUNDER_CAP: Final = "founder_cap"


@dataclass(frozen=True)
class BehaviourFeatures:
    """How a pilot flies, from the eval's per-ship metrics.

    ``engagement_rate`` stands in for the plan's "engagement range": the evals record
    the share of live ticks with an enemy inside 1.2 times the ship's longest weapon
    range, not a mean distance.

    Raises:
        ValueError: A non-finite feature.
    """

    fire_rate: float
    engagement_rate: float
    engine_duty: float

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isfinite(value):
                raise ValueError(f"behaviour feature {name} is {value}")


@dataclass(frozen=True)
class Standing:
    """One active rated member's place in the rule.

    Attributes:
        member: The member.
        family: Its family.
        founder: Its founder.
        rating: Raw combat rating.
        sd: The rating's standard deviation.
        nearest_top: The nearest other top member, or empty if there is none.
        tree_distance: Edges to ``nearest_top`` (``UNRELATED`` if in another tree, 0 if
            there is none).
        bonus: Diversity bonus.
        adjusted: ``rating + bonus``.
    """

    member: str
    family: str
    founder: str
    rating: float
    sd: float
    nearest_top: str
    tree_distance: int
    bonus: float
    adjusted: float


@dataclass(frozen=True)
class WouldCull:
    """A member the rule names.

    Attributes:
        member: The member.
        rule: ``RULE_BOTTOM`` or ``RULE_FOUNDER_CAP``.
        reason: A plain sentence.
        close_call: Its gap to the first survivor is within its rating's uncertainty,
            so a rerun could well name someone else.
    """

    member: str
    rule: str
    reason: str
    close_call: bool


@dataclass(frozen=True)
class Protected:
    """A member the rule spares whatever its rating, and why."""

    member: str
    reason: str


@dataclass(frozen=True)
class BehaviourPair:
    """Tree and behaviour distance of one pair of active members."""

    a: str
    b: str
    tree_distance: int
    behaviour_distance: float


@dataclass(frozen=True)
class BehaviourLog:
    """Tree against behaviour, for later review (not used by the rule).

    Attributes:
        pairs: Every pair of active members with features, closest behaviour first.
        tree_behaviour_correlation: Spearman rank correlation of the two distances;
            0 if it can't be computed. See ``correlation_pairs``.
        correlation_pairs: Pairs behind the correlation, 0 if it was not computed:
            related pairs only, with at least ``_MIN_CORRELATION_PAIRS``.
        missing: Active members with no features.
    """

    pairs: tuple[BehaviourPair, ...]
    tree_behaviour_correlation: float
    correlation_pairs: int
    missing: tuple[str, ...]


@dataclass(frozen=True)
class ShadowCullReport:
    """What ``shadow_cull`` found. Nothing was changed by it.

    Attributes:
        phase: Phase name.
        date: ``YYYY-MM-DD``.
        standings: Active rated members, highest adjusted rating first.
        culls: Who would go, bottom-of-combat first, then founder-cap.
        protected: Who was spared by the script rule.
        unrated: Active members with no rating, so outside the rule this phase.
        founder_counts: Founder -> active rated members, before culls.
        below_target: Fewer active members than ``POPULATION_TARGET``, when a live rule
            would likely not cull yet.
        behaviour: The tree against behaviour log.
        constants: The rule's constants, for reading old reports.
    """

    phase: str
    date: str
    standings: tuple[Standing, ...]
    culls: tuple[WouldCull, ...]
    protected: tuple[Protected, ...]
    unrated: tuple[str, ...]
    founder_counts: dict[str, int]
    below_target: bool
    behaviour: BehaviourLog
    constants: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return {"schema": SHADOW_SCHEMA, **asdict(self)}


def diversity_bonus(tree_distance: int) -> float:
    """The capped bonus for a tree distance; an unrelated member gets the cap."""
    if tree_distance < 0:
        raise ValueError(f"tree distance must be >= 0, got {tree_distance}")
    if tree_distance == UNRELATED:
        return DIVERSITY_BONUS_CAP
    return min(DIVERSITY_BONUS_CAP, DIVERSITY_BONUS_PER_EDGE * tree_distance)


def latest_drill_scores(member: Member) -> dict[str, float]:
    """The member's most recent drill scores (empty if it has none)."""
    return dict(member.drills[-1].scores) if member.drills else {}


def matched_drills(
    script_scores: Mapping[str, float], pilot_scores: Mapping[str, float]
) -> bool:
    """Whether a pilot is at or above the script on every drill the script has.

    With no script results, nobody has matched them.
    """
    if not script_scores:
        return False
    return all(
        drill in pilot_scores and pilot_scores[drill] >= score
        for drill, score in script_scores.items()
    )


def _nearest_top(
    population: Population, member_id: str, top: Sequence[str]
) -> tuple[str, int]:
    """The nearest top member other than ``member_id`` and its distance."""
    others = [t for t in top if t != member_id]
    if not others:
        return "", 0
    distances = {t: population.tree_distance(member_id, t) for t in others}
    nearest = min(others, key=lambda t: (distances[t], t))
    return nearest, distances[nearest]


def _standings(population: Population, rated: Sequence[Rating]) -> tuple[Standing, ...]:
    top = [r.member for r in rated[:TOP_N]]
    rows = []
    for rating in rated:
        member = population.member(rating.member)
        nearest, distance = _nearest_top(population, member.id, top)
        bonus = 0.0 if member.is_script or not nearest else diversity_bonus(distance)
        rows.append(
            Standing(
                member=member.id,
                family=member.family,
                founder=member.founder,
                rating=rating.rating,
                sd=rating.sd,
                nearest_top=nearest,
                tree_distance=distance,
                bonus=bonus,
                adjusted=rating.rating + bonus,
            )
        )
    return tuple(sorted(rows, key=lambda s: (-s.adjusted, s.member)))


def _script_protection(
    population: Population, standings: Sequence[Standing]
) -> tuple[Protected, ...]:
    """Why the script stays this phase, or nothing if the rule lets it go."""
    if not any(s.member == SCRIPT_ID for s in standings):
        return ()
    worst = min(standings, key=lambda s: (s.rating, s.member)).member
    if worst != SCRIPT_ID:
        return (Protected(SCRIPT_ID, f"not the worst on combat: {worst} is below it"),)
    script_scores = latest_drill_scores(population.member(SCRIPT_ID))
    if not script_scores:
        return (
            Protected(SCRIPT_ID, "worst on combat, but it has no drill results yet"),
        )
    matched = [
        s.member
        for s in standings
        if s.member != SCRIPT_ID
        and matched_drills(
            script_scores, latest_drill_scores(population.member(s.member))
        )
    ]
    if not matched:
        return (
            Protected(SCRIPT_ID, "worst on combat, but nobody has matched its drills"),
        )
    return ()


def _is_close(member: Standing, rivals: Sequence[Standing]) -> bool:
    """Whether ``member``'s gap to the lowest rival it could swap with is within noise.

    Only members the rule could have named count as rivals, so a protected script
    sitting below ``member`` doesn't make every cull look close.
    """
    if not rivals:
        return False
    lowest = min(rivals, key=lambda s: s.adjusted)
    return lowest.adjusted - member.adjusted <= sqrt(member.sd**2 + lowest.sd**2)


def _eligible(
    standings: Sequence[Standing], protected: Sequence[Protected]
) -> list[Standing]:
    spared = {p.member for p in protected}
    return [s for s in standings if s.member not in spared]


def _too_few(eligible: Sequence[Standing]) -> tuple[Protected, ...]:
    """Everyone spared when the bottom of the rule would take every eligible pilot."""
    if len(eligible) > BOTTOM_N:
        return ()
    reason = f"only {len(eligible)} eligible, and the rule would name all of them"
    return tuple(Protected(s.member, reason) for s in eligible)


def _founder_cap_culls(survivors: Sequence[Standing]) -> list[Standing]:
    """Lowest survivors of any founder over the cap, weakest first per founder."""
    counts = Counter(s.founder for s in survivors)
    culled: list[Standing] = []
    for founder, count in sorted(counts.items()):
        if count > FOUNDER_CAP:
            family = [s for s in survivors if s.founder == founder]
            culled.extend(reversed(family[FOUNDER_CAP:]))
    return culled


def _rank(values: Sequence[float]) -> np.ndarray:
    """Ranks with ties averaged."""
    array = np.asarray(values, dtype=np.float64)
    unique, inverse = np.unique(array, return_inverse=True)
    ranks = np.argsort(np.argsort(array), kind="stable").astype(np.float64)
    means = np.array([ranks[inverse == k].mean() for k in range(unique.size)])
    return means[inverse]


_MIN_CORRELATION_PAIRS: Final = 3


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Spearman correlation; 0 if either side is constant."""
    rank_x, rank_y = _rank(xs), _rank(ys)
    if rank_x.std() == 0.0 or rank_y.std() == 0.0:
        return 0.0
    return float(np.corrcoef(rank_x, rank_y)[0, 1])


def behaviour_log(
    population: Population,
    members: Sequence[str],
    features: Mapping[str, BehaviourFeatures],
) -> BehaviourLog:
    """Pairwise tree and behaviour distances of ``members`` with features.

    Behaviour distance is Euclidean over the features after scaling each by its standard
    deviation across these members, so a feature with a narrow range still counts.

    The correlation skips unrelated pairs, whose tree distance has no number to rank.
    """
    have = [m for m in members if m in features]
    missing = tuple(m for m in members if m not in features)
    if len(have) < 2:
        return BehaviourLog((), 0.0, 0, missing)
    matrix = np.array(
        [
            [
                features[m].fire_rate,
                features[m].engagement_rate,
                features[m].engine_duty,
            ]
            for m in have
        ],
        dtype=np.float64,
    )
    scale = matrix.std(axis=0)
    scaled = matrix / np.where(scale > 0.0, scale, 1.0)
    pairs = []
    for i, a in enumerate(have):
        for j, b in enumerate(have[i + 1 :], start=i + 1):
            pairs.append(
                BehaviourPair(
                    a=a,
                    b=b,
                    tree_distance=population.tree_distance(a, b),
                    behaviour_distance=float(np.linalg.norm(scaled[i] - scaled[j])),
                )
            )
    pairs.sort(key=lambda p: (p.behaviour_distance, p.a, p.b))
    related = [p for p in pairs if p.tree_distance != UNRELATED]
    if len(related) < _MIN_CORRELATION_PAIRS:
        return BehaviourLog(tuple(pairs), 0.0, 0, missing)
    correlation = _spearman(
        [float(p.tree_distance) for p in related],
        [p.behaviour_distance for p in related],
    )
    return BehaviourLog(tuple(pairs), correlation, len(related), missing)


def shadow_cull(
    population: Population,
    ratings: Sequence[Rating],
    phase: str,
    date: str,
    features: Mapping[str, BehaviourFeatures] | None = None,
) -> ShadowCullReport:
    """Name who would be culled this phase (module docstring). Changes nothing.

    Args:
        population: The records and tree.
        ratings: Combat ratings; those of archived members are ignored, so a round
            robin may include them.
        phase: Phase name.
        date: ``YYYY-MM-DD``.
        features: Behaviour features per member, when available.

    Returns:
        The report.

    Raises:
        PopulationError: A rating names an unknown member.
        ValueError: A member is rated twice.
    """
    names = [r.member for r in ratings]
    repeated = sorted(name for name, count in Counter(names).items() if count > 1)
    if repeated:
        raise ValueError(f"members rated more than once: {repeated}")
    active_rated = sorted(
        (r for r in ratings if population.member(r.member).is_active),
        key=lambda r: (-r.rating, r.member),
    )
    rated_ids = {r.member for r in active_rated}
    active_ids = [m.id for m in population.active()]
    standings = _standings(population, active_rated)
    protected = _script_protection(population, standings)
    eligible = _eligible(standings, protected)
    too_few = _too_few(eligible)
    protected = (*protected, *too_few)

    bottom = [] if too_few else eligible[-BOTTOM_N:]
    bottom_ids = {s.member for s in bottom}
    survivors = [s for s in standings if s.member not in bottom_ids]
    capped = _founder_cap_culls(survivors)
    capped_ids = {s.member for s in capped}
    remaining = [s for s in survivors if s.member not in capped_ids]
    spared_ids = {p.member for p in protected}
    rivals = [s for s in survivors if s.member not in spared_ids]
    remaining_rivals = [s for s in remaining if s.member not in spared_ids]

    culls = [
        WouldCull(
            s.member,
            RULE_BOTTOM,
            f"{s.rating:+.0f} combat, {s.bonus:+.0f} bonus.",
            _is_close(s, rivals),
        )
        for s in reversed(bottom)
    ] + [
        WouldCull(
            s.member,
            RULE_FOUNDER_CAP,
            f"Founder {s.founder} is over its cap of {FOUNDER_CAP}; this is its "
            f"lowest survivor ({s.adjusted:+.0f} adjusted).",
            _is_close(s, remaining_rivals),
        )
        for s in capped
    ]
    return ShadowCullReport(
        phase=phase,
        date=date,
        standings=standings,
        culls=tuple(culls),
        protected=protected,
        unrated=tuple(m for m in active_ids if m not in rated_ids),
        founder_counts=dict(sorted(Counter(s.founder for s in standings).items())),
        below_target=len(active_ids) < POPULATION_TARGET,
        behaviour=behaviour_log(population, active_ids, features or {}),
        constants={
            "BOTTOM_N": BOTTOM_N,
            "TOP_N": TOP_N,
            "POPULATION_TARGET": POPULATION_TARGET,
            "FOUNDER_CAP": FOUNDER_CAP,
            "DIVERSITY_BONUS_PER_EDGE": DIVERSITY_BONUS_PER_EDGE,
            "DIVERSITY_BONUS_CAP": DIVERSITY_BONUS_CAP,
        },
    )


def write_shadow_report(season_dir: Path, report: ShadowCullReport) -> Path:
    """Write ``shadow/<phase>.json``. Member records are not touched.

    Raises:
        FileExistsError: That phase already has a report; a shadow log is history, so
            it is not overwritten.
    """
    path = season_dir / SHADOW_DIRNAME / f"{report.phase}.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; a phase's shadow report is kept as is")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(report.to_dict(), indent=1) + "\n")
    os.replace(tmp, path)
    return path
