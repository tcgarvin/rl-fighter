"""Fleet rosters for training and eval: who plays each match, and in what arena.

A ``Roster`` is the two teams' hulls in slot order (team 0 first); its arena radius
comes from the sim's shared rule ``rlf_sim.arena_radius_for``
(``sim::setup::arena_radius_for``, 450 m for every fleet size today), which the
live page uses too. ``RosterDistribution`` describes a seeded distribution of rosters with 1 to
``MAX_PER_SIDE`` ships a side; ``RosterSampler`` draws from it. ``RustVecEnv`` takes a
sampler and queues a fresh draw for every env whenever its match ends.

Distribution (one draw):

1. With probability ``duel_p`` a fighter duel (the live ``/duel/`` mode stays in the
   training mix).
2. Else with probability ``draft_p`` a budget-matched draft like the live page's: a
   budget from ``draft_budgets`` and, per side independently, hulls drawn uniformly
   from those whose ``cost`` (hull YAML) still fits until nothing fits or the side
   has ``MAX_PER_SIDE`` ships. Sides can end up uneven (a gunship against three
   fighters).
3. Else a random skirmish: team 0's size from ``size_weights``; with probability
   ``uneven_p`` team 1 has one ship more or fewer (clipped to ``1..MAX_PER_SIDE``),
   else the same count; with probability ``mirror_p`` (same count only) team 1 is
   team 0's composition; otherwise every ship's hull is drawn from
   ``hull_weights``.

Every draw shuffles each team's slot order (squads of three form in slot order) and
swaps the teams with probability ½, so the distribution is symmetric in the teams.

Missions (M3 stage B, preset ``orders_v1``, ``OrdersDistribution``): a roster also
names its mission (``deathmatch``, ``carrier_battle``, ``convoy_escort``; SIM_VERSION 9
adds ``station_assault``, whose ``Roster.station_as`` says what the nets read it as) and
each team's commander mode (``scripted``, ``random``; SIM_VERSION 5). One draw picks the
mission by ``mission_weights`` (one weight per ``MISSIONS``; a three-weight tuple from a
config written before v9 means a station weight of 0, and a zero weight draws exactly
as the shorter tuple did); a deathmatch is a draw from the nested fleet preset;
a carrier battle is a carrier plus a wing of strike craft a side; a convoy is
freighters plus escorts (team 0, the sim's convoy side) against a strike force.
Each team's commander is ``random`` with ``random_commander_p``. Matches pad to
``MAX_TRAIN_SHIPS`` (12) slots. Capital ships (``CAPITAL_ROLES``) are flown by the
sim's scripts, never by the learned pilot. SIM_VERSION 10 adds role ``line`` (the
dreadnought) to them, and a second default station roster ("citadel": the citadel
against a carrier, a dreadnought and nine, 19 ships in a 550 m arena); a station
assault of ``OrdersDistribution`` still plays the sim's first (v9) station roster.

Live rosters (``docs/PILOT_TRAINING.md`` §3, preset ``pilots_v1``,
``PilotsDistribution``): a training match is drawn the way the live page draws one, so
pilots train on what they will play. One draw picks the mission by ``mission_weights``.
A deathmatch is the page's budget draft (``web/src/live/roster.ts``, ``chooseRoster``):
a size from ``draft_min_per_side..draft_max_per_side``, a budget of that many of the
cheapest hull, then each side spends it independently. A carrier battle or a convoy is
one of the sim's own rosters, read from ``rlf_sim.mission_rosters`` at run time and
never copied here (``web/src/live/missions.ts``, ``fromSim``): the first, the sim's
default, with ``default_roster_share``, else one of the others uniformly. A station
assault is the sim's v10 "citadel" roster by default (``citadel_share`` 1, as the live
page plays it on SIM_VERSION >= 10), and ``mission_weights`` gives it a fifth of the
matches by default, so pilots train on all four live missions. Both teams
have ``scripted`` commanders. With ``commander_p`` their orders are shown; otherwise
they are hidden from both teams (``Roster.hide_orders``), which is "no commander": the
script's logistics still run, because a carrier or a convoy cannot play without them.
The condition is the same on both sides, except under the experimental ``mixed_p``
(training only, default 0): a share of the shown matches hide one side's orders.

Order drills (``docs/PILOT_TRAINING.md`` §2): with ``drill_share`` a ``PilotsDistribution``
also draws drills from ``spacefight.env.drills``. A drill is a ``Roster`` like any other,
with a start layout, the orders it opens with, its own clock and drill rules; ``drill``
tells the trainer and the logs what it is. With ``drill_attack_pool_share`` (training only,
default 0) that share of the attack drills are kite drills, whose enemies the trainer has
learned pilots fly (``DrillTag.kite``). ``drill_dock_share`` (SIM_VERSION 11, default
0.25) of the drills are dock drills: a damaged strike craft ordered home to its carrier
or station (``DRILL_DOCK``; a carrier battle or a station assault laid out by hand, with
``Roster.start_hull``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Protocol

import numpy as np
import rlf_sim
import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSETS = REPO_ROOT / "assets"

# Hulls a fleet pilot flies (strike craft only: carrier and freighter are capital
# ships flown by scripts, SIM_SPEC §11), and the most ships a side can field. The v9
# bomber is a strike hull too, but opt-in (``STRIKE_HULLS``): the default rosters and
# drafts stay those of v8.
FLEET_HULLS: tuple[str, ...] = ("fighter", "strafer", "gunship")
BOMBER = "bomber"
STRIKE_HULLS: tuple[str, ...] = (*FLEET_HULLS, BOMBER)
MAX_PER_SIDE = 4
# Slots per match of a fleet roster env: two full sides. The sim allows more
# (``MAX_SHIPS``, 20 since SIM_VERSION 4, for carrier hangars), but a training env
# pads every match to its slot count, so it stays at what the rosters need.
MAX_FLEET_SHIPS: int = 2 * MAX_PER_SIDE
MAX_SHIPS: int = int(rlf_sim.MAX_SHIPS)
# Slots per match of an ``orders_v1`` training env (SIM_VERSION 5's
# ``MAX_TRAIN_SHIPS``): carrier + 5 a side, or 4 freighters + 3 escorts v 5. Preset
# ``pilots_v1`` plays the live rosters, which need ``MAX_SHIPS``.
MAX_TRAIN_SHIPS = 12

DEATHMATCH = "deathmatch"
CARRIER_BATTLE = "carrier_battle"
CONVOY_ESCORT = "convoy_escort"
STATION_ASSAULT = "station_assault"
MISSIONS: tuple[str, ...] = (DEATHMATCH, CARRIER_BATTLE, CONVOY_ESCORT, STATION_ASSAULT)
# What a station assault reads as to the nets (SIM_VERSION 9): a carrier battle for
# both sides, or a convoy escort with team 0 (the station) the defender.
STATION_READS_AS: tuple[str, ...] = tuple(rlf_sim.STATION_READS_AS)
STATION_AS_CARRIER, STATION_AS_CONVOY = "carrier", "convoy"
# Missions that take a ``Roster.start_layout`` (SIM_VERSION 11: a carrier battle and a
# station assault too, for the dock drills).
LAYOUT_MISSIONS: tuple[str, ...] = (DEATHMATCH, CARRIER_BATTLE, STATION_ASSAULT)


def mission_weights_of(weights: Sequence[float]) -> tuple[float, ...]:
    """``weights`` with one entry per ``MISSIONS``: a pre-v9 three-weight tuple gets a
    station-assault weight of 0 (which draws exactly as the three did).

    Raises:
        ValueError: Neither three weights nor one per mission.
    """
    w = tuple(float(x) for x in weights)
    if len(w) == len(MISSIONS) - 1:
        w = (*w, 0.0)
    if len(w) != len(MISSIONS):
        raise ValueError(f"mission_weights needs one weight per {MISSIONS}, got {w}")
    return w


# Order drills (``docs/PILOT_TRAINING.md`` §2), in ``drill_weights`` order.
DRILL_GOTO, DRILL_ATTACK, DRILL_DEFEND = "goto", "attack", "defend"
# ``OpeningOrder.deadline_tick`` of a go-to without a deadline (SIM_VERSION 8).
NO_DEADLINE: int = int(rlf_sim.NO_DEADLINE)
# The largest tick the sim's clock (and so a deadline) can hold.
_MAX_TICK = 2**32 - 1
DRILL_KINDS: tuple[str, ...] = (DRILL_GOTO, DRILL_ATTACK, DRILL_DEFEND)
# SIM_VERSION 11: the dock drill, apart from ``DRILL_KINDS`` (whose weights a config
# lists): ``drill_dock_share`` of the drills (``spacefight.env.drills``).
DRILL_DOCK = "dock"
SCRIPTED = "scripted"
RANDOM = "random"
EXTERNAL = "external"
# The learned commander (``docs/COMMANDER.md``): decisions submitted every
# ``LEARNED_COMMAND_TICKS`` through ``RustVecEnv.submit_commander_actions``.
LEARNED = "learned"
COMMANDER_MODES: tuple[str, ...] = (SCRIPTED, RANDOM, EXTERNAL, LEARNED)
# Hull roles the learned pilot never flies (SIM_SPEC §11: scripts fly them; SIM_VERSION
# 10 adds ``line``, the dreadnought).
CAPITAL_ROLES: frozenset[str] = frozenset({"carrier", "transport", "line"})

_ABBREV = {
    "fighter": "F",
    "strafer": "S",
    "gunship": "G",
    "carrier": "C",
    "freighter": "T",
    "bomber": "B",
    "station": "X",
    "citadel": "Z",
    "dreadnought": "D",
}
_MISSION_ABBREV = {
    CARRIER_BATTLE: "carrier",
    CONVOY_ESCORT: "convoy",
    STATION_ASSAULT: "station",
}


def arena_radius_for(n_ships: int) -> float:
    """Arena radius (m) for ``n_ships`` ships in total: the sim's shared rule."""
    return float(rlf_sim.arena_radius_for(n_ships))


