"""Gates of plan.md §5 (run B3) from the JSONs that ``eval.sh`` writes.

    .venv/bin/python lab/runs/2026-11-01-order-pilot-b3/gates.py [--run DIR] size
    .venv/bin/python lab/runs/2026-11-01-order-pilot-b3/gates.py [--run DIR] bounds
    .venv/bin/python lab/runs/2026-11-01-order-pilot-b3/gates.py [--run DIR] [gates [name ...]]

``size`` prints the following eval's matches per random-commander scenario from
the sizing run (``eval/sizing_w1_400_orders.json``; ``order_gates_b3.orders_n``).
``bounds`` applies the teacher-first rule (``order_gates_b3.teacher_bounds``: the
teacher's following against w1_400's hidden pass) and writes ``eval/o_bounds.json``
and ``eval/o_bounds.md``; it refuses to change bounds that already exist once a
candidate has been evaluated. ``gates`` (the default) writes ``eval/gates.json`` and
``eval/gates.md`` and prints the table, every failed check, the following of the
teacher, w1_400 and each candidate (followed and hidden), engine duty per hull and
order kind, and the pick (the passing candidate with the highest mean mission win vs
v1, ties by the deathmatch win vs v1). It exits 0 whether or not one passes; a
missing baseline is an error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from spacefight.eval import order_gates_b3 as G  # noqa: E402
from spacefight.eval.fleet import FleetResult  # noqa: E402
from spacefight.eval.missions import MissionResult, default_rosters  # noqa: E402
from spacefight.eval.orders import (  # noqa: E402
    FOLLOWED,
    HIDDEN,
    KINDS,
    RANDOM,
    FollowSummary,
    OrdersResult,
)

# A candidate needs every one of these (eval.sh writes them).
SUFFIXES = (
    "_orders.json",
    "_missions_vs_v1.json",
    "_missions_vs_w1_400.json",
    "_fleet_vs_script.json",
    "_fleet_vs_v1.json",
)
# Following references reported beside the candidates (eval.sh baseline).
REFERENCES = ("teacher", "w1_400")
SIZING = "sizing_w1_400_orders.json"
BOUNDS = "o_bounds.json"


def _orders(path: Path) -> OrdersResult:
    return OrdersResult.from_json(path.read_text())


def candidates(eval_dir: Path) -> list[str]:
    """Names with every gate eval present, sorted by arm then update."""
    names = [p.name.removesuffix(SUFFIXES[0]) for p in eval_dir.glob(f"*{SUFFIXES[0]}")]
    names = [n for n in names if n not in REFERENCES and not n.startswith("sizing")]
    complete = [
        n for n in names if all((eval_dir / f"{n}{s}").is_file() for s in SUFFIXES)
    ]

    def key(name: str) -> tuple[str, int]:
        arm, _, update = name.rpartition("_")
        return (arm, int(update) if update.isdigit() else -1)

    return sorted(complete, key=key)


def size(eval_dir: Path, low: int, high: int) -> int:
    """Matches per random-commander scenario (plan.md §5, the sizing rule)."""
    sizing = _orders(eval_dir / SIZING)
    block = math.lcm(*(2 * len(default_rosters(m)) for m in sizing.config.missions))
    return G.orders_n(sizing, block, low, high)


def write_bounds(eval_dir: Path) -> G.OBounds:
    """The teacher-first O bounds; never rewritten once a candidate was evaluated.

    Raises:
        SystemExit: The teacher's or w1_400's following is missing, or the bounds
            would change after a candidate's eval exists.
    """
    paths = [eval_dir / f"{r}_orders.json" for r in REFERENCES]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise SystemExit(f"missing {missing}: run eval.sh baseline first")
    bounds = G.teacher_bounds(_orders(paths[0]), _orders(paths[1]))
    out = eval_dir / BOUNDS
    if out.is_file():
        old = G.OBounds.from_json(out.read_text())
        if old != bounds and candidates(eval_dir):
            raise SystemExit(f"{out} differs and candidates were evaluated: keep it")
    out.write_text(bounds.to_json() + "\n")
    text = "O bounds after the teacher-first rule (plan.md §5):\n\n" + bounds.markdown()
    (eval_dir / "o_bounds.md").write_text(text + "\n")
    print(text)
    return bounds


def load_baselines(eval_dir: Path) -> G.Baselines:
    """The baseline stage's outputs.

    Raises:
        SystemExit: One is missing.
    """
    paths = {
        "bounds": eval_dir / BOUNDS,
        "missions": eval_dir / "v1_vs_v1_missions.json",
        "fleet": eval_dir / "v1_fleet_vs_script.json",
    }
    missing = [str(p) for p in paths.values() if not p.is_file()]
    if missing:
        raise SystemExit(f"missing baselines {missing}: run run.sh baseline first")
    return G.Baselines(
        o_bounds=G.OBounds.from_json(paths["bounds"].read_text()),
        v1_missions=MissionResult.from_json(paths["missions"].read_text()),
        v1_fleet_vs_script=FleetResult.from_json(paths["fleet"].read_text()),
    )


def load_evals(eval_dir: Path, name: str) -> G.Evals:
    """One candidate's gate evals."""
    path = [eval_dir / f"{name}{s}" for s in SUFFIXES]
    return G.Evals(
        orders=_orders(path[0]),
        missions_vs_v1=MissionResult.from_json(path[1].read_text()),
        missions_vs_w1=MissionResult.from_json(path[2].read_text()),
        fleet_vs_script=FleetResult.from_json(path[3].read_text()),
        fleet_vs_v1=FleetResult.from_json(path[4].read_text()),
    )


