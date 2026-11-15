"""Print every commander eval under a directory, one block per pilot list.

    .venv/bin/python lab/runs/2026-11-15-commander-3/summary.py <eval dir>

The directory holds one folder per pilot list, each with ``rlf.eval.commander/1`` files.
A score is side a's share of wins (a draw is half), with its standard error.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def orders(o: dict[str, Any]) -> str:
    if not o["orders_ended"]:
        return "no orders ended"
    return (
        f"{o['orders_per_ship_min']:.1f}/ship-min, median "
        f"{o['order_seconds_median']:.1f} s, {o['orders_under_5s']:.0%} under 5 s, "
        f"ordered {o['ordered_share']:.0%}"
    )


def main(root: Path) -> int:
    pools = sorted(p for p in root.iterdir() if p.is_dir())
    if not pools:
        raise SystemExit(f"no pilot-list folders under {root}")
    for pool in pools:
        print(f"pilots: {pool.name}")
        for f in sorted(pool.glob("*.json")):
            d = json.loads(f.read_text())
            n = sum(m["n"] for m in d["missions"].values())
            se = math.sqrt(d["score_a"] * (1.0 - d["score_a"]) / n)
            per = " ".join(
                f"{k[:7]} {v['score_a']:.2f}" for k, v in d["missions"].items()
            )
            print(
                f"{d['a']:>30} v {d['b']:<30} {d['score_a']:.3f} +-{se:.3f} "
                f"over {n}  ({per})"
            )
            print(f"{'':>30}   a orders: {orders(d['orders_a'])}")
            print(f"{'':>30}   b orders: {orders(d['orders_b'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
