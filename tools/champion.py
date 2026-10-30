"""The champion registry: promoted pilots in ``lab/champions/<id>/champion.json``.

The registry is committed; the weights are not. ``promote`` uploads a checkpoint to the
weight store under a content-addressed key (``rl-fighter/champions/<id>/<sha256>.pt``,
so an uploaded file never changes and caches can keep it forever) and writes the
``rlf.champion/1`` record. ``fetch`` resolves a champion to a local checkpoint: the
original training file if it is still on disk with the recorded hash, else a download
from the record's public URL into the local cache, checked against the same hash.

The current champion is the latest promotion (ties broken by id), the same rule
``tools/build_notebook.py`` uses for "watch this pilot".

    python -m tools.champion promote --id 2026-10-29-v3-fighter --name "v3 pilot" \\
        --run 2026-10-29-collision-damage \\
        --checkpoint lab/runs/2026-10-29-collision-damage/arm_a_rl/checkpoints/ppo_bc_600.pt \\
        --hulls fighter --eval-json lab/runs/2026-10-29-collision-damage/eval/a_600_vs_script.json
    python -m tools.champion fetch [<id>]   # prints the local checkpoint path
    python -m tools.champion env [<id>]     # shell assignments for scripts/build_site.sh
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from tools.export_policy import ExportError, summarize_eval

SCHEMA = "rlf.champion/1"
CHAMPIONS_DIR = Path("lab/champions")
RUNS_DIR = Path("lab/runs")
DEFAULT_CACHE = Path.home() / ".cache" / "rl-fighter" / "weights"

# The public bucket behind https://storage.tcgarvin.com (project tcgarvin-com, fronted
# by a proxied Cloudflare CNAME). Everything this tool writes lives under KEY_PREFIX;
# the bucket holds unrelated files too.
GCS_BUCKET = "storage.tcgarvin.com"
GCS_CONFIGURATION = "tcgarvin-com"
PUBLIC_BASE_URL = "https://storage.tcgarvin.com"
KEY_PREFIX = "rl-fighter/champions"
IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"

_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ChampionError(ValueError):
    """A champion record is missing, malformed, or does not match its weights."""


@dataclass(frozen=True)
class Weights:
    """Where a champion's checkpoint lives and how to recognise it."""

    sha256: str
    bytes: int
    url: str
    key: str


@dataclass(frozen=True)
class Champion:
    """One ``rlf.champion/1`` record."""

    id: str
    name: str
    run: str
    checkpoint: str
    sim_version: int
    hulls: tuple[str, ...]
    promoted: str
    parent: str
    eval_json: str
    eval: dict[str, Any]
    weights: Weights

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "id": self.id,
            "name": self.name,
            "run": self.run,
            "checkpoint": self.checkpoint,
            "sim_version": self.sim_version,
            "hulls": list(self.hulls),
            "promoted": self.promoted,
            "parent": self.parent,
            "eval_json": self.eval_json,
            "eval": self.eval,
            "weights": {
                "sha256": self.weights.sha256,
                "bytes": self.weights.bytes,
                "url": self.weights.url,
                "key": self.weights.key,
            },
        }


class WeightStore(Protocol):
    """Somewhere to put checkpoints that is readable by URL afterwards."""

    def put(self, local: Path, key: str) -> str:
        """Upload ``local`` to ``key`` (a no-op if it is already there); return its URL."""
        ...


class GcsStore:
    """``gs://storage.tcgarvin.com`` via gcloud, as the agent's tcgarvin-com config."""

    def __init__(
        self,
        bucket: str = GCS_BUCKET,
        configuration: str = GCS_CONFIGURATION,
        base_url: str = PUBLIC_BASE_URL,
    ) -> None:
        self.bucket = bucket
        self.configuration = configuration
        self.base_url = base_url.rstrip("/")

    def put(self, local: Path, key: str) -> str:
        if not key.startswith(f"{KEY_PREFIX}/"):
            raise ChampionError(f"refusing to write outside {KEY_PREFIX}/: {key}")
        cmd = [
            "gcloud",
            f"--configuration={self.configuration}",
            "storage",
            "cp",
            "--no-clobber",
            f"--cache-control={IMMUTABLE_CACHE_CONTROL}",
            "--content-type=application/octet-stream",
            str(local),
            f"gs://{self.bucket}/{key}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ChampionError(
                f"upload to gs://{self.bucket}/{key} failed:\n{result.stderr}"
            )
        return f"{self.base_url}/{key}"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def weights_key(champion_id: str, sha256: str) -> str:
    return f"{KEY_PREFIX}/{champion_id}/{sha256}.pt"


# ---------------------------------------------------------------------------
# Reading the registry
# ---------------------------------------------------------------------------


