"""Attack and defend drills with every pilot in a bomber (SIM_VERSION 9), against the
same drills as generated: is a drill with a fixed forward rack still passable?

The drills are those of ``spacefight.eval.drills`` (same generator, seeds and swap
partners); only the pilots' hulls change. A bomber is slower than any drill hull, but the
drill clocks are set for a gunship (24 m/s), so the clock is not what fails it. Prints
JSON (``rlf.lab.bomber_drills/1``): per kind and arm, the drill eval's summary.

    uv run python lab/runs/2026-11-19-station-mix/bomber_drills.py --a script \
        --n-per-kind 32 --out bomber_drills_script.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from spacefight.env.drills import DrillGenerator  # noqa: E402
from spacefight.env.rosters import BOMBER, DRILL_ATTACK, DRILL_DEFEND  # noqa: E402
from spacefight.eval.controllers import make_controller  # noqa: E402
from spacefight.eval.drills import (  # noqa: E402
    DEFAULT_SEED,
    KIND_SEED_STRIDE,
    run_pass,
    summarise_attack,
    summarise_defend,
)


def as_bombers(spec):  # type: ignore[no-untyped-def]
    team0 = list(spec.teams[0])
    for slot in spec.pilots:
        team0[slot] = BOMBER
    return replace(spec, teams=(tuple(team0), spec.teams[1]))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--a", required=True, help="checkpoint or script")
    p.add_argument("--n-per-kind", type=int, default=64)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    gen = DrillGenerator()
    out: dict[str, object] = {"schema": "rlf.lab.bomber_drills/1", "a": args.a,
                              "n_per_kind": args.n_per_kind, "seed": args.seed}
    for k, (kind, summarise) in enumerate(
        ((DRILL_ATTACK, summarise_attack), (DRILL_DEFEND, summarise_defend)), start=1
    ):
        base = args.seed + k * KIND_SEED_STRIDE
        specs = gen.generate_many(kind, args.n_per_kind, base)
        for arm, chosen in (("as_drawn", specs), ("bombers", [as_bombers(s) for s in specs])):
            controller = make_controller(args.a, sample=True, seed=args.seed)
            first = run_pass(controller, chosen, base, args.threads)
            second = run_pass(controller, [s.swapped() for s in chosen], base, args.threads)
            out[f"{kind}/{arm}"] = summarise(first, second)
    text = json.dumps(out, indent=1)
    if args.out:
        args.out.write_text(text + "\n")
    for key, s in out.items():
        if isinstance(s, dict):
            head = s.get("target_hit") or s.get("more_on_named")
            print(key, {k: v for k, v in head.items() if k in ("rate", "n", "ci95")},
                  "chose_named", s.get("chose_named"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
