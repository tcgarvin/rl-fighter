"""Order-following eval of SIM_VERSION 6 (M3 stage B3): attack, defend, go-to.

``evaluate(a, b, cfg)`` plays each mission of ``cfg`` under each commander mode
(``random``: the sim's random orders, what gate O reads; ``scripted``: the mission
script's, reported), with the live default rosters, ``a`` flying side ``a``'s strike
craft, ``b`` the other side's and the scripts the capital ships (the env layout of
``spacefight.eval.missions``: ``a`` flies each side of each roster equally often).
Only side ``a``'s strike craft are measured. Each scenario runs in two **passes** on
the same matches (the same seed): ``followed``, and ``hidden``, where the sim hides
side ``a``'s orders from its pilots' obs (``hide_orders``: they see exactly what a
ship with no order sees) while the orders, the rewards and the scripts stay as they
are. A script flies orders it cannot see, so the teacher needs only ``followed``.

The definitions are the reward's (``docs/M3_PLAN.md`` "Stage B3"). Every tick the
sim's ``order_tracks()`` give each ship's standing and effective order. An **order
instance** is one effective order of one ship: it opens on a live tick whose
effective order is not none, and it

- *ends* when the effective order becomes none on its own: an attack target or a
  defend ward died or left; a go-to *completes* on arrival (inside the radius);
- is *censored* when the ship dies or leaves, a new order arrives (the standing
  order's kind, target or instance start changes), or the match ends.

Per instance, from its first live tick (a ship launched into a running order starts
then):

- *attack*: **ticks to gun range** (the ship's longest present weapon), for
  instances whose target starts outside it by at most ``CLOSE_FROM_M`` (250 m); a
  target that died first counts as never, an instance censored before closing is
  excluded; the median and the share reached. **Damage share on the target**:
  damage dealt to the target over all damage dealt during attack instances
  (pooled). Positions are read every ``POS_EVERY`` ticks, so ticks to close are
  rounded up to that.
- *defend*: **ward hull lost per defended ward-minute**: a ward is defended on a
  tick where at least one measured ship has an open defend instance on it; its hull
  fraction lost on that step (``env.ward_hull_lost``, the reward's unit) is summed
  over defended ward-ticks and divided by defended ward-minutes. **Threat-set
  share**: damage dealt by defenders to their ward's threat set
  (``env.ward_threat`` on the step the hit lands) over all they dealt. Mean
  distance to the ward, reported only.
- *go-to*: **arrival within the deadline** ``GOTO_SLACK * (d / speed cap + 60
  ticks)``, ``d`` the straight-line distance to the arrival circle at the first live
  tick: arrived in time is a success; arrived late, or still out when cut short past
  the deadline, a failure; censored before the deadline, excluded. Near and far
  (``d > FAR_M``) instances are reported apart. **Arrivals per minute** of measured
  live ship time, reported.
- **engine duty** (the strongest thruster's level) per hull and per effective order
  kind (``none`` included), over live ticks.

Pooled per-tick metrics (shares, hull lost per minute, distance) count every
instance tick, censored instances included: censoring cuts a rate's denominator and
numerator together. JSON schema ``rlf.eval.orders/2`` (the SIM_VERSION 5 eval is
``spacefight.eval.orders_v1``).

    python -m spacefight.eval.orders --a ckpt.pt --out orders.json
    python -m spacefight.eval.orders --a script --passes followed   # the teacher
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
from spacefight.env.rust_env import OBS_LAYOUT, OBS_SLOTS, RustVecEnv
from spacefight.eval import features as F
from spacefight.eval.controllers import Controller, idle_actions, make_controller
from spacefight.eval.fleet import hull_names_by_id
from spacefight.eval.missions import ASSETS, MissionEnv, build_mission_env

SCHEMA = "rlf.eval.orders/2"
TICK_HZ = 30
DEFAULT_SEED = 400_000
DEFAULT_MISSIONS: tuple[str, ...] = (CARRIER_BATTLE, CONVOY_ESCORT)
DEFAULT_COMMANDERS: tuple[str, ...] = (RANDOM, SCRIPTED)
FOLLOWED, HIDDEN = "followed", "hidden"
PASSES: tuple[str, ...] = (FOLLOWED, HIDDEN)
# Effective / standing order codes of ``order_tracks()`` (SIM_VERSION 6).
KINDS: tuple[str, ...] = ("none", "attack", "defend", "goto")
NONE, ATTACK, DEFEND, GOTO = range(4)
NO_TARGET = -1
# Attack instances count for ticks to gun range when the target starts outside gun
# range by at most this (metres to close).
CLOSE_FROM_M = 250.0
# Go-to deadline: GOTO_SLACK * (distance / speed cap + GOTO_EXTRA_TICKS).
GOTO_SLACK = 1.5
GOTO_EXTRA_TICKS = 60
# A go-to point farther than this from the ship at the start is a "far" instance.
FAR_M = 200.0
# Ticks between position reads (render_state) for open attack and defend instances.
POS_EVERY = 3
# Instance outcomes.
ENDED, COMPLETED, CENSORED = 0, 1, 2
# Obs scales (SIM_SPEC §7.2).
VS = 100.0
SELF_SPEED_CAP = F.SELF_OFFSET + 14


@dataclass(frozen=True)
class OrdersEvalConfig:
    """The scenarios of one order-following evaluation.

    ``n_scripted`` matches per scripted-commander scenario (0: ``n_per_scenario``);
    the random commander's scenarios, which gate O reads, take ``n_per_scenario``.
    The hidden pass runs only under ``hidden_commanders`` (gate O compares followed
    and hidden under the random commander; the scripted one is reported followed).
    """

    missions: tuple[str, ...] = DEFAULT_MISSIONS
    commanders: tuple[str, ...] = DEFAULT_COMMANDERS
    passes: tuple[str, ...] = PASSES
    hidden_commanders: tuple[str, ...] = (RANDOM,)
    n_per_scenario: int = 192
    n_scripted: int = 0
    seed: int = DEFAULT_SEED
    reaction_ticks: int = 2
    sim_version: int = int(rlf_sim.SIM_VERSION)

    def passes_for(self, commanders: str) -> tuple[str, ...]:
        """The passes run under ``commanders``."""
        if commanders in self.hidden_commanders:
            return self.passes
        return tuple(p for p in self.passes if p != HIDDEN)

    def n_for(self, commanders: str) -> int:
        """Matches per scenario under ``commanders``."""
        if commanders == SCRIPTED and self.n_scripted:
            return self.n_scripted
        return self.n_per_scenario


# ---------------------------------------------------------------------------
# Instance tracking (pure numpy; tests feed it synthetic traces)
# ---------------------------------------------------------------------------


@dataclass
class Instances:
    """Closed order instances, one entry per instance (parallel lists)."""

    kind: list[int] = field(default_factory=list)
    hull: list[int] = field(default_factory=list)
    outcome: list[int] = field(default_factory=list)
    live_ticks: list[int] = field(default_factory=list)
    start_dist: list[float] = field(default_factory=list)  # NaN: no position read
    start_gap: list[float] = field(default_factory=list)  # attack: dist - gun range
    close_tick: list[int] = field(default_factory=list)  # attack, -1: never
    deadline: list[float] = field(default_factory=list)  # go-to, ticks
    damage_total: list[float] = field(default_factory=list)
    damage_on: list[float] = field(default_factory=list)  # target / threat set
    dist_sum: list[float] = field(default_factory=list)  # defend: to the ward
    dist_n: list[int] = field(default_factory=list)

    def extend(self, other: Instances) -> None:
        """Append every instance of ``other``."""
        for name in self.__dataclass_fields__:
            getattr(self, name).extend(getattr(other, name))

    def arrays(self) -> dict[str, NDArray[Any]]:
        """Every list as a numpy array (typed, also when empty)."""
        floats = {
            "start_dist",
            "start_gap",
            "deadline",
            "damage_total",
            "damage_on",
            "dist_sum",
        }
        return {
            name: np.asarray(
                getattr(self, name), dtype=np.float64 if name in floats else np.int64
            )
            for name in self.__dataclass_fields__
        }


@dataclass
class Tally:
    """Everything one scenario (or a pool of them) measured."""

    instances: Instances = field(default_factory=Instances)
    # Defended ward-ticks and the ward hull fraction lost on them.
    ward_ticks: int = 0
    ward_hull_lost: float = 0.0
    # Measured live ship-ticks, and go-to arrivals (completed instances).
    ship_ticks: int = 0
    # Engine duty per (hull id, effective kind): summed level and live ticks.
    duty_sum: dict[tuple[int, int], float] = field(default_factory=dict)
    duty_ticks: dict[tuple[int, int], int] = field(default_factory=dict)
    hull_names: dict[int, str] = field(default_factory=dict)

    def merge(self, other: Tally) -> None:
        """Add ``other``'s measurements to this tally."""
        self.instances.extend(other.instances)
        self.ward_ticks += other.ward_ticks
        self.ward_hull_lost += other.ward_hull_lost
        self.ship_ticks += other.ship_ticks
        for key, v in other.duty_sum.items():
            self.duty_sum[key] = self.duty_sum.get(key, 0.0) + v
        for key, c in other.duty_ticks.items():
            self.duty_ticks[key] = self.duty_ticks.get(key, 0) + c
        self.hull_names.update(other.hull_names)