def _require(data: dict[str, Any], field: str, kind: type, path: Path) -> Any:
    if field not in data:
        raise ChampionError(f"{path}: missing '{field}'")
    value = data[field]
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ChampionError(f"{path}: '{field}' must be {kind.__name__}")
    return value


def parse_champion(data: Any, path: Path) -> Champion:
    """Validate one ``champion.json`` payload.

    Raises:
        ChampionError: wrong schema, a missing or mistyped field, or an id that does
            not match its directory.
    """
    if not isinstance(data, dict):
        raise ChampionError(f"{path}: expected a JSON object")
    if data.get("schema") != SCHEMA:
        raise ChampionError(
            f"{path}: schema must be {SCHEMA}, got {data.get('schema')!r}"
        )
    champion_id = _require(data, "id", str, path)
    if path.parent.name != champion_id:
        raise ChampionError(f"{path}: id {champion_id!r} does not match its directory")
    hulls = _require(data, "hulls", list, path)
    if not hulls or not all(isinstance(h, str) for h in hulls):
        raise ChampionError(f"{path}: 'hulls' must be a non-empty list of hull names")
    raw_weights = _require(data, "weights", dict, path)
    sha = _require(raw_weights, "sha256", str, path)
    if not _SHA256.match(sha):
        raise ChampionError(f"{path}: weights.sha256 is not a sha256 hex digest")
    return Champion(
        id=champion_id,
        name=_require(data, "name", str, path),
        run=_require(data, "run", str, path),
        checkpoint=_require(data, "checkpoint", str, path),
        sim_version=_require(data, "sim_version", int, path),
        hulls=tuple(hulls),
        promoted=_require(data, "promoted", str, path),
        parent=_require(data, "parent", str, path),
        eval_json=_require(data, "eval_json", str, path),
        eval=_require(data, "eval", dict, path),
        weights=Weights(
            sha256=sha,
            bytes=_require(raw_weights, "bytes", int, path),
            url=_require(raw_weights, "url", str, path),
            key=_require(raw_weights, "key", str, path),
        ),
    )


