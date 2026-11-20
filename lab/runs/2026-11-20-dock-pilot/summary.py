"""Tables and gates of the dock-pilot run (plan.md "Gates").

    summary.py baseline <dir>        dock drill baselines (baseline.sh): one row a pilot
    summary.py eval <dir>            one eval.sh directory
    summary.py report <run> [--arms dock600 dock352]
                                     every eval of each arm against its parent, the
                                     training telemetry and the gates (report.md)

An eval directory holds ``dock.json`` (dock drills, rlf.eval.drills/1), ``dockm_carrier
.json`` and ``dockm_station.json`` (recalls in matches, rlf.lab.dock/1), ``drills.json``
(the order drills), ``missions.json`` (against the script, rlf.eval.mission/1) and
``fleet.json`` (the fleet_v1 suite against the script, rlf.eval.fleet/1). Any may be
missing (a run in progress, a smoke); its cells print "-" and its gates "n/a".
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DOCK_KINDS = ("dock_calm", "dock_threat")
ORDER_BARS = (
    ("goto_arrival", ("goto", "shown")),
    ("goto_lift", None),
    ("attack_target_hit", ("attack", "target_hit")),
    ("attack_side", ("attack", "chose_named")),
    ("attack_flip", ("attack", "flip")),
    ("defend_more_on_named", ("defend", "more_on_named")),
    ("defend_side", ("defend", "chose_named")),
    ("defend_flip", ("defend", "flip")),
)
MISSIONS = ("carrier_battle", "convoy_escort")
FLEET_CLASSES = ("1v1", "2v2", "3v3", "4v4")
# Gates (plan.md): lower bounds on the candidate's numbers.
CALM_DOCKED = 0.60
CALM_LIFT = 0.40
THREAT_DOCKED = 0.30
CARRIER_COMPLETION = 0.25
STATION_COMPLETION = 0.15
# "Beyond noise": more than this many standard errors of the difference below the parent.
NOISE_Z = 2.0
ARM_PARENTS = {"dock600": "parent600", "dock352": "parent352"}


def load(d: Path, name: str) -> dict[str, Any] | None:
    p = d / name
    return json.loads(p.read_text()) if p.is_file() else None


def fmt(x: float | None, digits: int = 2) -> str:
    return (
        "-"
        if x is None or (isinstance(x, float) and math.isnan(x))
        else f"{x:.{digits}f}"
    )


def binom_se(p: float, n: int) -> float:
    return math.sqrt(max(p * (1.0 - p), 0.0) / n) if n > 0 else math.inf


@dataclass(frozen=True)
class Value:
    """A measured share and its standard error."""

    x: float
    se: float

    def text(self) -> str:
        return (
            f"{self.x:.2f} ± {1.96 * self.se:.2f}"
            if math.isfinite(self.se)
            else f"{self.x:.2f}"
        )


def rate_value(node: dict[str, Any] | None) -> Value | None:
    """An ``rlf.eval.drills`` Rate (rate, se, n) as a Value."""
    if not node or not node.get("n"):
        return None
    return Value(float(node["rate"]), float(node["se"]))


def dock_drill(d: Path, kind: str, key: str) -> Value | None:
    data = load(d, "dock.json")
    if data is None or kind not in data["kinds"]:
        return None
    return rate_value(data["kinds"][kind][key])


def dock_lift(d: Path, kind: str) -> Value | None:
    data = load(d, "dock.json")
    if data is None or kind not in data["kinds"]:
        return None
    part = data["kinds"][kind]
    if part.get("lift") is None or not part.get("hidden"):
        return None
    shown, hidden = part["docked"], part["hidden"]["docked"]
    return Value(float(part["lift"]), math.hypot(shown["se"], hidden["se"]))


def mission_dock(d: Path, mission: str) -> dict[str, Any] | None:
    data = load(d, f"dockm_{mission}.json")
    return None if data is None else data["dock"]


def completion(d: Path, mission: str) -> Value | None:
    dock = mission_dock(d, mission)
    if dock is None or not dock["recalls"]:
        return None
    p = float(dock["completion"])
    return Value(p, binom_se(p, int(dock["recalls"])))


def order_bar(d: Path, bar: str, path: tuple[str, str] | None) -> Value | None:
    data = load(d, "drills.json")
    if data is None:
        return None
    kinds = data["kinds"]
    if path is None:  # goto_lift: shown minus hidden
        goto = kinds.get("goto")
        if not goto or goto.get("lift") is None or not goto.get("hidden"):
            return None
        return Value(
            float(goto["lift"]), math.hypot(goto["shown"]["se"], goto["hidden"]["se"])
        )
    kind, key = path
    if kind not in kinds:
        return None
    node = kinds[kind][key]
    return Value(float(node["rate"]), float(node["se"]))


def mission_win(d: Path, mission: str) -> Value | None:
    data = load(d, "missions.json")
    if data is None or mission not in data["missions"]:
        return None
    m = data["missions"][mission]
    return Value(float(m["win_rate"]), binom_se(float(m["win_rate"]), int(m["n"])))


def fleet_win(d: Path, klass: str | None = None) -> Value | None:
    data = load(d, "fleet.json")
    if data is None:
        return None
    if klass is None:
        p, n = float(data["side_a"]["win_rate"]), int(data["match"]["n"])
    else:
        part = data["classes"].get(klass)
        if not part:
            return None
        p, n = float(part["win_rate"]), int(part["n"])
    return Value(p, binom_se(p, n))


def no_worse(cand: Value | None, parent: Value | None) -> bool | None:
    """Within noise of the parent or above it (plan.md); None when either is missing."""
    if cand is None or parent is None:
        return None
    se = math.hypot(cand.se, parent.se)
    if not math.isfinite(se):
        return None
    return cand.x >= parent.x - NOISE_Z * se


def at_least(v: Value | None, floor: float) -> bool | None:
    return None if v is None else v.x >= floor


def verdict(ok: bool | None) -> str:
    return "n/a" if ok is None else ("pass" if ok else "**FAIL**")


# -- baseline -----------------------------------------------------------------------------


def baseline(d: Path) -> str:
    lines = [
        "| Pilot | Calm: docked | shot down | came within 30 m | docked of those | "
        "closest, median m | lift | Threat: docked | shot down | docked of survivors | "
        "fly-throughs a drill |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for path in sorted(d.glob("*.json")):
        data = json.loads(path.read_text())
        calm, threat = data["kinds"].get("dock_calm"), data["kinds"].get("dock_threat")
        if calm is None or threat is None:
            continue
        near = calm["closest_m"] or {}
        lines.append(
            f"| {data['name']} | {fmt(calm['docked']['rate'])} | "
            f"{fmt(calm['shot_down']['rate'])} | {fmt(calm['came_near']['rate'])} | "
            f"{fmt(calm['docked_of_near']['rate'])} | {fmt(near.get('median'), 0)} | "
            f"{fmt(calm['lift'])} | {fmt(threat['docked']['rate'])} | "
            f"{fmt(threat['shot_down']['rate'])} | "
            f"{fmt(threat['docked_of_survivors']['rate'])} | "
            f"{fmt(threat['fly_throughs_per_drill']['mean'])} |"
        )
    n = next(
        (
            json.loads(p.read_text())["config"]["n_per_kind"]
            for p in sorted(d.glob("*.json"))
        ),
        0,
    )
    return f"Dock drills, {n} a kind (seed 500000).\n\n" + "\n".join(lines) + "\n"


# -- one eval directory -------------------------------------------------------------------


def eval_rows(d: Path) -> list[tuple[str, Value | None]]:
    rows: list[tuple[str, Value | None]] = [
        ("calm drills: docked", dock_drill(d, "dock_calm", "docked")),
        ("calm drills: lift over the order hidden", dock_lift(d, "dock_calm")),
        ("calm drills: shot down", dock_drill(d, "dock_calm", "shot_down")),
        ("threat drills: docked", dock_drill(d, "dock_threat", "docked")),
        (
            "threat drills: docked of survivors",
            dock_drill(d, "dock_threat", "docked_of_survivors"),
        ),
        ("threat drills: shot down", dock_drill(d, "dock_threat", "shot_down")),
        ("carrier battle: recall completion", completion(d, "carrier")),
        ("station assault: recall completion", completion(d, "station")),
    ]
    rows += [
        (f"order drills: {bar}", order_bar(d, bar, path)) for bar, path in ORDER_BARS
    ]
    rows += [(f"vs script: {m}", mission_win(d, m)) for m in MISSIONS]
    rows += [("vs script: fleet_v1, all", fleet_win(d))]
    rows += [(f"vs script: fleet {k}", fleet_win(d, k)) for k in FLEET_CLASSES]
    return rows


def eval_text(d: Path) -> str:
    lines = [f"# {d}", "", "| Measure | Value (± 95%) |", "|---|---|"]
    for name, v in eval_rows(d):
        lines.append(f"| {name} | {'-' if v is None else v.text()} |")
    for mission in ("carrier", "station"):
        dock = mission_dock(d, mission)
        if dock is not None:
            lines.append(
                f"\n{mission}: recalls a match {fmt(dock['recalls_per_match'])}, docked a "
                f"match {fmt(dock['docked_per_match'])}, of survivors "
                f"{fmt(dock['completion_of_survivors'])}, failures {dock['failure_modes']}"
            )
    return "\n".join(lines) + "\n"


# -- the report ---------------------------------------------------------------------------


def evals_of(run: Path, arm: str) -> list[tuple[int, str, Path]]:
    """The arm's eval directories in update order: (update, label, dir)."""
    out = []
    for d in sorted((run / "eval").glob(f"{arm}_*")):
        m = re.fullmatch(rf"{re.escape(arm)}_(final_)?(\d+)", d.name)
        if m and d.is_dir():
            out.append((int(m.group(2)), d.name, d))
    return sorted(out)