@dataclass(frozen=True)
class Tracks:
    """One tick of ``order_tracks()`` for every slot (``[N, S]``; point ``[N, S, 2]``)."""

    standing: NDArray[np.int64]
    effective: NDArray[np.int64]
    target: NDArray[np.int64]
    point: NDArray[np.float64]
    radius: NDArray[np.float64]
    arrived: NDArray[np.bool_]
    instance_start: NDArray[np.int64]

    @classmethod
    def from_env(cls, tracks: Mapping[str, Any]) -> Tracks:
        """Owned copies of ``RustVecEnv.order_tracks()``."""
        return cls(
            standing=np.asarray(tracks["standing_kind"], dtype=np.int64).copy(),
            effective=np.asarray(tracks["effective_kind"], dtype=np.int64).copy(),
            target=np.asarray(tracks["target"], dtype=np.int64).copy(),
            point=np.asarray(tracks["point"], dtype=np.float64).copy(),
            radius=np.asarray(tracks["radius"], dtype=np.float64).copy(),
            arrived=np.asarray(tracks["arrived"], dtype=bool).copy(),
            instance_start=np.asarray(tracks["instance_start"], dtype=np.int64).copy(),
        )


class OrderTracker:
    """Per-ship open order instances over ``[N, S]`` slots, tick by tick.

    Each tick: ``observe`` (the state the actions are chosen from), then after the
    step ``add_hits``, ``add_ward_loss`` and ``end_matches``; ``finish`` censors what
    is still open.

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
        self.instance_start = np.zeros(shape, dtype=np.int64)
        self.ticks = np.zeros(shape, dtype=np.int64)
        self.start_dist = np.full(shape, np.nan)
        self.start_gap = np.full(shape, np.nan)
        self.close_tick = np.full(shape, -1, dtype=np.int64)
        self.deadline = np.full(shape, np.nan)
        self.damage_total = np.zeros(shape)
        self.damage_on = np.zeros(shape)
        self.dist_sum = np.zeros(shape)
        self.dist_n = np.zeros(shape, dtype=np.int64)
        # Wards defended on the last observed tick ([N, S] by ward slot).
        self.defended = np.zeros(shape, dtype=bool)
        self.tally = Tally()

    def position_envs(
        self, live: NDArray[np.bool_], tracks: Tracks, periodic: bool
    ) -> NDArray[np.bool_]:
        """[N] envs whose ship positions ``observe`` needs this tick: an instance
        opens or changes, or (``periodic``) an attack instance has not closed yet or
        a defend instance is open."""
        on = self.measured & live
        new = on & (tracks.effective != NONE) & (~self.open | self._new_order(tracks))
        need = new
        if periodic:
            chasing = self.open & (self.kind == ATTACK) & (self.close_tick < 0)
            need = need | (on & (chasing | (self.open & (self.kind == DEFEND))))
        return np.asarray(need.any(axis=1))

    def _new_order(self, tracks: Tracks) -> NDArray[np.bool_]:
        """Where the standing order differs from the open instance's."""
        return (
            (tracks.instance_start != self.instance_start)
            | (tracks.standing != self.kind)
            | (tracks.target != self.target)
        )

    def observe(
        self,
        live: NDArray[np.bool_],
        tracks: Tracks,
        positions: NDArray[np.float64],
        has_pos: NDArray[np.bool_],
        gun_range: NDArray[np.floating],
        speed_cap: NDArray[np.floating],
        engine_level: NDArray[np.floating],
    ) -> None:
        """One tick of the measured slots.

        Args:
            live: [N, S] present and alive, match running.
            tracks: The sim's order tracks this tick.
            positions: [N, S, 2] world positions, valid on envs ``has_pos``.
            has_pos: [N] envs whose positions were read this tick.
            gun_range: [N, S] metres, the ship's longest present weapon.
            speed_cap: [N, S] m/s.
            engine_level: [N, S] the strongest thruster's level.
        """
        measured_live = self.measured & live
        self._duty(measured_live, tracks.effective, engine_level)
        self.tally.ship_ticks += int(measured_live.sum())
        # Close what ended: death or departure, the order going away on its own
        # (the same standing instance, whatever the sim then shows as its target),
        # a new order.
        self.close(self.open & ~live, CENSORED)
        running = self.open & live
        same = (tracks.instance_start == self.instance_start) & (
            tracks.standing == self.kind
        )
        gone = running & same & (tracks.effective == NONE)
        self.close(gone & (self.kind == GOTO) & tracks.arrived, COMPLETED)
        self.close(gone, ENDED)
        self.close(self.open & live & self._new_order(tracks), CENSORED)
        self.close(self.open & (tracks.effective != self.kind), CENSORED)
        # Open what started (or a running order seen for the first time).
        opening = measured_live & ~self.open & (tracks.effective != NONE)
        self._open(opening, tracks)
        on = self.open & live
        valid = on & has_pos[:, None]
        dist = np.linalg.norm(tracks.point - positions, axis=-1)
        first = opening & valid
        self.start_dist[first] = dist[first]
        self.start_gap[first] = dist[first] - gun_range[first]
        out = np.maximum(dist - tracks.radius, 0.0)
        ticks_to_go = out / np.maximum(speed_cap, 1e-6) * TICK_HZ
        goto_first = first & (self.kind == GOTO)
        self.start_dist[goto_first] = out[goto_first]
        self.deadline[goto_first] = GOTO_SLACK * (
            ticks_to_go[goto_first] + GOTO_EXTRA_TICKS
        )
        closing = (
            valid & (self.kind == ATTACK) & (self.close_tick < 0) & (dist <= gun_range)
        )
        self.close_tick[closing] = self.ticks[closing]
        guarding = valid & (self.kind == DEFEND)
        self.dist_sum[guarding] += dist[guarding]
        self.dist_n[guarding] += 1
        self.defended[:] = False
        e, s = np.nonzero(on & (self.kind == DEFEND) & (self.target >= 0))
        self.defended[e, self.target[e, s]] = True
        self.ticks[on] += 1

    def _open(self, opening: NDArray[np.bool_], tracks: Tracks) -> None:
        self.open[opening] = True
        self.kind[opening] = tracks.effective[opening]
        self.target[opening] = tracks.target[opening]
        self.instance_start[opening] = tracks.instance_start[opening]
        for arr, value in (
            (self.ticks, 0),
            (self.start_dist, np.nan),
            (self.start_gap, np.nan),
            (self.close_tick, -1),
            (self.deadline, np.nan),
            (self.damage_total, 0.0),
            (self.damage_on, 0.0),
            (self.dist_sum, 0.0),
            (self.dist_n, 0),
        ):
            arr[opening] = value

    def _duty(
        self,
        live: NDArray[np.bool_],
        kind: NDArray[np.integer],
        engine_level: NDArray[np.floating],
    ) -> None:
        t = self.tally
        for hid in np.unique(self.hull[live]):
            for k in range(len(KINDS)):
                sel = live & (self.hull == hid) & (kind == k)
                if sel.any():
                    key = (int(hid), k)
                    t.duty_sum[key] = t.duty_sum.get(key, 0.0) + float(
                        engine_level[sel].sum()
                    )
                    t.duty_ticks[key] = t.duty_ticks.get(key, 0) + int(sel.sum())

    def add_hits(
        self,
        env: NDArray[np.integer],
        shooter: NDArray[np.integer],
        target: NDArray[np.integer],
        amount: NDArray[np.floating],
        ward_threat: NDArray[np.bool_],
    ) -> None:
        """Hits that landed on the last step (parallel arrays): hull + shield
        ``amount`` from ``shooter`` to ``target`` slots of ``env``. ``ward_threat``
        is the sim's ``[N, S, S]`` threat sets on that step."""
        sel = self.open[env, shooter] & self.measured[env, shooter]
        e, s, t, a = env[sel], shooter[sel], target[sel], amount[sel]
        np.add.at(self.damage_total, (e, s), a)
        kind, aim = self.kind[e, s], self.target[e, s]
        on_target = (kind == ATTACK) & (t == aim)
        threat = (kind == DEFEND) & (aim >= 0)
        threat[threat] = ward_threat[e[threat], aim[threat], t[threat]]
        on = on_target | threat
        np.add.at(self.damage_on, (e[on], s[on]), a[on])

    def add_ward_loss(
        self, hull_lost: NDArray[np.floating], running: NDArray[np.bool_]
    ) -> None:
        """The last step's ward hull fraction lost (``[N, S]``) on the wards that
        were defended when it was chosen, in envs still ``running`` before it."""
        defended = self.defended & running[:, None]
        self.tally.ward_ticks += int(defended.sum())
        self.tally.ward_hull_lost += float(np.asarray(hull_lost)[defended].sum())

    def end_matches(self, ending: NDArray[np.bool_]) -> None:
        """Censor every open instance of the ``ending`` envs (match end)."""
        self.close(self.open & ending[:, None], CENSORED)
        self.defended[ending] = False

    def finish(self) -> None:
        """Censor every open instance."""
        self.close(self.open.copy(), CENSORED)

    def close(self, rows: NDArray[np.bool_], outcome: int) -> None:
        """Close the open instances of ``rows`` with ``outcome``; instances with no
        live tick are dropped."""
        rows = rows & self.open
        record = rows & (self.ticks > 0)
        if record.any():
            d = self.tally.instances
            d.kind.extend(self.kind[record].tolist())
            d.hull.extend(self.hull[record].tolist())
            d.outcome.extend([outcome] * int(record.sum()))
            d.live_ticks.extend(self.ticks[record].tolist())
            d.start_dist.extend(self.start_dist[record].tolist())
            d.start_gap.extend(self.start_gap[record].tolist())
            d.close_tick.extend(self.close_tick[record].tolist())
            d.deadline.extend(self.deadline[record].tolist())
            d.damage_total.extend(self.damage_total[record].tolist())
            d.damage_on.extend(self.damage_on[record].tolist())
            d.dist_sum.extend(self.dist_sum[record].tolist())
            d.dist_n.extend(self.dist_n[record].tolist())
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
class AttackSummary:
    """Attack instances (module docstring)."""

    instances: int
    censored: int
    live_ticks: int
    close: Timing
    in_range_at_start: float
    damage_share: float
    target_damage_per_min: float


