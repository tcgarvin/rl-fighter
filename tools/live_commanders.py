"""The commanders the live page draws from, side by side: ``lab/live_commanders.json``.

Each match, each side of the live page gets one commander drawn uniformly from this
stable. The scripted commander (the sim's own, id ``scripted``, no weights) is always
in it; a learned one (``spacefight.commander.policy.save_commander``) runs in the
browser in the sim's ``learned`` mode. Weights stay out of git, as the pilots' do:
``publish`` uploads each checkpoint to the public bucket under
``rl-fighter/commanders/<id>/<sha256>.pt`` and records its URL and hash, and ``export``
reads the training file if it is still there, else a sha256-checked download.

    python -m tools.live_commanders publish --entry 2026-11-08-commander-1 \\
        --commander c1_1200=lab/runs/2026-11-08-commander-1/checkpoints/commander_1200.pt
    python -m tools.live_commanders list
    python -m tools.live_commanders export --bundle web/public/bundle \\
        --wasm-io-json "$(node ... commanderIoJson())"

``publish`` rewrites the stable as the scripted commander plus the ones it is given
(``--keep`` also keeps the learned ones listed now). ``export`` writes
``<bundle>/commanders/<id>/`` (``tools/export_commander.py``) and
``<bundle>/commanders/index.json``, which ``tools/build_bundle.py`` copies into the
bundle manifest. Viewers read about each commander on the page, so one cannot go live
without a sentence in ``lab/live_commander_notes.json``, and a stable with a learned
commander cannot go live without the logbook entry that introduces it (``--entry``, a
directory under ``lab/runs`` holding ``results.md``).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from spacefight.commander.policy import load_commander
from tools.champion import (
    DEFAULT_CACHE,
    ChampionError,
    GcsStore,
    WeightStore,
    _download,
    sha256_of,
)
from tools.export_commander import export

SCHEMA: Final = "rlf.live_commanders/1"
INDEX_SCHEMA: Final = "rlf.live_commander_index/1"
KEY_PREFIX: Final = "rl-fighter/commanders"
SCRIPTED: Final = "scripted"
LEARNED: Final = "learned"
KINDS: Final = (SCRIPTED, LEARNED)
# The scripted commander plus a handful of learned ones; more would rarely all be seen.
MAX_LIVE_COMMANDERS: Final = 8
DEFAULT_REGISTRY: Final = Path("lab/live_commanders.json")
DEFAULT_NOTES: Final = Path("lab/live_commander_notes.json")
DEFAULT_RUNS: Final = Path("lab/runs")
_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class LiveCommandersError(ValueError):
    """A bad stable, registry or download."""


@dataclass(frozen=True)
class LiveCommander:
    """One commander in the live page's stable.

    Attributes:
        id: Short and phone-friendly; the page shows it ("c1_1200"). ``scripted`` is
            the sim's scripted commander.
        kind: ``scripted`` or ``learned``.
        note: One plain sentence or two about it, for viewers.
        checkpoint: The training file, relative to the repo root ("" when scripted).
        sha256: The checkpoint's hash ("" when scripted).
        url: Where the checkpoint can be downloaded ("" when scripted).
        update: Its training update (-1 when scripted or unrecorded).
    """

    id: str
    kind: str
    note: str
    checkpoint: str = ""
    sha256: str = ""
    url: str = ""
    update: int = -1

    def to_json(self) -> dict[str, Any]:
        if self.kind == SCRIPTED:
            return {"id": self.id, "kind": self.kind, "note": self.note}
        return {
            "id": self.id,
            "kind": self.kind,
            "note": self.note,
            "checkpoint": self.checkpoint,
            "sha256": self.sha256,
            "url": self.url,
            "update": self.update,
        }


def _check(commanders: Sequence[LiveCommander], entry: str, where: str) -> None:
    """The stable's rules (module docs), for both ``publish`` and ``load_registry``."""
    ids = [c.id for c in commanders]
    if len(set(ids)) != len(ids):
        raise LiveCommandersError(f"{where}: a commander is listed twice")
    if not 0 < len(commanders) <= MAX_LIVE_COMMANDERS:
        raise LiveCommandersError(
            f"{where}: {len(commanders)} commanders, not 1-{MAX_LIVE_COMMANDERS}"
        )
    if [c.id for c in commanders if c.kind == SCRIPTED] != [SCRIPTED]:
        raise LiveCommandersError(
            f"{where}: the scripted commander must be listed once, as {SCRIPTED!r}"
        )
    for c in commanders:
        if c.kind not in KINDS:
            raise LiveCommandersError(f"{where}: {c.id} has kind {c.kind!r}")
        if not _ID.match(c.id):
            raise LiveCommandersError(
                f"{where}: id {c.id!r} is not a short lower-case slug"
            )
        if not c.note.strip():
            raise LiveCommandersError(f"{where}: {c.id} has no note")
        if c.kind == LEARNED and (
            not c.checkpoint or not _SHA256.match(c.sha256) or not c.url
        ):
            raise LiveCommandersError(
                f"{where}: learned {c.id} needs a checkpoint, sha256 and url"
            )
    if any(c.kind == LEARNED for c in commanders) and not entry:
        raise LiveCommandersError(f"{where}: a learned commander needs a logbook entry")


