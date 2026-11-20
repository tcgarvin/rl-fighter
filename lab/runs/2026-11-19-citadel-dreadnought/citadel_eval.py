"""Station assault v10 (SIM_VERSION 10): the citadel against a carrier and a dreadnought.

Plays ``--n`` station assaults of one of the sim's station rosters (``--roster``,
default ``citadel``; ``"strike of 8"`` is v9's), every strike craft flown by one
controller per team (the script, or a live pilot list ``rlf.live_pilots/1`` drawn per
strike slot per match), the capital ships by the sim's scripts, both commanders
scripted. Each env is read until its first ``done``.

Reports (JSON, ``rlf.lab.citadel/1``): attacker (team 1) win rate and its 95% interval,
end reasons, match length; the citadel's hardpoints destroyed a match (turrets by kind,
bays) and which kind went first; who damaged the citadel; what the citadel did to the
dreadnought and how often the dreadnought and the carrier survived; and how much the
defender's strike craft hit the dreadnought (the zero-shot question: do pilots engage a
hull class they never saw, the obs class ``spare``).

    uv run python lab/runs/2026-11-19-citadel-dreadnought/citadel_eval.py --n 512 \\
        --out lab/runs/2026-11-19-citadel-dreadnought/out/balance_script.json
    ... --pilots lab/live_pilots.json --checkpoint-root /home/timg/code/rl-fighter
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import torch
import yaml  # type: ignore[import-untyped]

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

SCHEMA = "rlf.lab.citadel/1"
TICK_HZ = 30
END_REASONS = tuple(rlf_sim.END_REASONS)
TURRET_DESTROYED = int(rlf_sim.EVENT_KINDS["turret_destroyed"])
BAY_DESTROYED = int(rlf_sim.EVENT_KINDS["bay_destroyed"])
DEATH = int(rlf_sim.EVENT_KINDS["death"])


def sim_roster(name: str) -> tuple[list[str], list[str]]:
    """The sim's station roster ``name``.

    Raises:
        ValueError: The sim has no station roster of that name.
    """
    for r in rlf_sim.mission_rosters(STATION_ASSAULT):
        if r["name"] == name:
            return list(r["fleets"][0]), list(r["fleets"][1])
    names = [r["name"] for r in rlf_sim.mission_rosters(STATION_ASSAULT)]
    raise ValueError(f"no station roster {name!r} (the sim has {names})")


def mount_kinds(assets: Path) -> dict[str, tuple[list[str], list[str]]]:
    """Hull name -> (turret kinds by turret index, bay ids): ``turret.flak.2`` reads as
    ``flak``."""
    out: dict[str, tuple[list[str], list[str]]] = {}
    for path in sorted((assets / "hulls").glob("*/hull.yaml")):
        raw = yaml.safe_load(path.read_text())
        turrets = [str(t["id"]).split(".")[1] for t in raw.get("turrets", [])]
        bays = [str(b["id"]) for b in raw.get("bays", [])]
        out[str(raw["name"])] = (turrets, bays)
    return out


class PilotPool:
    """Learned pilots drawn per strike slot per match (``rlf.live_pilots/1``), as in
    ``lab/runs/2026-11-19-station-bomber/station_eval.py``. Checkpoints resolve against
    ``root`` (the checkout that holds ``lab/runs``: a worktree has no weights)."""

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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--n", type=int, default=512)
    p.add_argument("--seed", type=int, default=910_000)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--assets", type=Path, default=REPO / "assets")
    p.add_argument("--roster", default="citadel", help="a sim station roster name")
    p.add_argument("--station-as", default="carrier", choices=("carrier", "convoy"))
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

    team0, team1 = sim_roster(args.roster)
    roster = Roster(
        (tuple(team0), tuple(team1)),
        STATION_ASSAULT,
        (SCRIPTED, SCRIPTED),
        hide_orders=(False, False),
        station_as=args.station_as,
    )
    spec: dict[str, Any] = {"kind": STATION_ASSAULT, "as": args.station_as}
    time_limit = float(rlf_sim.mission_time_limit_s(STATION_ASSAULT))
    env = RustVecEnv(
        args.assets,
        args.n,
        roster.fleets(),
        args.seed,
        time_limit_s=time_limit,
        n_threads=args.threads,
        record_events=True,
        reaction_ticks=2,
        max_ships=roster.n_ships,
        commanders=(SCRIPTED, SCRIPTED),
    )
    for i in range(args.n):
        env.raw.set_next_roster(
            i,
            roster.fleets(),
            roster.arena_radius,
            mission=json.dumps(spec),
            commanders=[SCRIPTED, SCRIPTED],
            time_limit_s=time_limit,
            hide_orders=[False, False],
        )
    env.reset()
    names = hull_names_by_id(args.assets)
    mounts = mount_kinds(args.assets)
    capital = np.isin(env.hull_id, capital_hull_ids(args.assets))
    team = env.team.copy()
    hull = env.hull_id.copy()
    hull_name = [[names[h] if h >= 0 else "" for h in row] for row in hull]
    pool = (
        PilotPool(args.pilots, args.seed, args.checkpoint_root) if args.pilots else None
    )
    if pool is not None:
        pool.draw(team.shape)
    strike = ~capital & (team >= 0)
    n, s = team.shape
    station = 0  # team 0's first slot
    lines = [hull_name[0].index(h) for h in hull_name[0] if h == "dreadnought"]
    dread = lines[0] if lines else -1
    carrier = int(np.flatnonzero((team[0] == 1) & capital[0])[0])

    running = np.ones(n, dtype=bool)
    winner = np.full(n, -2, dtype=np.int64)
    reason = np.zeros(n, dtype=np.int64)
    length = np.zeros(n, dtype=np.int64)
    on_station: defaultdict[str, float] = defaultdict(float)
    citadel_on_dread = np.zeros(n)
    defenders_on_dread = np.zeros(n)  # team 0 strike craft -> the dreadnought
    defenders_total = np.zeros(n)  # team 0 strike craft -> anything
    defenders_hit_dread = np.zeros((n, s), dtype=bool)
    turrets_lost: Counter[str] = Counter()
    bays_lost = 0
    first_kind: Counter[str] = Counter()
    first_seen = np.zeros(n, dtype=bool)
    dread_turrets_lost = 0
    died = {"dreadnought": np.zeros(n, dtype=bool), "carrier": np.zeros(n, dtype=bool)}
    max_steps = int(round(time_limit * TICK_HZ)) + 2
    for step in range(1, max_steps + 1):
        actions = env.scripted_actions().copy()
        if pool is not None:
            pool.act(env, strike & running[:, None], actions)
        _, _, dones, info = env.step(actions)
        for i in np.flatnonzero(running & (info.hit_count > 0)):
            for row in info.hits[i, : info.hit_count[i]]:
                shooter, target, dmg = int(row[0]), int(row[1]), row[3] / 1000.0
                if target == station:
                    on_station[hull_name[i][shooter]] += dmg
                if team[i, shooter] == 0 and strike[i, shooter]:
                    defenders_total[i] += dmg
                if target == dread:
                    if shooter == station:
                        citadel_on_dread[i] += dmg
                    elif team[i, shooter] == 0 and strike[i, shooter]:
                        defenders_on_dread[i] += dmg
                        defenders_hit_dread[i, shooter] = True
        ev = env.events()
        for row in ev:
            i, kind = int(row[0]), int(row[1])
            if not running[i]:
                continue
            ship, index = int(row[2]), int(row[3])
            if kind == DEATH:
                if ship == dread:
                    died["dreadnought"][i] = True
                elif ship == carrier:
                    died["carrier"][i] = True
                continue
            if kind not in (TURRET_DESTROYED, BAY_DESTROYED):
                continue
            if ship != station:
                dread_turrets_lost += int(ship == dread)
                continue
            turrets, _ = mounts[hull_name[i][ship]]
            what = turrets[index] if kind == TURRET_DESTROYED else "bay"
            if kind == TURRET_DESTROYED:
                turrets_lost[what] += 1
            else:
                bays_lost += 1
            if not first_seen[i]:
                first_seen[i] = True
                first_kind[what] += 1
        ending = running & dones
        winner[ending] = info.winner[ending]
        reason[ending] = env.end_reason[ending]
        length[ending] = step
        running &= ~dones
        if not running.any():
            break
    if running.any():
        raise RuntimeError(f"{int(running.sum())} matches did not end")
    # A repelled assault killed the dreadnought and the carrier on or before the end.
    repelled = reason == END_REASONS.index("assault_repelled")
    for k in died:
        died[k] |= repelled

    att = winner == 1
    draw = winner == -1
    score = att + 0.5 * draw
    se = float(score.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    secs = length / TICK_HZ
    defenders = int(((team[0] == 0) & strike[0]).sum())
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "sim_version": int(rlf_sim.SIM_VERSION),
        "n": int(n),
        "seed": args.seed,
        "roster_name": args.roster,
        "roster": [list(t) for t in roster.teams],
        "arena_radius": roster.arena_radius,
        "station_as": args.station_as,
        "pilots": str(args.pilots) if args.pilots else "script",
        "attacker_win_rate": float(score.mean()),
        "attacker_win_ci95": 1.96 * se,
        "end_reasons": {
            END_REASONS[c]: float(np.mean(reason == c))
            for c in range(1, len(END_REASONS))
            if (reason == c).any()
        },
        "length_median_s": float(np.median(secs)),
        "length_p90_s": float(np.percentile(secs, 90)),
        "station_damage_by_hull_per_match": {
            k: v / n for k, v in sorted(on_station.items())
        },
        "station_turrets_destroyed_per_match": {
            k: v / n for k, v in sorted(turrets_lost.items())
        },
        "station_turrets_destroyed_total_per_match": sum(turrets_lost.values()) / n,
        "station_bays_destroyed_per_match": bays_lost / n,
        "first_hardpoint_lost": dict(first_kind.most_common()),
        "matches_with_a_hardpoint_lost": float(first_seen.mean()),
    }
    if dread >= 0:
        out.update(
            {
                "citadel_damage_to_dreadnought_per_match": float(
                    citadel_on_dread.mean()
                ),
                "dreadnought_turrets_destroyed_per_match": dread_turrets_lost / n,
                "dreadnought_died": float(died["dreadnought"].mean()),
                "carrier_died": float(died["carrier"].mean()),
                "defender_strike_damage_to_dreadnought_per_match": float(
                    defenders_on_dread.mean()
                ),
                "defender_strike_damage_share_on_dreadnought": float(
                    defenders_on_dread.sum() / max(defenders_total.sum(), 1e-9)
                ),
                "defender_strike_craft_that_hit_dreadnought": float(
                    defenders_hit_dread.sum() / max(n * defenders, 1)
                ),
            }
        )
    text = json.dumps(out, indent=1)
    print(text)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
