"""The live page's pilots: choosing them, the registry, the bundle, the ship-by-ship draw."""

from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from spacefight.population.records import (
    ARCHIVED,
    Member,
    Population,
    RatingEntry,
    script_member,
)
from tools.build_bundle import BundleError, bundle_id, live_pilots
from tools.live_pilots import (
    LivePilot,
    LivePilotsError,
    fetch_checkpoint,
    load_registry,
    select_members,
)

REPO = Path(__file__).resolve().parents[1]
SHA = "a" * 64


def _member(member_id: str, rating: float | None, phase: str = "night") -> Member:
    ratings = (
        () if rating is None else (RatingEntry(phase, "2026-11-02", rating, 5.0, 100),)
    )
    return replace(
        script_member(),
        id=member_id,
        family="fighters",
        founder=member_id,
        checkpoint=f"lab/runs/{member_id}.pt",
        sha256=SHA,
        ratings=ratings,
    )


def _population(*members: Member) -> Population:
    population = Population(Path("."))
    population.members.update({m.id: m for m in members})
    return population


def test_the_best_rated_are_chosen_and_the_limit_drops_the_worst() -> None:
    population = _population(
        _member("low", -500.0), _member("high", 300.0), _member("mid", 10.0)
    )
    assert [m.id for m in select_members(population, 2)] == ["high", "mid"]


def test_the_script_and_unrated_members_never_fly() -> None:
    script = replace(
        script_member(), ratings=(RatingEntry("night", "2026-11-02", 900.0, 5.0, 100),)
    )
    population = _population(script, _member("unrated", None), _member("rated", 0.0))
    assert [m.id for m in select_members(population, 10)] == ["rated"]


def test_an_archived_member_still_flies() -> None:
    retired = replace(
        _member("retired", 50.0),
        status=ARCHIVED,
        archived_reason="gate",
        archived_date="2026-11-02",
    )
    assert [m.id for m in select_members(_population(retired), 10)] == ["retired"]


def test_a_rating_from_an_older_phase_is_not_compared() -> None:
    stale = replace(
        _member("stale", 900.0),
        ratings=(RatingEntry("old", "2026-10-01", 900.0, 5.0, 100),),
    )
    population = _population(stale, _member("current", 1.0))
    assert [m.id for m in select_members(population, 10)] == ["current"]


def test_nobody_rated_is_an_error() -> None:
    with pytest.raises(LivePilotsError, match="no rated member"):
        select_members(_population(_member("unrated", None)), 10)


def _pilot(pilot_id: str, sha: str = SHA) -> LivePilot:
    return LivePilot(
        pilot_id, "fighters", 1.0, f"lab/x/{pilot_id}.pt", sha, "https://x"
    )


def test_the_registry_refuses_too_many_pilots_and_duplicates(tmp_path: Path) -> None:
    registry = tmp_path / "live.json"

    def write(ids: list[str]) -> None:
        pilots = [vars(_pilot(i)) for i in ids]
        registry.write_text(
            json.dumps({"schema": "rlf.live_pilots/1", "pilots": pilots})
        )

    write(["a", "b"])
    assert [p.id for p in load_registry(registry)] == ["a", "b"]
    write([str(i) for i in range(11)])
    with pytest.raises(LivePilotsError, match="11 pilots"):
        load_registry(registry)
    write(["a", "a"])
    with pytest.raises(LivePilotsError, match="twice"):
        load_registry(registry)


def test_a_download_with_the_wrong_hash_is_refused_and_removed(tmp_path: Path) -> None:
    def fake_download(_url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"other weights")

    with pytest.raises(LivePilotsError, match="sha256"):
        fetch_checkpoint(_pilot("x"), tmp_path, fake_download)
    assert not (tmp_path / f"{SHA}.pt").exists()


def _bundle_with_pilot(tmp_path: Path, weights: bytes) -> Path:
    for rel, data in (
        ("pkg/sim_wasm_bg.wasm", b"w"),
        ("pkg/sim_wasm.js", b"j"),
        ("policy/weights.bin", b"c"),
        ("catalogue.json", b"{}"),
        ("pilots/a/weights.bin", weights),
        ("pilots/a/manifest.json", b"{}"),
    ):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    entry = {"id": "a", "dir": "pilots/a"}
    (tmp_path / "pilots/index.json").write_text(json.dumps({"pilots": [entry]}))
    return tmp_path


def test_the_bundle_id_changes_with_any_pilots_weights(tmp_path: Path) -> None:
    bundle = _bundle_with_pilot(tmp_path, b"one")
    settings = {"pilots": live_pilots(bundle)}
    before = bundle_id(bundle, settings)
    (bundle / "pilots/a/weights.bin").write_bytes(b"two")
    assert bundle_id(bundle, settings) != before


def test_a_bundle_without_an_index_has_no_pilots_and_a_missing_export_raises(
    tmp_path: Path,
) -> None:
    assert live_pilots(tmp_path) == []
    bundle = _bundle_with_pilot(tmp_path, b"one")
    (bundle / "pilots/a/weights.bin").unlink()
    with pytest.raises(BundleError, match="weights.bin is missing"):
        live_pilots(bundle)


def test_the_committed_registry_flies_ten_rated_pilots_and_never_the_script() -> None:
    pilots = load_registry(REPO / "lab/live_pilots.json")
    assert len(pilots) == 10
    assert "script" not in {p.id for p in pilots}
    assert all(
        p.url.startswith("https://storage.tcgarvin.com/rl-fighter/") for p in pilots
    )
    ratings = [p.rating for p in pilots]
    assert ratings == sorted(ratings, reverse=True)


ASSIGN = """
import { assignPilots } from "./web/src/live/match.ts";
const pool = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"];
const draws = [assignPilots(pool, 20, 7), assignPilots(pool, 20, 7), assignPilots(pool, 20, 8)];
const many = {};
for (const id of assignPilots(pool, 10000, 3)) many[id] = (many[id] ?? 0) + 1;
console.log(JSON.stringify({ draws, many, alone: assignPilots(["only"], 3, 1) }));
"""


def test_pilots_are_drawn_ship_by_ship_evenly_and_repeat_for_a_seed() -> None:
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--no-warnings",
            "--input-type=module",
            "-e",
            ASSIGN,
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    first, again, other = data["draws"]
    assert first == again, "the same seed flies the same pilots"
    assert first != other, "another seed flies other pilots"
    assert len(set(first)) > 1, "ships in one match have different pilots"
    assert set(data["many"]) == set("abcdefghij")
    assert all(800 < n < 1200 for n in data["many"].values()), data["many"]
    assert data["alone"] == ["only"] * 3
