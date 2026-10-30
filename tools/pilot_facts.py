"""Facts the ``/pilot/`` page states, computed from the code, and a check of the page.

The page (``web/pilot/index.html``) is static prose. Every number in it that can
drift (obs layout, layer sizes, parameter counts, head counts per hull, the
reaction delay, which champion it describes) is written inside an element with a
``data-fact="<key>"`` attribute. This module computes the same facts from their
sources and ``check_page`` lists every element whose text disagrees:

- the obs layout from the Rust sim (``rlf_sim.OBS_LAYOUT`` / ``OBS_SLOTS``);
- the actor and critic from ``spacefight.rl.spike_policy`` (instantiated, so the
  parameter counts are counted, not typed in);
- the actuators per hull from ``assets/hulls/*/hull.yaml``;
- the champion from ``lab/champions`` and its run's ``config.yaml``;
- optionally the exported champion policy (``web/public/bundle/policy/manifest.json``),
  whose layer shapes come from the champion's real weights.

``scripts/build_pages_data.sh`` runs the check, so the site build fails when the page
goes stale (for instance after a new champion is promoted):

    python -m tools.pilot_facts --page web/pilot/index.html \\
        [--policy-manifest web/public/bundle/policy/manifest.json]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch.nn as nn
import yaml  # type: ignore[import-untyped]

import rlf_sim
from spacefight.rl.spike_policy import (
    ACTION_WIDTH,
    CONTEXT_DIM,
    HEAD_CHOICES,
    HEAD_GROUPS,
    HIDDEN,
    N_LOGITS,
    OBS_DIM,
    FleetCritic,
    SpikeActor,
    param_count,
)
from spacefight.env.rosters import MAX_FLEET_SHIPS, MAX_PER_SIDE
from tools.champion import CHAMPIONS_DIR, Champion, find_champion

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGE = REPO_ROOT / "web/pilot/index.html"
TICK_HZ = 30
_FACT_RE = re.compile(r'data-fact="([^"]+)"[^>]*>([^<]*)<')
_UPDATE_RE = re.compile(r"_(\d+)\.pt$")


class PilotFactsError(ValueError):
    """A source the facts come from is missing or disagrees with another source."""


@dataclass(frozen=True)
class Mismatch:
    """One page element whose text is not the computed fact."""

    key: str
    page: str
    expected: str

    def __str__(self) -> str:
        return f"{self.key}: page says {self.page!r}, the code says {self.expected!r}"


def _n(value: int) -> str:
    """Thousands with commas, as the page writes them."""
    return f"{value:,}"


def _linear_params(module: nn.Module) -> list[int]:
    return [param_count(m) for m in module.modules() if isinstance(m, nn.Linear)]


def _activations(module: nn.Sequential) -> set[str]:
    return {
        type(m).__name__.lower()
        for m in module
        if not isinstance(m, nn.Linear) and isinstance(m, nn.Module)
    }


def obs_facts() -> dict[str, str]:
    """Width, offset and record count of every obs block, from the Rust sim."""
    if rlf_sim.OBS_DIM != OBS_DIM:
        raise PilotFactsError(
            f"rlf_sim.OBS_DIM {rlf_sim.OBS_DIM} != spike_policy.OBS_DIM {OBS_DIM}"
        )
    facts = {
        "obs.dim": str(rlf_sim.OBS_DIM),
        "sim.version": str(rlf_sim.SIM_VERSION),
        "sim.max_ships": str(rlf_sim.MAX_SHIPS),
        "sim.max_others": str(rlf_sim.MAX_SHIPS - 1),
        "sim.near_ships": str(rlf_sim.N_NEAR_SHIPS),
        # Strike-craft fleets (training rosters, live drafts): two full sides.
        "fleet.max_ships": str(MAX_FLEET_SHIPS),
        "fleet.max_per_side": str(MAX_PER_SIDE),
        "sim.max_reaction_ticks": str(rlf_sim.MAX_REACTION_TICKS),
        "sim.tick_hz": str(TICK_HZ),
    }
    slots = dict(rlf_sim.OBS_SLOTS)
    for name, (offset, width) in dict(rlf_sim.OBS_LAYOUT).items():
        records = slots[name]
        facts[f"obs.{name}.offset"] = str(offset)
        facts[f"obs.{name}.width"] = str(width)
        facts[f"obs.{name}.records"] = str(records)
        facts[f"obs.{name}.record_width"] = str(width // records)
    return facts


def network_facts() -> dict[str, str]:
    """Layer sizes and parameter counts of the actor and the fleet critic."""
    actor = SpikeActor(HIDDEN)
    layers = _linear_params(actor.net)
    activation = _activations(actor.net)
    if len(layers) != 3 or len(activation) != 1:
        raise PilotFactsError(
            f"the page describes a 3-layer MLP with one activation; the actor has "
            f"{len(layers)} linear layers and activations {sorted(activation)}"
        )
    weights_only = sum(m.weight.numel() for m in actor.net if isinstance(m, nn.Linear))
    critic = FleetCritic(HIDDEN, CONTEXT_DIM)
    total = param_count(actor)
    heads = sum(HEAD_GROUPS[g].stop - HEAD_GROUPS[g].start for g in HEAD_GROUPS)
    facts = {
        "actor.in": str(OBS_DIM),
        "actor.hidden": str(HIDDEN),
        "actor.logits": str(N_LOGITS),
        "actor.heads": str(heads),
        "actor.activation": activation.pop(),
        "actor.l0.params": _n(layers[0]),
        "actor.l1.params": _n(layers[1]),
        "actor.l2.params": _n(layers[2]),
        "actor.params": _n(total),
        "actor.params_k": str(round(total / 1000)),
        "actor.kb": str(round(total * 4 / 1000)),
        # A full fleet, every tick: multiply-adds per second in the browser, millions.
        "browser.mmacs": str(round(weights_only * MAX_FLEET_SHIPS * TICK_HZ / 1e6)),
        "critic.context": str(CONTEXT_DIM),
        "critic.mix_hidden": str(HIDDEN // 2),
        "critic.mix_in": str(HIDDEN + 2 * CONTEXT_DIM + 2),
        "critic.base.params": _n(param_count(critic.base)),
        "critic.encoder.params": _n(param_count(critic.encoder)),
        "critic.mix.params": _n(param_count(critic.mix)),
        "critic.params": _n(param_count(critic)),
        "action.width": str(ACTION_WIDTH),
    }
    if heads != ACTION_WIDTH:
        raise PilotFactsError(f"{heads} heads but ACTION_WIDTH {ACTION_WIDTH}")
    for group, cols in HEAD_GROUPS.items():
        facts[f"heads.{group}.count"] = str(cols.stop - cols.start)
        facts[f"heads.{group}.choices"] = str(HEAD_CHOICES[group])
    return facts


def hull_facts(assets: Path) -> dict[str, str]:
    """Actuators and unmasked action heads per hull, from the hull YAMLs.

    A throttle head is live per thruster, a fire head per turret, a slew head per
    turret that can turn (``arc_deg`` > 0), and the power head always (SIM_SPEC §7.1,
    ``HeadMasks.head_valid``).
    """
    facts: dict[str, str] = {}
    paths = sorted(assets.glob("hulls/*/hull.yaml"))
    if not paths:
        raise PilotFactsError(f"no hull YAMLs under {assets}/hulls")
    for path in paths:
        data = yaml.safe_load(path.read_text())
        name = str(data["name"])
        thrusters = len(data["thrusters"])
        turrets = data["turrets"]
        slewing = sum(1 for t in turrets if float(t["arc_deg"]) > 0)
        live = thrusters + slewing + len(turrets) + 1
        facts[f"hull.{name}.thrusters"] = str(thrusters)
        facts[f"hull.{name}.turrets"] = str(len(turrets))
        facts[f"hull.{name}.slewing"] = str(slewing)
        facts[f"hull.{name}.heads"] = str(live)
        facts[f"hull.{name}.masked"] = str(ACTION_WIDTH - live)
    return facts


def _run_config(champion: Champion, repo: Path) -> dict[str, Any]:
    """The PPO config the champion's checkpoint was trained with (committed)."""
    config_path = repo / Path(champion.checkpoint).parent.parent / "config.yaml"
    if not config_path.is_file():
        raise PilotFactsError(f"{champion.id}: no run config at {config_path}")
    config: dict[str, Any] = yaml.safe_load(config_path.read_text())
    return config


