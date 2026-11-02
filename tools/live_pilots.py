"""The pilots the live page flies, ship by ship: ``lab/live_pilots.json``.

The live page gives each strike craft one pilot at random from this list. The list holds
the highest-rated members of a population season who are not the script, at most
``MAX_LIVE_PILOTS`` of them. Weights stay out of git, as a champion's do: ``publish``
uploads each checkpoint to the public bucket and records its URL and hash, and ``export``
reads the training file if it is still there, else a sha256-checked download.

    python -m tools.live_pilots publish --season lab/population/2026-11-sim6
    python -m tools.live_pilots export --bundle web/public/bundle --wasm-sim-version 6 \\
        --wasm-obs-dim 583 --wasm-pilot-compat 3,4,5,6 \\
        --wasm-pilot-obs-dims '{"3": 385, "4": 385, "5": 403, "6": 583}'

``export`` writes ``<bundle>/pilots/<id>/`` (``tools/export_policy.py``) and
``<bundle>/pilots/index.json``, which ``tools/build_bundle.py`` copies into the bundle
manifest. A pilot with the champion's weights reuses ``<bundle>/policy/``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from spacefight.population.records import Member, Population, load_population
from tools.champion import (
    DEFAULT_CACHE,
    ChampionError,
    GcsStore,
    WeightStore,
    _download,
    sha256_of,
)
from tools.export_policy import ExportError, export

SCHEMA = "rlf.live_pilots/1"
INDEX_SCHEMA = "rlf.live_pilot_index/1"
MAX_LIVE_PILOTS = 10
KEY_PREFIX = "rl-fighter/pilots"
DEFAULT_REGISTRY = Path("lab/live_pilots.json")
CHAMPION_DIR = "policy"


class LivePilotsError(ValueError):
    """A bad selection, registry or download."""


@dataclass(frozen=True)
class LivePilot:
    """One pilot on the live page.

    Attributes:
        id: The population member's id.
        family: Its family.
        rating: Its combat rating in the phase the list was chosen from.
        checkpoint: The training file, relative to the repo root.
        sha256: The checkpoint's hash.
        url: Where the checkpoint can be downloaded.
    """

    id: str
    family: str
    rating: float
    checkpoint: str
    sha256: str
    url: str


def select_members(population: Population, limit: int) -> list[Member]:
    """The highest-rated members who are not the script, best first.

    Archived members count: a pilot retired from training can still fly on the page. A
    member with no rating has never played the round robin, so it is left out. Only
    ratings from the latest phase are compared, since points mean nothing across phases.

    Raises:
        LivePilotsError: ``limit`` is not positive, or no member qualifies.
    """
    if limit <= 0:
        raise LivePilotsError(f"limit must be positive, got {limit}")
    rated = [m for m in population.members.values() if m.ratings and not m.is_script]
    if not rated:
        raise LivePilotsError("no rated member who is not the script")
    phase = max((m.ratings[-1] for m in rated), key=lambda r: r.date).phase
    current = [m for m in rated if m.ratings[-1].phase == phase]
    current.sort(key=lambda m: (-m.ratings[-1].rating, m.id))
    return current[:limit]


def publish(
    season: Path,
    registry: Path,
    limit: int = MAX_LIVE_PILOTS,
    store: WeightStore | None = None,
) -> list[LivePilot]:
    """Upload the chosen members' checkpoints and write the registry.

    Raises:
        LivePilotsError: A checkpoint is missing or does not match its record.
        ChampionError: An upload fails.
    """
    weights = store if store is not None else GcsStore(key_prefix=KEY_PREFIX)
    pilots = []
    for member in select_members(load_population(season), limit):
        path = Path(member.checkpoint)
        if not path.is_file():
            raise LivePilotsError(f"{member.id}: {path} is missing")
        if sha256_of(path) != member.sha256:
            raise LivePilotsError(f"{member.id}: {path} does not match its record")
        key = f"{KEY_PREFIX}/{member.id}/{member.sha256}.pt"
        pilots.append(
            LivePilot(
                member.id,
                member.family,
                member.ratings[-1].rating,
                member.checkpoint,
                member.sha256,
                weights.put(path, key),
            )
        )
    data = {
        "schema": SCHEMA,
        "season": str(season),
        "pilots": [asdict(p) for p in pilots],
    }
    registry.write_text(json.dumps(data, indent=1) + "\n")
    return pilots


def load_registry(registry: Path) -> list[LivePilot]:
    """Read and check ``lab/live_pilots.json``.

    Raises:
        LivePilotsError: Wrong schema, no pilots, too many or duplicates.
    """
    data = json.loads(registry.read_text())
    if data.get("schema") != SCHEMA:
        raise LivePilotsError(
            f"{registry}: schema {data.get('schema')!r}, not {SCHEMA}"
        )
    pilots = [LivePilot(**p) for p in data["pilots"]]
    if not 0 < len(pilots) <= MAX_LIVE_PILOTS:
        raise LivePilotsError(
            f"{registry}: {len(pilots)} pilots, not 1-{MAX_LIVE_PILOTS}"
        )
    if len({p.id for p in pilots}) != len(pilots):
        raise LivePilotsError(f"{registry}: a pilot is listed twice")
    return pilots


def fetch_checkpoint(
    pilot: LivePilot, cache_dir: Path = DEFAULT_CACHE, download: Any = _download
) -> Path:
    """A local checkpoint with the pilot's recorded hash.

    Raises:
        LivePilotsError: The downloaded file does not match the record.
    """
    original = Path(pilot.checkpoint)
    if original.is_file() and sha256_of(original) == pilot.sha256:
        return original
    cached = cache_dir / f"{pilot.sha256}.pt"
    if cached.is_file() and sha256_of(cached) == pilot.sha256:
        return cached
    download(pilot.url, cached)
    got = sha256_of(cached)
    if got != pilot.sha256:
        cached.unlink()
        raise LivePilotsError(f"{pilot.url}: sha256 {got} != recorded {pilot.sha256}")
    return cached


def export_pilots(
    pilots: Sequence[LivePilot],
    bundle: Path,
    wasm_sim_version: int,
    wasm_obs_dim: int,
    wasm_pilot_compat: Sequence[int],
    wasm_pilot_obs_dims: dict[int, int],
) -> list[dict[str, Any]]:
    """Export each pilot into the bundle and write ``pilots/index.json``.

    Raises:
        LivePilotsError: A download fails to match its record.
        ExportError: A pilot does not fly in this wasm build.
    """
    champion = json.loads((bundle / CHAMPION_DIR / "manifest.json").read_text())
    champion_sha = champion["source"]["sha256"]
    index = []
    for pilot in pilots:
        if pilot.sha256 == champion_sha:
            directory, version = CHAMPION_DIR, int(champion["sim_version"])
        else:
            directory = f"pilots/{pilot.id}"
            manifest = export(
                fetch_checkpoint(pilot),
                bundle / directory,
                wasm_sim_version,
                wasm_obs_dim,
                wasm_pilot_compat=wasm_pilot_compat,
                wasm_pilot_obs_dims=wasm_pilot_obs_dims,
            )
            version = int(manifest["sim_version"])
        index.append(
            {
                "id": pilot.id,
                "family": pilot.family,
                "rating": round(pilot.rating, 1),
                "dir": directory,
                "sim_version": version,
            }
        )
    path = bundle / "pilots" / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema": INDEX_SCHEMA, "pilots": index}, indent=1) + "\n"
    )
    return index


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    send = commands.add_parser("publish", help="upload weights, write the registry")
    send.add_argument("--season", type=Path, required=True)
    send.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    send.add_argument("--limit", type=int, default=MAX_LIVE_PILOTS)

    out = commands.add_parser("export", help="export the registry's pilots to a bundle")
    out.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    out.add_argument("--bundle", type=Path, required=True)
    out.add_argument("--wasm-sim-version", type=int, required=True)
    out.add_argument("--wasm-obs-dim", type=int, required=True)
    out.add_argument("--wasm-pilot-compat", required=True, help="comma-separated")
    out.add_argument("--wasm-pilot-obs-dims", required=True, help="JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command; a bad registry or failed transfer ends it with a message."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "publish":
            pilots = publish(args.season, args.registry, args.limit)
            print(f"{args.registry}: {', '.join(p.id for p in pilots)}")
            return 0
        index = export_pilots(
            load_registry(args.registry),
            args.bundle,
            args.wasm_sim_version,
            args.wasm_obs_dim,
            [int(v) for v in args.wasm_pilot_compat.split(",")],
            {int(k): int(v) for k, v in json.loads(args.wasm_pilot_obs_dims).items()},
        )
        print(f"{args.bundle}/pilots: {', '.join(p['id'] for p in index)}")
        return 0
    except (LivePilotsError, ChampionError, ExportError, FileNotFoundError) as err:
        print(f"live_pilots: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
