"""A commander stable for pilot training: who commands each side of a training match.

The live page draws each side's commander from ``lab/live_commanders.json``. A pilot
trainer with a stable does the same for its matches (``docs/PILOT_TRAINING.md`` §3):
``StableSampler`` wraps the trainer's roster sampler and, on every roster it draws that
is not a drill, replaces the commander of each team whose orders are shown with a draw
from the stable, independently per side, and tags it with that commander's id
(``Roster.commander_ids``). A team with hidden orders keeps its scripted commander, since
"no commander" means the script runs the logistics; a drill keeps its external
commanders. The wrapper draws from its own generator, so the inner sampler's draws are
those it would make without a stable.

Specs: ``scripted``, ``random``, ``live`` (every commander of the live stable, the learned
ones fetched sha-checked by ``tools.live_commanders``) or a commander checkpoint
(``spacefight.commander.policy.save_commander``). Each spec has a weight (default 1); a
``live`` spec's weight is split evenly over its commanders.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

import numpy as np

from spacefight.commander.eval import Commander
from spacefight.commander.policy import CommanderActor
from spacefight.env.rosters import LEARNED, Roster, Sampler

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_SPEC: Final = "live"
DEFAULT_LIVE_REGISTRY: Final = REPO_ROOT / "lab" / "live_commanders.json"
# How the logs name a team with orders hidden: no commander, whatever runs underneath.
NO_COMMANDER: Final = "no_commander"
_STABLE_STREAM: Final = 0xC0FFEE


@dataclass(frozen=True)
class CommanderStable:
    """Commanders and the chance of each being drawn for a side.

    Attributes:
        commanders: The commanders, with distinct labels.
        weights: Draw probabilities, one per commander, summing to 1.

    Raises:
        ValueError: No commanders, repeated labels, or weights that do not fit.
    """

    commanders: tuple[Commander, ...]
    weights: tuple[float, ...]

    def __post_init__(self) -> None:
        labels = self.ids
        if not labels or len(set(labels)) != len(labels):
            raise ValueError(f"a stable needs distinct commanders, got {labels}")
        if len(self.weights) != len(labels):
            raise ValueError(
                f"{len(self.weights)} weights for {len(labels)} commanders"
            )
        if any(w < 0 for w in self.weights) or not np.isclose(sum(self.weights), 1.0):
            raise ValueError(f"weights must be >= 0 and sum to 1, got {self.weights}")
        for c in self.commanders:
            if (c.mode == LEARNED) != (c.actor is not None):
                raise ValueError(f"{c.label}: a network if and only if learned")

    @property
    def ids(self) -> tuple[str, ...]:
        """Every commander's label, in stable order."""
        return tuple(c.label for c in self.commanders)

    def learned(self) -> list[tuple[int, CommanderActor]]:
        """``(index, actor)`` of every learned commander (``decide_learned``)."""
        return [
            (k, c.actor) for k, c in enumerate(self.commanders) if c.actor is not None
        ]

    def draw(self, rng: np.random.Generator) -> Commander:
        """One commander, by the stable's weights."""
        return self.commanders[int(rng.choice(len(self.commanders), p=self.weights))]


def resolve_stable(
    specs: Sequence[str],
    weights: Sequence[float] = (),
    live_registry: Path = DEFAULT_LIVE_REGISTRY,
) -> CommanderStable:
    """The stable named by ``specs`` (module docstring), with per-spec ``weights``
    (empty: 1 each).

    Raises:
        ValueError: No specs, a weight count that does not match, negative weights or
            a zero total, or two commanders with the same label.
        FileNotFoundError: A checkpoint is missing.
    """
    # Imported here: only a run with a stable needs the registry's tools.
    from spacefight.population.war_matches import resolve_commanders

    if not specs:
        raise ValueError("a stable needs at least one commander spec")
    spec_weights = [float(w) for w in weights] if weights else [1.0] * len(specs)
    if len(spec_weights) != len(specs):
        raise ValueError(f"{len(spec_weights)} weights for {len(specs)} specs")
    if any(w < 0 for w in spec_weights) or sum(spec_weights) <= 0:
        raise ValueError(f"weights must be >= 0 with a positive sum: {spec_weights}")
    commanders: list[Commander] = []
    per_commander: list[float] = []
    for spec, weight in zip(specs, spec_weights):
        group = [c for c, _ in resolve_commanders([spec], live_registry)]
        commanders.extend(group)
        per_commander.extend([weight / len(group)] * len(group))
    total = sum(per_commander)
    return CommanderStable(tuple(commanders), tuple(w / total for w in per_commander))


def commander_label(roster: Roster, team: int) -> str:
    """How logs name ``team``'s commander: the stable's id if one was drawn, else
    ``NO_COMMANDER`` if its orders are hidden, else its sim mode."""
    if roster.commander_ids[team]:
        return roster.commander_ids[team]
    if roster.hide_orders[team]:
        return NO_COMMANDER
    return roster.commanders[team]


class StableSampler:
    """A roster sampler whose matches draw their commanders from a stable.

    Args:
        inner: The sampler that draws the rosters.
        stable: The commanders.
        seed: Seed of the commander draws (separate from ``inner``'s).
    """

    def __init__(self, inner: Sampler, stable: CommanderStable, seed: int) -> None:
        self.inner = inner
        self.stable = stable
        self.rng = np.random.default_rng([seed, _STABLE_STREAM])

    @property
    def max_ships(self) -> int:
        """The inner sampler's slots."""
        return self.inner.max_ships

    def sample(self) -> Roster:
        """The inner sampler's next roster, its shown sides commanded from the stable
        (a drill unchanged)."""
        roster = self.inner.sample()
        if roster.drill is not None:
            return roster
        modes = list(roster.commanders)
        ids = list(roster.commander_ids)
        for team in (0, 1):
            if roster.hide_orders[team]:
                continue
            drawn = self.stable.draw(self.rng)
            modes[team], ids[team] = drawn.mode, drawn.label
        return replace(
            roster, commanders=(modes[0], modes[1]), commander_ids=(ids[0], ids[1])
        )
