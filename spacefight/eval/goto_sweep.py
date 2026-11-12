"""The go-to deadline sweep (``docs/PILOT_TRAINING.md`` §2): what does a pilot do with the
time a go-to order gives it?

The go-to version of the swap test. One ship, alone on its team, is given a go-to under
drill rules, and the same start is replayed at different time allowances: slack 0.8 to 8
(``spacefight.env.drills.goto_order_deadline_tick``, so 0.8 and 1.0 are at or past what
a ship can do and show whether it still goes) and once with no deadline. A pilot that
understands the allowance changes what it does with it; a pilot that ignores the number
flies the same way every time.

**Layouts.** Hull x distance to the circle's edge x radius x opposition x
``seeds_per_cell`` (``DrillGenerator.single_goto``: the start, heading and start speed are
drawn as a go-to drill's are, and are the same for the three oppositions of a cell).
Opposition: ``parked`` (one enemy fighter at rest on the rim, far from the start and the
point, given idle actions here), ``one`` (one script fighter beside the route) and
``three`` (a script fighter, strafer and gunship beside the route).

**Matches.** Every level plays the same layouts in the same env slots with the same base
seed, so a layout's match seed does not depend on the level. The clock stops
``CLOCK_EXTRA_TICKS`` (20 s) after the deadline, so what the ship does after it is seen.
With no deadline the ship is judged by the old rule (twice the straight-line time plus
10 s) and the clock stops 20 s after that.

**Measures**, per level, and by opposition, hull and distance:

- ``in_time``: the share of ships alive at the deadline that were inside the circle by
  it. ``died`` counts the ships killed before the deadline without arriving, apart.
- ``arrival_s`` and ``arrival_share``: the median seconds from the order to first being
  inside the circle, and that time over the allowance (deadline minus order). Over the
  ships not killed before their deadline; one that never got there by the end of the
  match counts as never, so the median is null when half or more did not. An arrival in
  time has the sim's tick; a later one is the first position read inside the circle
  (every ``POLL_TICKS``).
- ``leave_s``: the median seconds from the order until the ship is first within half of
  the distance to the circle's edge it had when the order landed. Over every ship, one
  that never was (killed first, or went elsewhere) counting as never; null when half or
  more never were.
- ``damage_dealt`` and ``damage_taken``: gun damage (hull and shield points) up to the
  ship's arrival or its deadline, whichever is first; mean.

**Headlines.** ``in_time_feasible``: in time at slack 1.5 and over.
``arrival_time_ratio``: the median arrival seconds at slack 8 over slack 1.5, on the
layouts where the ship was inside the circle within the slack-1.5 allowance at both
(the same window for both levels, ``_arrival_time_ratio``); 1 means it ignores the
allowance. With it, the share of all layouts inside the circle within that window at
each level: equal if it ignores the allowance, lower at slack 8 if it used the time.
``hits_bought``: the mean damage dealt before arriving or the deadline at slack 8 minus
at slack 1.5, layout by layout, against ``one`` and ``three``. A ship that never arrives
also deals more with a later deadline, so it is read with the in-time share.

    python -m spacefight.eval.goto_sweep --a ckpt.pt --name followers_1793 --out sweep.json
    python -m spacefight.eval.goto_sweep --a script --out script.json
    python -m spacefight.eval.goto_sweep --a nodeadline:ckpt.pt --out blind.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.drills import (
    NO_SLACK,
    ORDER_TICK,
    TICK_HZ,
    DrillGenerator,
    DrillSpec,
)
from spacefight.env.rosters import DEFAULT_ASSETS, EXTERNAL, FLEET_HULLS
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval.controllers import Controller, idle_actions, make_controller
from spacefight.eval.drills import POLL_TICKS, Mean, Rate, check_orders_landed

SCHEMA = "rlf.eval.goto_sweep/1"
DEFAULT_SEED = 700_000
PARKED, ONE, THREE = "parked", "one", "three"
# Opposition -> the enemies' hulls.
OPPOSITIONS: dict[str, tuple[str, ...]] = {
    PARKED: ("fighter",),
    ONE: ("fighter",),
    THREE: ("fighter", "strafer", "gunship"),
}
DISTANCES_M = (150.0, 300.0, 500.0)
RADII_M = (20.0, 60.0)
SLACKS = (0.8, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0)
# The level with no deadline in the order, in tables and JSON keys.
NO_DEADLINE_LEVEL = "none"
# The clock runs this far past the tick a ship is judged by: 20 s.
CLOCK_EXTRA_TICKS = 20 * TICK_HZ
# The headlines compare these two slacks, and count "feasible" from the first.
TIGHT_SLACK, LOOSE_SLACK = 1.5, 8.0
# The pilot's slot: it is alone on team 0.
PILOT = 0
# Columns of the env's hits buffer (SIM_SPEC §10.1).
_HIT_SHOOTER, _HIT_TARGET, _HIT_DAMAGE = 0, 1, 3
NEVER = math.inf


def level_name(slack: float) -> str:
    """A slack's name in tables and JSON keys: ``1.5``, ``8``, ``none``."""
    return NO_DEADLINE_LEVEL if slack == NO_SLACK else f"{slack:g}"