@dataclass(frozen=True)
class ShipStart:
    """Where one ship starts (``MatchConfig.start_layout``): metres, m/s, radians."""

    x: float
    y: float
    vx: float
    vy: float
    heading: float

    def row(self) -> list[float]:
        """``[x, y, vx, vy, heading]`` as ``set_next_roster`` takes it."""
        return [self.x, self.y, self.vx, self.vy, self.heading]


# ``OpeningOrder.kind`` of a ship's dock order and a capital ship's waypoint (SIM_VERSION
# 11, the dock drills).
DOCK_COMMAND, WAYPOINT_COMMAND = "dock", "waypoint"


@dataclass(frozen=True)
class OpeningOrder:
    """A command an ``external`` team opens a match with (SIM_SPEC §10.3): a squad
    order, or (SIM_VERSION 11, the dock drills) a ship's dock order or a capital ship's
    waypoint.

    ``RustVecEnv`` queues it when the match is built and the sim applies it on the
    match's first slow tick.

    Attributes:
        team: The team.
        squad: Squad index (unused by ``dock`` and ``waypoint``).
        members: The squad's slots; for ``dock`` and ``waypoint`` the one ship.
        kind: ``"attack"``, ``"defend"``, ``"goto"``, ``"dock"`` (to the nearest live
            bay of the team's carrier) or ``"waypoint"`` (at ``point``).
        target: The attack target's or the defend ward's slot; -1 otherwise.
        point: The go-to point or the waypoint, metres.
        radius: The go-to radius, metres.
        deadline_tick: A go-to's deadline (SIM_VERSION 8): the match tick to be inside
            the radius by, ``NO_DEADLINE`` for none. An absolute tick, not a duration:
            an opening order lands on the first slow tick (``COMMAND_TICKS``, tick 60).

    Raises:
        ValueError: ``deadline_tick`` is not an int in ``0..2**32``, or is set on an
            order that is not a go-to; a ``dock`` or ``waypoint`` for other than one
            ship.
    """

    team: int
    squad: int
    members: tuple[int, ...]
    kind: str
    target: int = -1
    point: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.0
    deadline_tick: int = NO_DEADLINE

    def __post_init__(self) -> None:
        tick = self.deadline_tick
        if isinstance(tick, bool) or not isinstance(tick, int):
            raise ValueError(f"deadline_tick must be an int, got {tick!r}")
        if not 0 <= tick <= _MAX_TICK:
            raise ValueError(f"deadline_tick must be in 0..={_MAX_TICK}, got {tick}")
        if tick != NO_DEADLINE and self.kind != DRILL_GOTO:
            raise ValueError(
                f"only a go-to takes a deadline; a {self.kind!r} order got "
                f"deadline_tick {tick}"
            )
        if self.kind in (DOCK_COMMAND, WAYPOINT_COMMAND) and len(self.members) != 1:
            raise ValueError(
                f"a {self.kind!r} command is for one ship, got {self.members}"
            )

    def command(self) -> dict[str, object]:
        """The sim's command dict.

        Raises:
            ValueError: An unknown order kind.
        """
        if self.kind == DOCK_COMMAND:
            return {"kind": "dock", "ship": self.members[0], "bay": None}
        if self.kind == WAYPOINT_COMMAND:
            return {
                "kind": "waypoint",
                "ship": self.members[0],
                "pos": list(self.point),
            }
        order: dict[str, object]
        if self.kind == "attack":
            order = {"kind": "attack", "target": self.target}
        elif self.kind == "defend":
            order = {"kind": "defend", "ward": self.target}
        elif self.kind == "goto":
            order = {
                "kind": "goto",
                "point": list(self.point),
                "radius": self.radius,
                "deadline": self.deadline_tick,
            }
        else:
            raise ValueError(f"unknown order kind {self.kind!r}")
        return {
            "kind": "squad",
            "squad": self.squad,
            "members": list(self.members),
            "order": order,
        }


@dataclass(frozen=True)
class DrillTag:
    """What the trainer's logs need to know about a drill match.

    Attributes:
        kind: ``"goto"``, ``"attack"`` or ``"defend"``.
        pilots: The ordered strike craft's slots (team 0).
        named_slot: The attack target's or the ward's slot; -1 for a go-to.
        named_group: Enemy slots on the named side.
        other_group: Enemy slots on the other side.
        deadlines: Go-to: per pilot, the tick its arrival is judged by
            (``DrillSpec.deadlines``); empty: any arrival counts.
        timed: Go-to: the order itself carries a deadline (SIM_VERSION 8).
        kite: Attack: a kite drill (``spacefight.env.drills``): the trainer has pilots
            from its opponent pool fly the enemy team, whose orders are hidden.
        threat: Dock: enemies are ordered onto the pilot (else it flies home alone).
        base: Dock: what it docks with, ``"carrier"``, ``"station"`` or ``"citadel"``.

    Raises:
        ValueError: ``deadlines`` is neither empty nor one per pilot.
    """

    kind: str
    pilots: tuple[int, ...]
    named_slot: int = -1
    named_group: tuple[int, ...] = ()
    other_group: tuple[int, ...] = ()
    deadlines: tuple[int, ...] = ()
    timed: bool = False
    kite: bool = False
    threat: bool = False
    base: str = ""

    def __post_init__(self) -> None:
        if self.deadlines and len(self.deadlines) != len(self.pilots):
            raise ValueError(
                f"{len(self.deadlines)} deadlines for {len(self.pilots)} pilots"
            )


