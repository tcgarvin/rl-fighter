"""Print the dock-repair eval directory (``dock_eval.py`` outputs) as phone-width tables:
balance with the dock rules off and on, and the dock statistics.

    uv run python lab/runs/2026-11-20-dock-repair/summary.py lab/runs/2026-11-20-dock-repair/out
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MISSIONS = (
    "deathmatch",
    "carrier_battle",
    "convoy_escort",
    "station_assault",
    "citadel",
)


def load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.is_file() else None


def reasons(d: dict[str, Any]) -> str:
    return ", ".join(f"{k} {v:.2f}" for k, v in d["end_reasons"].items())


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    out = Path(argv[0])
    print("| Run | Team 1 win | End reasons | Median s |")
    print("|---|---|---|---|")
    for who in ("script", "pilots"):
        for mission in MISSIONS:
            for docking in ("off", "on"):
                d = load(out / f"{who}_{mission}_{docking}.json")
                if d is None:
                    continue
                print(
                    f"| {who} {mission} {docking} | {d['team1_win_rate']:.3f} ± "
                    f"{d['team1_win_ci95']:.3f} | {reasons(d)} | {d['length_median_s']:.0f} |"
                )
    print()
    print(
        "| Run | Recalls/match | Docked/match | Completion | Of survivors | s to dock p50 "
        "| Relaunches/match | Hull restored/match | Outcomes | Failure modes |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for who in ("script", "pilots"):
        for mission in MISSIONS:
            d = load(out / f"{who}_{mission}_on.json")
            if d is None:
                continue
            k = d["dock"]
            secs = k["seconds_to_dock"].get("p50", float("nan"))
            print(
                f"| {who} {mission} | {k['recalls_per_match']:.2f} | "
                f"{k['docked_per_match']:.2f} | {k['completion']:.2f} | "
                f"{k['completion_of_survivors']:.2f} | {secs:.1f} | "
                f"{k['relaunches_per_match']:.2f} | {k['hull_restored_per_match']:.2f} | "
                f"{k['outcomes']} | {k['failure_modes']} |"
            )
    print()
    print("| Run | Killed en route | s after the order p25/p50/p75 | m closed p50 |")
    print("|---|---|---|---|")
    for who in ("script", "pilots"):
        for mission in MISSIONS:
            d = load(out / f"{who}_{mission}_on.json")
            if d is None or "killed_seconds_after_order" not in d["dock"]:
                continue
            k = d["dock"]
            q = k["killed_seconds_after_order"]
            if not q:
                continue
            closed = k["killed_metres_closed"].get("p50", float("nan"))
            print(
                f"| {who} {mission} | {k['outcomes'].get('killed en route', 0)} | "
                f"{q['p25']:.1f} / {q['p50']:.1f} / {q['p75']:.1f} | {closed:.0f} |"
            )
    print()
    print(
        "| Run | Came within 30 m | Of them docked | Inside 10 m, not docked "
        "| Their slowest m/s there p50 |"
    )
    print("|---|---|---|---|---|")
    for who in ("script", "pilots"):
        for mission in MISSIONS:
            d = load(out / f"{who}_{mission}_on.json")
            if d is None or "came_near" not in d["dock"] or not d["dock"]["recalls"]:
                continue
            k = d["dock"]
            near = k["came_near"]
            slow = k["inside_not_docked_slowest_rel"].get("p50", float("nan"))
            print(
                f"| {who} {mission} | {near} | {k['came_near_docked'] / max(near, 1):.2f} "
                f"| {k['inside_not_docked']} | {slow:.0f} |"
            )
    for mission in MISSIONS:
        d = load(out / f"pilots_{mission}_on.json")
        if d is None:
            continue
        print(f"\npilots by pilot, {mission}:")
        for pid, v in d["dock"]["by_pilot"].items():
            print(
                f"  {pid}: {v['recalls']} recalls, {v['docked']} docked "
                f"({v['completion']:.2f}; of survivors {v['completion_of_survivors']:.2f}), "
                f"failures {v['failure_modes']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
