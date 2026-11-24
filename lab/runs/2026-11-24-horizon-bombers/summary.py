"""Tables of the horizon-bombers run (plan.md "Measures"). Measurements only: nothing
here passes or fails a pilot (WAR and the family rules pick what goes live).

    summary.py eval <dir>            one eval.sh directory
    summary.py report <run> [--arms h999 h995]
                                     every eval of each arm beside its parent, and the
                                     training telemetry (report.md)

An eval directory holds ``drills.json`` (the drill eval, order and dock drills,
rlf.eval.drills/1), ``dockm_carrier.json`` and ``dockm_station.json`` (recalls in
matches, rlf.lab.dock/1), ``swap_dm.json`` and ``swap_carrier.json`` (the bomber
swap, rlf.lab.swap/1) and, for the full evals, ``missions.json`` (against the script,
rlf.eval.mission/1), ``fleet.json`` (the fleet_v1 suite against the script,
rlf.eval.fleet/1) and ``oc_<base>_<rule>.json`` (the order cost, rlf.order_cost.rules/1).
Any may be missing (a periodic eval, a run in progress, a smoke); its cells print "-".
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
MISSIONS = ("carrier_battle", "convoy_escort", "station_assault")
FLEET_CLASSES = ("1v1", "2v2", "3v3", "4v4")
# The order cost's free opponents (eval.sh BASES) and the rules flown against them.
OC_BASES = (("base1052", "followers_school_1052"),)
OC_RULES = ("none", "nearest")
ARM_PARENTS = {"h999": "parent_dock2676", "h995": "parent_dock2676"}
ARM_TITLES = {
    "h999": "h999: the long horizon (gamma 0.999), bombers and mixed teammates",
    "h995": "h995: the parent's horizon (gamma 0.995), bombers and mixed teammates",
}
SWAPS = (("dm", "3 v 3 deathmatch"), ("carrier", "carrier battle"))


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
    """A measured number and its standard error (inf: none known)."""

    x: float
    se: float
    digits: int = 2
    signed: bool = False

    def text(self) -> str:
        sign = "+" if self.signed and self.x > 0 else ""
        head = f"{sign}{self.x:.{self.digits}f}"
        return (
            f"{head} ± {1.96 * self.se:.{self.digits}f}"
            if math.isfinite(self.se)
            else head
        )


def rate_value(node: dict[str, Any] | None) -> Value | None:
    """An ``rlf.eval.drills`` Rate (rate, se, n) as a Value."""
    if not node or not node.get("n"):
        return None
    return Value(float(node["rate"]), float(node["se"]))


# -- drills (drills.json) -----------------------------------------------------------------


def dock_drill(d: Path, kind: str, key: str) -> Value | None:
    data = load(d, "drills.json")
    if data is None or kind not in data["kinds"]:
        return None
    return rate_value(data["kinds"][kind].get(key))


def dock_lift(d: Path, kind: str) -> Value | None:
    data = load(d, "drills.json")
    if data is None or kind not in data["kinds"]:
        return None
    part = data["kinds"][kind]
    if part.get("lift") is None or not part.get("hidden"):
        return None
    shown, hidden = part["docked"], part["hidden"]["docked"]
    return Value(float(part["lift"]), math.hypot(shown["se"], hidden["se"]))


def order_bar(d: Path, path: tuple[str, str] | None) -> Value | None:
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
    return rate_value(kinds[kind].get(key))


# -- recalls in matches (dockm_*.json) ----------------------------------------------------


def mission_dock(d: Path, mission: str) -> dict[str, Any] | None:
    data = load(d, f"dockm_{mission}.json")
    return None if data is None else data["dock"]


def completion(d: Path, mission: str) -> Value | None:
    dock = mission_dock(d, mission)
    if dock is None or not dock["recalls"]:
        return None
    p = float(dock["completion"])
    return Value(p, binom_se(p, int(dock["recalls"])))


# -- wins against the script (missions.json, fleet.json) ----------------------------------


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


# -- the bomber swap (swap_<mission>.json) ------------------------------------------------


def swap_delta(d: Path, mission: str) -> Value | None:
    """Side X's paired score change when its first gunship becomes a bomber."""
    data = load(d, f"swap_{mission}.json")
    if data is None:
        return None
    return Value(float(data["delta"]), float(data["delta_ci95"]) / 1.96, signed=True)


def swap_damage(d: Path, mission: str, arm: str, target: str) -> Value | None:
    """The swapped slot's mean damage to ``target`` ships as gunship or bomber."""
    data = load(d, f"swap_{mission}.json")
    if data is None:
        return None
    return Value(float(data[arm][f"slot_damage_to_{target}"]), math.inf, digits=0)


# -- the order cost (oc_<base>_<rule>.json) -----------------------------------------------


