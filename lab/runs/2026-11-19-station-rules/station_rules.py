"""Hand-written commanders in the station assault (SIM_VERSION 9) against no orders.

One team (the **rule** side: the attacker, team 1, or the defender, team 0) is commanded
by one hand rule through the sim's external commander; the other is ``unseen``: the
scripted commander with its orders hidden from its own pilots. Every strike craft is
flown by a live pilot (``lab/live_pilots.json``), drawn per slot per match as on the
live page; capital ships by the sim's scripts. Seeds, rosters and pilot draws are the
same for every rule, so matches pair rule against rule.

An external commander has to launch and steer its carrier itself. ``Logistics`` ports
the scripted commander's station arms (``crates/sim/src/scripted/commander.rs``:
``station_defence`` / ``station_attack``, launches and the attacker's carrier
waypoint, but no squads), so the rule ``none`` launches exactly as ``unseen`` does and
gives no orders. ``--rule unseen`` (the script, hidden) is the check: ``none`` must
reproduce it match for match.

Rules (``RULES``; the module constants give the numbers):

- ``none``: the script's launches, no orders. ``scripted``: the sim's script, orders
  shown to its pilots. ``unseen``: the script, orders hidden (the check).
- Attacker. ``rally_release``: at the first slow tick, the whole wing (and every later
  launch) one squad, go-to a rally point ``RALLY_M`` from the station on the line to
  the attacker's carrier (outside its 230 m flak), radius ``GOTO_RADIUS``, with a v8
  deadline; a ship that arrives (or misses) is free. ``bomber_only``: only the bombers,
  go-to a standoff point ``STANDOFF_M`` from the station (radius 60, so arriving puts
  the station inside the torpedo's 240 m), with a deadline, then free; nobody else gets
  an order. ``escort_bombers``: as ``bomber_only``, and the gunships defend the lead
  bomber (the one nearest the station, kept until it is gone); fighters and strafers
  free. ``carrier_push``: no orders; once its hangar is empty, the carrier's waypoint
  is ``CARRIER_STANDOFF_M`` (170 m, the script's carrier-battle standoff) short of the
  station, inside both sides' flak, instead of the patrol out of reach.
- Defender. The script scrambles every bay while an attacking strike craft is within
  320 m of the station, and the attacker's jump-in trio is there by t = 2 s, so the
  script empties its hangar at once. ``hold_reserve``: no orders; launch nothing until
  ``WAVE_COUNT`` (4) attacking strike craft are within 320 m (the main wave, not the
  jump-in trio), then every bay every slow tick (one wave). ``hold_late``: no orders;
  launch nothing until the station's hull is below ``LATE_HULL_FRAC`` (0.6).
  ``hold_never``: no orders, no launches (the picket alone; the reserve dies docked if
  the station falls): what launching the reserve is worth at all.
  ``intercept_bombers``: the script's launches; the gunships defend the station,
  everyone else free. ``hunt_bombers``: as ``intercept_bombers``, and the fighters and
  strafers attack the bomber nearest the station once one is inside the alarm radius
  (kept until it dies), free otherwise.

``learned`` (added for ``../2026-11-19-station-commander``): a learned commander
(``--commander <commander.pt>``, ``save_commander``) runs the rule side in the sim's
``learned`` mode, its decisions sampled as in training; it launches and steers its carrier
itself. Every rule's output also times the rule side's launches (first launch, the
station's hull then, hangar empty), and a learned rule counts the strike craft it
re-orders a minute.

Go-to deadlines (v8) as in ``lab/runs/2026-11-17-order-cost/order_rules.py``: 2 times
the slowest member's straight-line time to the circle at its speed cap, plus 3 s, from
the first order; the same point and deadline are re-sent to ships that launch later,
so the members already ordered keep their instance.

    uv run python lab/runs/2026-11-19-station-rules/station_rules.py --role attacker \
        --rule rally_release --n 512 --out out/attacker_rally_release.json

Output: JSON ``rlf.lab.station_rules/1`` (summary and per-match arrays).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE.parent / "2026-11-19-station-bomber"))

from station_eval import PilotPool, default_roster  # noqa: E402

from spacefight.env.rosters import (  # noqa: E402
    SCRIPTED,
    STATION_ASSAULT,
    Roster,
    capital_hull_ids,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402

SCHEMA = "rlf.lab.station_rules/1"
TICK_HZ = 30
EXTERNAL = "external"
END_REASONS = tuple(rlf_sim.END_REASONS)
ATTACKER_RULES = ("rally_release", "bomber_only", "escort_bombers", "carrier_push")
DEFENDER_RULES = ("hold_reserve", "hold_late", "hold_never", "intercept_bombers", "hunt_bombers")
LEARNED = "learned"
RULES = ("none", "scripted", "unseen", LEARNED) + ATTACKER_RULES + DEFENDER_RULES

# The scripted commander's station constants (scripted/commander.rs).
WING_BASE = 3
WING_GROWTH_TICKS = 900
LAUNCH_INTERVAL_TICKS = 360
BAY_COOLDOWN_TICKS = 45
STATION_ALARM_RADIUS = 320.0
HOME_FRAC = 0.6
PATROL_Y = 60.0
PATROL_TICKS = 600
WAYPOINT_SLACK = 20.0
POINT_LIMIT_FRAC = 0.95
# The rules' numbers.
GOTO_RADIUS = 60.0
GOTO_SLACK = 2.0
GOTO_EXTRA_S = 3.0
FLAK_RANGE = 230.0
RALLY_M = 320.0  # arrival edge 260 m from the station: outside flak (230 m + mounts)
STANDOFF_M = 180.0  # arrival edge 240 m: the torpedo's range
SPEED_CAP = {"fighter": 60.0, "strafer": 50.0, "gunship": 24.0, "bomber": 34.0}
CAPITAL_ROLES = ("carrier", "transport")
SAMPLE_TICKS = 30  # telemetry every second
BOMBER_NEAR_M = 300.0  # a bomber "at" the station: torpedo range (240 m) plus a bit
SNAP_S = (10, 20, 30, 45, 60, 90)  # telemetry snapshots (s)
SNAP_KEYS = (
    "att_strike",  # attacking strike craft alive (docked included)
    "att_near",  # ... on the field within the alarm radius (320 m) of the station
    "bombers",
    "bombers_near",  # bombers within BOMBER_NEAR_M
    "def_out",  # defending strike craft on the field
    "def_hangar",  # defending strike craft still docked
    "station_hull",  # hull fraction
    "carrier_dist",  # attacking carrier to station (m)
)
WAVE_COUNT = 4  # hold_reserve: the main wave (the jump-in trio is 3 ships)
LATE_HULL_FRAC = 0.6  # hold_late: launch once the station's hull is below this
CARRIER_STANDOFF_M = 170.0  # carrier_push: the script's carrier-battle standoff
ORDER_SQUAD, ESCORT_SQUAD = 0, 1


def dist(a: Any, b: Any) -> float:
    return float(math.hypot(a[0] - b[0], a[1] - b[1]))


class View:
    """One match's state as the scripted commander reads it (render + mission state)."""

    def __init__(self, rs: dict, ms: dict) -> None:
        self.tick = int(rs["tick"]) + 1  # the slow tick the commands apply on
        self.radius = float(rs["arena_radius"])
        self.ships = rs["ships"]
        self.jump = [s["jump"] for s in ms["ships"]]
        self.waypoint = [s["waypoint"] for s in ms["ships"]]
        self.carrier = [int(c) for c in ms["carrier"]]
        self.hangar = [list(h) for h in ms["hangar"]]
        self.bay_ready = [list(b) for b in ms["bay_ready"]]

    def active(self, s: dict) -> bool:
        return bool(s["alive"] and s["present"])

    def in_match(self, s: dict) -> bool:
        return bool(s["alive"]) and self.jump[s["slot"]] != "departed"

    def strike(self, s: dict) -> bool:
        return s["role"] not in CAPITAL_ROLES

    def wing(self, team: int) -> list[dict]:
        """Own strike craft in the match and not docked."""
        return [
            s
            for s in self.ships
            if s["team"] == team and self.in_match(s) and not s["docked"] and self.strike(s)
        ]

    def enemy_strike(self, team: int) -> list[dict]:
        return [s for s in self.ships if s["team"] != team and self.active(s) and self.strike(s)]

    def station(self) -> dict:
        return self.ships[self.carrier[0]]


