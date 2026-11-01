"""Screen ranking and gate F of plan.md §4, from the JSONs that ``eval.sh`` writes.

    .venv/bin/python lab/runs/2026-11-01-fighters-v2/gates.py screen
    .venv/bin/python lab/runs/2026-11-01-fighters-v2/gates.py gate <name> [<name> ...]

``screen`` ranks every screened checkpoint per arm by mean mission win vs R and names
what goes to the gates. ``gate`` writes ``eval/gates_f.md`` and prints it, with the pick
among the candidates that pass. Gate H is B3's (``hide_gates/eval/gates.md``). A missing
eval is an error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

EVAL = Path(__file__).resolve().parent / "eval"
F_MEAN = 0.55
F_EACH = 0.47
DM_VS_R = 0.50
DM_VS_SCRIPT = 0.85
MAX_BAD_SHARE = 0.01
MAX_OUTSIDE = 0.02
MAX_TIME_LIMIT = 0.10
SHORT_MATCH_S = 30.0


def _load(name: str) -> dict[str, Any]:
    path = EVAL / f"{name}.json"
    if not path.is_file():
        raise SystemExit(f"missing {path}: run eval.sh first")
    data: dict[str, Any] = json.loads(path.read_text())
    return data


def screen() -> None:
    """Rank the screen's checkpoints and name the candidates for the gates."""
    rows = []
    for path in sorted(EVAL.glob("screen_*.json")):
        name = path.stem.removeprefix("screen_")
        data = _load(path.stem)
        missions = data["missions"]
        rows.append(
            (
                data["win_rate_mean"],
                name,
                missions["carrier_battle"]["win_rate"],
                missions["convoy_escort"]["win_rate"],
            )
        )
    rows.sort(reverse=True)
    print("| candidate | mean vs R | carrier | convoy |\n|---|---|---|---|")
    for mean, name, carrier, convoy in rows:
        print(f"| {name} | {mean:.3f} | {carrier:.3f} | {convoy:.3f} |")
    fighters = [r[1] for r in rows if not r[1].startswith("hide")][:2]
    hide = [r[1] for r in rows if r[1].startswith("hide")][:1]
    print(f"\nto gate F: {' '.join(fighters)}\nto gate H: {' '.join(hide)}")


def _duty(side: dict[str, Any]) -> str:
    return " ".join(
        f"{hull} {m['engine_duty']:.2f}" for hull, m in sorted(side["hulls"].items())
    )


def check(name: str) -> tuple[bool, float, list[str], str]:
    """One candidate: pass, mean mission win, failures, and its table row."""
    res = _load(f"{name}_missions_vs_R")
    dm_r = _load(f"{name}_fleet_vs_R")
    dm_s = _load(f"{name}_fleet_vs_script")
    fails: list[str] = []
    mean = float(res["win_rate_mean"])
    if mean < F_MEAN:
        fails.append(f"F1 mean mission win {mean:.3f} < {F_MEAN}")
    notes: list[str] = []
    for mission, m in res["missions"].items():
        if m["win_rate"] < F_EACH:
            fails.append(f"F1 {mission} {m['win_rate']:.3f} < {F_EACH}")
        a = m["side_a"]
        bad = max(a["nan_matches"], a["stuck_matches"]) / m["n"]
        if bad > MAX_BAD_SHARE:
            fails.append(f"F3 {mission} NaN or stuck {bad:.3f}")
        if a["all_ships"]["outside_share"] > MAX_OUTSIDE:
            fails.append(f"F3 {mission} outside {a['all_ships']['outside_share']:.3f}")
        if m["time_limit_rate"] > MAX_TIME_LIMIT:
            fails.append(f"F3 {mission} time limit {m['time_limit_rate']:.3f}")
        if m["length_median_s"] < SHORT_MATCH_S:
            notes.append(f"{mission} median {m['length_median_s']:.0f} s: short")
        notes.append(f"{mission} engine duty {_duty(a)}")
    dm_vs_r = float(dm_r["side_a"]["win_rate"])
    dm_vs_script = float(dm_s["side_a"]["win_rate"])
    if dm_vs_r < DM_VS_R:
        fails.append(f"F2 deathmatch vs R {dm_vs_r:.3f} < {DM_VS_R}")
    if dm_vs_script < DM_VS_SCRIPT:
        fails.append(f"F2 deathmatch vs script {dm_vs_script:.3f} < {DM_VS_SCRIPT}")
    missions = res["missions"]
    row = (
        f"| {name} | {'✓' if not fails else '✗'} | {mean:.3f} | "
        f"{missions['carrier_battle']['win_rate']:.3f} | "
        f"{missions['convoy_escort']['win_rate']:.3f} | {dm_vs_r:.3f} | "
        f"{dm_vs_script:.3f} |\n" + "".join(f"  - {n}\n" for n in notes + fails)
    )
    return (not fails, mean, fails, row)


def gate(names: list[str]) -> None:
    """Write the gate F table and the pick."""
    out = (
        "| candidate | F | mean vs R | carrier | convoy | dm vs R | dm vs script |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    passing = []
    for name in names:
        ok, mean, _, row = check(name)
        out += row
        if ok:
            passing.append((mean, name))
    pick = max(passing)[1] if passing else "none"
    out += f"\nPick (gate F): {pick}\n"
    (EVAL / "gates_f.md").write_text(out)
    print(out)


def main() -> int:
    """CLI."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("screen", "gate"))
    p.add_argument("names", nargs="*")
    args = p.parse_args()
    if args.stage == "screen":
        screen()
    else:
        gate(args.names)
    return 0


if __name__ == "__main__":
    sys.exit(main())
