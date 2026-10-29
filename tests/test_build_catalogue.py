"""``tools/build_catalogue.py``: hull and weapon YAML become the catalogue JSON."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tools.build_catalogue import (
    Arc,
    CatalogueError,
    arc_name,
    build_catalogue,
    merge_arcs,
)

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def test_arcs_merge_across_the_wrap_and_absent_means_uniform() -> None:
    fighter = [
        {"from_deg": -180, "to_deg": -135, "mult": 1.5},
        {"from_deg": -135, "to_deg": -45, "mult": 1.0},
        {"from_deg": -45, "to_deg": 45, "mult": 0.5},
        {"from_deg": 45, "to_deg": 135, "mult": 1.0},
        {"from_deg": 135, "to_deg": 180, "mult": 1.5},
    ]
    merged = merge_arcs(fighter)
    assert merged[0] == Arc(135.0, -135.0, 1.5)
    assert [arc_name(a) for a in merged] == ["rear", "starboard", "nose", "port"]
    assert merge_arcs(None) == [Arc(-180.0, 180.0, 1.0)]
    assert arc_name(Arc(-180.0, 180.0, 0.75)) == "all round"


def test_real_catalogue_has_every_hull_with_derived_handling(tmp_path: Path) -> None:
    catalogue = build_catalogue(ASSETS, tmp_path)
    hulls = {h["name"]: h for h in catalogue["hulls"]}
    assert [h["name"] for h in catalogue["hulls"]] == ["fighter", "strafer", "gunship"]
    assert json.loads((tmp_path / "hulls.json").read_text()) == catalogue
    # Fighter: 900 N main on 10 kg; RCS pairs 160 N each side.
    assert hulls["fighter"]["thrust"]["forward"] == 90.0
    assert hulls["fighter"]["thrust"]["lateral"] == 32.0
    # The strafer pushes sideways harder than forward, and its note says so.
    strafer = hulls["strafer"]
    assert strafer["thrust"]["lateral"] > strafer["thrust"]["forward"]
    assert "sideways" in strafer["flying"][0]
    gunship = hulls["gunship"]
    assert any("Three turrets slew independently" in s for s in gunship["flying"])
    assert gunship["impact"] == [
        {"from_deg": -180.0, "to_deg": 180.0, "mult": 0.75, "name": "all round"}
    ]
    assert set(catalogue["weapons"]) == {"gauss", "laser", "flak"}
    assert catalogue["weapons"]["gauss"]["rate"] == 5.0


def test_a_turret_with_an_unknown_weapon_is_an_error(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    shutil.copytree(ASSETS, assets)
    hull = assets / "hulls" / "fighter" / "hull.yaml"
    hull.write_text(hull.read_text().replace("weapon: gauss", "weapon: railgun"))
    with pytest.raises(CatalogueError, match="unknown weapon"):
        build_catalogue(assets, tmp_path / "out")
