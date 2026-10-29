"""Fleet pilot v1 gates (spacefight.eval.fleet_gates) on the run's baseline JSONs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from spacefight.eval import fleet_gates
from spacefight.eval.duel import DuelResult
from spacefight.eval.fleet import FleetResult

EVAL = Path(__file__).resolve().parent.parent / "lab/runs/2026-10-30-fleet-pilot/eval"


@pytest.fixture(scope="module")
def baseline() -> FleetResult:
    return FleetResult.from_json((EVAL / "script_vs_script_fleet.json").read_text())


@pytest.fixture(scope="module")
def champ_duel() -> DuelResult:
    return DuelResult.from_json((EVAL / "champ_v3_duel_vs_script.json").read_text())


def strong(baseline: FleetResult) -> FleetResult:
    """The baseline with side a made a clear, healthy winner."""
    side = baseline.side_a
    hulls = {
        h: replace(m, damage_dealt=m.damage_dealt * 1.2, survival=m.survival + 0.2)
        for h, m in side.hulls.items()
    }
    classes = {k: replace(c, win_rate=0.75) for k, c in baseline.classes.items()}
    return replace(
        baseline,
        side_a=replace(side, win_rate=0.75, hulls=hulls),
        classes=classes,
    )


def by_name(report: fleet_gates.GateReport) -> dict[str, fleet_gates.Check]:
    return {c.name: c for c in report.checks}


def test_the_script_mirror_fails_strength_only(
    baseline: FleetResult, champ_duel: DuelResult
) -> None:
    report = fleet_gates.check("script", baseline, baseline, champ_duel, champ_duel)
    checks = by_name(report)
    assert not report.gate_passed("G1")
    assert checks["win vs script, all rosters"].value == pytest.approx(0.499, abs=0.01)
    assert report.gate_passed("G3")
    assert checks["time-limit rate - script's"].value == pytest.approx(0.0)
    assert checks["fighter damage / script's"].value == pytest.approx(1.0, abs=0.02)
    assert report.gate_passed("G4")
    assert not report.passed


def test_a_strong_healthy_candidate_passes(
    baseline: FleetResult, champ_duel: DuelResult
) -> None:
    report = fleet_gates.check(
        "good", strong(baseline), baseline, champ_duel, champ_duel
    )
    assert report.passed, fleet_gates.failures(report)
    assert report.to_dict()["gates"] == {"G1": True, "G2": True, "G3": True, "G4": True}
    assert "| good | ✓ | ✓ | ✓ | ✓ | ✓ |" in fleet_gates.markdown([report])


def test_one_weak_hull_or_class_fails_its_gate(
    baseline: FleetResult, champ_duel: DuelResult
) -> None:
    good = strong(baseline)
    hulls = dict(good.side_a.hulls)
    hulls["gunship"] = replace(hulls["gunship"], damage_dealt=50.0)
    weak_hull = replace(good, side_a=replace(good.side_a, hulls=hulls))
    report = fleet_gates.check("hull", weak_hull, baseline, champ_duel, champ_duel)
    assert report.gate_passed("G1") and not report.gate_passed("G2")
    assert any("gunship damage" in f for f in fleet_gates.failures(report))

    classes = dict(good.classes)
    classes["4v4"] = replace(classes["4v4"], win_rate=0.3)
    weak_class = replace(good, classes=classes)
    report = fleet_gates.check("class", weak_class, baseline, champ_duel, champ_duel)
    assert not report.gate_passed("G1") and report.gate_passed("G2")


def test_parked_engines_and_a_lost_duel_fail(
    baseline: FleetResult, champ_duel: DuelResult
) -> None:
    good = strong(baseline)
    hulls = dict(good.side_a.hulls)
    hulls["strafer"] = replace(hulls["strafer"], engine_duty=0.05)
    parked = replace(good, side_a=replace(good.side_a, hulls=hulls))
    lost = replace(champ_duel, side_a=replace(champ_duel.side_a, win_rate=0.2))
    report = fleet_gates.check("parked", parked, baseline, lost, champ_duel)
    assert not report.gate_passed("G3")
    assert not report.gate_passed("G4")


def test_a_different_scenario_is_refused(
    baseline: FleetResult, champ_duel: DuelResult
) -> None:
    other = replace(baseline, config=replace(baseline.config, seed=1))
    with pytest.raises(ValueError, match="same scenario"):
        fleet_gates.check("x", other, baseline, champ_duel, champ_duel)
