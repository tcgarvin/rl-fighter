"""Parity of the browser commander (``web/src/live/commander.js``) with ``CommanderActor``.

``tools/export_commander.py`` writes the weights; ``tools/web/commander_parity.mjs``
runs the JS forward pass and head sampling on the same features under Node. The
features are real decisions from ``rlf_sim`` (carrier battle, convoy escort, deathmatch,
both teams learned), flattened in the wasm's ``commander_features`` layout, plus copies
with every mask cleared (a head with nothing allowed allows choice 0). Masked logits
must agree to 1e-4, argmax decisions exactly (where the top two logits are not a
near-tie), no sample may take a choice its mask forbids, and sampled frequencies must
follow torch's softmax.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.commander.io import ACTION_DIM, COMMANDER_IO_VERSION, CommanderInputs
from spacefight.commander.policy import (
    CHECKPOINT_FORMAT,
    CommanderActor,
    act,
    load_commander,
    save_commander,
)
from tools.export_commander import (
    CommanderExportError,
    check_wasm_io,
    export,
    features_len,
    flat_layout,
)

REPO = Path(__file__).resolve().parents[1]
ASSETS = str(REPO / "assets")
PARITY_SCRIPT = REPO / "tools" / "web" / "commander_parity.mjs"
NODE = shutil.which("node")
# (rows, choices) of every head, in the order commander.js lays its logits out.
HEAD_SHAPES = {
    "launch": (3, 2),
    "waypoint": (1, 26),
    "squad": (20, 6),
    "order": (4, 5),
    "target": (4, 20),
    "ward": (4, 20),
    "point": (4, 25),
}
HEAD_ORDER = tuple(HEAD_SHAPES)
FEATURE_KEYS = [name for name, _, _ in flat_layout()]
SAMPLES = 40
MANY = 4000

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not on PATH")


def _checkpoint(path: Path, seed: int, scale: float | None) -> None:
    """A commander checkpoint; ``scale`` redraws every weight so logits are far from
    uniform (the default init leaves the heads near-uniform)."""
    torch.manual_seed(seed)
    actor = CommanderActor()
    if scale is not None:
        with torch.no_grad():
            for p in actor.parameters():
                p.normal_(0.0, scale)
    save_commander(path, actor, {"update": 7})


def _decisions() -> dict[str, np.ndarray]:
    """Real decision inputs from ``rlf_sim`` with both commanders learned, the
    decisions taken by a random-weight actor so squads, orders and launches change."""
    rlf_sim = pytest.importorskip("rlf_sim")
    from spacefight.eval.missions import default_rosters

    torch.manual_seed(5)
    driver = CommanderActor().eval()
    rows: dict[str, list[np.ndarray]] = {k: [] for k in FEATURE_KEYS}
    setups = [
        ("carrier_battle", default_rosters("carrier_battle")[0][1].teams),
        ("convoy_escort", default_rosters("convoy_escort")[0][1].teams),
        ("deathmatch", (("fighter", "strafer", "gunship"), ("fighter", "fighter"))),
    ]
    for mission, teams in setups:
        env = rlf_sim.VecEnv(
            ASSETS,
            2,
            [list(teams[0]), list(teams[1])],
            11,
            mission=None if mission == "deathmatch" else mission,
            commanders=["learned", "learned"],
            n_threads=1,
            max_ships=20,
        )
        taken = 0
        for _tick in range(900):
            for team in (0, 1):
                due = np.asarray(env.commander_due(team), dtype=bool)
                if not due.any():
                    continue
                ids = np.flatnonzero(due)
                feats = env.commander_features(team)
                sub = {k: np.asarray(feats[k])[ids] for k in FEATURE_KEYS}
                actions, _ = act(driver, CommanderInputs.from_numpy(sub))
                env.submit_commander_actions(
                    team, ids.astype(np.int64), actions.numpy().astype(np.int32)
                )
                if _tick % 90 < 30:
                    for k in FEATURE_KEYS:
                        rows[k].append(sub[k])
                    taken += len(ids)
            env.scripted_actions()
            env.step()
        assert taken > 0, f"no {mission} decisions"
    return {k: np.concatenate(v) for k, v in rows.items()}


def _with_cleared_masks(d: dict[str, np.ndarray], n: int) -> dict[str, np.ndarray]:
    """The first ``n`` rows again, with every mask (and launch mask) all false."""
    out = {k: np.concatenate([v, v[:n]]) for k, v in d.items()}
    for k in FEATURE_KEYS:
        if k.endswith("_mask"):
            out[k][-n:] = False
    return out


def _flat(d: dict[str, np.ndarray]) -> np.ndarray:
    b = d["globals"].shape[0]
    parts = [np.asarray(d[k], dtype=np.float32).reshape(b, -1) for k in FEATURE_KEYS]
    flat = np.concatenate(parts, axis=1)
    assert flat.shape == (b, features_len())
    return flat


def _torch_logits(actor: CommanderActor, x: CommanderInputs) -> np.ndarray:
    with torch.no_grad():
        logits = actor(x)
    b = x.batch_size
    return torch.cat(
        [getattr(logits, name).reshape(b, -1) for name in HEAD_ORDER], dim=1
    ).numpy()


def _run_js(
    export_dir: Path, flat: np.ndarray, tmp: Path, many_row: int
) -> dict[str, list[list[float]]]:
    feats, out = tmp / "features.f32", tmp / "out.json"
    flat.astype("<f4").tofile(feats)
    assert NODE is not None
    subprocess.run(
        [
            NODE,
            str(PARITY_SCRIPT),
            str(export_dir),
            str(feats),
            str(out),
            str(SAMPLES),
            str(many_row),
            str(MANY),
        ],
        check=True,
        cwd=REPO,
    )
    result: dict[str, list[list[float]]] = json.loads(out.read_text())
    return result


def _allowed(d: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Per head, ``[B, rows, choices]`` allowed choices as ``policy._masked`` reads
    them (an all-false row allows choice 0)."""
    b = d["globals"].shape[0]
    launch = np.stack([np.ones((b, 3), dtype=bool), d["launch_mask"]], axis=-1)
    heads = {
        "launch": launch,
        "waypoint": d["waypoint_mask"][:, None, :],
        "squad": d["squad_mask"],
        "order": d["order_mask"],
        "target": np.repeat(d["target_mask"][:, None, :], 4, axis=1),
        "ward": np.repeat(d["ward_mask"][:, None, :], 4, axis=1),
        "point": np.ones((b, 4, 25), dtype=bool),
    }
    for allowed in heads.values():
        allowed[..., 0] |= ~allowed.any(axis=-1)
    return heads


