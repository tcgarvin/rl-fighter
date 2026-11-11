"""Facts the ``/commander/`` page states, computed from the code, and a check of the page.

The page (``web/commander/index.html``) is static prose, written like ``/pilot/``: every
number in it that can drift sits in an element with a ``data-fact="<key>"`` attribute.
This module computes the same facts from their sources:

- the input and output layout from ``spacefight.commander.io``;
- the layer sizes and parameter counts from ``spacefight.commander.policy`` (the actor
  and critic are instantiated, so the counts are counted, not typed in; the critic at
  the size of the live pilot list, ``lab/live_pilots.json``);
- the training setup from ``spacefight.commander.train.TrainConfig``'s defaults;
- the constants that live only in the sim and the agreed design (the learned cadence,
  the map points' radii, the go-to radius) from ``docs/COMMANDER.md``, cross-checked
  against ``spacefight.commander.io`` and, when the built ``rlf_sim`` exposes
  ``commander_io()``, against the sim.

``check_page`` (shared with ``tools/pilot_facts.py``) lists every element whose text
disagrees. ``scripts/build_pages_data.sh`` runs the check on every site build:

    python -m tools.commander_facts --page web/commander/index.html
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import fields
from pathlib import Path

import torch.nn as nn

import rlf_sim
from spacefight.commander import io
from spacefight.commander.policy import (
    HEADS,
    SQUAD_EMBED,
    SUMMARY,
    WIDTH,
    CommanderActor,
    CommanderCritic,
    n_params,
)
from spacefight.commander.train import OPP_NAMES, TrainConfig
from tools.pilot_facts import PilotFactsError, check_page, page_facts

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGE = REPO_ROOT / "web/commander/index.html"
DESIGN_DOC = REPO_ROOT / "docs/COMMANDER.md"
LIVE_PILOTS = REPO_ROOT / "lab/live_pilots.json"
TICK_HZ = 30


class CommanderFactsError(PilotFactsError):
    """A source the commander facts come from is missing or disagrees with another."""


def _n(value: int) -> str:
    """Thousands with commas, as the page writes them."""
    return f"{value:,}"


def _pct(share: float) -> str:
    return f"{round(share * 100)} %"


def _doc_int(doc: str, name: str) -> int:
    """The integer the design doc gives a constant, written as `` `NAME = 30` ``."""
    found = re.search(rf"`{name} = (\d+)", doc)
    if found is None:
        raise CommanderFactsError(f"{DESIGN_DOC.name} does not state `{name} = ...`")
    return int(found.group(1))


def _doc_float(doc: str, name: str) -> float:
    number = r"(\d+(?:\.\d+)?)"
    found = re.search(rf"`{name}`\s+starts at {number}|`{name} = {number}", doc)
    if found is None:
        raise CommanderFactsError(f"{DESIGN_DOC.name} does not state {name}")
    return float(found.group(1) or found.group(2))


def _doc_radii(doc: str) -> tuple[float, ...]:
    found = re.search(r"radius `\(([0-9., ]+)\)\[r\] R`", doc)
    if found is None:
        raise CommanderFactsError(f"{DESIGN_DOC.name} does not state the point radii")
    return tuple(float(r) for r in found.group(1).split(","))


def _doc_bearing(doc: str) -> int:
    found = re.search(r"bearing `(\d+) b` degrees", doc)
    if found is None:
        raise CommanderFactsError(f"{DESIGN_DOC.name} does not state the point bearing")
    return int(found.group(1))


def map_points(radii: Sequence[float], bearing_deg: int) -> list[tuple[float, float]]:
    """The commander's map points in the team frame, in units of the arena radius:
    point 0 the centre, point ``1 + 8 r + b`` at ``radii[r]`` and ``bearing_deg * b``
    degrees counter-clockwise from ``+x`` (docs/COMMANDER.md "Map points")."""
    per_ring = round(360 / bearing_deg)
    points = [(0.0, 0.0)]
    for radius in radii:
        for b in range(per_ring):
            angle = math.radians(bearing_deg * b)
            points.append((radius * math.cos(angle), radius * math.sin(angle)))
    return points


def design_facts(doc: str) -> dict[str, str]:
    """Constants of the agreed design, checked against the Python layout and the sim.

    Raises:
        CommanderFactsError: the doc, ``spacefight.commander.io`` and the sim disagree.
    """
    layout = {
        "ENTITY_DIM": io.ENTITY_DIM,
        "GLOBAL_DIM": io.GLOBAL_DIM,
        "ACTION_DIM": io.ACTION_DIM,
        "N_POINTS": io.N_POINTS,
        "HOLD_DECISIONS": io.HOLD_DECISIONS,
        "MAX_SHIPS": io.MAX_ENTITIES,
    }
    problems = [
        f"{name}: doc {_doc_int(doc, name)}, spacefight.commander.io {value}"
        for name, value in layout.items()
        if _doc_int(doc, name) != value
    ]
    learned_ticks = _doc_int(doc, "LEARNED_COMMAND_TICKS")
    scripted_ticks = _doc_int(doc, "COMMAND_TICKS")
    if scripted_ticks != int(rlf_sim.COMMAND_TICKS):
        problems.append(
            f"COMMAND_TICKS: doc {scripted_ticks}, sim {rlf_sim.COMMAND_TICKS}"
        )
    radii = _doc_radii(doc)
    bearing = _doc_bearing(doc)
    if len(map_points(radii, bearing)) != io.N_POINTS:
        problems.append(
            f"{len(radii)} rings of {360 // bearing} points and the centre is not "
            f"N_POINTS = {io.N_POINTS}"
        )
    shaping = _doc_float(doc, "SHAPING_WEIGHT")
    if shaping != TrainConfig().shaping:
        problems.append(
            f"SHAPING_WEIGHT: doc {shaping}, TrainConfig {TrainConfig().shaping}"
        )
    # The built sim states its own layout once the commander interface is in it.
    sim_io = getattr(rlf_sim, "commander_io", None)
    if sim_io is not None:
        constants = dict(sim_io())
        try:
            io.check_sim_layout(constants)
        except ValueError as e:
            problems.append(str(e))
        # commander_io() gives the learned cadence as ``command_ticks``.
        if "command_ticks" not in constants:
            problems.append("the sim's commander_io() has no 'command_ticks'")
        elif int(constants["command_ticks"]) != learned_ticks:
            problems.append(
                f"LEARNED_COMMAND_TICKS: doc {learned_ticks}, "
                f"sim commander_io() command_ticks {constants['command_ticks']}"
            )
    sim_ticks = getattr(rlf_sim, "LEARNED_COMMAND_TICKS", None)
    if sim_ticks is not None and int(sim_ticks) != learned_ticks:
        problems.append(
            f"LEARNED_COMMAND_TICKS: doc {learned_ticks}, sim module {sim_ticks}"
        )
    if problems:
        raise CommanderFactsError("commander layout: " + "; ".join(problems))
    if TICK_HZ % learned_ticks or scripted_ticks % TICK_HZ:
        raise CommanderFactsError(
            f"the page says whole seconds; cadences are {learned_ticks} and "
            f"{scripted_ticks} ticks at {TICK_HZ} Hz"
        )
    return {
        "sim.tick_hz": str(TICK_HZ),
        "cadence.ticks": str(learned_ticks),
        "cadence.per_s": str(TICK_HZ // learned_ticks),
        "cadence.scripted_ticks": str(scripted_ticks),
        "cadence.scripted_s": str(scripted_ticks // TICK_HZ),
        "points.radii": ", ".join(f"{r:g}" for r in radii),
        "points.bearing": str(bearing),
        "points.per_ring": str(360 // bearing),
        "points.rings": str(len(radii)),
        "goto.radius": str(_doc_int(doc, "GOTO_RADIUS")),
        "io.vel_scale": str(_doc_int(doc, "VEL_SCALE")),
    }


def io_facts() -> dict[str, str]:
    """The input and output layout the network is shaped by."""
    return {
        "io.version": str(io.COMMANDER_IO_VERSION),
        "io.entity_dim": str(io.ENTITY_DIM),
        "io.global_dim": str(io.GLOBAL_DIM),
        "io.action_dim": str(io.ACTION_DIM),
        "io.n_points": str(io.N_POINTS),
        "io.hold_decisions": str(io.HOLD_DECISIONS),
        # A change at decision n leaves decisions n+1 .. n+HOLD_DECISIONS-1 able only
        # to keep; the ship is free again at decision n+HOLD_DECISIONS.
        "io.hold_keep": str(io.HOLD_DECISIONS - 1),
        "io.max_entities": str(io.MAX_ENTITIES),
        "io.inputs": _n(io.MAX_ENTITIES * io.ENTITY_DIM + io.GLOBAL_DIM),
        "io.n_squads": str(io.N_SQUADS),
        "io.squad_global_dim": str(io.SQUAD_GLOBAL_DIM),
        "io.launch_hulls": str(io.N_LAUNCH_HULLS),
        "io.waypoint_choices": str(io.N_WAYPOINT_CHOICES),
        "io.squad_choices": str(io.N_SQUAD_CHOICES),
        "io.order_choices": str(io.N_ORDER_CHOICES),
    }


def _linears(module: nn.Module) -> list[int]:
    return [n_params(m) for m in module.modules() if isinstance(m, nn.Linear)]


def network_facts(n_pilots: int) -> dict[str, str]:
    """Layer widths and parameter counts of the actor, and of the critic for
    ``n_pilots`` pilots.

    Raises:
        CommanderFactsError: the actor's parts do not add up to the whole (a layer
            the page does not describe).
    """
    actor = CommanderActor()
    trunk = actor.trunk
    encode = _linears(trunk.encode)
    squad = _linears(actor.squad)
    attention = sum(n_params(m) for m in (trunk.q, trunk.k, trunk.v, trunk.o))
    parts = {
        "trunk.encode.l0": encode[0],
        "trunk.encode.l1": encode[1],
        "trunk.attention": attention,
        "trunk.summary": n_params(trunk.summary),
        "launch": n_params(actor.launch),
        "waypoint": n_params(actor.waypoint),
        "squad.l0": squad[0],
        "squad.l1": squad[1],
        "squad_embed": actor.squad_embed.numel(),
        "query": n_params(actor.query),
        "order": n_params(actor.order),
        "point": n_params(actor.point),
        "attack": n_params(actor.attack_q) + n_params(actor.attack_k),
        "defend": n_params(actor.defend_q) + n_params(actor.defend_k),
    }
    total = n_params(actor)
    if len(encode) != 2 or len(squad) != 2 or sum(parts.values()) != total:
        raise CommanderFactsError(
            f"the page's layer table adds up to {sum(parts.values())}, the actor has "
            f"{total} parameters"
        )
    critic = CommanderCritic(n_pilots)
    facts = {f"actor.{key}": _n(value) for key, value in parts.items()}
    facts |= {
        "actor.trunk.encode": _n(encode[0] + encode[1]),
        "actor.trunk.attention.each": _n(n_params(trunk.q)),
        "actor.trunk": _n(n_params(trunk)),
        "actor.squad": _n(squad[0] + squad[1]),
        "actor.summary_heads": _n(parts["launch"] + parts["waypoint"]),
        "actor.per_squad": _n(
            sum(
                parts[key]
                for key in (
                    "squad_embed",
                    "query",
                    "order",
                    "point",
                    "attack",
                    "defend",
                )
            )
        ),
        "actor.heads": _n(total - n_params(trunk)),
        "actor.params": _n(total),
        "actor.kb": str(round(total * 4 / 1000)),
        "net.width": str(WIDTH),
        "net.summary": str(SUMMARY),
        "net.attention_heads": str(HEADS),
        "net.head_width": str(WIDTH // HEADS),
        "net.squad_embed": str(SQUAD_EMBED),
        "net.summary_in": str(WIDTH + io.GLOBAL_DIM),
        "net.squad_in": str(WIDTH + SUMMARY),
        "net.query_in": str(SQUAD_EMBED + io.SQUAD_GLOBAL_DIM + SUMMARY),
        "net.pointer_scale": f"{math.sqrt(WIDTH):g}",
        "critic.n_pilots": str(n_pilots),
        "critic.pilot_onehot": str(n_pilots + 1),
        "critic.entity_in": str(critic.trunk.entity_dim),
        "critic.trunk.encode.l0": _n(_linears(critic.trunk.encode)[0]),
        "critic.trunk": _n(n_params(critic.trunk)),
        "critic.value": _n(n_params(critic.value)),
        "critic.params": _n(n_params(critic)),
    }
    return facts


def training_facts() -> dict[str, str]:
    """The PPO setup and the enemy-commander mix, from ``TrainConfig``'s defaults."""
    cfg = TrainConfig()
    names = {field.name for field in fields(TrainConfig)}
    for needed in ("gamma", "lam", "opponent_shares", "pfsp_floor", "snapshot_every"):
        if needed not in names:
            raise CommanderFactsError(f"TrainConfig has no {needed}")
    shares = dict(zip(OPP_NAMES, cfg.opponent_shares, strict=True))
    total = sum(shares.values())
    facts = {f"train.opp.{name}": _pct(share / total) for name, share in shares.items()}
    facts |= {
        "train.gamma": f"{cfg.gamma:g}",
        "train.horizon": str(round(1 / (1 - cfg.gamma))),
        "train.lambda": f"{cfg.lam:g}",
        "train.shaping": f"{cfg.shaping:g}",
        "train.decisions_per_update": _n(cfg.decisions_per_update),
        "train.epochs": str(cfg.epochs),
        "train.minibatch": str(cfg.minibatch),
        "train.clip": f"{cfg.clip:g}",
        "train.lr": f"{cfg.lr:g}",
        "train.ent_coef": f"{cfg.ent_coef:g}",
        "train.n_envs": str(cfg.n_envs),
        "train.snapshot_every": str(cfg.snapshot_every),
        "train.max_snapshots": str(cfg.max_snapshots),
        "train.pfsp_floor": f"{cfg.pfsp_floor:g}",
    }
    return facts


