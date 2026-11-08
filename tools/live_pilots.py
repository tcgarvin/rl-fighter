"""The pilots the live page flies, ship by ship: ``lab/live_pilots.json``.

The live page gives each strike craft one pilot at random from this list. The list holds
the highest-rated members of a population season who are not the script, at most
``MAX_LIVE_PILOTS`` of them. Weights stay out of git, as a champion's do: ``publish``
uploads each checkpoint to the public bucket and records its URL and hash, and ``export``
reads the training file if it is still there, else a sha256-checked download.

    python -m tools.live_pilots publish --season lab/population/2026-11-sim6 \\
        --entry 2026-11-02-ten-pilots [--war lab/population/2026-11-sim6/war/x/war.json]
    python -m tools.live_pilots export --bundle web/public/bundle --wasm-sim-version 6 \\
        --wasm-obs-dim 583 --wasm-pilot-compat 3,4,5,6 \\
        --wasm-pilot-obs-dims '{"3": 385, "4": 385, "5": 403, "6": 583}'

``export`` writes ``<bundle>/pilots/<id>/`` (``tools/export_policy.py``) and
``<bundle>/pilots/index.json``, which ``tools/build_bundle.py`` copies into the bundle
manifest. A pilot with the champion's weights reuses ``<bundle>/policy/``.

Viewers read about each pilot on the page, so a pilot cannot go live without a sentence in
``lab/live_pilot_notes.json``, and a list cannot go live without the logbook entry that
introduces it (``--entry``, a directory under ``lab/runs``).

``--war`` picks by wins above replacement (``spacefight.population.war``) instead of the
combat rating: the highest-WAR members of that measurement who are not the script. Each
pilot's ``rating`` is then its WAR per 100 matches, and the registry says
``"rated_by": "war"``.
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
from spacefight.population.war import read_war
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
MATCHUPS_SCHEMA = "rlf.notebook.matchups/1"
MATCHUP_MODES = ("overall", "deathmatch", "carrier_battle", "convoy_escort")
MAX_LIVE_PILOTS = 10
KEY_PREFIX = "rl-fighter/pilots"
DEFAULT_REGISTRY = Path("lab/live_pilots.json")
DEFAULT_NOTES = Path("lab/live_pilot_notes.json")
DEFAULT_RUNS = Path("lab/runs")
CHAMPION_DIR = "policy"
# The drill results a viewer can read: did it go there, did it switch when the order did.
FOLLOW_SCORES = {
    "goto_arrival": "go_to",
    "attack_flip": "attack",
    "defend_flip": "defend",
}


class LivePilotsError(ValueError):
    """A bad selection, registry or download."""


@dataclass(frozen=True)
class LivePilot:
    """One pilot on the live page.

    Attributes:
        id: The population member's id.
        family: Its family.
        rating: Its combat rating in the phase the list was chosen from, or its WAR
            per 100 matches when the list was chosen by WAR.
        checkpoint: The training file, relative to the repo root.
        sha256: The checkpoint's hash.
        url: Where the checkpoint can be downloaded.
        note: One plain sentence or two about it, for viewers.
        follows: Its latest order drill scores, 0 to 1; empty if it never drilled.
    """

    id: str
    family: str
    rating: float
    checkpoint: str
    sha256: str
    url: str
    note: str
    follows: dict[str, float]


def follow_scores(member: Member) -> dict[str, float]:
    """The member's latest drill scores a viewer reads; empty if it never drilled."""
    if not member.drills:
        return {}
    scores = member.drills[-1].scores
    return {name: round(scores[key], 2) for key, name in FOLLOW_SCORES.items()}


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


def select_members_by_war(
    population: Population, war: Path, limit: int
) -> list[tuple[Member, float]]:
    """The highest-WAR members of a WAR measurement who are not the script, best first,
    with their WAR per 100 matches.

    Archived members count, as with ratings.

    Raises:
        LivePilotsError: ``limit`` is not positive, a measured pilot is not a member of
            the season, or nobody but the script was measured.
    """
    if limit <= 0:
        raise LivePilotsError(f"limit must be positive, got {limit}")
    fit = read_war(war).fit
    measured = [p for p in fit.pilots if not p.is_script]
    unknown = [p.pilot for p in measured if p.pilot not in population.members]
    if unknown:
        raise LivePilotsError(f"{war}: not members of the season: {', '.join(unknown)}")
    if not measured:
        raise LivePilotsError(f"{war}: nobody but the script was measured")
    measured.sort(key=lambda p: (-p.war, p.pilot))
    return [(population.members[p.pilot], p.war) for p in measured[:limit]]


