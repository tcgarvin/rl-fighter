"""Bomber paired swap (SIM_VERSION 9): the same rosters and seeds twice, once as they
are and once with side X's first gunship swapped for a bomber.

Deathmatch: 3 v 3 rosters, side X has at least one gunship (``X_SIDES`` against
``Y_SIDES``, every pair, side X on either team). Carrier battle: the sim's default
carrier rosters (scripted commanders), side X's first gunship swapped. Every strike
craft is flown by the script, or by live pilots drawn per slot per match with the same
draws in both arms (``--pilots``); capital ships by the sim's scripts. Env ``i`` plays
the same roster, side and match seed in both arms, so the rows pair.

Reports (JSON ``rlf.lab.swap/1``): side X's score (wins + half draws) in each arm, the
paired delta with its 95% interval, end reasons, and the swapped slot's damage dealt
to capital ships and to strike craft in each arm.

    uv run python lab/runs/2026-11-19-station-bomber/swap_eval.py --mission deathmatch \
        --n-per-roster 16 --out out/swap_dm_script.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from spacefight.env.rosters import (  # noqa: E402
    CARRIER_BATTLE,
    DEATHMATCH,
    SCRIPTED,
    Roster,
    capital_hull_ids,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402
from station_eval import PilotPool  # noqa: E402

SCHEMA = "rlf.lab.swap/1"
TICK_HZ = 30
END_REASONS = tuple(rlf_sim.END_REASONS)
X_SIDES = (
    ("gunship", "fighter", "fighter"),
    ("gunship", "fighter", "strafer"),
    ("gunship", "strafer", "strafer"),
    ("gunship", "gunship", "fighter"),
)
Y_SIDES = (
    ("fighter", "fighter", "fighter"),
    ("fighter", "strafer", "gunship"),
    ("strafer", "strafer", "fighter"),
    ("gunship", "fighter", "fighter"),
)


def swapped(team: tuple[str, ...]) -> tuple[str, ...]:
    i = team.index("gunship")
    return (*team[:i], "bomber", *team[i + 1 :])


def roster_pairs(mission: str) -> list[tuple[str, tuple[str, ...], tuple[str, ...]]]:
    """``(name, side X, side Y)`` per roster."""
    if mission == DEATHMATCH:
        return [
            (f"{''.join(h[0].upper() for h in x)} v {''.join(h[0].upper() for h in y)}",
             x, y)
            for x in X_SIDES for y in Y_SIDES
        ]
    out = []
    for r in rlf_sim.mission_rosters(mission):
        out.append((str(r["name"]), tuple(r["fleets"][0]), tuple(r["fleets"][1])))
    return out


def run_arm(args: argparse.Namespace, swap: bool) -> dict[str, Any]:
    pairs = roster_pairs(args.mission)
    n = len(pairs) * 2 * args.n_per_roster
    idx = np.arange(n)
    entry = idx % len(pairs)
    x_team = (idx // len(pairs)) % 2
    rosters = []
    for i in range(n):
        _, x, y = pairs[entry[i]]
        x = swapped(x) if swap else x
        teams = (x, y) if x_team[i] == 0 else (y, x)
        rosters.append(Roster(teams, args.mission, (SCRIPTED, SCRIPTED)))
    time_limit = float(rlf_sim.mission_time_limit_s(args.mission))
    env = RustVecEnv(
        REPO / "assets", n, rosters[0].fleets(), args.seed, time_limit_s=time_limit,
        n_threads=args.threads, reaction_ticks=2,
        max_ships=max(r.n_ships for r in rosters), commanders=(SCRIPTED, SCRIPTED),
    )
    for i, r in enumerate(rosters):
        env.set_next_roster(i, r, time_limit_s=time_limit)
    env.reset()
    capital = np.isin(env.hull_id, capital_hull_ids(REPO / "assets"))
    team = env.team.copy()
    # The swapped slot: side X's first gunship (base) or its bomber (swap).
    slot = np.full(n, -1)
    for i, r in enumerate(rosters):
        xt = int(x_team[i])
        names = r.teams[xt]
        k = names.index("bomber" if swap else "gunship")
        slot[i] = k + (0 if xt == 0 else len(r.teams[0]))
    pool = PilotPool(args.pilots, args.seed, args.checkpoint_root) if args.pilots else None
    if pool is not None:
        pool.draw(team.shape)
    rows = ~capital & (team >= 0)
    running = np.ones(n, dtype=bool)
    winner = np.full(n, -2)
    reason = np.zeros(n, dtype=np.int64)
    length = np.zeros(n)
    to_cap = np.zeros(n)
    to_strike = np.zeros(n)
    for step in range(1, int(time_limit * TICK_HZ) + 3):
        actions = env.scripted_actions().copy()
        if pool is not None:
            pool.act(env, rows & running[:, None], actions)
        _, _, dones, info = env.step(actions)
        for i in np.flatnonzero(running & (info.hit_count > 0)):
            for row in info.hits[i, : info.hit_count[i]]:
                if int(row[0]) != slot[i]:
                    continue
                dmg = row[3] / 1000.0
                if capital[i, int(row[1])]:
                    to_cap[i] += dmg
                else:
                    to_strike[i] += dmg
        ending = running & dones
        winner[ending] = info.winner[ending]
        reason[ending] = env.end_reason[ending]
        length[ending] = step / TICK_HZ
        running &= ~dones
        if not running.any():
            break
    if running.any():
        raise RuntimeError("matches did not end")
    score = (winner == x_team) + 0.5 * (winner == -1)
    return {
        "score": score,
        "reason": reason,
        "length": length,
        "to_cap": to_cap,
        "to_strike": to_strike,
        "names": [p[0] for p in pairs],
        "entry": entry,
    }


def summary(arm: dict[str, Any]) -> dict[str, Any]:
    s = arm["score"]
    return {
        "x_score": float(s.mean()),
        "x_score_ci95": float(1.96 * s.std(ddof=1) / np.sqrt(s.size)),
        "end_reasons": {END_REASONS[c]: float(np.mean(arm["reason"] == c))
                        for c in range(1, len(END_REASONS)) if (arm["reason"] == c).any()},
        "length_median_s": float(np.median(arm["length"])),
        "slot_damage_to_capital": float(arm["to_cap"].mean()),
        "slot_damage_to_strike": float(arm["to_strike"].mean()),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--mission", choices=(DEATHMATCH, CARRIER_BATTLE), default=DEATHMATCH)
    p.add_argument("--n-per-roster", type=int, default=16)
    p.add_argument("--seed", type=int, default=910_000)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--pilots", type=Path)
    p.add_argument("--checkpoint-root", type=Path, default=Path("/home/timg/code/rl-fighter"))
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    torch.set_num_threads(max(1, args.threads))
    base = run_arm(args, swap=False)
    swap = run_arm(args, swap=True)
    d = swap["score"] - base["score"]
    out = {
        "schema": SCHEMA,
        "sim_version": int(rlf_sim.SIM_VERSION),
        "mission": args.mission,
        "n": int(d.size),
        "seed": args.seed,
        "pilots": str(args.pilots) if args.pilots else "script",
        "base": summary(base),
        "swap": summary(swap),
        "delta": float(d.mean()),
        "delta_ci95": float(1.96 * d.std(ddof=1) / np.sqrt(d.size)),
        "delta_by_roster": {
            name: float(d[base["entry"] == k].mean()) for k, name in enumerate(base["names"])
        },
    }
    text = json.dumps(out, indent=1)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