class Logistics:
    """The scripted commander's launches and waypoint (no squads), per ``launch`` mode.

    ``script`` ports ``station_defence`` / ``station_attack`` exactly. The defender also
    has ``wave`` (nothing until ``WAVE_COUNT`` attacking strike craft are inside the
    alarm radius, then every bay every slow tick) and ``late`` (nothing until the
    station's hull is below ``LATE_HULL_FRAC``, then every bay) and ``never``. The
    attacker also has
    ``push``: the script's launches, and once the hangar is empty the carrier's waypoint
    is ``CARRIER_STANDOFF_M`` short of the station instead of the patrol."""

    def __init__(self, team: int, mode: str) -> None:
        self.team = team
        self.mode = mode

    def commands(self, v: View) -> tuple[list[dict], list[int]]:
        """Launch and waypoint commands, and the reserves the launches will take."""
        if not v.active(v.station()):
            return [], []
        return self.defence(v) if self.team == 0 else self.attack(v)

    def launches(self, v: View, n: int) -> tuple[list[dict], list[int]]:
        taken = v.hangar[self.team][: max(0, min(n, len(v.hangar[self.team])))]
        return [{"kind": "launch", "hull": None, "bay": None} for _ in taken], taken

    def defence(self, v: View) -> tuple[list[dict], list[int]]:
        at = v.station()["pos"]
        alarmed = any(dist(s["pos"], at) < STATION_ALARM_RADIUS for s in v.enemy_strike(0))
        bays = len(v.bay_ready[0])
        if self.mode == "wave":
            near = sum(dist(s["pos"], at) < STATION_ALARM_RADIUS for s in v.enemy_strike(0))
            return self.launches(v, bays if near >= WAVE_COUNT else 0)
        if self.mode == "never":
            return [], []
        if self.mode == "late":
            hull = v.station()["hp"] / v.station()["max_hp"]
            return self.launches(v, bays if hull < LATE_HULL_FRAC else 0)
        last = max(v.bay_ready[0]) if bays else 0
        last = max(0, last - BAY_COOLDOWN_TICKS)
        paced = v.tick >= last + LAUNCH_INTERVAL_TICKS or last == 0
        target = WING_BASE + v.tick // WING_GROWTH_TICKS
        if alarmed:
            n = bays
        elif len(v.wing(0)) < target and paced:
            n = 1
        else:
            n = 0
        return self.launches(v, n)

    def attack(self, v: View) -> tuple[list[dict], list[int]]:
        own = v.carrier[1]
        if not v.active(v.ships[own]):
            return [], []
        cmds, taken = self.launches(v, len(v.bay_ready[1]))
        wing = len(v.wing(1)) + len(taken)
        at = v.station()["pos"]
        if wing == 0 and not v.hangar[1]:
            goal = tuple(at)
        elif self.mode == "push" and not v.hangar[1]:
            here = v.ships[own]["pos"]
            d = max(dist(here, at), 1e-6)
            goal = (
                at[0] + (here[0] - at[0]) / d * CARRIER_STANDOFF_M,
                at[1] + (here[1] - at[1]) / d * CARRIER_STANDOFF_M,
            )
        else:
            leg = 1.0 if (v.tick // PATROL_TICKS) % 2 == 0 else -1.0
            goal = (HOME_FRAC * v.radius, leg * PATROL_Y)
        limit = POINT_LIMIT_FRAC * v.radius
        r = math.hypot(*goal)
        if r > limit:
            goal = (goal[0] * limit / r, goal[1] * limit / r)
        cur = v.waypoint[own]
        if cur is None or dist(cur, goal) > WAYPOINT_SLACK:
            cmds.append({"kind": "waypoint", "ship": own, "pos": [goal[0], goal[1]]})
        return cmds, taken


def launch_mode(rule: str) -> str:
    return {
        "hold_reserve": "wave",
        "hold_late": "late",
        "hold_never": "never",
        "carrier_push": "push",
    }.get(rule, "script")


class Rule:
    """One external team's commands in every match (module docs)."""

    def __init__(self, rule: str, team: int, n: int) -> None:
        self.rule = rule
        self.team = team
        self.logistics = Logistics(team, launch_mode(rule))
        self.goto: list[dict | None] = [None] * n  # the one go-to order, once set
        self.sent: list[dict[int, tuple]] = [dict() for _ in range(n)]  # squad -> last
        self.ward = np.full(n, -1, dtype=np.int64)
        self.prey = np.full(n, -1, dtype=np.int64)

    def commands(self, i: int, v: View) -> list[dict]:
        cmds, taken = self.logistics.commands(v)
        if not v.active(v.station()):
            return cmds
        joining = [v.ships[s] for s in taken]
        wing = v.wing(self.team) + joining
        squads: dict[int, tuple[list[int], dict]] = {}
        if self.rule == "rally_release":
            squads[ORDER_SQUAD] = (slots(wing), self.goto_order(i, v, wing, RALLY_M))
        elif self.rule in ("bomber_only", "escort_bombers"):
            bombers = [s for s in wing if s["hull"] == "bomber"]
            if bombers:
                squads[ORDER_SQUAD] = (slots(bombers), self.goto_order(i, v, bombers, STANDOFF_M))
            if self.rule == "escort_bombers":
                guns = [s for s in v.wing(self.team) if s["hull"] == "gunship"]
                squads[ESCORT_SQUAD] = (slots(guns), self.escort_order(i, v))
        elif self.rule in ("intercept_bombers", "hunt_bombers"):
            guns = [s for s in v.wing(self.team) if s["hull"] == "gunship"]
            squads[ORDER_SQUAD] = (
                slots(guns),
                {"kind": "defend", "ward": v.carrier[0]} if guns else {"kind": "none"},
            )
            if self.rule == "hunt_bombers":
                rest = [s for s in v.wing(self.team) if s["hull"] != "gunship"]
                squads[ESCORT_SQUAD] = (slots(rest), self.hunt_order(i, v))
        for k, (members, order) in squads.items():
            if not members:
                order = {"kind": "none"}
            key = (tuple(members), json.dumps(order, sort_keys=True))
            if self.sent[i].get(k) != key:
                self.sent[i][k] = key
                cmds.append({"kind": "squad", "squad": k, "members": members, "order": order})
        return cmds

    def goto_order(self, i: int, v: View, members: list[dict], from_station: float) -> dict:
        """The side's one go-to: a point ``from_station`` m from the station toward the
        attacker's carrier, with a deadline from its first members (module docs)."""
        if self.goto[i] is None:
            at = v.station()["pos"]
            toward = v.ships[v.carrier[1]]["pos"]
            d = max(dist(at, toward), 1e-6)
            point = (
                at[0] + (toward[0] - at[0]) / d * from_station,
                at[1] + (toward[1] - at[1]) / d * from_station,
            )
            secs = max(
                max(dist(s["pos"], point) - GOTO_RADIUS, 0.0) / SPEED_CAP[s["hull"]]
                for s in members
            )
            deadline = v.tick + math.ceil((GOTO_SLACK * secs + GOTO_EXTRA_S) * TICK_HZ)
            self.goto[i] = {
                "kind": "goto",
                "point": [float(point[0]), float(point[1])],
                "radius": GOTO_RADIUS,
                "deadline": int(deadline),
            }
        return self.goto[i]

    def escort_order(self, i: int, v: View) -> dict:
        """Defend the lead bomber (nearest the station), kept while it is on the field."""
        bombers = [
            s for s in v.ships if s["team"] == self.team and v.active(s) and s["hull"] == "bomber"
        ]
        alive = {s["slot"] for s in bombers}
        if self.ward[i] not in alive:
            at = v.station()["pos"]
            self.ward[i] = (
                min(bombers, key=lambda s: (dist(s["pos"], at), s["slot"]))["slot"]
                if bombers
                else -1
            )
        return (
            {"kind": "defend", "ward": int(self.ward[i])} if self.ward[i] >= 0 else {"kind": "none"}
        )

    def hunt_order(self, i: int, v: View) -> dict:
        """Attack the bomber nearest the station once one is inside the alarm radius."""
        at = v.station()["pos"]
        bombers = [s for s in v.enemy_strike(self.team) if s["hull"] == "bomber"]
        if self.prey[i] not in {s["slot"] for s in bombers}:
            near = [s for s in bombers if dist(s["pos"], at) < STATION_ALARM_RADIUS]
            self.prey[i] = (
                min(near, key=lambda s: (dist(s["pos"], at), s["slot"]))["slot"] if near else -1
            )
        return (
            {"kind": "attack", "target": int(self.prey[i])}
            if self.prey[i] >= 0
            else {"kind": "none"}
        )


def slots(ships: list[dict]) -> list[int]:
    return sorted({int(s["slot"]) for s in ships})


def build_env(args: argparse.Namespace, rule_team: int) -> tuple[RustVecEnv, tuple, tuple]:
    team0, team1 = default_roster()
    modes = [SCRIPTED, SCRIPTED]
    hide = [True, True]
    if args.rule == "scripted":
        hide[rule_team] = False
    elif args.rule == LEARNED:
        modes[rule_team] = LEARNED
        hide[rule_team] = False
    elif args.rule != "unseen":
        modes[rule_team] = EXTERNAL
        hide[rule_team] = False
    roster = Roster.of(team0, team1, mission=STATION_ASSAULT, commanders=tuple(modes))
    roster = Roster(
        roster.teams,
        STATION_ASSAULT,
        roster.commanders,
        hide_orders=(hide[0], hide[1]),
        station_as=args.station_as,
    )
    time_limit = float(rlf_sim.mission_time_limit_s(STATION_ASSAULT))
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
        commanders=tuple(modes),
    )
    spec = json.dumps({"kind": STATION_ASSAULT, "as": args.station_as})
    for i in range(args.n):
        env.raw.set_next_roster(
            i,
            roster.fleets(),
            roster.arena_radius,
            mission=spec,
            commanders=list(modes),
            time_limit_s=time_limit,
            hide_orders=list(hide),
        )
    env.reset()
    return env, tuple(modes), tuple(hide)


