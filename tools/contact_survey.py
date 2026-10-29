"""Survey ship-ship contacts in duels: how often, how fast, which side of each ship.

Plays ``n`` duels like ``spacefight.eval.duel`` and, after every tick, reads each
running match's ``render_state``. A tick is a *contact* when any pair of collision
circles of the two ships is within ``TOUCH_EPS`` of touching (the sim's positional
correction leaves the deepest pair exactly touching). A contact *event* is the first
contact tick after a non-contact tick; its closing speed is the relative velocity
along the centre line on the tick before, and its bearing on each ship is the other
ship's direction in that ship's body frame (0° = nose).

From SIM_VERSION 3 it also reports the sim's own damaging collisions: ``Collision``
events per match, the collision share of hull damage, and *crash deaths* (a ship
that dies on a step where it took collision damage).

    python tools/contact_survey.py --a lab/.../ppo_bc_1200.pt --b script --n 128
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from spacefight.eval import features as F
from spacefight.eval.controllers import Controller, make_controller
from spacefight.eval.duel import ASSETS, TICK_HZ, EvalConfig, _Tracker
from spacefight.env.rust_env import RustVecEnv

TOUCH_EPS = 0.05  # m
NEAR_M = (10.0, 20.0, 40.0)


def hull_circles(name: str) -> list[tuple[float, float, float]]:
    """Collision circles ``(x, y, r)`` of a hull, body frame (SIM_SPEC §4)."""
    import yaml

    raw = yaml.safe_load((ASSETS / "hulls" / name / "hull.yaml").read_text())
    return [(c["pos"][0], c["pos"][1], c["r"]) for c in raw["collision"]]


def to_world(ship: dict, x: float, y: float) -> tuple[float, float]:
    c, s = math.cos(ship["heading"]), math.sin(ship["heading"])
    px, py = ship["pos"]
    return px + c * x - s * y, py + s * x + c * y


def min_gap(a: dict, b: dict, ca: list, cb: list) -> float:
    """Smallest surface gap over all collision-circle pairs (negative = overlap)."""
    best = math.inf
    for ax, ay, ar in ca:
        wa = to_world(a, ax, ay)
        for bx, by, br in cb:
            wb = to_world(b, bx, by)
            best = min(best, math.dist(wa, wb) - ar - br)
    return best


def bearing_deg(me: dict, other: dict) -> float:
    """The other ship's bearing in ``me``'s body frame, degrees in (-180, 180]."""
    dx, dy = other["pos"][0] - me["pos"][0], other["pos"][1] - me["pos"][1]
    ang = math.atan2(dy, dx) - me["heading"]
    return math.degrees(math.atan2(math.sin(ang), math.cos(ang)))


def survey(a: Controller, b: Controller, n: int, seed: int) -> dict:
    cfg = EvalConfig(n=n, seed=seed)
    env = RustVecEnv(
        ASSETS,
        cfg.n,
        [list(t) for t in cfg.fleets],
        cfg.seed,
        arena_radius=cfg.arena_radius,
        time_limit_s=cfg.time_limit_s,
        n_threads=12,
        record_events=True,
        reaction_ticks=cfg.reaction_ticks,
    )
    a.reset(cfg.seed)
    b.reset(cfg.seed + 1)
    tracker = _Tracker(env, cfg)
    raw = env.raw
    first = raw.render_state(0)["ships"]
    circles = [hull_circles(s["hull"]) for s in first]
    prev: list[dict | None] = [None] * n
    in_contact = np.zeros(n, bool)
    contact_ticks = np.zeros(n, np.int64)
    live_ticks = np.zeros(n, np.int64)
    near_ticks = {d: np.zeros(n, np.int64) for d in NEAR_M}
    events: list[dict] = []
    crash_deaths = np.zeros(n, np.int64)
    max_steps = int(round(cfg.time_limit_s * TICK_HZ)) + 1
    for _ in range(max_steps):
        was_running = tracker.running.copy()
        actions = tracker.choose(env, a, b)
        _, _, dones, info = env.step(actions)
        tracker.observe(
            env,
            dones.copy(),
            info.winner,
            info.hits,
            info.hit_count,
            info.collision_damage,
        )
        sim_events = env.events()
        deaths = sim_events[sim_events[:, F.EV_KIND] == F.KIND_DEATH]
        for row in deaths:
            i, slot = int(row[F.EV_MATCH]), int(row[F.EV_A])
            if was_running[i] and info.collision_damage[i, slot] > 0:
                crash_deaths[i] += 1
        for i in np.flatnonzero(was_running & ~dones):
            ships = raw.render_state(int(i))["ships"]
            sa, sb = ships[0], ships[1]
            if not (sa["alive"] and sb["alive"] and sa["present"] and sb["present"]):
                prev[i] = None
                continue
            live_ticks[i] += 1
            dist = math.dist(sa["pos"], sb["pos"])
            for d in NEAR_M:
                near_ticks[d][i] += dist < d
            touching = min_gap(sa, sb, circles[0], circles[1]) < TOUCH_EPS
            contact_ticks[i] += touching
            if touching and not in_contact[i] and prev[i] is not None:
                pa, pb = prev[i]
                rx, ry = pb["pos"][0] - pa["pos"][0], pb["pos"][1] - pa["pos"][1]
                r = math.hypot(rx, ry) or 1.0
                vx, vy = pb["vel"][0] - pa["vel"][0], pb["vel"][1] - pa["vel"][1]
                events.append(
                    {
                        "match": int(i),
                        "closing": -(vx * rx + vy * ry) / r,
                        "bearing": [bearing_deg(pa, pb), bearing_deg(pb, pa)],
                        "speed": [math.hypot(*pa["vel"]), math.hypot(*pb["vel"])],
                    }
                )
            in_contact[i] = touching
            prev[i] = (sa, sb)
        if not tracker.running.any():
            break
    rec = tracker.records
    out = summarise(rec, n, events, contact_ticks, live_ticks, near_ticks)
    out.update(crash_summary(rec, crash_deaths))
    return out


def crash_summary(rec, crash_deaths: np.ndarray) -> dict:
    """SIM_VERSION 3 crash numbers: damaging collisions, crash deaths, hp share."""
    crash_hp = float(rec.crash_damage.sum())
    all_hp = crash_hp + float(rec.hull_damage.sum())
    return {
        "median_length": float(np.median(rec.length)),
        "draw_rate": float(np.mean(rec.winner == -1)),
        "crashes_per_match": float(rec.crashes.mean()),
        "crash_deaths_per_match": float(crash_deaths.mean()),
        "matches_with_crash_death": float((crash_deaths > 0).mean()),
        "double_crash_kill_rate": float((crash_deaths >= 2).mean()),
        "crash_hp_share": crash_hp / all_hp if all_hp > 0 else 0.0,
    }


def summarise(rec, n, events, contact_ticks, live_ticks, near_ticks) -> dict:
    closing = np.array([e["closing"] for e in events]) if events else np.zeros(0)
    bearings = np.abs(np.array([e["bearing"] for e in events])).ravel()
    arcs = {
        "nose(<45)": float((bearings < 45).mean()) if len(bearings) else 0.0,
        "flank(45-135)": (
            float(((bearings >= 45) & (bearings < 135)).mean())
            if len(bearings)
            else 0.0
        ),
        "tail(>=135)": float((bearings >= 135).mean()) if len(bearings) else 0.0,
    }
    head_on = (
        float(
            np.mean(
                [
                    abs(e["bearing"][0]) < 45 and abs(e["bearing"][1]) < 45
                    for e in events
                ]
            )
        )
        if events
        else 0.0
    )
    per_match = np.bincount([e["match"] for e in events], minlength=n)
    live = max(int(live_ticks.sum()), 1)
    return {
        "n": n,
        "a_win": float(np.mean(rec.winner == rec.a_team)),
        "median_ticks": float(np.median(live_ticks)),
        "matches_with_contact": float((per_match > 0).mean()),
        "contacts_per_match": float(per_match.mean()),
        "contact_tick_share": float(contact_ticks.sum() / live),
        "near_tick_share": {
            f"<{d:g}m": float(v.sum() / live) for d, v in near_ticks.items()
        },
        "closing_mps": {
            q: float(np.percentile(closing, p)) if len(closing) else 0.0
            for q, p in (("p10", 10), ("p50", 50), ("p90", 90), ("max", 100))
        },
        "closing_share": {
            f">{v}": float((closing > v).mean()) if len(closing) else 0.0
            for v in (5, 15, 30, 60)
        },
        "contact_bearing_share": arcs,
        "head_on_share": head_on,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--a", required=True, help="checkpoint path or 'script'")
    p.add_argument("--b", required=True, help="checkpoint path or 'script'")
    p.add_argument("--n", type=int, default=128)
    p.add_argument("--seed", type=int, default=100_000)
    p.add_argument("--argmax", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    out = survey(
        make_controller(args.a, not args.argmax),
        make_controller(args.b, not args.argmax),
        args.n,
        args.seed,
    )
    out.update({"a": args.a, "b": args.b})
    text = json.dumps(out, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
