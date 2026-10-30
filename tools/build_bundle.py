"""Write the live page's champion bundle files (``web/public/bundle/``).

``scripts/build_bundle.sh`` builds the sim wasm into ``<bundle>/pkg/`` and exports the
policy into ``<bundle>/policy/`` (``tools/export_policy.py``) first; this reads those
and the hull YAMLs and writes the remaining two files:

- ``catalogue.json``: ``{"hulls": [[name, yaml_text], ...], "weapons": yaml_text,
  "info": {name: {"role", "cost", "hp", "shield"}}}``. The first two are the
  ``WasmMatch`` constructor's input; ``info`` is what the muster cards show.
- ``manifest.json`` (``rlf.bundle/1``): the bundle id, sim version, the champion
  (id, name, notebook run, the hulls it is certified to fly, an eval summary), the
  match config it was trained on, and the roster rules the page drafts from.

The bundle id is a hash of the wasm, the weights, the catalogue and the manifest's
own settings, so rebuilding the same inputs keeps the id and the live page does not
swap for nothing.

    python -m tools.build_bundle --bundle web/public/bundle --run 2026-10-29-collision-damage
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "rlf.bundle/1"
POLICY_FORMAT = "rlf.web_policy/1"
# SIM_SPEC §2.1: at most 8 ships in a match.
MAX_SHIPS = 8
# Eval-summary keys copied into the manifest (export_policy.summarize_eval names).
_EVAL_KEYS = (
    "a",
    "b",
    "n",
    "sim_version",
    "wins",
    "draws",
    "losses",
    "win_rate",
    "hit_rate",
    "length_median_ticks",
)


class BundleError(ValueError):
    """The bundle directory or the options cannot make a valid bundle."""


@dataclass(frozen=True)
class RosterRules:
    """How the live page drafts each side (DESIGN §6 muster stub)."""

    hulls: tuple[str, ...]
    min_per_side: int
    max_per_side: int
    budget: int


def load_catalogue(assets: Path) -> dict[str, Any]:
    """Every ``assets/hulls/*/hull.yaml`` (sorted by name) plus ``weapons.yaml``.

    Raises:
        BundleError: A hull YAML lacks the fields the muster cards need.
    """
    hulls_dir = assets / "hulls"
    names = sorted(p.name for p in hulls_dir.iterdir() if (p / "hull.yaml").is_file())
    if not names:
        raise BundleError(f"no hull.yaml under {hulls_dir}")
    pairs: list[list[str]] = []
    info: dict[str, dict[str, Any]] = {}
    for name in names:
        text = (hulls_dir / name / "hull.yaml").read_text()
        spec = yaml.safe_load(text)
        try:
            shield = spec.get("shield")
            info[name] = {
                "role": str(spec["role"]),
                "cost": int(spec["cost"]),
                "hp": float(spec["hp"]),
                "shield": float(shield["hp"]) if shield else 0.0,
            }
        except (KeyError, TypeError) as exc:
            raise BundleError(f"{name}/hull.yaml: missing {exc}") from exc
        pairs.append([name, text])
    return {
        "hulls": pairs,
        "weapons": (assets / "weapons.yaml").read_text(),
        "info": info,
    }


def certified_hulls(
    policy: dict[str, Any], override: Sequence[str] | None
) -> list[str]:
    """The hulls the champion may fly: ``override``, else those it trained on."""
    if override:
        return sorted(set(override))
    fleets = policy.get("match_config", {}).get("fleets")
    if not fleets:
        raise BundleError("policy manifest has no match_config.fleets; pass --hulls")
    return sorted({hull for fleet in fleets for hull in fleet})


# Duels are dull to watch (user, 2026-10-30): drafts field at least two ships a side.
# ?fleets=duel still asks for one explicitly.
MIN_PER_SIDE = 2


def roster_rules(
    hulls: Sequence[str],
    info: dict[str, dict[str, Any]],
    min_per_side: int,
    max_per_side: int,
    budget: int | None,
) -> RosterRules:
    """Validate the roster options against the catalogue and the sim's ship cap.

    The default budget buys ``max_per_side`` of the cheapest certified hull, so the
    largest fighter-only draft is a full side.

    Raises:
        BundleError: An unknown hull, or sizes or a budget no draft can satisfy.
    """
    unknown = [h for h in hulls if h not in info]
    if unknown:
        raise BundleError(f"certified hulls not in the catalogue: {unknown}")
    if not 1 <= min_per_side <= max_per_side or 2 * max_per_side > MAX_SHIPS:
        raise BundleError(
            f"need 1 <= min_per_side ({min_per_side}) <= max_per_side "
            f"({max_per_side}) <= {MAX_SHIPS // 2}"
        )
    cheapest = min(info[h]["cost"] for h in hulls)
    spend = budget if budget is not None else cheapest * max_per_side
    if spend < cheapest * min_per_side:
        raise BundleError(
            f"budget {spend} cannot buy {min_per_side} of the cheapest hull ({cheapest})"
        )
    return RosterRules(tuple(hulls), min_per_side, max_per_side, spend)


def eval_summary(policy: dict[str, Any], repo: Path) -> dict[str, Any] | None:
    """The export's eval summary with the file path made repo-relative."""
    raw = policy.get("eval")
    if not raw:
        return None
    out = {k: raw.get(k) for k in _EVAL_KEYS}
    path = Path(str(raw.get("file", "")))
    try:
        out["file"] = str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        out["file"] = path.name
    return out


def bundle_id(bundle: Path, settings: dict[str, Any]) -> str:
    """Content hash of the wasm, the weights, the catalogue and the settings."""
    digest = hashlib.sha256()
    for rel in (
        "pkg/sim_wasm_bg.wasm",
        "pkg/sim_wasm.js",
        "policy/weights.bin",
        "catalogue.json",
    ):
        digest.update(rel.encode())
        digest.update((bundle / rel).read_bytes())
    digest.update(json.dumps(settings, sort_keys=True).encode())
    return digest.hexdigest()[:16]


def build(
    bundle: Path,
    run: str,
    assets: Path,
    repo: Path,
    champion_id: str | None = None,
    champion_name: str | None = None,
    hulls: Sequence[str] | None = None,
    min_per_side: int = MIN_PER_SIDE,
    max_per_side: int = 4,
    budget: int | None = None,
) -> dict[str, Any]:
    """Write ``catalogue.json`` and ``manifest.json`` into ``bundle``; return the manifest.

    Raises:
        BundleError: Missing or inconsistent pkg/policy files, or bad roster options.
    """
    for rel in (
        "pkg/sim_wasm_bg.wasm",
        "pkg/sim_wasm.js",
        "policy/manifest.json",
        "policy/weights.bin",
    ):
        if not (bundle / rel).is_file():
            raise BundleError(
                f"{bundle / rel} is missing; build the wasm and export the policy first"
            )
    policy = json.loads((bundle / "policy/manifest.json").read_text())
    if policy.get("format") != POLICY_FORMAT:
        raise BundleError(
            f"policy manifest format {policy.get('format')}, expected {POLICY_FORMAT}"
        )

    catalogue = load_catalogue(assets)
    (bundle / "catalogue.json").write_text(json.dumps(catalogue))
    certified = certified_hulls(policy, hulls)
    rules = roster_rules(
        certified, catalogue["info"], min_per_side, max_per_side, budget
    )

    source = policy.get("source", {})
    stem = Path(str(source.get("checkpoint", "policy"))).stem
    update = source.get("update")
    config = policy["match_config"]
    settings: dict[str, Any] = {
        "sim_version": policy["sim_version"],
        "champion": {
            "id": champion_id or f"{run}/{stem}",
            "name": champion_name
            or (
                f"v{policy['sim_version']} pilot · update {update}"
                if update is not None
                else stem
            ),
            "run": run,
            "hulls": list(rules.hulls),
            "update": update,
            "checkpoint_sha256": source.get("sha256"),
            "eval": eval_summary(policy, repo),
        },
        "match": {
            "arena_radius": float(config["arena_radius"]),
            "time_limit_ticks": int(config["time_limit_ticks"]),
            "reaction_ticks": int(config["reaction_ticks"]),
        },
        "roster": {
            "hulls": list(rules.hulls),
            "min_per_side": rules.min_per_side,
            "max_per_side": rules.max_per_side,
            "budget": rules.budget,
        },
    }
    manifest = {"schema": SCHEMA, "bundle_id": bundle_id(bundle, settings), **settings}
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--run", required=True, help="lab run id (the notebook entry)")
    parser.add_argument("--assets", type=Path, default=Path("assets"))
    parser.add_argument("--champion-id", default=None)
    parser.add_argument("--champion-name", default=None)
    parser.add_argument(
        "--hulls",
        default=None,
        help="comma-separated hulls the champion may fly (default: its training fleets)",
    )
    parser.add_argument("--min-per-side", type=int, default=MIN_PER_SIDE)
    parser.add_argument("--max-per-side", type=int, default=4)
    parser.add_argument("--budget", type=int, default=None)
    args = parser.parse_args(argv)
    try:
        manifest = build(
            args.bundle,
            args.run,
            args.assets,
            Path.cwd(),
            champion_id=args.champion_id,
            champion_name=args.champion_name,
            hulls=args.hulls.split(",") if args.hulls else None,
            min_per_side=args.min_per_side,
            max_per_side=args.max_per_side,
            budget=args.budget,
        )
    except (BundleError, FileNotFoundError, KeyError) as exc:
        print(f"build_bundle: {exc}", file=sys.stderr)
        return 1
    print(
        f"build_bundle: {args.bundle}/manifest.json bundle {manifest['bundle_id']}, "
        f"champion {manifest['champion']['id']} ({', '.join(manifest['champion']['hulls'])}), "
        f"roster {manifest['roster']['min_per_side']}-{manifest['roster']['max_per_side']} "
        f"a side, budget {manifest['roster']['budget']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
