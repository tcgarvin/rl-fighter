"""Script-vs-script fleet survey: do the scripted teachers fight, and is any hull too
strong for its cost? (fleet pilot v1 plan §2.)

Plays a fleet-eval suite (default ``survey``) with the scripted controller on both
sides and prints three tables: per roster (the roster's first team's win rate, so
asymmetric rosters read as balance), per hull pooled over both sides (damage, damage
per point of cost, survival, hit rate, engagement, outside-arena share, crash
damage), and an arena-radius comparison when several radii are given.

    PYTHONPATH=. .venv/bin/python tools/fleet_survey.py --n-per-roster 128 \\
        --out lab/runs/2026-10-30-fleet-pilot/survey/script_vs_script.json
    PYTHONPATH=. .venv/bin/python tools/fleet_survey.py --suite fleet_v1 \\
        --arena-radius 450 600 --n-per-roster 64
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spacefight.env.rosters import load_hull_costs  # noqa: E402
from spacefight.eval.controllers import Scripted  # noqa: E402
from spacefight.eval.fleet import (  # noqa: E402
    SUITES,
    FleetEvalConfig,
    FleetRecords,
    FleetResult,
    run_matches,
    ship_metrics,
    summarise,
)


def pooled_hulls(records: FleetRecords) -> dict[str, dict[str, float]]:
    """Per-hull ship metrics over both sides, plus damage per point of cost."""
    costs = load_hull_costs()
    out: dict[str, dict[str, float]] = {}
    for hid, name in sorted(records.hull_names.items(), key=lambda kv: kv[1]):
        m = asdict(ship_metrics(records, records.hull == hid))
        m["damage_per_cost"] = (m["damage_dealt"] + m["shield_damage_dealt"]) / costs[
            name
        ]
        out[name] = m
    return out


def survey(cfg: FleetEvalConfig, n_threads: int) -> tuple[FleetResult, dict]:
    """One script-vs-script run of ``cfg``: the result and the pooled hull table."""
    records = run_matches(Scripted(), Scripted(), cfg, n_threads=n_threads)
    return summarise(records, cfg, "script", "script"), pooled_hulls(records)


def roster_table(result: FleetResult) -> str:
    costs = load_hull_costs()
    entries = {e.name: e for e in result.config.entries()}
    lines = [
        "| roster | cost | team-0 win | time limit | draws | median ticks |",
        "|---|---|---|---|---|---|",
    ]
    for r in result.rosters:
        c0, c1 = entries[r.name].roster.cost(costs)
        lines.append(
            f"| {r.name} | {c0:.0f} v {c1:.0f} | {r.team0_win_rate:.2f} | "
            f"{r.time_limit_rate:.2f} | {r.draw_rate:.2f} | {r.length_median:.0f} |"
        )
    return "\n".join(lines)


def hull_table(hulls: dict[str, dict[str, float]]) -> str:
    lines = [
        "| hull | ship-matches | dmg | shield dmg | dmg / cost | survival | hit rate "
        "| shots | engage | outside | engine | crash dmg |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, m in hulls.items():
        lines.append(
            f"| {name} | {m['ships']:.0f} | {m['damage_dealt']:.1f} | "
            f"{m['shield_damage_dealt']:.1f} | {m['damage_per_cost']:.2f} | "
            f"{m['survival']:.2f} | {m['hit_rate']:.3f} | {m['shots']:.0f} | "
            f"{m['engagement_rate']:.2f} | {m['outside_share']:.4f} | "
            f"{m['engine_duty']:.2f} | {m['crash_damage_taken']:.1f} |"
        )
    return "\n".join(lines)


def radius_table(runs: Sequence[tuple[float, FleetResult, dict]]) -> str:
    lines = [
        "| radius | class | time limit | median ticks | engage (all) | crash dmg / ship |",
        "|---|---|---|---|---|---|",
    ]
    for radius, result, hulls in runs:
        ships = sum(m["ships"] for m in hulls.values())
        crash = sum(m["crash_damage_taken"] * m["ships"] for m in hulls.values())
        engage = np.mean([m["engagement_rate"] for m in hulls.values()])
        label = f"{radius:.0f}" if radius > 0 else "rule"
        for c in result.classes.values():
            lines.append(
                f"| {label} | {c.klass} | {c.time_limit_rate:.2f} | "
                f"{c.length_median:.0f} | {engage:.2f} | {crash / max(ships, 1):.1f} |"
            )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--suite", default="survey", choices=sorted(SUITES))
    p.add_argument("--n-per-roster", type=int, default=128)
    p.add_argument("--seed", type=int, default=300_000)
    p.add_argument("--n-threads", type=int, default=12)
    p.add_argument(
        "--arena-radius",
        type=float,
        nargs="+",
        default=[0.0],
        help="radii to compare (m); 0 = the shared rule",
    )
    p.add_argument("--out", type=Path, help="JSON of the first radius's run")
    args = p.parse_args(argv)
    runs = []
    for radius in args.arena_radius:
        cfg = FleetEvalConfig(
            suite=args.suite,
            n_per_roster=args.n_per_roster,
            seed=args.seed,
            arena_radius=radius,
        )
        result, hulls = survey(cfg, args.n_threads)
        runs.append((radius, result, hulls))
        print(f"\n## radius {radius:.0f} (0 = rule): rosters\n")
        print(roster_table(result))
        print("\n## per hull, both sides pooled\n")
        print(hull_table(hulls))
    if len(runs) > 1:
        print("\n## arena radius\n")
        print(radius_table(runs))
    if args.out is not None:
        _, result, hulls = runs[0]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = {"result": result.to_dict(), "pooled_hulls": hulls}
        args.out.write_text(json.dumps(payload, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