def live_pilot_count(path: Path = LIVE_PILOTS) -> int:
    """How many pilots the live list names (the critic's pilot one-hot has one more).

    Raises:
        CommanderFactsError: the file is not a non-empty live list.
    """
    data = json.loads(path.read_text())
    if data.get("schema") != "rlf.live_pilots/1" or not data.get("pilots"):
        raise CommanderFactsError(f"{path} is not a non-empty rlf.live_pilots/1 list")
    return len(data["pilots"])


def compute_facts(
    doc_path: Path = DESIGN_DOC, live_pilots: Path = LIVE_PILOTS
) -> dict[str, str]:
    """Every fact the page may state, as the exact text it should show."""
    n_pilots = live_pilot_count(live_pilots)
    facts: dict[str, str] = {"pilots.live": str(n_pilots)}
    for part in (
        design_facts(doc_path.read_text()),
        io_facts(),
        network_facts(n_pilots),
        training_facts(),
    ):
        overlap = facts.keys() & part.keys()
        if overlap:
            raise CommanderFactsError(f"fact keys defined twice: {sorted(overlap)}")
        facts.update(part)
    return facts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE)
    parser.add_argument(
        "--print", action="store_true", help="print every fact as JSON and exit"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    facts = compute_facts()
    if args.print:
        print(json.dumps(facts, indent=1))
        return 0
    page = args.page.read_text()
    mismatches = check_page(page, facts)
    if mismatches:
        print(
            f"{args.page}: {len(mismatches)} stale fact(s); update the page:",
            file=sys.stderr,
        )
        for mismatch in mismatches:
            print(f"  {mismatch}", file=sys.stderr)
        return 1
    print(f"commander page: {len(page_facts(page))} facts match the code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