@dataclass(frozen=True)
class DefendSummary:
    """Defend instances and defended wards (module docstring)."""

    instances: int
    censored: int
    live_ticks: int
    ward_minutes: float
    hull_lost_per_ward_minute: float | None  # None: no defended ward-minute
    threat_share: float
    damage_per_min: float
    mean_distance_m: float | None


@dataclass(frozen=True)
class Arrivals:
    """Go-to instances judged against their deadline."""

    n: int  # judged (not excluded by censoring)
    in_time: float  # share of n
    excluded: int


@dataclass(frozen=True)
class GotoSummary:
    """Go-to instances (module docstring)."""

    instances: int
    censored: int
    live_ticks: int
    arrivals: int
    arrivals_per_min: float
    all: Arrivals
    near: Arrivals
    far: Arrivals


@dataclass(frozen=True)
class FollowSummary:
    """Every kind and engine duty of one scenario set."""

    attack: AttackSummary
    defend: DefendSummary
    goto: GotoSummary
    ship_minutes: float
    engine_duty: dict[str, dict[str, float]]  # hull -> order kind -> duty
    duty_ticks: dict[str, dict[str, int]]


def _minutes(ticks: float) -> float:
    return ticks / TICK_HZ / 60.0


def summarise_attack(arr: Mapping[str, NDArray[Any]]) -> AttackSummary:
    """``AttackSummary`` of the attack instances in ``arr`` (``Instances.arrays``)."""
    sel = arr["kind"] == ATTACK
    censored = arr["outcome"] == CENSORED
    gap = arr["start_gap"]
    near = sel & (gap > 0.0) & (gap <= CLOSE_FROM_M)
    close = arr["close_tick"]
    # Censored before closing: unknown, excluded. A target that died first: never.
    judged = near & ~(censored & (close < 0))
    known = sel & np.isfinite(gap)
    in_range = float(np.mean(gap[known] <= 0.0)) if known.any() else 0.0
    dealt = float(arr["damage_total"][sel].sum())
    on_target = float(arr["damage_on"][sel].sum())
    live = int(arr["live_ticks"][sel].sum())
    minutes = _minutes(live)
    return AttackSummary(
        instances=int(sel.sum()),
        censored=int((sel & censored).sum()),
        live_ticks=live,
        close=censored_median(close[judged]),
        in_range_at_start=in_range,
        damage_share=on_target / dealt if dealt > 0 else 0.0,
        target_damage_per_min=on_target / minutes if minutes > 0 else 0.0,
    )


