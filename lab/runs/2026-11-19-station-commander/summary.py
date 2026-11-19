"""A learned commander's station-assault cells (eval.sh) against the hand rules.

    python lab/runs/2026-11-19-station-commander/summary.py \
        lab/runs/2026-11-19-station-commander/eval/<name>

Reads ``<dir>/<as>_<role>_learned.json`` (``station_rules.py --rule learned``) and the
hand-rule cells in ``../2026-11-19-station-rules/out`` (the same seeds, rosters and pilot
draws). Scores are the commander side's, a draw counting half. Deltas are paired match by
match, ± 1.96 standard errors of the paired difference. The verdict (plan.md) is on the
carrier reading: PASS if in both roles the commander beats no orders (the lower bound of
its delta above 0) and is not below the best hand rule by more than that noise
(``hold_late`` defending, ``carrier_push`` attacking); PARTIAL if it beats no orders in
both roles; FAIL otherwise.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

RULES_OUT = Path(__file__).resolve().parent.parent / "2026-11-19-station-rules" / "out"
BEST_RULE = {"defender": "hold_late", "attacker": "carrier_push"}
ROLES = ("defender", "attacker")
READINGS = ("carrier", "convoy")


def side_score(res: dict, role: str) -> np.ndarray:
    w = np.asarray(res["per_match"]["winner"])
    attacker = (w == 1) + 0.5 * (w == -1)
    return attacker if role == "attacker" else 1.0 - attacker


def paired(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Mean of ``a - b`` and its 95% half-width, over the matches both played."""
    n = min(a.size, b.size)
    d = a[:n] - b[:n]
    return float(d.mean()), float(1.96 * d.std(ddof=1) / math.sqrt(n))


def load(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None


def fmt(x: float | None, digits: int = 2) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    here = Path(argv[0])
    print(f"# {here.name}\n")
    print(
        "| Reading | Role | n | Score | vs none | Best rule | Rule vs none |"
        " vs the rule | End: station / repelled / clock |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    verdict: dict[str, tuple[bool, bool]] = {}
    for reading in READINGS:
        base = load(RULES_OUT / f"{reading}_check_unseen.json")
        for role in ROLES:
            res = load(here / f"{reading}_{role}_learned.json")
            if res is None or base is None:
                continue
            s = side_score(res, role)
            d_none = paired(s, side_score(base, role))
            rule = load(RULES_OUT / f"{reading}_{role}_{BEST_RULE[role]}.json")
            r_none = paired(side_score(rule, role), side_score(base, role)) if rule else None
            d_rule = paired(s, side_score(rule, role)) if rule else None
            ends = res["end_reasons"]
            print(
                f"| {reading} | {role} | {s.size} | {s.mean():.3f} |"
                f" {d_none[0]:+.3f} ± {d_none[1]:.3f} | `{BEST_RULE[role]}` |"
                + (f" {r_none[0]:+.3f} ± {r_none[1]:.3f} |" if r_none else " – |")
                + (f" {d_rule[0]:+.3f} ± {d_rule[1]:.3f} |" if d_rule else " – |")
                + f" {ends.get('station_destroyed', 0):.2f} /"
                f" {ends.get('assault_repelled', 0):.2f} / {ends.get('time_limit', 0):.2f} |"
            )
            if reading == "carrier" and d_rule is not None:
                verdict[role] = (
                    d_rule[0] + d_rule[1] >= 0.0,  # not below the rule beyond noise
                    d_none[0] - d_none[1] > 0.0,  # above no orders
                )
    print("\n## Telemetry (commander side)\n")
    print(
        "| Reading | Role | First launch s (median, IQR) | Station hull then |"
        " Hangar empty s | Re-orders / min | Under an order | Carrier to station m"
        " at 10/20/30/45/60/90 s | Station hull at 10/20/30/45/60/90 s |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for reading in READINGS:
        for role in ROLES:
            res = load(here / f"{reading}_{role}_learned.json")
            if res is None:
                continue
            la = res["launches"]
            iqr = la["first_launch_quartiles_s"]
            snaps = res["snapshots"]
            print(
                f"| {reading} | {role} | {fmt(la['first_launch_median_s'], 0)}"
                + (f" ({iqr[0]:.0f}–{iqr[1]:.0f})" if iqr else "")
                + f" | {fmt(la['station_hull_at_first_launch_median'])} |"
                f" {fmt(la['hangar_empty_median_s'], 0)} |"
                f" {fmt(la['orders_per_minute'], 1)} |"
                f" {res['rule_side']['ordered_share']:.2f} |"
                f" {' / '.join(fmt(x, 0) for x in snaps['carrier_dist'])} |"
                f" {' / '.join(fmt(x) for x in snaps['station_hull'])} |"
            )
    print(
        "\nHand rules for comparison (carrier reading): the script (`none`) launches the"
        " station's reserve at about 2 s and has emptied it by 4 s; `hold_late` waits for"
        " hull < 0.60 (first launch about 30 s, 16-match smoke: median 32 s at hull 0.54)."
        " `carrier_push`'s carrier is 396 m out at 20 s, 237 m at 45 s, 163 m at 90 s;"
        " the patrol's 420 to 460 m."
    )
    if len(verdict) == 2:
        if all(v[0] and v[1] for v in verdict.values()):
            word = "PASS"
        elif all(v[1] for v in verdict.values()):
            word = "PARTIAL"
        else:
            word = "FAIL"
        detail = ", ".join(
            f"{r}: {'matches the rule' if v[0] else 'below the rule'}, "
            f"{'beats' if v[1] else 'does not beat'} no orders"
            for r, v in verdict.items()
        )
        print(f"\n**Verdict: {word}** ({detail})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