def run(args: argparse.Namespace) -> dict:
    rule_team = 1 if args.role == "attacker" else 0
    if args.rule in ATTACKER_RULES and rule_team != 1:
        raise ValueError(f"{args.rule} is an attacker rule")
    if args.rule in DEFENDER_RULES and rule_team != 0:
        raise ValueError(f"{args.rule} is a defender rule")
    env, modes, hide = build_env(args, rule_team)
    n, S = env.n_envs, env.n_ships
    team = env.team.copy()
    capital = np.isin(env.hull_id, capital_hull_ids(args.assets))
    rs0 = [env.raw.render_state(i) for i in range(n)]
    hull = np.full((n, S), "", dtype=object)
    for i in range(n):
        for s in rs0[i]["ships"]:
            hull[i, s["slot"]] = s["hull"]
    station = np.array(
        [
            [s["slot"] for s in r["ships"] if s["team"] == 0 and s["role"] == "carrier"][0]
            for r in rs0
        ]
    )
    bomber = hull == "bomber"
    pool = PilotPool(args.pilots, args.seed, args.checkpoint_root)
    pool.draw(team.shape)
    learned = ~capital & (team >= 0)
    rule = Rule(args.rule, rule_team, n) if modes[rule_team] == EXTERNAL else None
    commander = load_learned(args) if modes[rule_team] == LEARNED else None
    strike = learned
    rule_side = strike & (team == rule_team)
    launch = LaunchTimes(rs0, rule_team, station)
    reordered = np.zeros(n)  # strike craft the learned commander re-ordered

    time_limit = float(rlf_sim.mission_time_limit_s(STATION_ASSAULT))
    max_steps = int(round(time_limit * TICK_HZ)) + 4
    running = np.ones(n, dtype=bool)
    winner = np.full(n, -2, dtype=np.int64)
    reason = np.zeros(n, dtype=np.int64)
    end_tick = np.zeros(n, dtype=np.int64)
    neg = lambda: np.full(n, -1, dtype=np.int64)  # noqa: E731
    rec = {
        "first_station_hit": neg(),
        "first_torpedo_on_station": neg(),
        "contact": neg(),  # first sample with an attacking strike craft in alarm radius
    }
    snap = {key: np.full((n, len(SNAP_S)), np.nan) for key in SNAP_KEYS}
    station_dmg = np.zeros(n)
    station_dmg_bomber = np.zeros(n)
    bomber_dmg_capital = np.zeros(n)
    alive_end = np.zeros((n, S), dtype=bool)
    ordered_s = np.zeros((n, S))
    alive_s = np.zeros((n, S))
    goto_seen = np.zeros((n, S), dtype=bool)
    goto_arrived = np.zeros((n, S), dtype=bool)
    goto_missed = np.zeros((n, S), dtype=bool)
    torch.manual_seed(args.seed)
    t0 = time.time()
    for step in range(max_steps):
        if commander is not None:
            reordered += decide(env, commander, rule_team, running)
        due = np.asarray(env.raw.command_due())
        sample = step % SAMPLE_TICKS == SAMPLE_TICKS - 1
        if sample or due.any():
            tracks = env.order_tracks()
            eff = np.asarray(tracks["effective_kind"])
            std = np.asarray(tracks["standing_kind"])
        for i in np.flatnonzero(running & (due | sample)):
            rs = env.raw.render_state(int(i))
            if due[i] and rule is not None:
                v = View(rs, env.raw.mission_state(int(i)))
                cmds = rule.commands(int(i), v)
                if cmds:
                    env.raw.submit_command(int(i), rule_team, cmds)
            if sample:
                launch.sample(int(i), rs)
                telemetry(
                    i,
                    rs,
                    rec,
                    snap,
                    station[i],
                    rule_side,
                    eff,
                    std,
                    tracks,
                    ordered_s,
                    alive_s,
                    goto_seen,
                    goto_arrived,
                    goto_missed,
                )
        actions = env.scripted_actions().copy()
        pool.act(env, learned & running[:, None], actions)
        prev_alive = env.raw.alive.copy()
        _, _, dones, info = env.step(actions)
        for i in np.flatnonzero(running & (info.hit_count > 0)):
            for row in info.hits[i, : info.hit_count[i]]:
                sh, tg, dmg = int(row[0]), int(row[1]), row[3] / 1000.0
                if bomber[i, sh] and capital[i, tg] and team[i, tg] != team[i, sh]:
                    bomber_dmg_capital[i] += dmg
                if tg == station[i] and team[i, sh] == 1:
                    station_dmg[i] += dmg
                    if rec["first_station_hit"][i] < 0:
                        rec["first_station_hit"][i] = step + 1
                    if bomber[i, sh]:
                        station_dmg_bomber[i] += dmg
                        if rec["first_torpedo_on_station"][i] < 0:
                            rec["first_torpedo_on_station"][i] = step + 1
        ending = running & dones
        winner[ending] = info.winner[ending]
        reason[ending] = env.end_reason[ending]
        end_tick[ending] = step + 1
        alive_end[ending] = prev_alive[ending]
        running &= ~dones
        if not running.any():
            break
    else:
        raise RuntimeError(f"{int(running.sum())} matches did not end")
    alive_end[reason == END_REASONS.index("station_destroyed"), 0] = False
    alive_end[(reason == END_REASONS.index("assault_repelled"))[:, None] & (team == 1)] = False
    return report(
        args,
        modes,
        hide,
        time.time() - t0,
        team,
        hull,
        strike,
        rule_side,
        winner,
        reason,
        end_tick,
        rec,
        snap,
        station_dmg,
        station_dmg_bomber,
        bomber_dmg_capital,
        alive_end,
        ordered_s,
        alive_s,
        goto_seen,
        goto_arrived,
        goto_missed,
        launch.summary(end_tick, reordered if commander is not None else None),
    )


