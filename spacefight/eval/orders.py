"""Order-following eval (M3 stage B): do pilots fly the order in their obs?

``evaluate(a, b, cfg)`` plays each mission of ``cfg`` under each commander mode
(``random``: the sim's random orders; ``scripted``: the mission script's), with the
live default rosters, ``a`` flying side ``a``'s strike craft, ``b`` the other side's
and the scripts the capital ships (the env layout of ``spacefight.eval.missions``).
Only side ``a``'s strike craft are measured. It needs SIM_VERSION 5: the metrics
come from the obs order block (SIM_SPEC §7.2, "Stage B decisions" in
``docs/M3_PLAN.md``), which holds the ship's *effective* order (none at once when an
attack target dies or a ward leaves), and the ship state per tick.

An **order instance** follows the sim's (SIM_SPEC §5.9): it starts on a tick where
the obs shows an order whose kind differs from the last tick's, or whose age
(feature 14, ticks since the sim's instance started) went back, and ends when the
effective order becomes none or changes again, or the ship dies, departs or the
match ends. The target slot of an attack (for the damage share) is the standing
order's, read from ``mission_state`` when the instance starts. Per instance, from its
first tick:

- *attack*: **time to close**, ticks until the target is inside the ship's gun range
  (its longest present weapon), for targets nearer than ``CLOSE_FROM_M`` at the
  start; **damage share**, hull + shield damage the ship dealt to its ordered
  target over all it dealt during attack instances (pooled), and damage on the
  target per minute of attack order;
- *guard*: **time within** the guard radius (``GUARD_PRESENCE`` 90 m + the ward's
  bound radius: obs ``signed (dist - radius) <= 0``), share of the instance's live
  ticks, pooled;
- *hold*: **time inside** the hold radius, the same way;
- every kind: **response time**, ticks until the nose is within ``RESPONSE_DEG``
  of the target point, for instances that start outside the order's radius;
- **engine duty** (the strongest thruster's level, as the fleet eval) per hull and
  per order kind (``none`` included), over live ticks.

A median over instances counts an instance that never got there as never (``null``
in the JSON when that is more than half of them); each median comes with the share
that got there. JSON schema ``rlf.eval.orders/1``.

    python -m spacefight.eval.orders --a ckpt.pt --out orders.json
    python -m spacefight.eval.orders --a v1.pt            # baseline (obs[:385])
    python -m spacefight.eval.orders --a blank:ckpt.pt    # block zeroed
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Self

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.rosters import CARRIER_BATTLE, CONVOY_ESCORT, RANDOM, SCRIPTED
from spacefight.env.rust_env import OBS_LAYOUT, OBS_SLOTS, ORDERS_SUPPORTED
from spacefight.eval import features as F
from spacefight.eval.controllers import Controller, idle_actions, make_controller
from spacefight.eval.fleet import hull_names_by_id
from spacefight.eval.missions import ASSETS, MissionEnv, build_mission_env

SCHEMA = "rlf.eval.orders/1"
TICK_HZ = 30
DEFAULT_SEED = 400_000
DEFAULT_MISSIONS: tuple[str, ...] = (CARRIER_BATTLE, CONVOY_ESCORT)
DEFAULT_COMMANDERS: tuple[str, ...] = (RANDOM, SCRIPTED)
KINDS: tuple[str, ...] = ("none", "attack", "guard", "hold")
NONE, ATTACK, GUARD, HOLD = range(4)
# Attack instances count for time to close when the target starts nearer than this.
CLOSE_FROM_M = 250.0
RESPONSE_DEG = 30.0
NO_TARGET = -1

# Order block (SIM_VERSION 5), offsets inside the block.
ORD_HAS, ORD_KIND = 0, slice(1, 4)
ORD_REL_X, ORD_REL_Y = 4, 5
ORD_MARGIN, ORD_RADIUS = 8, 9
ORD_AGE = 14
# Feature 14 is ticks / 300; an instance restarted when it drops by more than this.
AGE_RESET = 0.5 / 300.0


@dataclass(frozen=True)
class OrdersEvalConfig:
    """The scenarios of one order-following evaluation."""

    missions: tuple[str, ...] = DEFAULT_MISSIONS
    commanders: tuple[str, ...] = DEFAULT_COMMANDERS
    n_per_scenario: int = 192
    seed: int = DEFAULT_SEED
    reaction_ticks: int = 2
    sim_version: int = int(rlf_sim.SIM_VERSION)


# ---------------------------------------------------------------------------
# Instance tracking (pure numpy; tests feed it synthetic traces)
# ---------------------------------------------------------------------------


@dataclass
class Instances:
    """Closed order instances, one entry per instance (parallel lists)."""

    kind: list[int] = field(default_factory=list)
    hull: list[int] = field(default_factory=list)
    live_ticks: list[int] = field(default_factory=list)
    start_dist: list[float] = field(default_factory=list)
    start_outside: list[bool] = field(default_factory=list)
    close_tick: list[int] = field(default_factory=list)  # -1: never
    response_tick: list[int] = field(default_factory=list)  # -1: never
    inside_ticks: list[int] = field(default_factory=list)
    damage_total: list[float] = field(default_factory=list)
    damage_target: list[float] = field(default_factory=list)

    def extend(self, other: Instances) -> None:
        """Append every instance of ``other``."""
        for name in self.__dataclass_fields__:
            getattr(self, name).extend(getattr(other, name))

    def arrays(self) -> dict[str, NDArray[Any]]:
        """Every list as a numpy array (typed, also when empty)."""
        dtypes = {
            "start_dist": np.float64,
            "damage_total": np.float64,
            "damage_target": np.float64,
            "start_outside": np.bool_,
        }
        return {
            name: np.asarray(getattr(self, name), dtype=dtypes.get(name, np.int64))
            for name in self.__dataclass_fields__
        }


class OrderTracker:
    """Per-ship open order instances over ``[N, S]`` slots, step by step.

    Call ``begin`` when orders change (after a slow tick) and ``step`` once per tick
    with that tick's measurements; ``finish`` closes what is still open.

    Args:
        measured: [N, S] slots whose orders are measured (side ``a``'s strike craft).
        hull: [N, S] hull ids.
    """

    def __init__(self, measured: NDArray[np.bool_], hull: NDArray[np.integer]) -> None:
        shape = measured.shape
        self.measured = measured.copy()
        self.hull = np.asarray(hull, dtype=np.int64)
        self.open = np.zeros(shape, dtype=bool)
        self.kind = np.zeros(shape, dtype=np.int64)
        self.target = np.full(shape, NO_TARGET, dtype=np.int64)
        self.ticks = np.zeros(shape, dtype=np.int64)
        self.live = np.zeros(shape, dtype=np.int64)
        self.started = np.zeros(shape, dtype=bool)
        self.start_dist = np.zeros(shape, dtype=np.float64)
        self.start_outside = np.zeros(shape, dtype=bool)
        self.close_tick = np.full(shape, -1, dtype=np.int64)
        self.response_tick = np.full(shape, -1, dtype=np.int64)
        self.inside = np.zeros(shape, dtype=np.int64)
        self.damage_total = np.zeros(shape, dtype=np.float64)
        self.damage_target = np.zeros(shape, dtype=np.float64)
        self.done = Instances()
        # Engine duty per (hull id, order kind): summed level and live ticks.
        self.duty_sum: dict[tuple[int, int], float] = {}
        self.duty_ticks: dict[tuple[int, int], int] = {}

    def begin(
        self,
        changed: NDArray[np.bool_],
        kind: NDArray[np.integer],
        target: NDArray[np.integer],
    ) -> None:
        """Close the open instances of ``changed`` slots and open new ones where the
        new ``kind`` is not ``none`` (``target``: the attacked or guarded slot, or
        ``NO_TARGET``)."""
        changed = changed & self.measured
        self.close(changed & self.open)
        opening = changed & (np.asarray(kind) != NONE)
        self.open[opening] = True
        self.kind[opening] = np.asarray(kind)[opening]
        self.target[opening] = np.asarray(target)[opening]
        for arr, value in (
            (self.ticks, 0),
            (self.live, 0),
            (self.started, False),
            (self.start_dist, 0.0),
            (self.start_outside, False),
            (self.close_tick, -1),
            (self.response_tick, -1),
            (self.inside, 0),
            (self.damage_total, 0.0),
            (self.damage_target, 0.0),
        ):
            arr[opening] = value

    def step(
        self,
        live: NDArray[np.bool_],
        dist: NDArray[np.floating],
        margin: NDArray[np.floating],
        angle: NDArray[np.floating],
        gun_range: NDArray[np.floating],
        engine_level: NDArray[np.floating],
        obs_kind: NDArray[np.integer],
    ) -> None:
        """One tick of the measured slots (all ``[N, S]``).

        Args:
            live: Present and alive this tick (a dead or departed ship's instance
                is closed).
            dist: Metres to the order's target point.
            margin: ``dist - radius`` (metres; <= 0 is inside).
            angle: Radians between the nose and the target point.
            gun_range: Metres, the ship's longest present weapon.
            engine_level: The strongest thruster's level.
            obs_kind: The order kind in the obs (engine duty is binned by it).
        """
        measured_live = self.measured & live
        for hid in np.unique(self.hull[measured_live]):
            for k in range(len(KINDS)):
                sel = measured_live & (self.hull == hid) & (obs_kind == k)
                if sel.any():
                    key = (int(hid), k)
                    self.duty_sum[key] = self.duty_sum.get(key, 0.0) + float(
                        engine_level[sel].sum()
                    )
                    self.duty_ticks[key] = self.duty_ticks.get(key, 0) + int(sel.sum())
        self.close(self.open & ~live & self.started)
        on = self.open & live
        first = on & ~self.started
        self.started[first] = True
        self.start_dist[first] = dist[first]
        self.start_outside[first] = margin[first] > 0.0
        closing = on & (self.close_tick < 0) & (dist < gun_range)
        self.close_tick[closing] = self.ticks[closing]
        facing = (
            on & (self.response_tick < 0) & (np.abs(angle) < math.radians(RESPONSE_DEG))
        )
        self.response_tick[facing] = self.ticks[facing]
        self.inside[on & (margin <= 0.0)] += 1
        self.live[on] += 1
        self.ticks[self.open & self.started] += 1

    def add_damage(
        self,
        env: NDArray[np.integer],
        shooter: NDArray[np.integer],
        target: NDArray[np.integer],
        amount: NDArray[np.floating],
    ) -> None:
        """Hits of one step: hull + shield ``amount`` from ``shooter`` to ``target``
        slots of ``env`` (parallel arrays)."""
        sel = self.open[env, shooter] & self.started[env, shooter]
        e, s, t, a = env[sel], shooter[sel], target[sel], amount[sel]
        np.add.at(self.damage_total, (e, s), a)
        on_target = t == self.target[e, s]
        np.add.at(self.damage_target, (e[on_target], s[on_target]), a[on_target])

    def finish(self) -> None:
        """Close every open instance (match end)."""
        self.close(self.open.copy())

    def close(self, rows: NDArray[np.bool_]) -> None:
        """Close the open instances of ``rows``: record those that had a live tick,
        drop the rest (e.g. a docked ship's order that ended before it launched)."""
        rows = rows & self.open
        record = rows & self.started
        if record.any():
            d = self.done
            d.kind.extend(self.kind[record].tolist())
            d.hull.extend(self.hull[record].tolist())
            d.live_ticks.extend(self.live[record].tolist())
            d.start_dist.extend(self.start_dist[record].tolist())
            d.start_outside.extend(self.start_outside[record].tolist())
            d.close_tick.extend(self.close_tick[record].tolist())
            d.response_tick.extend(self.response_tick[record].tolist())
            d.inside_ticks.extend(self.inside[record].tolist())
            d.damage_total.extend(self.damage_total[record].tolist())
            d.damage_target.extend(self.damage_target[record].tolist())
        self.open[rows] = False


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Timing:
    """Median ticks over instances; ``reached`` is the share that got there."""

    n: int
    median: float | None  # None: more than half never got there (or no instance)
    reached: float


def censored_median(ticks: NDArray[np.integer]) -> Timing:
    """Median of tick counts where -1 means never (treated as infinitely late)."""
    n = int(ticks.size)
    if n == 0:
        return Timing(0, None, 0.0)
    values = np.where(ticks < 0, np.inf, ticks.astype(np.float64))
    med = float(np.median(values))
    return Timing(n, med if math.isfinite(med) else None, float(np.mean(ticks >= 0)))


@dataclass(frozen=True)
class KindSummary:
    """One order kind's following metrics (pooled over instances)."""

    instances: int
    live_ticks: int
    response: Timing
    # attack only (zeros otherwise)
    close: Timing
    damage_share: float
    target_damage_per_min: float
    # guard / hold only: share of live instance ticks inside the radius
    time_inside: float


@dataclass(frozen=True)
class FollowSummary:
    """Every kind, the pooled response time and engine duty of one scenario set."""

    attack: KindSummary
    guard: KindSummary
    hold: KindSummary
    response: Timing  # all kinds
    engine_duty: dict[str, dict[str, float]]  # hull -> order kind -> duty
    duty_ticks: dict[str, dict[str, int]]


def summarise_kind(arr: Mapping[str, NDArray[Any]], kind: int) -> KindSummary:
    """``KindSummary`` of the instances of ``kind`` in ``arr`` (``Instances.arrays``)."""
    sel = arr["kind"] == kind
    total_live = int(arr["live_ticks"][sel].sum())
    response = censored_median(arr["response_tick"][sel & arr["start_outside"]])
    close = Timing(0, None, 0.0)
    share = rate = inside = 0.0
    if kind == ATTACK:
        near = arr["start_dist"][sel] < CLOSE_FROM_M
        close = censored_median(arr["close_tick"][sel][near])
        dealt = float(arr["damage_total"][sel].sum())
        on_target = float(arr["damage_target"][sel].sum())
        share = on_target / dealt if dealt > 0 else 0.0
        minutes = total_live / TICK_HZ / 60.0
        rate = on_target / minutes if minutes > 0 else 0.0
    if kind in (GUARD, HOLD) and total_live:
        inside = float(arr["inside_ticks"][sel].sum()) / total_live
    return KindSummary(
        instances=int(sel.sum()),
        live_ticks=total_live,
        response=response,
        close=close,
        damage_share=share,
        target_damage_per_min=rate,
        time_inside=inside,
    )


def summarise(
    instances: Instances,
    duty_sum: Mapping[tuple[int, int], float],
    duty_ticks: Mapping[tuple[int, int], int],
    hull_names: Mapping[int, str],
) -> FollowSummary:
    """Reduce closed instances and duty counters to a ``FollowSummary``."""
    arr = instances.arrays()
    duty: dict[str, dict[str, float]] = {}
    ticks: dict[str, dict[str, int]] = {}
    for (hid, k), n in sorted(duty_ticks.items()):
        name = hull_names.get(hid, str(hid))
        duty.setdefault(name, {})[KINDS[k]] = duty_sum[(hid, k)] / n if n else 0.0
        ticks.setdefault(name, {})[KINDS[k]] = n
    return FollowSummary(
        attack=summarise_kind(arr, ATTACK),
        guard=summarise_kind(arr, GUARD),
        hold=summarise_kind(arr, HOLD),
        response=censored_median(arr["response_tick"][arr["start_outside"]]),
        engine_duty=duty,
        duty_ticks=ticks,
    )


@dataclass(frozen=True)
class OrdersResult:
    """Outcome of ``evaluate``; JSON schema ``SCHEMA``.

    ``scenarios`` is keyed ``"<mission>/<commander>"``; ``by_commander`` pools the
    missions of each commander mode (what the gates read).
    """

    a: str
    b: str
    config: OrdersEvalConfig
    scenarios: dict[str, FollowSummary]
    by_commander: dict[str, FollowSummary]
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict (``None`` for medians never reached)."""
        return asdict(self)

    def to_json(self) -> str:
        """Indented JSON text."""
        return json.dumps(self.to_dict(), indent=1)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Rebuild from ``to_dict`` output.

        Raises:
            ValueError: Wrong schema.
        """
        if data.get("schema") != SCHEMA:
            raise ValueError(f"expected schema {SCHEMA!r}, got {data.get('schema')!r}")

        def kind(raw: dict[str, Any]) -> KindSummary:
            return KindSummary(
                **{
                    **raw,
                    "response": Timing(**raw["response"]),
                    "close": Timing(**raw["close"]),
                }
            )

        def follow(raw: dict[str, Any]) -> FollowSummary:
            return FollowSummary(
                attack=kind(raw["attack"]),
                guard=kind(raw["guard"]),
                hold=kind(raw["hold"]),
                response=Timing(**raw["response"]),
                engine_duty=raw["engine_duty"],
                duty_ticks=raw["duty_ticks"],
            )

        config = dict(data["config"])
        config["missions"] = tuple(config["missions"])
        config["commanders"] = tuple(config["commanders"])
        return cls(
            a=data["a"],
            b=data["b"],
            config=OrdersEvalConfig(**config),
            scenarios={k: follow(v) for k, v in data["scenarios"].items()},
            by_commander={k: follow(v) for k, v in data["by_commander"].items()},
        )

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Parse ``to_json`` output."""
        return cls.from_dict(json.loads(text))

    def markdown(self) -> str:
        """Following table per scenario set, and engine duty per hull and kind."""

        def ticks(t: Timing) -> str:
            med = "never" if t.median is None else f"{t.median:.0f}"
            return f"{med} ({t.reached:.2f} of {t.n})"

        lines = [
            f"**{self.a}** following orders (opponent {self.b})",
            "",
            "| scenarios | attack: close ticks | attack: dmg share | attack: target "
            "dmg/min | guard: time within | hold: time inside | response ticks "
            "| instances a/g/h |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for name, f in [*self.by_commander.items(), *self.scenarios.items()]:
            lines.append(
                f"| {name} | {ticks(f.attack.close)} | {f.attack.damage_share:.3f} | "
                f"{f.attack.target_damage_per_min:.1f} | {f.guard.time_inside:.3f} | "
                f"{f.hold.time_inside:.3f} | {ticks(f.response)} | "
                f"{f.attack.instances}/{f.guard.instances}/{f.hold.instances} |"
            )
        lines += ["", "| scenarios | hull | " + " | ".join(KINDS) + " |"]
        lines.append("|---|---|" + "---|" * len(KINDS))
        for name, f in self.by_commander.items():
            for hull, by_kind in f.engine_duty.items():
                cells = [f"{by_kind[k]:.2f}" if k in by_kind else "–" for k in KINDS]
                lines.append(f"| {name} | {hull} | " + " | ".join(cells) + " |")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Running the matches
# ---------------------------------------------------------------------------


def ship_orders(
    mission_state: Mapping[str, Any], n_slots: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Each slot's standing squad order from a ``mission_state`` dict: kind code and
    target slot (attack target or guard ward, else ``NO_TARGET``)."""
    kind = np.zeros(n_slots, dtype=np.int64)
    target = np.full(n_slots, NO_TARGET, dtype=np.int64)
    for team_squads in mission_state["squads"]:
        for squad in team_squads:
            order = squad["order"]
            code = KINDS.index(str(order["kind"]))
            slot_target = int(order.get("target", order.get("ward", NO_TARGET)))
            for member in squad["members"]:
                kind[member] = code
                target[member] = slot_target
    return kind, target


def instance_starts(
    kind: NDArray[np.integer],
    age: NDArray[np.floating],
    prev_kind: NDArray[np.integer],
    prev_age: NDArray[np.floating],
    is_open: NDArray[np.bool_],
) -> NDArray[np.bool_]:
    """Where a new order instance starts this tick (module docstring): an order is
    shown and its kind changed, its age went back, or no instance is open."""
    shown = np.asarray(kind) != NONE
    changed = np.asarray(kind) != np.asarray(prev_kind)
    restarted = np.asarray(age) < np.asarray(prev_age) - AGE_RESET
    return shown & (changed | restarted | ~is_open)


def _obs_measurements(
    obs: NDArray[np.float32], radius: NDArray[np.float64]
) -> dict[str, NDArray[Any]]:
    """Per-slot order measurements from ``[N, S, OBS_DIM]`` obs (v5)."""
    lo, width = OBS_LAYOUT["order"]
    block = obs[..., lo : lo + width]
    r = radius[:, None]
    rel_x, rel_y = block[..., ORD_REL_X], block[..., ORD_REL_Y]
    kind = np.where(block[..., ORD_HAS] > 0.5, block[..., ORD_KIND].argmax(-1) + 1, 0)
    t_lo, t_w = OBS_LAYOUT["turrets"]
    turret_present = (
        obs[..., t_lo : t_lo + t_w].reshape(*obs.shape[:-1], OBS_SLOTS["turrets"], -1)[
            ..., 0
        ]
        > 0.5
    )
    r_lo, r_w = OBS_LAYOUT["turret_range"]
    ranges = obs[..., r_lo : r_lo + r_w] * r[..., None]
    th_lo, th_w = OBS_LAYOUT["thrusters"]
    thrusters = obs[..., th_lo : th_lo + th_w].reshape(
        *obs.shape[:-1], OBS_SLOTS["thrusters"], -1
    )
    accel = np.where(
        thrusters[..., F.THRUSTER_PRESENT] > 0.5,
        thrusters[..., F.THRUSTER_ACCEL],
        -np.inf,
    )
    main = accel.argmax(axis=-1)[..., None]
    level = np.take_along_axis(thrusters[..., F.THRUSTER_LEVEL], main, axis=-1)[..., 0]
    return {
        "live": obs[..., F.SELF_PRESENT] > 0.5,
        "dist": np.hypot(rel_x, rel_y) * r,
        "margin": block[..., ORD_MARGIN] * r,
        "angle": np.arctan2(rel_y, rel_x),
        "gun_range": np.where(turret_present, ranges, 0.0).max(axis=-1),
        "engine_level": level,
        "obs_kind": kind,
        "age": block[..., ORD_AGE],
    }


def run_scenario(
    a: Controller,
    b: Controller,
    mission: str,
    commanders: str,
    cfg: OrdersEvalConfig,
    seed: int,
    n_threads: int,
    assets_dir: Path = ASSETS,
) -> tuple[OrderTracker, dict[int, str]]:
    """Play one mission under one commander mode; the tracker of side ``a``.

    Raises:
        RuntimeError: The sim has no order block, or a match did not end in time.
    """
    if not ORDERS_SUPPORTED:
        raise RuntimeError("the order-following eval needs SIM_VERSION >= 5")
    me: MissionEnv = build_mission_env(
        mission,
        cfg.n_per_scenario,
        seed,
        commanders,
        n_threads,
        cfg.reaction_ticks,
        assets_dir,
    )
    env = me.env
    n, s = env.n_envs, env.n_ships
    team = env.team.astype(np.int64).copy()
    a_rows = team == me.a_team[:, None]
    b_rows = team == (1 - me.a_team)[:, None]
    strike = (team >= 0) & ~me.capital
    tracker = OrderTracker(a_rows & strike, env.hull_id)
    radius = env.arena_radius.astype(np.float64).copy()
    prev_kind = np.zeros((n, s), dtype=np.int64)
    prev_age = np.zeros((n, s), dtype=np.float32)
    running = np.ones(n, dtype=bool)
    hull_names = hull_names_by_id(env)
    a.reset(seed)
    b.reset(seed + 1)
    max_steps = int(round(me.time_limit_s * TICK_HZ)) + 2
    for _ in range(max_steps):
        decide = running[:, None] & env.act_mask
        actions = idle_actions(n * s).reshape(n, s, -1)
        scripted = decide & me.capital
        if scripted.any():
            actions[scripted] = env.scripted_actions()[scripted]
        for ctrl, side in ((a, a_rows), (b, b_rows)):
            rows = decide & side & strike
            if rows.any():
                actions[rows] = ctrl.act(env, rows)
        _, _, dones, info = env.step(actions)
        dones = dones.copy()
        _record_hits(tracker, info.hits, info.hit_count, running)
        ending = running & dones
        if ending.any():
            stop = np.zeros((n, s), dtype=bool)
            stop[ending] = True
            tracker.close(stop)
        running &= ~dones
        if not running.any():
            break
        m = _obs_measurements(env.obs, radius)
        live = m["live"] & running[:, None]
        kind = np.where(live, m["obs_kind"], NONE)
        tracker.close(tracker.open & live & (kind == NONE))
        start = (
            tracker.measured
            & live
            & instance_starts(kind, m["age"], prev_kind, prev_age, tracker.open)
        )
        if start.any():
            target = np.full((n, s), NO_TARGET, dtype=np.int64)
            for i in np.flatnonzero(start.any(axis=1)):
                target[i] = ship_orders(env.raw.mission_state(int(i)), s)[1]
            tracker.begin(start, kind, target)
        prev_kind, prev_age = kind, m["age"].copy()
        tracker.step(
            live,
            m["dist"],
            m["margin"],
            m["angle"],
            m["gun_range"],
            m["engine_level"],
            m["obs_kind"],
        )
    else:
        raise RuntimeError(f"{mission}/{commanders}: matches did not end in time")
    tracker.finish()
    return tracker, hull_names


def _record_hits(
    tracker: OrderTracker,
    hits: NDArray[np.int32],
    hit_count: NDArray[np.int32],
    running: NDArray[np.bool_],
) -> None:
    valid = (np.arange(hits.shape[1]) < hit_count[:, None]) & running[:, None]
    if not valid.any():
        return
    env_ids, _ = np.nonzero(valid)
    rows = hits[valid]
    amount = rows[:, F.HIT_DAMAGE] / float(rlf_sim.HIT_DAMAGE_SCALE)
    tracker.add_damage(
        env_ids.astype(np.int64),
        rows[:, F.HIT_SHOOTER].astype(np.int64),
        rows[:, F.HIT_TARGET].astype(np.int64),
        amount,
    )


def evaluate(
    a: Controller,
    b: Controller,
    cfg: OrdersEvalConfig | None = None,
    n_threads: int = 12,
    assets_dir: Path = ASSETS,
) -> OrdersResult:
    """Play every (mission, commander mode) of ``cfg``; side ``a`` is measured."""
    cfg = cfg or OrdersEvalConfig()
    scenarios: dict[str, FollowSummary] = {}
    pooled: dict[
        str, tuple[Instances, dict[Any, float], dict[Any, int], dict[int, str]]
    ] = {}
    for ci, commanders in enumerate(cfg.commanders):
        for mi, mission in enumerate(cfg.missions):
            seed = cfg.seed + 100_003 * mi + 7_919 * ci
            tracker, names = run_scenario(
                a, b, mission, commanders, cfg, seed, n_threads, assets_dir
            )
            scenarios[f"{mission}/{commanders}"] = summarise(
                tracker.done, tracker.duty_sum, tracker.duty_ticks, names
            )
            inst, dsum, dticks, all_names = pooled.setdefault(
                commanders, (Instances(), {}, {}, {})
            )
            inst.extend(tracker.done)
            for key, v in tracker.duty_sum.items():
                dsum[key] = dsum.get(key, 0.0) + v
            for key, c in tracker.duty_ticks.items():
                dticks[key] = dticks.get(key, 0) + c
            all_names.update(names)
    by_commander = {
        mode: summarise(inst, dsum, dticks, names)
        for mode, (inst, dsum, dticks, names) in pooled.items()
    }
    return OrdersResult(a.label, b.label, cfg, scenarios, by_commander)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: run one evaluation, print Markdown, write JSON."""
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--a", required=True, help="checkpoint, blank:<ckpt> or script")
    p.add_argument("--b", default="script", help="the other side's pilot")
    p.add_argument("--missions", nargs="+", default=list(DEFAULT_MISSIONS))
    p.add_argument("--commanders", nargs="+", default=list(DEFAULT_COMMANDERS))
    p.add_argument("--n-per-scenario", type=int, default=192)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--n-threads", type=int, default=12)
    p.add_argument("--argmax", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    cfg = OrdersEvalConfig(
        missions=tuple(args.missions),
        commanders=tuple(args.commanders),
        n_per_scenario=args.n_per_scenario,
        seed=args.seed,
    )
    sample = not args.argmax
    result = evaluate(
        make_controller(args.a, sample=sample, seed=0),
        make_controller(args.b, sample=sample, seed=1),
        cfg,
        n_threads=args.n_threads,
    )
    print(result.markdown())
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