def load_registry(registry: Path) -> tuple[list[LiveCommander], str]:
    """Read and check ``lab/live_commanders.json``: ``(commanders, entry)``.

    Raises:
        LiveCommandersError: Wrong schema, or a stable that breaks the rules.
    """
    data = json.loads(registry.read_text())
    if data.get("schema") != SCHEMA:
        raise LiveCommandersError(
            f"{registry}: schema {data.get('schema')!r}, not {SCHEMA}"
        )
    try:
        commanders = [LiveCommander(**c) for c in data["commanders"]]
    except (KeyError, TypeError) as err:
        raise LiveCommandersError(f"{registry}: bad commander record: {err}") from err
    entry = str(data.get("entry", ""))
    _check(commanders, entry, str(registry))
    return commanders, entry


def write_registry(
    registry: Path, commanders: Sequence[LiveCommander], entry: str
) -> None:
    """Check and write the stable.

    Raises:
        LiveCommandersError: The stable breaks the rules.
    """
    _check(commanders, entry, str(registry))
    data = {
        "schema": SCHEMA,
        "entry": entry,
        "commanders": [c.to_json() for c in commanders],
    }
    registry.write_text(json.dumps(data, indent=1) + "\n")


def parse_assignments(values: Sequence[str]) -> list[tuple[str, Path]]:
    """``id=checkpoint`` pairs from the command line.

    Raises:
        LiveCommandersError: A value without ``=``.
    """
    pairs = []
    for value in values:
        cid, sep, path = value.partition("=")
        if not sep or not cid or not path:
            raise LiveCommandersError(f"--commander {value!r} is not <id>=<checkpoint>")
        pairs.append((cid, Path(path)))
    return pairs


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def publish(
    registry: Path,
    entry: str,
    learned: Sequence[tuple[str, Path]],
    keep: bool = False,
    notes: Path = DEFAULT_NOTES,
    runs: Path = DEFAULT_RUNS,
    store: WeightStore | None = None,
) -> list[LiveCommander]:
    """Upload each learned commander's checkpoint and write the stable.

    Args:
        registry: The file to write (and, with ``keep``, to read first).
        entry: The logbook entry introducing these commanders: a directory under ``runs``.
        learned: ``(id, checkpoint)`` of each learned commander to list.
        keep: Also keep the learned commanders the registry lists now (a new one with
            the same id replaces the old).
        notes: Commander id -> the sentence viewers read about it (``scripted`` too).
        runs: The logbook's run directories.
        store: Where the weights go; the public bucket by default.

    Raises:
        LiveCommandersError: No such entry, a commander without a note, a checkpoint
            missing, or a stable that breaks the rules.
        ValueError: A checkpoint is not a commander of this io version.
        ChampionError: An upload fails.
    """
    if not (runs / entry / "results.md").is_file():
        raise LiveCommandersError(f"no logbook entry {runs / entry / 'results.md'}")
    written: dict[str, str] = json.loads(notes.read_text())
    ids = [SCRIPTED, *(cid for cid, _ in learned)]
    unwritten = [cid for cid in ids if not written.get(cid)]
    if unwritten:
        raise LiveCommandersError(f"{notes}: no note for {', '.join(unwritten)}")
    kept: list[LiveCommander] = []
    if keep and registry.is_file():
        new_ids = set(ids)
        kept = [
            c
            for c in load_registry(registry)[0]
            if c.kind == LEARNED and c.id not in new_ids
        ]
    # Every checkpoint loads before anything is uploaded.
    checked = []
    for cid, path in learned:
        if not path.is_file():
            raise LiveCommandersError(f"{cid}: {path} is missing")
        _, meta = load_commander(path)
        update = meta.get("update")
        checked.append((cid, path, int(update) if isinstance(update, int) else -1))
    weights = store if store is not None else GcsStore(key_prefix=KEY_PREFIX)
    commanders = [LiveCommander(SCRIPTED, SCRIPTED, written[SCRIPTED]), *kept]
    for cid, path, update in checked:
        sha = sha256_of(path)
        commanders.append(
            LiveCommander(
                cid,
                LEARNED,
                written[cid],
                _repo_relative(path),
                sha,
                weights.put(path, f"{KEY_PREFIX}/{cid}/{sha}.pt"),
                update,
            )
        )
    write_registry(registry, commanders, entry)
    return commanders


