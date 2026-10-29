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
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import rlf_sim
import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSETS = REPO_ROOT / "assets"

# Hulls a fleet pilot flies, and the most ships a side can field (MAX_SHIPS = 8).
FLEET_HULLS: tuple[str, ...] = ("fighter", "strafer", "gunship")
MAX_PER_SIDE = 4
MAX_SHIPS: int = int(rlf_sim.MAX_SHIPS)

_ABBREV = {"fighter": "F", "strafer": "S", "gunship": "G"}


def arena_radius_for(n_ships: int) -> float:
    """Arena radius (m) for ``n_ships`` ships in total: the sim's shared rule."""
    return float(rlf_sim.arena_radius_for(n_ships))


@dataclass(frozen=True)
class Roster:
    """Two teams' hulls in slot order.

    Attributes:
        teams: ``(team 0 hulls, team 1 hulls)``.

    Raises:
        ValueError: An empty team, or more than ``MAX_SHIPS`` ships.
    """

    teams: tuple[tuple[str, ...], tuple[str, ...]]

    def __post_init__(self) -> None:
        if len(self.teams) != 2 or any(len(t) == 0 for t in self.teams):
            raise ValueError(f"a roster needs two non-empty teams, got {self.teams}")
        if self.n_ships > MAX_SHIPS:
            raise ValueError(f"{self.n_ships} ships exceed MAX_SHIPS = {MAX_SHIPS}")

    @classmethod
    def of(cls, team0: Sequence[str], team1: Sequence[str]) -> Roster:
        """Build from two hull-name sequences."""
        return cls((tuple(team0), tuple(team1)))

    @property
    def n_ships(self) -> int:
        """Ships in the match."""
        return len(self.teams[0]) + len(self.teams[1])

    @property
    def arena_radius(self) -> float:
        """Arena radius from the shared rule."""
        return arena_radius_for(self.n_ships)

    @property
    def size_class(self) -> str:
        """``"<n0>v<n1>"`` with the larger side second (e.g. ``"2v3"``)."""
        a, b = sorted(len(t) for t in self.teams)
        return f"{a}v{b}"

    @property
    def label(self) -> str:
        """Short label, e.g. ``"FS v GF"``."""
        return " v ".join("".join(_ABBREV.get(h, h) for h in t) for t in self.teams)

    def fleets(self) -> list[list[str]]:
        """``[[team 0 hulls], [team 1 hulls]]`` as the env takes them."""
        return [list(t) for t in self.teams]

    def swapped(self) -> Roster:
        """The same match with the teams exchanged."""
        return Roster((self.teams[1], self.teams[0]))

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


# Named distributions for the CLI and configs.
ROSTER_PRESETS: dict[str, RosterDistribution] = {
    "fleet_v1": RosterDistribution(),
}


def resolve_distribution(spec: str | Mapping[str, object]) -> RosterDistribution:
    """A preset name or a ``to_dict`` mapping -> distribution.

    Raises:
        KeyError: Unknown preset name.
    """
    if isinstance(spec, str):
        if spec not in ROSTER_PRESETS:
            raise KeyError(
                f"unknown roster preset {spec!r}; known: {list(ROSTER_PRESETS)}"
            )
        return ROSTER_PRESETS[spec]
    return RosterDistribution.from_dict(spec)


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
