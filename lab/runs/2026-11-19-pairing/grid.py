"""One cell of the pairing grid: side a (a commander, and a pilot flying all its strike
craft, or the per-ship draw) against side b, over one mission. Run from the repo root:

    PYTHONPATH=. .venv/bin/python lab/runs/2026-11-19-pairing/grid.py \\
        --mission deathmatch --a <commander> --pilot-a <id|draw> \\
        [--b scripted --pilot-b draw] --n 96 --out <cell.json> [--threads 4] \\
        [--checkpoint-root <checkout>]

The matches are the commander eval's (``spacefight.commander.eval.play_matches``): the
mission's live rosters in turn, a on each side half the time, the pilot draw per ship.
Every cell of a mission uses the same seed, so the rosters, sides and b's per-ship pilots
are the same match by match in every cell (b's draw is made as if a were not pinned),
and cells pair. The cell JSON keeps every match: a's score (a draw is half), a's team,
the roster, and the ships each pilot flew per side, for the WAR prediction.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import rlf_sim
import torch

from spacefight.commander.eval import (
    DRAWN,
    REPO_ROOT,
    WINNER_DRAW,
    Commander,
    named_mission_rosters,
    play_matches,
)
from spacefight.commander.io import check_sim_layout
from spacefight.commander.pilots import (
    LIVE_PILOTS,
    PILOT_DRAW_SHIP,
    UNPINNED,
    live_pilot_checkpoints,
)

SCHEMA = "rlf.pairing.cell/1"
DEATHMATCH_DRAFTS = 24
MISSION_SEEDS = {"deathmatch": 0, "carrier_battle": 1000, "convoy_escort": 2000}


def run_cell(
    mission: str,
    a: str,
    pilot_a: str,
    b: str,
    pilot_b: str,
    n: int,
    seed: int,
    threads: int,
    root: Path,
) -> dict[str, object]:
    """Play one cell; the JSON-ready record (``SCHEMA``)."""
    check_sim_layout(rlf_sim.commander_io())
    pilots = live_pilot_checkpoints(LIVE_PILOTS, root)
    ids = [p for p, _ in pilots]

    def pin(pilot: str) -> int:
        if pilot == DRAWN:
            return UNPINNED
        return ids.index(pilot)

    mission_seed = seed + MISSION_SEEDS[mission]
    named = named_mission_rosters(mission, DEATHMATCH_DRAFTS, mission_seed)
    block = 2 * len(named)
    if n % block:
        raise ValueError(f"n must be a multiple of {block} for {mission}, got {n}")
    index = np.arange(n)
    entry = index % len(named)
    a_team = (index // len(named)) % 2
    side = np.stack([a_team != 0, a_team != 1], axis=1).astype(np.int64)
    pin_a, pin_b = pin(pilot_a), pin(pilot_b)
    pinned = None
    if pin_a != UNPINNED or pin_b != UNPINNED:
        pinned = np.where(
            np.stack([a_team == 0, a_team == 1], axis=1), pin_a, pin_b
        ).astype(np.int64)
    commanders = (Commander.from_spec(a), Commander.from_spec(b))
    t0 = time.time()
    played = play_matches(
        [named[e][1] for e in entry],
        mission,
        commanders,
        side,
        mission_seed,
        threads,
        pilots,
        pilot_draw=PILOT_DRAW_SHIP,
        pinned_pilots=pinned,
    )
    secs = time.time() - t0
    score = (played.winner == a_team) + 0.5 * (played.winner == WINNER_DRAW)
    # [n, 2 (a, b), pilots + script]: strike craft each pilot flew for each side.
    counts = np.zeros((n, 2, len(ids) + 1), dtype=np.int64)
    for i in range(n):
        for s, team in enumerate((a_team[i], 1 - a_team[i])):
            mine = played.strike[i] & (played.team[i] == team)
            counts[i, s] = np.bincount(played.assign[i][mine], minlength=len(ids) + 1)
    return {
        "schema": SCHEMA,
        "sim_version": int(rlf_sim.SIM_VERSION),
        "mission": mission,
        "a": commanders[0].label,
        "a_spec": a,
        "pilot_a": pilot_a,
        "b": commanders[1].label,
        "b_spec": b,
        "pilot_b": pilot_b,
        "pilots": ids,
        "n": n,
        "seed": mission_seed,
        "secs": round(secs, 1),
        "score_a": float(score.mean()),
        "score": score.tolist(),
        "a_team": a_team.tolist(),
        "roster": [named[e][0] for e in entry],
        "counts": counts.tolist(),
        "end_reason": played.end_reason.tolist(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--mission", required=True, choices=sorted(MISSION_SEEDS))
    p.add_argument("--a", required=True)
    p.add_argument("--pilot-a", default=DRAWN)
    p.add_argument("--b", default="scripted")
    p.add_argument("--pilot-b", default=DRAWN)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--seed", type=int, default=20261119)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--checkpoint-root", type=Path, default=REPO_ROOT)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    torch.set_num_threads(args.threads)
    cell = run_cell(
        args.mission,
        args.a,
        args.pilot_a,
        args.b,
        args.pilot_b,
        args.n,
        args.seed,
        args.threads,
        args.checkpoint_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_suffix(".tmp")
    tmp.write_text(json.dumps(cell) + "\n")
    tmp.replace(args.out)
    print(
        f"{args.mission} {cell['a']}+{args.pilot_a} v {cell['b']}+{args.pilot_b}: "
        f"{cell['score_a']:.3f} over {args.n} in {cell['secs']} s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