@dataclass(frozen=True)
class SweepConfig:
    """One sweep.

    Attributes:
        seeds_per_cell: Layouts per hull, distance, radius and opposition.
        seed: Base of the layouts' and the matches' seeds.
        hulls: The pilot's hulls.
        distances_m: Distances from the start to the circle's edge.
        radii_m: Circle radii.
        oppositions: Names of ``OPPOSITIONS``.
        slacks: The time allowances; the level with no deadline is always played too.

    Raises:
        ValueError: A size that is not positive, an unknown hull or opposition, a slack
            that is not positive, or slacks without the two the headlines compare.
    """

    seeds_per_cell: int = 6
    seed: int = DEFAULT_SEED
    hulls: tuple[str, ...] = FLEET_HULLS
    distances_m: tuple[float, ...] = DISTANCES_M
    radii_m: tuple[float, ...] = RADII_M
    oppositions: tuple[str, ...] = tuple(OPPOSITIONS)
    slacks: tuple[float, ...] = SLACKS
    sim_version: int = int(rlf_sim.SIM_VERSION)

    def __post_init__(self) -> None:
        if self.seeds_per_cell <= 0:
            raise ValueError(
                f"seeds_per_cell must be positive, got {self.seeds_per_cell}"
            )
        axes = (self.hulls, self.distances_m, self.radii_m, self.oppositions)
        if any(len(axis) == 0 for axis in axes):
            raise ValueError("every axis of the sweep needs a value")
        unknown = [h for h in self.hulls if h not in FLEET_HULLS]
        unknown += [o for o in self.oppositions if o not in OPPOSITIONS]
        if unknown:
            raise ValueError(f"unknown hulls or oppositions: {unknown}")
        if min(*self.distances_m, *self.radii_m, *self.slacks) <= 0:
            raise ValueError("distances, radii and slacks must be positive")
        if TIGHT_SLACK not in self.slacks or LOOSE_SLACK not in self.slacks:
            raise ValueError(
                f"slacks must include {TIGHT_SLACK} and {LOOSE_SLACK}, which the "
                f"headlines compare; got {self.slacks}"
            )

    @property
    def levels(self) -> tuple[float, ...]:
        """Every slack played, the level with no deadline (``NO_SLACK``) last."""
        return (*self.slacks, NO_SLACK)


@dataclass(frozen=True)
class Layout:
    """One start of the sweep.

    Attributes:
        hull: The pilot's hull.
        distance_m: From its start to the circle's edge.
        radius_m: The circle's radius.
        opposition: A name of ``OPPOSITIONS``.
        spec: The go-to, with no deadline yet (``DrillGenerator.with_slack``).
    """

    hull: str
    distance_m: float
    radius_m: float
    opposition: str
    spec: DrillSpec


def build_layouts(
    cfg: SweepConfig, assets_dir: Path = DEFAULT_ASSETS
) -> tuple[Layout, ...]:
    """Every layout of ``cfg``. The three oppositions of a hull, distance, radius and
    seed share a layout seed, so the pilot starts in the same place against each."""
    gen = DrillGenerator(assets_dir)
    layouts = []
    cell = 0
    for hull in cfg.hulls:
        for distance in cfg.distances_m:
            for radius in cfg.radii_m:
                for k in range(cfg.seeds_per_cell):
                    seed = cfg.seed + cell * cfg.seeds_per_cell + k
                    for opposition in cfg.oppositions:
                        spec = gen.single_goto(
                            seed,
                            hull,
                            distance,
                            radius,
                            OPPOSITIONS[opposition],
                            parked=opposition == PARKED,
                        )
                        layouts.append(Layout(hull, distance, radius, opposition, spec))
                cell += 1
    return tuple(layouts)


