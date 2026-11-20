"""Dock and repair (SIM_VERSION 11): what the dock rules do to a mission.

Plays ``--n`` matches of one mission (``--mission``: deathmatch, carrier_battle,
convoy_escort, station_assault, citadel; each env plays the mission's sim rosters in
turn, a deathmatch two fixed drafts), every strike craft flown by one controller (the
script, or a live pilot list ``rlf.live_pilots/1`` drawn per strike slot per match),
the capital ships by the sim's scripts, both commanders scripted, the dock rules on or
off (``--docking``). Each env is read until its first ``done``.

Reports (JSON, ``rlf.lab.dock/1``): team 1's win rate (the attacker of a convoy or a
station; in a carrier battle the side that jumps in from +x) and its 95% interval, end
reasons, match length, and the dock statistics: recalls ordered (the scripted
commander's ``dock_ordered`` events), docks, the completion rate, the time from recall to dock, the
failures (killed on the way, carrier lost, no bay left, the match ending first), the
relaunches and the hull restored a match (hull fraction at relaunch less at docking).
For recalls that neither docked nor died, how they failed (``failure_modes``): never
within 30 m of the dock point ("never close"), inside the capture radius but always too
fast ("too fast"), within 30 m more than once without docking ("circling"), else
within 30 m once ("overshoot").

    uv run python lab/runs/2026-11-20-dock-repair/dock_eval.py --mission carrier_battle \\
        --n 512 --out lab/runs/2026-11-20-dock-repair/out/script_carrier_on.json
    ... --pilots lab/live_pilots.json --checkpoint-root /home/timg/code/rl-fighter
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import torch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from spacefight.env.rosters import (  # noqa: E402
    CARRIER_BATTLE,
    CONVOY_ESCORT,
    DEATHMATCH,
    SCRIPTED,
    STATION_ASSAULT,
    Roster,
    capital_hull_ids,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402

SCHEMA = "rlf.lab.dock/1"
TICK_HZ = 30
END_REASONS = tuple(rlf_sim.END_REASONS)
EV = {k: int(v) for k, v in rlf_sim.EVENT_KINDS.items()}
CAPTURE = float(rlf_sim.DOCK["capture_radius"])
MAX_REL = float(rlf_sim.DOCK["max_rel_speed"])
NEAR = 30.0
INBOUND = rlf_sim.DOCK_PHASES.index("inbound")
DEATHMATCH_DRAFTS = (
    (("fighter", "strafer", "gunship"), ("gunship", "fighter", "strafer")),
    (("fighter", "fighter"), ("strafer", "gunship")),
)
MISSIONS = (DEATHMATCH, CARRIER_BATTLE, CONVOY_ESCORT, STATION_ASSAULT, "citadel")


def rosters(mission: str) -> list[tuple[Roster, str]]:
    """The rosters an env plays, each with its sim mission spec (JSON text)."""
    if mission == DEATHMATCH:
        return [(Roster((a, b), DEATHMATCH), DEATHMATCH) for a, b in DEATHMATCH_DRAFTS]
    kind = STATION_ASSAULT if mission == "citadel" else mission
    raw = rlf_sim.mission_rosters(kind)
    if mission == STATION_ASSAULT:
        raw = raw[:1]
    elif mission == "citadel":
        raw = [r for r in raw if r["name"] == "citadel"]
    if not raw:
        raise ValueError(f"the sim has no rosters for {mission!r}")
    spec = (
        json.dumps({"kind": STATION_ASSAULT, "as": "carrier"})
        if kind == STATION_ASSAULT
        else kind
    )
    return [
        (Roster((tuple(r["fleets"][0]), tuple(r["fleets"][1])), kind), spec)
        for r in raw
    ]


class PilotPool:
    """Learned pilots drawn per strike slot per match (``rlf.live_pilots/1``), as in
    ``lab/runs/2026-11-19-citadel-dreadnought/citadel_eval.py``. Checkpoints resolve
    against ``root`` (the checkout that holds ``lab/runs``: a worktree has no weights).
    """

    def __init__(self, path: Path, seed: int, root: Path) -> None:
        from spacefight.commander.pilots import live_pilot_checkpoints
        from spacefight.eval.controllers import Policy

        pairs = live_pilot_checkpoints(path, root)
        self.ids = [i for i, _ in pairs]
        self.policies = [Policy(p, sample=True) for _, p in pairs]
        self.rng = np.random.default_rng(seed)
        self.assign = np.zeros((0, 0), dtype=np.int64)
        torch.manual_seed(seed)

    def draw(self, shape: tuple[int, int]) -> None:
        self.assign = self.rng.integers(0, len(self.policies), size=shape)

    def act(self, env: RustVecEnv, rows: np.ndarray, out: np.ndarray) -> None:
        for k, pol in enumerate(self.policies):
            sel = rows & (self.assign == k)
            if sel.any():
                out[sel] = pol.act(env, sel)


@dataclass
class Recall:
    """One dock order, from the order to its end."""

    env: int
    ship: int
    pilot: str
    ordered: int
    outcome: str = "match ended"
    ended: int = 0
    min_dist: float = float("inf")
    rel_at_min: float = float("nan")
    inside_capture: bool = False
    min_rel_inside: float = float("inf")
    near_entries: int = 0
    was_near: bool = False
    start_dist: float = float("nan")
    dists: list[float] = field(default_factory=list)


def failure_mode(r: Recall) -> str:
    """How a recall that neither docked nor died failed (module docs)."""
    if r.min_dist > NEAR:
        return "never close"
    if r.inside_capture:
        return "too fast"
    if r.near_entries > 1:
        return "circling"
    return "overshoot"


def quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    a = np.asarray(values)
    return {
        "p25": float(np.percentile(a, 25)),
        "p50": float(np.median(a)),
        "p75": float(np.percentile(a, 75)),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--mission", required=True, choices=MISSIONS)
    p.add_argument("--n", type=int, default=512)
    p.add_argument("--seed", type=int, default=1_100_000)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--assets", type=Path, default=REPO / "assets")
    p.add_argument("--docking", choices=("on", "off"), default="on")
    p.add_argument("--pilots", type=Path, help="live pilot list; default: the script")
    p.add_argument(
        "--checkpoint-root",
        type=Path,
        default=Path("/home/timg/code/rl-fighter"),
        help="checkout holding the pilots' lab/runs checkpoints",
    )
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    torch.set_num_threads(max(1, args.threads))

    plays = rosters(args.mission)
    kind = plays[0][0].mission
    time_limit = float(rlf_sim.mission_time_limit_s(kind))
    max_ships = max(r.n_ships for r, _ in plays)
    docking = args.docking == "on"
    env = RustVecEnv(
        args.assets,
        args.n,
        plays[0][0].fleets(),
        args.seed,
        time_limit_s=time_limit,
        n_threads=args.threads,
        record_events=True,
        reaction_ticks=2,
        max_ships=max_ships,
        commanders=(SCRIPTED, SCRIPTED),
        docking=docking,
    )
    for i in range(args.n):
        roster, spec = plays[i % len(plays)]
        env.raw.set_next_roster(
            i,
            roster.fleets(),
            roster.arena_radius,
            mission=spec,
            commanders=[SCRIPTED, SCRIPTED],
            time_limit_s=time_limit,
            hide_orders=[False, False],
        )
    env.reset()
    capital = np.isin(env.hull_id, capital_hull_ids(args.assets))
    team = env.team.copy()
    strike = ~capital & (team >= 0)
    pool = (
        PilotPool(args.pilots, args.seed, args.checkpoint_root) if args.pilots else None
    )
    if pool is not None:
        pool.draw(team.shape)

    def pilot_of(i: int, s: int) -> str:
        return pool.ids[int(pool.assign[i, s])] if pool is not None else "script"

    n = args.n
    running = np.ones(n, dtype=bool)
    winner = np.full(n, -2, dtype=np.int64)
    reason = np.zeros(n, dtype=np.int64)
    length = np.zeros(n, dtype=np.int64)
    recalls: list[Recall] = []
    open_: dict[tuple[int, int], Recall] = {}
    docked_hp: dict[tuple[int, int], float] = {}
    relaunches = 0
    restored = 0.0
    repaired = 0
    max_steps = int(round(time_limit * TICK_HZ)) + 2
    for step in range(1, max_steps + 1):
        actions = env.scripted_actions().copy()
        if pool is not None:
            pool.act(env, strike & running[:, None], actions)
        _, _, dones, info = env.step(actions)
        for row in env.events():
            i, k = int(row[0]), int(row[1])
            if not running[i]:
                continue
            ship = int(row[2])
            key = (i, ship)
            if k == EV["dock_ordered"]:
                r = Recall(i, ship, pilot_of(i, ship), step)
                open_[key] = r
                recalls.append(r)
            elif k == EV["docked"]:
                docked_hp[key] = float(row[6])
                if key in open_:
                    r = open_.pop(key)
                    r.outcome, r.ended = "docked", step
            elif k == EV["relaunched"]:
                relaunches += 1
                restored += float(row[6]) - docked_hp.pop(key, float(row[6]))
            elif k == EV["repaired"]:
                repaired += 1
            elif k == EV["death"] and key in open_:
                r = open_.pop(key)
                r.outcome, r.ended = "killed en route", step
            elif k == EV["dock_aborted"] and key in open_:
                r = open_.pop(key)
                r.outcome = "carrier lost" if int(row[8]) == 0 else "no bay left"
                r.ended = step
        if open_:
            ds = env.dock_state()
            for (i, s), r in open_.items():
                if ds["phase"][i, s] != INBOUND:
                    continue
                d, v = float(ds["dist"][i, s]), float(ds["rel_speed"][i, s])
                if np.isnan(r.start_dist):
                    r.start_dist = d
                if d < r.min_dist:
                    r.min_dist, r.rel_at_min = d, v
                if d <= CAPTURE:
                    r.inside_capture = True
                    r.min_rel_inside = min(r.min_rel_inside, v)
                near = d <= NEAR
                if near and not r.was_near:
                    r.near_entries += 1
                r.was_near = near
        ending = running & dones
        for e in np.flatnonzero(ending).tolist():
            for key in [k for k in open_ if k[0] == e]:
                open_.pop(key).ended = step
        winner[ending] = info.winner[ending]
        reason[ending] = env.end_reason[ending]
        length[ending] = step
        running &= ~dones
        if not running.any():
            break
    if running.any():
        raise RuntimeError(f"{int(running.sum())} matches did not end")

    t1 = winner == 1
    score = t1 + 0.5 * (winner == -1)
    se = float(score.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    secs = length / TICK_HZ
    outcomes = Counter(r.outcome for r in recalls)
    docked = [r for r in recalls if r.outcome == "docked"]
    stuck = [r for r in recalls if r.outcome == "match ended"]
    survived = [r for r in recalls if r.outcome != "killed en route"]
    killed = [r for r in recalls if r.outcome == "killed en route"]
    by_pilot: dict[str, dict[str, Any]] = {}
    for pid in sorted({r.pilot for r in recalls}):
        mine = [r for r in recalls if r.pilot == pid]
        ok = [r for r in mine if r.outcome == "docked"]
        alive = [r for r in mine if r.outcome != "killed en route"]
        by_pilot[pid] = {
            "recalls": len(mine),
            "docked": len(ok),
            "completion": len(ok) / max(len(mine), 1),
            "completion_of_survivors": len(ok) / max(len(alive), 1),
            "failure_modes": dict(
                Counter(failure_mode(r) for r in mine if r.outcome == "match ended")
            ),
        }
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "sim_version": int(rlf_sim.SIM_VERSION),
        "mission": args.mission,
        "docking": docking,
        "n": int(n),
        "seed": args.seed,
        "rosters": [[list(t) for t in r.teams] for r, _ in plays],
        "pilots": str(args.pilots) if args.pilots else "script",
        "team1_win_rate": float(score.mean()),
        "team1_win_ci95": 1.96 * se,
        "end_reasons": {
            END_REASONS[c]: float(np.mean(reason == c))
            for c in range(1, len(END_REASONS))
            if (reason == c).any()
        },
        "length_median_s": float(np.median(secs)),
        "length_p90_s": float(np.percentile(secs, 90)),
        "dock": {
            "recalls": len(recalls),
            "recalls_per_match": len(recalls) / n,
            "docked": len(docked),
            "docked_per_match": len(docked) / n,
            "completion": len(docked) / max(len(recalls), 1),
            "completion_of_survivors": len(docked) / max(len(survived), 1),
            "seconds_to_dock": quantiles(
                [(r.ended - r.ordered) / TICK_HZ for r in docked]
            ),
            "metres_at_order": quantiles(
                [r.start_dist for r in recalls if not np.isnan(r.start_dist)]
            ),
            "outcomes": dict(outcomes.most_common()),
            "failure_modes": dict(
                Counter(failure_mode(r) for r in stuck).most_common()
            ),
            "failed_closest_m": quantiles([r.min_dist for r in stuck]),
            # The approach: of the recalls that came within 30 m of the dock point (a
            # docked one did), how many docked; of the ones that were inside the capture
            # radius and did not dock, the slowest they were there (too fast, m/s).
            "came_near": len(docked)
            + sum(1 for r in recalls if r.outcome != "docked" and r.min_dist <= NEAR),
            "came_near_docked": len(docked),
            "inside_not_docked": sum(
                1 for r in recalls if r.outcome != "docked" and r.inside_capture
            ),
            "inside_not_docked_slowest_rel": quantiles(
                [
                    r.min_rel_inside
                    for r in recalls
                    if r.outcome != "docked" and r.inside_capture
                ]
            ),
            "killed_seconds_after_order": quantiles(
                [(r.ended - r.ordered) / TICK_HZ for r in killed]
            ),
            "killed_metres_closed": quantiles(
                [
                    r.start_dist - r.min_dist
                    for r in killed
                    if np.isfinite(r.start_dist) and np.isfinite(r.min_dist)
                ]
            ),
            "failed_rel_speed_at_closest": quantiles(
                [r.rel_at_min for r in stuck if np.isfinite(r.rel_at_min)]
            ),
            "relaunches": relaunches,
            "relaunches_per_match": relaunches / n,
            "repaired_full": repaired,
            "hull_restored_per_match": restored / n,
            "by_pilot": by_pilot,
        },
    }
    text = json.dumps(out, indent=1)
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