def summarise_defend(
    arr: Mapping[str, NDArray[Any]], ward_ticks: int, ward_hull_lost: float
) -> DefendSummary:
    """``DefendSummary`` of the defend instances and the defended wards."""
    sel = arr["kind"] == DEFEND
    dealt = float(arr["damage_total"][sel].sum())
    live = int(arr["live_ticks"][sel].sum())
    n_dist = int(arr["dist_n"][sel].sum())
    ward_minutes = _minutes(ward_ticks)
    return DefendSummary(
        instances=int(sel.sum()),
        censored=int((sel & (arr["outcome"] == CENSORED)).sum()),
        live_ticks=live,
        ward_minutes=ward_minutes,
        hull_lost_per_ward_minute=(
            ward_hull_lost / ward_minutes if ward_minutes > 0 else None
        ),
        threat_share=float(arr["damage_on"][sel].sum()) / dealt if dealt > 0 else 0.0,
        damage_per_min=dealt / _minutes(live) if live else 0.0,
        mean_distance_m=(
            float(arr["dist_sum"][sel].sum()) / n_dist if n_dist else None
        ),
    )


def _arrivals(arr: Mapping[str, NDArray[Any]], sel: NDArray[np.bool_]) -> Arrivals:
    deadline = arr["deadline"]
    ticks = arr["live_ticks"]
    completed = arr["outcome"] == COMPLETED
    timed = sel & np.isfinite(deadline)
    success = timed & completed & (ticks <= deadline)
    failure = timed & ~success & (completed | (ticks >= deadline))
    judged = success | failure
    n = int(judged.sum())
    return Arrivals(
        n=n,
        in_time=float(success.sum()) / n if n else 0.0,
        excluded=int((sel & ~judged).sum()),
    )


