"""What an ordered pilot does in an even deathmatch's first 30 seconds, and whether the
cost is the script's target choice or following any order. Run from the repo root:

    PYTHONPATH=. .venv/bin/python lab/runs/2026-11-17-order-cost/order_rules.py \
        --rule scripted --k 2 --blocks 24 --out lab/runs/2026-11-17-order-cost/out/k2_scripted.json

One side (the "ordered" side) gets orders its pilots see, from one of these rules; the
other side is always the eval's ``unseen`` side (the scripted commander, its orders
hidden from its own pilots). The same pilots fly both sides, drawn ship by ship from
``--pilots``, or every ship by the one pilot ``--checkpoint`` names; every rule plays
the same seeds and rosters (and, for one pilot list, the same pilot draws), so scores
pair match by match across rules and across pilots. One pilot, e.g. a learner's
checkpoint:

    PYTHONPATH=. .venv/bin/python lab/runs/2026-11-17-order-cost/order_rules.py \
        --rule nearest --k 3 --checkpoint <ckpt.pt> --out k3_nearest.json

Rules for the ordered side (all attack orders, given on the sim's slow tick, every 2 s
from t = 2 s):

- ``scripted``: the sim's scripted commander (half the fleet on the enemy nearest
  its centroid, half on the most damaged enemy within 300 m; both sticky).
- ``nearest``: every ship its own squad, ordered onto the enemy nearest *it*,
  re-chosen every decision (no stickiness).
- ``focus``: the whole side one squad, on the enemy nearest the side's centroid,
  kept until it dies.
- ``near250``: as ``nearest``, but a ship whose nearest enemy is farther than 250 m
  gets no order (the order only once the fight has reached it).
- ``none``: an external commander that gives no orders (a control: should be 0.50).

Go-to and defend rules (added 2026-11-19, lab/runs/2026-11-19-order-kinds; the rules
above are unchanged). A go-to is issued once, at the first slow tick, to the whole side
as one squad, and never re-sent: it completes ship by ship on arrival (or, with a
deadline, on a miss), and from then on the ship's effective order is none, which is
exactly what a ship with no order sees (SIM_SPEC §0.4 row 2, §0.6 row 3). The squad's
standing order stays a go-to; nothing a pilot reads shows it.

- ``goto_front``: go to the midpoint of the two fleets' centroids (radius
  ``GOTO_RADIUS`` = 60 m, the learned commander's), no deadline.
- ``goto_front_deadline``: the same, with a v8 deadline: ``GOTO_SLACK`` (2) times the
  slowest ship's straight-line time to the circle at its speed cap, plus 3 s (the tight
  end of the drills' 2 to 8 times).
- ``goto_rally``: go to a point ``RALLY_BACK_M`` (120 m) behind the side's own
  centroid, away from the enemy's (radius 60 m), no deadline: regroup, then fight.
- ``defend_ward``: one ship is the ward (no order), the others one squad defending it.
  The ward is the ship nearest the side's centroid when first chosen, kept until it
  dies; then the survivor nearest the survivors' centroid, while two are left.
- ``defend_ring``: every ship its own squad, defending the next live ship in slot order
  (two left: each other; one: no order). Every ship is ordered, as under ``nearest``.

Rosters are even k v k of one hull (fighter, strafer, gunship; 8 rosters each, as in
the commander-3 ``DUELS`` runs), each played with the ordered side on team 0 and on
team 1.

Telemetry over the first ``--window`` seconds (default 30), per strike craft, split by
side: time with its ordered target / a non-target enemy in its gun arc, distances,
damage taken and dealt split by whether the other ship is its target, and how the
first ship lost in each match died. A ship's "target" is its standing attack order's
target as the sim tracks it (``order_tracks``); on the unseen side that is the order
the script computed and hid, which its pilots never saw, so the unseen side's numbers
show what a pilot does about that enemy when it was not told to.

Gun arc: fighter and strafer have one fixed nose gun, so "in arc" is within
``NOSE_DEG`` of the nose and inside the gun's range (gauss 220 m, laser 180 m). The
gunship's turrets cover nearly all round, so for it "in arc" is inside 230 m.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import rlf_sim
import torch

from spacefight.commander.eval import ASSETS, TICK_HZ
from spacefight.commander.pilots import PilotStable, live_pilot_checkpoints
from spacefight.env.rosters import SCRIPTED, Roster
from spacefight.env.rust_env import RustVecEnv

EXTERNAL = "external"
HULLS = ("fighter", "strafer", "gunship")
NOSE_DEG = 10.0
GUN_RANGE = {"fighter": 220.0, "strafer": 180.0, "gunship": 230.0}
NOSE_ONLY = {"fighter": True, "strafer": True, "gunship": False}
BIN_S = 2
RULES = (
    "scripted",
    "nearest",
    "focus",
    "none",
    "near250",
    "goto_front",
    "goto_front_deadline",
    "goto_rally",
    "defend_ward",
    "defend_ring",
)
NEAR_ORDER_M = 250.0
GOTO_RADIUS = 60.0
GOTO_SLACK = 2.0
GOTO_EXTRA_S = 3.0
RALLY_BACK_M = 120.0
SPEED_CAP = {"fighter": 60.0, "strafer": 50.0, "gunship": 24.0}
# The sim's defend threat set (order module): an enemy within its reach plus
# THREAT_MARGIN of the ward, or one that hit the ward in the last RECENT_HIT_TICKS.
# Approximated here with GUN_RANGE as the reach and no bound radius.
THREAT_MARGIN = 40.0
RECENT_HIT_TICKS = 150
DEFAULT_PILOTS = Path("lab/runs/2026-11-15-commander-3/pilots_followers.json")


def wrap(a: np.ndarray) -> np.ndarray:
    return (a + np.pi) % (2 * np.pi) - np.pi


def first_step(record: np.ndarray, now: np.ndarray, step: int) -> None:
    """Set ``record`` (−1 = not yet) to ``step`` where ``now`` holds for the first time."""
    record[(record < 0) & now] = step


class ExternalRule:
    """Orders for one team of every match, from positions (``render_state``)."""

    def __init__(self, rule: str, n: int) -> None:
        self.rule = rule
        self.focus = np.full(n, -1, dtype=np.int64)
        self.issued = np.zeros(n, dtype=bool)  # go-to rules: the one go-to is sent
        self.ward = np.full(n, -1, dtype=np.int64)  # defend_ward: the current ward

    def commands(self, i: int, team: int, ships: list[dict], tick: int = 0) -> list[dict]:
        own = [s for s in ships if s["team"] == team and s["alive"]]
        foes = [s for s in ships if s["team"] != team and s["alive"]]
        if self.rule == "none" or not own or not foes:
            return []
        if self.rule.startswith("goto_"):
            return self.goto(i, own, foes, tick)
        if self.rule == "defend_ward":
            return self.defend_ward(i, own)
        if self.rule == "defend_ring":
            return self.defend_ring(own)
        if self.rule in ("nearest", "near250"):
            out = []
            for k, s in enumerate(sorted(own, key=lambda s: s["slot"])):
                p = np.asarray(s["pos"])
                t = min(foes, key=lambda f: (np.hypot(*(np.asarray(f["pos"]) - p)), f["slot"]))
                far = np.hypot(*(np.asarray(t["pos"]) - p)) > NEAR_ORDER_M
                order = (
                    {"kind": "none"}
                    if self.rule == "near250" and far
                    else {"kind": "attack", "target": int(t["slot"])}
                )
                out.append(
                    {"kind": "squad", "squad": k, "members": [s["slot"]], "order": order}
                )
            # Squads of ships that died are emptied by the sim; unused squads stay empty.
            return out
        if self.rule == "focus":
            alive = {f["slot"] for f in foes}
            if self.focus[i] not in alive:
                c = np.mean([s["pos"] for s in own], axis=0)
                t = min(foes, key=lambda f: (np.hypot(*(np.asarray(f["pos"]) - c)), f["slot"]))
                self.focus[i] = t["slot"]
            return [
                {
                    "kind": "squad",
                    "squad": 0,
                    "members": sorted(int(s["slot"]) for s in own),
                    "order": {"kind": "attack", "target": int(self.focus[i])},
                }
            ]
        raise ValueError(self.rule)

    def goto(self, i: int, own: list[dict], foes: list[dict], tick: int) -> list[dict]:
        """The side's one go-to, sent once (module docs); nothing after it."""
        if self.issued[i]:
            return []
        self.issued[i] = True
        c_own = np.mean([s["pos"] for s in own], axis=0)
        c_foe = np.mean([s["pos"] for s in foes], axis=0)
        if self.rule in ("goto_front", "goto_front_deadline"):
            point = (c_own + c_foe) / 2
        elif self.rule == "goto_rally":
            away = c_own - c_foe
            point = c_own + away / max(float(np.hypot(*away)), 1e-6) * RALLY_BACK_M
        else:
            raise ValueError(self.rule)
        order = {"kind": "goto", "point": [float(point[0]), float(point[1])], "radius": GOTO_RADIUS}
        if self.rule == "goto_front_deadline":
            secs = max(
                max(float(np.hypot(*(np.asarray(s["pos"]) - point))) - GOTO_RADIUS, 0.0)
                / SPEED_CAP[s["hull"]]
                for s in own
            )
            order["deadline"] = int(tick + math.ceil((GOTO_SLACK * secs + GOTO_EXTRA_S) * TICK_HZ))
        members = sorted(int(s["slot"]) for s in own)
        return [{"kind": "squad", "squad": 0, "members": members, "order": order}]

    def defend_ward(self, i: int, own: list[dict]) -> list[dict]:
        """One ward (no squad), every other live ship in squad 0 defending it."""
        alive = {int(s["slot"]) for s in own}
        if self.ward[i] not in alive:
            c = np.mean([s["pos"] for s in own], axis=0)
            w = min(own, key=lambda s: (np.hypot(*(np.asarray(s["pos"]) - c)), s["slot"]))
            self.ward[i] = int(w["slot"])
        ward = int(self.ward[i])
        defenders = sorted(alive - {ward})
        order = {"kind": "defend", "ward": ward} if defenders else {"kind": "none"}
        return [{"kind": "squad", "squad": 0, "members": defenders, "order": order}]

    @staticmethod
    def defend_ring(own: list[dict]) -> list[dict]:
        """Each live ship its own squad, defending the next live ship in slot order."""
        slots = sorted(int(s["slot"]) for s in own)
        out = []
        for k, s in enumerate(slots):
            nxt = slots[(k + 1) % len(slots)]
            order = {"kind": "defend", "ward": nxt} if nxt != s else {"kind": "none"}
            out.append({"kind": "squad", "squad": k, "members": [s], "order": order})
        # As for ``nearest``: a squad past the live count held only ships now dead.
        return out