COLUMNS = {
    "launch": slice(0, 3),
    "waypoint": slice(3, 4),
    "squad": slice(4, 24),
    "order": slice(24, 28),
    "target": slice(28, 32),
    "ward": slice(32, 36),
    "point": slice(36, 40),
}


@pytest.fixture(scope="module")
def decisions() -> dict[str, np.ndarray]:
    return _with_cleared_masks(_decisions(), 8)


# The default init's heads are near-uniform (gain 0.01), so more of its argmaxes are
# near-ties, left out of the exact comparison.
@pytest.mark.parametrize(
    ("scale", "min_clear"),
    [(0.12, 0.9), (None, 0.6)],
    ids=["random-weights", "default-init"],
)
def test_js_commander_matches_torch_on_real_features(
    tmp_path: Path,
    decisions: dict[str, np.ndarray],
    scale: float | None,
    min_clear: float,
) -> None:
    ckpt = tmp_path / "commander.pt"
    _checkpoint(ckpt, seed=3, scale=scale)
    manifest = export(ckpt, tmp_path / "export")
    assert manifest["source"]["update"] == 7
    actor = load_commander(ckpt)[0]
    x = CommanderInputs.from_numpy(decisions)
    b = x.batch_size
    want = _torch_logits(actor, x)
    want_argmax = act(actor, x, deterministic=True)[0].numpy()
    # The carrier battle's first row: launches, waypoints and pointers all have choices.
    got = _run_js(tmp_path / "export", _flat(decisions), tmp_path, many_row=0)

    logits = np.asarray(got["logits"])
    assert logits.shape == want.shape == (b, 432)
    np.testing.assert_allclose(logits, want, atol=1e-4, rtol=0)

    # Argmax where the best choice is clear of the runner-up (torch picks the first
    # of a near-tie by float32 rounding, which JS's double sums need not reproduce).
    argmax = np.asarray(got["argmax"])
    clear = np.ones_like(argmax, dtype=bool)
    offset = 0
    for name, (rows, choices) in HEAD_SHAPES.items():
        block = want[:, offset : offset + rows * choices].reshape(b, rows, choices)
        top2 = np.sort(block, axis=-1)[..., -2:]
        clear[:, COLUMNS[name]] = (top2[..., 1] - top2[..., 0]) > 1e-3
        offset += rows * choices
    assert clear.mean() > min_clear
    np.testing.assert_array_equal(argmax[clear], want_argmax[clear])

    # No sample ever takes a choice its mask forbids.
    allowed = _allowed(decisions)
    sampled = np.asarray(got["sampled"]).reshape(b, SAMPLES, ACTION_DIM)
    assert sampled.dtype.kind == "i"
    for name, cols in COLUMNS.items():
        picks = sampled[:, :, cols]
        mask = allowed[name]
        ok = np.take_along_axis(
            np.broadcast_to(mask[:, None], (b, SAMPLES, *mask.shape[1:])),
            picks[..., None],
            axis=-1,
        )[..., 0]
        assert ok.all(), f"{name}: {np.count_nonzero(~ok)} forbidden choices sampled"
    # The rows with every mask cleared can only keep, hold and pick slot / point 0.
    cleared = sampled[-8:, :, :36]
    assert (cleared == 0).all()

    # Sampled frequencies follow torch's softmax (4000 draws: within 0.04).
    many = np.asarray(got["many"])
    with torch.no_grad():
        heads = actor(x.index(slice(0, 1)))
    for name in ("waypoint", "order", "target", "squad"):
        rows, choices = HEAD_SHAPES[name]
        probs = torch.softmax(getattr(heads, name)[0], dim=-1).reshape(rows, choices)
        probs = probs.numpy()
        for r, col in enumerate(range(COLUMNS[name].start, COLUMNS[name].stop)):
            freq = np.bincount(many[:, col], minlength=probs.shape[1]) / len(many)
            assert np.abs(freq - probs[r]).max() < 0.04, (name, r)


