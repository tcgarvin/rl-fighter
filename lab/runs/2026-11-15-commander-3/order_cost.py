"""Where the scripted commander's orders cost its side, against the same pilots with no
orders (the eval's ``unseen`` side). Run from the repo root:

    PYTHONPATH=. .venv/bin/python lab/runs/2026-11-15-commander-3/order_cost.py \
        <pilots.json> [blocks] [threads] [missions,comma,separated]

Per mission: the scripted side's score (a draw is half), each side's ship-time by order
kind (the unseen side's orders are the ones its pilots did not see), strike craft lost by
side in each 30-second window, and the scripted side's share of both sides' value over
time. Deathmatch also splits the score by fleet size. ``DUELS=k`` flies even k v k
deathmatches of one hull instead of the live drafts: at k=1 an attack order can only name
the one enemy there is. ``blocks`` repeats every roster on each side that many times.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import rlf_sim
import torch

from spacefight.commander.eval import (
    ASSETS,
    TICK_HZ,
    UNSEEN,
    Commander,
    mission_rosters,
)
from spacefight.commander.pilots import PilotStable, live_pilot_checkpoints
from spacefight.commander.train import MISSIONS
from spacefight.env.rosters import SCRIPTED, Roster
from spacefight.env.rust_env import RustVecEnv

KINDS = ("none", "attack", "defend", "goto")
WINDOW_S = 30


def run(mission: str, pilots, blocks: int, threads: int, seed: int) -> None:
    rosters = mission_rosters(mission, 24, seed)
    if os.environ.get("DUELS") and mission == "deathmatch":
        # One ship a side: the attack order names the only enemy there is.
        k = int(os.environ["DUELS"])
        hulls = ("fighter", "strafer", "gunship")
        rosters = [Roster.of([h] * k, [h] * k) for h in hulls for _ in range(8)]
    n = 2 * len(rosters) * blocks
    index = np.arange(n)
    entry = index % len(rosters)
    scripted_team = (index // len(rosters)) % 2  # the team the scripted commander has
    sides = (Commander.from_spec(UNSEEN), Commander.from_spec(SCRIPTED))
    time_limit = float(rlf_sim.mission_time_limit_s(mission))
    env = RustVecEnv(
        ASSETS,
        n,
        rosters[0].fleets(),
        seed,
        n_threads=threads,
        reaction_ticks=2,
        max_ships=20,
        commanders=(SCRIPTED, SCRIPTED),
    )
    for i in range(n):
        hide = (scripted_team[i] != 0, scripted_team[i] != 1)  # the unseen team hidden
        env.set_next_roster(
            i,
            Roster(rosters[entry[i]].teams, mission, (SCRIPTED, SCRIPTED)),
            time_limit_s=time_limit,
            hide_orders=(bool(hide[0]), bool(hide[1])),
        )
    env.reset()
    stable = PilotStable(pilots, n, env.n_ships, seed + 1, ASSETS)
    stable.draw(env, range(n))
    strike = stable.strike_mask(env).copy()
    team = np.asarray(env.team).copy()
    on_scripted = team == scripted_team[:, None]  # [N, S] slot is on the scripted side
    torch.manual_seed(seed)
    running = np.ones(n, dtype=bool)
    winner = np.full(n, -2, dtype=np.int64)
    max_steps = int(time_limit * TICK_HZ) + 4
    n_windows = int(time_limit // WINDOW_S) + 1
    kind_s = np.zeros((2, 4))  # [side: unseen, scripted][kind] flying ship-seconds
    lost = np.zeros((2, n_windows))
    value_share = np.zeros(n_windows)
    value_n = np.zeros(n_windows)
    alive_prev = np.asarray(env.raw.alive).copy()
    for step in range(max_steps):
        _, _, dones, info = env.step(stable.actions(env))
        ending = running & dones
        winner[ending] = np.asarray(info.winner)[ending]
        running &= ~dones
        if not running.any():
            break
        w = min(step // (WINDOW_S * TICK_HZ), n_windows - 1)
        alive = np.asarray(env.raw.alive)
        kind = np.asarray(env.order_tracks()["standing_kind"])
        live = running[:, None] & strike & alive
        flying = live & np.asarray(env.act_mask)
        died = running[:, None] & strike & alive_prev & ~alive
        for side, mask in enumerate((~on_scripted, on_scripted)):
            for k in range(4):
                kind_s[side, k] += float((flying & mask & (kind == k)).sum()) / TICK_HZ
            lost[side, w] += float((died & mask).sum())
        alive_prev = alive.copy()
        if step % TICK_HZ == 0:
            values = np.asarray(env.team_values())
            rows = np.flatnonzero(running)
            own = values[rows, scripted_team[rows]]
            total = values[rows].sum(axis=1)
            value_share[w] += float((own / np.maximum(total, 1e-6)).sum())
            value_n[w] += rows.size
    score = (winner == scripted_team) + 0.5 * (winner == -1)
    print(f"\n== {mission}: {n} matches, scripted side scored {score.mean():.3f}")
    for side, name in enumerate(("no orders (script's orders, unseen)", "scripted")):
        share = kind_s[side] / kind_s[side].sum()
        row = "  ".join(f"{k} {s:.2f}" for k, s in zip(KINDS, share))
        print(f"  {name:36s} ship-time by order: {row}")
    print(
        "  window (s)        "
        + " ".join(f"{w * WINDOW_S:5d}" for w in range(n_windows))
    )
    for side, name in enumerate(("lost, no orders  ", "lost, scripted   ")):
        print(f"  {name} " + " ".join(f"{x / n:5.2f}" for x in lost[side]))
    if mission == "deathmatch":
        # By fleet size: with one enemy an attack order names the only target there is.
        sizes = np.array([[len(t) for t in rosters[e].teams] for e in entry])
        own = sizes[index, scripted_team]
        foe = sizes[index, 1 - scripted_team]
        for a, b in sorted({(int(x), int(y)) for x, y in zip(own, foe)}):
            m = (own == a) & (foe == b)
            draws = int((winner[m] == -1).sum())
            print(
                f"  scripted {a} v {b} no orders: scripted scored {score[m].mean():.3f} "
                f"over {int(m.sum())} ({draws} draws)"
            )
    share = value_share / np.maximum(value_n, 1)
    print("  scripted value sh " + " ".join(f"{x:5.2f}" for x in share))
    print("  matches running   " + " ".join(f"{x / WINDOW_S:5.0f}" for x in value_n))


def main() -> int:
    pilots = live_pilot_checkpoints(Path(sys.argv[1]))
    blocks = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    torch.set_num_threads(threads)
    only = sys.argv[4].split(",") if len(sys.argv) > 4 else list(MISSIONS)
    for k, mission in enumerate(MISSIONS):
        if mission in only:
            run(mission, pilots, blocks, threads, 20261107 + 1000 * k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