def oc_score(d: Path, base: str, rule: str) -> Value | None:
    data = load(d, f"oc_{base}_{rule}.json")
    if data is None:
        return None
    return Value(float(data["score"]), float(data["score_se"]), digits=3)


def oc_cost(d: Path, base: str) -> Value | None:
    """``nearest`` minus ``none``, paired match by match (the same seeds and rosters)."""
    near, free = load(d, f"oc_{base}_nearest.json"), load(d, f"oc_{base}_none.json")
    if near is None or free is None:
        return None
    a, b = near["per_match"]["score"], free["per_match"]["score"]
    if len(a) != len(b) or len(a) < 2:
        return None
    diff = [x - y for x, y in zip(a, b)]
    n = len(diff)
    mean = sum(diff) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in diff) / (n - 1))
    return Value(mean, sd / math.sqrt(n), digits=3, signed=True)


def oc_side(d: Path, base: str, what: str) -> Value | None:
    """What the ordered side did under ``nearest`` in the first 30 s (as the kite drills'
    results table): ``arc`` target in arc (share of time alive), ``lost`` ships a match,
    ``dealt`` / ``taken`` damage to / from its target a match."""
    data = load(d, f"oc_{base}_nearest.json")
    if data is None:
        return None
    side, n = data["sides"]["ordered"], int(data["n"])
    if what == "arc":
        x = side["tgt_arc_s"] / side["alive_s"] if side["alive_s"] else math.nan
        return Value(x, math.inf)
    key = {"lost": "lost", "dealt": "dealt_tgt", "taken": "taken_tgt"}[what]
    return Value(side[key] / n, math.inf, digits=2 if what == "lost" else 0)


# -- one eval directory -------------------------------------------------------------------


def eval_rows(d: Path) -> list[tuple[str, Value | None]]:
    rows: list[tuple[str, Value | None]] = [
        ("calm dock drills: docked", dock_drill(d, "dock_calm", "docked")),
        ("calm dock drills: lift over the order hidden", dock_lift(d, "dock_calm")),
        ("calm dock drills: shot down", dock_drill(d, "dock_calm", "shot_down")),
        ("threat dock drills: docked", dock_drill(d, "dock_threat", "docked")),
        (
            "threat dock drills: docked of survivors",
            dock_drill(d, "dock_threat", "docked_of_survivors"),
        ),
        ("threat dock drills: shot down", dock_drill(d, "dock_threat", "shot_down")),
        ("carrier battle: recall completion", completion(d, "carrier")),
        ("station assault: recall completion", completion(d, "station")),
    ]
    rows += [(f"order drills: {bar}", order_bar(d, path)) for bar, path in ORDER_BARS]
    for mission, label in SWAPS:
        rows += [
            (f"bomber swap, {label}: score change", swap_delta(d, mission)),
            (
                f"bomber swap, {label}: bomber's damage to capital ships",
                swap_damage(d, mission, "swap", "capital"),
            ),
            (
                f"bomber swap, {label}: bomber's damage to strike craft",
                swap_damage(d, mission, "swap", "strike"),
            ),
            (
                f"bomber swap, {label}: gunship's damage to capital ships",
                swap_damage(d, mission, "base", "capital"),
            ),
        ]
    for base, label in OC_BASES:
        rows += [
            (f"order cost v free {label}: {rule}", oc_score(d, base, rule))
            for rule in OC_RULES
        ]
        rows += [
            (
                f"order cost v free {label}: cost (nearest − none, paired)",
                oc_cost(d, base),
            ),
            (
                f"order cost v free {label}: nearest, target in arc",
                oc_side(d, base, "arc"),
            ),
            (
                f"order cost v free {label}: nearest, ships lost a match",
                oc_side(d, base, "lost"),
            ),
            (
                f"order cost v free {label}: nearest, dealt to target",
                oc_side(d, base, "dealt"),
            ),
            (
                f"order cost v free {label}: nearest, taken from target",
                oc_side(d, base, "taken"),
            ),
        ]
    rows += [(f"vs script: {m}", mission_win(d, m)) for m in MISSIONS]
    rows += [("vs script: fleet_v1, all", fleet_win(d))]
    rows += [(f"vs script: fleet {k}", fleet_win(d, k)) for k in FLEET_CLASSES]
    return rows


def cell(v: Value | None) -> str:
    return "-" if v is None else v.text()


def eval_text(d: Path) -> str:
    lines = [f"# {d}", "", "| Measure | Value (± 95%) |", "|---|---|"]
    for name, v in eval_rows(d):
        lines.append(f"| {name} | {cell(v)} |")
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