@dataclass(frozen=True)
class Roster:
    """Two teams' hulls in slot order, the mission and each team's commander.

    Attributes:
        teams: ``(team 0 hulls, team 1 hulls)``.
        mission: One of ``MISSIONS``.
        commanders: Each team's commander mode (``COMMANDER_MODES``).
        hide_orders: Per team, whether its pilots' obs hide their orders (SIM_VERSION
            6, ``MatchConfig.hide_orders``). ``RustVecEnv`` applies it when the roster
            is queued.
        start_layout: Where every slot starts; empty: the mission places the ships. A
            deathmatch, or (SIM_VERSION 11, the dock drills) a carrier battle or a
            station assault, every ship on the field and nobody in a hangar.
        start_hull: SIM_VERSION 11: each slot's hull at the start as a fraction of its
            maximum, in (0, 1]; empty: full. Needs a ``start_layout``.
        opening_orders: Orders ``RustVecEnv`` queues whenever this roster's match is
            built, for teams with ``external`` commanders.
        time_limit_s: The match's clock; 0: the env's or the mission's default.
        drill: Set on a drill match (``spacefight.env.drills``): the sim plays it under
            drill rules (SIM_SPEC §5.10). ``None`` on every other match.
        commander_ids: Per team, the id of the commander a trainer's commander stable
            drew for it (``spacefight.commander.stable``), which picks the network of a
            ``learned`` team and labels the logs; ``""`` where no stable drew one. The
            sim sees only ``commanders``.
        station_as: A station assault's obs mapping (SIM_VERSION 9, one of
            ``STATION_READS_AS``): what its pilots' and commanders' mission one-hots
            read. Ignored by every other mission.

    Raises:
        ValueError: An empty team, more than ``MAX_SHIPS`` ships, an unknown mission
            or commander mode, ``hide_orders`` not two bools, a layout that does not
            have one entry per ship or is on a convoy, a drill without a layout, or a
            ``start_hull`` without a layout, of the wrong length or out of (0, 1].
    """

    teams: tuple[tuple[str, ...], tuple[str, ...]]
    mission: str = DEATHMATCH
    commanders: tuple[str, str] = (SCRIPTED, SCRIPTED)
    hide_orders: tuple[bool, bool] = (False, False)
    start_layout: tuple[ShipStart, ...] = ()
    start_hull: tuple[float, ...] = ()
    opening_orders: tuple[OpeningOrder, ...] = ()
    time_limit_s: float = 0.0
    drill: DrillTag | None = None
    commander_ids: tuple[str, str] = ("", "")
    station_as: str = STATION_AS_CARRIER

    def __post_init__(self) -> None:
        if self.station_as not in STATION_READS_AS:
            raise ValueError(
                f"station_as must be one of {STATION_READS_AS}, got {self.station_as!r}"
            )
        if len(self.teams) != 2 or any(len(t) == 0 for t in self.teams):
            raise ValueError(f"a roster needs two non-empty teams, got {self.teams}")
        if self.n_ships > MAX_SHIPS:
            raise ValueError(f"{self.n_ships} ships exceed MAX_SHIPS = {MAX_SHIPS}")
        if self.mission not in MISSIONS:
            raise ValueError(f"unknown mission {self.mission!r}; known: {MISSIONS}")
        if len(self.commanders) != 2 or any(
            c not in COMMANDER_MODES for c in self.commanders
        ):
            raise ValueError(
                f"commanders must be two of {COMMANDER_MODES}, got {self.commanders}"
            )
        if len(self.hide_orders) != 2 or any(
            not isinstance(h, bool) for h in self.hide_orders
        ):
            raise ValueError(f"hide_orders must be two bools, got {self.hide_orders}")
        if len(self.commander_ids) != 2 or any(
            not isinstance(c, str) for c in self.commander_ids
        ):
            raise ValueError(
                f"commander_ids must be two strings, got {self.commander_ids}"
            )
        if self.start_layout:
            if len(self.start_layout) != self.n_ships:
                raise ValueError(
                    f"start_layout has {len(self.start_layout)} entries for "
                    f"{self.n_ships} ships"
                )
            if self.mission not in LAYOUT_MISSIONS:
                raise ValueError(f"{self.mission} places its own ships")
        elif self.drill is not None:
            raise ValueError("a drill needs a start_layout")
        if self.start_hull:
            if len(self.start_hull) != len(self.start_layout):
                raise ValueError(
                    f"start_hull has {len(self.start_hull)} entries for "
                    f"{len(self.start_layout)} laid-out ships (it needs a layout)"
                )
            if not all(0.0 < f <= 1.0 for f in self.start_hull):
                raise ValueError(f"start_hull must be in (0, 1], got {self.start_hull}")
        if self.time_limit_s < 0:
            raise ValueError(f"time_limit_s must be >= 0, got {self.time_limit_s}")

    @classmethod
    def of(
        cls,
        team0: Sequence[str],
        team1: Sequence[str],
        mission: str = DEATHMATCH,
        commanders: Sequence[str] = (SCRIPTED, SCRIPTED),
        hide_orders: tuple[bool, bool] = (False, False),
    ) -> Roster:
        """Build from two hull-name sequences."""
        pair = tuple(commanders)
        if len(pair) != 2:
            raise ValueError(f"commanders must name two modes, got {pair}")
        return cls(
            (tuple(team0), tuple(team1)), mission, (pair[0], pair[1]), hide_orders
        )

    @property
    def n_ships(self) -> int:
        """Ships in the match."""
        return len(self.teams[0]) + len(self.teams[1])

    @property
    def mission_spec(self) -> str | dict[str, str] | None:
        """The mission as the sim takes it (SIM_SPEC §10.3): ``None`` for a
        deathmatch, the kind name for a carrier battle or a convoy, a spec dict for a
        station assault (its ``station_as`` mapping)."""
        if self.mission == DEATHMATCH:
            return None
        if self.mission == STATION_ASSAULT:
            return {"kind": STATION_ASSAULT, "as": self.station_as}
        return self.mission

    @property
    def arena_radius(self) -> float:
        """Arena radius from the shared rule (per mission since SIM_VERSION 4)."""
        if self.mission == DEATHMATCH:
            return arena_radius_for(self.n_ships)
        return float(rlf_sim.arena_radius_for_mission(self.mission, self.n_ships))

    @property
    def klass(self) -> str:
        """Class training logs group by: the size class of a deathmatch, else the
        mission; ``"drill/<kind>"`` for a drill."""
        if self.drill is not None:
            return f"drill/{self.drill.kind}"
        return self.size_class if self.mission == DEATHMATCH else self.mission

    @property
    def size_class(self) -> str:
        """``"<n0>v<n1>"`` with the larger side second (e.g. ``"2v3"``)."""
        a, b = sorted(len(t) for t in self.teams)
        return f"{a}v{b}"

    @property
    def label(self) -> str:
        """Short label, e.g. ``"FS v GF"`` or ``"convoy: TTTFS v FFSGF"``."""
        teams = " v ".join("".join(_ABBREV.get(h, h) for h in t) for t in self.teams)
        if self.mission == DEATHMATCH:
            return teams
        if self.mission == STATION_ASSAULT and self.station_as != STATION_AS_CARRIER:
            return f"{_MISSION_ABBREV[self.mission]} as {self.station_as}: {teams}"
        return f"{_MISSION_ABBREV[self.mission]}: {teams}"

    def fleets(self) -> list[list[str]]:
        """``[[team 0 hulls], [team 1 hulls]]`` as the env takes them."""
        return [list(t) for t in self.teams]

    def scripts_follow_orders(self) -> tuple[bool, bool]:
        """Per team: whether its scripted strike pilots fly their squad's order.

        Mirrors ``scripted::orders::active_order`` (SIM_SPEC §11): every commander's
        orders are followed except the scripted commander's in a deathmatch, which
        are advisory (shown, and in the pilot obs, but not flown by the scripts).
        """
        return (
            not (self.mission == DEATHMATCH and self.commanders[0] == SCRIPTED),
            not (self.mission == DEATHMATCH and self.commanders[1] == SCRIPTED),
        )

    def swapped(self) -> Roster:
        """The same match with the teams (commanders, hidden orders) exchanged.

        Raises:
            ValueError: A convoy, whose transports must be team 0, or a roster with a
                start layout or opening orders, which name slots.
        """
        if self.mission == CONVOY_ESCORT:
            raise ValueError("a convoy cannot swap teams: the convoy is team 0")
        if self.start_layout or self.opening_orders:
            raise ValueError("a roster that names slots cannot swap teams")
        return Roster(
            (self.teams[1], self.teams[0]),
            self.mission,
            (self.commanders[1], self.commanders[0]),
            (self.hide_orders[1], self.hide_orders[0]),
            commander_ids=(self.commander_ids[1], self.commander_ids[0]),
        )

    def cost(self, costs: Mapping[str, float]) -> tuple[float, float]:
        """Each team's summed hull cost."""
        return (
            float(sum(costs[h] for h in self.teams[0])),
            float(sum(costs[h] for h in self.teams[1])),
        )