def _row(name: str, mode: str, pass_: str, f: FollowSummary) -> str:
    close = f.attack.close.median
    hull = f.defend.hull_lost_per_ward_minute
    return (
        f"| {name} | {mode}/{pass_} | "
        + ("never" if close is None else f"{close:.0f}")
        + f" | {f.attack.damage_share:.3f} | "
        + ("–" if hull is None else f"{hull:.3f}")
        + f" | {f.defend.ward_minutes:.0f} | {f.defend.threat_share:.3f} | "
        f"{f.goto.all.in_time:.3f} | {f.goto.near.in_time:.3f} | "
        f"{f.goto.far.in_time:.3f} | {f.goto.arrivals_per_min:.2f} |"
    )


def following_table(eval_dir: Path, names: list[str]) -> str:
    """Headline following of the references and the candidates, every pass."""
    lines = [
        "| pilot | commander/pass | attack close | attack share | defend hull lost "
        "/ ward-min | ward-min | threat share | go-to in time | near | far "
        "| arrivals/min |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name in [*REFERENCES, *names]:
        path = eval_dir / f"{name}{SUFFIXES[0]}"
        if not path.is_file():
            continue
        for mode, passes in _orders(path).by_commander.items():
            for pass_, f in passes.items():
                lines.append(_row(name, mode, pass_, f))
    return "\n".join(lines)


def duty_table(eval_dir: Path, names: list[str]) -> str:
    """Engine duty per hull and order kind (random commander, followed), reported."""
    lines = [
        "| pilot | hull | " + " | ".join(KINDS) + " |",
        "|---|---|" + "---|" * len(KINDS),
    ]
    for name in [*REFERENCES, *names]:
        path = eval_dir / f"{name}{SUFFIXES[0]}"
        if not path.is_file():
            continue
        f = _orders(path).by_commander[RANDOM][FOLLOWED]
        for hull, by_kind in f.engine_duty.items():
            cells = [f"{by_kind[k]:.2f}" if k in by_kind else "–" for k in KINDS]
            lines.append(f"| {name} | {hull} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def gates(eval_dir: Path, names: list[str]) -> int:
    """The gate table, the failures and the pick (module docstring)."""
    base = load_baselines(eval_dir)
    names = names or candidates(eval_dir)
    if not names:
        raise SystemExit(f"no candidate with all of {SUFFIXES} in {eval_dir}")
    reports = [G.check(n, load_evals(eval_dir, n), base) for n in names]
    pick = G.pick(reports)
    lines = [G.markdown(reports), ""]
    for r in reports:
        failed = G.failures(r)
        lines.append(
            f"- {r.candidate}: " + ("passes" if not failed else "; ".join(failed))
        )
    lines += [
        "",
        "O bounds (teacher-first, fixed by the baseline stage):",
        "",
        base.o_bounds.markdown(),
        "",
        f"Following, reported ({FOLLOWED} and {HIDDEN} passes; the teacher is the "
        "order-following scripts, w1_400 the init):",
        "",
        following_table(eval_dir, names),
        "",
        "Engine duty per hull and order kind, random commander, followed:",
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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--run", type=Path, default=Path(__file__).resolve().parent)
    sub = p.add_subparsers(dest="command")
    sizing = sub.add_parser("size", help="the following eval's n (prints it)")
    sizing.add_argument("--low", type=int, default=96)
    sizing.add_argument("--high", type=int, default=384)
    sub.add_parser("bounds", help="the teacher-first O bounds")
    judge = sub.add_parser("gates", help="the gate table (default)")
    judge.add_argument("names", nargs="*")
    args = p.parse_args()
    eval_dir = args.run / "eval"
    if args.command == "size":
        print(size(eval_dir, args.low, args.high))
        return 0
    if args.command == "bounds":
        write_bounds(eval_dir)
        return 0
    return gates(eval_dir, getattr(args, "names", []))


if __name__ == "__main__":
    sys.exit(main())