def test_export_records_shape_layout_and_source(tmp_path: Path) -> None:
    ckpt = tmp_path / "c.pt"
    _checkpoint(ckpt, seed=0, scale=None)
    manifest = export(ckpt, tmp_path / "out")
    assert manifest["format"] == "rlf.web_commander/1"
    assert manifest["io_version"] == COMMANDER_IO_VERSION
    assert manifest["features_len"] == 1082
    n = sum(p.numel() for p in CommanderActor().parameters())
    assert manifest["weights_floats"] == n
    assert (tmp_path / "out" / "weights.bin").stat().st_size == 4 * n
    assert len(manifest["source"]["sha256"]) == 64


def test_the_layout_agrees_with_the_built_sim() -> None:
    rlf_sim = pytest.importorskip("rlf_sim")
    io = rlf_sim.commander_io()
    flat = [(name, off, width) for name, (off, width) in io["flat_layout"].items()]
    assert flat == flat_layout()
    check_wasm_io(
        {
            "version": io["version"],
            "entity_dim": io["entity_dim"],
            "global_dim": io["global_dim"],
            "action_dim": io["action_dim"],
            "n_entities": io["n_entities"],
            "n_points": io["n_points"],
            "flat_dim": io["flat_dim"],
            "flat_layout": [list(e) for e in flat],
        }
    )


def _wasm_io() -> dict[str, object]:
    return {
        "version": COMMANDER_IO_VERSION,
        "entity_dim": 40,
        "global_dim": 53,
        "action_dim": 40,
        "n_entities": 20,
        "n_points": 25,
        "flat_dim": 1082,
        "flat_layout": [list(e) for e in flat_layout()],
    }


def test_export_refuses_a_wasm_of_another_io_version_or_layout(tmp_path: Path) -> None:
    ckpt = tmp_path / "c.pt"
    _checkpoint(ckpt, seed=0, scale=None)
    export(ckpt, tmp_path / "ok", _wasm_io())
    with pytest.raises(CommanderExportError, match="version"):
        export(
            ckpt, tmp_path / "v", {**_wasm_io(), "version": COMMANDER_IO_VERSION + 1}
        )
    moved = _wasm_io()
    moved["flat_layout"] = list(reversed(moved["flat_layout"]))  # type: ignore[call-overload]
    with pytest.raises(CommanderExportError, match="flat layout"):
        export(ckpt, tmp_path / "l", moved)


def test_export_refuses_a_checkpoint_that_is_not_a_commander_of_this_io(
    tmp_path: Path,
) -> None:
    other = tmp_path / "pilot.pt"
    torch.save({"format": "something else"}, other)
    with pytest.raises(CommanderExportError, match="not a"):
        export(other, tmp_path / "a")
    old = tmp_path / "old.pt"
    torch.save(
        {
            "format": CHECKPOINT_FORMAT,
            "io_version": COMMANDER_IO_VERSION + 1,
            "actor": CommanderActor().state_dict(),
            "meta": {},
        },
        old,
    )
    with pytest.raises(CommanderExportError, match="commander io"):
        export(old, tmp_path / "b")


CHECK_JS = """
import fs from "node:fs";
import { createCommander } from "./web/src/live/commander.js";
const dir = process.argv[1];
const m = JSON.parse(fs.readFileSync(`${dir}/manifest.json`, "utf8"));
const b = fs.readFileSync(`${dir}/weights.bin`);
const w = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const expect = { ioVersion: m.io_version, featuresLen: m.features_len, actionDim: 40, flatLayout: m.flat_layout };
const errors = [];
for (const [name, e, weights] of [
  ["ok", expect, w],
  ["io", { ...expect, ioVersion: m.io_version + 1 }, w],
  ["layout", { ...expect, flatLayout: m.flat_layout.slice().reverse() }, w],
  ["short", expect, w.slice(4)],
]) {
  try { createCommander(m, weights, e); errors.push([name, ""]); } catch (err) { errors.push([name, String(err.message)]); }
}
console.log(JSON.stringify(errors));
"""


def test_the_browser_refuses_a_commander_its_wasm_cannot_run(tmp_path: Path) -> None:
    ckpt = tmp_path / "c.pt"
    _checkpoint(ckpt, seed=0, scale=None)
    export(ckpt, tmp_path / "out")
    assert NODE is not None
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", CHECK_JS, str(tmp_path / "out")],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    errors = dict(json.loads(result.stdout))
    assert errors["ok"] == ""
    assert "commander io" in errors["io"]
    assert "flat layout" in errors["layout"]
    assert "bytes" in errors["short"]
