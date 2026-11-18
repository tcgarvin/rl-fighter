"""Tables from ``order_rules.py`` outputs (``out/k<k>_<rule><tag>.json``). Run from the
repo root:

    .venv/bin/python lab/runs/2026-11-17-order-cost/analyze.py [tag]

Prints markdown: scores (± is 1.96 standard errors; the paired column is each rule
minus the script on the same matches), first-30-s telemetry by side, and how the first
ship lost in each match died.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).parent / "out"
RULES = ("scripted", "nearest", "near250", "focus", "none")


def load(k: int, rule: str, tag: str) -> dict | None:
    p = OUT / f"k{k}_{rule}{tag}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def pm(x: np.ndarray) -> str:
    return f"{x.mean():.3f} ± {1.96 * x.std(ddof=1) / math.sqrt(x.size):.3f}"


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    ks = [k for k in (1, 2, 3, 4) if load(k, "scripted", tag) or load(k, "nearest", tag)]
    print("## Scores (ordered side against the unseen side)\n")
    print(
        "| k v k | rule | matches | score | minus no orders, paired | minus scripted, paired "
        "| fighter | strafer | gunship |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for k in ks:
        base = load(k, "scripted", tag)
        ctrl = load(k, "none", tag)
        for rule in RULES:
            d = load(k, rule, tag)
            if d is None:
                continue
            s = np.asarray(d["per_match"]["score"])
            diff = "" if base is None or rule == "scripted" else pm(
                s - np.asarray(base["per_match"]["score"])
            )
            h = d["score_by_hull"]
            vs_none = "" if ctrl is None or rule == "none" else pm(
                s - np.asarray(ctrl["per_match"]["score"])
            )
            print(
                f"| {k} | {rule} | {d['n']} | {pm(s)} | {vs_none} | {diff} | {h['fighter']:.2f} | "
                f"{h['strafer']:.2f} | {h['gunship']:.2f} |"
            )
    print("\n## First 30 s, per side\n")
    print(
        "Shares are of a ship's time alive in the window. Damage is per match (hull and "
        "shield), split by whether the other ship is the ship's own (seen or hidden) "
        "target.\n"
    )
    cols = (
        "| k | rule | side | lost /match | under order | target in arc | other in arc "
        "| any in arc | target is nearest | m to target | m to nearest other "
        "| taken from target | taken from others | taken from behind | dealt to target "
        "| dealt to others |"
    )
    print(cols)
    print("|" + "---|" * (cols.count("|") - 1))
    for k in ks:
        for rule in RULES:
            d = load(k, rule, tag)
            if d is None:
                continue
            n = d["n"]
            for side in ("ordered", "unseen"):
                t = d["sides"][side]
                a = t["alive_s"]
                okt = max(t.get("ok_t_s", 0.0), 1e-9)
                oko = max(t.get("ok_o_s", 0.0), 1e-9)
                print(
                    f"| {k} | {rule} | {side} | {t['lost'] / n:.2f} | {t['ordered_s'] / a:.2f} "
                    f"| {t['tgt_arc_s'] / a:.3f} | {t['other_arc_s'] / a:.3f} "
                    f"| {t['any_arc_s'] / a:.3f} | {t['tgt_nearest_s'] / okt:.2f} "
                    f"| {t['dist_tgt_sum'] / okt / 30:.0f} | {t['dist_other_sum'] / oko / 30:.0f} "
                    f"| {t['taken_tgt'] / n:.0f} | {t['taken_other'] / n:.0f} "
                    f"| {t['taken_rear'] / n:.0f} "
                    f"| {t['dealt_tgt'] / n:.0f} | {t['dealt_other'] / n:.0f} |"
                )
    print("\n## Movement and shooting, first 30 s, per side\n")
    print(
        "| k | rule | side | speed (m/s) | toward enemy fleet (m/s) | m from own centroid "
        "| trigger held | trigger held, enemy in arc | hits per s in arc | m per hit "
        "| landed first hit | retreating | of which nose on nearest enemy | m/s toward own target |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ks:
        for rule in RULES:
            d = load(k, rule, tag)
            if d is None or "timeline" not in d:
                continue
            fh = np.asarray(d["per_match"]["first_hit"], dtype=float)
            fh[fh < 0] = np.inf
            firsts = (fh[:, 0] < fh[:, 1]).mean(), (fh[:, 1] < fh[:, 0]).mean()
            for sd, side in enumerate(("ordered", "unseen")):
                t = d["sides"][side]
                a = t["alive_s"]
                ticks = a * 30
                print(
                    f"| {k} | {rule} | {side} | {t['speed_sum'] / ticks:.0f} "
                    f"| {t['advance_m'] / a:.1f} | {t['cohesion_sum'] / ticks:.0f} "
                    f"| {t['trigger_s'] / a:.2f} | {t['trigger_arc_s'] / max(t['trigger_s'], 1e-9):.2f} "
                    f"| {t['hits_dealt'] / max(t['any_arc_s'], 1e-9):.1f} "
                    f"| {t['hit_range_sum'] / max(t['hits_dealt'], 1):.0f} | {firsts[sd]:.2f} "
                    + (
                        f"| {t['retreat_s'] / a:.2f} | {t['backpedal_s'] / max(t['retreat_s'], 1e-9):.2f} "
                        f"| {t['advance_tgt_m'] / max(t['ok_t_s'], 1e-9):.1f} |"
                        if "retreat_s" in t
                        else "| | | |"
                    )
                )
    print("\n## Timeline, 2-s bins (first 30 s)\n")
    for k in ks:
        for rule in RULES:
            d = load(k, rule, tag)
            if d is None or "timeline" not in d:
                continue
            tl = d["timeline"]
            n = d["n"]
            bins = len(tl["centroid_gap"])
            print(f"\n{k} v {k}, {rule}:\n")
            print("| t (s) | " + " | ".join(str(2 * b) for b in range(bins)) + " |")
            print("|---" * (bins + 1) + "|")
            print("| fleet gap (m) | " + " | ".join(f"{x:.0f}" for x in tl["centroid_gap"]) + " |")
            for sd, side in enumerate(("ordered", "unseen")):
                al = np.maximum(np.asarray(tl["alive_s"][sd]), 1e-9)
                adv = np.asarray(tl["advance_m"][sd]) / al
                print(f"| {side}: toward (m/s) | " + " | ".join(f"{x:.0f}" for x in adv) + " |")
            for sd, side in enumerate(("ordered", "unseen")):
                dl = np.asarray(tl["dealt"][sd]) / n
                print(f"| {side}: dealt /match | " + " | ".join(f"{x:.0f}" for x in dl) + " |")
            for sd, side in enumerate(("ordered", "unseen")):
                lo = np.cumsum(tl["lost"][sd]) / n
                print(f"| {side}: lost so far | " + " | ".join(f"{x:.2f}" for x in lo) + " |")
    print("\n## The first ship lost in each match\n")
    print(
        "| k | rule | side lost it first | of those: killed by its own target | killer "
        "behind its beam | its target in arc, last 2 s | enemies hitting it, last 3 s "
        "| its target off the nose (median deg) | m to target | m to killer | t (s) |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ks:
        for rule in RULES:
            d = load(k, rule, tag)
            if d is None:
                continue
            f = {key: np.asarray(v, dtype=float) for key, v in d["per_match"]["first"].items()}
            vs = np.asarray(d["per_match"]["first_victim_side"])
            for sd, name in ((0, "ordered"), (1, "unseen")):
                m = (vs == sd) & (f["killer"] >= 0)
                if not m.any():
                    continue
                with_t = m & (f["victim_target"] >= 0)
                own = (f["killer"][with_t] == f["victim_target"][with_t]).mean()
                behind = (f["killer_bearing_deg"][m] > 90).mean()
                print(
                    f"| {k} | {rule} | {name}: {(vs == sd).mean():.2f} | {own:.2f} "
                    f"| {behind:.2f} | {np.nanmean(f['tgt_arc_last2s'][with_t]):.2f} "
                    f"| {f['attackers_last3s'][m].mean():.2f} "
                    f"| {np.nanmedian(f['tgt_off_deg'][with_t]):.0f} "
                    f"| {np.nanmedian(f['dist_tgt'][with_t]):.0f} "
                    f"| {np.nanmedian(f['dist_killer'][m]):.0f} "
                    f"| {np.median(f['tick'][m]) / 30:.1f} |"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