@dataclass
class Flight:
    """One layout flown at one time allowance.

    Attributes:
        layout: The layout.
        slack: The allowance; ``NO_SLACK`` for no deadline.
        deadline: The tick the ship is judged by.
        start_edge_m: Its distance to the circle's edge when the order landed.
        arrived_tick: The tick the sim first showed it arrived (with a deadline, only
            an arrival in time); -1 never.
        inside_tick: The tick of the first position read inside the circle; -1 never.
        half_tick: The tick of the first position read within half ``start_edge_m`` of
            the circle; -1 never.
        gone_tick: The tick it was first seen dead, or its match ended; -1 neither.
        dealt: Gun damage it dealt up to its arrival or deadline.
        taken: Gun damage it took up to its arrival or deadline.
    """

    layout: Layout
    slack: float
    deadline: int
    start_edge_m: float = 0.0
    arrived_tick: int = -1
    inside_tick: int = -1
    half_tick: int = -1
    gone_tick: int = -1
    dealt: float = 0.0
    taken: float = 0.0

    def outcome(self) -> str:
        """``arrived`` (by the deadline), ``died`` (killed before it without arriving)
        or ``late``."""
        if 0 <= self.arrived_tick <= self.deadline:
            return "arrived"
        if 0 <= self.gone_tick < self.deadline:
            return "died"
        return "late"

    @property
    def allowance_s(self) -> float:
        """Seconds from the order to the deadline."""
        return (self.deadline - ORDER_TICK) / TICK_HZ

    @property
    def arrival_s(self) -> float:
        """Seconds from the order to first being inside the circle; ``NEVER`` if it
        was not by the end of the match."""
        ticks = [t for t in (self.arrived_tick, self.inside_tick) if t >= 0]
        return (min(ticks) - ORDER_TICK) / TICK_HZ if ticks else NEVER

    @property
    def leave_s(self) -> float:
        """Seconds from the order to being within half the start distance of the
        circle; ``NEVER`` if it never was."""
        if self.half_tick < 0:
            return NEVER
        return (self.half_tick - ORDER_TICK) / TICK_HZ


class _Tracker:
    """The arrays one level's matches fill, one row per env (the pilot is slot 0)."""

    def __init__(self, specs: Sequence[DrillSpec]) -> None:
        n = len(specs)
        self.point = np.array([s.point for s in specs], dtype=np.float64)
        self.radius = np.array([s.radius for s in specs], dtype=np.float64)
        self.deadline = np.array([s.deadlines[PILOT] for s in specs], dtype=np.int64)
        self.start_edge = np.zeros(n)
        self.arrived_tick = np.full(n, -1, dtype=np.int64)
        self.inside_tick = np.full(n, -1, dtype=np.int64)
        self.half_tick = np.full(n, -1, dtype=np.int64)
        self.gone_tick = np.full(n, -1, dtype=np.int64)
        self.dealt = np.zeros(n)
        self.taken = np.zeros(n)

    def see_tracks(
        self, env: RustVecEnv, running: NDArray[np.bool_], tick: int
    ) -> None:
        """Note the first tick the sim shows each pilot arrived, and dead."""
        arrived = np.asarray(env.order_tracks()["arrived"], dtype=np.bool_)[:, PILOT]
        alive = np.asarray(env.raw.alive, dtype=np.bool_)[:, PILOT]
        self.arrived_tick[running & arrived & (self.arrived_tick < 0)] = tick
        self.gone_tick[running & ~alive & (self.gone_tick < 0)] = tick

    def see_positions(
        self, env: RustVecEnv, running: NDArray[np.bool_], tick: int
    ) -> None:
        """Read the position of every pilot that has not yet been inside its circle."""
        for i in np.flatnonzero(running & (self.inside_tick < 0)):
            ship = env.raw.render_state(int(i))["ships"][PILOT]
            if not ship["alive"]:
                continue
            gap = math.hypot(*(np.asarray(ship["pos"]) - self.point[i]))
            edge = max(0.0, gap - self.radius[i])
            if tick == ORDER_TICK:
                self.start_edge[i] = edge
            if self.half_tick[i] < 0 and edge <= self.start_edge[i] / 2.0:
                self.half_tick[i] = tick
            if edge == 0.0:
                self.inside_tick[i] = tick

    def add_hits(
        self,
        hits: NDArray[np.int32],
        hit_count: NDArray[np.int32],
        running: NDArray[np.bool_],
        tick: int,
    ) -> None:
        """Book the gun damage of the step that ended at ``tick``, for the pilots that
        had not arrived before it and whose deadline had not passed."""
        counted = running & (self.arrived_tick < 0) & (tick <= self.deadline)
        count = hit_count * counted
        if not count.any():
            return
        env_ids, k = np.nonzero(np.arange(hits.shape[1]) < count[:, None])
        rows = hits[env_ids, k]
        amount = rows[:, _HIT_DAMAGE] / float(rlf_sim.HIT_DAMAGE_SCALE)
        by_pilot = rows[:, _HIT_SHOOTER] == PILOT
        on_pilot = rows[:, _HIT_TARGET] == PILOT
        np.add.at(self.dealt, env_ids[by_pilot], amount[by_pilot])
        np.add.at(self.taken, env_ids[on_pilot], amount[on_pilot])

    def flights(self, layouts: Sequence[Layout], slack: float) -> list[Flight]:
        """One ``Flight`` per env."""
        return [
            Flight(
                layout,
                slack,
                int(self.deadline[i]),
                float(self.start_edge[i]),
                int(self.arrived_tick[i]),
                int(self.inside_tick[i]),
                int(self.half_tick[i]),
                int(self.gone_tick[i]),
                float(self.dealt[i]),
                float(self.taken[i]),
            )
            for i, layout in enumerate(layouts)
        ]


