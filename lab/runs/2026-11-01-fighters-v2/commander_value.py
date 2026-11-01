"""How much does the order channel matter today?

Same pilot on both sides, side b always under the scripted commander with orders
shown. Side a changes only its command:
  scripted  - control, should be about 0.5
  hidden    - the script commands logistics, pilots see no order
  random    - script logistics, random squads and orders

Prints a's win rate per mission as JSON lines.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np

import rlf_sim
from spacefight.env.rosters import Roster
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval import missions as M
from spacefight.eval.controllers import make_controller

B3 = "lab/runs/2026-11-01-order-pilot-b3"
PILOTS = {
    "reward_300": f"{B3}/reward/checkpoints/ppo_bc_300.pt",
    "transit_300": f"{B3}/transit/checkpoints/ppo_bc_300.pt",
    "script": "script",
}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 258
THREADS = int(sys.argv[2]) if len(sys.argv) > 2 else 8


def builder(a_mode: str, hide_a: bool):
    """A build_mission_env whose side a alone gets ``a_mode`` and hidden orders."""

    def build(mission, n, seed, commanders, n_threads, reaction_ticks=2,
              assets_dir=M.ASSETS, hide_a_unused=False):
        rosters = M.default_rosters(mission)
        block = 2 * len(rosters)
        if n % block:
            raise ValueError(f"n must be a multiple of {block}")
        idx = np.arange(n, dtype=np.int64)
        entry = idx % len(rosters)
        a_team = (idx // len(rosters)) % 2
        first = rosters[0][1]
        time_limit_s = float(rlf_sim.mission_time_limit_s(mission))
        env = RustVecEnv(
            assets_dir, n, first.fleets(), seed, time_limit_s=time_limit_s,
            n_threads=n_threads, record_events=True, reaction_ticks=reaction_ticks,
            max_ships=max(r.n_ships for _, r in rosters),
            commanders=("scripted", "scripted"),
        )
        for i, k in enumerate(entry):
            roster = rosters[int(k)][1]
            t = int(a_team[i])
            modes = (a_mode, "scripted") if t == 0 else ("scripted", a_mode)
            hide = (hide_a and t == 0, hide_a and t == 1)
            env.set_next_roster(i, Roster(roster.teams, mission, modes), hide_orders=hide)
        env.reset()
        capital = np.isin(env.hull_id, M.capital_hull_ids(assets_dir))
        return M.MissionEnv(env=env, names=[n_ for n_, _ in rosters], entry=entry,
                            a_team=a_team, capital=capital, time_limit_s=time_limit_s)

    return build


ARMS = [("scripted", "scripted", False), ("hidden", "scripted", True), ("random", "random", False)]
for pilot, spec in PILOTS.items():
    for arm, mode, hide in ARMS:
        if spec == "script" and hide:
            continue  # scripts read the command state directly, not the obs
        for mission in M.DEFAULT_MISSIONS:
            M.build_mission_env = builder(mode, hide)
            t0 = time.time()
            a = make_controller(spec, sample=True, seed=0)
            b = make_controller(spec, sample=True, seed=1)
            cfg = M.MissionEvalConfig(missions=(mission,), n_per_mission=N)
            a.reset(cfg.seed)
            b.reset(cfg.seed + 1)
            s = M.run_mission(a, b, mission, cfg, THREADS)
            print(json.dumps({
                "pilot": pilot, "a_command": arm, "mission": mission, "n": s.n,
                "a_win": round(s.win_rate, 3),
                "a_win_team0": round(s.win_rate_team0, 3),
                "a_win_team1": round(s.win_rate_team1, 3),
                "len_s": round(s.length_median_s, 1),
                "tl": round(s.time_limit_rate, 3),
                "secs": round(time.time() - t0),
            }), flush=True)
