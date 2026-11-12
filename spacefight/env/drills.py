"""Order drills (``docs/PILOT_TRAINING.md`` §2): scenarios that keep each order's meaning
clear. A drill checks that a pilot understood what it was told, not how well it did it.

``DrillGenerator.generate(kind, seed)`` is a pure function of its arguments and the hull
YAML. It returns a ``DrillSpec``: the fleets, where every ship starts, the order and who
gets it, the clock, and what the eval needs to judge the outcome. Enemies are script
pilots. ``DrillSpec.swapped()`` is the swap partner: the same spec with the other side
named.

How a drill is played:

- **Mission.** A deathmatch under drill rules (``MatchConfig.drill``, SIM_SPEC §5.10), so
  the obs read as they do in a deathmatch, and ``external`` commanders on both teams,
  whose orders script pilots follow in a deathmatch (only the scripted commander's are
  advisory there; ``scripted::orders::active_order``). Drill rules have no result: the
  match ends on the clock, when team 0 has no strike craft left, or when team 1 is gone
  and no go-to is open, always as a draw, so no match result is paid.
- **Orders** are queued when the match is built and the sim applies them on the first
  slow tick (``ORDER_TICK``). Drill rules hold every ship in a control lock until then, so
  they coast for the first 2 s and nobody flies blind before the orders land.
- **The ordered team is team 0.** Slots: pilots, then wards; team 1 is the side-0 group,
  then the side-1 group.
- **Wards and decoys** are freighters: capital ships, never learner rows, flown by the
  transport script, which coasts with no waypoint. Each side's enemy group holds an attack
  order on its own side's freighter, which keeps the groups apart and makes "under attack"
  true however the pilot flies. An attacker falls back to its role's choice if its
  freighter dies.

Kinds:

- ``goto``: a near or far point, sometimes with enemies around the route, sometimes far
  from it. Three in four carry a deadline in the order itself (SIM_VERSION 8), one tick
  for the whole squad: a slack drawn log-uniformly from ``GOTO_SLACK`` times the slowest
  ship's straight-line time at its speed cap, plus ``GOTO_TURN_S`` to turn and get going
  (``goto_order_deadline_tick``). So in a mixed squad the fast ships have time to spare
  and the slow one is tight. The sim pays and charges by that tick and the pilot sees
  the time left. The rest (``GOTO_NO_DEADLINE_P``) carry none, as every commander's
  go-to does today; the eval then judges each ship by the old rule: its straight-line
  time doubled, plus 10 s (``goto_deadline_tick``). Neither says anything about the
  route. The match's clock runs a drawn 1 to 20 s past the last deadline, so the match's
  time left, which the pilot sees as a fraction of the clock, no longer marks the
  deadline; once it has passed the pilots have no order and fight on until the clock, as
  they would in a real match.
- ``attack``: enemy groups on opposite sides, one member of one group named. Usually each
  group is busy with a freighter on its side; sometimes (``charging``) there are no
  freighters and the groups fly straight at the pilots.
- ``defend``: two freighters on opposite sides, each attacked by its own group, one named.

**Variety** is the point, since drills replace random orders as the protection against
overfitting to one commander: hull mix, squad size 1 to 4, side and go-to distances, go-to
radius, starting speed and heading. The whole layout gets a random rotation and, half the
time, a mirror, so the named side is not fixed in the world or in the pilot's own frame.
The pilots start facing across the line between the sides, so neither side is ahead of
them.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.rosters import (
    DEFAULT_ASSETS,
    DRILL_ATTACK,
    DRILL_DEFEND,
    DRILL_GOTO,
    DRILL_KINDS,
    EXTERNAL,
    FLEET_HULLS,
    NO_DEADLINE,
    DrillTag,
    OpeningOrder,
    Roster,
    ShipStart,
    arena_radius_for,
    load_hull_speed_caps,
)

TICK_HZ = 30
# The first slow tick (``COMMAND_TICKS``): when the orders reach the ships.
ORDER_TICK = 60
# What a go-to with no deadline in its order is judged by: this many times the
# straight-line time at the hull's speed cap, plus this many seconds. "You've got to get
# there eventually."
GOTO_TIME_MULT = 2.0
GOTO_SLACK_S = 10.0
# Share of go-to drills whose order carries no deadline (all a commander issues today).
GOTO_NO_DEADLINE_P = 0.25
# The order's deadline: a slack drawn log-uniformly from this range, times the slowest
# ship's straight-line time at its speed cap, plus GOTO_TURN_S to turn and get going.
GOTO_SLACK = (2.0, 8.0)
GOTO_TURN_S = 3.0
# ``DrillSpec.slack`` of a go-to whose order carries no deadline.
NO_SLACK = 0.0
# The clock runs this many ticks (1 to 20 s, drawn per drill) past the last deadline. The
# pilot sees the share of the match that is left, so a fixed margin would give the
# deadline away; the least of it lets a reader polling the sim see an arrival on the
# deadline.
GOTO_CLOCK_EXTRA_TICKS = (30, 600)
# Attack and defend clock: long enough for a gunship (24 m/s) to cross to either side.
SIDE_CLOCK_TICKS = 900

WARD_HULL = "freighter"
MAX_PILOTS = 4
# Metres at a 450 m arena radius; generate() scales them with the arena.
REFERENCE_RADIUS = 450.0
# Sides are this far from the pilots. Past gauss range (220 m) from the centre, so a pilot
# has to move to fight either side; inside what the scripts' turn-back at 0.85 R allows.
WARD_DISTANCE = (240.0, 320.0)
ATTACKER_RING = (70.0, 110.0)
# An attacker's bearing from its freighter, off the outward line, radians, and the step it
# is swung by when the arena's edge is too near.
ATTACKER_BEARING = (math.radians(25.0), math.radians(100.0))
ATTACKER_SWING = math.radians(10.0)
CHARGE_DISTANCE = (260.0, 340.0)
# Share of attack drills whose groups fly straight at the pilots.
CHARGING_P = 0.25
ATTACKERS_PER_SIDE = (1, 2)
CHARGERS_PER_SIDE = (1, 3)
PILOT_SPACING = 30.0
# No ship starts farther than this from the centre, nor a go-to point.
START_LIMIT = 355.0
POINT_LIMIT = 395.0
GOTO_NEAR = (120.0, 300.0)
GOTO_FAR = (400.0, 745.0)
GOTO_FAR_P = 0.5
GOTO_RADIUS = (15.0, 80.0)
GOTO_ENEMIES = (1, 3)
GOTO_ENEMIES_AROUND_P = 0.5
# Enemies "around" a go-to start this far beside the route.
AROUND_ROUTE = (60.0, 180.0)
# ... and every one at least this far from the middle of the pilots' start.
START_CLEARANCE = 110.0
ENEMY_SPACING = 40.0
# How far off the sides' axis the pilots may start heading, radians.
HEADING_JITTER = 0.35
# Pilots start at up to this fraction of their speed cap, along their heading.
START_SPEED_FRAC = 0.5
WARD_MAX_SPEED = 3.0
ENEMY_START_SPEED_FRAC = 0.3
MAX_PLACEMENT_TRIES = 64
# Bearings tried for a parked ship's place on the rim.
PARKED_BEARINGS = 72


def goto_deadline_tick(distance_m: float, speed_cap: float) -> int:
    """The tick a go-to must be finished by.

    Args:
        distance_m: Straight-line distance from the ship's start to the arrival circle.
        speed_cap: The hull's speed cap, m/s.

    Raises:
        ValueError: A negative distance or a non-positive speed cap.
    """
    if distance_m < 0 or speed_cap <= 0:
        raise ValueError(f"bad go-to: {distance_m} m at {speed_cap} m/s")
    seconds = GOTO_TIME_MULT * distance_m / speed_cap + GOTO_SLACK_S
    return ORDER_TICK + int(math.ceil(seconds * TICK_HZ))


def goto_order_deadline_tick(
    slack: float, distances_m: Sequence[float], speed_caps: Sequence[float]
) -> int:
    """The deadline tick a go-to order carries, one for the whole squad.

    ``ORDER_TICK + ceil((slack * max_i(d_i / cap_i) + GOTO_TURN_S) * TICK_HZ)``: slack 1
    is the slowest ship's straight line at its speed cap from a flying start, plus the
    turn allowance. The drills and the deadline sweep (``spacefight.eval.goto_sweep``)
    both use it.

    Args:
        slack: The multiple of the slowest ship's straight-line time.
        distances_m: Each pilot's straight-line distance to the arrival circle's edge.
        speed_caps: Each pilot's hull speed cap, m/s.

    Raises:
        ValueError: No ships, lengths that differ, a slack or speed cap that is not
            positive, or a negative distance.
    """
    if not distances_m or len(distances_m) != len(speed_caps):
        raise ValueError(
            f"need one distance per speed cap, got {len(distances_m)} and "
            f"{len(speed_caps)}"
        )
    if not slack > 0 or not math.isfinite(slack):
        raise ValueError(f"slack must be positive and finite, got {slack}")
    if min(distances_m) < 0 or min(speed_caps) <= 0:
        raise ValueError(f"bad go-to: {distances_m} m at {speed_caps} m/s")
    slowest = max(d / cap for d, cap in zip(distances_m, speed_caps))
    seconds = slack * slowest + GOTO_TURN_S
    return ORDER_TICK + int(math.ceil(seconds * TICK_HZ))


@dataclass(frozen=True)
class DrillSpec:
    """One drill. ``kind``, ``seed`` and the layout never change between swap partners.

    Attributes:
        kind: One of ``DRILL_KINDS``.
        seed: The seed it was generated from.
        teams: ``(team 0 hulls, team 1 hulls)``: pilots then wards, side 0's enemies then
            side 1's.
        layout: Where each slot starts.
        pilots: The ordered strike craft's slots.
        clock_ticks: The match's time limit.
        arena_radius: The arena it was laid out for, metres.
        named_side: 0 or 1, the side the order names; 0 for a go-to.
        side_targets: For attack, the slot each side would name; for defend, each side's
            ward. Empty for a go-to.
        side_groups: Each side's enemy slots. Empty for a go-to.
        side_axis: World unit vector from side 0 toward side 1; ``(0, 0)`` for a go-to.
        enemy_orders: The orders that set each group on its freighter.
        charging: Attack only: no freighters, the groups fly at the pilots.
        point: Go-to point.
        radius: Go-to radius.
        deadline_tick: Go-to: the deadline the order carries (SIM_VERSION 8), one tick
            for the squad; ``NO_DEADLINE`` (0) when it carries none.
        slack: Go-to: the slack ``deadline_tick`` was drawn with
            (``goto_order_deadline_tick``); ``NO_SLACK`` (0.0) with no deadline.
        deadlines: Go-to: per pilot, the tick the eval judges its arrival by: the
            order's deadline when it has one, else the old rule for that ship
            (``goto_deadline_tick``).
        distances: Go-to: per pilot, the straight-line distance to the arrival circle.
        far: Go-to: a map-crossing distance.
        enemies_around: Go-to: the enemies start beside the route, not far from it.
    """

    kind: str
    seed: int
    teams: tuple[tuple[str, ...], tuple[str, ...]]
    layout: tuple[ShipStart, ...]
    pilots: tuple[int, ...]
    clock_ticks: int
    arena_radius: float
    named_side: int = 0
    side_targets: tuple[int, ...] = ()
    side_groups: tuple[tuple[int, ...], ...] = ()
    side_axis: tuple[float, float] = (0.0, 0.0)
    enemy_orders: tuple[OpeningOrder, ...] = ()
    charging: bool = False
    point: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.0
    deadline_tick: int = NO_DEADLINE
    slack: float = NO_SLACK
    deadlines: tuple[int, ...] = ()
    distances: tuple[float, ...] = ()
    far: bool = False
    enemies_around: bool = False

    @property
    def has_sides(self) -> bool:
        """Attack and defend name a side; a go-to does not."""
        return self.kind != DRILL_GOTO

    @property
    def timed(self) -> bool:
        """Whether the order carries a deadline (a go-to only)."""
        return self.deadline_tick != NO_DEADLINE

    @property
    def named_slot(self) -> int:
        """The attack target's or the ward's slot; -1 for a go-to."""
        return self.side_targets[self.named_side] if self.has_sides else -1

    def swapped(self) -> DrillSpec:
        """The swap partner: the same spec with the other side named.

        Raises:
            ValueError: A go-to, which has no sides.
        """
        if not self.has_sides:
            raise ValueError("a go-to has no side to swap")
        return replace(self, named_side=1 - self.named_side)

    def order(self) -> OpeningOrder:
        """The order the pilots get."""
        if self.kind == DRILL_GOTO:
            return OpeningOrder(
                0,
                0,
                self.pilots,
                DRILL_GOTO,
                point=self.point,
                radius=self.radius,
                deadline_tick=self.deadline_tick,
            )
        return OpeningOrder(0, 0, self.pilots, self.kind, target=self.named_slot)

    def roster(self, hidden: bool = False) -> Roster:
        """The match.

        Args:
            hidden: Hide the order from the pilots' obs (the go-to baseline). The order
                still stands for the sim; a pilot just cannot see it.
        """
        tag = DrillTag(
            kind=self.kind,
            pilots=self.pilots,
            named_slot=self.named_slot,
            named_group=(self.side_groups[self.named_side] if self.has_sides else ()),
            other_group=(
                self.side_groups[1 - self.named_side] if self.has_sides else ()
            ),
            deadlines=self.deadlines,
            timed=self.timed,
        )
        return Roster(
            teams=self.teams,
            commanders=(EXTERNAL, EXTERNAL),
            hide_orders=(hidden, False),
            start_layout=self.layout,
            opening_orders=(self.order(), *self.enemy_orders),
            time_limit_s=self.clock_ticks / TICK_HZ,
            drill=tag,
        )


class _Frame:
    """The random rotation and optional mirror of one drill's layout.

    Layouts are written with the sides on the x axis (side 0 at -x) and the pilots
    facing +y.
    """

    def __init__(self, rng: np.random.Generator) -> None:
        self.mirror = bool(rng.random() < 0.5)
        self.angle = float(rng.uniform(0.0, 2.0 * math.pi))

    def point(self, x: float, y: float) -> tuple[float, float]:
        """World position or velocity of a layout vector."""
        x = -x if self.mirror else x
        c, s = math.cos(self.angle), math.sin(self.angle)
        return (c * x - s * y, s * x + c * y)

    def heading(self, heading: float) -> float:
        """World heading of a layout heading, wrapped to ``[-pi, pi)``."""
        h = math.pi - heading if self.mirror else heading
        return (h + self.angle + math.pi) % (2.0 * math.pi) - math.pi

    def start(self, x: float, y: float, speed: float, heading: float) -> ShipStart:
        """A ship at ``(x, y)`` moving along its ``heading`` at ``speed``."""
        px, py = self.point(x, y)
        vx, vy = self.point(speed * math.cos(heading), speed * math.sin(heading))
        return ShipStart(px, py, vx, vy, self.heading(heading))


def _strike_hulls(rng: np.random.Generator, n: int) -> tuple[str, ...]:
    picks = rng.integers(len(FLEET_HULLS), size=n)
    return tuple(FLEET_HULLS[int(i)] for i in picks)


def _bearing(x: float, y: float, to_x: float, to_y: float) -> float:
    return math.atan2(to_y - y, to_x - x)


class DrillGenerator:
    """Makes ``DrillSpec``s: every draw comes from ``generate``'s own seeded generator.

    Args:
        assets_dir: Directory holding ``hulls/``, for the speed caps.
        arena_radius: The drills' arena, metres (default: the shared rule's for a drill's
            ship count, which is the same for every drill today).

    Raises:
        FileNotFoundError: No hull YAML under ``assets_dir``.
        KeyError: A drill hull missing from the assets.
    """

    def __init__(
        self,
        assets_dir: Path = DEFAULT_ASSETS,
        arena_radius: float = arena_radius_for(12),
    ) -> None:
        caps = load_hull_speed_caps(assets_dir)
        self.speed_caps = {h: caps[h] for h in (*FLEET_HULLS, WARD_HULL)}
        self.arena_radius = arena_radius
        self.scale = arena_radius / REFERENCE_RADIUS

    def generate(self, kind: str, seed: int) -> DrillSpec:
        """The ``kind`` drill of ``seed``: the same arguments give the same spec.

        Raises:
            ValueError: An unknown kind.
        """
        if kind not in DRILL_KINDS:
            raise ValueError(f"unknown drill kind {kind!r}; known: {DRILL_KINDS}")
        rng = np.random.default_rng([seed, DRILL_KINDS.index(kind), 0xD1711])
        if kind == DRILL_GOTO:
            return self._goto(seed, rng)
        return self._sides(kind, seed, rng)

    def roster(self, kind: str, seed: int) -> Roster:
        """The match of ``generate(kind, seed)``."""
        return self.generate(kind, seed).roster()

    def generate_many(self, kind: str, n: int, base_seed: int) -> tuple[DrillSpec, ...]:
        """``n`` drills of ``kind`` from consecutive seeds."""
        return tuple(self.generate(kind, base_seed + i) for i in range(n))

    def _pilots(
        self, rng: np.random.Generator, frame: _Frame, center_y: float
    ) -> tuple[tuple[str, ...], list[ShipStart]]:
        """Pilots in a file along the layout's y axis, facing +y, near neither side."""
        n = int(rng.integers(1, MAX_PILOTS + 1))
        hulls = _strike_hulls(rng, n)
        starts = []
        for k, hull in enumerate(hulls):
            y = center_y + (k - (n - 1) / 2) * PILOT_SPACING * self.scale
            x = float(rng.uniform(-8.0, 8.0)) * self.scale
            heading = math.pi / 2 + float(rng.uniform(-HEADING_JITTER, HEADING_JITTER))
            speed = float(rng.uniform(0.0, START_SPEED_FRAC)) * self.speed_caps[hull]
            starts.append(frame.start(x, y, speed, heading))
        return hulls, starts

    def _sides(self, kind: str, seed: int, rng: np.random.Generator) -> DrillSpec:
        frame = _Frame(rng)
        center_y = float(rng.uniform(-40.0, 40.0)) * self.scale
        pilot_hulls, pilot_starts = self._pilots(rng, frame, center_y)
        n_pilots = len(pilot_hulls)
        charging = kind == DRILL_ATTACK and bool(rng.random() < CHARGING_P)
        group_hulls: list[tuple[str, ...]] = []
        group_starts: list[list[ShipStart]] = []
        ward_starts: list[ShipStart] = []
        for side in (0, 1):
            sign = -1.0 if side == 0 else 1.0
            if charging:
                hulls, starts = self._chargers(rng, frame, sign, center_y)
            else:
                ward = self._ward_position(rng, sign)
                ward_starts.append(self._ward_start(rng, frame, ward))
                hulls, starts = self._attackers(rng, frame, sign, ward)
            group_hulls.append(hulls)
            group_starts.append(starts)
        n_wards = len(ward_starts)
        team0 = (*pilot_hulls, *([WARD_HULL] * n_wards))
        team1 = (*group_hulls[0], *group_hulls[1])
        first_enemy = len(team0)
        group0 = tuple(range(first_enemy, first_enemy + len(group_hulls[0])))
        group1 = tuple(range(group0[-1] + 1, first_enemy + len(team1)))
        wards = tuple(range(n_pilots, n_pilots + n_wards))
        if kind == DRILL_DEFEND:
            targets = wards
        else:
            targets = (
                group0[int(rng.integers(len(group0)))],
                group1[int(rng.integers(len(group1)))],
            )
        enemy_orders: tuple[OpeningOrder, ...] = ()
        if wards:
            enemy_orders = (
                OpeningOrder(1, 0, group0, DRILL_ATTACK, target=wards[0]),
                OpeningOrder(1, 1, group1, DRILL_ATTACK, target=wards[1]),
            )
        return DrillSpec(
            kind=kind,
            seed=seed,
            teams=(team0, team1),
            layout=(
                *pilot_starts,
                *ward_starts,
                *group_starts[0],
                *group_starts[1],
            ),
            pilots=tuple(range(n_pilots)),
            clock_ticks=SIDE_CLOCK_TICKS,
            arena_radius=self.arena_radius,
            named_side=int(rng.integers(2)),
            side_targets=targets,
            side_groups=(group0, group1),
            side_axis=frame.point(1.0, 0.0),
            enemy_orders=enemy_orders,
            charging=charging,
        )

    def _ward_position(
        self, rng: np.random.Generator, sign: float
    ) -> tuple[float, float]:
        """A side's freighter, its distance drawn per side: the nearer side must not
        always be the same one, and a pilot that simply takes the nearer fails the swap.
        """
        distance = float(rng.uniform(*WARD_DISTANCE)) * self.scale
        return (sign * distance, float(rng.uniform(-60.0, 60.0)) * self.scale)

    def _ward_start(
        self, rng: np.random.Generator, frame: _Frame, ward: tuple[float, float]
    ) -> ShipStart:
        heading = float(rng.uniform(-math.pi, math.pi))
        speed = float(rng.uniform(0.0, WARD_MAX_SPEED))
        return frame.start(ward[0], ward[1], speed, heading)

    def _attackers(
        self,
        rng: np.random.Generator,
        frame: _Frame,
        sign: float,
        ward: tuple[float, float],
    ) -> tuple[tuple[str, ...], list[ShipStart]]:
        """A freighter's attackers on its far side, so that the pilots at the centre start
        out of gun range: one each side of the line outward from the freighter, far enough
        off it not to touch, swung toward the freighter's flank if the arena's edge is near.
        """
        n = int(rng.integers(ATTACKERS_PER_SIDE[0], ATTACKERS_PER_SIDE[1] + 1))
        hulls = _strike_hulls(rng, n)
        outward = 0.0 if sign > 0 else math.pi
        limit = START_LIMIT * self.scale
        low, high = ATTACKER_BEARING
        starts = []
        for k, hull in enumerate(hulls):
            r = float(rng.uniform(*ATTACKER_RING)) * self.scale
            off = float(rng.uniform(low, high))
            flank = 1.0 if k == 0 else -1.0
            x, y = 0.0, 0.0
            for off_now in np.arange(off, high + ATTACKER_SWING, ATTACKER_SWING):
                bearing = outward + flank * min(float(off_now), high)
                x = ward[0] + r * math.cos(bearing)
                y = ward[1] + r * math.sin(bearing)
                if math.hypot(x, y) <= limit:
                    break
            else:
                raise RuntimeError(f"no room for an attacker of a freighter at {ward}")
            heading = _bearing(x, y, ward[0], ward[1])
            speed = float(rng.uniform(0.0, ENEMY_START_SPEED_FRAC))
            starts.append(frame.start(x, y, speed * self.speed_caps[hull], heading))
        return hulls, starts

    def _chargers(
        self, rng: np.random.Generator, frame: _Frame, sign: float, center_y: float
    ) -> tuple[tuple[str, ...], list[ShipStart]]:
        """A group that flies at the pilots: no order, so the role's own choice."""
        n = int(rng.integers(CHARGERS_PER_SIDE[0], CHARGERS_PER_SIDE[1] + 1))
        hulls = _strike_hulls(rng, n)
        distance = float(rng.uniform(*CHARGE_DISTANCE)) * self.scale
        starts = []
        for k, hull in enumerate(hulls):
            x = sign * distance
            y = center_y + (k - (n - 1) / 2) * 40.0 * self.scale
            heading = _bearing(x, y, 0.0, center_y)
            speed = float(rng.uniform(0.0, ENEMY_START_SPEED_FRAC))
            starts.append(frame.start(x, y, speed * self.speed_caps[hull], heading))
        return hulls, starts

    def _route(
        self, rng: np.random.Generator, span: tuple[float, float]
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """A start and a point at a distance drawn from ``span`` (metres at the
        reference arena), both inside their limits, along the layout's y axis."""
        low, high = span
        start_limit = START_LIMIT * self.scale
        point_limit = POINT_LIMIT * self.scale
        for _ in range(MAX_PLACEMENT_TRIES):
            distance = float(rng.uniform(low, high)) * self.scale
            x = float(rng.uniform(-start_limit, start_limit))
            y0 = float(rng.uniform(-start_limit, start_limit))
            y1 = y0 + distance
            if math.hypot(x, y0) <= start_limit and math.hypot(x, y1) <= point_limit:
                return (x, y0), (x, y1)
        raise RuntimeError(
            f"no go-to route of {low}..{high} m fits an arena of {self.arena_radius} m"
        )

    def _goto(self, seed: int, rng: np.random.Generator) -> DrillSpec:
        frame = _Frame(rng)
        far = bool(rng.random() < GOTO_FAR_P)
        start, point = self._route(rng, GOTO_FAR if far else GOTO_NEAR)
        radius = float(rng.uniform(*GOTO_RADIUS)) * self.scale
        n = int(rng.integers(1, MAX_PILOTS + 1))
        pilot_hulls = _strike_hulls(rng, n)
        pilot_starts = []
        distances = []
        for k, hull in enumerate(pilot_hulls):
            x = start[0] + (k - (n - 1) / 2) * PILOT_SPACING * self.scale
            # Any heading: a turn before the run is part of what the deadline allows.
            heading = float(rng.uniform(-math.pi, math.pi))
            speed = float(rng.uniform(0.0, START_SPEED_FRAC)) * self.speed_caps[hull]
            pilot_starts.append(frame.start(x, start[1], speed, heading))
            distance = max(0.0, math.hypot(point[0] - x, point[1] - start[1]) - radius)
            distances.append(distance)
        around = bool(rng.random() < GOTO_ENEMIES_AROUND_P)
        m = int(rng.integers(GOTO_ENEMIES[0], GOTO_ENEMIES[1] + 1))
        enemy_hulls = _strike_hulls(rng, m)
        enemy_starts = self._goto_enemies(rng, frame, start, point, enemy_hulls, around)
        # Drawn after everything above, so a seed's layout is what it was before the
        # order carried a deadline (SIM_VERSION 7 and earlier). All three are drawn
        # whatever the outcome, so no draw depends on another's.
        untimed = bool(rng.random() < GOTO_NO_DEADLINE_P)
        low, high = GOTO_SLACK
        slack = float(math.exp(rng.uniform(math.log(low), math.log(high))))
        extra = int(
            rng.integers(GOTO_CLOCK_EXTRA_TICKS[0], GOTO_CLOCK_EXTRA_TICKS[1] + 1)
        )
        spec = DrillSpec(
            kind=DRILL_GOTO,
            seed=seed,
            teams=(pilot_hulls, enemy_hulls),
            layout=(*pilot_starts, *enemy_starts),
            pilots=tuple(range(n)),
            clock_ticks=0,
            arena_radius=self.arena_radius,
            point=frame.point(*point),
            radius=radius,
            distances=tuple(distances),
            far=far,
            enemies_around=around,
        )
        return self.with_slack(spec, NO_SLACK if untimed else slack, extra)

    def with_slack(
        self, spec: DrillSpec, slack: float, clock_extra_ticks: int
    ) -> DrillSpec:
        """The go-to ``spec`` with its deadline and clock set.

        Args:
            spec: A go-to drill.
            slack: The order's deadline is ``goto_order_deadline_tick`` of this slack
                for the squad; ``NO_SLACK`` (0.0): the order carries none and each ship
                is judged by the old rule (``goto_deadline_tick``).
            clock_extra_ticks: The clock runs this far past the last tick a ship is
                judged by.

        Raises:
            ValueError: Not a go-to, a negative slack, or a negative clock margin.
        """
        if spec.kind != DRILL_GOTO:
            raise ValueError(f"only a go-to takes a deadline, not a {spec.kind!r}")
        if slack < 0 or clock_extra_ticks < 0:
            raise ValueError(
                f"slack and clock margin must be >= 0, got {slack}, {clock_extra_ticks}"
            )
        caps = [self.speed_caps[spec.teams[0][slot]] for slot in spec.pilots]
        if slack == NO_SLACK:
            tick = NO_DEADLINE
            deadlines = tuple(
                goto_deadline_tick(d, cap) for d, cap in zip(spec.distances, caps)
            )
        else:
            tick = goto_order_deadline_tick(slack, spec.distances, caps)
            deadlines = (tick,) * len(spec.pilots)
        return replace(
            spec,
            deadline_tick=tick,
            slack=slack,
            deadlines=deadlines,
            clock_ticks=max(deadlines) + clock_extra_ticks,
        )

    def single_goto(
        self,
        seed: int,
        hull: str,
        edge_distance_m: float,
        radius_m: float,
        enemy_hulls: Sequence[str],
        parked: bool = False,
    ) -> DrillSpec:
        """A go-to for one ship at a set distance from a circle of a set radius: the
        layouts of the deadline sweep (``spacefight.eval.goto_sweep``).

        The start, heading and start speed are drawn as a go-to drill's are, and before
        anything about the enemies, so the same ``seed`` with other enemies has the same
        ship in the same place. The order carries no deadline and the clock stops at the
        last tick judged; ``with_slack`` sets both.

        Args:
            seed: The layout's seed.
            hull: The pilot's hull.
            edge_distance_m: From the ship's start to the circle's edge.
            radius_m: The circle's radius.
            enemy_hulls: The enemies' hulls, beside the route as a drill's are.
            parked: Instead: one enemy at rest on the rim, as far as it can be from
                both the start and the point (a roster needs two teams). Whoever flies
                the match gives it idle actions.

        Raises:
            KeyError: An unknown hull.
            ValueError: A distance or radius that is not positive, no enemy, or more
                than one enemy to park.
            RuntimeError: The route does not fit the arena.
        """
        if edge_distance_m <= 0 or radius_m <= 0:
            raise ValueError(f"bad go-to: {edge_distance_m} m to a {radius_m} m circle")
        if not enemy_hulls or (parked and len(enemy_hulls) != 1):
            raise ValueError(f"need enemies, and one to park, got {enemy_hulls}")
        rng = np.random.default_rng([seed, DRILL_KINDS.index(DRILL_GOTO), 0x51E9])
        frame = _Frame(rng)
        centre = (edge_distance_m + radius_m) / self.scale
        start, point = self._route(rng, (centre, centre))
        heading = float(rng.uniform(-math.pi, math.pi))
        speed = float(rng.uniform(0.0, START_SPEED_FRAC)) * self.speed_caps[hull]
        hulls = tuple(enemy_hulls)
        if parked:
            enemies = [self._parked(frame, start, point)]
        else:
            enemies = self._goto_enemies(rng, frame, start, point, hulls, True)
        spec = DrillSpec(
            kind=DRILL_GOTO,
            seed=seed,
            teams=((hull,), hulls),
            layout=(frame.start(start[0], start[1], speed, heading), *enemies),
            pilots=(0,),
            clock_ticks=0,
            arena_radius=self.arena_radius,
            point=frame.point(*point),
            radius=radius_m,
            distances=(edge_distance_m,),
            far=edge_distance_m >= GOTO_FAR[0] * self.scale,
            enemies_around=not parked,
        )
        return self.with_slack(spec, NO_SLACK, 0)

    def _parked(
        self, frame: _Frame, start: tuple[float, float], point: tuple[float, float]
    ) -> ShipStart:
        """A ship at rest on the rim, as far as it can be from ``start`` and ``point``."""
        limit = START_LIMIT * self.scale
        best, best_gap = (limit, 0.0), -1.0
        for angle in np.linspace(0.0, 2.0 * math.pi, PARKED_BEARINGS, endpoint=False):
            x, y = limit * math.cos(angle), limit * math.sin(angle)
            gap = min(
                math.hypot(x - start[0], y - start[1]),
                math.hypot(x - point[0], y - point[1]),
            )
            if gap > best_gap:
                best, best_gap = (x, y), gap
        return frame.start(best[0], best[1], 0.0, _bearing(*best, 0.0, 0.0))

    def _goto_enemies(
        self,
        rng: np.random.Generator,
        frame: _Frame,
        start: tuple[float, float],
        point: tuple[float, float],
        hulls: tuple[str, ...],
        around: bool,
    ) -> list[ShipStart]:
        """Enemies beside the route, clear of the pilots' start, or on the edge of the
        arena farthest from the route. They form a line toward the centre, so the group
        stays inside the limit."""
        limit = START_LIMIT * self.scale
        clearance = START_CLEARANCE * self.scale
        spacing = ENEMY_SPACING * self.scale

        def line(cx: float, cy: float) -> list[tuple[float, float]]:
            toward = math.atan2(-cy, -cx)
            return [
                (
                    cx + k * spacing * math.cos(toward),
                    cy + k * spacing * math.sin(toward),
                )
                for k in range(len(hulls))
            ]

        def clear(ship: tuple[float, float]) -> bool:
            return math.hypot(ship[0] - start[0], ship[1] - start[1]) >= clearance

        # The route runs along y at x = start[0]: this edge is across the arena from it.
        places = line(-limit if start[0] > 0 else limit, 0.0)
        if around:
            for _ in range(MAX_PLACEMENT_TRIES):
                along = float(rng.uniform(0.3, 0.8))
                cy = start[1] + along * (point[1] - start[1])
                side = 1.0 if rng.random() < 0.5 else -1.0
                cx = start[0] + side * float(rng.uniform(*AROUND_ROUTE)) * self.scale
                norm = math.hypot(cx, cy)
                if norm > limit:
                    cx, cy = cx * limit / norm, cy * limit / norm
                places = line(cx, cy)
                if all(clear(ship) for ship in places):
                    break
            else:
                raise RuntimeError(f"no room for enemies beside the route at {start}")
        mid_y = (start[1] + point[1]) / 2
        starts = []
        for (x, y), hull in zip(places, hulls):
            heading = _bearing(x, y, start[0], mid_y)
            speed = float(rng.uniform(0.0, ENEMY_START_SPEED_FRAC))
            starts.append(frame.start(x, y, speed * self.speed_caps[hull], heading))
        return starts


# Columns of the env's hits buffer (SIM_SPEC §10.1).
_HIT_SHOOTER, _HIT_TARGET, _HIT_DAMAGE = 0, 1, 3
# Per-slot marks of ``DrillLedger.side_of``.
_NOT_A_GROUP, _NAMED_GROUP, _OTHER_GROUP = -1, 0, 1
# ``DrillLedger.deadline`` of a slot whose arrival counts whenever it comes.
_ANY_TICK = np.iinfo(np.int64).max


@dataclass(frozen=True)
class DrillOutcome:
    """One finished drill, for the training log (``DrillLedger.finish``).

    Attributes:
        kind: The drill's kind.
        successes: Go-to: pilots that arrived in time. Attack and defend: 0 or 1.
        trials: Go-to: the pilots. Attack and defend: 1.
        timed_ships: Go-to whose order carried a deadline: the pilots; else 0.
        missed: Of ``timed_ships``, those alive when their deadline passed without
            them (the ones the sim charged).
    """

    kind: str
    successes: int
    trials: int
    timed_ships: int = 0
    missed: int = 0


class DrillLedger:
    """What the pilots of each env's current drill did, vectorised over the envs.

    The trainer's logs and the eval share it: every hit a pilot lands is booked here, and
    go-to arrivals and missed deadlines as the sim's order tracks show them. It does no
    per-env work on a step; only ``begin`` and ``finish``, once a match, loop in Python.

    Args:
        n_envs: Envs.
        n_ships: Slots per env.
    """

    def __init__(self, n_envs: int, n_ships: int) -> None:
        self.n_envs = n_envs
        self.n_ships = n_ships
        self.running = np.zeros(n_envs, dtype=np.bool_)
        self.goto = np.zeros(n_envs, dtype=np.bool_)
        self.tags: list[DrillTag | None] = [None] * n_envs
        self.pilot = np.zeros((n_envs, n_ships), dtype=np.bool_)
        self.named_slot = np.full(n_envs, -1, dtype=np.int64)
        self.side_of = np.full((n_envs, n_ships), _NOT_A_GROUP, dtype=np.int8)
        self.target_damage = np.zeros(n_envs, dtype=np.float64)
        # [N, 2] the pilots' damage on the named group's ships and on the other's.
        self.group_damage = np.zeros((n_envs, 2), dtype=np.float64)
        self.total_damage = np.zeros(n_envs, dtype=np.float64)
        # Go-to: arrived in time; alive when the order's deadline passed without it.
        self.arrived = np.zeros((n_envs, n_ships), dtype=np.bool_)
        self.missed = np.zeros((n_envs, n_ships), dtype=np.bool_)
        # [N, S] the tick each pilot's arrival is judged by, and [N] whether the order
        # itself carries a deadline (the sim then marks only arrivals in time).
        self.deadline = np.full((n_envs, n_ships), _ANY_TICK, dtype=np.int64)
        self.timed = np.zeros(n_envs, dtype=np.bool_)

    def begin(self, env: int, tag: DrillTag | None) -> None:
        """Env ``env``'s new match has this drill; ``None``: it is not a drill."""
        self.tags[env] = tag
        self.running[env] = tag is not None
        self.goto[env] = tag is not None and tag.kind == DRILL_GOTO
        self.pilot[env] = False
        self.side_of[env] = _NOT_A_GROUP
        self.named_slot[env] = -1
        self.target_damage[env] = 0.0
        self.group_damage[env] = 0.0
        self.total_damage[env] = 0.0
        self.arrived[env] = False
        self.missed[env] = False
        self.deadline[env] = _ANY_TICK
        self.timed[env] = False
        if tag is None:
            return
        self.pilot[env, list(tag.pilots)] = True
        if tag.deadlines:
            self.deadline[env, list(tag.pilots)] = tag.deadlines
        self.timed[env] = tag.timed
        self.named_slot[env] = tag.named_slot
        self.side_of[env, list(tag.named_group)] = _NAMED_GROUP
        self.side_of[env, list(tag.other_group)] = _OTHER_GROUP

    def add_hits(self, hits: NDArray[np.int32], hit_count: NDArray[np.int32]) -> None:
        """Book the hits of one step (``StepInfo.hits`` and ``hit_count``; call before
        ``finish`` and ``begin`` on a done step: the hits belong to the old match)."""
        count = hit_count * self.running
        if not count.any():
            return
        env_ids, k = np.nonzero(np.arange(hits.shape[1]) < count[:, None])
        rows = hits[env_ids, k]
        shooter = rows[:, _HIT_SHOOTER]
        by_pilot = self.pilot[env_ids, shooter]
        if not by_pilot.any():
            return
        env_ids = env_ids[by_pilot]
        target = rows[by_pilot, _HIT_TARGET]
        amount = rows[by_pilot, _HIT_DAMAGE] / float(rlf_sim.HIT_DAMAGE_SCALE)
        np.add.at(self.total_damage, env_ids, amount)
        named = target == self.named_slot[env_ids]
        np.add.at(self.target_damage, env_ids[named], amount[named])
        side = self.side_of[env_ids, target]
        grouped = side >= 0
        np.add.at(self.group_damage, (env_ids[grouped], side[grouped]), amount[grouped])

    def see_tracks(
        self,
        arrived: NDArray[np.bool_],
        missed: NDArray[np.bool_],
        alive: NDArray[np.bool_],
        tick: NDArray[np.integer],
    ) -> None:
        """Note go-to arrivals in time and missed deadlines. Call before every step: an
        arrival counts if it is first seen by the tick the pilot is judged by.

        Args:
            arrived: ``order_tracks()["arrived"]``, ``[N, S]``.
            missed: ``order_tracks()["missed"]``, ``[N, S]``.
            alive: ``[N, S]`` ships alive now. A ship dead when its deadline passes is
                marked missed by the sim and not charged; it is not counted here.
            tick: ``[N]`` each env's match tick now.
        """
        rows = self.goto[:, None] & self.pilot
        in_time = self.timed[:, None] | (
            np.asarray(tick, dtype=np.int64)[:, None] <= self.deadline
        )
        self.arrived |= rows & arrived & in_time
        self.missed |= rows & missed & alive

    def any_goto_running(self) -> bool:
        """Whether a go-to drill is being played."""
        return bool(self.goto.any())

    def finish(self, env: int) -> DrillOutcome:
        """The drill in ``env`` is over: its outcome for the logs.

        A go-to counts each pilot that arrived in time: by the order's deadline when it
        carries one, else by the old rule for that ship (``DrillSpec.deadlines``). A ship
        killed on the way counts as not arrived here; the eval sets those aside. An attack
        counts whether any damage landed on the named target, and a defend whether the
        named ward's attackers took more than the other's. These are running signals for
        a training log; the side chosen and the swap test need the eval
        (``spacefight.eval.drills``).

        Raises:
            ValueError: ``env`` is not running a drill.
        """
        tag = self.tags[env]
        if tag is None:
            raise ValueError(f"env {env} is not running a drill")
        self.running[env] = False
        self.goto[env] = False
        self.tags[env] = None
        if tag.kind == DRILL_GOTO:
            return DrillOutcome(
                tag.kind,
                int(self.arrived[env].sum()),
                len(tag.pilots),
                timed_ships=len(tag.pilots) if tag.timed else 0,
                missed=int(self.missed[env].sum()),
            )
        if tag.kind == DRILL_ATTACK:
            return DrillOutcome(tag.kind, int(self.target_damage[env] > 0.0), 1)
        more = self.group_damage[env, 0] > self.group_damage[env, 1]
        return DrillOutcome(tag.kind, int(more), 1)
