"""Training telemetry of the station-mix arms over update windows (results.md).

    python3 lab/runs/2026-11-19-station-mix/telemetry.py [mix_s1 mix_s2] [--window 500]

Wins are by the learner's side, weighted by episodes; drill pass by drill episodes;
bomber hit rate and damage by bomber hull samples (damage is the trainer's per-sample
hull_damage_dealt, in reward units, so read it against the gunship's beside it).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLASSES = [
    ("station_assault/attack", "stn att"),
    ("station_assault/defend", "stn def"),
    ("carrier_battle", "carrier"),
    ("convoy_escort/attack", "cvy att"),
    ("convoy_escort/defend", "cvy def"),
]
DRILLS = ["attack", "defend", "goto"]


def windows(rows: list[dict], w: int):
    last = rows[-1]["update"]
    lo = 1
    while lo <= last:
        hi = min(lo + w - 1, last)
        yield lo, hi, [r for r in rows if lo <= r["update"] <= hi]
        lo = hi + 1


def wavg(rows, val_key, w_key, sub):
    num = den = 0.0
    for r in rows:
        v = (r.get(val_key) or {}).get(sub)
        n = (r.get(w_key) or {}).get(sub)
        if v is None or not n:
            continue
        num += v * n
        den += n
    return (num / den if den else None), int(den)


def dm(rows):
    num = den = 0.0
    for r in rows:
        for k, n in (r.get("episodes_by_class") or {}).items():
            if k[0].isdigit() and "v" in k:
                v = (r.get("win_by_class") or {}).get(k)
                if v is not None and n:
                    num += v * n
                    den += n
    return (num / den if den else None), int(den)


def f(x, d=3):
    return "-" if x is None else f"{x:.{d}f}"


def main() -> None:
    args = sys.argv[1:]
    w = 500
    if "--window" in args:
        i = args.index("--window")
        w = int(args[i + 1])
        del args[i : i + 2]
    arms = args or ["mix_s1", "mix_s2"]
    head = (["Arm", "Updates"] + [c[1] + " win (n)" for c in CLASSES] + ["dm win (n)"]
            + [f"drill {d}" for d in DRILLS] + ["bomber hit", "bomber/gunship dmg"])
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for arm in arms:
        rows = [json.loads(l) for l in open(HERE / arm / "log.jsonl")]
        # A restart can repeat updates; keep the last record of each.
        by = {r["update"]: r for r in rows}
        rows = [by[u] for u in sorted(by)]
        for lo, hi, rs in windows(rows, w):
            cells = [arm, f"{lo}–{hi}"]
            for key, _ in CLASSES:
                v, n = wavg(rs, "win_by_class", "episodes_by_class", key)
                cells.append(f"{f(v, 2)} ({n})")
            v, n = dm(rs)
            cells.append(f"{f(v, 2)} ({n})")
            for d in DRILLS:
                v, _ = wavg(rs, "drill_success", "drill_episodes", d)
                cells.append(f(v, 2))
            hit = wavg(rs, "hull_hit_rate", "hull_samples", "bomber")[0]
            bd = wavg(rs, "hull_damage_dealt", "hull_samples", "bomber")[0]
            gd = wavg(rs, "hull_damage_dealt", "hull_samples", "gunship")[0]
            cells.append(f(hit))
            cells.append(f(bd / gd if bd is not None and gd else None, 2))
            print("| " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