def summarise_goto(arr: Mapping[str, NDArray[Any]], ship_ticks: int) -> GotoSummary:
    """``GotoSummary`` of the go-to instances; arrivals per measured ship-minute."""
    sel = arr["kind"] == GOTO
    arrivals = int((sel & (arr["outcome"] == COMPLETED)).sum())
    minutes = _minutes(ship_ticks)
    far = arr["start_dist"] > FAR_M
    return GotoSummary(
        instances=int(sel.sum()),
        censored=int((sel & (arr["outcome"] == CENSORED)).sum()),
        live_ticks=int(arr["live_ticks"][sel].sum()),
        arrivals=arrivals,
        arrivals_per_min=arrivals / minutes if minutes > 0 else 0.0,
        all=_arrivals(arr, sel),
        near=_arrivals(arr, sel & ~far),
        far=_arrivals(arr, sel & far),
    )


def summarise(tally: Tally) -> FollowSummary:
    """Reduce a tally to a ``FollowSummary``."""
    arr = tally.instances.arrays()
    duty: dict[str, dict[str, float]] = {}
    ticks: dict[str, dict[str, int]] = {}
    for (hid, k), n in sorted(tally.duty_ticks.items()):
        name = tally.hull_names.get(hid, str(hid))
        duty.setdefault(name, {})[KINDS[k]] = tally.duty_sum[(hid, k)] / n if n else 0.0
        ticks.setdefault(name, {})[KINDS[k]] = n
    return FollowSummary(
        attack=summarise_attack(arr),
        defend=summarise_defend(arr, tally.ward_ticks, tally.ward_hull_lost),
        goto=summarise_goto(arr, tally.ship_ticks),
        ship_minutes=_minutes(tally.ship_ticks),
        engine_duty=duty,
        duty_ticks=ticks,
    )