def load_champions(champions_dir: Path = CHAMPIONS_DIR) -> list[Champion]:
    """Every champion, oldest promotion first (an absent directory means none)."""
    if not champions_dir.is_dir():
        return []
    champions = []
    for path in sorted(champions_dir.glob("*/champion.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise ChampionError(f"{path}: invalid JSON: {exc}") from exc
        champions.append(parse_champion(data, path))
    return sorted(champions, key=lambda c: (c.promoted, c.id))


def find_champion(champion_id: str, champions_dir: Path = CHAMPIONS_DIR) -> Champion:
    """The champion called ``champion_id``, or the current one for ``"current"``.

    Raises:
        ChampionError: no such champion, or the registry is empty.
    """
    champions = load_champions(champions_dir)
    if not champions:
        raise ChampionError(f"no champions in {champions_dir}")
    if champion_id == "current":
        return champions[-1]
    for champion in champions:
        if champion.id == champion_id:
            return champion
    known = ", ".join(c.id for c in champions)
    raise ChampionError(f"no champion {champion_id!r} (known: {known})")


# ---------------------------------------------------------------------------
# Promote
# ---------------------------------------------------------------------------


def _sim_version_of(checkpoint: Path) -> int:
    """The sim version a spike checkpoint was trained on (its ``meta``)."""
    import torch

    blob = torch.load(checkpoint, map_location="cpu", weights_only=False)
    meta = blob.get("meta", {}) if isinstance(blob, dict) else {}
    version = meta.get("sim_version") if isinstance(meta, dict) else None
    if not isinstance(version, int):
        raise ChampionError(f"{checkpoint}: no integer meta.sim_version")
    return version


def promote(
    *,
    champion_id: str,
    name: str,
    run: str,
    checkpoint: Path,
    hulls: Sequence[str],
    eval_json: Path,
    store: WeightStore,
    sim_version: int,
    parent: str = "",
    promoted: str = "",
    champions_dir: Path = CHAMPIONS_DIR,
    runs_dir: Path = RUNS_DIR,
) -> Champion:
    """Upload ``checkpoint`` and write ``<champions_dir>/<id>/champion.json``.

    ``promoted`` defaults to today; ``parent`` is the champion this one replaces
    ("" for the first). Paths in the record are stored as given, so pass them
    repo-relative.

    Raises:
        ChampionError: a bad id, an unknown run or parent, a missing file, an eval
            that is not a duel eval, or an id that is already promoted.
    """
    if not _ID.match(champion_id):
        raise ChampionError(
            f"champion id {champion_id!r} must look like YYYY-MM-DD-name"
        )
    if not (runs_dir / run).is_dir():
        raise ChampionError(f"run {run!r} is not in {runs_dir}")
    for path in (checkpoint, eval_json):
        if not path.is_file():
            raise ChampionError(f"{path} does not exist")
    if not hulls:
        raise ChampionError("a champion must be certified for at least one hull")
    existing = {c.id for c in load_champions(champions_dir)}
    if champion_id in existing:
        raise ChampionError(f"champion {champion_id} is already promoted")
    if parent and parent not in existing:
        raise ChampionError(f"parent {parent!r} is not a promoted champion")
    try:
        summary = summarize_eval(eval_json)
    except ExportError as exc:
        raise ChampionError(str(exc)) from exc

    sha = sha256_of(checkpoint)
    key = weights_key(champion_id, sha)
    url = store.put(checkpoint, key)
    champion = Champion(
        id=champion_id,
        name=name,
        run=run,
        checkpoint=str(checkpoint),
        sim_version=sim_version,
        hulls=tuple(hulls),
        promoted=promoted or dt.date.today().isoformat(),
        parent=parent,
        eval_json=str(eval_json),
        eval=summary,
        weights=Weights(sha256=sha, bytes=checkpoint.stat().st_size, url=url, key=key),
    )
    out = champions_dir / champion_id / "champion.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(champion.to_json(), indent=2) + "\n")
    return champion


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url, headers={"User-Agent": "rl-fighter-champion/1"}
    )
    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                for block in iter(lambda: response.read(1 << 20), b""):
                    tmp.write(block)
        except (urllib.error.URLError, TimeoutError) as exc:
            tmp_path.unlink(missing_ok=True)
            raise ChampionError(f"download of {url} failed: {exc}") from exc
    tmp_path.replace(dest)


def fetch(
    champion: Champion,
    cache_dir: Path = DEFAULT_CACHE,
    download: Any = _download,
) -> Path:
    """A local checkpoint with the champion's recorded hash.

    Uses the original training file when it is still there and unchanged, else the
    cached download, else downloads it.

    Raises:
        ChampionError: the download fails or its hash does not match the record.
    """
    sha = champion.weights.sha256
    original = Path(champion.checkpoint)
    if original.is_file() and sha256_of(original) == sha:
        return original
    cached = cache_dir / f"{sha}.pt"
    if cached.is_file() and sha256_of(cached) == sha:
        return cached
    download(champion.weights.url, cached)
    got = sha256_of(cached)
    if got != sha:
        cached.unlink()
        raise ChampionError(f"{champion.weights.url}: sha256 {got} != recorded {sha}")
    return cached


def build_env(champion: Champion, checkpoint: Path) -> dict[str, str]:
    """What ``scripts/build_site.sh`` needs to build the bundle for ``champion``."""
    return {
        "CHAMPION_CHECKPOINT": str(checkpoint),
        "CHAMPION_RUN": champion.run,
        "CHAMPION_EVAL_JSON": champion.eval_json,
        "RLF_CHAMPION_ID": champion.id,
        "RLF_CHAMPION_NAME": champion.name,
        "RLF_CHAMPION_HULLS": ",".join(champion.hulls),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--champions", type=Path, default=CHAMPIONS_DIR)
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path(os.environ.get("RLF_WEIGHT_CACHE", DEFAULT_CACHE)),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("promote", help="upload a checkpoint and register it")
    p.add_argument("--id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--run", required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--hulls", required=True, help="comma-separated certified hulls")
    p.add_argument("--eval-json", type=Path, required=True)
    p.add_argument("--parent", default="")
    p.add_argument("--promoted", default="", help="ISO date (default: today)")

    for command in ("fetch", "env"):
        f = sub.add_parser(command)
        f.add_argument("id", nargs="?", default="current")
    sub.add_parser("list")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "promote":
            champion = promote(
                champion_id=args.id,
                name=args.name,
                run=args.run,
                checkpoint=args.checkpoint,
                hulls=[h for h in args.hulls.split(",") if h],
                eval_json=args.eval_json,
                store=GcsStore(),
                sim_version=_sim_version_of(args.checkpoint),
                parent=args.parent,
                promoted=args.promoted,
                champions_dir=args.champions,
            )
            print(f"promoted {champion.id}: {champion.weights.url}")
        elif args.command == "list":
            for c in load_champions(args.champions):
                print(
                    f"{c.promoted}  {c.id}  sim v{c.sim_version}  {','.join(c.hulls)}  {c.name}"
                )
        else:
            champion = find_champion(args.id, args.champions)
            checkpoint = fetch(champion, args.cache)
            if args.command == "fetch":
                print(checkpoint)
            else:
                for key, value in build_env(champion, checkpoint).items():
                    print(f"{key}={shlex.quote(value)}")
    except ChampionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