def _level_env(
    specs: Sequence[DrillSpec], seed: int, n_threads: int, assets_dir: Path
) -> RustVecEnv:
    """An env whose match ``i`` is ``specs[i]``, at tick 0."""
    env = RustVecEnv(
        assets_dir,
        len(specs),
        specs[0].roster().fleets(),
        seed,
        n_threads=n_threads,
        max_ships=max(spec.roster().n_ships for spec in specs),
        commanders=(EXTERNAL, EXTERNAL),
    )
    for i, spec in enumerate(specs):
        env.set_next_roster(i, spec.roster())
    env.reset()
    return env


def run_level(
    controller: Controller,
    layouts: Sequence[Layout],
    slack: float,
    seed: int,
    n_threads: int = 4,
    assets_dir: Path = DEFAULT_ASSETS,
) -> list[Flight]:
    """Fly every layout once at ``slack``, ``controller`` flying the pilot.

    Env ``i`` plays ``layouts[i]`` with match seed ``split(seed, i, 0)``, whatever the
    slack. Enemies fly their scripts, but a parked one gets idle actions.

    Args:
        controller: Flies the pilot.
        layouts: The layouts (``build_layouts``).
        slack: The time allowance; ``NO_SLACK`` for no deadline.
        seed: Base seed of the matches.
        n_threads: Sim threads.
        assets_dir: Hull and weapon YAML.

    Returns:
        One flight per layout, in order.

    Raises:
        RuntimeError: A match did not end on its clock, or a pilot never got its order.
        ValueError: No layouts.
    """
    if not layouts:
        raise ValueError("run_level needs at least one layout")
    gen = DrillGenerator(assets_dir)
    specs = [gen.with_slack(lay.spec, slack, CLOCK_EXTRA_TICKS) for lay in layouts]
    env = _level_env(specs, seed, n_threads, assets_dir)
    n, s = env.n_envs, env.n_ships
    team = env.team.astype(np.int64).copy()
    pilots = team == 0
    parked = np.array([lay.opposition == PARKED for lay in layouts])
    scripted = (team == 1) & ~parked[:, None]
    tracker = _Tracker(specs)
    running = np.ones(n, dtype=np.bool_)
    controller.reset(seed)
    for tick in range(max(spec.clock_ticks for spec in specs) + 2):
        if tick == ORDER_TICK + 1:
            check_orders_landed(env, specs, running)
        tracker.see_tracks(env, running, tick)
        if tick >= ORDER_TICK and tick % POLL_TICKS == 0:
            tracker.see_positions(env, running, tick)
        decide = running[:, None] & env.act_mask
        actions = idle_actions(n * s).reshape(n, s, -1)
        rows = decide & scripted
        if rows.any():
            actions[rows] = env.scripted_actions()[rows]
        rows = decide & pilots
        if rows.any():
            actions[rows] = controller.act(env, rows)
        _, _, dones, info = env.step(actions)
        tracker.add_hits(info.hits, info.hit_count, running, tick + 1)
        ending = running & dones
        # A match that ends with its pilot neither arrived nor seen dead: it died on
        # this step, or its go-to was over and the enemies were gone.
        still_open = ending & (tracker.gone_tick < 0) & (tracker.arrived_tick < 0)
        tracker.gone_tick[still_open] = tick + 1
        running &= ~dones
        if not running.any():
            break
    else:
        raise RuntimeError("sweep matches did not end on their clocks")
    return tracker.flights(layouts, slack)


