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
names its mission (``deathmatch``, ``carrier_battle``, ``convoy_escort``) and each
team's commander mode (``scripted``, ``random``; SIM_VERSION 5). One draw picks the
mission by ``mission_weights``; a deathmatch is a draw from the nested fleet preset;
a carrier battle is a carrier plus a wing of strike craft a side; a convoy is
freighters plus escorts (team 0, the sim's convoy side) against a strike force.
Each team's commander is ``random`` with ``random_commander_p``. Matches pad to
``MAX_TRAIN_SHIPS`` (12) slots. Capital ships (``CAPITAL_ROLES``) are flown by the
sim's scripts, never by the learned pilot.

Live rosters (``docs/PILOT_TRAINING.md`` §3, preset ``pilots_v1``,
``PilotsDistribution``): a training match is drawn the way the live page draws one, so
pilots train on what they will play. One draw picks the mission by ``mission_weights``.
A deathmatch is the page's budget draft (``web/src/live/roster.ts``, ``chooseRoster``):
a size from ``draft_min_per_side..draft_max_per_side``, a budget of that many of the
cheapest hull, then each side spends it independently. A carrier battle or a convoy is
one of the sim's own rosters, read from ``rlf_sim.mission_rosters`` at run time and
never copied here (``web/src/live/missions.ts``, ``fromSim``): the first, the sim's
default, with ``default_roster_share``, else one of the others uniformly. Both teams
have ``scripted`` commanders. With ``commander_p`` their orders are shown; otherwise
they are hidden from both teams (``Roster.hide_orders``), which is "no commander": the
script's logistics still run, because a carrier or a convoy cannot play without them.
The condition is always the same on both sides.

Order drills (``docs/PILOT_TRAINING.md`` §2): with ``drill_share`` a ``PilotsDistribution``
also draws drills from ``spacefight.env.drills``. A drill is a ``Roster`` like any other,
with a start layout, the orders it opens with, its own clock and drill rules; ``drill``
tells the trainer and the logs what it is.
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
# ships flown by scripts, SIM_SPEC §11), and the most ships a side can field.
FLEET_HULLS: tuple[str, ...] = ("fighter", "strafer", "gunship")
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
MISSIONS: tuple[str, ...] = (DEATHMATCH, CARRIER_BATTLE, CONVOY_ESCORT)
# Order drills (``docs/PILOT_TRAINING.md`` §2), in ``drill_weights`` order.
DRILL_GOTO, DRILL_ATTACK, DRILL_DEFEND = "goto", "attack", "defend"
DRILL_KINDS: tuple[str, ...] = (DRILL_GOTO, DRILL_ATTACK, DRILL_DEFEND)
SCRIPTED = "scripted"
RANDOM = "random"
EXTERNAL = "external"
COMMANDER_MODES: tuple[str, ...] = (SCRIPTED, RANDOM, EXTERNAL)
# Hull roles the learned pilot never flies (SIM_SPEC §11: scripts fly them).
CAPITAL_ROLES: frozenset[str] = frozenset({"carrier", "transport"})

_ABBREV = {
    "fighter": "F",
    "strafer": "S",
    "gunship": "G",
    "carrier": "C",
    "freighter": "T",
}
_MISSION_ABBREV = {CARRIER_BATTLE: "carrier", CONVOY_ESCORT: "convoy"}


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


@dataclass(frozen=True)
class OpeningOrder:
    """A squad order an ``external`` team opens a match with (SIM_SPEC §10.3).

    ``RustVecEnv`` queues it when the match is built and the sim applies it on the
    match's first slow tick.

    Attributes:
        team: The team.
        squad: Squad index.
        members: The squad's slots.
        kind: ``"attack"``, ``"defend"`` or ``"goto"``.
        target: The attack target's or the defend ward's slot; -1 for a go-to.
        point: The go-to point, metres.
        radius: The go-to radius, metres.
    """

    team: int
    squad: int
    members: tuple[int, ...]
    kind: str
    target: int = -1
    point: tuple[float, float] = (0.0, 0.0)
    radius: float = 0.0

    def command(self) -> dict[str, object]:
        """The sim's command dict.

        Raises:
            ValueError: An unknown order kind.
        """
        order: dict[str, object]
        if self.kind == "attack":
            order = {"kind": "attack", "target": self.target}
        elif self.kind == "defend":
            order = {"kind": "defend", "ward": self.target}
        elif self.kind == "goto":
            order = {"kind": "goto", "point": list(self.point), "radius": self.radius}
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
    """

    kind: str
    pilots: tuple[int, ...]
    named_slot: int = -1
    named_group: tuple[int, ...] = ()
    other_group: tuple[int, ...] = ()


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
            deathmatch only.
        opening_orders: Orders ``RustVecEnv`` queues whenever this roster's match is
            built, for teams with ``external`` commanders.
        time_limit_s: The match's clock; 0: the env's or the mission's default.
        drill: Set on a drill match (``spacefight.env.drills``): the sim plays it under
            drill rules (SIM_SPEC §5.10). ``None`` on every other match.

    Raises:
        ValueError: An empty team, more than ``MAX_SHIPS`` ships, an unknown mission
            or commander mode, ``hide_orders`` not two bools, a layout that does not
            have one entry per ship or is not on a deathmatch, or a drill without a
            layout.
    """

    teams: tuple[tuple[str, ...], tuple[str, ...]]
    mission: str = DEATHMATCH
    commanders: tuple[str, str] = (SCRIPTED, SCRIPTED)
    hide_orders: tuple[bool, bool] = (False, False)
    start_layout: tuple[ShipStart, ...] = ()
    opening_orders: tuple[OpeningOrder, ...] = ()
    time_limit_s: float = 0.0
    drill: DrillTag | None = None

    def __post_init__(self) -> None:
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
        if self.start_layout:
            if len(self.start_layout) != self.n_ships:
                raise ValueError(
                    f"start_layout has {len(self.start_layout)} entries for "
                    f"{self.n_ships} ships"
                )
            if self.mission != DEATHMATCH:
                raise ValueError(f"{self.mission} places its own ships")
        elif self.drill is not None:
            raise ValueError("a drill needs a start_layout")
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
    """Hull name -> ``speed_cap`` (m/s) from every ``hulls/*/hull.yaml``.

    Raises:
        FileNotFoundError: No hull YAML under ``assets_dir``.
        ValueError: A hull YAML without a positive ``speed_cap``.
    """
    paths = sorted((assets_dir / "hulls").glob("*/hull.yaml"))
    if not paths:
        raise FileNotFoundError(f"no hulls/*/hull.yaml under {assets_dir}")
    caps: dict[str, float] = {}
    for path in paths:
        raw = yaml.safe_load(path.read_text())
        cap = raw.get("speed_cap") if isinstance(raw, dict) else None
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
    """Hull names in hull-id order: the sim's catalogue numbers the hull
    directories in sorted name order (``Catalogue::load_dir``).

    Raises:
        FileNotFoundError: No hull directories.
    """
    names = sorted(p.parent.name for p in (assets_dir / "hulls").glob("*/hull.yaml"))
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
        mission_weights: Weights of ``MISSIONS`` (deathmatch, carrier, convoy).
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
    mission_weights: tuple[float, ...] = (0.4, 0.3, 0.3)
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
        if len(self.mission_weights) != len(MISSIONS):
            raise ValueError(f"mission_weights needs one weight per {MISSIONS}")
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
        mission_weights: Weights of ``MISSIONS`` (deathmatch, carrier, convoy).
        commander_p: Chance a match has orders shown on both sides (else hidden from
            both).
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

    Raises:
        ValueError: Bad weights, shares or draft sizes, or a live roster or a drill
            that does not fit ``max_ships``.
    """

    kind: str = PILOTS_KIND
    mission_weights: tuple[float, ...] = (0.4, 0.3, 0.3)
    commander_p: float = 0.5
    default_roster_share: float = 0.5
    draft_hulls: tuple[str, ...] = FLEET_HULLS
    draft_min_per_side: int = 2
    draft_max_per_side: int = MAX_PER_SIDE
    draft_budget: float = 40.0
    max_ships: int = MAX_SHIPS
    drill_share: float = 0.0
    drill_weights: tuple[float, ...] = (1.0, 1.0, 1.0)

    def __post_init__(self) -> None:
        if self.kind != PILOTS_KIND:
            raise ValueError(f"kind must be {PILOTS_KIND!r}, got {self.kind!r}")
        if len(self.mission_weights) != len(MISSIONS):
            raise ValueError(f"mission_weights needs one weight per {MISSIONS}")
        if any(w < 0 for w in self.mission_weights) or sum(self.mission_weights) <= 0:
            raise ValueError("mission_weights must be >= 0 with a positive sum")
        for name in ("commander_p", "default_roster_share", "drill_share"):
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
            widest = (
                2 * self.draft_max_per_side
                if mission == DEATHMATCH
                else max(r.n_ships for r in live_mission_rosters(mission))
            )
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

    def roster(self, kind: str, seed: int) -> Roster:
        """The ``kind`` drill of ``seed``."""
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
        self.drills: DrillSource | None = None
        if d.drill_share > 0:
            # Imported here: spacefight.env.drills builds Rosters from this module.
            from spacefight.env.drills import DrillGenerator

            self.drills = DrillGenerator()

    @property
    def max_ships(self) -> int:
        """Slots of the env: the biggest live roster by default."""
        return self.distribution.max_ships

    def sample(self) -> Roster:
        """One roster (the env pads it to ``max_ships``). With ``drill_share`` 0 no
        extra number is drawn, so the draws are those of a distribution without drills.
        """
        d, rng = self.distribution, self.rng
        if self.drills is not None and rng.random() < d.drill_share:
            return self._drill()
        p = np.asarray(d.mission_weights, dtype=np.float64)
        mission = MISSIONS[int(rng.choice(len(MISSIONS), p=p / p.sum()))]
        roster = self._draft() if mission == DEATHMATCH else self._live_roster(mission)
        hidden = not bool(rng.random() < d.commander_p)
        return replace(roster, hide_orders=(hidden, hidden))

    def sample_many(self, n: int) -> list[Roster]:
        """``n`` rosters in draw order."""
        return [self.sample() for _ in range(n)]

    def _drill(self) -> Roster:
        """A fresh drill: a kind by ``drill_weights``, the rest from a drawn seed."""
        d, rng = self.distribution, self.rng
        if self.drills is None:
            raise RuntimeError("_drill called without drill_share")
        p = np.asarray(d.drill_weights, dtype=np.float64)
        kind = DRILL_KINDS[int(rng.choice(len(DRILL_KINDS), p=p / p.sum()))]
        return self.drills.roster(kind, int(rng.integers(2**62)))

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