@dataclass(frozen=True)
class OrdersResult:
    """Outcome of ``evaluate``; JSON schema ``SCHEMA``.

    ``scenarios`` is keyed ``"<mission>/<commander>/<pass>"``; ``by_commander[mode]
    [pass]`` pools the missions (what the gates read).
    """

    a: str
    b: str
    config: OrdersEvalConfig
    scenarios: dict[str, FollowSummary]
    by_commander: dict[str, dict[str, FollowSummary]]
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
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

        def follow(raw: dict[str, Any]) -> FollowSummary:
            attack = dict(raw["attack"])
            attack["close"] = Timing(**attack["close"])
            goto = dict(raw["goto"])
            for key in ("all", "near", "far"):
                goto[key] = Arrivals(**goto[key])
            return FollowSummary(
                attack=AttackSummary(**attack),
                defend=DefendSummary(**raw["defend"]),
                goto=GotoSummary(**goto),
                ship_minutes=raw["ship_minutes"],
                engine_duty=raw["engine_duty"],
                duty_ticks=raw["duty_ticks"],
            )

        config = dict(data["config"])
        for key in ("missions", "commanders", "passes", "hidden_commanders"):
            config[key] = tuple(config[key])
        return cls(
            a=data["a"],
            b=data["b"],
            config=OrdersEvalConfig(**config),
            scenarios={k: follow(v) for k, v in data["scenarios"].items()},
            by_commander={
                mode: {p: follow(v) for p, v in passes.items()}
                for mode, passes in data["by_commander"].items()
            },
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

        def num(v: float | None, fmt: str = ".3f") -> str:
            return "–" if v is None else format(v, fmt)

        lines = [
            f"**{self.a}** following orders (opponent {self.b})",
            "",
            "| scenarios | attack: close ticks | attack: dmg share | defend: hull "
            "lost / ward-min | defend: ward-min | defend: threat share | defend: "
            "dist m | go-to: in time (n) | near | far | arrivals/min "
            "| instances a/d/g |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        rows: list[tuple[str, FollowSummary]] = [
            (f"{mode}/{p}", f)
            for mode, passes in self.by_commander.items()
            for p, f in passes.items()
        ]
        for name, f in [*rows, *self.scenarios.items()]:
            g, d = f.goto, f.defend
            lines.append(
                f"| {name} | {ticks(f.attack.close)} | {f.attack.damage_share:.3f} | "
                f"{num(d.hull_lost_per_ward_minute)} | {d.ward_minutes:.0f} | "
                f"{d.threat_share:.3f} | {num(d.mean_distance_m, '.0f')} | "
                f"{g.all.in_time:.3f} ({g.all.n}) | {g.near.in_time:.3f} "
                f"({g.near.n}) | {g.far.in_time:.3f} ({g.far.n}) | "
                f"{g.arrivals_per_min:.2f} | "
                f"{f.attack.instances}/{d.instances}/{g.instances} |"
            )
        lines += ["", "| scenarios | hull | " + " | ".join(KINDS) + " |"]
        lines.append("|---|---|" + "---|" * len(KINDS))
        for name, f in rows:
            for hull, by_kind in f.engine_duty.items():
                cells = [f"{by_kind[k]:.2f}" if k in by_kind else "–" for k in KINDS]
                lines.append(f"| {name} | {hull} | " + " | ".join(cells) + " |")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Running the matches
# ---------------------------------------------------------------------------


def _obs_measurements(
    obs: NDArray[np.float32], radius: NDArray[np.float64]
) -> dict[str, NDArray[Any]]:
    """Per-slot measurements from ``[N, S, OBS_DIM]`` obs that hiding orders does
    not touch: live, gun range, speed cap and engine level."""
    r = radius[:, None]
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
        "gun_range": np.where(turret_present, ranges, 0.0).max(axis=-1),
        "speed_cap": obs[..., SELF_SPEED_CAP].astype(np.float64) * VS,
        "engine_level": level,
    }