# -- summaries --------------------------------------------------------------------------


def _median(values: Sequence[float]) -> float | None:
    """The median, ``NEVER`` counting as later than any time; ``None`` when there is
    no value or the median is ``NEVER`` (half or more never did)."""
    if not values:
        return None
    middle = float(np.median(np.asarray(values, dtype=np.float64)))
    return middle if math.isfinite(middle) else None


def measure(flights: Sequence[Flight]) -> dict[str, Any]:
    """The module docstring's measures over ``flights`` (one level, or part of one)."""
    outcomes = [f.outcome() for f in flights]
    arrived, late = outcomes.count("arrived"), outcomes.count("late")
    alive = [f for f, outcome in zip(flights, outcomes) if outcome != "died"]
    reached = sum(math.isfinite(f.arrival_s) for f in alive)
    return {
        "n": len(flights),
        "died": outcomes.count("died"),
        "in_time": asdict(Rate.of(arrived, arrived + late)),
        "reached": asdict(Rate.of(reached, len(alive))),
        "arrival_s": _median([f.arrival_s for f in alive]),
        "arrival_share": _median([f.arrival_s / f.allowance_s for f in alive]),
        "allowance_s": _median([f.allowance_s for f in flights]),
        "leave_s": _median([f.leave_s for f in flights]),
        "damage_dealt": asdict(Mean.of([f.dealt for f in flights])),
        "damage_taken": asdict(Mean.of([f.taken for f in flights])),
    }


def summarise_level(flights: Sequence[Flight]) -> dict[str, Any]:
    """One level: its measures over every layout, and by opposition, hull and
    distance."""

    def split(key: Callable[[Layout], str]) -> dict[str, Any]:
        groups: dict[str, list[Flight]] = {}
        for flight in flights:
            groups.setdefault(key(flight.layout), []).append(flight)
        return {name: measure(group) for name, group in groups.items()}

    return {
        "all": measure(flights),
        "by_opposition": split(lambda lay: lay.opposition),
        "by_hull": split(lambda lay: lay.hull),
        "by_distance": split(lambda lay: f"{lay.distance_m:g}"),
    }


def _arrival_time_ratio(
    tight: Sequence[Flight], loose: Sequence[Flight]
) -> dict[str, Any]:
    """Median arrival seconds at the loose slack over the tight one, and how many
    layouts it is over.

    Both levels are read through the same window, the tight level's allowance: an
    arrival after it counts as none at either level. At the tight level the order is
    over by then and the match ends 20 s later, so later arrivals cannot be compared;
    pairing instead on "reached at both, whenever" picks the tight level's quick
    flights and the loose level's every flight, which reads above 1 for any pilot
    whose flights vary. ``early_tight`` and ``early_loose`` are the shares of all
    layouts inside the circle within that window at each level: a pilot that ignores
    the allowance has the same share at both, one that uses its time has fewer at the
    loose level. ``ratio`` is null when no layout made the window at both levels.
    """
    windows = [a.allowance_s for a in tight]
    early_tight = [a.arrival_s <= w for a, w in zip(tight, windows, strict=True)]
    early_loose = [b.arrival_s <= w for b, w in zip(loose, windows, strict=True)]
    both = [x and y for x, y in zip(early_tight, early_loose)]
    out: dict[str, Any] = {
        "ratio": None,
        "layouts": sum(both),
        "tight_s": None,
        "loose_s": None,
        "early_tight": asdict(Rate.of(sum(early_tight), len(tight))),
        "early_loose": asdict(Rate.of(sum(early_loose), len(loose))),
    }
    if any(both):
        out["tight_s"] = float(
            np.median([a.arrival_s for a, k in zip(tight, both) if k])
        )
        out["loose_s"] = float(
            np.median([b.arrival_s for b, k in zip(loose, both) if k])
        )
        out["ratio"] = out["loose_s"] / out["tight_s"]
    return out


