"""Commander against commander (docs/COMMANDER.md): matches as on the live page, every
strike craft flown by a pilot drawn from the live list, both sides drawn the same way.

    uv run python -m spacefight.commander.eval --a <commander.pt|scripted|random> \
        --b scripted --n-per-mission 192 --out eval.json

Each mission plays ``n_per_mission`` matches: its live rosters (deathmatch: drafts as on
the live page) in turn, ``a`` on each side half the time. Pilots are drawn with a fixed
seed, so two evals with the same seed fly the same pilots.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import torch

from spacefight.commander.io import CommanderInputs, check_sim_layout
from spacefight.commander.pilots import LIVE_PILOTS, PilotStable, live_pilot_checkpoints
from spacefight.commander.policy import CommanderActor, act, load_commander
from spacefight.commander.train import FEATURE_KEYS, LEARNED, MISSIONS
from spacefight.env.rosters import (
    DEATHMATCH,
    RANDOM,
    SCRIPTED,
    PilotsDistribution,
    Roster,
    make_sampler,
)
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval.missions import default_rosters

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = REPO_ROOT / "assets"
WINNER_DRAW = -1
WINNER_NONE = -2


@dataclass
class Commander:
    """A side's commander: a sim mode, and a network for the learned ones."""

    label: str
    mode: str
    actor: CommanderActor | None = None

    @classmethod
    def from_spec(cls, spec: str) -> Commander:
        """``scripted``, ``random`` or a commander checkpoint.

        Raises:
            FileNotFoundError: Neither keyword nor an existing file.
        """
        if spec in (SCRIPTED, RANDOM):
            return cls(spec, spec)
        path = Path(spec)
        if not path.is_file():
            raise FileNotFoundError(f"no commander {spec!r}")
        actor, _ = load_commander(path)
        return cls(f"{path.parent.parent.name}/{path.stem}", LEARNED, actor)


def mission_rosters(mission: str, n_drafts: int, seed: int) -> list[Roster]:
    if mission != DEATHMATCH:
        return [r for _, r in default_rosters(mission)]
    sampler = make_sampler(PilotsDistribution(mission_weights=(1.0, 0.0, 0.0)), seed)
    return [sampler.sample() for _ in range(n_drafts)]


def play_mission(
    a: Commander,
    b: Commander,
    mission: str,
    n: int,
    seed: int,
    n_threads: int,
    pilots: list[tuple[str, Path]],
) -> dict[str, Any]:
    """Play ``n`` matches of ``mission``; ``a``'s score and how they ended."""
    rosters = mission_rosters(mission, 24, seed)
    block = 2 * len(rosters)
    if n % block:
        raise ValueError(f"n must be a multiple of {block} for {mission}, got {n}")
    index = np.arange(n)
    entry = index % len(rosters)
    a_team = (index // len(rosters)) % 2
    time_limit = float(rlf_sim.mission_time_limit_s(mission))
    env = RustVecEnv(
        ASSETS,
        n,
        rosters[0].fleets(),
        seed,
        n_threads=n_threads,
        reaction_ticks=2,
        max_ships=20,
        commanders=(SCRIPTED, SCRIPTED),
    )
    for i in range(n):
        modes = [b.mode, b.mode]
        modes[a_team[i]] = a.mode
        r = rosters[entry[i]]
        env.set_next_roster(
            i,
            Roster(r.teams, mission, (modes[0], modes[1])),
            time_limit_s=time_limit,
            hide_orders=(False, False),
        )
    env.reset()
    stable = PilotStable(pilots, n, env.n_ships, seed + 1, ASSETS)
    stable.draw(env, range(n))
    torch.manual_seed(seed)
    running = np.ones(n, dtype=bool)
    winner = np.full(n, WINNER_NONE, dtype=np.int64)
    end_reason = np.zeros(n, dtype=np.int64)
    max_steps = int(time_limit * 30) + 4
    for _ in range(max_steps):
        for team in (0, 1):
            due = np.asarray(env.raw.commander_due(team), dtype=bool) & running
            if not due.any():
                continue
            feats = None
            for cmd, is_a in ((a, True), (b, False)):
                if cmd.actor is None:
                    continue
                rows = np.flatnonzero(due & ((a_team == team) == is_a))
                if rows.size == 0:
                    continue
                if feats is None:
                    feats = env.raw.commander_features(team)
                x = CommanderInputs.from_numpy(
                    {k: np.asarray(feats[k])[rows] for k in FEATURE_KEYS}
                )
                actions, _ = act(cmd.actor, x)
                env.raw.submit_commander_actions(
                    team, rows.astype(np.int64), actions.numpy().astype(np.int32)
                )
        _, _, dones, info = env.step(stable.actions(env))
        ending = running & dones
        winner[ending] = np.asarray(info.winner)[ending]
        end_reason[ending] = env.end_reason[ending]
        running &= ~dones
        if not running.any():
            break
    else:
        raise RuntimeError(f"{mission}: {int(running.sum())} matches did not end")
    a_won = winner == a_team
    draws = winner == WINNER_DRAW
    score = (a_won + 0.5 * draws).astype(float)
    by_side = {
        f"a_on_team{t}": float(score[a_team == t].mean()) for t in (0, 1)
    }
    return {
        "n": n,
        "score_a": float(score.mean()),
        "draw_rate": float(draws.mean()),
        **by_side,
        "end_reasons": {
            str(int(k)): int(v) for k, v in zip(*np.unique(end_reason, return_counts=True))
        },
    }


def evaluate(
    a: str,
    b: str,
    n_per_mission: int,
    seed: int = 20261107,
    n_threads: int = 8,
    live_pilots: Path = LIVE_PILOTS,
    missions: Sequence[str] = MISSIONS,
) -> dict[str, Any]:
    check_sim_layout(rlf_sim.commander_io())
    ca, cb = Commander.from_spec(a), Commander.from_spec(b)
    pilots = live_pilot_checkpoints(live_pilots)
    out: dict[str, Any] = {
        "schema": "rlf.eval.commander/1",
        "a": ca.label,
        "b": cb.label,
        "seed": seed,
        "pilots": [p for p, _ in pilots],
        "missions": {},
    }
    for k, mission in enumerate(missions):
        t0 = time.time()
        res = play_mission(ca, cb, mission, n_per_mission, seed + 1000 * k, n_threads, pilots)
        res["secs"] = round(time.time() - t0, 1)
        out["missions"][mission] = res
        print(f"{mission}: a scores {res['score_a']:.3f} over {res['n']}", flush=True)
    scores = [m["score_a"] for m in out["missions"].values()]
    out["score_a"] = float(np.mean(scores))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--a", required=True)
    p.add_argument("--b", default=SCRIPTED)
    p.add_argument("--n-per-mission", type=int, default=192)
    p.add_argument("--seed", type=int, default=20261107)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    torch.set_num_threads(args.threads)
    res = evaluate(args.a, args.b, args.n_per_mission, args.seed, args.threads)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res, indent=1) + "\n")
    print(f"a {res['a']} v b {res['b']}: {res['score_a']:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