def load_hull_costs(assets_dir: Path = DEFAULT_ASSETS) -> dict[str, float]:
    """Hull name -> ``cost`` from every ``hulls/*/hull.yaml``.

    Raises:
        FileNotFoundError: No hull YAML under ``assets_dir``.
        ValueError: A hull YAML without a positive ``cost``.
    """
    paths = sorted((assets_dir / "hulls").glob("*/hull.yaml"))
    if not paths:
        raise FileNotFoundError(f"no hulls/*/hull.yaml under {assets_dir}")
    costs: dict[str, float] = {}
    for path in paths:
        raw = yaml.safe_load(path.read_text())
        cost = raw.get("cost") if isinstance(raw, dict) else None
        if not isinstance(cost, (int, float)) or cost <= 0:
            raise ValueError(f"{path} has no positive cost (got {cost!r})")
        costs[str(raw["name"])] = float(cost)
    return costs


def load_hull_speed_caps(assets_dir: Path = DEFAULT_ASSETS) -> dict[str, float]:
    """Hull name -> ``speed_cap`` (m/s) from every ``hulls/*/hull.yaml`` that can
    move (a ``static`` hull, SIM_VERSION 9's station, has none and is left out).

    Raises:
        FileNotFoundError: No hull YAML under ``assets_dir``.
        ValueError: A non-static hull YAML without a positive ``speed_cap``.
    """
    paths = sorted((assets_dir / "hulls").glob("*/hull.yaml"))
    if not paths:
        raise FileNotFoundError(f"no hulls/*/hull.yaml under {assets_dir}")
    caps: dict[str, float] = {}
    for path in paths:
        raw = yaml.safe_load(path.read_text())
        cap = raw.get("speed_cap") if isinstance(raw, dict) else None
        if isinstance(raw, dict) and raw.get("static"):
            continue
        if not isinstance(cap, (int, float)) or cap <= 0:
            raise ValueError(f"{path} has no positive speed_cap (got {cap!r})")
        caps[str(raw["name"])] = float(cap)
    return caps


def load_hull_roles(assets_dir: Path = DEFAULT_ASSETS) -> dict[str, str]:
    """Hull name -> ``role`` from every ``hulls/*/hull.yaml``.

    Raises:
        FileNotFoundError: No hull YAML under ``assets_dir``.
        ValueError: A hull YAML without a role.
    """
    paths = sorted((assets_dir / "hulls").glob("*/hull.yaml"))
    if not paths:
        raise FileNotFoundError(f"no hulls/*/hull.yaml under {assets_dir}")
    roles: dict[str, str] = {}
    for path in paths:
        raw = yaml.safe_load(path.read_text())
        role = raw.get("role") if isinstance(raw, dict) else None
        if not isinstance(role, str):
            raise ValueError(f"{path} has no role")
        roles[str(raw["name"])] = role
    return roles


def capital_hull_ids(assets_dir: Path = DEFAULT_ASSETS) -> list[int]:
    """Hull ids (``hull_names_by_id`` order) of the capital-role hulls."""
    roles = load_hull_roles(assets_dir)
    return [
        hid
        for hid, name in enumerate(hull_names_by_id(assets_dir))
        if roles[name] in CAPITAL_ROLES
    ]


def hull_names_by_id(assets_dir: Path = DEFAULT_ASSETS) -> list[str]:
    """Hull names in hull-id order, the sim's (``Catalogue::load_dir``,
    ``sim::data::hull_order``): the hulls of ``rlf_sim.LEGACY_HULL_ORDER`` first, in
    that order (they keep their v4-v8 ids), then every other hull directory by name
    (SIM_VERSION 9: bomber, station; v10 freezes those too and adds citadel, dreadnought).

    Raises:
        FileNotFoundError: No hull directories.
    """
    legacy = list(rlf_sim.LEGACY_HULL_ORDER)
    names = sorted(
        (p.parent.name for p in (assets_dir / "hulls").glob("*/hull.yaml")),
        key=lambda n: (legacy.index(n) if n in legacy else len(legacy), n),
    )
    if not names:
        raise FileNotFoundError(f"no hulls/*/hull.yaml under {assets_dir}")
    return names