def champion_facts(repo: Path, champions_dir: Path) -> dict[str, str]:
    """Which champion the page describes, and how its PPO stage was set up."""
    champion = find_champion("current", champions_dir)
    config = _run_config(champion, repo)
    update = _UPDATE_RE.search(champion.checkpoint)
    if update is None:
        raise PilotFactsError(
            f"{champion.id}: no update number in checkpoint {champion.checkpoint}"
        )
    reaction = int(config["reaction_ticks"])
    duel = champion.eval
    return {
        "champion.id": champion.id,
        "champion.name": champion.name,
        "champion.run": champion.run,
        "champion.update": update.group(1),
        "champion.hulls": ", ".join(champion.hulls),
        "champion.sim_version": str(champion.sim_version),
        "champion.duel_wins": f"{duel['wins']} of {duel['n']}",
        "train.critic": str(config["critic"]),
        "train.rosters": str(config["rosters"]),
        "train.n_envs": str(config["n_envs"]),
        "train.n_steps": str(config["n_steps"]),
        "train.n_updates": str(config["n_updates"]),
        "reaction.ticks": str(reaction),
        "reaction.ms": str(round(reaction * 1000 / TICK_HZ)),
    }


def check_manifest(manifest: Mapping[str, Any], facts: Mapping[str, str]) -> None:
    """Check the exported champion policy against the facts.

    The manifest's layer shapes come from the champion's real weights, so this is
    where "the code says" becomes "the champion is".

    Raises:
        PilotFactsError: any shape, count, activation or champion sha disagrees.
    """
    problems = []
    actor_params = int(facts["actor.params"].replace(",", ""))
    expected = {
        "obs_dim": int(facts["actor.in"]),
        "n_logits": int(facts["actor.logits"]),
        "action_width": int(facts["actor.heads"]),
        "hidden": [int(facts["actor.hidden"])] * 2,
        "weights_floats": actor_params,
    }
    for key, want in expected.items():
        if manifest.get(key) != want:
            problems.append(f"{key} is {manifest.get(key)!r}, expected {want!r}")
    activations = [layer["activation"] for layer in manifest.get("layers", [])]
    want_act = [facts["actor.activation"]] * 2 + ["none"]
    if activations != want_act:
        problems.append(f"activations {activations}, expected {want_act}")
    reaction = manifest.get("match_config", {}).get("reaction_ticks")
    if reaction != int(facts["reaction.ticks"]):
        problems.append(
            f"reaction_ticks {reaction}, expected {facts['reaction.ticks']}"
        )
    if problems:
        raise PilotFactsError("policy manifest: " + "; ".join(problems))