Downloader = Callable[[str, Path], None]


def fetch_checkpoint(
    commander: LiveCommander,
    cache_dir: Path = DEFAULT_CACHE,
    download: Downloader = _download,
) -> Path:
    """A local checkpoint with the learned commander's recorded hash.

    Raises:
        LiveCommandersError: The commander is scripted, or the download does not
            match its record.
    """
    if commander.kind != LEARNED:
        raise LiveCommandersError(f"{commander.id} has no weights")
    original = Path(commander.checkpoint)
    if original.is_file() and sha256_of(original) == commander.sha256:
        return original
    cached = cache_dir / f"{commander.sha256}.pt"
    if cached.is_file() and sha256_of(cached) == commander.sha256:
        return cached
    download(commander.url, cached)
    got = sha256_of(cached)
    if got != commander.sha256:
        cached.unlink()
        raise LiveCommandersError(
            f"{commander.url}: sha256 {got} != recorded {commander.sha256}"
        )
    return cached


def export_commanders(
    commanders: Sequence[LiveCommander],
    bundle: Path,
    wasm_io: Mapping[str, Any],
    entry: str,
    fetch: Callable[[LiveCommander], Path] = fetch_checkpoint,
) -> list[dict[str, Any]]:
    """Export each learned commander into the bundle and write
    ``commanders/index.json``.

    Raises:
        LiveCommandersError: A download fails to match its record.
        tools.export_commander.CommanderExportError: A commander does not run in this
            wasm build.
    """
    index = []
    for c in commanders:
        record: dict[str, Any] = {"id": c.id, "kind": c.kind, "note": c.note}
        if c.kind == LEARNED:
            directory = f"commanders/{c.id}"
            export(fetch(c), bundle / directory, wasm_io)
            record |= {"dir": directory, "update": c.update}
        index.append(record)
    path = bundle / "commanders" / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"schema": INDEX_SCHEMA, "entry": entry, "commanders": index}
    path.write_text(json.dumps(data, indent=1) + "\n")
    return index


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    send = commands.add_parser("publish", help="upload weights, write the stable")
    send.add_argument("--entry", required=True, help="logbook entry (lab/runs/<id>)")
    send.add_argument(
        "--commander",
        action="append",
        default=[],
        metavar="ID=CHECKPOINT",
        help="a learned commander to list (repeatable)",
    )
    send.add_argument(
        "--keep", action="store_true", help="keep the learned ones listed now"
    )
    send.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    send.add_argument("--notes", type=Path, default=DEFAULT_NOTES)

    show = commands.add_parser("list", help="print the stable")
    show.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)

    out = commands.add_parser("export", help="export the stable into a bundle")
    out.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    out.add_argument("--bundle", type=Path, required=True)
    out.add_argument(
        "--wasm-io-json", required=True, help="the wasm build's commanderIoJson()"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command; a bad stable or failed transfer ends it with a message."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "publish":
            commanders = publish(
                args.registry,
                args.entry,
                parse_assignments(args.commander),
                keep=args.keep,
                notes=args.notes,
            )
            print(f"{args.registry}: {', '.join(c.id for c in commanders)}")
            return 0
        if args.command == "list":
            commanders, entry = load_registry(args.registry)
            for c in commanders:
                where = f" {c.url}" if c.kind == LEARNED else ""
                print(f"{c.id} ({c.kind}){where}")
            print(f"entry: {entry or '(none)'}")
            return 0
        commanders, entry = load_registry(args.registry)
        index = export_commanders(
            commanders, args.bundle, json.loads(args.wasm_io_json), entry
        )
        print(f"{args.bundle}/commanders: {', '.join(c['id'] for c in index)}")
        return 0
    except (ValueError, ChampionError, FileNotFoundError) as err:
        # ValueError: a bad stable (LiveCommandersError), a commander the wasm cannot
        # run (CommanderExportError), bad JSON, or load_commander refusing a file.
        print(f"live_commanders: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
