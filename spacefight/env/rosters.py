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
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
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
# Slots per match of a mission training env (SIM_VERSION 5's ``MAX_TRAIN_SHIPS``;
# live rosters go to 18): carrier + 5 a side, or 4 freighters + 3 escorts v 5.
MAX_TRAIN_SHIPS = 12

DEATHMATCH = "deathmatch"
CARRIER_BATTLE = "carrier_battle"
CONVOY_ESCORT = "convoy_escort"
MISSIONS: tuple[str, ...] = (DEATHMATCH, CARRIER_BATTLE, CONVOY_ESCORT)
SCRIPTED = "scripted"
RANDOM = "random"
COMMANDER_MODES: tuple[str, ...] = (SCRIPTED, RANDOM, "external")
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
class Roster:
    """Two teams' hulls in slot order, the mission and each team's commander.

    Attributes:
        teams: ``(team 0 hulls, team 1 hulls)``.
        mission: One of ``MISSIONS``.
        commanders: Each team's commander mode (``COMMANDER_MODES``).

    Raises:
        ValueError: An empty team, more than ``MAX_SHIPS`` ships, or an unknown
            mission or commander mode.
    """

    teams: tuple[tuple[str, ...], tuple[str, ...]]
    mission: str = DEATHMATCH
    commanders: tuple[str, str] = (SCRIPTED, SCRIPTED)

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

    @classmethod
    def of(
        cls,
        team0: Sequence[str],
        team1: Sequence[str],
        mission: str = DEATHMATCH,
        commanders: Sequence[str] = (SCRIPTED, SCRIPTED),
    ) -> Roster:
        """Build from two hull-name sequences."""
        pair = tuple(commanders)
        if len(pair) != 2:
            raise ValueError(f"commanders must name two modes, got {pair}")
        return cls((tuple(team0), tuple(team1)), mission, (pair[0], pair[1]))

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
        mission."""
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
        """The same match with the teams (and their commanders) exchanged.

        Raises:
            ValueError: A convoy, whose transports must be team 0.
        """
        if self.mission == CONVOY_ESCORT:
            raise ValueError("a convoy cannot swap teams: the convoy is team 0")
        return Roster(
            (self.teams[1], self.teams[0]),
            self.mission,
            (self.commanders[1], self.commanders[0]),
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


Distribution = RosterDistribution | OrdersDistribution

# Named distributions for the CLI and configs.
ROSTER_PRESETS: dict[str, Distribution] = {
    "fleet_v1": RosterDistribution(),
    "orders_v1": OrdersDistribution(),
}


def resolve_distribution(spec: str | Mapping[str, object]) -> Distribution:
    """A preset name or a ``to_dict`` mapping -> distribution (an
    ``OrdersDistribution`` when the mapping's ``kind`` is ``"orders"``).

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
    return RosterDistribution.from_dict(spec)


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
    """The sampler of ``distribution`` (``RosterSampler`` or
    ``OrdersRosterSampler``)."""
    if isinstance(distribution, OrdersDistribution):
        return OrdersRosterSampler(distribution, seed)
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
