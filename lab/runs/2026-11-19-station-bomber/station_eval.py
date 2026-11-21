"""Station assault (SIM_VERSION 9) from the attacker's and defender's side.

Plays ``--n`` station assaults of one roster (default: the sim's default station
roster), every strike craft flown by one controller per team (``script`` or a live
pilot list, ``rlf.live_pilots/1``, each strike slot drawn from it per match), the
capital ships by the sim's scripts, both commanders ``--commanders`` (``unseen`` on a
team: the scripted commander with that team's orders hidden from its pilots). Each env
is read until its first ``done``.

Reports (JSON, ``rlf.lab.station/1``): attacker (team 1) win rate and its 95% interval,
end reasons, match length, the station's damage by the hull that dealt it, and survival
by team and hull.

    uv run python lab/runs/2026-11-19-station-bomber/station_eval.py --n 512 \
        --out lab/runs/2026-11-19-station-bomber/out/balance_script.json
    ... --pilots lab/live_pilots.json --station-as convoy
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import torch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from spacefight.env.rosters import (  # noqa: E402
    SCRIPTED,
    STATION_ASSAULT,
    Roster,
    capital_hull_ids,
    hull_names_by_id,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402

SCHEMA = "rlf.lab.station/1"
TICK_HZ = 30
END_REASONS = tuple(rlf_sim.END_REASONS)
UNSEEN = "unseen"


def default_roster() -> tuple[list[str], list[str]]:
    # STATION_ROSTER names one of the sim's station rosters (e.g. "citadel"); default the
    # first, the v9 station these measurements were made on.
    name = os.environ.get("STATION_ROSTER", "")
    rosters = rlf_sim.mission_rosters(STATION_ASSAULT)
    r = next(x for x in rosters if x["name"] == name) if name else rosters[0]
    return list(r["fleets"][0]), list(r["fleets"][1])


class PilotPool:
    """Learned pilots drawn per strike slot per match (``rlf.live_pilots/1``).

    Checkpoints resolve against ``root`` (the checkout that holds ``lab/runs``: a
    worktree has no weights)."""

    def __init__(self, path: Path, seed: int, root: Path) -> None:
        from spacefight.commander.pilots import live_pilot_checkpoints
        from spacefight.eval.controllers import Policy

        self.ids = [i for i, _ in live_pilot_checkpoints(path, root)]
        self.policies = [
            Policy(p, sample=True) for _, p in live_pilot_checkpoints(path, root)
        ]
        self.rng = np.random.default_rng(seed)
        self.assign: np.ndarray | None = None
        torch.manual_seed(seed)

    def draw(self, shape: tuple[int, int]) -> None:
        self.assign = self.rng.integers(0, len(self.policies), size=shape)

    def act(self, env: RustVecEnv, rows: np.ndarray, out: np.ndarray) -> None:
        assert self.assign is not None
        for k, pol in enumerate(self.policies):
            sel = rows & (self.assign == k)
            if sel.any():
                out[sel] = pol.act(env, sel)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--n", type=int, default=512)
    p.add_argument("--seed", type=int, default=900_000)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--assets", type=Path, default=REPO / "assets")
    p.add_argument("--team0", nargs="*", help="defender hulls (station first)")
    p.add_argument("--team1", nargs="*", help="attacker hulls (carrier first)")
    p.add_argument("--jump-in", type=int, nargs=2, default=None)
    p.add_argument("--station-as", default="carrier", choices=("carrier", "convoy"))
    p.add_argument("--commanders", nargs=2, default=[SCRIPTED, SCRIPTED])
    p.add_argument("--pilots", type=Path, help="live pilot list; default: the script")
    p.add_argument(
        "--pilots-team",
        type=int,
        choices=(0, 1),
        default=None,
        help="only this team flies the pilots (the other the script)",
    )
    p.add_argument(
        "--pilots-other",
        type=Path,
        default=None,
        help="with --pilots-team: a pilot list the other team flies (default: script)",
    )
    p.add_argument("--time-limit-s", type=float, default=None)
    p.add_argument(
        "--checkpoint-root",
        type=Path,
        default=Path("/home/timg/code/rl-fighter"),
        help="checkout holding the pilots' lab/runs checkpoints",
    )
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    torch.set_num_threads(max(1, args.threads))

    d0, d1 = default_roster()
    team0 = args.team0 or d0
    team1 = args.team1 or d1
    hide = tuple(c == UNSEEN for c in args.commanders)
    modes = tuple(SCRIPTED if c == UNSEEN else c for c in args.commanders)
    roster = Roster.of(team0, team1, mission=STATION_ASSAULT, commanders=modes)
    roster = Roster(
        roster.teams,
        STATION_ASSAULT,
        roster.commanders,
        hide_orders=(hide[0], hide[1]),
        station_as=args.station_as,
    )
    spec: dict[str, Any] = {"kind": STATION_ASSAULT, "as": args.station_as}
    if args.jump_in is not None:
        spec["jump_in"] = list(args.jump_in)
    time_limit = args.time_limit_s or float(
        rlf_sim.mission_time_limit_s(STATION_ASSAULT)
    )
    env = RustVecEnv(
        args.assets,
        args.n,
        roster.fleets(),
        args.seed,
        time_limit_s=time_limit,
        n_threads=args.threads,
        record_events=False,
        reaction_ticks=2,
        max_ships=roster.n_ships,
        commanders=modes,
    )
    for i in range(args.n):
        env.raw.set_next_roster(
            i,
            roster.fleets(),
            roster.arena_radius,
            mission=json.dumps(spec),
            commanders=list(modes),
            time_limit_s=time_limit,
            hide_orders=list(hide),
        )
    env.reset()
    names = hull_names_by_id(args.assets)
    capital = np.isin(env.hull_id, capital_hull_ids(args.assets))
    team = env.team.copy()
    hull = env.hull_id.copy()
    pool = (
        PilotPool(args.pilots, args.seed, args.checkpoint_root) if args.pilots else None
    )
    if pool is not None:
        pool.draw(team.shape)
    learned_rows = ~capital & (team >= 0)
    other: PilotPool | None = None
    other_rows = np.zeros_like(learned_rows)
    if pool is not None and args.pilots_team is not None:
        other_rows = learned_rows & (team == 1 - args.pilots_team)
        learned_rows &= team == args.pilots_team
        if args.pilots_other is not None:
            other = PilotPool(args.pilots_other, args.seed + 1, args.checkpoint_root)
            other.draw(team.shape)
    elif args.pilots_other is not None:
        raise SystemExit("--pilots-other needs --pilots and --pilots-team")
    station = 0  # team 0's first slot

    n, s = team.shape
    running = np.ones(n, dtype=bool)
    winner = np.full(n, -2, dtype=np.int64)
    reason = np.zeros(n, dtype=np.int64)
    length = np.zeros(n, dtype=np.int64)
    alive_end = np.zeros((n, s), dtype=bool)
    station_dmg = defaultdict(float)  # hull name -> damage summed over matches
    dmg_by = np.zeros((n, s), dtype=np.float64)  # damage dealt by slot
    dmg_to_capital = np.zeros((n, s), dtype=np.float64)
    max_steps = int(round(time_limit * TICK_HZ)) + 2
    for step in range(1, max_steps + 1):
        actions = env.scripted_actions().copy()
        if pool is not None:
            pool.act(env, learned_rows & running[:, None], actions)
        if other is not None:
            other.act(env, other_rows & running[:, None], actions)
        prev_alive = env.raw.alive.copy()
        _, _, dones, info = env.step(actions)
        for i in np.flatnonzero(running & (info.hit_count > 0)):
            for row in info.hits[i, : info.hit_count[i]]:
                shooter, target, dmg = int(row[0]), int(row[1]), row[3] / 1000.0
                dmg_by[i, shooter] += dmg
                if capital[i, target]:
                    dmg_to_capital[i, shooter] += dmg
                if target == station:
                    station_dmg[names[hull[i, shooter]]] += dmg
        ending = running & dones
        winner[ending] = info.winner[ending]
        reason[ending] = env.end_reason[ending]
        length[ending] = step
        alive_end[ending] = prev_alive[ending]
        running &= ~dones
        if not running.any():
            break
    if running.any():
        raise RuntimeError(f"{int(running.sum())} matches did not end")
    # alive_end is "alive before the last step" (a done env resets at once); the end
    # reason says who died on it: the station, or every attacker.
    alive_end[reason == END_REASONS.index("station_destroyed"), station] = False
    alive_end[
        (reason == END_REASONS.index("assault_repelled"))[:, None] & (team == 1)
    ] = False
    return report(
        args,
        roster,
        names,
        team,
        hull,
        capital,
        winner,
        reason,
        length,
        alive_end,
        station_dmg,
        dmg_by,
        dmg_to_capital,
    )


def report(
    args: argparse.Namespace,
    roster: Roster,
    names: list[str],
    team,
    hull,
    capital,
    winner,
    reason,
    length,
    alive_end,
    station_dmg,
    dmg_by,
    dmg_to_capital,
) -> int:
    n = winner.size
    att = winner == 1
    draw = winner == -1
    score = att + 0.5 * draw
    se = float(score.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    reasons = {
        END_REASONS[c]: float(np.mean(reason == c))
        for c in range(1, len(END_REASONS))
        if (reason == c).any()
    }
    secs = length / TICK_HZ
    surv: dict[str, dict[str, float]] = {}
    dealt: dict[str, dict[str, float]] = {}
    for t, side in ((0, "defender"), (1, "attacker")):
        surv[side] = {}
        dealt[side] = {}
        for hid in np.unique(hull[team == t]):
            sel = (team == t) & (hull == hid)
            name = names[int(hid)]
            surv[side][name] = float(alive_end[sel].mean())
            dealt[side][name] = float(dmg_by[sel].mean())
            if not capital[sel].any():
                dealt[side][f"{name}_vs_capital"] = float(dmg_to_capital[sel].mean())
    out = {
        "schema": SCHEMA,
        "sim_version": int(rlf_sim.SIM_VERSION),
        "n": int(n),
        "seed": args.seed,
        "roster": [list(t) for t in roster.teams],
        "station_as": args.station_as,
        "jump_in": args.jump_in,
        "commanders": list(args.commanders),
        "pilots": str(args.pilots) if args.pilots else "script",
        "pilots_team": args.pilots_team,
        "pilots_other": str(args.pilots_other) if args.pilots_other else None,
        "attacker_win_rate": float(score.mean()),
        "attacker_win_ci95": 1.96 * se,
        "draw_rate": float(draw.mean()),
        "end_reasons": reasons,
        "length_median_s": float(np.median(secs)),
        "length_p10_s": float(np.percentile(secs, 10)),
        "length_p90_s": float(np.percentile(secs, 90)),
        "station_damage_by_hull_per_match": {
            k: v / n for k, v in sorted(station_dmg.items())
        },
        "survival": surv,
        "damage_dealt_per_ship": dealt,
    }
    text = json.dumps(out, indent=1)
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