def gates(cand: Path, parent: Path) -> list[tuple[str, bool | None, str]]:
    """(gate, verdict, what it measured) for one candidate against its parent."""
    out: list[tuple[str, bool | None, str]] = []
    calm = dock_drill(cand, "dock_calm", "docked")
    lift = dock_lift(cand, "dock_calm")
    ok = (
        None
        if calm is None or lift is None
        else bool(calm.x >= CALM_DOCKED and lift.x >= CALM_LIFT)
    )
    out.append(
        (
            f"1. calm dock drills: docked >= {CALM_DOCKED}, lift >= {CALM_LIFT}",
            ok,
            f"{'-' if calm is None else calm.text()}, lift {'-' if lift is None else lift.text()}",
        )
    )
    threat = dock_drill(cand, "dock_threat", "docked")
    out.append(
        (
            f"2. threat dock drills: docked >= {THREAT_DOCKED}",
            at_least(threat, THREAT_DOCKED),
            "-" if threat is None else threat.text(),
        )
    )
    carrier, station = completion(cand, "carrier"), completion(cand, "station")
    ok3 = (
        None
        if carrier is None or station is None
        else bool(carrier.x >= CARRIER_COMPLETION and station.x >= STATION_COMPLETION)
    )
    out.append(
        (
            f"3. scripted-commander missions: recall completion, carrier >= "
            f"{CARRIER_COMPLETION}, station >= {STATION_COMPLETION}",
            ok3,
            f"{'-' if carrier is None else carrier.text()}, "
            f"{'-' if station is None else station.text()}",
        )
    )
    slips = []
    seen = []
    for bar, path in ORDER_BARS:
        verdict_bar = no_worse(order_bar(cand, bar, path), order_bar(parent, bar, path))
        seen.append(verdict_bar)
        if verdict_bar is False:
            slips.append(bar)
    ok4 = None if any(v is None for v in seen) else not slips
    out.append(
        (
            "4. order drill bars: none below the parent beyond noise",
            ok4,
            f"slipped: {', '.join(slips) or 'none'}",
        )
    )
    slips, seen = [], []
    wins: list[tuple[str, Value | None, Value | None]] = [
        (m, mission_win(cand, m), mission_win(parent, m)) for m in MISSIONS
    ]
    wins.append(("fleet_v1", fleet_win(cand), fleet_win(parent)))
    for name, c, p in wins:
        v = no_worse(c, p)
        seen.append(v)
        if v is False:
            slips.append(f"{name} {c.x:.2f} vs {p.x:.2f}" if c and p else name)
    ok5 = None if any(v is None for v in seen) else not slips
    out.append(
        (
            "5. win rates against the script (carrier, convoy, fleet_v1): none below the "
            "parent beyond noise",
            ok5,
            f"slipped: {', '.join(slips) or 'none'}",
        )
    )
    return out


