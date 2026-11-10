"""Publishing a notebook entry's films: content-addressed keys and the manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.notebook_media import MediaError, load_media, media_key, publish

BASE_URL = "https://example.test"


class RecordingStore:
    """A media store that only remembers what it was asked to put."""

    def __init__(self) -> None:
        self.puts: list[tuple[str, str, str]] = []

    def put(self, local: Path, key: str, content_type: str) -> str:
        self.puts.append((local.name, key, content_type))
        return f"{BASE_URL}/{key}"


def _run_with_media(tmp_path: Path, files: dict[str, bytes]) -> Path:
    run = tmp_path / "2026-01-01-films"
    (run / "media").mkdir(parents=True)
    for name, content in files.items():
        (run / "media" / name).write_bytes(content)
    return run


def test_publish_uploads_films_and_posters_by_content_and_writes_the_manifest(
    tmp_path: Path,
) -> None:
    run = _run_with_media(
        tmp_path, {"a.mp4": b"film", "a.jpg": b"still", "notes.txt": b"skip me"}
    )
    store = RecordingStore()

    manifest = publish(run, store)

    film_sha = hashlib.sha256(b"film").hexdigest()
    still_sha = hashlib.sha256(b"still").hexdigest()
    film_key = f"rl-fighter/notebook/2026-01-01-films/{film_sha}.mp4"
    still_key = f"rl-fighter/notebook/2026-01-01-films/{still_sha}.jpg"
    assert media_key("2026-01-01-films", film_sha, ".mp4") == film_key
    assert store.puts == [
        ("a.jpg", still_key, "image/jpeg"),
        ("a.mp4", film_key, "video/mp4"),
    ]
    assert json.loads((run / "media.json").read_text()) == manifest
    assert manifest["schema"] == "rlf.notebook.media/1"
    assert manifest["files"][1] == {
        "name": "a.mp4",
        "sha256": film_sha,
        "bytes": 4,
        "key": film_key,
        "url": f"{BASE_URL}/{film_key}",
    }
    assert load_media(run) == {
        "a.jpg": f"{BASE_URL}/{still_key}",
        "a.mp4": f"{BASE_URL}/{film_key}",
    }


def test_publish_refuses_a_run_with_nothing_to_publish(tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="no media directory"):
        publish(tmp_path / "2026-01-01-none", RecordingStore())
    run = _run_with_media(tmp_path, {"notes.txt": b"not a film"})
    with pytest.raises(MediaError, match="holds none"):
        publish(run, RecordingStore())


def test_load_media_is_empty_without_a_manifest_and_rejects_a_bad_one(
    tmp_path: Path,
) -> None:
    run = tmp_path / "2026-01-01-films"
    run.mkdir()
    assert load_media(run) == {}
    (run / "media.json").write_text(json.dumps({"schema": "other"}))
    with pytest.raises(MediaError, match="schema is not"):
        load_media(run)
    bad = {"schema": "rlf.notebook.media/1", "files": [{"name": "a.mp4"}]}
    (run / "media.json").write_text(json.dumps(bad))
    with pytest.raises(MediaError, match="name and a url"):
        load_media(run)
