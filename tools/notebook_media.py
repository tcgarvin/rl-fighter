"""Publish a notebook entry's films to the public bucket, like the pilots' weights.

A run's ``media/`` directory (before/after films from ``tools/web/film.mjs`` and their
posters) stays out of git. ``publish`` uploads each file under a content-addressed key,
``rl-fighter/notebook/<run-id>/<sha256><suffix>`` in ``gs://storage.tcgarvin.com``
(served at https://storage.tcgarvin.com), and writes ``lab/runs/<run-id>/media.json``
(schema ``rlf.notebook.media/1``), which is committed. ``tools/build_notebook.py``
reads that file, so the notebook page plays the films from the bucket.

    python -m tools.notebook_media publish --run 2026-11-10-picture-pass
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from tools.champion import ChampionError, GcsStore, sha256_of

MEDIA_SCHEMA = "rlf.notebook.media/1"
MEDIA_FILE = "media.json"
MEDIA_DIR = "media"
KEY_PREFIX = "rl-fighter/notebook"
RUNS_DIR = Path("lab/runs")
CONTENT_TYPES: Mapping[str, str] = {".mp4": "video/mp4", ".jpg": "image/jpeg"}


class MediaError(ValueError):
    """A media directory or manifest this tool cannot use, with the path in the message."""


class MediaStore(Protocol):
    """Somewhere to put files that is readable by URL afterwards."""

    def put(self, local: Path, key: str, content_type: str) -> str:
        """Upload ``local`` to ``key`` (a no-op if it is already there); return its URL."""
        ...


def media_key(run_id: str, sha256: str, suffix: str) -> str:
    """The bucket key of a run's file with this content."""
    return f"{KEY_PREFIX}/{run_id}/{sha256}{suffix}"


def publish(run_dir: Path, store: MediaStore) -> dict[str, Any]:
    """Upload every film and poster in ``run_dir/media`` and write its manifest.

    Returns the manifest written to ``run_dir/media.json``.

    Raises:
        MediaError: The run has no media directory, or it holds no film or poster.
    """
    media_dir = run_dir / MEDIA_DIR
    if not media_dir.is_dir():
        raise MediaError(f"{media_dir}: no media directory to publish")
    locals_ = sorted(
        p for p in media_dir.iterdir() if p.is_file() and p.suffix in CONTENT_TYPES
    )
    if not locals_:
        raise MediaError(
            f"{media_dir}: holds none of {', '.join(sorted(CONTENT_TYPES))}"
        )
    files = []
    for local in locals_:
        sha = sha256_of(local)
        key = media_key(run_dir.name, sha, local.suffix)
        url = store.put(local, key, CONTENT_TYPES[local.suffix])
        files.append(
            {
                "name": local.name,
                "sha256": sha,
                "bytes": local.stat().st_size,
                "key": key,
                "url": url,
            }
        )
    manifest = {"schema": MEDIA_SCHEMA, "files": files}
    (run_dir / MEDIA_FILE).write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def load_media(run_dir: Path) -> dict[str, str]:
    """A run's published media as ``{file name: URL}``; empty without a manifest.

    Raises:
        MediaError: The manifest is not ``rlf.notebook.media/1`` or an entry lacks a
            name or URL.
    """
    path = run_dir / MEDIA_FILE
    if not path.is_file():
        return {}
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict) or manifest.get("schema") != MEDIA_SCHEMA:
        raise MediaError(f"{path}: schema is not {MEDIA_SCHEMA}")
    media = {}
    for entry in manifest.get("files", []):
        name, url = entry.get("name"), entry.get("url")
        if not isinstance(name, str) or not isinstance(url, str):
            raise MediaError(f"{path}: every file needs a name and a url")
        media[name] = url
    return media


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    publish_parser = commands.add_parser(
        "publish", help="upload a run's media and write its media.json"
    )
    publish_parser.add_argument("--run", required=True, help="the run id")
    publish_parser.add_argument("--runs", type=Path, default=RUNS_DIR)
    args = parser.parse_args(argv)
    try:
        manifest = publish(args.runs / args.run, GcsStore(key_prefix=KEY_PREFIX))
    except (MediaError, ChampionError) as err:
        print(f"notebook_media: {err}", file=sys.stderr)
        return 1
    for entry in manifest["files"]:
        print(f"{entry['name']}: {entry['bytes']} bytes -> {entry['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