def check_manifest_champion(manifest: Mapping[str, Any], champion: Champion) -> None:
    """The exported policy must be the champion's checkpoint (by sha256).

    Raises:
        PilotFactsError: it was exported from some other checkpoint.
    """
    sha = manifest.get("source", {}).get("sha256")
    if sha != champion.weights.sha256:
        raise PilotFactsError(
            f"policy manifest was exported from {sha}, not champion {champion.id} "
            f"({champion.weights.sha256})"
        )


def compute_facts(
    repo: Path = REPO_ROOT, champions_dir: Path = CHAMPIONS_DIR
) -> dict[str, str]:
    """Every fact the page may state, as the exact text it should show."""
    facts: dict[str, str] = {}
    for part in (
        obs_facts(),
        network_facts(),
        hull_facts(repo / "assets"),
        champion_facts(repo, champions_dir),
    ):
        overlap = facts.keys() & part.keys()
        if overlap:
            raise PilotFactsError(f"fact keys defined twice: {sorted(overlap)}")
        facts.update(part)
    return facts


def page_facts(page_html: str) -> list[tuple[str, str]]:
    """``(key, text)`` of every ``data-fact`` element, in page order."""
    return [
        (key, html.unescape(text).strip()) for key, text in _FACT_RE.findall(page_html)
    ]


def check_page(page_html: str, facts: Mapping[str, str]) -> list[Mismatch]:
    """Every ``data-fact`` element whose text is not the computed fact.

    Raises:
        PilotFactsError: the page names a key no source computes, or has no facts.
    """
    found = page_facts(page_html)
    if not found:
        raise PilotFactsError("the page has no data-fact elements")
    unknown = sorted({key for key, _ in found if key not in facts})
    if unknown:
        raise PilotFactsError(f"the page uses unknown fact keys: {unknown}")
    return [
        Mismatch(key, text, facts[key]) for key, text in found if text != facts[key]
    ]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE)
    parser.add_argument(
        "--policy-manifest",
        type=Path,
        help="the exported champion policy to check the layer shapes against",
    )
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
    if args.policy_manifest is not None:
        manifest = json.loads(args.policy_manifest.read_text())
        check_manifest(manifest, facts)
        check_manifest_champion(manifest, find_champion("current"))
    mismatches = check_page(args.page.read_text(), facts)
    if mismatches:
        print(
            f"{args.page}: {len(mismatches)} stale fact(s); update the page:",
            file=sys.stderr,
        )
        for mismatch in mismatches:
            print(f"  {mismatch}", file=sys.stderr)
        return 1
    checked = len(page_facts(args.page.read_text()))
    against = f" and {args.policy_manifest}" if args.policy_manifest is not None else ""
    print(f"pilot page: {checked} facts match the code{against}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