def run(args: argparse.Namespace) -> dict:
    k = args.k
    rosters = [Roster.of([h] * k, [h] * k) for h in HULLS for _ in range(8)]
    n = 2 * len(rosters) * args.blocks
    index = np.arange(n)
    entry = index % len(rosters)
    ord_team = (index // len(rosters)) % 2  # the team the ordered side has
    time_limit = float(rlf_sim.mission_time_limit_s("deathmatch"))
    env = RustVecEnv(
        ASSETS,
        n,
        rosters[0].fleets(),
        args.seed,
        n_threads=args.threads,
        reaction_ticks=2,
        max_ships=20,
        commanders=(SCRIPTED, SCRIPTED),
    )
    ord_mode = SCRIPTED if args.rule == "scripted" else EXTERNAL
    for i in range(n):
        modes = [SCRIPTED, SCRIPTED]
        modes[ord_team[i]] = ord_mode
        hide = [True, True]
        hide[ord_team[i]] = False
        env.set_next_roster(
            i,
            Roster(rosters[entry[i]].teams, "deathmatch", tuple(modes)),
            time_limit_s=time_limit,
            hide_orders=tuple(hide),
        )
    env.reset()
    if args.checkpoint:
        ckpt = Path(args.checkpoint)
        if not ckpt.is_file():
            raise FileNotFoundError(f"no checkpoint at {ckpt}")
        pilots = [(args.name or ckpt.stem, ckpt)]
        if args.unseen_checkpoint:
            uckpt = Path(args.unseen_checkpoint)
            if not uckpt.is_file():
                raise FileNotFoundError(f"no checkpoint at {uckpt}")
            pilots.append((args.unseen_name or uckpt.stem, uckpt))
    elif args.unseen_checkpoint:
        raise ValueError("--unseen-checkpoint needs --checkpoint")
    else:
        pilots = live_pilot_checkpoints(Path(args.pilots))
    stable = PilotStable(pilots, n, env.n_ships, args.seed + 1, ASSETS)
    stable.draw(env, range(n))
    assign = stable.assign.copy()
    strike = stable.strike_mask(env).copy()
    team = np.asarray(env.team).copy()
    S = env.n_ships
    side = np.where(team == ord_team[:, None], 0, 1)  # 0 ordered, 1 unseen
    side[~strike] = -1
    if args.unseen_checkpoint:
        # Pilot 0 flies every ordered strike craft, pilot 1 every unseen one: an
        # ordered learner measured against a fixed free pilot, not against itself.
        stable.assign[side == 0] = 0
        stable.assign[side == 1] = 1
        assign = stable.assign.copy()
    hull_name = np.empty((n, S), dtype=object)
    rule = ExternalRule(args.rule, n)
    torch.manual_seed(args.seed)

    win_ticks = int(args.window * TICK_HZ)
    max_steps = int(time_limit * TICK_HZ) + 4
    running = np.ones(n, dtype=bool)
    winner = np.full(n, -2, dtype=np.int64)
    end_tick = np.zeros(n, dtype=np.int64)

    # Per-ship accumulators over the window, [n, S].
    z = lambda: np.zeros((n, S))  # noqa: E731
    acc = {
        name: z()
        for name in (
            "alive_s",
            "ordered_s",  # under an attack order
            "tgt_arc_s",
            "other_arc_s",
            "any_arc_s",
            "tgt_nearest_s",  # its target is the nearest enemy
            "dist_tgt_sum",
            "dist_other_sum",
            "dist_near_sum",
            "taken_tgt",
            "taken_other",
            "taken_rear",  # from shooters behind its beam (bearing > 90 deg off nose)
            "dealt_tgt",
            "dealt_other",
            "taken",
            "dealt",
            "lost",
            "speed_sum",  # |v| per tick
            "advance_m",  # metres flown toward the enemy fleet's centroid
            "cohesion_sum",  # m to its own side's centroid, per tick
            "trigger_s",  # any gun's trigger held
            "trigger_arc_s",  # held with an enemy in arc
            "hits_dealt",
            "hit_range_sum",  # m from shooter to target, per hit dealt
            "retreat_s",  # moving away from the enemy fleet faster than 5 m/s
            "backpedal_s",  # ... with its nose within 30 deg of its nearest enemy
            "nose_near_s",  # nose within 30 deg of its nearest enemy (any motion)
            "advance_tgt_m",  # metres flown toward its own target
        )
    }
    n_bins = int(args.window // BIN_S)
    # [side, bin] timeline: ship-seconds alive, advance, damage dealt, in-arc seconds,
    # and per match the centroid gap.
    tl = {
        key: np.zeros((2, n_bins))
        for key in ("alive_s", "advance_m", "dealt", "any_arc_s", "lost", "trigger_s")
    }
    gap_sum = np.zeros(n_bins)
    gap_n = np.zeros(n_bins)
    first_hit = np.full((n, 2), -1)  # tick each side first landed damage
    # First ship lost in each match (window or not).
    first = {
        "tick": np.full(n, -1),
        "victim": np.full(n, -1),
        "killer": np.full(n, -1),
        "victim_target": np.full(n, -1),
        "killer_target": np.full(n, -1),
        "tgt_off_deg": np.full(n, np.nan),  # victim's nose to its target at death
        "killer_bearing_deg": np.full(n, np.nan),  # killer off the victim's nose
        "dist_tgt": np.full(n, np.nan),
        "dist_killer": np.full(n, np.nan),
        "tgt_arc_last2s": np.full(n, np.nan),  # share of its last 2 s with target in arc
        "attackers_last3s": np.full(n, -1),  # distinct enemies that hit it in its last 3 s
    }
    # Rolling state for the first-death record.
    tgt_arc_hist = np.zeros((n, S, 2 * TICK_HZ), dtype=bool)
    last_hit_tick = np.full((n, S, S), -10_000)  # [i, victim, shooter]
    last_hitter = np.full((n, S), -1)

    # Whole-match per-ship steps (−1 = never): the first step under a standing go-to,
    # arrived in time, missed its deadline; the first under any effective order, and
    # the first with none again after it (the order spent); and its death.
    order_t = {
        key: np.full((n, S), -1, dtype=np.int64)
        for key in ("goto_start", "goto_arrive", "goto_miss", "order_start", "order_spent", "death")
    }
    pos = np.zeros((n, S, 2))
    vel = np.zeros((n, S, 2))
    head = np.zeros((n, S))
    alive = np.zeros((n, S), dtype=bool)
    for i in range(n):
        for s in env.raw.render_state(i)["ships"]:
            hull_name[i, s["slot"]] = s["hull"]
    nose = np.vectorize(lambda h: NOSE_ONLY.get(h, False) if h else False)(hull_name)
    rng_ = np.vectorize(lambda h: GUN_RANGE.get(h, 0.0) if h else 0.0)(hull_name)

    t0 = time.time()
    for step in range(max_steps):
        in_window = step < win_ticks
        rows = np.flatnonzero(running)
        due = np.asarray(env.raw.command_due())
        if True:
            for i in rows:
                rs = env.raw.render_state(int(i))
                ships = rs["ships"]
                for s in ships:
                    j = s["slot"]
                    pos[i, j] = s["pos"]
                    head[i, j] = s["heading"]
                    vel[i, j] = s["vel"]
                    alive[i, j] = s["alive"]
                if ord_mode == EXTERNAL and due[i]:
                    cmds = rule.commands(int(i), int(ord_team[i]), ships, int(rs["tick"]))
                    if cmds:
                        env.raw.submit_command(int(i), int(ord_team[i]), cmds)
        tracks = env.order_tracks()
        kind = np.asarray(tracks["standing_kind"]).astype(np.int64)
        target = np.asarray(tracks["target"]).astype(np.int64)
        # Go-to and defend telemetry (2026-11-19): what the order kinds' ships see.
        eff = np.asarray(tracks["effective_kind"]).astype(np.int64)
        ward = np.where(eff == 2, target, -1)
        target = np.where(kind == 1, target, -1)
        alive_before = alive.copy()
        on = running[:, None] & strike & alive
        goto_now = on & (kind == 3)
        arr_now = goto_now & np.asarray(tracks["arrived"]) & ~np.asarray(tracks["missed"])
        miss_now = goto_now & np.asarray(tracks["missed"])
        first_step(order_t["goto_start"], goto_now, step)
        first_step(order_t["goto_arrive"], arr_now, step)
        first_step(order_t["goto_miss"], miss_now, step)
        first_step(order_t["order_start"], on & (eff != 0), step)
        had_order = order_t["order_start"] >= 0
        first_step(order_t["order_spent"], on & had_order & (eff == 0), step)

        if in_window:
            live = running[:, None] & strike & alive  # [n, S]
            # Pairwise geometry: d[i, a, b] from a to b.
            rel = pos[:, None, :, :] - pos[:, :, None, :]
            dist = np.hypot(rel[..., 0], rel[..., 1])
            bearing = np.arctan2(rel[..., 1], rel[..., 0])
            off = np.abs(wrap(bearing - head[:, :, None]))  # off a's nose toward b
            enemy = (team[:, :, None] != team[:, None, :]) & strike[:, None, :] & alive[:, None, :]
            enemy &= live[:, :, None]
            in_rng = dist <= rng_[:, :, None]
            in_arc = in_rng & np.where(nose[:, :, None], off <= math.radians(NOSE_DEG), True)
            in_arc &= enemy
            is_tgt = np.zeros((n, S, S), dtype=bool)
            ti, tj = np.nonzero(target >= 0)
            is_tgt[ti, tj, target[ti, tj]] = True
            is_tgt &= enemy
            has_tgt = is_tgt.any(axis=2)
            other = enemy & ~is_tgt
            dt = 1.0 / TICK_HZ
            acc["alive_s"] += live * dt
            acc["ordered_s"] += (live & has_tgt) * dt
            tgt_arc = (in_arc & is_tgt).any(axis=2)
            acc["tgt_arc_s"] += tgt_arc * dt
            acc["other_arc_s"] += (in_arc & other).any(axis=2) * dt
            acc["any_arc_s"] += in_arc.any(axis=2) * dt
            dmask = np.where(enemy, dist, np.inf)
            near = dmask.min(axis=2)
            nearest = dmask.argmin(axis=2)
            tgt_d = np.where(is_tgt, dist, np.inf).min(axis=2)
            oth_d = np.where(other, dist, np.inf).min(axis=2)
            ok_t = live & has_tgt & np.isfinite(tgt_d)
            acc["dist_tgt_sum"] += np.where(ok_t, tgt_d, 0)
            ok_o = live & has_tgt & np.isfinite(oth_d)
            acc["dist_other_sum"] += np.where(ok_o, oth_d, 0)
            acc["dist_near_sum"] += np.where(live & np.isfinite(near), near, 0)
            acc["tgt_nearest_s"] += (ok_t & (nearest == np.where(has_tgt, target, -2))) * dt
            if "ok_t_s" not in acc:
                acc["ok_t_s"] = z()
                acc["ok_o_s"] = z()
            acc["ok_t_s"] += ok_t * dt
            acc["ok_o_s"] += ok_o * dt
            tgt_arc_hist[:, :, step % (2 * TICK_HZ)] = tgt_arc
            # Fleet geometry: each side's centroid over its live strike craft.
            cent = np.zeros((n, 2, 2))
            cnt = np.zeros((n, 2))
            for sd in (0, 1):
                m = live & (side == sd)
                cnt[:, sd] = m.sum(axis=1)
                cent[:, sd] = (pos * m[..., None]).sum(axis=1) / np.maximum(cnt[:, sd], 1)[:, None]
            my_c = np.where((side == 0)[..., None], cent[:, None, 0], cent[:, None, 1])
            foe_c = np.where((side == 0)[..., None], cent[:, None, 1], cent[:, None, 0])
            to_foe = foe_c - pos
            to_foe /= np.maximum(np.hypot(to_foe[..., 0], to_foe[..., 1]), 1e-6)[..., None]
            adv = (vel * to_foe).sum(axis=2)
            acc["speed_sum"] += np.where(live, np.hypot(vel[..., 0], vel[..., 1]), 0)
            acc["advance_m"] += np.where(live, adv, 0) * dt
            near_off = np.take_along_axis(off, nearest[..., None], axis=2)[..., 0]
            nose_on = live & np.isfinite(near) & (near_off <= math.radians(30))
            retreat = live & (adv < -5.0)
            acc["retreat_s"] += retreat * dt
            acc["backpedal_s"] += (retreat & nose_on) * dt
            acc["nose_near_s"] += nose_on * dt
            tj = np.clip(target, 0, S - 1)
            to_t = np.take_along_axis(pos, tj[..., None].repeat(2, axis=2), axis=1) - pos
            to_t /= np.maximum(np.hypot(to_t[..., 0], to_t[..., 1]), 1e-6)[..., None]
            acc["advance_tgt_m"] += np.where(ok_t, (vel * to_t).sum(axis=2), 0) * dt
            acc["cohesion_sum"] += np.where(live, np.hypot(*(pos - my_c).transpose(2, 0, 1)), 0)
            bn = step // (BIN_S * TICK_HZ)
            for sd in (0, 1):
                m = live & (side == sd)
                tl["alive_s"][sd, bn] += m.sum() * dt
                tl["advance_m"][sd, bn] += (adv * m).sum() * dt
                tl["any_arc_s"][sd, bn] += (in_arc.any(axis=2) & m).sum() * dt
            both = running & (cnt > 0).all(axis=1)
            gap_sum[bn] += np.hypot(*(cent[both, 0] - cent[both, 1]).T).sum()
            gap_n[bn] += both.sum()
            # Order kinds (2026-11-19): time under each effective kind, distance to the
            # ward, and time / damage as a ward (a ship some live ally defends).
            for name in (
                "eff_ordered_s",
                "goto_s",
                "defend_s",
                "ward_s",
                "dist_ward_sum",
                "ward_taken",
                "ward_lost",
                "dealt_threat",
                "dealt_nonthreat",
            ):
                acc.setdefault(name, z())
            acc["eff_ordered_s"] += (live & (eff != 0)) * dt
            acc["goto_s"] += (live & (eff == 3)) * dt
            acc["defend_s"] += (live & (eff == 2)) * dt
            wj = np.clip(ward, 0, S - 1)
            ward_d = np.take_along_axis(dist, wj[..., None], axis=2)[..., 0]
            acc["dist_ward_sum"] += np.where(live & (ward >= 0), ward_d, 0)
            is_ward = np.zeros((n, S), dtype=bool)
            wi, ws = np.nonzero(live & (ward >= 0))
            is_ward[wi, ward[wi, ws]] = True
            acc["ward_s"] += (is_ward & live) * dt

        acts = stable.actions(env)
        if in_window:
            trig = (acts[..., 14:20] > 0).any(axis=2) & live
            acc["trigger_s"] += trig * dt
            acc["trigger_arc_s"] += (trig & in_arc.any(axis=2)) * dt
            for sd in (0, 1):
                tl["trigger_s"][sd, bn] += (trig & (side == sd)).sum() * dt
        _, _, dones, info = env.step(acts)
        hc = np.asarray(env.raw.hit_count)
        hits = np.asarray(env.raw.hits)
        for i in np.flatnonzero(running & (hc > 0)):
            for h in hits[i, : hc[i]]:
                sh, tg, dmg = int(h[0]), int(h[1]), h[3] / 1000.0
                if not (0 <= sh < S and 0 <= tg < S) or team[i, sh] == team[i, tg]:
                    continue
                last_hit_tick[i, tg, sh] = step
                last_hitter[i, tg] = sh
                if first_hit[i, side[i, sh]] < 0 and side[i, sh] >= 0:
                    first_hit[i, side[i, sh]] = step
                if in_window:
                    acc["hits_dealt"][i, sh] += 1
                    acc["hit_range_sum"][i, sh] += float(np.hypot(*(pos[i, sh] - pos[i, tg])))
                    if side[i, sh] >= 0:
                        tl["dealt"][side[i, sh], bn] += dmg
                    acc["taken"][i, tg] += dmg
                    acc["dealt"][i, sh] += dmg
                    if target[i, tg] == sh:
                        acc["taken_tgt"][i, tg] += dmg
                    else:
                        acc["taken_other"][i, tg] += dmg
                    if target[i, sh] == tg:
                        acc["dealt_tgt"][i, sh] += dmg
                    else:
                        acc["dealt_other"][i, sh] += dmg
                    b = math.atan2(*(pos[i, sh] - pos[i, tg])[::-1])
                    if abs(wrap(np.asarray(b - head[i, tg]))) > math.pi / 2:
                        acc["taken_rear"][i, tg] += dmg
                    if is_ward[i, tg]:
                        acc["ward_taken"][i, tg] += dmg
                    w = int(ward[i, sh])
                    if w >= 0:  # a defender's hit: on the ward's threat set (approx.)?
                        near = float(np.hypot(*(pos[i, tg] - pos[i, w])))
                        threat = near <= GUN_RANGE[hull_name[i, tg]] + THREAT_MARGIN or (
                            last_hit_tick[i, w, tg] >= step - RECENT_HIT_TICKS
                        )
                        acc["dealt_threat" if threat else "dealt_nonthreat"][i, sh] += dmg
        # Deaths this step, from the env's alive buffer (the finished match on a done).
        alive_now = np.asarray(env.raw.alive).copy()
        died = running[:, None] & strike & alive_before & ~alive_now
        first_step(order_t["death"], died, step)
        if in_window:
            acc["lost"] += died
            acc["ward_lost"] += died & is_ward
            for sd in (0, 1):
                tl["lost"][sd, bn] += (died & (side == sd)).sum()
        for i in np.flatnonzero(died.any(axis=1)):
            if first["tick"][i] >= 0:
                continue
            v = int(np.flatnonzero(died[i])[0])
            kl = int(last_hitter[i, v])
            first["tick"][i] = step
            first["victim"][i] = v
            first["killer"][i] = kl
            first["victim_target"][i] = target[i, v]
            if kl >= 0:
                first["killer_target"][i] = target[i, kl]
                d = pos[i, kl] - pos[i, v]
                first["killer_bearing_deg"][i] = math.degrees(
                    abs(float(wrap(np.asarray(math.atan2(d[1], d[0]) - head[i, v]))))
                )
                first["dist_killer"][i] = float(np.hypot(*d))
            t = target[i, v]
            if t >= 0:
                d = pos[i, t] - pos[i, v]
                first["tgt_off_deg"][i] = math.degrees(
                    abs(float(wrap(np.asarray(math.atan2(d[1], d[0]) - head[i, v]))))
                )
                first["dist_tgt"][i] = float(np.hypot(*d))
                if step < win_ticks:
                    first["tgt_arc_last2s"][i] = float(tgt_arc_hist[i, v].mean())
            first["attackers_last3s"][i] = int(
                (last_hit_tick[i, v] >= step - 3 * TICK_HZ).sum()
            )
        alive = alive_now
        ending = running & dones
        winner[ending] = np.asarray(info.winner)[ending]
        end_tick[ending] = step + 1
        running &= ~dones
        if not running.any():
            break
    else:
        raise RuntimeError("matches did not end")
    secs = time.time() - t0

    score = (winner == ord_team) + 0.5 * (winner == -1)
    out = {
        "schema": "rlf.order_cost.rules/1",
        "rule": args.rule,
        "k": k,
        "n": n,
        "seed": args.seed,
        "window_s": args.window,
        "pilots": [p for p, _ in pilots],
        "checkpoints": [str(c) for _, c in pilots],
        "secs": round(secs, 1),
        "score": float(score.mean()),
        "score_se": float(score.std(ddof=1) / math.sqrt(n)),
        "draws": int((winner == -1).sum()),
        "score_by_hull": {
            h: float(score[np.asarray([rosters[e].teams[0][0] == h for e in entry])].mean())
            for h in HULLS
        },
    }
    # Per-match arrays, so the analysis can pair rules match by match.
    out["per_match"] = {
        "score": score.tolist(),
        "ord_team": ord_team.tolist(),
        "hull": [rosters[e].teams[0][0] for e in entry],
        "end_tick": end_tick.tolist(),
        "first": {key: np.asarray(v).tolist() for key, v in first.items()},
        "first_victim_side": [
            int(side[i, first["victim"][i]]) if first["victim"][i] >= 0 else -1
            for i in range(n)
        ],
        "first_killer_side": [
            int(side[i, first["killer"][i]]) if first["killer"][i] >= 0 else -1
            for i in range(n)
        ],
    }
    sides = {}
    for sd, name in ((0, "ordered"), (1, "unseen")):
        m = side == sd
        tot = {key: float(v[m].sum()) for key, v in acc.items()}
        sides[name] = tot
        # Per pilot id: same sums, for the followers' differences.
        sides[name]["by_pilot"] = {
            pid: {key: float(v[m & (assign == p)].sum()) for key, v in acc.items()}
            for p, pid in enumerate(stable.ids)
        }
        sides[name]["ships"] = int(m.sum())
    out["sides"] = sides
    out["timeline"] = {
        "bin_s": BIN_S,
        **{key: v.tolist() for key, v in tl.items()},
        "centroid_gap": (gap_sum / np.maximum(gap_n, 1)).tolist(),
    }
    out["per_match"]["first_hit"] = first_hit.tolist()
    out["per_match"]["side"] = side.tolist()
    out["per_match"]["order_steps"] = {key: v.tolist() for key, v in order_t.items()}
    out["orders"] = order_summary(order_t, side, end_tick)
    return out


def order_summary(order_t: dict, side: np.ndarray, end_tick: np.ndarray) -> dict:
    """Per side, whole match: how the go-to and the order as a whole ended, ship by ship.

    Times are seconds from the step the ship's go-to (or first effective order) began.
    """
    out = {}
    for sd, name in ((0, "ordered"), (1, "unseen")):
        m = side == sd
        go = m & (order_t["goto_start"] >= 0)
        arr = go & (order_t["goto_arrive"] >= 0)
        miss = go & (order_t["goto_miss"] >= 0)
        dead = order_t["death"] >= 0
        open_ = go & ~arr & ~miss
        t_arr = (order_t["goto_arrive"] - order_t["goto_start"])[arr] / TICK_HZ
        od = m & (order_t["order_start"] >= 0)
        spent = od & (order_t["order_spent"] >= 0)
        t_spent = (order_t["order_spent"] - order_t["order_start"])[spent] / TICK_HZ
        quant = lambda a: [float(np.quantile(a, q)) for q in (0.25, 0.5, 0.75)] if a.size else []  # noqa: E731
        out[name] = {
            "ships": int(m.sum()),
            "goto_ships": int(go.sum()),
            "arrived": int(arr.sum()),
            "missed": int(miss.sum()),
            "died_before_end_of_goto": int((open_ & dead).sum()),
            "goto_open_at_match_end": int((open_ & ~dead).sum()),
            "arrive_s_mean": float(t_arr.mean()) if t_arr.size else None,
            "arrive_s_quartiles": quant(t_arr),
            "ordered_ships": int(od.sum()),
            "spent": int(spent.sum()),
            "spent_s_mean": float(t_spent.mean()) if t_spent.size else None,
            "spent_s_quartiles": quant(t_spent),
            "match_s_mean": float(end_tick.mean() / TICK_HZ),
        }
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rule", choices=RULES, required=True)
    p.add_argument("--k", type=int, default=2)
    p.add_argument("--blocks", type=int, default=24)
    p.add_argument("--seed", type=int, default=20261117)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--window", type=float, default=30.0)
    p.add_argument("--pilots", default=str(DEFAULT_PILOTS))
    p.add_argument(
        "--checkpoint", help="one pilot flies every ship (instead of --pilots)"
    )
    p.add_argument("--name", help="its id in the output (default: the file's stem)")
    p.add_argument(
        "--unseen-checkpoint",
        help="with --checkpoint: this pilot flies the unseen side instead",
    )
    p.add_argument("--unseen-name", help="its id in the output")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(args.threads)
    res = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(res) + "\n")
    print(
        f"{args.rule} k={args.k}: ordered side {res['score']:.3f} +- {1.96 * res['score_se']:.3f}"
        f" over {res['n']} ({res['draws']} draws), {res['secs']} s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