def load_learned(args: argparse.Namespace) -> Any:
    from spacefight.commander.policy import load_commander

    if args.commander is None:
        raise ValueError("--rule learned needs --commander <commander.pt>")
    actor, _ = load_commander(args.commander)
    return actor


def decide(env: RustVecEnv, actor: Any, team: int, running: np.ndarray) -> np.ndarray:
    """Submit the learned team's due decisions (sampled, as in training); the number of
    strike craft each match's decision re-ordered."""
    from spacefight.commander.io import CommanderInputs
    from spacefight.commander.policy import sample_actions
    from spacefight.commander.train import FEATURE_KEYS

    out = np.zeros(env.n_envs)
    rows = np.flatnonzero(np.asarray(env.raw.commander_due(team), dtype=bool) & running)
    if rows.size == 0:
        return out
    feats = env.raw.commander_features(team)
    x = CommanderInputs.from_numpy({k: np.asarray(feats[k])[rows] for k in FEATURE_KEYS})
    actions = sample_actions(actor, x)
    changed = env.raw.submit_commander_actions(
        team, rows.astype(np.int64), actions.numpy().astype(np.int32)
    )
    out[rows] = np.asarray(changed, dtype=np.float64)
    return out


class LaunchTimes:
    """When the rule side's hangar empties, sampled once a second: the first launch (a
    docked strike craft that is no longer docked), the station's hull then, the
    hangar empty."""

    def __init__(self, rs0: list[dict], team: int, station: np.ndarray) -> None:
        self.team = team
        self.station = station
        self.docked0 = np.array(
            [sum(s["team"] == team and s["docked"] for s in r["ships"]) for r in rs0]
        )
        n = len(rs0)
        self.first = np.full(n, -1, dtype=np.int64)
        self.empty = np.full(n, -1, dtype=np.int64)
        self.hull_at_first = np.full(n, np.nan)

    def sample(self, i: int, rs: dict) -> None:
        ships = rs["ships"]
        docked = sum(s["team"] == self.team and s["alive"] and s["docked"] for s in ships)
        tick = int(rs["tick"]) + 1
        if self.first[i] < 0 and docked < self.docked0[i]:
            st = ships[self.station[i]]
            self.first[i] = tick
            self.hull_at_first[i] = st["hp"] / st["max_hp"]
        if self.empty[i] < 0 and docked == 0 and self.docked0[i] > 0:
            self.empty[i] = tick

    def summary(self, end_tick: np.ndarray, reordered: np.ndarray | None) -> dict:
        def median_s(t: np.ndarray) -> float | None:
            t = t[t >= 0]
            return float(np.median(t) / TICK_HZ) if t.size else None

        launched = self.first >= 0
        out: dict[str, Any] = {
            "docked_at_start_mean": float(self.docked0.mean()),
            "launched_share": float(launched.mean()),
            "first_launch_median_s": median_s(self.first),
            "first_launch_quartiles_s": (
                [float(q) / TICK_HZ for q in np.percentile(self.first[launched], (25, 75))]
                if launched.any()
                else None
            ),
            "station_hull_at_first_launch_median": (
                float(np.nanmedian(self.hull_at_first)) if launched.any() else None
            ),
            "hangar_empty_share": float((self.empty >= 0).mean()),
            "hangar_empty_median_s": median_s(self.empty),
            "orders_per_minute": None,
            "per_match": {
                "first_launch": self.first.tolist(),
                "hangar_empty": self.empty.tolist(),
                "station_hull_at_first_launch": [
                    None if math.isnan(h) else round(float(h), 3) for h in self.hull_at_first
                ],
            },
        }
        if reordered is not None:
            minutes = np.maximum(end_tick, 1) / (TICK_HZ * 60.0)
            out["orders_per_minute"] = float(np.mean(reordered / minutes))
            out["per_match"]["reordered"] = reordered.astype(int).tolist()
        return out