def _hits_bought(tight: Sequence[Flight], loose: Sequence[Flight]) -> dict[str, Any]:
    """Mean damage dealt before arriving at the loose slack minus at the tight one,
    layout by layout, for each opposition whose enemies fly."""
    out: dict[str, Any] = {}
    for opposition in (ONE, THREE):
        gains = [
            b.dealt - a.dealt
            for a, b in zip(tight, loose, strict=True)
            if a.layout.opposition == opposition
        ]
        if gains:
            out[opposition] = asdict(Mean.of(gains))
    return out


def headlines(by_slack: Mapping[float, Sequence[Flight]]) -> dict[str, Any]:
    """The three headline numbers (module docstring)."""
    feasible = [
        f.outcome()
        for slack, flights in by_slack.items()
        if slack >= TIGHT_SLACK
        for f in flights
    ]
    arrived, late = feasible.count("arrived"), feasible.count("late")
    tight, loose = by_slack[TIGHT_SLACK], by_slack[LOOSE_SLACK]
    return {
        "in_time_feasible": asdict(Rate.of(arrived, arrived + late)),
        "arrival_time_ratio": _arrival_time_ratio(tight, loose),
        "hits_bought": _hits_bought(tight, loose),
        "tight_slack": TIGHT_SLACK,
        "loose_slack": LOOSE_SLACK,
    }


# -- the eval ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepResult:
    """Outcome of ``evaluate``; JSON schema ``SCHEMA``.

    Attributes:
        pilot: The controller's label.
        name: The pilot's name in the report.
        config: The sweep.
        n_layouts: Layouts flown at every level.
        headline: ``headlines``.
        levels: Level name (``level_name``) -> ``summarise_level``.
    """

    pilot: str
    name: str
    config: SweepConfig
    n_layouts: int
    headline: dict[str, Any]
    levels: dict[str, Any]
    schema: str = SCHEMA
    clock_extra_s: float = CLOCK_EXTRA_TICKS / TICK_HZ

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return asdict(self)

    def to_json(self) -> str:
        """Indented JSON text."""
        return json.dumps(self.to_dict(), indent=1)

    def to_markdown(self) -> str:
        """A plain report."""
        return report_markdown(self)


def evaluate(
    controller: Controller,
    name: str,
    cfg: SweepConfig | None = None,
    n_threads: int = 4,
    assets_dir: Path = DEFAULT_ASSETS,
) -> SweepResult:
    """Fly every layout of ``cfg`` at every time allowance.

    Args:
        controller: The pilot.
        name: The pilot's name in the report.
        cfg: The sweep (default ``SweepConfig()``).
        n_threads: Sim threads.
        assets_dir: Hull and weapon YAML.
    """
    cfg = cfg or SweepConfig()
    layouts = build_layouts(cfg, assets_dir)
    by_slack = {
        slack: run_level(controller, layouts, slack, cfg.seed, n_threads, assets_dir)
        for slack in cfg.levels
    }
    return SweepResult(
        pilot=controller.label,
        name=name,
        config=cfg,
        n_layouts=len(layouts),
        headline=headlines(by_slack),
        levels={
            level_name(slack): summarise_level(flights)
            for slack, flights in by_slack.items()
        },
    )


def _num(value: float | None, digits: int = 1) -> str:
    """A number for a table; ``-`` for a median that half or more never reached."""
    return "-" if value is None else f"{value:.{digits}f}"


def _level_table(levels: Mapping[str, Any], pick: Callable[[Any], Any]) -> list[str]:
    """One row per level: slack, in time, arrival over allowance, leave, damage."""
    lines = [
        "| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |",
        "|---|---|---|---|---|---|",
    ]
    for level, summary in levels.items():
        part = pick(summary)
        lines.append(
            f"| {level} | {part['in_time']['rate']:.2f} "
            f"| {_num(part['arrival_share'], 2)} | {_num(part['leave_s'])} "
            f"| {part['damage_dealt']['mean']:.1f} | {part['damage_taken']['mean']:.1f} |"
        )
    return lines


