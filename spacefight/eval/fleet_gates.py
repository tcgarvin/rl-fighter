"""Promotion gates of fleet pilot v1 (lab/runs/2026-10-30-fleet-pilot/plan.md §5).

The thresholds below were fixed in the plan before any learned fleet policy was
evaluated; change them only with a dated note in the plan. Inputs are the eval
JSONs the run's ``eval.sh`` writes:

- the candidate's fleet eval vs the script (``rlf.eval.fleet/1``, suite
  ``fleet_v1``, sampled actions),
- the script-vs-script fleet baseline on the same suite, seed and size,
- the candidate's fighter duel vs the v3 duel champion and vs the script
  (``rlf.eval.duel/2``, n = 512).

G1 strength, G2 no hull left behind, G3 health, G4 the duel. A candidate passes
when every check passes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from spacefight.eval.duel import DuelResult
from spacefight.eval.fleet import FleetResult

HULLS: tuple[str, ...] = ("fighter", "strafer", "gunship")

# G1: win rate (draws ½) vs the script over the suite, and in every roster class.
MIN_WIN_OVERALL = 0.60
MIN_WIN_PER_CLASS = 0.45
# G2: per hull, damage dealt (hull + shield, per ship) at least this share of the
# script's own in script vs script, and survival no lower than the script's.
MIN_HULL_DAMAGE_RATIO = 0.9
MIN_HULL_SURVIVAL_MARGIN = 0.0
# G3: engine duty of every hull in this band; outside-arena share, draws, NaN or
# stuck matches at most these; time-limit endings at most the script's plus this.
ENGINE_DUTY_BAND = (0.15, 0.95)
MAX_OUTSIDE_SHARE = 0.02
MAX_DRAW_RATE = 0.05
MAX_NAN_OR_STUCK_SHARE = 0.01
MAX_TIME_LIMIT_EXCESS = 0.15
# G4: fighter duel (n = 512) vs the v3 duel champion and vs the script.
MIN_DUEL_WIN_VS_CHAMPION = 0.35
MIN_DUEL_WIN_VS_SCRIPT = 0.80


@dataclass(frozen=True)
class Check:
    """One gate check: its gate, what was measured, the bound, pass or fail."""

    gate: str
    name: str
    value: float
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
        """All checks of ``gate`` ("G1".."G4") pass."""
        return all(c.passed for c in self.checks if c.gate == gate)

    def to_dict(self) -> dict[str, object]:
        """JSON-ready dict."""
        return {
            "candidate": self.candidate,
            "passed": self.passed,
            "gates": {g: self.gate_passed(g) for g in ("G1", "G2", "G3", "G4")},
            "checks": [asdict(c) for c in self.checks],
        }


def _total_damage(result: FleetResult, side: str, hull: str) -> float:
    s = result.side_a if side == "a" else result.side_b
    m = s.hulls[hull]
    return m.damage_dealt + m.shield_damage_dealt


def _pooled_script(baseline: FleetResult, hull: str) -> tuple[float, float]:
    """The script's per-ship damage (hull + shield) and survival for ``hull`` in the
    script-vs-script baseline, pooled over both sides."""
    a, b = baseline.side_a.hulls[hull], baseline.side_b.hulls[hull]
    ships = a.ships + b.ships
    damage = (
        (a.damage_dealt + a.shield_damage_dealt) * a.ships
        + (b.damage_dealt + b.shield_damage_dealt) * b.ships
    ) / ships
    survival = (a.survival * a.ships + b.survival * b.ships) / ships
    return damage, survival


def check(
    name: str,
    fleet_vs_script: FleetResult,
    baseline: FleetResult,
    duel_vs_champion: DuelResult,
    duel_vs_script: DuelResult,
) -> GateReport:
    """Apply G1-G4 to one candidate.

    Raises:
        ValueError: The fleet eval and the baseline differ in suite, seed or size,
            or the fleet eval lacks a hull.
    """
    fc, bc = fleet_vs_script.config, baseline.config
    if (fc.suite, fc.seed, fc.n_per_roster) != (bc.suite, bc.seed, bc.n_per_roster):
        raise ValueError(f"fleet eval {fc} and baseline {bc} are not the same scenario")
    checks: list[Check] = []

    def add(gate: str, what: str, value: float, bound: str, ok: bool) -> None:
        checks.append(Check(gate, what, float(value), bound, bool(ok)))

    a = fleet_vs_script.side_a
    add(
        "G1",
        "win vs script, all rosters",
        a.win_rate,
        f">= {MIN_WIN_OVERALL}",
        a.win_rate >= MIN_WIN_OVERALL,
    )
    for klass, c in fleet_vs_script.classes.items():
        add(
            "G1",
            f"win vs script, {klass}",
            c.win_rate,
            f">= {MIN_WIN_PER_CLASS}",
            c.win_rate >= MIN_WIN_PER_CLASS,
        )

    for hull in HULLS:
        if hull not in a.hulls:
            raise ValueError(f"fleet eval has no {hull} ships on side a")
        script_damage, script_survival = _pooled_script(baseline, hull)
        damage = _total_damage(fleet_vs_script, "a", hull)
        ratio = damage / script_damage if script_damage > 0 else 0.0
        add(
            "G2",
            f"{hull} damage / script's",
            ratio,
            f">= {MIN_HULL_DAMAGE_RATIO}",
            ratio >= MIN_HULL_DAMAGE_RATIO,
        )
        margin = a.hulls[hull].survival - script_survival
        add(
            "G2",
            f"{hull} survival - script's",
            margin,
            f">= {MIN_HULL_SURVIVAL_MARGIN}",
            margin >= MIN_HULL_SURVIVAL_MARGIN,
        )

    lo, hi = ENGINE_DUTY_BAND
    for hull in HULLS:
        duty = a.hulls[hull].engine_duty
        add("G3", f"{hull} engine duty", duty, f"in [{lo}, {hi}]", lo <= duty <= hi)
    add(
        "G3",
        "outside-arena share",
        a.all_ships.outside_share,
        f"<= {MAX_OUTSIDE_SHARE}",
        a.all_ships.outside_share <= MAX_OUTSIDE_SHARE,
    )
    m = fleet_vs_script.match
    add(
        "G3",
        "draw rate",
        m.draw_rate,
        f"<= {MAX_DRAW_RATE}",
        m.draw_rate <= MAX_DRAW_RATE,
    )
    bad = max(a.nan_matches, a.stuck_matches) / m.n
    add(
        "G3",
        "NaN or stuck matches (share)",
        bad,
        f"<= {MAX_NAN_OR_STUCK_SHARE}",
        bad <= MAX_NAN_OR_STUCK_SHARE,
    )
    excess = m.time_limit_rate - baseline.match.time_limit_rate
    add(
        "G3",
        "time-limit rate - script's",
        excess,
        f"<= {MAX_TIME_LIMIT_EXCESS}",
        excess <= MAX_TIME_LIMIT_EXCESS,
    )

    champ = duel_vs_champion.side_a.win_rate
    add(
        "G4",
        "duel win vs v3 champion",
        champ,
        f">= {MIN_DUEL_WIN_VS_CHAMPION}",
        champ >= MIN_DUEL_WIN_VS_CHAMPION,
    )
    script = duel_vs_script.side_a.win_rate
    add(
        "G4",
        "duel win vs script",
        script,
        f">= {MIN_DUEL_WIN_VS_SCRIPT}",
        script >= MIN_DUEL_WIN_VS_SCRIPT,
    )
    return GateReport(name, checks)


def markdown(reports: list[GateReport]) -> str:
    """One row per candidate: G1-G4 and the headline numbers."""
    lines = [
        "| candidate | G1 | G2 | G3 | G4 | all | win vs script | duel vs champ |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        by = {c.name: c.value for c in r.checks}
        marks = ["✓" if r.gate_passed(g) else "✗" for g in ("G1", "G2", "G3", "G4")]
        lines.append(
            f"| {r.candidate} | {' | '.join(marks)} | {'✓' if r.passed else '✗'} | "
            f"{by['win vs script, all rosters']:.3f} | "
            f"{by['duel win vs v3 champion']:.3f} |"
        )
    return "\n".join(lines)


def failures(report: GateReport) -> list[str]:
    """Human-readable failed checks."""
    return [
        f"{c.gate} {c.name}: {c.value:.3f} (needs {c.bound})"
        for c in report.checks
        if not c.passed
    ]
