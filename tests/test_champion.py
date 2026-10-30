"""The champion registry: promote, load, fetch (tools/champion.py), with a local store."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools import build_notebook
from tools.champion import (
    SCHEMA,
    Champion,
    ChampionError,
    GcsStore,
    build_env,
    fetch,
    find_champion,
    load_champions,
    promote,
    sha256_of,
)

BASE_URL = "https://example.test"


class DirStore:
    """A weight store backed by a directory, standing in for the bucket."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.puts: list[str] = []

    def put(self, local: Path, key: str) -> str:
        self.puts.append(key)
        dest = self.root / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, dest)
        return f"{BASE_URL}/{key}"

    def download(self, url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.root / url.removeprefix(f"{BASE_URL}/"), dest)


@pytest.fixture
def lab(tmp_path: Path) -> dict[str, Path]:
    runs = tmp_path / "runs"
    run = runs / "2026-10-29-pilot"
    (run / "eval").mkdir(parents=True)
    checkpoint = run / "ppo_600.pt"
    checkpoint.write_bytes(b"weights v1")
    eval_json = run / "eval" / "vs_script.json"
    eval_json.write_text(
        json.dumps(
            {
                "a": "policy:ppo_600.pt",
                "b": "script",
                "config": {"n": 8, "sim_version": 3},
                "side_a": {"wins": 6, "draws": 1, "losses": 1, "win_rate": 0.75},
                "match": {"length_median": 300},
            }
        )
    )
    return {
        "runs": runs,
        "champions": tmp_path / "champions",
        "checkpoint": checkpoint,
        "eval": eval_json,
        "store": tmp_path / "store",
        "cache": tmp_path / "cache",
    }


def _promote(lab: dict[str, Path], store: DirStore, cid: str, **extra: str) -> Champion:
    return promote(
        champion_id=cid,
        name=f"pilot {cid}",
        run="2026-10-29-pilot",
        checkpoint=lab["checkpoint"],
        hulls=["fighter", "strafer"],
        eval_json=lab["eval"],
        store=store,
        sim_version=3,
        champions_dir=lab["champions"],
        runs_dir=lab["runs"],
        **extra,
    )


def test_promote_uploads_by_content_hash_and_writes_the_record(
    lab: dict[str, Path],
) -> None:
    store = DirStore(lab["store"])
    champion = _promote(lab, store, "2026-10-29-v3", promoted="2026-10-29")

    sha = sha256_of(lab["checkpoint"])
    assert store.puts == [f"rl-fighter/champions/2026-10-29-v3/{sha}.pt"]
    record = json.loads(
        (lab["champions"] / "2026-10-29-v3" / "champion.json").read_text()
    )
    assert record["schema"] == SCHEMA
    assert record["weights"]["sha256"] == sha
    assert record["weights"]["url"] == f"{BASE_URL}/{store.puts[0]}"
    assert record["eval"]["win_rate"] == 0.75
    assert record["parent"] == ""
    assert load_champions(lab["champions"]) == [champion]


def test_promote_refuses_duplicates_unknown_parents_and_bad_ids(
    lab: dict[str, Path],
) -> None:
    store = DirStore(lab["store"])
    _promote(lab, store, "2026-10-29-v3")
    with pytest.raises(ChampionError, match="already promoted"):
        _promote(lab, store, "2026-10-29-v3")
    with pytest.raises(ChampionError, match="parent"):
        _promote(lab, store, "2026-10-30-fleet", parent="2026-01-01-nobody")
    with pytest.raises(ChampionError, match="YYYY-MM-DD"):
        _promote(lab, store, "Fleet Pilot")


def test_the_current_champion_is_the_latest_promotion(lab: dict[str, Path]) -> None:
    store = DirStore(lab["store"])
    _promote(lab, store, "2026-10-29-v3", promoted="2026-10-29")
    _promote(
        lab, store, "2026-10-30-fleet", promoted="2026-10-30", parent="2026-10-29-v3"
    )

    assert find_champion("current", lab["champions"]).id == "2026-10-30-fleet"
    assert find_champion("2026-10-29-v3", lab["champions"]).id == "2026-10-29-v3"
    with pytest.raises(ChampionError, match="no champion"):
        find_champion("2026-10-31-missing", lab["champions"])


def test_the_notebook_reads_champion_records(lab: dict[str, Path]) -> None:
    _promote(lab, DirStore(lab["store"]), "2026-10-29-v3", promoted="2026-10-29")
    [seen] = build_notebook.load_champions(lab["champions"])
    assert (seen.id, seen.run, seen.hulls) == (
        "2026-10-29-v3",
        "2026-10-29-pilot",
        ("fighter", "strafer"),
    )


def test_fetch_prefers_the_original_then_downloads_and_verifies(
    lab: dict[str, Path],
) -> None:
    store = DirStore(lab["store"])
    champion = _promote(lab, store, "2026-10-29-v3")
    assert fetch(champion, lab["cache"], store.download) == lab["checkpoint"]

    lab["checkpoint"].write_bytes(b"retrained since")
    got = fetch(champion, lab["cache"], store.download)
    assert got == lab["cache"] / f"{champion.weights.sha256}.pt"
    assert got.read_bytes() == b"weights v1"


def test_fetch_rejects_a_download_with_the_wrong_hash(lab: dict[str, Path]) -> None:
    store = DirStore(lab["store"])
    champion = _promote(lab, store, "2026-10-29-v3")
    lab["checkpoint"].unlink()
    (lab["store"] / champion.weights.key).write_bytes(b"tampered")

    with pytest.raises(ChampionError, match="sha256"):
        fetch(champion, lab["cache"], store.download)
    assert not (lab["cache"] / f"{champion.weights.sha256}.pt").exists()


def test_build_env_names_what_the_site_build_needs(lab: dict[str, Path]) -> None:
    champion = _promote(lab, DirStore(lab["store"]), "2026-10-29-v3")
    env = build_env(champion, lab["checkpoint"])
    assert env["CHAMPION_RUN"] == "2026-10-29-pilot"
    assert env["RLF_CHAMPION_ID"] == "2026-10-29-v3"
    assert env["RLF_CHAMPION_HULLS"] == "fighter,strafer"


def test_records_with_the_wrong_schema_or_directory_are_rejected(
    lab: dict[str, Path],
) -> None:
    champion = _promote(lab, DirStore(lab["store"]), "2026-10-29-v3")
    record = champion.to_json()
    moved = lab["champions"] / "2026-10-29-other" / "champion.json"
    moved.parent.mkdir()
    moved.write_text(json.dumps(record))
    with pytest.raises(ChampionError, match="directory"):
        load_champions(lab["champions"])

    moved.write_text(json.dumps(record | {"id": "2026-10-29-other", "schema": "old/0"}))
    with pytest.raises(ChampionError, match="schema"):
        load_champions(lab["champions"])


def test_the_gcs_store_only_writes_under_its_prefix(tmp_path: Path) -> None:
    with pytest.raises(ChampionError, match="outside"):
        GcsStore().put(tmp_path / "x.pt", "me.png")