def telemetry(run: Path, arm: str, window: int) -> list[str]:
    path = run / arm / "log.jsonl"
    if not path.is_file():
        return [f"(no log for {arm})"]
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    lines = [
        f"| Updates | calm: docked (n) | threat: docked (n) | fly-throughs a calm drill | "
        f"carrier: recalls / docks a match (n) | completion | drill rows |",
        "|---|---|---|---|---|---|---|",
    ]
    for start in range(0, len(rows), window):
        chunk = rows[start : start + window]
        acc: dict[str, list[float]] = {"calm": [0, 0, 0.0], "threat": [0, 0, 0.0]}
        carrier = [0.0, 0.0, 0.0]
        share = []
        for row in chunk:
            for variant, part in (row.get("drill_dock") or {}).items():
                a = acc.setdefault(variant, [0, 0, 0.0])
                a[0] += part["episodes"]
                a[1] += part["docked"] * part["episodes"]
                a[2] += part["fly_throughs"] * part["episodes"]
            md = (row.get("mission_docks") or {}).get("carrier_battle")
            if md and md["episodes"]:
                carrier[0] += md["episodes"]
                carrier[1] += md["recalls_per_match"] * md["episodes"]
                carrier[2] += md["docks_per_match"] * md["episodes"]
            if row.get("drill_rows_share") is not None:
                share.append(float(row["drill_rows_share"]))

        def docked(v: list[float]) -> str:
            return f"{v[1] / v[0]:.2f} ({int(v[0])})" if v[0] else "-"

        n = carrier[0]
        lines.append(
            f"| {chunk[0]['update']}-{chunk[-1]['update']} | {docked(acc['calm'])} | "
            f"{docked(acc['threat'])} | "
            f"{fmt(acc['calm'][2] / acc['calm'][0] if acc['calm'][0] else None)} | "
            f"{fmt(carrier[1] / n if n else None)} / {fmt(carrier[2] / n if n else None)} "
            f"({int(n)}) | {fmt(carrier[2] / carrier[1] if carrier[1] else None)} | "
            f"{fmt(sum(share) / len(share) if share else None)} |"
        )
    return lines


