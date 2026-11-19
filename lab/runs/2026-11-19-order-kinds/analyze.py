"""Tables from this run's ``order_rules.py`` outputs (``out/<pilot>_k3_<rule>.json``).
Run from the repo root:

    .venv/bin/python lab/runs/2026-11-19-order-kinds/analyze.py [pilot]

Prints markdown: the ordered side's score (± is 1.96 standard errors), its cost against
``none`` paired match by match, and the ordered side's first-30-s and whole-match order
telemetry, with the unseen side under ``none`` as the free reference.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).parent / "out"
RULES = (
    "none",
    "nearest",
    "goto_front",
    "goto_front_deadline",
    "goto_rally",
    "defend_ward",
    "defend_ring",
)


def load(pilot: str, rule: str) -> dict | None:
    p = OUT / f"{pilot}_k3_{rule}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def pm(x: np.ndarray) -> str:
    return f"{x.mean():.3f} ± {1.96 * x.std(ddof=1) / math.sqrt(x.size):.3f}"


def fmt(x: float | None, nd: int = 2) -> str:
    return "" if x is None or not math.isfinite(x) else f"{x:.{nd}f}"


def scores(pilot: str) -> None:
    ctrl = load(pilot, "none")
    print(
        "| Rule | Matches | Ordered score | Minus no orders (paired) "
        "| fighter (cost) | strafer (cost) | gunship (cost) |"
    )
    print("|---|---|---|---|---|---|---|")
    for rule in RULES:
        d = load(pilot, rule)
        if d is None:
            continue
        s = np.asarray(d["per_match"]["score"])
        cost = "" if ctrl is None or rule == "none" else pm(s - np.asarray(ctrl["per_match"]["score"]))
        hull = np.asarray(d["per_match"]["hull"])
        base = np.asarray(ctrl["per_match"]["score"]) if ctrl is not None else None
        cells = []
        for h in ("fighter", "strafer", "gunship"):
            m = hull == h
            c = "" if base is None or rule == "none" else f" ({pm(s[m] - base[m])})"
            cells.append(f"{s[m].mean():.2f}{c}")
        print(f"| `{rule}` | {d['n']} | {pm(s)} | {cost} | " + " | ".join(cells) + " |")


def window_row(name: str, d: dict, side: str) -> str:
    s = d["sides"][side]
    n = d["n"]
    alive = s["alive_s"]
    dealt = s["dealt"]
    tgt_share = s["dealt_tgt"] / dealt if dealt and s["ordered_s"] else None
    defend_dealt = s.get("dealt_threat", 0.0) + s.get("dealt_nonthreat", 0.0)
    threat_share = s["dealt_threat"] / defend_dealt if defend_dealt else None
    dist_ward = s["dist_ward_sum"] / (s["defend_s"] * 30) if s.get("defend_s") else None
    return (
        f"| {name} | {s['lost'] / n:.2f} | {s['advance_m'] / alive:+.1f} | "
        f"{s['eff_ordered_s'] / alive:.2f} | {s['any_arc_s'] / alive:.3f} | {dealt / n:.0f} | "
        f"{s['taken'] / n:.0f} | {fmt(tgt_share)} | {fmt(threat_share)} | {fmt(dist_ward, 0)} | "
        f"{s['ward_lost'] / n:.2f} | {s['ward_taken'] / n:.0f} |"
    )


def window(pilot: str) -> None:
    print(
        "| Side | Lost | Advance (m/s) | Under an order | Any enemy in arc | Dealt | Taken "
        "| Share on target | Defenders' share on threats | Defender to ward (m) "
        "| Wards lost | Taken as ward |"
    )
    print("|" + "---|" * 12)
    ctrl = load(pilot, "none")
    if ctrl is not None:
        print(window_row("`none`, free side (unseen)", ctrl, "unseen"))
    for rule in RULES:
        d = load(pilot, rule)
        if d is not None:
            print(window_row(f"`{rule}`, ordered", d, "ordered"))


def orders(pilot: str) -> None:
    print(
        "| Rule | Ships | Go-to: arrived | missed | died first | still open at the end "
        "| s to arrive (quartiles) | Order spent (share) | s to spent (median) | Match s |"
    )
    print("|" + "---|" * 10)
    for rule in RULES:
        d = load(pilot, rule)
        if d is None or rule == "none":
            continue
        o = d["orders"]["ordered"]
        g = o["goto_ships"]
        q = o["arrive_s_quartiles"]
        sq = o["spent_s_quartiles"]
        share = (lambda k: f"{o[k] / g:.2f}") if g else (lambda k: "")
        print(
            f"| `{rule}` | {o['ships']} | {share('arrived')} | {share('missed')} | "
            f"{share('died_before_end_of_goto')} | {share('goto_open_at_match_end')} | "
            f"{' / '.join(f'{x:.1f}' for x in q)} | "
            f"{o['spent'] / max(o['ordered_ships'], 1):.2f} | {fmt(sq[1] if sq else None, 1)} | "
            f"{o['match_s_mean']:.0f} |"
        )


def timeline(pilot: str) -> None:
    bins = (0, 2, 4, 6, 8, 10, 12, 16, 20, 24, 28)
    print("| Rule | Row | " + " | ".join(f"{t}" for t in bins) + " |")
    print("|" + "---|" * (len(bins) + 2))
    for rule in RULES:
        d = load(pilot, rule)
        if d is None:
            continue
        tl = d["timeline"]
        bs = tl["bin_s"]
        idx = [t // bs for t in bins]
        adv = np.asarray(tl["advance_m"]) / np.maximum(np.asarray(tl["alive_s"]), 1e-9)
        lost = np.cumsum(np.asarray(tl["lost"]), axis=1) / d["n"]
        gap = np.asarray(tl["centroid_gap"])
        rows = (
            ("gap (m)", [f"{gap[j]:.0f}" for j in idx]),
            ("ordered toward (m/s)", [f"{adv[0, j]:+.0f}" for j in idx]),
            ("unseen toward (m/s)", [f"{adv[1, j]:+.0f}" for j in idx]),
            ("ordered lost so far", [f"{lost[0, j]:.2f}" for j in idx]),
            ("unseen lost so far", [f"{lost[1, j]:.2f}" for j in idx]),
        )
        for name, vals in rows:
            print(f"| `{rule}` | {name} | " + " | ".join(vals) + " |")


def main() -> int:
    pilot = sys.argv[1] if len(sys.argv) > 1 else "followers_school_1052"
    print(f"# {pilot}\n\n## Scores (ordered side against the unseen side, 3 v 3)\n")
    scores(pilot)
    print("\n## First 30 s, per match\n")
    window(pilot)
    print("\n## Whole match: how the orders ended (ordered side, per ship)\n")
    orders(pilot)
    print("\n## Over time (2-s bins, first 30 s; t is the bin's start)\n")
    timeline(pilot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
