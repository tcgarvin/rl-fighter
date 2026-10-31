"""Promotion gates of the order pilot (``lab/runs/2026-10-31-order-pilot/plan.md`` §5).

The bounds below were fixed in the plan before any order pilot was evaluated (the
gate shapes are ``docs/M3_PLAN.md`` "Stage B decisions"); change them only with a
dated note in the plan. Inputs are the JSONs the run's ``eval.sh`` writes:

- following (``rlf.eval.orders/1``, ``spacefight.eval.orders_v1``): the candidate, and
  the primary baseline, fleet pilot v1 on ``obs[:385]``, on the same scenarios
  (carrier battle + convoy under the random and the scripted commander, live
  default rosters, the script on the other side);
- missions (``rlf.eval.mission/1``): the candidate vs v1 pilots under scripted
  commanders, and the baseline v1 vs v1;
- deathmatch (``rlf.eval.fleet/1``, suite ``fleet_v1``): the candidate vs the script
  and vs v1, and the baseline v1 vs the script.

Gates: **O** following (random commander, then scripted), **M** missions, **D**
deathmatch, **H** health. A candidate passes when every check passes. The secondary
following baseline (the candidate with the order block zeroed) and engine duty per
hull and order kind are reported, not gated.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

from spacefight.eval.fleet import FleetResult
from spacefight.eval.missions import MissionResult
from spacefight.eval.orders_v1 import FollowSummary, OrdersResult, Timing

GATES: tuple[str, ...] = ("O", "M", "D", "H")
RANDOM, SCRIPTED = "random", "scripted"

# O: following, pooled over carrier battle + convoy, per commander mode.
MAX_CLOSE_TICKS = 150  # attack: median ticks to gun range (targets < 250 m)
MAX_RESPONSE_TICKS = 90  # every kind: median ticks to the nose within 30°
# Random commander: margins over v1 on obs[:385], and floors.
MIN_ATTACK_SHARE_GAIN_RANDOM = 0.10
MIN_GUARD_GAIN_RANDOM = 0.15
MIN_GUARD_WITHIN_RANDOM = 0.50
MIN_HOLD_GAIN_RANDOM = 0.15
MIN_HOLD_INSIDE_RANDOM = 0.40
# Scripted commander (what the live page shows): margins over v1.
MIN_ATTACK_SHARE_GAIN_SCRIPTED = 0.05
MIN_GUARD_GAIN_SCRIPTED = 0.10
MIN_HOLD_GAIN_SCRIPTED = 0.10
# A kind with fewer instances than this cannot be judged and fails.
MIN_INSTANCES = 30
# M: win vs v1 pilots, scripted commanders, live default rosters.
MIN_MISSION_WIN_EACH = 0.47
MIN_MISSION_WIN_MEAN = 0.52
# D: deathmatch, suite fleet_v1.
MIN_FLEET_WIN_VS_SCRIPT = 0.85
MIN_FLEET_WIN_VS_V1 = 0.45
# H: health against the measured baselines.
MAX_TIME_LIMIT_EXCESS = 0.10  # per mission, over v1 vs v1; deathmatch over v1
MAX_STALEMATE_EXCESS = 0.05  # per mission, over v1 vs v1
MAX_NAN_OR_STUCK_SHARE = 0.01
MAX_OUTSIDE_SHARE = 0.02


@dataclass(frozen=True)
class Check:
    """One gate check: its gate, what was measured, the bound, pass or fail."""

    gate: str
    name: str
    value: float | None
    bound: str
    passed: bool


@dataclass(frozen=True)
class GateReport:
    """Every check of one candidate."""

    candidate: str
    checks: list[Check]

    @property
    def passed(self) -> bool:
        """All checks pass."""
        return all(c.passed for c in self.checks)

    def gate_passed(self, gate: str) -> bool:
        """All checks of ``gate`` pass."""
        return all(c.passed for c in self.checks if c.gate == gate)

    def value(self, name: str) -> float | None:
        """The measured value of the check ``name``.

        Raises:
            KeyError: No such check.
        """
        for c in self.checks:
            if c.name == name:
                return c.value
        raise KeyError(name)

    def to_dict(self) -> dict[str, object]:
        """JSON-ready dict."""
        return {
            "candidate": self.candidate,
            "passed": self.passed,
            "gates": {g: self.gate_passed(g) for g in GATES},
            "checks": [asdict(c) for c in self.checks],
        }


@dataclass(frozen=True)
class Evals:
    """The JSONs one candidate is judged on (module docstring)."""

    orders: OrdersResult
    missions_vs_v1: MissionResult
    fleet_vs_script: FleetResult
    fleet_vs_v1: FleetResult


@dataclass(frozen=True)
class Baselines:
    """Measured before any candidate: v1's following, v1 vs v1 missions, v1's
    deathmatch vs the script."""

    v1_orders: OrdersResult
    v1_missions: MissionResult
    v1_fleet_vs_script: FleetResult


class _Checks:
    def __init__(self) -> None:
        self.checks: list[Check] = []

    def add(
        self,
        gate: str,
        name: str,
        value: float | None,
        bound: str,
        ok: Callable[[float], bool],
    ) -> None:
        passed = value is not None and bool(ok(value))
        self.checks.append(
            Check(gate, name, None if value is None else float(value), bound, passed)
        )


def _median(t: Timing) -> float | None:
    return t.median


def _following(c: _Checks, mode: str, cand: FollowSummary, base: FollowSummary) -> None:
    """The O checks of one commander mode."""
    rand = mode == RANDOM
    for kind in ("attack", "guard", "hold"):
        n = getattr(cand, kind).instances
        c.add(
            "O",
            f"{mode}: {kind} instances",
            n,
            f">= {MIN_INSTANCES}",
            lambda v: v >= MIN_INSTANCES,
        )
    if rand:
        c.add(
            "O",
            f"{mode}: attack median ticks to gun range",
            _median(cand.attack.close),
            f"<= {MAX_CLOSE_TICKS}",
            lambda v: v <= MAX_CLOSE_TICKS,
        )
    gain = MIN_ATTACK_SHARE_GAIN_RANDOM if rand else MIN_ATTACK_SHARE_GAIN_SCRIPTED
    need = base.attack.damage_share + gain
    c.add(
        "O",
        f"{mode}: attack damage share on target",
        cand.attack.damage_share,
        f">= v1 {base.attack.damage_share:.3f} + {gain}",
        lambda v: v >= need,
    )
    for kind, gain_r, floor_r, gain_s in (
        (
            "guard",
            MIN_GUARD_GAIN_RANDOM,
            MIN_GUARD_WITHIN_RANDOM,
            MIN_GUARD_GAIN_SCRIPTED,
        ),
        ("hold", MIN_HOLD_GAIN_RANDOM, MIN_HOLD_INSIDE_RANDOM, MIN_HOLD_GAIN_SCRIPTED),
    ):
        mine = getattr(cand, kind).time_inside
        theirs = getattr(base, kind).time_inside
        if rand:
            bound = max(floor_r, theirs + gain_r)
            text = f">= max({floor_r}, v1 {theirs:.3f} + {gain_r})"
        else:
            bound = theirs + gain_s
            text = f">= v1 {theirs:.3f} + {gain_s}"
        c.add(
            "O",
            f"{mode}: {kind} time inside",
            mine,
            text,
            lambda v, b=bound: v >= b,  # type: ignore[misc]
        )
    c.add(
        "O",
        f"{mode}: response median ticks",
        _median(cand.response),
        f"<= {MAX_RESPONSE_TICKS}",
        lambda v: v <= MAX_RESPONSE_TICKS,
    )


def check(name: str, evals: Evals, base: Baselines) -> GateReport:
    """Apply O, M, D and H to one candidate.

    Raises:
        ValueError: An eval and its baseline are not the same scenario.
    """
    if evals.orders.config != base.v1_orders.config:
        raise ValueError("candidate and v1 following evals differ in scenario")
    if evals.missions_vs_v1.config != base.v1_missions.config:
        raise ValueError("candidate and v1 mission evals differ in scenario")
    c = _Checks()
    for mode in (RANDOM, SCRIPTED):
        if mode not in evals.orders.by_commander:
            raise ValueError(f"the following eval has no {mode} commander scenarios")
        _following(
            c, mode, evals.orders.by_commander[mode], base.v1_orders.by_commander[mode]
        )

    missions = evals.missions_vs_v1
    for m in missions.missions.values():
        c.add(
            "M",
            f"{m.mission}: win vs v1",
            m.win_rate,
            f">= {MIN_MISSION_WIN_EACH}",
            lambda v: v >= MIN_MISSION_WIN_EACH,
        )
    c.add(
        "M",
        "mean mission win vs v1",
        missions.win_rate_mean,
        f">= {MIN_MISSION_WIN_MEAN}",
        lambda v: v >= MIN_MISSION_WIN_MEAN,
    )

    c.add(
        "D",
        "deathmatch win vs script",
        evals.fleet_vs_script.side_a.win_rate,
        f">= {MIN_FLEET_WIN_VS_SCRIPT}",
        lambda v: v >= MIN_FLEET_WIN_VS_SCRIPT,
    )
    c.add(
        "D",
        "deathmatch win vs v1",
        evals.fleet_vs_v1.side_a.win_rate,
        f">= {MIN_FLEET_WIN_VS_V1}",
        lambda v: v >= MIN_FLEET_WIN_VS_V1,
    )

    for m in missions.missions.values():
        b = base.v1_missions.missions[m.mission]
        tl_bound = b.time_limit_rate + MAX_TIME_LIMIT_EXCESS
        c.add(
            "H",
            f"{m.mission}: time-limit rate",
            m.time_limit_rate,
            f"<= v1 {b.time_limit_rate:.3f} + {MAX_TIME_LIMIT_EXCESS}",
            lambda v, x=tl_bound: v <= x,  # type: ignore[misc]
        )
        st_bound = b.stalemate_rate + MAX_STALEMATE_EXCESS
        c.add(
            "H",
            f"{m.mission}: stalemate rate",
            m.stalemate_rate,
            f"<= v1 {b.stalemate_rate:.3f} + {MAX_STALEMATE_EXCESS}",
            lambda v, x=st_bound: v <= x,  # type: ignore[misc]
        )
        bad = max(m.side_a.nan_matches, m.side_a.stuck_matches) / m.n
        c.add(
            "H",
            f"{m.mission}: NaN or stuck matches",
            bad,
            f"<= {MAX_NAN_OR_STUCK_SHARE}",
            lambda v: v <= MAX_NAN_OR_STUCK_SHARE,
        )
        c.add(
            "H",
            f"{m.mission}: outside-arena share",
            m.side_a.all_ships.outside_share,
            f"<= {MAX_OUTSIDE_SHARE}",
            lambda v: v <= MAX_OUTSIDE_SHARE,
        )
    fleet = evals.fleet_vs_script
    tl = base.v1_fleet_vs_script.match.time_limit_rate + MAX_TIME_LIMIT_EXCESS
    c.add(
        "H",
        "deathmatch time-limit rate",
        fleet.match.time_limit_rate,
        f"<= v1 {base.v1_fleet_vs_script.match.time_limit_rate:.3f} + "
        f"{MAX_TIME_LIMIT_EXCESS}",
        lambda v: v <= tl,
    )
    a = fleet.side_a
    c.add(
        "H",
        "deathmatch NaN or stuck matches",
        max(a.nan_matches, a.stuck_matches) / fleet.match.n,
        f"<= {MAX_NAN_OR_STUCK_SHARE}",
        lambda v: v <= MAX_NAN_OR_STUCK_SHARE,
    )
    c.add(
        "H",
        "deathmatch outside-arena share",
        a.all_ships.outside_share,
        f"<= {MAX_OUTSIDE_SHARE}",
        lambda v: v <= MAX_OUTSIDE_SHARE,
    )
    return GateReport(name, c.checks)


def pick(reports: list[GateReport]) -> str | None:
    """The plan's pick rule: among candidates passing every gate, the highest mean
    mission win vs v1; ties broken by the deathmatch win vs v1. None if none
    passes."""
    passing = [r for r in reports if r.passed]
    if not passing:
        return None

    def key(r: GateReport) -> tuple[float, float]:
        return (
            r.value("mean mission win vs v1") or 0.0,
            r.value("deathmatch win vs v1") or 0.0,
        )

    return max(passing, key=key).candidate


def markdown(reports: list[GateReport]) -> str:
    """One row per candidate: each gate and the headline numbers."""

    def num(r: GateReport, name: str) -> str:
        v = r.value(name)
        return "–" if v is None else f"{v:.3f}"

    lines = [
        "| candidate | O | M | D | H | all | mission win vs v1 | guard (random) "
        "| hold (random) | response (random) | dm vs script | dm vs v1 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        marks = ["✓" if r.gate_passed(g) else "✗" for g in GATES]
        lines.append(
            f"| {r.candidate} | {' | '.join(marks)} | {'✓' if r.passed else '✗'} | "
            f"{num(r, 'mean mission win vs v1')} | "
            f"{num(r, 'random: guard time inside')} | "
            f"{num(r, 'random: hold time inside')} | "
            f"{num(r, 'random: response median ticks')} | "
            f"{num(r, 'deathmatch win vs script')} | "
            f"{num(r, 'deathmatch win vs v1')} |"
        )
    return "\n".join(lines)


def failures(report: GateReport) -> list[str]:
    """Human-readable failed checks."""
    return [
        f"{c.gate} {c.name}: "
        + ("n/a" if c.value is None else f"{c.value:.3f}")
        + f" (needs {c.bound})"
        for c in report.checks
        if not c.passed
    ]