def report(run: Path, arms: Sequence[str]) -> str:
    lines = [f"# Dock pilot: report ({run})", ""]
    verdicts = {}
    for arm in arms:
        parent = run / "eval" / ARM_PARENTS[arm]
        evals = evals_of(run, arm)
        lines += [f"## {arm} (parent `{ARM_PARENTS[arm]}`)", ""]
        header = ["Measure", ARM_PARENTS[arm], *[label for _, label, _ in evals]]
        lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        columns = [parent, *[d for _, _, d in evals]]
        rows_by_column = [dict(eval_rows(d)) for d in columns]
        for name, _ in eval_rows(parent):
            cells = [
                "-" if col.get(name) is None else col[name].text()  # type: ignore[union-attr]
                for col in rows_by_column
            ]
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        finals = [d for _, label, d in evals if "final" in label]
        lines.append("")
        if finals:
            final = finals[-1]
            lines += [f"Gates, `{final.name}` against `{parent.name}`:", ""]
            results = gates(final, parent)
            for gate, ok, measured in results:
                lines.append(f"- {gate}: {verdict(ok)} ({measured})")
            oks = [ok for _, ok, _ in results]
            verdicts[arm] = None if any(o is None for o in oks) else all(oks)
            lines.append(f"\n{arm}: {verdict(verdicts[arm])}")
        else:
            lines.append("No final eval yet.")
        if evals:
            # Every checkpoint's gates; the periodic ones are at the quick sizes, so
            # wider, and only point at a checkpoint to evaluate at full size.
            lines += [
                "",
                "Gates by checkpoint (periodic evals at the quick sizes):",
                "",
                "| Checkpoint | 1 calm | 2 threat | 3 missions | 4 drills | 5 wins |",
                "|---|---|---|---|---|---|",
            ]
            for _, label, d in evals:
                cells = [verdict(ok) for _, ok, _ in gates(d, parent)]
                lines.append(f"| {label} | " + " | ".join(cells) + " |")
        lines += ["", "Training (log.jsonl), windows of updates:", ""]
        lines += telemetry(run, arm, window=1 if "smoke" in str(run) else 250)
        lines.append("")
    passing = [a for a, v in verdicts.items() if v]
    lines.append(
        "**Run: "
        + (f"PASS ({', '.join(passing)})" if passing else "no arm passes every gate")
        + "** (plan.md: an arm passes on all five gates; each arm is judged alone)."
    )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="what", required=True)
    sub.add_parser("baseline").add_argument("dir", type=Path)
    sub.add_parser("eval").add_argument("dir", type=Path)
    rep = sub.add_parser("report")
    rep.add_argument("run", type=Path)
    rep.add_argument("--arms", nargs="+", default=list(ARM_PARENTS))
    args = parser.parse_args(argv)
    if args.what == "baseline":
        sys.stdout.write(baseline(args.dir))
    elif args.what == "eval":
        sys.stdout.write(eval_text(args.dir))
    else:
        sys.stdout.write(report(args.run, args.arms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
