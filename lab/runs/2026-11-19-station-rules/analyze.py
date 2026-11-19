"""Tables for results.md from out/<as>_<role>_<rule>.json (station_rules.py).

    uv run python lab/runs/2026-11-19-station-rules/analyze.py

Scores are the rule side's (a draw counts half). Deltas are paired match by match
against ``none`` on the same seeds, ± 1.96 standard errors of the paired difference.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / "out"
ORDER = {
    "attacker": (
        "none",
        "scripted",
        "rally_release",
        "bomber_only",
        "escort_bombers",
        "carrier_push",
    ),
    "defender": (
        "none",
        "scripted",
        "hold_reserve",
        "hold_late",
        "hold_never",
        "intercept_bombers",
        "hunt_bombers",
    ),
}
REASONS = (
    ("station_destroyed", "station"),
    ("assault_repelled", "repelled"),
    ("time_limit", "clock"),
)
TICK_HZ = 30


def load(station_as: str, role: str, rule: str) -> dict | None:
    path = OUT / f"{station_as}_{role}_{rule}.json"
    return json.loads(path.read_text()) if path.is_file() else None


def cell(station_as: str, role: str, rule: str) -> dict | None:
    """A table's cell: ``none`` is the baseline (unseen v unseen, the same matches as
    the rule ``none``, which the identity check shows)."""
    if rule == "none":
        return load(station_as, "check", "unseen")
    return load(station_as, role, rule)


def side_score(res: dict, role: str) -> np.ndarray:
    w = np.asarray(res["per_match"]["winner"])
    att = (w == 1) + 0.5 * (w == -1)
    return att if role == "attacker" else 1.0 - att


def ci(x: np.ndarray) -> float:
    return 1.96 * float(x.std(ddof=1) / math.sqrt(x.size))


def median_s(ticks: list[int]) -> str:
    t = np.asarray(ticks)
    t = t[t >= 0]
    return f"{np.median(t) / TICK_HZ:.0f}" if t.size else "-"


def table(station_as: str, role: str) -> list[str]:
    base = cell(station_as, role, "none")
    if base is None:
        return []
    b = side_score(base, role)
    rows = [
        f"### {role.capitalize()}, as {station_as}",
        "",
        "| Rule | n | Attacker win | Rule side score | vs `none` (paired) | End: station / repelled / clock | Median s |",
        "|---|---|---|---|---|---|---|",
    ]
    tele = [
        "",
        "| Rule | Torpedo hit the station | First torpedo hit (s) | Station damage: all / bombers | At 20 s: attackers / within 320 m / bombers / bombers within 300 m | At 20 s: defenders out / docked | At 45 s: station hull / carrier distance (m) | Rule side under an order | Go-to arrived / missed / ships |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for rule in ORDER[role]:
        res = cell(station_as, role, rule)
        if res is None:
            continue
        s = side_score(res, role)
        n = s.size
        pm = res["per_match"]
        if rule == "none":
            delta = ""
        else:
            k = min(n, b.size)
            d = s[:k] - b[:k]
            delta = f"{d.mean():+.3f} ± {ci(d):.3f}"
        aw = res["attacker_win_rate"]
        er = " / ".join(f"{res['end_reasons'].get(r, 0.0):.2f}" for r, _ in REASONS)
        rows.append(
            f"| `{rule}` | {n} | {aw:.3f} ± {1.96 * res['attacker_win_se']:.3f} | {s.mean():.3f} |"
            f" {delta} | {er} | {res['length_median_s']:.0f} |"
        )
        sn = res["snapshots"]
        k20 = res["snapshots_s"].index(20)
        k45 = res["snapshots_s"].index(45)
        fmt = lambda x, d=1: "-" if x is None else f"{x:.{d}f}"  # noqa: E731
        rs = res["rule_side"]
        go = (
            f"{rs['goto_arrived']} / {rs['goto_missed']} / {rs['goto_ships']}"
            if rs["goto_ships"]
            else "-"
        )
        tele.append(
            f"| `{rule}` | {res['torpedo_on_station_share']:.2f} | {median_s(pm['first_torpedo_on_station'])} |"
            f" {res['station_damage_mean']:.0f} / {res['station_damage_bomber_mean']:.0f} |"
            f" {fmt(sn['att_strike'][k20])} / {fmt(sn['att_near'][k20])} / {fmt(sn['bombers'][k20])} /"
            f" {fmt(sn['bombers_near'][k20])} |"
            f" {fmt(sn['def_out'][k20])} / {fmt(sn['def_hangar'][k20])} |"
            f" {fmt(sn['station_hull'][k45], 2)} / {fmt(sn['carrier_dist'][k45], 0)} |"
            f" {rs['ordered_share']:.2f} | {go} |"
        )
    return rows + tele + [""]


def timeline(station_as: str, role: str) -> list[str]:
    """Snapshots over time, per rule: station hull, attackers alive and near, defenders
    out (means over the matches still running), and the share still running."""
    rows = [
        f"#### Over time: {role}, as {station_as}",
        "",
        "| Rule | " + " | ".join(f"{s} s" for s in (10, 20, 30, 45, 60, 90)) + " |",
        "|---|" + "---|" * 6,
    ]
    for rule in ORDER[role]:
        res = cell(station_as, role, rule)
        if res is None:
            continue
        sn, run = res["snapshots"], res["running_share"]
        cells = []
        for k in range(len(res["snapshots_s"])):
            if sn["station_hull"][k] is None:
                cells.append("-")
                continue
            cells.append(
                f"{sn['station_hull'][k]:.2f} · {sn['att_strike'][k]:.1f} ({sn['att_near'][k]:.1f})"
                f" · {sn['def_out'][k] + sn['def_hangar'][k]:.1f} · {run[k]:.2f}"
            )
        rows.append(f"| `{rule}` | " + " | ".join(cells) + " |")
    return rows + [""]


def identity() -> list[str]:
    """``none`` reproduces ``unseen`` match for match (the logistics port). Torch's
    sampling stream depends on the batch, so the check compares cells of one size."""
    out = []
    for station_as in ("carrier", "convoy"):
        u = load(station_as, "checksmall", "unseen")
        if u is None:
            continue
        for role in ("attacker", "defender"):
            nres = load(station_as, role, "none")
            if nres is None:
                continue
            k = min(u["n"], nres["n"])
            same = all(
                u["per_match"][f][:k] == nres["per_match"][f][:k]
                for f in (
                    "winner",
                    "reason",
                    "end_tick",
                    "station_damage",
                    "first_torpedo_on_station",
                )
            )
            out.append(
                f"- {station_as}, {role} `none` vs `unseen` on {k} matches: {'identical' if same else 'DIFFERENT'}"
            )
    return out


def main() -> int:
    lines: list[str] = []
    for station_as in ("carrier", "convoy"):
        for role in ("attacker", "defender"):
            lines += table(station_as, role)
            if station_as == "carrier":
                lines += timeline(station_as, role)
    lines += identity()
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
