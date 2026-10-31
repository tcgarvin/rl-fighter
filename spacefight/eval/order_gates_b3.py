"""Promotion gates of run B3 (``lab/runs/2026-11-01-order-pilot-b3/plan.md`` §5).

The gate shapes are ``docs/M3_PLAN.md`` "Stage B3"; the numbers were fixed in the
plan before any candidate was evaluated. Run 1's and B2b's gates stay in
``spacefight.eval.order_gates`` (SIM_VERSION 5, ``rlf.eval.orders/1``). Inputs are the
JSONs the run's ``eval.sh`` writes:

- following (``rlf.eval.orders/2``, ``spacefight.eval.orders``): the candidate's
  followed and hidden passes (random commander; the scripted one is reported);
- missions (``rlf.eval.mission/1``): the candidate vs v1 and vs run 1's w1_400 under
  scripted commanders, and the baseline v1 vs v1;
- deathmatch (``rlf.eval.fleet/1``, suite ``fleet_v1``): the candidate vs the script
  and vs v1, and the baseline v1 vs the script.

**Teacher-first rule.** Before any candidate is evaluated, the baseline stage
measures the order-following scripts (the teacher) on the same following eval, and
``teacher_bounds`` replaces every O bound the teacher cannot meet with one set from
the teacher: ``teacher - 0.05`` for a ``>=`` bound, ``teacher * 1.05`` for a ``<=``
bound. A relative bound ("hidden + 0.05", "0.8 x hidden") is judged for the teacher
against run 1's w1_400 with its orders hidden (a script cannot be hidden: it flies
orders it does not see); a replaced bound is absolute. The bounds are written to
``eval/o_bounds.json`` and logged, and ``check`` reads them from there.

Gates: **O** following (random commander), **M** missions, **D** deathmatch, **H**
health. A candidate passes when every check passes.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Self

from spacefight.eval.fleet import FleetResult
from spacefight.eval.missions import MissionResult
from spacefight.eval.order_gates import (
    MAX_NAN_OR_STUCK_SHARE,
    MAX_OUTSIDE_SHARE,
    MAX_STALEMATE_EXCESS,
    MAX_TIME_LIMIT_EXCESS,
    MIN_FLEET_WIN_VS_SCRIPT,
    MIN_FLEET_WIN_VS_V1,
    MIN_MISSION_WIN_EACH,
    MIN_MISSION_WIN_MEAN,
    GateReport,
    _Checks,
    failures,
)
from spacefight.eval.orders import FOLLOWED, HIDDEN, RANDOM, FollowSummary, OrdersResult

__all__ = [
    "Baselines",
    "Bound",
    "Evals",
    "OBounds",
    "check",
    "failures",
    "markdown",
    "orders_n",
    "pick",
    "teacher_bounds",
]

BOUNDS_SCHEMA = "rlf.gates.b3_o_bounds/1"
# O, random commander (the plan's bounds before the teacher-first rule).
MAX_CLOSE_TICKS = 150.0  # attack: median ticks to gun range (targets < 250 m out)
MIN_ATTACK_SHARE_GAIN = 0.05  # attack: damage share on target >= hidden + this
MAX_HULL_LOST_RATIO = 0.8  # defend: ward hull lost / ward-min <= this x hidden
MIN_THREAT_SHARE_GAIN = 0.05  # defend: threat-set share >= hidden + this
MIN_GOTO_IN_TIME = 0.7  # go-to: share arriving within the deadline
# Teacher-first replacements.
TEACHER_MARGIN = 0.05  # ">=" bounds: teacher - this
TEACHER_FACTOR = 1.05  # "<=" bounds: teacher x this
# Sample sizes O needs to judge at all.
MIN_INSTANCES = 30
MIN_WARD_MINUTES = 300.0
# Sizing the following eval: this many times MIN_WARD_MINUTES, from a small run.
SIZE_MARGIN = 1.3
# M: also against run 1's w1_400 (the init).
MIN_MISSION_WIN_MEAN_VS_W1 = 0.45

# O check names (keys of ``OBounds.bounds``).
ATTACK_CLOSE = "attack median ticks to gun range"
ATTACK_SHARE = "attack damage share on target"
DEFEND_HULL = "defend ward hull lost per ward-minute"
DEFEND_THREAT = "defend threat-set share"
GOTO_IN_TIME = "go-to arrivals in time"


@dataclass(frozen=True)
class Bound:
    """One O bound after the teacher-first rule.

    Attributes:
        op: ``">="`` or ``"<="``.
        relative: ``"none"`` (``value`` is absolute), ``"plus"`` (the candidate's
            hidden + ``value``) or ``"times"`` (``value`` x the candidate's hidden).
        value: The number.
        teacher: The teacher's measured value (None: not measured).
        reference: What the teacher was judged against (w1_400 hidden, or the
            absolute bound).
        replaced: The teacher could not meet the plan's bound, so this one is set
            from the teacher.
        text: The bound in words.
    """

    op: str
    relative: str
    value: float | None
    teacher: float | None
    reference: float | None
    replaced: bool
    text: str

    def need(self, hidden: float | None) -> float | None:
        """The number a candidate must reach, given its own hidden value; None when
        it cannot be judged (no value, or no hidden reference)."""
        if self.value is None:
            return None
        if self.relative == "none":
            return self.value
        if hidden is None:
            return None
        return hidden + self.value if self.relative == "plus" else hidden * self.value

    def ok(self, value: float, hidden: float | None) -> bool:
        """Whether ``value`` passes (a bound that cannot be judged fails)."""
        need = self.need(hidden)
        if need is None:
            return False
        return value >= need if self.op == ">=" else value <= need


@dataclass(frozen=True)
class OBounds:
    """The O bounds of a run, fixed by the baseline stage before any candidate."""

    bounds: dict[str, Bound]
    teacher: str
    reference: str
    schema: str = BOUNDS_SCHEMA

    def to_json(self) -> str:
        """Indented JSON text."""
        return json.dumps(asdict(self), indent=1)

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Parse ``to_json`` output.

        Raises:
            ValueError: Wrong schema.
        """
        data: dict[str, Any] = json.loads(text)
        if data.get("schema") != BOUNDS_SCHEMA:
            raise ValueError(f"expected schema {BOUNDS_SCHEMA!r}")
        return cls(
            bounds={k: Bound(**v) for k, v in data["bounds"].items()},
            teacher=data["teacher"],
            reference=data["reference"],
        )

    def markdown(self) -> str:
        """One row per bound: the plan's, the teacher's value, and the result."""
        lines = [
            "| check (random commander) | bound | teacher | judged against "
            "| replaced from the teacher |",
            "|---|---|---|---|---|",
        ]
        for name, b in self.bounds.items():
            lines.append(
                f"| {name} | {b.text} | {_num(b.teacher)} | {_num(b.reference)} | "
                f"{'yes' if b.replaced else 'no'} |"
            )
        return "\n".join(lines)


def _num(v: float | None) -> str:
    return "–" if v is None else f"{v:.3f}"


def _plan_bound(
    op: str,
    relative: str,
    value: float,
    teacher: float | None,
    reference_hidden: float | None,
    describe: str,
) -> Bound:
    """The plan's bound, or its teacher-set replacement (module docstring)."""
    if relative == "none":
        reference: float | None = value
    elif reference_hidden is None:
        reference = None
    elif relative == "plus":
        reference = reference_hidden + value
    else:
        reference = reference_hidden * value
    meets = (
        teacher is not None
        and reference is not None
        and (teacher >= reference if op == ">=" else teacher <= reference)
    )
    if meets or teacher is None:
        # A teacher that was not measured leaves the plan's bound in place.
        return Bound(op, relative, value, teacher, reference, False, describe)
    new = teacher - TEACHER_MARGIN if op == ">=" else teacher * TEACHER_FACTOR
    text = (
        f"{op} teacher {teacher:.3f} "
        + (f"- {TEACHER_MARGIN}" if op == ">=" else f"x {TEACHER_FACTOR}")
        + f" = {new:.3f} (plan: {describe})"
    )
    return Bound(op, "none", new, teacher, reference, True, text)


def teacher_bounds(teacher: OrdersResult, w1_400: OrdersResult) -> OBounds:
    """O bounds after the teacher-first rule (module docstring).

    Args:
        teacher: The scripts' following, followed pass, random commander.
        w1_400: Run 1's w1_400 on the same eval, with its hidden pass.

    Raises:
        KeyError: A needed commander mode or pass is missing.
    """
    t = teacher.by_commander[RANDOM][FOLLOWED]
    ref = w1_400.by_commander[RANDOM][HIDDEN]
    attack_close = t.attack.close.median
    bounds = {
        ATTACK_CLOSE: _close_bound(attack_close),
        ATTACK_SHARE: _plan_bound(
            ">=",
            "plus",
            MIN_ATTACK_SHARE_GAIN,
            t.attack.damage_share,
            ref.attack.damage_share,
            f">= hidden + {MIN_ATTACK_SHARE_GAIN}",
        ),
        DEFEND_HULL: _plan_bound(
            "<=",
            "times",
            MAX_HULL_LOST_RATIO,
            t.defend.hull_lost_per_ward_minute,
            ref.defend.hull_lost_per_ward_minute,
            f"<= {MAX_HULL_LOST_RATIO} x hidden",
        ),
        DEFEND_THREAT: _plan_bound(
            ">=",
            "plus",
            MIN_THREAT_SHARE_GAIN,
            t.defend.threat_share,
            ref.defend.threat_share,
            f">= hidden + {MIN_THREAT_SHARE_GAIN}",
        ),
        GOTO_IN_TIME: _plan_bound(
            ">=",
            "none",
            MIN_GOTO_IN_TIME,
            t.goto.all.in_time if t.goto.all.n else None,
            None,
            f">= {MIN_GOTO_IN_TIME}",
        ),
    }
    return OBounds(bounds, teacher=teacher.a, reference=f"{w1_400.a} hidden")


def _close_bound(teacher: float | None) -> Bound:
    """Ticks to gun range: a teacher that never closes (median None) cannot set a
    finite bound, so the plan's stays and the replacement is noted."""
    describe = f"<= {MAX_CLOSE_TICKS:.0f}"
    if teacher is None:
        return Bound(
            "<=",
            "none",
            MAX_CLOSE_TICKS,
            None,
            MAX_CLOSE_TICKS,
            False,
            describe + " (teacher: never; kept)",
        )
    return _plan_bound("<=", "none", MAX_CLOSE_TICKS, teacher, None, describe)


@dataclass(frozen=True)
class Evals:
    """The JSONs one candidate is judged on (module docstring)."""

    orders: OrdersResult
    missions_vs_v1: MissionResult
    missions_vs_w1: MissionResult
    fleet_vs_script: FleetResult
    fleet_vs_v1: FleetResult


@dataclass(frozen=True)
class Baselines:
    """Measured before any candidate: the O bounds (teacher-first), v1 vs v1
    missions and v1's deathmatch vs the script (H's references)."""

    o_bounds: OBounds
    v1_missions: MissionResult
    v1_fleet_vs_script: FleetResult


def _following(
    c: _Checks, bounds: OBounds, followed: FollowSummary, hidden: FollowSummary
) -> None:
    """The O checks (random commander)."""
    for kind, n in (
        ("attack", followed.attack.instances),
        ("defend", followed.defend.instances),
        ("go-to judged", followed.goto.all.n),
    ):
        c.add(
            "O",
            f"{kind} instances",
            n,
            f">= {MIN_INSTANCES}",
            lambda v: v >= MIN_INSTANCES,
        )
    for name, minutes in (
        ("defended ward-minutes", followed.defend.ward_minutes),
        ("defended ward-minutes, hidden", hidden.defend.ward_minutes),
    ):
        c.add(
            "O",
            name,
            minutes,
            f">= {MIN_WARD_MINUTES:.0f}",
            lambda v: v >= MIN_WARD_MINUTES,
        )
    measured: dict[str, tuple[float | None, float | None]] = {
        ATTACK_CLOSE: (followed.attack.close.median, None),
        ATTACK_SHARE: (followed.attack.damage_share, hidden.attack.damage_share),
        DEFEND_HULL: (
            followed.defend.hull_lost_per_ward_minute,
            hidden.defend.hull_lost_per_ward_minute,
        ),
        DEFEND_THREAT: (followed.defend.threat_share, hidden.defend.threat_share),
        GOTO_IN_TIME: (followed.goto.all.in_time, None),
    }
    for name, (value, hid) in measured.items():
        bound = bounds.bounds[name]
        need = bound.need(hid)
        text = bound.text if need is None else f"{bound.text} -> {bound.op} {need:.3f}"
        c.add("O", name, value, text, _passes(bound, hid))


def orders_n(sizing: OrdersResult, block: int, low: int, high: int) -> int:
    """Matches per random-commander scenario so that a pilot like the one in
    ``sizing`` (a small followed run) defends ``SIZE_MARGIN x MIN_WARD_MINUTES``
    ward-minutes: a multiple of ``block`` (twice the default rosters), clamped to
    ``[low, high]``."""
    f = sizing.by_commander[RANDOM][FOLLOWED]
    scenarios = len(sizing.config.missions)
    per_match = f.defend.ward_minutes / (sizing.config.n_per_scenario * scenarios)
    if per_match <= 0.0:
        return high
    need = SIZE_MARGIN * MIN_WARD_MINUTES / per_match / scenarios
    n = block * math.ceil(need / block)
    return int(min(max(n, low), high))


def _passes(bound: Bound, hidden: float | None) -> Callable[[float], bool]:
    def ok(value: float) -> bool:
        return bound.ok(value, hidden)

    return ok


def _at_most(limit: float) -> Callable[[float], bool]:
    def ok(value: float) -> bool:
        return value <= limit

    return ok


def check(name: str, evals: Evals, base: Baselines) -> GateReport:
    """Apply O, M, D and H to one candidate.

    Raises:
        ValueError: The following eval has no random-commander followed and hidden
            passes, or the mission evals and their baseline differ in scenario.
    """
    passes = evals.orders.by_commander.get(RANDOM, {})
    if FOLLOWED not in passes or HIDDEN not in passes:
        raise ValueError("the following eval needs random-commander followed + hidden")
    if evals.missions_vs_v1.config != base.v1_missions.config:
        raise ValueError("candidate and v1 mission evals differ in scenario")
    c = _Checks()
    _following(c, base.o_bounds, passes[FOLLOWED], passes[HIDDEN])

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
        "M",
        "mean mission win vs w1_400",
        evals.missions_vs_w1.win_rate_mean,
        f">= {MIN_MISSION_WIN_MEAN_VS_W1}",
        lambda v: v >= MIN_MISSION_WIN_MEAN_VS_W1,
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
        tl = b.time_limit_rate + MAX_TIME_LIMIT_EXCESS
        c.add(
            "H",
            f"{m.mission}: time-limit rate",
            m.time_limit_rate,
            f"<= v1 {b.time_limit_rate:.3f} + {MAX_TIME_LIMIT_EXCESS}",
            _at_most(tl),
        )
        st = b.stalemate_rate + MAX_STALEMATE_EXCESS
        c.add(
            "H",
            f"{m.mission}: stalemate rate",
            m.stalemate_rate,
            f"<= v1 {b.stalemate_rate:.3f} + {MAX_STALEMATE_EXCESS}",
            _at_most(st),
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
    base_tl = base.v1_fleet_vs_script.match.time_limit_rate
    c.add(
        "H",
        "deathmatch time-limit rate",
        fleet.match.time_limit_rate,
        f"<= v1 {base_tl:.3f} + {MAX_TIME_LIMIT_EXCESS}",
        lambda v: v <= base_tl + MAX_TIME_LIMIT_EXCESS,
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
    mission win vs v1 (ties: the deathmatch win vs v1). None if none passes."""
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
        return _num(r.value(name))

    gates = ("O", "M", "D", "H")
    lines = [
        "| candidate | O | M | D | H | all | mission win vs v1 | vs w1_400 "
        "| attack share | defend hull lost / ward-min | threat share | go-to in time "
        "| dm vs script | dm vs v1 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        marks = ["✓" if r.gate_passed(g) else "✗" for g in gates]
        lines.append(
            f"| {r.candidate} | {' | '.join(marks)} | {'✓' if r.passed else '✗'} | "
            f"{num(r, 'mean mission win vs v1')} | "
            f"{num(r, 'mean mission win vs w1_400')} | "
            f"{num(r, ATTACK_SHARE)} | {num(r, DEFEND_HULL)} | "
            f"{num(r, DEFEND_THREAT)} | {num(r, GOTO_IN_TIME)} | "
            f"{num(r, 'deathmatch win vs script')} | "
            f"{num(r, 'deathmatch win vs v1')} |"
        )
    return "\n".join(lines)
