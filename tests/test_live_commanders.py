"""The live page's commanders: the stable, publishing, the bundle, the side-by-side draw."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import torch

from spacefight.commander.policy import CommanderActor, save_commander
from tools.build_bundle import BundleError, bundle_id, live_commanders
from tools.champion import sha256_of
from tools.export_commander import flat_layout
from tools.live_commanders import (
    KEY_PREFIX,
    LEARNED,
    SCRIPTED,
    LiveCommander,
    LiveCommandersError,
    export_commanders,
    fetch_checkpoint,
    load_registry,
    parse_assignments,
    publish,
    write_registry,
)

REPO = Path(__file__).resolve().parents[1]
SHA = "b" * 64
SCRIPT = LiveCommander(SCRIPTED, SCRIPTED, "The sim's rules.")


def _learned(cid: str, checkpoint: str = "lab/x.pt", sha: str = SHA) -> LiveCommander:
    return LiveCommander(cid, LEARNED, "A net.", checkpoint, sha, "https://x", 5)


def _commander_checkpoint(path: Path, update: int = 1200) -> Path:
    torch.manual_seed(0)
    save_commander(path, CommanderActor(), {"update": update})
    return path


def _wasm_io() -> dict[str, object]:
    return {
        "version": 1,
        "entity_dim": 40,
        "global_dim": 53,
        "action_dim": 40,
        "n_entities": 20,
        "n_points": 25,
        "flat_dim": 1082,
        "flat_layout": [list(e) for e in flat_layout()],
    }


def test_the_committed_stable_leads_with_the_scripted_commander_and_is_noted() -> None:
    commanders, entry = load_registry(REPO / "lab/live_commanders.json")
    assert (commanders[0].id, commanders[0].kind) == (SCRIPTED, SCRIPTED)
    notes = json.loads((REPO / "lab/live_commander_notes.json").read_text())
    assert all(c.note == notes[c.id] for c in commanders)
    learned = [c for c in commanders if c.kind == LEARNED]
    assert all(
        c.url == f"https://storage.tcgarvin.com/{KEY_PREFIX}/{c.id}/{c.sha256}.pt"
        for c in learned
    )
    if learned:
        assert (REPO / "lab/runs" / entry / "results.md").is_file()


@pytest.mark.parametrize(
    ("commanders", "entry", "error"),
    [
        ([_learned("c1")], "e", "scripted commander must be listed once"),
        ([SCRIPT, SCRIPT], "e", "twice"),
        ([SCRIPT, _learned("c1"), _learned("c1")], "e", "twice"),
        ([SCRIPT, _learned("c1")], "", "needs a logbook entry"),
        ([SCRIPT, _learned("C 1")], "e", "slug"),
        ([SCRIPT, _learned("c1", sha="short")], "e", "needs a checkpoint, sha256"),
        ([SCRIPT, LiveCommander("c2", "other", "x")], "e", "kind"),
        ([SCRIPT, LiveCommander("c3", LEARNED, " ", "a.pt", SHA, "u")], "e", "no note"),
    ],
)
def test_the_stable_refuses_a_bad_list(
    tmp_path: Path, commanders: list[LiveCommander], entry: str, error: str
) -> None:
    with pytest.raises(LiveCommandersError, match=error):
        write_registry(tmp_path / "s.json", commanders, entry)


def test_a_written_stable_reads_back(tmp_path: Path) -> None:
    registry = tmp_path / "s.json"
    write_registry(registry, [SCRIPT, _learned("c1_1200")], "2026-11-08-commander-1")
    commanders, entry = load_registry(registry)
    assert commanders == [SCRIPT, _learned("c1_1200")]
    assert entry == "2026-11-08-commander-1"
    # The scripted commander's record carries no weights fields.
    assert json.loads(registry.read_text())["commanders"][0] == {
        "id": SCRIPTED,
        "kind": SCRIPTED,
        "note": "The sim's rules.",
    }


def test_assignments_are_id_equals_checkpoint() -> None:
    assert parse_assignments(["c1=a/b.pt"]) == [("c1", Path("a/b.pt"))]
    with pytest.raises(LiveCommandersError, match="not <id>=<checkpoint>"):
        parse_assignments(["c1"])


class _FakeStore:
    def __init__(self) -> None:
        self.keys: list[str] = []

    def put(self, local: Path, key: str) -> str:
        self.keys.append(key)
        return f"https://storage.example/{key}"


def _logbook(root: Path, entry: str = "2026-01-01-cmd") -> Path:
    runs = root / "runs"
    (runs / entry).mkdir(parents=True, exist_ok=True)
    (runs / entry / "results.md").write_text("# Commanders\n")
    return runs


def _notes(root: Path, notes: dict[str, str]) -> Path:
    path = root / "notes.json"
    path.write_text(json.dumps(notes))
    return path


def test_publish_uploads_by_hash_and_lists_the_scripted_commander_first(
    tmp_path: Path,
) -> None:
    ckpt = _commander_checkpoint(tmp_path / "c.pt")
    store = _FakeStore()
    registry = tmp_path / "s.json"
    commanders = publish(
        registry,
        "2026-01-01-cmd",
        [("c1_1200", ckpt)],
        notes=_notes(tmp_path, {SCRIPTED: "Rules.", "c1_1200": "First night."}),
        runs=_logbook(tmp_path),
        store=store,
    )
    sha = sha256_of(ckpt)
    assert store.keys == [f"{KEY_PREFIX}/c1_1200/{sha}.pt"]
    assert [c.id for c in commanders] == [SCRIPTED, "c1_1200"]
    learned = commanders[1]
    assert (learned.sha256, learned.update, learned.note) == (sha, 1200, "First night.")
    assert (
        learned.url == f"https://storage.example/rl-fighter/commanders/c1_1200/{sha}.pt"
    )
    assert load_registry(registry) == (commanders, "2026-01-01-cmd")


def test_publish_keep_adds_to_the_learned_ones_listed(tmp_path: Path) -> None:
    registry = tmp_path / "s.json"
    write_registry(registry, [SCRIPT, _learned("old")], "e")
    ckpt = _commander_checkpoint(tmp_path / "c.pt")
    notes = _notes(tmp_path, {SCRIPTED: "Rules.", "new": "Second night."})
    commanders = publish(
        registry,
        "2026-01-01-cmd",
        [("new", ckpt)],
        keep=True,
        notes=notes,
        runs=_logbook(tmp_path),
        store=_FakeStore(),
    )
    assert [c.id for c in commanders] == [SCRIPTED, "old", "new"]


def test_a_commander_cannot_go_live_without_a_note_an_entry_or_a_commander_file(
    tmp_path: Path,
) -> None:
    ckpt = _commander_checkpoint(tmp_path / "c.pt")
    runs = _logbook(tmp_path)
    store = _FakeStore()
    registry = tmp_path / "s.json"

    def attempt(entry: str, checkpoint: Path, notes: dict[str, str]) -> None:
        publish(
            registry,
            entry,
            [("c1", checkpoint)],
            notes=_notes(tmp_path, notes),
            runs=runs,
            store=store,
        )

    noted = {SCRIPTED: "Rules.", "c1": "A net."}
    with pytest.raises(LiveCommandersError, match="no note for c1"):
        attempt("2026-01-01-cmd", ckpt, {SCRIPTED: "Rules."})
    with pytest.raises(LiveCommandersError, match="no logbook entry"):
        attempt("2026-01-01-other", ckpt, noted)
    pilot = tmp_path / "pilot.pt"
    torch.save({"format": "rlf.spike_policy/1"}, pilot)
    with pytest.raises(ValueError, match="not a rlf.commander/1 file"):
        attempt("2026-01-01-cmd", pilot, noted)
    assert store.keys == [], "nothing is uploaded unless every commander checks out"
    assert not registry.exists()


def test_a_download_with_the_wrong_hash_is_refused_and_removed(tmp_path: Path) -> None:
    def fake_download(_url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"other weights")

    with pytest.raises(LiveCommandersError, match="sha256"):
        fetch_checkpoint(_learned("c1", "missing.pt"), tmp_path, fake_download)
    assert not (tmp_path / f"{SHA}.pt").exists()
    with pytest.raises(LiveCommandersError, match="no weights"):
        fetch_checkpoint(SCRIPT, tmp_path, fake_download)


def test_export_writes_each_learned_commander_and_the_index(tmp_path: Path) -> None:
    ckpt = _commander_checkpoint(tmp_path / "c.pt")
    bundle = tmp_path / "bundle"
    stable = [SCRIPT, _learned("c1", str(ckpt), sha256_of(ckpt))]
    index = export_commanders(stable, bundle, _wasm_io(), "2026-01-01-cmd")
    assert index == [
        {"id": SCRIPTED, "kind": SCRIPTED, "note": "The sim's rules."},
        {
            "id": "c1",
            "kind": LEARNED,
            "note": "A net.",
            "dir": "commanders/c1",
            "update": 5,
        },
    ]
    manifest = json.loads((bundle / "commanders/c1/manifest.json").read_text())
    assert manifest["format"] == "rlf.web_commander/1"
    assert live_commanders(bundle) == (index, "2026-01-01-cmd")


def _bundle_files(root: Path) -> None:
    for rel, data in (
        ("pkg/sim_wasm_bg.wasm", b"w"),
        ("pkg/sim_wasm.js", b"j"),
        ("policy/weights.bin", b"c"),
        ("catalogue.json", b"{}"),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def test_the_bundle_id_changes_with_a_commanders_weights_and_a_missing_export_raises(
    tmp_path: Path,
) -> None:
    assert live_commanders(tmp_path) == ([], "")
    _bundle_files(tmp_path)
    ckpt = _commander_checkpoint(tmp_path / "c.pt")
    export_commanders(
        [SCRIPT, _learned("c1", str(ckpt), sha256_of(ckpt))], tmp_path, _wasm_io(), "e"
    )
    settings = {"commanders": live_commanders(tmp_path)[0]}
    before = bundle_id(tmp_path, settings)
    weights = tmp_path / "commanders/c1/weights.bin"
    weights.write_bytes(weights.read_bytes()[:-4] + b"\0\0\0\0")
    assert bundle_id(tmp_path, settings) != before
    weights.unlink()
    with pytest.raises(BundleError, match="weights.bin is missing"):
        live_commanders(tmp_path)


DRAW = """
import { assignCommanders } from "./web/src/live/match.ts";
const stable = ["scripted", "a", "b"];
const draws = [assignCommanders(stable, 7), assignCommanders(stable, 7), assignCommanders(stable, 8)];
const many = { 0: {}, 1: {} };
let mixed = 0;
for (let seed = 0; seed < 6000; seed++) {
  const pair = assignCommanders(stable, seed);
  pair.forEach((id, t) => { many[t][id] = (many[t][id] ?? 0) + 1; });
  if (pair[0] !== pair[1]) mixed += 1;
}
console.log(JSON.stringify({ draws, many, mixed, alone: assignCommanders(["scripted"], 3) }));
"""


def test_each_side_draws_its_commander_uniformly_and_repeats_for_a_seed() -> None:
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--no-warnings",
            "--input-type=module",
            "-e",
            DRAW,
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    first, again, _ = data["draws"]
    assert first == again, "the same seed draws the same commanders"
    for side in ("0", "1"):
        assert set(data["many"][side]) == {"scripted", "a", "b"}
        assert all(1800 < n < 2200 for n in data["many"][side].values()), data["many"]
    # Sides draw alone: about two thirds of matches have different commanders.
    assert 3700 < data["mixed"] < 4300
    assert data["alone"] == ["scripted", "scripted"]