def publish(
    season: Path,
    registry: Path,
    entry: str,
    notes: Path = DEFAULT_NOTES,
    runs: Path = DEFAULT_RUNS,
    limit: int = MAX_LIVE_PILOTS,
    store: WeightStore | None = None,
    war: Path | None = None,
) -> list[LivePilot]:
    """Upload the chosen members' checkpoints and write the registry.

    Args:
        season: The population season to choose from.
        registry: The file to write.
        entry: The logbook entry introducing this list: a directory under ``runs``.
        notes: Pilot id -> the sentence viewers read about it.
        runs: The logbook's run directories.
        limit: At most this many pilots.
        store: Where the weights go; the public bucket by default.
        war: A WAR measurement to choose by (``select_members_by_war``) instead of
            the combat rating; omitted, the rating chooses.

    Raises:
        LivePilotsError: The entry does not exist, a pilot has no note, or a checkpoint
            is missing or does not match its record.
        ChampionError: An upload fails.
    """
    if not (runs / entry / "results.md").is_file():
        raise LivePilotsError(f"no logbook entry {runs / entry / 'results.md'}")
    weights = store if store is not None else GcsStore(key_prefix=KEY_PREFIX)
    written = json.loads(notes.read_text())
    population = load_population(season)
    if war is not None:
        chosen = select_members_by_war(population, war, limit)
    else:
        chosen = [(m, m.ratings[-1].rating) for m in select_members(population, limit)]
    members = [m for m, _ in chosen]
    unwritten = [m.id for m in members if not written.get(m.id)]
    if unwritten:
        raise LivePilotsError(f"{notes}: no note for {', '.join(unwritten)}")
    pilots = []
    for member, score in chosen:
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
                score,
                member.checkpoint,
                member.sha256,
                weights.put(path, key),
                written[member.id],
                follow_scores(member),
            )
        )
    data: dict[str, Any] = {
        "schema": SCHEMA,
        "season": str(season),
        "entry": entry,
        "pilots": [asdict(p) for p in pilots],
    }
    if war is not None:
        data |= {"rated_by": "war", "war": str(war)}
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


def registry_entry(registry: Path) -> str:
    """The logbook entry that introduces the list in ``registry``."""
    load_registry(registry)
    return str(json.loads(registry.read_text())["entry"])


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
    entry: str,
) -> list[dict[str, Any]]:
    """Export each pilot into the bundle and write ``pilots/index.json``.

    ``entry`` is the logbook entry that introduces the list, for the page to link to.

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
                "note": pilot.note,
                "follows": pilot.follows,
            }
        )
    path = bundle / "pilots" / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema": INDEX_SCHEMA, "entry": entry, "pilots": index}, indent=1)
        + "\n"
    )
    return index


def matchups(pilots: Sequence[LivePilot], results: Path, out: Path) -> dict[str, Any]:
    """Write the logbook's who-beats-whom grid for ``pilots``, in rating order.

    Args:
        pilots: The pilots, best first.
        results: A round robin's directory, holding ``summary.json`` and ``config.json``.
        out: The ``matchups.json`` to write.

    Returns:
        ``modes[mode][i][j]``, how often pilot ``i`` beat pilot ``j`` (null on the
        diagonal), and ``script[mode][i]``, how often pilot ``i`` beat the script.

    Raises:
        LivePilotsError: The round robin did not play one of the pilots.
    """
    summary = json.loads((results / "summary.json").read_text())
    config = json.loads((results / "config.json").read_text())
    ids = [p.id for p in pilots]
    unplayed = [i for i in ids if i not in summary["members"]]
    if unplayed:
        raise LivePilotsError(f"{results}: never played {', '.join(unplayed)}")
    grid = summary["win_matrix"]
    data = {
        "schema": MATCHUPS_SCHEMA,
        "source": results.as_posix(),
        "n_per_mission": config["n_per_mission"],
        "pilots": [{"id": p.id, "rating": round(p.rating)} for p in pilots],
        "modes": {
            mode: [
                [None if a == b else round(grid[mode][a][b], 3) for b in ids]
                for a in ids
            ]
            for mode in MATCHUP_MODES
        },
        "script": {
            mode: [round(grid[mode][a]["script"], 3) for a in ids]
            for mode in MATCHUP_MODES
        },
    }
    out.write_text(json.dumps(data, indent=1) + "\n")
    return data


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    send = commands.add_parser("publish", help="upload weights, write the registry")
    send.add_argument("--season", type=Path, required=True)
    send.add_argument("--entry", required=True, help="logbook entry (lab/runs/<id>)")
    send.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    send.add_argument("--limit", type=int, default=MAX_LIVE_PILOTS)
    send.add_argument(
        "--war", type=Path, help="choose by this WAR JSON instead of the rating"
    )

    grid = commands.add_parser("matchups", help="write the logbook's who-beats-whom")
    grid.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    grid.add_argument("--results", type=Path, required=True, help="a round robin's dir")
    grid.add_argument("--out", type=Path, required=True)

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
            pilots = publish(
                args.season, args.registry, args.entry, limit=args.limit, war=args.war
            )
            print(f"{args.registry}: {', '.join(p.id for p in pilots)}")
            return 0
        if args.command == "matchups":
            matchups(load_registry(args.registry), args.results, args.out)
            print(f"wrote {args.out}")
            return 0
        index = export_pilots(
            load_registry(args.registry),
            args.bundle,
            args.wasm_sim_version,
            args.wasm_obs_dim,
            [int(v) for v in args.wasm_pilot_compat.split(",")],
            {int(k): int(v) for k, v in json.loads(args.wasm_pilot_obs_dims).items()},
            registry_entry(args.registry),
        )
        print(f"{args.bundle}/pilots: {', '.join(p['id'] for p in index)}")
        return 0
    except (LivePilotsError, ChampionError, ExportError, FileNotFoundError) as err:
        print(f"live_pilots: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
