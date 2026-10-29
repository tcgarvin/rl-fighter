"""How does a duel pilot fly fighters inside fleets? (fleet pilot v1 plan §3.)

Runs the fleet eval with team ``a`` = the script on every hull except the fighter,
which the given checkpoint flies, against the all-script team, and prints the
per-hull table. Compare ``a``'s fighter row with the script's own fighter row.

    PYTHONPATH=. .venv/bin/python tools/champion_in_fleets.py CKPT --out out.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spacefight.env.rosters import hull_names_by_id  # noqa: E402
from spacefight.eval import fleet  # noqa: E402
from spacefight.eval.controllers import PerHull, Policy, Scripted  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("checkpoint", type=Path)
    p.add_argument("--n-per-roster", type=int, default=32)
    p.add_argument("--n-threads", type=int, default=8)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    names = dict(enumerate(hull_names_by_id()))
    fighter = next(h for h, n in names.items() if n == "fighter")
    mixed = PerHull(Scripted(), {fighter: Policy(args.checkpoint)}, names)
    cfg = fleet.FleetEvalConfig(n_per_roster=args.n_per_roster)
    result = fleet.evaluate(mixed, Scripted(), cfg, n_threads=args.n_threads)
    print(result.markdown())
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