def read_positions(
    env: RustVecEnv, envs: NDArray[np.bool_], out: NDArray[np.float64]
) -> None:
    """World positions of every slot of the ``envs`` matches into ``out`` [N, S, 2]
    (``render_state``)."""
    for i in np.flatnonzero(envs):
        for ship in env.raw.render_state(int(i))["ships"]:
            out[i, int(ship["slot"])] = ship["pos"]


def run_scenario(
    a: Controller,
    b: Controller,
    mission: str,
    commanders: str,
    cfg: OrdersEvalConfig,
    seed: int,
    n_threads: int,
    hidden: bool,
    assets_dir: Path = ASSETS,
) -> Tally:
    """Play one mission under one commander mode; side ``a``'s tally.

    Raises:
        RuntimeError: A match did not end in time.
    """
    me: MissionEnv = build_mission_env(
        mission,
        cfg.n_for(commanders),
        seed,
        commanders,
        n_threads,
        cfg.reaction_ticks,
        assets_dir,
        hide_a=hidden,
    )
    env = me.env
    n, s = env.n_envs, env.n_ships
    team = env.team.astype(np.int64).copy()
    a_rows = team == me.a_team[:, None]
    b_rows = team == (1 - me.a_team)[:, None]
    strike = (team >= 0) & ~me.capital
    tracker = OrderTracker(a_rows & strike, env.hull_id)
    tracker.tally.hull_names = hull_names_by_id(env)
    radius = env.arena_radius.astype(np.float64).copy()
    positions = np.zeros((n, s, 2))
    running = np.ones(n, dtype=bool)
    a.reset(seed)
    b.reset(seed + 1)
    max_steps = int(round(me.time_limit_s * TICK_HZ)) + 2
    for tick in range(max_steps):
        m = _obs_measurements(env.obs, radius)
        live = m["live"] & running[:, None]
        tracks = Tracks.from_env(env.order_tracks())
        has_pos = tracker.position_envs(live, tracks, tick % POS_EVERY == 0)
        has_pos &= running
        read_positions(env, has_pos, positions)
        tracker.observe(
            live,
            tracks,
            positions,
            has_pos,
            m["gun_range"],
            m["speed_cap"],
            m["engine_level"],
        )
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
        _record_hits(tracker, info.hits, info.hit_count, running, env.ward_threat)
        tracker.add_ward_loss(env.ward_hull_lost, running)
        ending = running & dones
        if ending.any():
            tracker.end_matches(ending)
        running &= ~dones
        if not running.any():
            break
    else:
        raise RuntimeError(f"{mission}/{commanders}: matches did not end in time")
    tracker.finish()
    return tracker.tally