def _headline_lines(headline: Mapping[str, Any]) -> list[str]:
    ratio = headline["arrival_time_ratio"]
    tight, loose = f"{headline['tight_slack']:g}", f"{headline['loose_slack']:g}"
    bought = ", ".join(
        f"{opposition} {Mean(**raw).mean:+.1f} +/- {Mean(**raw).se:.1f}"
        for opposition, raw in headline["hits_bought"].items()
    )
    return [
        f"- In time at slack {tight} and over: "
        f"{Rate(**headline['in_time_feasible']).text()}",
        f"- Arrival-time ratio, slack {loose} over slack {tight}: "
        f"{_num(ratio['ratio'], 2)} (median {_num(ratio['loose_s'])} s over "
        f"{_num(ratio['tight_s'])} s, on the {ratio['layouts']} layouts inside the "
        f"circle within the slack-{tight} allowance at both). 1 means it ignores the "
        "allowance.",
        f"- Inside the circle within the slack-{tight} allowance, of all layouts: "
        f"{ratio['early_tight']['rate']:.2f} at slack {tight}, "
        f"{ratio['early_loose']['rate']:.2f} at slack {loose}. The same share means "
        "it ignores the allowance; fewer at the looser one means it used the time.",
        f"- Hits bought by slack (damage dealt before arriving or the deadline, slack "
        f"{loose} minus slack {tight}, by enemies): "
        f"{bought or 'no flying enemies in this sweep'}. A ship that never arrives "
        "also deals more with a later deadline, so read this with the in-time share.",
    ]


def _opposition_part(opposition: str) -> Callable[[Any], Any]:
    """Picks one opposition's measures out of a level's summary."""

    def pick(summary: Any) -> Any:
        return summary["by_opposition"][opposition]

    return pick


def report_markdown(result: SweepResult) -> str:
    """The result as plain Markdown, slack levels as rows."""
    cfg = result.config
    untimed = result.levels[NO_DEADLINE_LEVEL]["all"]
    lines = [
        f"# Go-to deadline sweep: {result.name}",
        "",
        f"Pilot `{result.pilot}`, seed {cfg.seed}, sim version {cfg.sim_version}. One "
        f"ship alone with a go-to: {result.n_layouts} layouts, each flown at "
        f"{len(cfg.levels)} time allowances. Slack 1 is a straight line at the hull's "
        "speed cap plus 3 s to turn.",
        "",
        "## Headlines",
        "",
        *_headline_lines(result.headline),
        "",
        "## Every layout",
        "",
        *_level_table(result.levels, lambda summary: summary["all"]),
        "",
        "In time: of the ships alive at the deadline. Arrive / allowed: median time to "
        "the circle over the time allowed (- if half or more never got there by 20 s "
        "after the deadline). Leave s: median seconds until half the distance was "
        "covered. Dealt, taken: mean gun damage before arriving or the deadline. "
        "The `none` row has no deadline and is judged by twice the straight-line time "
        "plus 10 s.",
        "",
        f"No deadline: {untimed['in_time']['rate']:.2f} arrive by that rule, median "
        f"time to arrive {_num(untimed['arrival_s'])} s; "
        f"{untimed['reached']['rate']:.2f} get there within 20 s more.",
    ]
    for opposition in cfg.oppositions:
        lines += [
            "",
            f"## Enemies: {opposition}",
            "",
            *_level_table(result.levels, _opposition_part(opposition)),
        ]
    died = ", ".join(
        f"{level} {summary['all']['died']}" for level, summary in result.levels.items()
    )
    lines += [
        "",
        f"Killed before the deadline, by slack (of {result.n_layouts}): {died}.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--a",
        required=True,
        help="A checkpoint path, script, nodeadline:<checkpoint> or notime:<checkpoint>",
    )
    parser.add_argument(
        "--name", default="", help="The pilot's name (default: from --a)"
    )
    parser.add_argument(
        "--seeds-per-cell", type=int, default=SweepConfig.seeds_per_cell
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--out", type=Path, help="JSON path; the report goes beside it")
    args = parser.parse_args(argv)
    controller = make_controller(args.a, sample=True, seed=args.seed)
    name = args.name or Path(args.a).stem
    started = time.monotonic()
    result = evaluate(
        controller,
        name,
        SweepConfig(seeds_per_cell=args.seeds_per_cell, seed=args.seed),
        args.threads,
    )
    report = result.to_markdown()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result.to_json())
        args.out.with_suffix(".md").write_text(report)
    sys.stdout.write(report)
    sys.stdout.write(f"\n{time.monotonic() - started:.0f} s\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