def _weighted(
    acc: dict[str, list[float]], key: str, part: dict[str, Any], *fields: str
) -> None:
    """Adds ``part``'s episodes and episode-weighted ``fields`` into ``acc[key]``."""
    episodes = float(part.get("episodes") or 0)
    a = acc.setdefault(key, [0.0] * (len(fields) + 1))
    a[0] += episodes
    for i, f in enumerate(fields):
        value = part.get(f)
        a[i + 1] += float(value) * episodes if value is not None else 0.0


def telemetry(run: Path, arm: str, window: int) -> list[str]:
    path = run / arm / "log.jsonl"
    if not path.is_file():
        return [f"(no log for {arm})"]
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    lines = [
        "| Updates | calm dock: docked (n) | threat dock: docked (n) | carrier: recalls / "
        "docks a match (n) | kite: pass (n) | kite: pilots lost | kite: dealt / taken, "
        "target | attack: pass | drill rows |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for start in range(0, len(rows), window):
        chunk = rows[start : start + window]
        dock: dict[str, list[float]] = {}
        sides: dict[str, list[float]] = {}
        carrier = [0.0, 0.0, 0.0]
        share = []
        for row in chunk:
            for variant, part in (row.get("drill_dock") or {}).items():
                _weighted(dock, variant, part, "docked")
            for kind, part in (row.get("drill_sides") or {}).items():
                _weighted(
                    sides,
                    kind,
                    part,
                    "pass",
                    "pilots_lost",
                    "target_damage",
                    "damage_from_target",
                )
            md = (row.get("mission_docks") or {}).get("carrier_battle")
            if md and md["episodes"]:
                carrier[0] += md["episodes"]
                carrier[1] += md["recalls_per_match"] * md["episodes"]
                carrier[2] += md["docks_per_match"] * md["episodes"]
            if row.get("drill_rows_share") is not None:
                share.append(float(row["drill_rows_share"]))

        def mean(acc: dict[str, list[float]], key: str, i: int, digits: int = 2) -> str:
            a = acc.get(key)
            return fmt(a[i] / a[0], digits) if a and a[0] else "-"

        def with_n(acc: dict[str, list[float]], key: str) -> str:
            a = acc.get(key)
            return f"{mean(acc, key, 1)} ({int(a[0])})" if a and a[0] else "-"

        n = carrier[0]
        lines.append(
            f"| {chunk[0]['update']}-{chunk[-1]['update']} | {with_n(dock, 'calm')} | "
            f"{with_n(dock, 'threat')} | "
            f"{fmt(carrier[1] / n if n else None)} / {fmt(carrier[2] / n if n else None)} "
            f"({int(n)}) | {with_n(sides, 'attack_kite')} | "
            f"{mean(sides, 'attack_kite', 2)} | {mean(sides, 'attack_kite', 3, 0)} / "
            f"{mean(sides, 'attack_kite', 4, 0)} | {mean(sides, 'attack', 1)} | "
            f"{fmt(sum(share) / len(share) if share else None)} |"
        )
    return lines


def report(run: Path, arms: Sequence[str]) -> str:
    lines = [
        f"# Horizon and bombers: report ({run})",
        "",
        "Measurements only (± is 95%). The parent's column is its full-size eval; the "
        "periodic columns are at the quick sizes (64 drills a kind, 96 recall matches) "
        "and have no order cost or wins against the script. Order cost: 3 v 3, the "
        "checkpoint's side ordered (`nearest`) or not (`none`) against a free pilot; "
        "cost is nearest minus none, paired match by match. Bomber swap: the same "
        "matches with side X's first gunship as it is and as a bomber, the checkpoint "
        "on every strike slot; the change is paired match by match.",
        "",
    ]
    for arm in arms:
        parent = run / "eval" / ARM_PARENTS[arm]
        evals = evals_of(run, arm)
        lines += [f"## {ARM_TITLES.get(arm, arm)} (parent `{ARM_PARENTS[arm]}`)", ""]
        header = ["Measure", ARM_PARENTS[arm], *[label for _, label, _ in evals]]
        lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        columns = [parent, *[d for _, _, d in evals]]
        rows_by_column = [dict(eval_rows(d)) for d in columns]
        for name, _ in eval_rows(parent):
            cells = [cell(col.get(name)) for col in rows_by_column]
            if all(c == "-" for c in cells):
                continue
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines += ["", "Training (log.jsonl), windows of updates:", ""]
        lines += telemetry(run, arm, window=1 if "smoke" in str(run) else 250)
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="what", required=True)
    sub.add_parser("eval").add_argument("dir", type=Path)
    rep = sub.add_parser("report")
    rep.add_argument("run", type=Path)
    rep.add_argument("--arms", nargs="+", default=list(ARM_PARENTS))
    args = parser.parse_args(argv)
    if args.what == "eval":
        sys.stdout.write(eval_text(args.dir))
    else:
        sys.stdout.write(report(args.run, args.arms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