def _record_hits(
    tracker: OrderTracker,
    hits: NDArray[np.int32],
    hit_count: NDArray[np.int32],
    running: NDArray[np.bool_],
    ward_threat: NDArray[np.bool_],
) -> None:
    valid = (np.arange(hits.shape[1]) < hit_count[:, None]) & running[:, None]
    if not valid.any():
        return
    env_ids, _ = np.nonzero(valid)
    rows = hits[valid]
    amount = rows[:, F.HIT_DAMAGE] / float(rlf_sim.HIT_DAMAGE_SCALE)
    tracker.add_hits(
        env_ids.astype(np.int64),
        rows[:, F.HIT_SHOOTER].astype(np.int64),
        rows[:, F.HIT_TARGET].astype(np.int64),
        amount,
        np.asarray(ward_threat, dtype=bool),
    )


def scenario_seed(cfg: OrdersEvalConfig, mission: str, commanders: str) -> int:
    """The seed of one (mission, commander) scenario; both passes share it."""
    mi = cfg.missions.index(mission)
    ci = cfg.commanders.index(commanders)
    return cfg.seed + 100_003 * mi + 7_919 * ci


def evaluate(
    a: Controller,
    b: Controller,
    cfg: OrdersEvalConfig | None = None,
    n_threads: int = 12,
    assets_dir: Path = ASSETS,
) -> OrdersResult:
    """Play every (mission, commander mode, pass) of ``cfg``; side ``a`` is
    measured.

    Raises:
        ValueError: An unknown pass.
    """
    cfg = cfg or OrdersEvalConfig()
    unknown = set(cfg.passes) - set(PASSES)
    if unknown:
        raise ValueError(f"unknown passes {sorted(unknown)}; known: {PASSES}")
    scenarios: dict[str, FollowSummary] = {}
    pooled: dict[str, dict[str, Tally]] = {}
    for commanders in cfg.commanders:
        for mission in cfg.missions:
            seed = scenario_seed(cfg, mission, commanders)
            for pass_ in cfg.passes_for(commanders):
                tally = run_scenario(
                    a,
                    b,
                    mission,
                    commanders,
                    cfg,
                    seed,
                    n_threads,
                    pass_ == HIDDEN,
                    assets_dir,
                )
                scenarios[f"{mission}/{commanders}/{pass_}"] = summarise(tally)
                pooled.setdefault(commanders, {}).setdefault(pass_, Tally()).merge(
                    tally
                )
    by_commander = {
        mode: {p: summarise(t) for p, t in passes.items()}
        for mode, passes in pooled.items()
    }
    return OrdersResult(a.label, b.label, cfg, scenarios, by_commander)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: run one evaluation, print Markdown, write JSON."""
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--a", required=True, help="checkpoint or script")
    p.add_argument("--b", default="script", help="the other side's pilot")
    p.add_argument("--missions", nargs="+", default=list(DEFAULT_MISSIONS))
    p.add_argument("--commanders", nargs="+", default=list(DEFAULT_COMMANDERS))
    p.add_argument("--passes", nargs="+", default=list(PASSES), choices=PASSES)
    p.add_argument(
        "--hidden-commanders",
        nargs="+",
        default=[RANDOM],
        help="commander modes the hidden pass runs under",
    )
    p.add_argument("--n-per-scenario", type=int, default=192)
    p.add_argument(
        "--n-scripted", type=int, default=0, help="scripted-commander n (0: same)"
    )
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--n-threads", type=int, default=12)
    p.add_argument("--argmax", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    cfg = OrdersEvalConfig(
        missions=tuple(args.missions),
        commanders=tuple(args.commanders),
        passes=tuple(args.passes),
        hidden_commanders=tuple(args.hidden_commanders),
        n_per_scenario=args.n_per_scenario,
        n_scripted=args.n_scripted,
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
