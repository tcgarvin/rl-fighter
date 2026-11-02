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
from tools.champion import sha256_of
from tools.live_pilots import (
    MATCHUP_MODES,
    LivePilot,
    LivePilotsError,
    fetch_checkpoint,
    load_registry,
    matchups,
    publish,
    registry_entry,
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
        pilot_id,
        "fighters",
        1.0,
        f"lab/x/{pilot_id}.pt",
        sha,
        "https://x",
        "A note.",
        {"go_to": 0.5},
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


class _FakeStore:
    def put(self, local: Path, key: str) -> str:
        return f"https://x/{key}"


def _season_with_one_pilot(root: Path) -> Path:
    """A season whose one rated, drilled member's checkpoint is under the cwd."""
    checkpoint = root / "pilot.pt"
    checkpoint.write_bytes(b"weights")
    member = {
        "schema": "rlf.population.member/1",
        "id": "ace",
        "family": "fighters",
        "founder": "ace",
        "parent": "",
        "relation": "",
        "fork_update": -1,
        "settings_changed": {},
        "checkpoint": checkpoint.relative_to(Path.cwd()).as_posix(),
        "sha256": sha256_of(checkpoint),
        "status": "active",
        "archived_reason": "",
        "archived_date": "",
        "note": "",
        "ratings": [
            {
                "phase": "p",
                "date": "2026-01-01",
                "rating": 5.0,
                "sd": 1.0,
                "matches": 10,
            }
        ],
        "drills": [
            {
                "phase": "p",
                "date": "2026-01-01",
                "scores": {
                    "goto_arrival": 0.5,
                    "attack_flip": 0.25,
                    "defend_flip": 1.0,
                },
                "passed": True,
            }
        ],
    }
    season = root / "season"
    (season / "members").mkdir(parents=True)
    (season / "members" / "ace.json").write_text(json.dumps(member))
    return season


def _publish(root: Path, notes: dict[str, str], entry: str) -> list[LivePilot]:
    (root / "runs" / "2026-01-01-list").mkdir(parents=True, exist_ok=True)
    (root / "runs" / "2026-01-01-list" / "results.md").write_text("# List\n")
    (root / "notes.json").write_text(json.dumps(notes))
    return publish(
        _season_with_one_pilot(root),
        root / "live.json",
        entry,
        notes=root / "notes.json",
        runs=root / "runs",
        store=_FakeStore(),
    )


def test_publish_records_the_note_the_drills_and_the_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    pilots = _publish(tmp_path, {"ace": "Flies well."}, "2026-01-01-list")
    assert pilots[0].note == "Flies well."
    assert pilots[0].follows == {"go_to": 0.5, "attack": 0.25, "defend": 1.0}
    assert registry_entry(tmp_path / "live.json") == "2026-01-01-list"
    assert load_registry(tmp_path / "live.json")[0].note == "Flies well."


def test_a_pilot_cannot_go_live_without_a_note_or_an_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    with pytest.raises(LivePilotsError, match="no note for ace"):
        _publish(tmp_path / "a", {}, "2026-01-01-list")
    with pytest.raises(LivePilotsError, match="no logbook entry"):
        _publish(tmp_path / "b", {"ace": "Flies well."}, "2026-01-01-other")


def test_the_grid_keeps_rating_order_and_refuses_a_pilot_who_never_played(
    tmp_path: Path,
) -> None:
    results = tmp_path / "rr"
    results.mkdir()
    grid = {
        "a": {"b": 0.75, "script": 0.875},
        "b": {"a": 0.25, "script": 0.5},
    }
    (results / "summary.json").write_text(
        json.dumps(
            {
                "members": ["a", "b", "script"],
                "win_matrix": {mode: grid for mode in MATCHUP_MODES},
            }
        )
    )
    (results / "config.json").write_text(json.dumps({"n_per_mission": 240}))
    out = tmp_path / "matchups.json"
    data = matchups([_pilot("b"), _pilot("a")], results, out)
    assert data["modes"]["overall"] == [[None, 0.25], [0.75, None]]
    assert data["script"]["convoy_escort"] == [0.5, 0.875]
    assert json.loads(out.read_text()) == data
    with pytest.raises(LivePilotsError, match="never played c"):
        matchups([_pilot("c")], results, out)


def test_the_committed_list_has_notes_and_an_entry_with_its_grid() -> None:
    registry = REPO / "lab/live_pilots.json"
    pilots = load_registry(registry)
    assert all(p.note for p in pilots)
    entry = REPO / "lab/runs" / registry_entry(registry)
    grid = json.loads((entry / "matchups.json").read_text())
    assert [p["id"] for p in grid["pilots"]] == [p.id for p in pilots]
    assert 'data-figure="matchups"' in (entry / "results.md").read_text()


INSPECT = """
import { outputRows, pickShip, rowOdds } from "./web/src/live/inspect.ts";
const near = [{ id: 3, x: 100, y: 100, sizePx: 10 }, { id: 5, x: 130, y: 100, sizePx: 10 }];
const carrier = [{ id: 1, x: 200, y: 200, sizePx: 200 }, { id: 2, x: 250, y: 200, sizePx: 10 }];
const heads = [
  { name: "throttle", action_start: 0, count: 8, choices: 3, logit_start: 0, masked_value: 1 },
  { name: "slew", action_start: 8, count: 6, choices: 3, logit_start: 24, masked_value: 1 },
  { name: "fire", action_start: 14, count: 6, choices: 2, logit_start: 42, masked_value: 0 },
  { name: "power", action_start: 20, count: 1, choices: 7, logit_start: 54, masked_value: null },
];
const valid = new Uint8Array(21);
valid[0] = valid[1] = valid[14] = valid[20] = 1;
const rows = outputRows(heads, valid, ["thruster.main", "thruster.rcs.fl"], ["turret.nose"]);
const logits = new Float32Array(61);
logits[1] = Math.log(3);
const odds = new Float64Array(7);
rowOdds(rows[0], logits, new Int8Array(21), odds);
const net = Array.from(odds.subarray(0, 3));
const action = new Int8Array(21);
action[0] = 2;
rowOdds(rows[0], null, action, odds);
console.log(JSON.stringify({
  nearest: pickShip(near, 112, 100),
  other: pickShip(near, 128, 100),
  miss: pickShip(near, 300, 300),
  onHull: pickShip(carrier, 160, 200),
  underFinger: pickShip(carrier, 250, 200),
  rows: rows.map((r) => [r.kind, r.label, r.logitStart]),
  net,
  script: Array.from(odds.subarray(0, 3)),
}));
"""


def test_a_tap_finds_the_ship_and_outputs_read_as_odds() -> None:
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--no-warnings",
            "--input-type=module",
            "-e",
            INSPECT,
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    got = json.loads(result.stdout)
    assert (got["nearest"], got["other"], got["miss"]) == (3, 5, -1)
    # A carrier's hull is a target, but a fighter under the finger wins over it.
    assert (got["onHull"], got["underFinger"]) == (1, 2)
    # Only the hull's real mounts get a row, each reading its own logits.
    assert got["rows"] == [
        ["throttle", "main", 0],
        ["throttle", "rcs.fl", 3],
        ["fire", "nose", 42],
        ["power", "", 54],
    ]
    assert got["net"] == pytest.approx([0.2, 0.6, 0.2])
    # The script has no odds: its choice has all of them.
    assert got["script"] == [0, 0, 1]
