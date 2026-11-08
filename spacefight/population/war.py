"""Wins above replacement (WAR): the wins a pilot adds per 100 matches it flies in, over
the script pilot flying the same ships (``docs/PILOT_TRAINING.md`` section 5).

**The matches** are the live page's (``war_matches``): every strike craft is flown by a
pilot drawn uniformly, ship by ship, from the candidates plus the script, and each side's
commander is drawn from the commander stable. So a team is a random mix, as in a pickup
game, and a pilot is judged by what its ships do for whatever team it lands on.

**The model** is the one basketball's RAPM uses, as a logistic regression with a ridge
(Gaussian) prior. For a match, with ``n_p0`` and ``n_p1`` the ships pilot ``p`` flew for
team 0 and team 1::

    logit P(team 0 wins) = side[roster] + sum_p beta_p (n_p0 - n_p1)
                           + sum_c,m delta_c,m ([cmd0 = c] - [cmd1 = c]) [mission = m]

- ``beta_p`` is what one ship flown by ``p`` instead of the script is worth, in logits.
  The script has no column: its coefficient is 0 by definition, so it *is* replacement.
- ``side[roster]`` is team 0's advantage in that roster (each deathmatch draft and each
  carrier and convoy roster is its own), since convoy and carrier sides are not alike.
- ``delta_c,m`` is commander ``c``'s strength in mission ``m`` against the reference
  commander (``scripted`` when it played, else the first label), which takes 0.
- A draw is half a win: two rows of weight one half, one won and one lost. That is the
  same likelihood as one row with target 0.5, which is how it is fitted.

**The prior** is ``N(0, prior_sd^2)`` on every ``beta`` (default 1 logit per ship) and a
wider ``N(0, nuisance_prior_sd^2)`` on the nuisance terms (default 3). Pilots are drawn at
random, so the design is close to orthogonal and the ridge is not there to untangle
collinear players as in basketball. It keeps the fit finite when a small sample separates
(a pilot that only ever won, a roster one side always wins), and at the sizes a real
measurement uses it moves nothing much: ``prior_weight`` reports, per pilot, the share of
its coefficient's precision that came from the prior.

**WAR** for pilot ``p``: over the matches ``p`` flew in, the sum of the model's win
probability for each side ``p`` flew for, minus the same with ``p``'s ships on that side
flown by the script, per 100 of those matches. A draw counts half, so "wins" means wins
plus half the draws. It depends on how many ships a pilot flies per match, so it compares
pilots within one measurement; the per-ship coefficient travels better between them.

**Uncertainty** is a bootstrap over matches, stratified by mission: resample each
mission's matches with replacement, refit, recompute WAR. The interval is the percentile
interval of those refits.

Pure numpy; no sim. ``war_matches`` plays the matches.
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Final

import numpy as np
from numpy.typing import NDArray

from spacefight.population.records import SCRIPT_ID

WAR_SCHEMA: Final = "rlf.population.war/1"
DRAW: Final = -1
TEAMS: Final = (0, 1)
PER_MATCHES: Final = 100.0
DEFAULT_PRIOR_SD: Final = 1.0
DEFAULT_NUISANCE_PRIOR_SD: Final = 3.0
DEFAULT_BOOTSTRAP: Final = 500
DEFAULT_CI_LEVEL: Final = 0.95
REFERENCE_COMMANDER: Final = "scripted"
_MAX_NEWTON_STEPS: Final = 100
_GRADIENT_TOLERANCE: Final = 1e-8
# Largest Newton step in logits; a full step can overshoot on a separated sample.
_MAX_STEP: Final = 2.0
MISSION_SHORT: Final[dict[str, str]] = {
    "deathmatch": "DM",
    "carrier_battle": "Carrier",
    "convoy_escort": "Convoy",
}


@dataclass(frozen=True)
class MatchRecord:
    """One match as WAR needs it.

    Attributes:
        mission: The mission.
        roster: The roster's name within the mission (a deathmatch draft's number).
        commanders: Team 0's and team 1's commander labels.
        ships: Per team, pilot id -> hull -> strike craft it flew. Capital ships fly
            the sim's scripts and are not counted.
        winner: 0 or 1, or ``DRAW``.
        end_reason: The sim's end reason.

    Raises:
        ValueError: A bad winner, an empty label or a non-positive ship count.
    """

    mission: str
    roster: str
    commanders: tuple[str, str]
    ships: tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]
    winner: int
    end_reason: int = 0

    def __post_init__(self) -> None:
        if self.winner not in (0, 1, DRAW):
            raise ValueError(f"winner must be 0, 1 or {DRAW}, got {self.winner}")
        if not self.mission or not self.roster or not all(self.commanders):
            raise ValueError(f"a match needs a mission, roster and commanders: {self}")
        if len(self.commanders) != 2 or len(self.ships) != 2:
            raise ValueError("a match has two teams")
        for team in self.ships:
            for pilot, hulls in team.items():
                if not pilot or any(
                    not isinstance(n, int) or n <= 0 for n in hulls.values()
                ):
                    raise ValueError(f"bad ship counts for {pilot!r}: {hulls}")

    def pilot_ships(self, team: int) -> dict[str, int]:
        """Pilot id -> strike craft it flew for ``team``, hulls added up."""
        return {p: sum(h.values()) for p, h in self.ships[team].items()}

    @property
    def score_team0(self) -> float:
        """Team 0's points: 1 for a win, a half for a draw."""
        return 0.5 if self.winner == DRAW else float(self.winner == 0)

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return {
            "mission": self.mission,
            "roster": self.roster,
            "commanders": list(self.commanders),
            "ships": [dict(team) for team in self.ships],
            "winner": self.winner,
            "end_reason": self.end_reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MatchRecord:
        """Parse one record.

        Raises:
            ValueError: Missing keys or bad values.
        """
        try:
            ships = data["ships"]
            return cls(
                mission=str(data["mission"]),
                roster=str(data["roster"]),
                commanders=(str(data["commanders"][0]), str(data["commanders"][1])),
                ships=(
                    {
                        str(p): {str(h): int(n) for h, n in hs.items()}
                        for p, hs in ships[0].items()
                    },
                    {
                        str(p): {str(h): int(n) for h, n in hs.items()}
                        for p, hs in ships[1].items()
                    },
                ),
                winner=int(data["winner"]),
                end_reason=int(data.get("end_reason", 0)),
            )
        except (KeyError, IndexError, TypeError, AttributeError) as err:
            raise ValueError(f"bad match record {dict(data)}: {err}") from err


@dataclass(frozen=True)
class Design:
    """The regression's inputs, one row per match.

    Attributes:
        pilots: Candidate pilots with a column, sorted; never the script.
        nuisance: Names of the side and commander terms.
        ships0: [M, P] ships each pilot flew for team 0.
        ships1: [M, P] ships each pilot flew for team 1.
        nuisance_x: [M, Q] the side and commander columns.
        score: [M] team 0's points (1, 0.5, 0).
        missions: Missions present, in first-seen order.
        mission_of: [M] index into ``missions``.
        script_ships: [M] ships the script flew, both teams.
    """

    pilots: tuple[str, ...]
    nuisance: tuple[str, ...]
    ships0: NDArray[np.float64]
    ships1: NDArray[np.float64]
    nuisance_x: NDArray[np.float64]
    score: NDArray[np.float64]
    missions: tuple[str, ...]
    mission_of: NDArray[np.int64]
    script_ships: NDArray[np.float64]

    @property
    def x(self) -> NDArray[np.float64]:
        """[M, P + Q] pilot columns (team 0 minus team 1), then nuisance columns."""
        return np.hstack([self.ships0 - self.ships1, self.nuisance_x])

    def take(self, rows: NDArray[np.int64]) -> Design:
        """The same design on ``rows`` (repeats allowed), for a bootstrap."""
        return Design(
            self.pilots,
            self.nuisance,
            self.ships0[rows],
            self.ships1[rows],
            self.nuisance_x[rows],
            self.score[rows],
            self.missions,
            self.mission_of[rows],
            self.script_ships[rows],
        )


def reference_commander(records: Sequence[MatchRecord]) -> str:
    """``scripted`` if any match had it, else the first label alphabetically."""
    labels = {c for r in records for c in r.commanders}
    if REFERENCE_COMMANDER in labels:
        return REFERENCE_COMMANDER
    return min(labels)


def side_term(mission: str, roster: str) -> str:
    """The name of a roster's team-0 advantage term."""
    return f"side {mission} / {roster}"


def commander_term(commander: str, mission: str) -> str:
    """The name of a commander's strength term in a mission."""
    return f"commander {commander} in {mission}"


def build_design(records: Sequence[MatchRecord]) -> Design:
    """Turn match records into the regression's columns (module docstring).

    Raises:
        ValueError: No matches, or no pilot but the script flew.
    """
    if not records:
        raise ValueError("no matches to fit")
    pilots = tuple(
        sorted({p for r in records for t in TEAMS for p in r.ships[t]} - {SCRIPT_ID})
    )
    if not pilots:
        raise ValueError("only the script flew; there is nobody to rate")
    missions = tuple(dict.fromkeys(r.mission for r in records))
    reference = reference_commander(records)
    sides = list(dict.fromkeys(side_term(r.mission, r.roster) for r in records))
    commanders = sorted(
        {
            commander_term(c, r.mission)
            for r in records
            for c in r.commanders
            if c != reference
        }
    )
    nuisance = (*sides, *commanders)
    column = {name: k for k, name in enumerate(nuisance)}
    pilot_column = {p: k for k, p in enumerate(pilots)}
    m = len(records)
    ships = np.zeros((2, m, len(pilots)), dtype=np.float64)
    nuisance_x = np.zeros((m, len(nuisance)), dtype=np.float64)
    script_ships = np.zeros(m, dtype=np.float64)
    for i, r in enumerate(records):
        for t in TEAMS:
            for pilot, n in r.pilot_ships(t).items():
                if pilot == SCRIPT_ID:
                    script_ships[i] += n
                else:
                    ships[t, i, pilot_column[pilot]] += n
        nuisance_x[i, column[side_term(r.mission, r.roster)]] = 1.0
        for t, sign in zip(TEAMS, (1.0, -1.0)):
            label = r.commanders[t]
            if label != reference:
                nuisance_x[i, column[commander_term(label, r.mission)]] += sign
    return Design(
        pilots=pilots,
        nuisance=nuisance,
        ships0=ships[0],
        ships1=ships[1],
        nuisance_x=nuisance_x,
        score=np.array([r.score_team0 for r in records], dtype=np.float64),
        missions=missions,
        mission_of=np.array([missions.index(r.mission) for r in records]),
        script_ships=script_ships,
    )


def _sigmoid(z: NDArray[np.float64]) -> NDArray[np.float64]:
    out: NDArray[np.float64] = 0.5 * (1.0 + np.tanh(0.5 * z))
    return out


def fit_logistic(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    precision: NDArray[np.float64],
    start: NDArray[np.float64] | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Maximum a posteriori logistic regression with a Gaussian prior, by Newton.

    Args:
        x: [M, K] inputs.
        y: [M] targets in 0..=1 (a fractional target is a weighted pair of rows).
        precision: [K] prior precision per coefficient; all must be positive, so the
            problem is strictly concave and every column, even an empty one, is fixed.
        start: Where to start (a bootstrap starts from the full fit); zeros if omitted.

    Returns:
        The coefficients and the negative Hessian of the log posterior there (its
        inverse is the Laplace covariance).

    Raises:
        ValueError: Shapes disagree, a target is outside 0..=1, or a precision is not
            positive.
        RuntimeError: Newton's method did not converge.
    """
    if x.ndim != 2 or y.shape != (x.shape[0],) or precision.shape != (x.shape[1],):
        raise ValueError(f"shapes x {x.shape}, y {y.shape}, prior {precision.shape}")
    if np.any((y < 0.0) | (y > 1.0)) or not np.all(np.isfinite(x)):
        raise ValueError("targets must be in 0..=1 and inputs finite")
    if np.any(precision <= 0.0):
        raise ValueError("every prior precision must be positive")
    theta = np.zeros(x.shape[1]) if start is None else start.astype(np.float64).copy()
    for _ in range(_MAX_NEWTON_STEPS):
        p = _sigmoid(x @ theta)
        gradient = x.T @ (y - p) - precision * theta
        information = (x.T * (p * (1.0 - p))) @ x + np.diag(precision)
        if np.abs(gradient).max() < _GRADIENT_TOLERANCE:
            return theta, information
        step = np.linalg.solve(information, gradient)
        biggest = np.abs(step).max()
        theta = theta + step * min(1.0, _MAX_STEP / biggest) if biggest > 0 else theta
    raise RuntimeError(
        f"WAR fit did not converge in {_MAX_NEWTON_STEPS} steps "
        f"(largest gradient {np.abs(gradient).max():.3g})"
    )


def war_contributions(
    design: Design, theta: NDArray[np.float64]
) -> NDArray[np.float64]:
    """[M, P] wins each pilot added in each match over the script flying its ships.

    For each side the pilot flew for, its side's model win probability minus the same
    with that side's ships of the pilot flown by the script (logit shifted by
    ``beta_p * ships``). Zero where the pilot did not fly.
    """
    beta = theta[: len(design.pilots)]
    eta = (design.x @ theta)[:, None]
    base = _sigmoid(eta)
    # Team 0's ships of p flown by the script lower team 0's logit by beta * n.
    gain0 = base - _sigmoid(eta - beta * design.ships0)
    # Team 1's win probability is 1 - P(team 0); its ships raise team 0's logit back.
    gain1 = _sigmoid(eta + beta * design.ships1) - base
    return gain0 + gain1


def _appeared(design: Design) -> NDArray[np.bool_]:
    flew: NDArray[np.bool_] = (design.ships0 + design.ships1) > 0
    return flew


def _war_per_100(
    contributions: NDArray[np.float64], appeared: NDArray[np.bool_]
) -> NDArray[np.float64]:
    """WAR per 100 matches flown in, per pilot; NaN for a pilot that never flew."""
    matches = appeared.sum(axis=0).astype(np.float64)
    total = contributions.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out: NDArray[np.float64] = np.where(
            matches > 0, PER_MATCHES * total / matches, np.nan
        )
    return out


@dataclass(frozen=True)
class MissionWar:
    """A pilot's WAR in one mission.

    Attributes:
        war: Wins added per 100 matches of this mission it flew in.
        ci_low: Lower end of the bootstrap interval.
        ci_high: Upper end.
        matches: Matches of this mission it flew in.
        ships: Ships it flew in them.
    """

    war: float
    ci_low: float
    ci_high: float
    matches: int
    ships: int


@dataclass(frozen=True)
class PilotWar:
    """One pilot's WAR (module docstring).

    Attributes:
        pilot: Pilot id; ``script`` is replacement, all zeros but its playing time.
        war: Wins added per 100 matches it flew in.
        ci_low: Lower end of the bootstrap interval.
        ci_high: Upper end.
        se: Bootstrap standard deviation of ``war``.
        coef: Logits per ship over the script.
        coef_sd: Laplace standard deviation of ``coef``.
        prior_weight: Share of ``coef``'s precision that came from the prior; near 0
            means the data decided it.
        matches: Matches it flew in.
        ships: Strike craft it flew.
        by_mission: Mission -> its WAR there, for missions it flew in.
    """

    pilot: str
    war: float
    ci_low: float
    ci_high: float
    se: float
    coef: float
    coef_sd: float
    prior_weight: float
    matches: int
    ships: int
    by_mission: dict[str, MissionWar] = field(default_factory=dict)

    @property
    def is_script(self) -> bool:
        """Whether this is the replacement pilot."""
        return self.pilot == SCRIPT_ID


@dataclass(frozen=True)
class WarFit:
    """A whole WAR fit.

    Attributes:
        pilots: Every pilot, the script included, highest WAR first.
        nuisance: Side and commander terms -> logits.
        reference_commander: The commander whose strength is 0.
        matches: Matches fitted.
        matches_by_mission: Mission -> matches.
        draws: Matches drawn.
        prior_sd: Prior width of each pilot's coefficient, logits per ship.
        nuisance_prior_sd: Prior width of each nuisance term, logits.
        n_bootstrap: Bootstrap refits.
        bootstrap_seed: Their seed.
        ci_level: The interval's coverage.
    """

    pilots: tuple[PilotWar, ...]
    nuisance: dict[str, float]
    reference_commander: str
    matches: int
    matches_by_mission: dict[str, int]
    draws: int
    prior_sd: float
    nuisance_prior_sd: float
    n_bootstrap: int
    bootstrap_seed: int
    ci_level: float

    def pilot(self, pilot_id: str) -> PilotWar:
        """The WAR of ``pilot_id``.

        Raises:
            KeyError: It did not fly.
        """
        for p in self.pilots:
            if p.pilot == pilot_id:
                return p
        raise KeyError(f"{pilot_id!r} is not in this WAR fit")

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WarFit:
        """Parse a fit written by ``to_dict``.

        Raises:
            ValueError: Missing or unknown keys.
        """
        try:
            raw = dict(data)
            pilots = tuple(
                PilotWar(
                    **{
                        **p,
                        "by_mission": {
                            m: MissionWar(**w) for m, w in p["by_mission"].items()
                        },
                    }
                )
                for p in raw.pop("pilots")
            )
            return cls(pilots=pilots, **raw)
        except (KeyError, TypeError) as err:
            raise ValueError(f"bad WAR fit: {err}") from err


def _bootstrap(
    design: Design,
    theta: NDArray[np.float64],
    precision: NDArray[np.float64],
    n_bootstrap: int,
    seed: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """WAR per pilot of each refit, overall [B, P] and by mission [B, missions, P]."""
    rng = np.random.default_rng(seed)
    strata = [
        np.flatnonzero(design.mission_of == k) for k in range(len(design.missions))
    ]
    overall = np.empty((n_bootstrap, len(design.pilots)))
    by_mission = np.empty((n_bootstrap, len(design.missions), len(design.pilots)))
    for b in range(n_bootstrap):
        rows = np.concatenate(
            [rng.choice(s, size=s.size, replace=True) for s in strata]
        )
        sample = design.take(rows)
        refit, _ = fit_logistic(sample.x, sample.score, precision, start=theta)
        gains = war_contributions(sample, refit)
        flew = _appeared(sample)
        overall[b] = _war_per_100(gains, flew)
        for k in range(len(design.missions)):
            here = sample.mission_of == k
            by_mission[b, k] = _war_per_100(gains[here], flew[here])
    return overall, by_mission


def _interval(
    draws: NDArray[np.float64], level: float, what: str
) -> tuple[float, float, float]:
    """Percentile interval and sd of bootstrap draws, skipping refits it sat out.

    Raises:
        ValueError: Every refit left it out, so there is nothing to bootstrap.
    """
    valid = draws[np.isfinite(draws)]
    if valid.size == 0:
        raise ValueError(f"{what}: no bootstrap refit included it; play more matches")
    tail = 100.0 * (1.0 - level) / 2.0
    low, high = np.percentile(valid, [tail, 100.0 - tail])
    return float(low), float(high), float(valid.std(ddof=1)) if valid.size > 1 else 0.0


def fit_war(
    records: Sequence[MatchRecord],
    prior_sd: float = DEFAULT_PRIOR_SD,
    nuisance_prior_sd: float = DEFAULT_NUISANCE_PRIOR_SD,
    n_bootstrap: int = DEFAULT_BOOTSTRAP,
    bootstrap_seed: int = 0,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> WarFit:
    """Fit WAR to match records (module docstring).

    Args:
        records: The matches.
        prior_sd: Prior width of each pilot's coefficient, logits per ship.
        nuisance_prior_sd: Prior width of each side and commander term, logits.
        n_bootstrap: Bootstrap refits for the intervals; at least 2.
        bootstrap_seed: Their seed.
        ci_level: Interval coverage, in 0..1.

    Returns:
        The fit.

    Raises:
        ValueError: No matches, nobody but the script, bad prior widths or interval
            settings, or a pilot no refit included.
        RuntimeError: A fit did not converge.
    """
    if prior_sd <= 0.0 or nuisance_prior_sd <= 0.0:
        raise ValueError(
            f"prior widths must be positive: {prior_sd}, {nuisance_prior_sd}"
        )
    if n_bootstrap < 2 or not 0.0 < ci_level < 1.0:
        raise ValueError(
            f"need >= 2 refits and a level in 0..1: {n_bootstrap}, {ci_level}"
        )
    design = build_design(records)
    n_pilots = len(design.pilots)
    precision = np.concatenate(
        [
            np.full(n_pilots, 1.0 / prior_sd**2),
            np.full(len(design.nuisance), 1.0 / nuisance_prior_sd**2),
        ]
    )
    theta, information = fit_logistic(design.x, design.score, precision)
    covariance = np.linalg.inv(information)
    gains = war_contributions(design, theta)
    flew = _appeared(design)
    war = _war_per_100(gains, flew)
    boot, boot_by_mission = _bootstrap(
        design, theta, precision, n_bootstrap, bootstrap_seed
    )
    pilots = []
    for k, pilot in enumerate(design.pilots):
        low, high, se = _interval(boot[:, k], ci_level, pilot)
        by_mission = {}
        for j, mission in enumerate(design.missions):
            here = design.mission_of == j
            matches = int(flew[here, k].sum())
            if matches == 0:
                continue
            m_low, m_high, _ = _interval(
                boot_by_mission[:, j, k], ci_level, f"{pilot} in {mission}"
            )
            by_mission[mission] = MissionWar(
                war=float(_war_per_100(gains[here], flew[here])[k]),
                ci_low=m_low,
                ci_high=m_high,
                matches=matches,
                ships=int((design.ships0[here, k] + design.ships1[here, k]).sum()),
            )
        pilots.append(
            PilotWar(
                pilot=pilot,
                war=float(war[k]),
                ci_low=low,
                ci_high=high,
                se=se,
                coef=float(theta[k]),
                coef_sd=float(math.sqrt(covariance[k, k])),
                prior_weight=float(precision[k] / information[k, k]),
                matches=int(flew[:, k].sum()),
                ships=int((design.ships0[:, k] + design.ships1[:, k]).sum()),
                by_mission=by_mission,
            )
        )
    pilots.append(_script_war(records, design))
    return WarFit(
        pilots=tuple(sorted(pilots, key=lambda p: (-p.war, p.pilot))),
        nuisance={
            name: float(theta[n_pilots + q]) for q, name in enumerate(design.nuisance)
        },
        reference_commander=reference_commander(records),
        matches=len(records),
        matches_by_mission=dict(Counter(r.mission for r in records)),
        draws=sum(r.winner == DRAW for r in records),
        prior_sd=prior_sd,
        nuisance_prior_sd=nuisance_prior_sd,
        n_bootstrap=n_bootstrap,
        bootstrap_seed=bootstrap_seed,
        ci_level=ci_level,
    )


def _script_war(records: Sequence[MatchRecord], design: Design) -> PilotWar:
    """The replacement pilot: zero by definition, with its playing time."""
    by_mission = {}
    for j, mission in enumerate(design.missions):
        here = design.mission_of == j
        flew = design.script_ships[here] > 0
        if flew.any():
            by_mission[mission] = MissionWar(
                0.0, 0.0, 0.0, int(flew.sum()), int(design.script_ships[here].sum())
            )
    return PilotWar(
        pilot=SCRIPT_ID,
        war=0.0,
        ci_low=0.0,
        ci_high=0.0,
        se=0.0,
        coef=0.0,
        coef_sd=0.0,
        prior_weight=0.0,
        matches=int((design.script_ships > 0).sum()),
        ships=int(design.script_ships.sum()),
        by_mission=by_mission,
    )


@dataclass(frozen=True)
class WarDocument:
    """A WAR measurement on disk: how it was played, every match, and the fit.

    Attributes:
        config: The run's settings (``war_matches.WarConfig.to_dict``), as written.
        records: Every match.
        fit: The fit of ``records``.
    """

    config: dict[str, Any]
    records: tuple[MatchRecord, ...]
    fit: WarFit

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict, schema first."""
        return {
            "schema": WAR_SCHEMA,
            "config": self.config,
            "fit": self.fit.to_dict(),
            "records": [r.to_dict() for r in self.records],
        }


def read_war(path: Path) -> WarDocument:
    """Read a WAR JSON.

    Raises:
        ValueError: Wrong schema or a bad record or fit.
    """
    data = json.loads(path.read_text())
    if data.get("schema") != WAR_SCHEMA:
        raise ValueError(f"{path}: schema {data.get('schema')!r}, not {WAR_SCHEMA}")
    return WarDocument(
        config=dict(data["config"]),
        records=tuple(MatchRecord.from_dict(r) for r in data["records"]),
        fit=WarFit.from_dict(data["fit"]),
    )


def write_war(path: Path, document: WarDocument, title: str = "") -> tuple[Path, Path]:
    """Write the JSON and the phone table beside it (``.md``), atomically.

    Returns:
        The JSON's and the table's paths.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    table = path.with_suffix(".md")
    for target, text in (
        (path, json.dumps(document.to_dict(), indent=1) + "\n"),
        (table, render_war_table(document.fit, title)),
    ):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(text)
        os.replace(tmp, target)
    return path, table


def _signed(value: float) -> str:
    return f"{value:+.1f}"


def render_war_table(fit: WarFit, title: str = "") -> str:
    """The phone table: pilot, WAR per 100, interval, ships; then WAR by mission."""
    level = round(100 * fit.ci_level)
    missions = ", ".join(
        f"{n} {MISSION_SHORT.get(m, m)}" for m, n in fit.matches_by_mission.items()
    )
    lines = [
        f"# Wins above replacement{f': {title}' if title else ''}",
        "",
        f"{fit.matches} matches ({missions}). Wins added per 100 matches a pilot flew "
        "in, over the script flying its ships. A draw is half a win.",
        "",
        f"| Pilot | WAR | {level}% CI | Ships |",
        "|---|--:|---|--:|",
    ]
    for p in fit.pilots:
        ci = (
            "replacement"
            if p.is_script
            else f"{_signed(p.ci_low)} to {_signed(p.ci_high)}"
        )
        war = "0" if p.is_script else _signed(p.war)
        lines.append(f"| {p.pilot} | {war} | {ci} | {p.ships} |")
    shown = list(fit.matches_by_mission)
    lines += [
        "",
        "**By mission**",
        "",
        "| Pilot | " + " | ".join(MISSION_SHORT.get(m, m) for m in shown) + " |",
        "|---|" + "--:|" * len(shown),
    ]
    for p in fit.pilots:
        if p.is_script:
            continue
        cells = [
            _signed(p.by_mission[m].war) if m in p.by_mission else "-" for m in shown
        ]
        lines.append(f"| {p.pilot} | " + " | ".join(cells) + " |")
    lines += [
        "",
        f"{level}% intervals from {fit.n_bootstrap} bootstrap refits over matches. "
        f"Ridge prior {fit.prior_sd:g} logit per ship.",
    ]
    return "\n".join(lines) + "\n"
