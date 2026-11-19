"""Balance sweep for the station assault: run ``station_eval.py`` on copies of the
assets with YAML overrides (the station's and bomber's numbers, the torpedo), script
against script, and print one line per variant.

    uv run python lab/runs/2026-11-19-station-bomber/tune.py --n 128 --out out/tune.jsonl

Variants are ``name: {file: {dotted.key: value}}``; ``turrets`` replaces the list.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

FLAK = "flak"
GAUSS = "gauss"


def turret(i: int, kind: str, angle_deg: float) -> dict[str, Any]:
    import math

    a = math.radians(angle_deg)
    return {
        "id": f"turret.{kind}.{i}",
        "pos": [round(16 * math.cos(a), 1), round(16 * math.sin(a), 1)],
        "rest_deg": angle_deg,
        "arc_deg": 220,
        "slew_deg_s": 90 if kind == FLAK else 120,
        "weapon": kind,
    }


def ring(kinds: list[str]) -> list[dict[str, Any]]:
    step = 360 / len(kinds)
    out = []
    count: dict[str, int] = {}
    for k, kind in enumerate(kinds):
        ang = ((k * step + 180) % 360) - 180
        out.append(turret(count.get(kind, 0), kind, ang))
        count[kind] = count.get(kind, 0) + 1
    return out


def apply(assets: Path, edits: dict[str, dict[str, Any]]) -> None:
    for file, keys in edits.items():
        path = assets / file
        if file == "weapons.yaml":
            data = yaml.safe_load(path.read_text())
        else:
            data = yaml.safe_load(path.read_text())
        for dotted, value in keys.items():
            node = data
            parts = dotted.split(".")
            for p in parts[:-1]:
                node = node[p]
            node[parts[-1]] = value
        path.write_text(yaml.safe_dump(data, sort_keys=False))


def run(name: str, edits: dict[str, dict[str, Any]], args: argparse.Namespace,
        extra: list[str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        assets = Path(tmp) / "assets"
        shutil.copytree(REPO / "assets", assets)
        apply(assets, edits)
        cmd = [sys.executable, str(HERE / "station_eval.py"), "--n", str(args.n),
               "--assets", str(assets), "--threads", str(args.threads), *extra]
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    d = json.loads(out)
    d["variant"] = name
    d["edits"] = edits
    return d


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=128)
    p.add_argument("--threads", type=int, default=8)
    p.add_argument("--variants", type=Path, required=True, help="JSON {name: edits}")
    p.add_argument("--only", nargs="*")
    p.add_argument("--out", type=Path)
    p.add_argument("extra", nargs="*", help="passed to station_eval.py after --")
    args = p.parse_args()
    variants = json.loads(args.variants.read_text())
    for name, spec in variants.items():
        if args.only and name not in args.only:
            continue
        edits = dict(spec.get("edits", {}))
        if "ring" in spec:
            edits.setdefault("hulls/station/hull.yaml", {})["turrets"] = ring(spec["ring"])
        d = run(name, edits, args, spec.get("args", []) + args.extra)
        line = (f"{name:28s} att {d['attacker_win_rate']:.3f} ± {d['attacker_win_ci95']:.3f} "
                f"len {d['length_median_s']:.0f}s "
                + " ".join(f"{k} {v:.2f}" for k, v in d["end_reasons"].items())
                + " | stn dmg " + " ".join(f"{k} {v:.0f}" for k, v in
                                           d["station_damage_by_hull_per_match"].items()))
        print(line, flush=True)
        if args.out:
            with args.out.open("a") as f:
                f.write(json.dumps(d) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
