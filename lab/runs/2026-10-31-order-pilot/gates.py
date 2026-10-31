"""Gate table of plan.md §5 from the JSONs that ``eval.sh`` writes.

    .venv/bin/python lab/runs/2026-10-31-order-pilot/gates.py [--run DIR] [name ...]

Writes ``<run>/eval/gates.json`` and ``<run>/eval/gates.md`` and prints the table,
every failed check, the secondary following baseline (each candidate against
itself with the order block zeroed), engine duty per hull and order kind, and the
pick (``spacefight.eval.order_gates.pick``: the passing candidate with the highest
mean mission win vs v1, ties by the deathmatch win vs v1). Exits 0 whether or not
one passes; a missing baseline is an error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from spacefight.eval import order_gates  # noqa: E402
from spacefight.eval.fleet import FleetResult  # noqa: E402
from spacefight.eval.missions import MissionResult  # noqa: E402
from spacefight.eval.orders_v1 import KINDS, OrdersResult  # noqa: E402

# A candidate needs every one of these (eval.sh writes them); "_orders_blank" is
# the secondary baseline, reported when present.
SUFFIXES = (
    "_orders.json",
    "_missions_vs_v1.json",
    "_fleet_vs_script.json",
    "_fleet_vs_v1.json",
)
BLANK = "_orders_blank.json"
BASELINES = {
    "v1_orders": "v1_orders.json",
    "v1_missions": "v1_vs_v1_missions.json",
    "v1_fleet_vs_script": "v1_fleet_vs_script.json",
}


def candidates(eval_dir: Path) -> list[str]:
    """Names with every gate eval present, sorted by arm then update."""
    names = [p.name.removesuffix(SUFFIXES[0]) for p in eval_dir.glob(f"*{SUFFIXES[0]}")]
    names = [n for n in names if n != "v1" and not n.endswith("_blank")]
    complete = [
        n for n in names if all((eval_dir / f"{n}{s}").is_file() for s in SUFFIXES)
    ]

    def key(name: str) -> tuple[str, int]:
        arm, _, update = name.rpartition("_")
        return (arm, int(update) if update.isdigit() else -1)

    return sorted(complete, key=key)


def load_baselines(eval_dir: Path) -> order_gates.Baselines:
    """The baseline stage's JSONs.

    Raises:
        SystemExit: One is missing.
    """
    paths = {k: eval_dir / v for k, v in BASELINES.items()}
    missing = [str(p) for p in paths.values() if not p.is_file()]
    if missing:
        raise SystemExit(f"missing baselines {missing}: run run.sh baseline first")
    return order_gates.Baselines(
        v1_orders=OrdersResult.from_json(paths["v1_orders"].read_text()),
        v1_missions=MissionResult.from_json(paths["v1_missions"].read_text()),
        v1_fleet_vs_script=FleetResult.from_json(
            paths["v1_fleet_vs_script"].read_text()
        ),
    )


def load_evals(eval_dir: Path, name: str) -> order_gates.Evals:
    """One candidate's gate evals."""
    path = {s: eval_dir / f"{name}{s}" for s in SUFFIXES}
    return order_gates.Evals(
        orders=OrdersResult.from_json(path[SUFFIXES[0]].read_text()),
        missions_vs_v1=MissionResult.from_json(path[SUFFIXES[1]].read_text()),
        fleet_vs_script=FleetResult.from_json(path[SUFFIXES[2]].read_text()),
        fleet_vs_v1=FleetResult.from_json(path[SUFFIXES[3]].read_text()),
    )


def secondary_table(eval_dir: Path, names: list[str]) -> str:
    """Following against the same pilot with the order block zeroed (reported)."""
    lines = [
        "| candidate | commander | guard: with − blank | hold: with − blank "
        "| attack share: with − blank | response: with / blank |",
        "|---|---|---|---|---|---|",
    ]
    for name in names:
        blank_path = eval_dir / f"{name}{BLANK}"
        if not blank_path.is_file():
            continue
        cand = OrdersResult.from_json((eval_dir / f"{name}{SUFFIXES[0]}").read_text())
        blank = OrdersResult.from_json(blank_path.read_text())
        for mode, f in cand.by_commander.items():
            b = blank.by_commander[mode]
            resp = [
                "never" if t.median is None else f"{t.median:.0f}"
                for t in (f.response, b.response)
            ]
            lines.append(
                f"| {name} | {mode} | {f.guard.time_inside - b.guard.time_inside:+.3f} "
                f"| {f.hold.time_inside - b.hold.time_inside:+.3f} | "
                f"{f.attack.damage_share - b.attack.damage_share:+.3f} | "
                f"{resp[0]} / {resp[1]} |"
            )
    return "\n".join(lines)


def duty_table(eval_dir: Path, names: list[str]) -> str:
    """Engine duty per hull and order kind (random commander), reported."""
    lines = [
        "| candidate | hull | " + " | ".join(KINDS) + " |",
        "|---|---|" + "---|" * len(KINDS),
    ]
    for name in ["v1", *names]:
        result = OrdersResult.from_json((eval_dir / f"{name}{SUFFIXES[0]}").read_text())
        for hull, by_kind in result.by_commander["random"].engine_duty.items():
            cells = [f"{by_kind[k]:.2f}" if k in by_kind else "–" for k in KINDS]
            lines.append(f"| {name} | {hull} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("names", nargs="*")
    args = p.parse_args()
    eval_dir = args.run / "eval"
    base = load_baselines(eval_dir)
    names = args.names or candidates(eval_dir)
    if not names:
        raise SystemExit(f"no candidate with all of {SUFFIXES} in {eval_dir}")
    reports = [order_gates.check(n, load_evals(eval_dir, n), base) for n in names]
    pick = order_gates.pick(reports)
    lines = [order_gates.markdown(reports), ""]
    for r in reports:
        failed = order_gates.failures(r)
        lines.append(
            f"- {r.candidate}: " + ("passes" if not failed else "; ".join(failed))
        )
    lines += [
        "",
        "Secondary baseline, reported (the candidate with the order block zeroed):",
        "",
        secondary_table(eval_dir, names),
        "",
        "Engine duty per hull and order kind, random commander, reported:",
        "",
        duty_table(eval_dir, names),
        "",
        f"pick: {pick or 'none (no candidate passes every gate)'}",
    ]
    text = "\n".join(lines)
    print(text)
    (eval_dir / "gates.md").write_text(text + "\n")
    payload = {"pick": pick, "candidates": [r.to_dict() for r in reports]}
    (eval_dir / "gates.json").write_text(json.dumps(payload, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