def telemetry(
    i,
    rs,
    rec,
    snap,
    station,
    rule_side,
    eff,
    std,
    tracks,
    ordered_s,
    alive_s,
    goto_seen,
    goto_arrived,
    goto_missed,
) -> None:
    """One match's one-second sample: first contact, the snapshots (``SNAP_S``) and the
    rule side's orders."""
    tick = int(rs["tick"])
    ships = rs["ships"]
    at = ships[station]["pos"]
    on_field = [s for s in ships if s["alive"] and s["present"] and s["role"] not in CAPITAL_ROLES]
    for s in on_field:
        j = s["slot"]
        if rule_side[i, j]:
            alive_s[i, j] += 1.0
            if eff[i, j] != 0:
                ordered_s[i, j] += 1.0
            if std[i, j] == 3:
                goto_seen[i, j] = True
                goto_arrived[i, j] |= bool(tracks["arrived"][i, j]) and not bool(
                    tracks["missed"][i, j]
                )
                goto_missed[i, j] |= bool(tracks["missed"][i, j])
    att = [s for s in on_field if s["team"] == 1]
    near = [s for s in att if dist(s["pos"], at) < STATION_ALARM_RADIUS]
    if rec["contact"][i] < 0 and near:
        rec["contact"][i] = tick
    if (tick + 1) % TICK_HZ or (tick + 1) // TICK_HZ not in SNAP_S:
        return
    k = SNAP_S.index((tick + 1) // TICK_HZ)
    wing = [s for s in ships if s["team"] == 1 and s["alive"] and s["role"] not in CAPITAL_ROLES]
    carrier = [s for s in ships if s["team"] == 1 and s["role"] == "carrier" and s["alive"]]
    st = ships[station]
    snap["att_strike"][i, k] = len(wing)
    snap["att_near"][i, k] = len(near)
    snap["bombers"][i, k] = sum(s["hull"] == "bomber" for s in wing)
    snap["bombers_near"][i, k] = sum(
        s["hull"] == "bomber" and dist(s["pos"], at) < BOMBER_NEAR_M for s in att
    )
    snap["def_out"][i, k] = sum(s["team"] == 0 for s in on_field)
    snap["def_hangar"][i, k] = sum(s["team"] == 0 and s["alive"] and s["docked"] for s in ships)
    snap["station_hull"][i, k] = st["hp"] / st["max_hp"]
    snap["carrier_dist"][i, k] = dist(carrier[0]["pos"], at) if carrier else np.nan


def report(
    args,
    modes,
    hide,
    secs,
    team,
    hull,
    strike,
    rule_side,
    winner,
    reason,
    end_tick,
    rec,
    snap,
    station_dmg,
    station_dmg_bomber,
    bomber_dmg_capital,
    alive_end,
    ordered_s,
    alive_s,
    goto_seen,
    goto_arrived,
    goto_missed,
    launches: dict,
) -> dict:
    n = winner.size
    att_score = (winner == 1) + 0.5 * (winner == -1)
    se = float(att_score.std(ddof=1) / math.sqrt(n))
    reasons = {
        END_REASONS[c]: float(np.mean(reason == c))
        for c in range(1, len(END_REASONS))
        if (reason == c).any()
    }
    first_torp = rec["first_torpedo_on_station"]
    hit_t = first_torp[first_torp >= 0] / TICK_HZ
    surv = {}
    for t, side in ((0, "defender"), (1, "attacker")):
        surv[side] = {
            str(h): float(alive_end[(team == t) & (hull == h) & strike].mean())
            for h in sorted(set(hull[(team == t) & strike]))
        }
    out = {
        "schema": SCHEMA,
        "sim_version": int(rlf_sim.SIM_VERSION),
        "role": args.role,
        "rule": args.rule,
        "commander": str(args.commander) if args.commander else None,
        "n": int(n),
        "seed": args.seed,
        "station_as": args.station_as,
        "commanders": list(modes),
        "hide_orders": list(hide),
        "pilots": str(args.pilots),
        "secs": round(secs, 1),
        "attacker_win_rate": float(att_score.mean()),
        "attacker_win_se": se,
        "end_reasons": reasons,
        "length_median_s": float(np.median(end_tick / TICK_HZ)),
        "station_damage_mean": float(station_dmg.mean()),
        "station_damage_bomber_mean": float(station_dmg_bomber.mean()),
        "bomber_damage_to_capital_mean": float(bomber_dmg_capital.mean()),
        "torpedo_on_station_share": float((first_torp >= 0).mean()),
        "first_torpedo_on_station_median_s": float(np.median(hit_t)) if hit_t.size else None,
        "contact_median_s": (
            float(np.median(rec["contact"][rec["contact"] >= 0] / TICK_HZ))
            if (rec["contact"] >= 0).any()
            else None
        ),
        "snapshots_s": list(SNAP_S),
        "running_share": [
            float(np.mean(~np.isnan(snap["att_strike"][:, k]))) for k in range(len(SNAP_S))
        ],
        # Means over the matches still running at each snapshot.
        "snapshots": {
            key: [
                float(np.nanmean(v[:, k])) if (~np.isnan(v[:, k])).any() else None
                for k in range(len(SNAP_S))
            ]
            for key, v in snap.items()
        },
        "survival": surv,
        "rule_side": {
            "ordered_share": float(ordered_s[rule_side].sum() / max(alive_s[rule_side].sum(), 1.0)),
            "goto_ships": int(goto_seen[rule_side].sum()),
            "goto_arrived": int(goto_arrived[rule_side].sum()),
            "goto_missed": int(goto_missed[rule_side].sum()),
        },
        "launches": launches,
        "per_match": {
            "winner": winner.tolist(),
            "reason": reason.tolist(),
            "end_tick": end_tick.tolist(),
            "station_damage": np.round(station_dmg, 1).tolist(),
            "station_damage_bomber": np.round(station_dmg_bomber, 1).tolist(),
            **{k: v.tolist() for k, v in rec.items()},
        },
    }
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--role", choices=("attacker", "defender"), required=True)
    p.add_argument("--rule", choices=RULES, required=True)
    p.add_argument("--n", type=int, default=512)
    p.add_argument("--seed", type=int, default=1_119_000)
    p.add_argument("--threads", type=int, default=2, help="sim threads")
    p.add_argument("--torch-threads", type=int, default=1, help="fixed across cells: pairing")
    p.add_argument("--station-as", default="carrier", choices=("carrier", "convoy"))
    p.add_argument("--assets", type=Path, default=REPO / "assets")
    p.add_argument("--pilots", type=Path, default=REPO / "lab" / "live_pilots.json")
    p.add_argument("--checkpoint-root", type=Path, default=Path("/home/timg/code/rl-fighter"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--commander", type=Path, default=None, help="--rule learned's commander")
    args = p.parse_args(argv)
    torch.set_num_threads(args.torch_threads)
    res = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res) + "\n")
    print(
        f"{args.role} {args.rule} ({args.station_as}): attacker {res['attacker_win_rate']:.3f}"
        f" +- {1.96 * res['attacker_win_se']:.3f} over {res['n']}, {res['secs']} s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
