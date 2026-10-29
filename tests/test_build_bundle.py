"""``tools/build_bundle.py``: the live page's bundle manifest and catalogue."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.build_bundle import SCHEMA, BundleError, build

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "assets"


def _fake_bundle(
    root: Path, fleets: list[list[str]], weights: bytes = b"w" * 16
) -> Path:
    """A bundle directory with stand-in wasm and policy files, as build_bundle.sh leaves it."""
    bundle = root / "bundle"
    (bundle / "pkg").mkdir(parents=True)
    (bundle / "policy").mkdir()
    (bundle / "pkg/sim_wasm_bg.wasm").write_bytes(b"\0asm-fake")
    (bundle / "pkg/sim_wasm.js").write_text("export {}")
    (bundle / "policy/weights.bin").write_bytes(weights)
    policy = {
        "format": "rlf.web_policy/1",
        "sim_version": 3,
        "match_config": {
            "fleets": fleets,
            "arena_radius": 450.0,
            "time_limit_ticks": 2700,
            "reaction_ticks": 2,
        },
        "source": {
            "checkpoint": "/x/ppo_bc_600.pt",
            "sha256": "ab" * 32,
            "update": 600,
        },
        "eval": {
            "file": str(REPO / "lab/runs/r/eval/e.json"),
            "a": "policy:ppo_bc_600.pt",
            "b": "script",
            "n": 512,
            "sim_version": 3,
            "wins": 500,
            "draws": 2,
            "losses": 10,
            "win_rate": 0.98,
            "hit_rate": 0.7,
            "length_median_ticks": 300.0,
        },
    }
    (bundle / "policy/manifest.json").write_text(json.dumps(policy))
    return bundle


def test_manifest_certifies_the_training_hulls_and_defaults_the_budget(
    tmp_path: Path,
) -> None:
    bundle = _fake_bundle(tmp_path, [["fighter"], ["fighter"]])
    manifest = build(bundle, "2026-10-29-collision-damage", ASSETS, REPO)
    assert manifest["schema"] == SCHEMA
    assert manifest["champion"]["hulls"] == ["fighter"]
    assert manifest["champion"]["run"] == "2026-10-29-collision-damage"
    assert manifest["champion"]["id"] == "2026-10-29-collision-damage/ppo_bc_600"
    assert manifest["champion"]["eval"]["file"] == "lab/runs/r/eval/e.json"
    assert manifest["match"] == {
        "arena_radius": 450.0,
        "time_limit_ticks": 2700,
        "reaction_ticks": 2,
    }
    # Four fighters (cost 10) a side at most.
    assert manifest["roster"] == {
        "hulls": ["fighter"],
        "min_per_side": 1,
        "max_per_side": 4,
        "budget": 40,
    }
    on_disk = json.loads((bundle / "manifest.json").read_text())
    assert on_disk == manifest


def test_catalogue_carries_every_hull_and_the_card_info(tmp_path: Path) -> None:
    bundle = _fake_bundle(tmp_path, [["fighter"], ["fighter"]])
    build(bundle, "run", ASSETS, REPO)
    catalogue = json.loads((bundle / "catalogue.json").read_text())
    names = [name for name, _ in catalogue["hulls"]]
    assert names == sorted(names) and {"fighter", "strafer", "gunship"} <= set(names)
    assert catalogue["info"]["gunship"]["shield"] > 0
    assert catalogue["info"]["fighter"] == {
        "role": "fighter",
        "cost": 10,
        "hp": 80.0,
        "shield": 0.0,
    }
    assert "gauss" in catalogue["weapons"]


def test_bundle_id_is_stable_for_the_same_inputs_and_changes_with_the_weights(
    tmp_path: Path,
) -> None:
    first = build(
        _fake_bundle(tmp_path / "a", [["fighter"], ["fighter"]]), "run", ASSETS, REPO
    )
    again = build(
        _fake_bundle(tmp_path / "b", [["fighter"], ["fighter"]]), "run", ASSETS, REPO
    )
    other = build(
        _fake_bundle(tmp_path / "c", [["fighter"], ["fighter"]], weights=b"v" * 16),
        "run",
        ASSETS,
        REPO,
    )
    assert first["bundle_id"] == again["bundle_id"]
    assert other["bundle_id"] != first["bundle_id"]


def test_mixed_training_fleets_certify_every_hull_they_used(tmp_path: Path) -> None:
    bundle = _fake_bundle(tmp_path, [["fighter", "gunship"], ["strafer"]])
    manifest = build(bundle, "run", ASSETS, REPO)
    assert manifest["champion"]["hulls"] == ["fighter", "gunship", "strafer"]
    assert manifest["roster"]["hulls"] == ["fighter", "gunship", "strafer"]


def test_unknown_certified_hull_is_refused(tmp_path: Path) -> None:
    bundle = _fake_bundle(tmp_path, [["fighter"], ["fighter"]])
    with pytest.raises(BundleError, match="not in the catalogue"):
        build(bundle, "run", ASSETS, REPO, hulls=["fighter", "dreadnought"])


def test_roster_sizes_beyond_the_ship_cap_are_refused(tmp_path: Path) -> None:
    bundle = _fake_bundle(tmp_path, [["fighter"], ["fighter"]])
    with pytest.raises(BundleError, match="max_per_side"):
        build(bundle, "run", ASSETS, REPO, max_per_side=5)


def test_a_budget_too_small_for_one_ship_is_refused(tmp_path: Path) -> None:
    bundle = _fake_bundle(tmp_path, [["fighter"], ["fighter"]])
    with pytest.raises(BundleError, match="budget"):
        build(bundle, "run", ASSETS, REPO, budget=5)


def test_missing_policy_export_is_reported(tmp_path: Path) -> None:
    bundle = _fake_bundle(tmp_path, [["fighter"], ["fighter"]])
    (bundle / "policy/weights.bin").unlink()
    with pytest.raises(BundleError, match="weights.bin"):
        build(bundle, "run", ASSETS, REPO)