@dataclass(frozen=True)
class RosterDistribution:
    """Parameters of the training roster distribution (module docstring).

    Plain types only, so it round-trips through ``config.yaml``.
    """

    hulls: tuple[str, ...] = FLEET_HULLS
    size_weights: tuple[float, ...] = (0.2, 0.3, 0.25, 0.25)
    hull_weights: tuple[float, ...] = (1.0, 1.0, 1.0)
    uneven_p: float = 0.25
    mirror_p: float = 0.2
    draft_p: float = 0.25
    draft_budgets: tuple[float, ...] = (20.0, 30.0, 40.0)
    duel_p: float = 0.05

    def __post_init__(self) -> None:
        if len(self.size_weights) != MAX_PER_SIDE:
            raise ValueError(
                f"size_weights needs {MAX_PER_SIDE} entries (sizes 1..{MAX_PER_SIDE})"
            )
        if len(self.hull_weights) != len(self.hulls) or not self.hulls:
            raise ValueError("hull_weights needs one weight per hull")
        for name, weights in (
            ("size_weights", self.size_weights),
            ("hull_weights", self.hull_weights),
        ):
            if any(w < 0 for w in weights) or sum(weights) <= 0:
                raise ValueError(f"{name} must be >= 0 with a positive sum")
        for name in ("uneven_p", "mirror_p", "draft_p", "duel_p"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")
        if self.draft_p > 0 and not self.draft_budgets:
            raise ValueError("draft_p > 0 needs at least one draft budget")

    def to_dict(self) -> dict[str, object]:
        """Plain dict (lists for tuples) for YAML."""
        return {
            k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> RosterDistribution:
        """Inverse of ``to_dict``.

        Raises:
            ValueError: Unknown keys.
        """
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown roster distribution keys: {sorted(unknown)}")
        kwargs = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
        return cls(**kwargs)  # type: ignore[arg-type]


ORDERS_KIND = "orders"


@dataclass(frozen=True)
class OrdersDistribution:
    """Stage B's per-episode mission mix (module docstring; M3 "Stage B decisions").

    Ranges are inclusive ``(low, high)`` counts drawn uniformly. Plain types only.

    Attributes:
        kind: Always ``"orders"`` (tells ``resolve_distribution`` the class apart).
        mission_weights: Weights of ``MISSIONS`` (deathmatch, carrier, convoy,
            station; three weights mean station 0). A station assault plays the sim's
            default station roster.
        random_commander_p: Per team, the chance its commander is ``random``
            (else ``scripted``).
        deathmatch: Fleet preset a deathmatch roster is drawn from.
        strike_hulls: Hulls of wings, escorts and attackers.
        strike_weights: Their weights.
        carrier_wing: Strike craft per side in a carrier battle (besides the
            carrier).
        wing_mirror_p: Chance team 1's carrier wing copies team 0's hulls.
        convoy_transports: Freighters in a convoy.
        convoy_escorts: The convoy's escorts.
        convoy_attackers: The attackers' strike craft.
        carrier_hull: The carrier hull.
        transport_hull: The convoy's hull.
        max_ships: Slots every roster must fit.
    """

    kind: str = ORDERS_KIND
    mission_weights: tuple[float, ...] = (0.4, 0.3, 0.3, 0.0)
    random_commander_p: float = 0.5
    deathmatch: str = "fleet_v1"
    strike_hulls: tuple[str, ...] = FLEET_HULLS
    strike_weights: tuple[float, ...] = (1.0, 1.0, 1.0)
    carrier_wing: tuple[int, ...] = (4, 5)
    wing_mirror_p: float = 0.25
    convoy_transports: tuple[int, ...] = (3, 4)
    convoy_escorts: tuple[int, ...] = (2, 3)
    convoy_attackers: tuple[int, ...] = (4, 5)
    carrier_hull: str = "carrier"
    transport_hull: str = "freighter"
    max_ships: int = MAX_TRAIN_SHIPS

    def __post_init__(self) -> None:
        if self.kind != ORDERS_KIND:
            raise ValueError(f"kind must be {ORDERS_KIND!r}, got {self.kind!r}")
        object.__setattr__(
            self, "mission_weights", mission_weights_of(self.mission_weights)
        )
        if len(self.strike_weights) != len(self.strike_hulls) or not self.strike_hulls:
            raise ValueError("strike_weights needs one weight per strike hull")
        for name in ("mission_weights", "strike_weights"):
            weights = getattr(self, name)
            if any(w < 0 for w in weights) or sum(weights) <= 0:
                raise ValueError(f"{name} must be >= 0 with a positive sum")
        for name in ("random_commander_p", "wing_mirror_p"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        for name in (
            "carrier_wing",
            "convoy_transports",
            "convoy_escorts",
            "convoy_attackers",
        ):
            lo_hi = getattr(self, name)
            if len(lo_hi) != 2 or not 0 <= lo_hi[0] <= lo_hi[1]:
                raise ValueError(f"{name} must be (low, high) with 0 <= low <= high")
        if self.carrier_wing[0] < 1 or self.convoy_attackers[0] < 1:
            raise ValueError("a carrier wing and the convoy attackers need >= 1 ship")
        if self.convoy_transports[0] < 1:
            raise ValueError("a convoy needs at least one transport")
        widest = max(
            2 * (1 + self.carrier_wing[1]),
            self.convoy_transports[1]
            + self.convoy_escorts[1]
            + self.convoy_attackers[1],
            2 * MAX_PER_SIDE,
        )
        if self.mission_weights[MISSIONS.index(STATION_ASSAULT)] > 0:
            # It plays the sim's first station roster (v9's), whatever v10 appended.
            widest = max(widest, live_mission_rosters(STATION_ASSAULT)[0].n_ships)
        if widest > self.max_ships:
            raise ValueError(
                f"rosters reach {widest} ships > max_ships {self.max_ships}"
            )

    def to_dict(self) -> dict[str, object]:
        """Plain dict (lists for tuples) for YAML."""
        return {
            k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> OrdersDistribution:
        """Inverse of ``to_dict``.

        Raises:
            ValueError: Unknown keys.
        """
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown orders distribution keys: {sorted(unknown)}")
        kwargs = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
        return cls(**kwargs)  # type: ignore[arg-type]


def live_mission_rosters(mission: str) -> tuple[Roster, ...]:
    """The sim's rosters of ``mission``, default first (``rlf_sim.mission_rosters``,
    which the live page plays too), each with scripted commanders and orders shown.

    Raises:
        ValueError: The sim lists no rosters for ``mission`` (a deathmatch is drafted).
    """
    raw = rlf_sim.mission_rosters(mission)
    if not raw:
        raise ValueError(f"the sim has no rosters for mission {mission!r}")
    return tuple(
        Roster.of(r["fleets"][0], r["fleets"][1], mission=mission) for r in raw
    )


# The sim's v10 station roster: the citadel against a carrier and a dreadnought.
CITADEL_ROSTER = "citadel"


def citadel_roster() -> Roster:
    """The sim's v10 "citadel" station-assault roster (``rlf_sim.mission_rosters``).

    Raises:
        ValueError: The sim has no such roster (a build before SIM_VERSION 10).
    """
    for r in rlf_sim.mission_rosters(STATION_ASSAULT):
        if r["name"] == CITADEL_ROSTER:
            return Roster.of(r["fleets"][0], r["fleets"][1], mission=STATION_ASSAULT)
    raise ValueError(f"the sim has no {CITADEL_ROSTER!r} station roster")


PILOTS_KIND = "pilots"
# The most ships a drill fields: 4 pilots, 2 wards, 3 enemies a side
# (``spacefight.env.drills``).
MAX_DRILL_SHIPS = 12


@dataclass(frozen=True)
class PilotsDistribution:
    """Live rosters under both-sides conditions (module docstring). Plain types only.

    The roster parameters mirror the live page: ``default_roster_share`` is
    ``DEFAULT_ROSTER_SHARE`` in ``web/src/live/missions.ts``, the ``draft_*`` values
    are the bundle's roster rules (``tools/build_bundle.py``: ``MIN_PER_SIDE``,
    ``max_per_side`` and its default budget). ``tests/test_pilots_rosters.py`` checks
    them against that code.

    Attributes:
        kind: Always ``"pilots"`` (tells ``resolve_distribution`` the class apart).
        mission_weights: Weights of ``MISSIONS`` (deathmatch, carrier, convoy,
            station; three weights mean station 0). The default plays every live
            mission (the live page rotates all four), station assault a fifth.
        commander_p: Chance a match has orders shown on both sides (else hidden from
            both).
        mixed_p: Experimental (``docs/PILOT_TRAINING.md`` §3, training only): of the
            matches ``commander_p`` would show on both sides, the share that instead
            hides one side's orders, the side drawn at random per match. 0 draws no
            extra number, so the draws are those of a distribution without it.
        default_roster_share: Chance a carrier or convoy plays the mission's first
            roster (else one of the others, uniformly).
        draft_hulls: Hulls a deathmatch drafts.
        draft_min_per_side: Fewest ships a drafted side can be held to.
        draft_max_per_side: Most ships a drafted side can field.
        draft_budget: Cap on the credits each side spends.
        max_ships: Slots every roster of a mission with positive weight must fit.
        drill_share: Share of draws that are order drills (``docs/PILOT_TRAINING.md``
            §2) instead of matches; ``commander_p`` then splits what is left.
        drill_weights: Weights of the drill kinds ``DRILL_KINDS`` (go-to, attack,
            defend) among the drills.
        drill_goto_solo_share: Chance that a go-to drill is one ship alone whatever
            squad size it drew (``DrillGenerator``); 0 leaves every drill as it was.
        drill_attack_pool_share: Training only: the share of attack drills that are
            kite drills (``spacefight.env.drills``), their enemies flown by pilots from
            the trainer's opponent pool with their orders hidden. 0 draws no extra
            number, so the draws are those of a distribution without it.
        station_as_convoy_share: Chance a station assault reads to the nets as a
            convoy escort (``Roster.station_as`` ``"convoy"``), else as a carrier
            battle. 0 draws no extra number (every assault reads as a carrier battle,
            the sim's default).
        citadel_share: Chance a station assault plays the sim's v10 "citadel" roster
            (the citadel against a carrier, a dreadnought and nine: 19 ships, so
            ``max_ships`` must hold them), else the sim's first (v9) station roster.
            The default, 1, is the live page's (the citadel only, SIM_VERSION >= 10).
            0 draws no extra number, so the draws are those of v9.
        bomber_share: Training only: in a deathmatch, carrier battle or convoy, each
            strike slot (a ``FLEET_HULLS`` hull, either team) becomes a bomber with this
            chance, drawn slot by slot. A draft keeps its size, so a swapped side's cost
            moves by the hull's cost difference. A station assault keeps the sim's
            roster, which has bombers of its own. 0 draws no extra number.
        drill_bomber_share: Training only: in an attack or defend drill, each pilot
            slot becomes a bomber with this chance (one draw per pilot, after the
            drill's seed). Go-to drills are untouched: their deadlines come from the
            drawn hulls' speeds. 0 draws no extra number.
        drill_dock_share: SIM_VERSION 11: the share of drills that are dock drills
            (``spacefight.env.drills``, ``DRILL_DOCK``); the rest are drawn by
            ``drill_weights``. The default, 0.25, has dock drills in the mix whenever
            ``drill_share`` is set. 0 draws no extra number.
        drill_dock_threat_share: Of the dock drills, the share with enemies ordered
            onto the pilot (else it flies home alone). The drill generator draws it
            from the drill's own seed, so it draws no number here.

    Raises:
        ValueError: Bad weights, shares or draft sizes, or a live roster or a drill
            that does not fit ``max_ships``.
    """

    kind: str = PILOTS_KIND
    mission_weights: tuple[float, ...] = (0.3, 0.25, 0.25, 0.2)
    commander_p: float = 0.5
    mixed_p: float = 0.0
    default_roster_share: float = 0.5
    draft_hulls: tuple[str, ...] = FLEET_HULLS
    draft_min_per_side: int = 2
    draft_max_per_side: int = MAX_PER_SIDE
    draft_budget: float = 40.0
    max_ships: int = MAX_SHIPS
    drill_share: float = 0.0
    drill_weights: tuple[float, ...] = (1.0, 1.0, 1.0)
    drill_goto_solo_share: float = 0.0
    drill_attack_pool_share: float = 0.0
    station_as_convoy_share: float = 0.0
    bomber_share: float = 0.0
    drill_bomber_share: float = 0.0
    citadel_share: float = 1.0
    drill_dock_share: float = 0.25
    drill_dock_threat_share: float = 0.5

    def __post_init__(self) -> None:
        if self.kind != PILOTS_KIND:
            raise ValueError(f"kind must be {PILOTS_KIND!r}, got {self.kind!r}")
        object.__setattr__(
            self, "mission_weights", mission_weights_of(self.mission_weights)
        )
        if any(w < 0 for w in self.mission_weights) or sum(self.mission_weights) <= 0:
            raise ValueError("mission_weights must be >= 0 with a positive sum")
        for name in (
            "commander_p",
            "mixed_p",
            "default_roster_share",
            "drill_share",
            "drill_goto_solo_share",
            "drill_attack_pool_share",
            "station_as_convoy_share",
            "bomber_share",
            "drill_bomber_share",
            "citadel_share",
            "drill_dock_share",
            "drill_dock_threat_share",
        ):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {getattr(self, name)}")
        if len(self.drill_weights) != len(DRILL_KINDS):
            raise ValueError(f"drill_weights needs one weight per {DRILL_KINDS}")
        if any(w < 0 for w in self.drill_weights) or sum(self.drill_weights) <= 0:
            raise ValueError("drill_weights must be >= 0 with a positive sum")
        if self.drill_share > 0 and self.max_ships < MAX_DRILL_SHIPS:
            raise ValueError(
                f"drills reach {MAX_DRILL_SHIPS} ships > max_ships {self.max_ships}"
            )
        if not self.draft_hulls:
            raise ValueError("draft_hulls needs at least one hull")
        if not 1 <= self.draft_min_per_side <= self.draft_max_per_side <= MAX_PER_SIDE:
            raise ValueError(
                "need 1 <= draft_min_per_side <= draft_max_per_side <= "
                f"{MAX_PER_SIDE}, got {self.draft_min_per_side}, "
                f"{self.draft_max_per_side}"
            )
        if self.draft_budget <= 0:
            raise ValueError(f"draft_budget must be positive, got {self.draft_budget}")
        if self.max_ships > MAX_SHIPS:
            raise ValueError(f"max_ships {self.max_ships} > MAX_SHIPS {MAX_SHIPS}")
        for mission, weight in zip(MISSIONS, self.mission_weights):
            if weight <= 0:
                continue
            if mission == DEATHMATCH:
                widest = 2 * self.draft_max_per_side
            elif mission == STATION_ASSAULT:
                station = live_mission_rosters(mission)[0].n_ships
                citadel = citadel_roster().n_ships if self.citadel_share > 0 else 0
                widest = max(station, citadel)
            else:
                widest = max(r.n_ships for r in live_mission_rosters(mission))
            if widest > self.max_ships:
                raise ValueError(
                    f"{mission} rosters reach {widest} ships > max_ships "
                    f"{self.max_ships}"
                )

    def to_dict(self) -> dict[str, object]:
        """Plain dict (lists for tuples) for YAML."""
        return {
            k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> PilotsDistribution:
        """Inverse of ``to_dict``.

        Raises:
            ValueError: Unknown keys.
        """
        known = set(cls.__dataclass_fields__)
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown pilots distribution keys: {sorted(unknown)}")
        kwargs = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
        return cls(**kwargs)  # type: ignore[arg-type]


Distribution = RosterDistribution | OrdersDistribution | PilotsDistribution

# Named distributions for the CLI and configs.
ROSTER_PRESETS: dict[str, Distribution] = {
    "fleet_v1": RosterDistribution(),
    "orders_v1": OrdersDistribution(),
    "pilots_v1": PilotsDistribution(),
}


def resolve_distribution(spec: str | Mapping[str, object]) -> Distribution:
    """A preset name or a ``to_dict`` mapping -> distribution (the mapping's
    ``kind`` names an ``OrdersDistribution`` or a ``PilotsDistribution``; without one
    it is a ``RosterDistribution``).

    Raises:
        KeyError: Unknown preset name.
    """
    if isinstance(spec, str):
        if spec not in ROSTER_PRESETS:
            raise KeyError(
                f"unknown roster preset {spec!r}; known: {list(ROSTER_PRESETS)}"
            )
        return ROSTER_PRESETS[spec]
    if spec.get("kind") == ORDERS_KIND:
        return OrdersDistribution.from_dict(spec)
    if spec.get("kind") == PILOTS_KIND:
        return PilotsDistribution.from_dict(spec)
    return RosterDistribution.from_dict(spec)


class DrillSource(Protocol):
    """Makes drill rosters (``spacefight.env.drills.DrillGenerator``)."""

    def roster(self, kind: str, seed: int, kite: bool = False) -> Roster:
        """The ``kind`` drill of ``seed``; ``kite``: an attack's kite variant."""
        ...

    def dock_roster(self, seed: int) -> Roster:
        """The dock drill of ``seed`` (SIM_VERSION 11)."""
        ...


class Sampler(Protocol):
    """Draws rosters for ``RustVecEnv``; ``max_ships`` is the env's slot count."""

    @property
    def max_ships(self) -> int:
        """Slots every drawn roster fits in."""
        ...

    def sample(self) -> Roster:
        """One roster."""
        ...


def make_sampler(distribution: Distribution, seed: int) -> Sampler:
    """The sampler of ``distribution`` (``RosterSampler``, ``OrdersRosterSampler``
    or ``PilotsRosterSampler``)."""
    if isinstance(distribution, OrdersDistribution):
        return OrdersRosterSampler(distribution, seed)
    if isinstance(distribution, PilotsDistribution):
        return PilotsRosterSampler(distribution, seed)
    return RosterSampler(distribution, seed)


@dataclass
class RosterSampler:
    """Seeded draws from a ``RosterDistribution``.

    Args:
        distribution: The distribution.
        seed: Seed of the sampler's own generator.
        costs: Hull costs for drafts (default: from the asset YAML).

    Raises:
        ValueError: A draftable hull has no cost, or no hull fits the smallest
            budget.
    """

    distribution: RosterDistribution
    seed: int
    costs: dict[str, float] = field(default_factory=load_hull_costs)

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng([self.seed, 0xF1EE7])
        missing = [h for h in self.distribution.hulls if h not in self.costs]
        if missing:
            raise ValueError(f"no cost for hulls {missing}")
        if self.distribution.draft_p > 0:
            cheapest = min(self.costs[h] for h in self.distribution.hulls)
            if min(self.distribution.draft_budgets) < cheapest:
                raise ValueError("a draft budget is below the cheapest hull's cost")

    @property
    def max_ships(self) -> int:
        """Slots of a fleet env: two full sides."""
        return MAX_FLEET_SHIPS

    def sample(self) -> Roster:
        """One roster."""
        d, rng = self.distribution, self.rng
        if rng.random() < d.duel_p:
            roster = Roster.of(["fighter"], ["fighter"])
        elif rng.random() < d.draft_p:
            budget = float(rng.choice(d.draft_budgets))
            roster = Roster.of(self._draft(budget), self._draft(budget))
        else:
            roster = self._skirmish()
        teams = tuple(tuple(rng.permutation(list(t)).tolist()) for t in roster.teams)
        roster = Roster((teams[0], teams[1]))
        return roster.swapped() if rng.random() < 0.5 else roster

    def sample_many(self, n: int) -> list[Roster]:
        """``n`` rosters in draw order."""
        return [self.sample() for _ in range(n)]

    def _hulls(self, n: int) -> list[str]:
        d = self.distribution
        p = np.asarray(d.hull_weights, dtype=np.float64)
        return [str(h) for h in self.rng.choice(d.hulls, size=n, p=p / p.sum())]

    def _skirmish(self) -> Roster:
        d, rng = self.distribution, self.rng
        p = np.asarray(d.size_weights, dtype=np.float64)
        n0 = int(rng.choice(np.arange(1, MAX_PER_SIDE + 1), p=p / p.sum()))
        n1 = n0
        if rng.random() < d.uneven_p:
            n1 = int(np.clip(n0 + rng.choice([-1, 1]), 1, MAX_PER_SIDE))
            if n1 == n0:  # clipped at an end: go the other way
                n1 = n0 - 1 if n0 == MAX_PER_SIDE else n0 + 1
        team0 = self._hulls(n0)
        if n1 == n0 and rng.random() < d.mirror_p:
            team1 = list(team0)
        else:
            team1 = self._hulls(n1)
        return Roster.of(team0, team1)

    def _draft(self, budget: float) -> list[str]:
        hulls = self.distribution.hulls
        side: list[str] = []
        left = budget
        while len(side) < MAX_PER_SIDE:
            fits = [h for h in hulls if self.costs[h] <= left]
            if not fits:
                break
            pick = str(fits[int(self.rng.integers(len(fits)))])
            side.append(pick)
            left -= self.costs[pick]
        return side


@dataclass
class OrdersRosterSampler:
    """Seeded draws from an ``OrdersDistribution`` (module docstring).

    Slot order: a carrier battle is ``[carrier, wing...]`` a side (the sim launches
    the wing in slot order after the first ``jump_in`` jump in); a convoy is
    ``[transports..., escorts...]`` v ``[attackers...]``. Wings, escorts and
    attackers are drawn in random order; a deathmatch draw keeps the fleet
    sampler's own shuffles and team swap.

    Args:
        distribution: The distribution.
        seed: Seed of the sampler's own generator (the nested fleet sampler is
            seeded from it too).
    """

    distribution: OrdersDistribution
    seed: int

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng([self.seed, 0x0D3E5])
        fleet = resolve_distribution(self.distribution.deathmatch)
        if not isinstance(fleet, RosterDistribution):
            raise ValueError("the deathmatch preset must be a fleet distribution")
        self.fleet = RosterSampler(fleet, self.seed)

    @property
    def max_ships(self) -> int:
        """Slots of a mission training env."""
        return self.distribution.max_ships

    def sample(self) -> Roster:
        """One roster (the env pads it to ``max_ships``)."""
        d, rng = self.distribution, self.rng
        p = np.asarray(d.mission_weights, dtype=np.float64)
        mission = MISSIONS[int(rng.choice(len(MISSIONS), p=p / p.sum()))]
        modes = [RANDOM if rng.random() < d.random_commander_p else SCRIPTED]
        modes.append(RANDOM if rng.random() < d.random_commander_p else SCRIPTED)
        teams: tuple[tuple[str, ...], tuple[str, ...]]
        if mission == DEATHMATCH:
            teams = self.fleet.sample().teams
        elif mission == STATION_ASSAULT:
            teams = live_mission_rosters(STATION_ASSAULT)[0].teams
        elif mission == CARRIER_BATTLE:
            wing0 = self._strike(self._count(d.carrier_wing))
            if rng.random() < d.wing_mirror_p:
                wing1 = [str(h) for h in rng.permutation(wing0)]
            else:
                wing1 = self._strike(self._count(d.carrier_wing))
            teams = ((d.carrier_hull, *wing0), (d.carrier_hull, *wing1))
        else:
            convoy = [d.transport_hull] * self._count(d.convoy_transports)
            escorts = self._strike(self._count(d.convoy_escorts))
            attackers = self._strike(self._count(d.convoy_attackers))
            teams = (tuple(convoy + escorts), tuple(attackers))
        return Roster(teams, mission, (modes[0], modes[1]))

    def sample_many(self, n: int) -> list[Roster]:
        """``n`` rosters in draw order."""
        return [self.sample() for _ in range(n)]

    def _count(self, low_high: tuple[int, ...]) -> int:
        return int(self.rng.integers(low_high[0], low_high[1] + 1))

    def _strike(self, n: int) -> list[str]:
        d = self.distribution
        p = np.asarray(d.strike_weights, dtype=np.float64)
        return [str(h) for h in self.rng.choice(d.strike_hulls, size=n, p=p / p.sum())]


@dataclass
class PilotsRosterSampler:
    """Seeded draws from a ``PilotsDistribution`` (module docstring).

    Slot order is the live page's: a mission roster keeps the sim's order (a carrier
    launches its wing in it), a drafted side its draw order. Neither side is shuffled
    or swapped; a draft treats the two sides alike, and a convoy must stay team 0.

    Args:
        distribution: The distribution.
        seed: Seed of the sampler's own generator.
        costs: Hull costs for drafts (default: from the asset YAML).

    Raises:
        ValueError: A draftable hull has no cost, or the budget cannot field
            ``draft_min_per_side`` of the cheapest hull.
    """

    distribution: PilotsDistribution
    seed: int
    costs: dict[str, float] = field(default_factory=load_hull_costs)

    def __post_init__(self) -> None:
        self.rng = np.random.default_rng([self.seed, 0x91107])
        d = self.distribution
        missing = [h for h in d.draft_hulls if h not in self.costs]
        if missing:
            raise ValueError(f"no cost for hulls {missing}")
        self.cheapest = min(self.costs[h] for h in d.draft_hulls)
        if d.draft_budget < self.cheapest * d.draft_min_per_side:
            raise ValueError(
                f"draft_budget {d.draft_budget} cannot field {d.draft_min_per_side} "
                f"of the cheapest hull ({self.cheapest})"
            )
        self.live: dict[str, tuple[Roster, ...]] = {
            mission: live_mission_rosters(mission)
            for mission, weight in zip(MISSIONS, d.mission_weights)
            if mission != DEATHMATCH and weight > 0
        }
        # A station assault plays the sim's first (v9) roster; the v10 citadel one only
        # by ``citadel_share``.
        if STATION_ASSAULT in self.live:
            self.live[STATION_ASSAULT] = self.live[STATION_ASSAULT][:1]
        self.citadel: Roster | None = citadel_roster() if d.citadel_share > 0 else None
        self.drills: DrillSource | None = None
        if d.drill_share > 0:
            # Imported here: spacefight.env.drills builds Rosters from this module.
            from spacefight.env.drills import DrillGenerator

            self.drills = DrillGenerator(
                goto_solo_share=d.drill_goto_solo_share,
                dock_threat_share=d.drill_dock_threat_share,
            )

    @property
    def max_ships(self) -> int:
        """Slots of the env: the biggest live roster by default."""
        return self.distribution.max_ships

    def sample(self) -> Roster:
        """One roster (the env pads it to ``max_ships``). With ``drill_share`` 0 no
        extra number is drawn, so the draws are those of a distribution without drills;
        likewise ``mixed_p``, ``station_as_convoy_share`` and ``bomber_share`` at 0
        draw nothing.
        """
        d, rng = self.distribution, self.rng
        if self.drills is not None and rng.random() < d.drill_share:
            return self._drill()
        p = np.asarray(d.mission_weights, dtype=np.float64)
        mission = MISSIONS[int(rng.choice(len(MISSIONS), p=p / p.sum()))]
        roster = self._draft() if mission == DEATHMATCH else self._live_roster(mission)
        if mission == STATION_ASSAULT:
            if self.citadel is not None and rng.random() < d.citadel_share:
                roster = self.citadel
            if d.station_as_convoy_share > 0 and (
                rng.random() < d.station_as_convoy_share
            ):
                roster = replace(roster, station_as=STATION_AS_CONVOY)
        elif d.bomber_share > 0:
            roster = self._with_bombers(roster)
        hidden = not bool(rng.random() < d.commander_p)
        if not hidden and d.mixed_p > 0 and rng.random() < d.mixed_p:
            side = int(rng.integers(2))
            return replace(roster, hide_orders=(side == 0, side == 1))
        return replace(roster, hide_orders=(hidden, hidden))

    def sample_many(self, n: int) -> list[Roster]:
        """``n`` rosters in draw order."""
        return [self.sample() for _ in range(n)]

    def _drill(self) -> Roster:
        """A fresh drill: a dock drill by ``drill_dock_share`` (only when it is set),
        else a kind by ``drill_weights``, then for an attack whether it is a kite drill
        (only with ``drill_attack_pool_share``), the rest from a drawn seed."""
        d, rng = self.distribution, self.rng
        if self.drills is None:
            raise RuntimeError("_drill called without drill_share")
        if d.drill_dock_share > 0 and rng.random() < d.drill_dock_share:
            return self.drills.dock_roster(int(rng.integers(2**62)))
        p = np.asarray(d.drill_weights, dtype=np.float64)
        kind = DRILL_KINDS[int(rng.choice(len(DRILL_KINDS), p=p / p.sum()))]
        kite = (
            kind == DRILL_ATTACK
            and d.drill_attack_pool_share > 0
            and bool(rng.random() < d.drill_attack_pool_share)
        )
        seed = int(rng.integers(2**62))
        if kite:
            roster = self.drills.roster(kind, seed, kite=True)
        else:
            roster = self.drills.roster(kind, seed)
        if d.drill_bomber_share > 0 and kind != DRILL_GOTO and roster.drill is not None:
            team0 = list(roster.teams[0])
            for slot in roster.drill.pilots:
                if rng.random() < d.drill_bomber_share:
                    team0[slot] = BOMBER
            roster = replace(roster, teams=(tuple(team0), roster.teams[1]))
        return roster

    def _with_bombers(self, roster: Roster) -> Roster:
        """``roster`` with each strike slot a bomber with chance ``bomber_share``
        (one draw per strike slot, team 0 first, in slot order)."""
        share, rng = self.distribution.bomber_share, self.rng
        teams = tuple(
            tuple(
                BOMBER if h in FLEET_HULLS and rng.random() < share else h for h in team
            )
            for team in roster.teams
        )
        return replace(roster, teams=(teams[0], teams[1]))

    def _live_roster(self, mission: str) -> Roster:
        """``fromSim`` in ``web/src/live/missions.ts``."""
        rosters = self.live[mission]
        rng = self.rng
        if len(rosters) == 1 or rng.random() < self.distribution.default_roster_share:
            return rosters[0]
        return rosters[1 + int(rng.integers(len(rosters) - 1))]

    def _draft(self) -> Roster:
        """``chooseRoster``'s draft in ``web/src/live/roster.ts``: the two sides share
        a budget and spend it independently, so they can differ in size."""
        d = self.distribution
        size = int(self.rng.integers(d.draft_min_per_side, d.draft_max_per_side + 1))
        budget = min(d.draft_budget, self.cheapest * size)
        return Roster.of(self._draft_side(budget), self._draft_side(budget))

    def _draft_side(self, budget: float) -> list[str]:
        """``draftSide``: spend ``budget`` on random affordable hulls until nothing
        fits or the side is full, never leaving too little to reach the minimum."""
        d = self.distribution
        side: list[str] = []
        left = budget
        while len(side) < d.draft_max_per_side:
            still_needed = max(0, d.draft_min_per_side - len(side) - 1)
            reserve = self.cheapest * still_needed
            fits = [h for h in d.draft_hulls if self.costs[h] + reserve <= left]
            if not fits:
                break
            pick = fits[int(self.rng.integers(len(fits)))]
            side.append(pick)
            left -= self.costs[pick]
        return side
