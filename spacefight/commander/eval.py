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
from numpy.typing import NDArray

from spacefight.commander.decide import decide_learned
from spacefight.commander.io import check_sim_layout
from spacefight.commander.pilots import LIVE_PILOTS, PilotStable, live_pilot_checkpoints
from spacefight.commander.policy import CommanderActor, load_commander
from spacefight.commander.train import LEARNED, MISSIONS
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


def named_mission_rosters(
    mission: str, n_drafts: int, seed: int
) -> list[tuple[str, Roster]]:
    """``(name, roster)`` of a mission's live rosters; deathmatch: ``n_drafts`` drafts
    as on the live page, named ``draft <k>``."""
    if mission != DEATHMATCH:
        return default_rosters(mission)
    sampler = make_sampler(PilotsDistribution(mission_weights=(1.0, 0.0, 0.0)), seed)
    return [(f"draft {k}", sampler.sample()) for k in range(n_drafts)]


def mission_rosters(mission: str, n_drafts: int, seed: int) -> list[Roster]:
    """A mission's live rosters (deathmatch: ``n_drafts`` drafts as on the live page)."""
    return [r for _, r in named_mission_rosters(mission, n_drafts, seed)]


@dataclass(frozen=True)
class MatchesPlayed:
    """What ``play_matches`` saw, one row per match.

    Attributes:
        winner: [n] the winning team, or ``WINNER_DRAW``.
        end_reason: [n] the sim's end reason.
        assign: [n, S] the stable's pilot index per slot at the start (``script`` for
            capital ships, padding and strike craft the script was drawn to fly).
        script: The index ``assign`` uses for the script.
        strike: [n, S] strike craft, the slots pilots were drawn for.
        team: [n, S] each slot's team, -1 for padding.
        hull_id: [n, S] each slot's hull, -1 for padding.
    """

    winner: NDArray[np.int64]
    end_reason: NDArray[np.int64]
    assign: NDArray[np.int64]
    script: int
    strike: NDArray[np.bool_]
    team: NDArray[np.int8]
    hull_id: NDArray[np.int16]


def play_matches(
    rosters: Sequence[Roster],
    mission: str,
    commanders: Sequence[Commander],
    side_commander: NDArray[np.int64],
    seed: int,
    n_threads: int,
    pilots: Sequence[tuple[str, Path]],
    include_script: bool = False,
) -> MatchesPlayed:
    """Play one match of ``mission`` per roster, as on the live page.

    Every strike craft is flown by a pilot drawn ship by ship from ``pilots`` (and the
    script, with ``include_script``); capital ships fly the sim's scripts. Orders are
    shown to both sides.

    Args:
        rosters: Match ``i``'s teams; its commanders are set from ``side_commander``.
        mission: The mission every match plays.
        commanders: The commanders the matches draw on.
        side_commander: [n, 2] index into ``commanders`` of each match's team 0 and
            team 1 commander.
        seed: Env seed; the pilot draw uses ``seed + 1`` and torch ``seed``.
        n_threads: Sim threads.
        pilots: The neural pilots.
        include_script: Put the script pilot in the draw.

    Raises:
        ValueError: ``side_commander`` does not fit ``rosters`` and ``commanders``.
        RuntimeError: A match did not end within its clock.
    """
    n = len(rosters)
    side_commander = np.asarray(side_commander, dtype=np.int64)
    if side_commander.shape != (n, 2):
        raise ValueError(f"side_commander must be [{n}, 2], got {side_commander.shape}")
    if n == 0 or side_commander.min() < 0 or side_commander.max() >= len(commanders):
        raise ValueError(f"{n} matches, commander indices outside 0..{len(commanders)}")
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
    for i, r in enumerate(rosters):
        modes = (
            commanders[side_commander[i, 0]].mode,
            commanders[side_commander[i, 1]].mode,
        )
        env.set_next_roster(
            i,
            Roster(r.teams, mission, modes),
            time_limit_s=time_limit,
            hide_orders=(False, False),
        )
    env.reset()
    stable = PilotStable(
        pilots, n, env.n_ships, seed + 1, ASSETS, include_script=include_script
    )
    stable.draw(env, range(n))
    # The env moves on to a new match when one ends, so the start is kept now.
    assign = stable.assign.copy()
    strike = stable.strike_mask(env).copy()
    team = np.asarray(env.team).copy()
    hull_id = np.asarray(env.hull_id).copy()
    learned = [(k, c.actor) for k, c in enumerate(commanders) if c.actor is not None]
    torch.manual_seed(seed)
    running = np.ones(n, dtype=bool)
    winner = np.full(n, WINNER_NONE, dtype=np.int64)
    end_reason = np.zeros(n, dtype=np.int64)
    max_steps = int(time_limit * 30) + 4
    for _ in range(max_steps):
        decide_learned(env, side_commander, learned, running)
        _, _, dones, info = env.step(stable.actions(env))
        ending = running & dones
        winner[ending] = np.asarray(info.winner)[ending]
        end_reason[ending] = env.end_reason[ending]
        running &= ~dones
        if not running.any():
            break
    else:
        raise RuntimeError(f"{mission}: {int(running.sum())} matches did not end")
    return MatchesPlayed(
        winner, end_reason, assign, stable.script, strike, team, hull_id
    )


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
    # Commander 0 is a, 1 is b: a on its team, b on the other.
    side = np.stack([a_team != 0, a_team != 1], axis=1).astype(np.int64)
    played = play_matches(
        [rosters[e] for e in entry], mission, (a, b), side, seed, n_threads, pilots
    )
    winner = played.winner
    a_won = winner == a_team
    draws = winner == WINNER_DRAW
    score = (a_won + 0.5 * draws).astype(float)
    by_side = {f"a_on_team{t}": float(score[a_team == t].mean()) for t in (0, 1)}
    return {
        "n": n,
        "score_a": float(score.mean()),
        "draw_rate": float(draws.mean()),
        **by_side,
        "end_reasons": {
            str(int(k)): int(v)
            for k, v in zip(*np.unique(played.end_reason, return_counts=True))
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
        res = play_mission(
            ca, cb, mission, n_per_mission, seed + 1000 * k, n_threads, pilots
        )
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
