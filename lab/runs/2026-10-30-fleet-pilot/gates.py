"""Gate table of plan.md §5 from the JSONs that ``eval.sh`` writes.

    .venv/bin/python lab/runs/2026-10-30-fleet-pilot/gates.py [--run DIR] [name ...]

Writes ``<run>/eval/gates.json`` and ``<run>/eval/gates.md`` and prints the table,
every failed check, and the pick: the passing candidate with the highest fleet win
rate vs the script (ties: duel win vs the v3 champion). Exits 0 whether or not one
passes; a missing baseline is an error.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from spacefight.eval import fleet_gates  # noqa: E402
from spacefight.eval.duel import DuelResult  # noqa: E402
from spacefight.eval.fleet import FleetResult  # noqa: E402

SUFFIXES = ("_fleet_vs_script.json", "_duel_vs_champ_v3.json", "_duel_vs_script.json")


def load_fleet(path: Path) -> FleetResult:
    return FleetResult.from_json(path.read_text())


def load_duel(path: Path) -> DuelResult:
    return DuelResult.from_json(path.read_text())


def candidates(eval_dir: Path) -> list[str]:
    """Names with all three gate evals present, in file order."""
    names = sorted(
        p.name.removesuffix(SUFFIXES[0]) for p in eval_dir.glob(f"*{SUFFIXES[0]}")
    )
    return [n for n in names if all((eval_dir / f"{n}{s}").is_file() for s in SUFFIXES)]


HULLS = ("fighter", "strafer", "gunship")
# Waived by the user on 2026-10-30, after the gates first ran: if coasting is the
# strongest play, it ships, and the sim or reward is what gets discussed (plan.md §5).
WAIVED = frozenset(f"{h} engine duty" for h in HULLS)


def duty_table(reports: list[fleet_gates.GateReport]) -> str:
    """Engine duty per hull, with ✗ where the original G3 bound fails."""
    lines = [
        "| candidate | " + " | ".join(f"{h} engine duty" for h in HULLS) + " |",
        "|---" * (len(HULLS) + 1) + "|",
    ]
    for r in reports:
        by = {c.name: c for c in r.checks}
        cells = []
        for h in HULLS:
            c = by[f"{h} engine duty"]
            cells.append(f"{c.value:.3f}" + ("" if c.passed else " ✗"))
        lines.append(f"| {r.candidate} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("names", nargs="*")
    args = p.parse_args()
    eval_dir = args.run / "eval"
    baseline_path = eval_dir / "script_vs_script_fleet.json"
    if not baseline_path.is_file():
        raise SystemExit(f"no baseline {baseline_path}: run eval.sh baseline first")
    baseline = load_fleet(baseline_path)
    names = args.names or candidates(eval_dir)
    if not names:
        raise SystemExit(f"no candidate with all of {SUFFIXES} in {eval_dir}")
    measured = []
    for name in names:
        measured.append(
            fleet_gates.check(
                name,
                load_fleet(eval_dir / f"{name}{SUFFIXES[0]}"),
                baseline,
                load_duel(eval_dir / f"{name}{SUFFIXES[1]}"),
                load_duel(eval_dir / f"{name}{SUFFIXES[2]}"),
            )
        )
    reports = [
        fleet_gates.GateReport(
            r.candidate, [c for c in r.checks if c.name not in WAIVED]
        )
        for r in measured
    ]
    table = fleet_gates.markdown(reports)
    waived = "Engine duty per hull, reported, not gated (waived 2026-10-30):"
    lines = [table, "", waived, "", duty_table(measured), ""]
    for r in reports:
        failed = fleet_gates.failures(r)
        lines.append(
            f"- {r.candidate}: " + ("passes" if not failed else "; ".join(failed))
        )

    def key(r: fleet_gates.GateReport) -> tuple[float, float]:
        by = {c.name: c.value for c in r.checks}
        return (by["win vs script, all rosters"], by["duel win vs v3 champion"])

    passing = [r for r in reports if r.passed]
    pick = max(passing, key=key).candidate if passing else None
    lines += ["", f"pick: {pick or 'none (no candidate passes every gate)'}"]
    text = "\n".join(lines)
    print(text)
    (eval_dir / "gates.md").write_text(text + "\n")
    payload = {
        "pick": pick,
        "waived": sorted(WAIVED),
        "candidates": [
            r.to_dict() | {"waived": [asdict(c) for c in m.checks if c.name in WAIVED]}
            for r, m in zip(reports, measured)
        ],
    }
    (eval_dir / "gates.json").write_text(json.dumps(payload, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
