"""Print one eval directory of eval.sh (plan.md "Measures") and its bars.

    uv run python lab/runs/2026-11-19-station-mix/summary.py lab/runs/2026-11-19-station-mix/eval/s1_725

Against 1052 a symmetric measure is 0.5 for 1052 itself, so "within 0.05 of 1052" on
old missions and the 3 v 3 reads as the candidate's score against 1052 >= 0.45.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

READINGS = ("carrier", "convoy")


def load(d: Path, name: str) -> dict[str, Any] | None:
    p = d / name
    return json.loads(p.read_text()) if p.is_file() else None


def mean(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def fmt(x: float | None, digits: int = 3) -> str:
    return "-" if x is None else f"{x:.{digits}f}"


def bar(ok: bool | None) -> str:
    return "n/a" if ok is None else ("PASS" if ok else "FAIL")


def station(d: Path, kind: str) -> tuple[float | None, float | None, float | None]:
    """(attacker win, its ci95, bomber damage to capital a bomber), both readings."""
    runs = [r for r in (load(d, f"station_{kind}_{x}.json") for x in READINGS) if r]
    if not runs:
        return None, None, None
    win = mean([r["attacker_win_rate"] for r in runs])
    ci = mean([r["attacker_win_ci95"] for r in runs])
    ci = ci / len(runs) ** 0.5 if ci is not None else None
    cap = mean(
        [r["damage_dealt_per_ship"]["attacker"].get("bomber_vs_capital", 0.0) for r in runs]
    )
    return win, ci, cap


def main(argv: list[str]) -> int:
    d = Path(argv[0])
    print(f"# {d}")
    rows: list[tuple[str, str, str]] = []
    for r in READINGS:
        for kind in ("self", "attack", "defend"):
            x = load(d, f"station_{kind}_{r}.json")
            if x:
                rows.append(
                    (
                        f"station {kind} as {r}: attacker win",
                        f"{x['attacker_win_rate']:.3f} ± {x['attacker_win_ci95']:.3f}",
                        f"ends {x['end_reasons']}",
                    )
                )
    att, att_ci, att_cap = station(d, "attack")
    dfn, dfn_ci, _ = station(d, "defend")
    slf, slf_ci, slf_cap = station(d, "self")
    att_ok = None if att is None else att >= 0.45
    rows += [
        ("(a) station attacker win, cand attacking 1052", f"{fmt(att)} ± {fmt(att_ci)}",
         f"bar >= 0.45: {bar(att_ok)}"),
        ("(a) station defender win, cand defending vs 1052",
         fmt(None if dfn is None else 1 - dfn), f"± {fmt(dfn_ci)}"),
        ("(a) station attacker win, cand both sides", f"{fmt(slf)} ± {fmt(slf_ci)}",
         "script 0.55; 1052's own in eval_before"),
        ("(b) bomber dmg to capital a bomber (self / attacking 1052)",
         f"{fmt(slf_cap, 0)} / {fmt(att_cap, 0)}", "script 305, live pilots 36"),
    ]
    for mission in ("dm", "carrier"):
        s = load(d, f"swap_{mission}.json")
        if s:
            ok = s["delta"] > -0.15 if mission == "dm" else None
            note = (
                f"bomber slot dmg capital/strike {s['swap']['slot_damage_to_capital']:.0f}"
                f"/{s['swap']['slot_damage_to_strike']:.0f}"
            )
            if ok is not None:
                note += f"; bar > -0.15: {bar(ok)}"
            rows.append(
                (f"(b) bomber swap delta, {mission}",
                 f"{s['delta']:+.3f} ± {s['delta_ci95']:.3f}", note)
            )
    b = load(d, "bomber_drills.json")
    if b:
        for kind, key in (("attack", "target_hit"), ("defend", "more_on_named")):
            rows.append(
                (f"drills in bombers: {kind} {key}",
                 f"{b[f'{kind}/bombers'][key]['rate']:.3f}",
                 f"as drawn {b[f'{kind}/as_drawn'][key]['rate']:.3f}")
            )
    m = load(d, "missions.json")
    if m:
        for name, x in m["missions"].items():
            rows.append(
                (f"(c) {name} win vs 1052", f"{x['win_rate']:.3f}",
                 f"team0 {x['win_rate_team0']:.3f} team1 {x['win_rate_team1']:.3f}; "
                 f"bar >= 0.45: {bar(x['win_rate'] >= 0.45)}")
            )
    f = load(d, "fleet.json")
    if f:
        c = f["classes"]["3v3"]
        rows.append(
            ("(c) 3v3 fleet win vs 1052", f"{c['win_rate']:.3f}",
             f"n {c['n']}; bar >= 0.45: {bar(c['win_rate'] >= 0.45)}")
        )
    g = load(d, "drills.json")
    if g:
        meas = g["gate"]["measured"]
        rows.append(
            ("(c) drill gate", g["gate"]["verdict"],
             " ".join(f"{k} {v:.3f}" for k, v in meas.items() if v is not None))
        )
    width = max(len(r[0]) for r in rows)
    for a, v, note in rows:
        print(f"{a:<{width}}  {v:<16} {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
