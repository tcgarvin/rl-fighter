"""Build the ``/hulls/`` catalogue data from ``assets/hulls/*/hull.yaml`` and weapons.

Writes ``<out>/hulls.json`` so the browser never parses YAML. The hull schema and
conventions are SIM_SPEC §4.1: body frame +x forward, +y port, bearings in degrees
CCW from +x, thruster ``dir`` is the direction the force pushes the ship. Each hull
also gets numbers derived from that data (accelerations, turn rate, the merged
armour and impact arcs) and a short "how it is flown" note built from them; the
role and control-scheme lines come from DESIGN §5's starting-catalogue table.

    python -m tools.build_catalogue [--assets assets] [--out web/public/hulls/data]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "rlf.catalogue/1"
GITHUB_BLOB = "https://github.com/tcgarvin/rl-fighter/blob/main"

# DESIGN §5, "Starting catalogue": (role, control scheme) per hull.
DESIGN_ROLES: dict[str, tuple[str, str]] = {
    "fighter": ("Dogfighter", "Main engine and four RCS thrusters, fixed nose gun"),
    "strafer": (
        "Skirmisher; circle-strafes",
        "Lateral thruster pairs plus a weak main engine",
    ),
    "gunship": ("Anchor, anti-fighter", "Slow hull with independent turrets"),
}
WEAPON_NAMES = {"gauss": "gauss gun"}
WEAPON_KINDS = {
    "bullet": "slug",
    "beam": "beam",
    "flak": "flak burst",
    "torpedo": "torpedo",
}


class CatalogueError(ValueError):
    """A hull or weapon file the catalogue cannot use, with the path in the message."""


@dataclass(frozen=True)
class Arc:
    """A bearing arc ``[from_deg, to_deg)`` with a damage multiplier."""

    from_deg: float
    to_deg: float
    mult: float


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise CatalogueError(f"{path}: not valid YAML ({exc})") from exc


def _require(data: Mapping[str, Any], keys: Sequence[str], where: Path) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise CatalogueError(f"{where}: missing {', '.join(missing)}")


def merge_arcs(raw: Sequence[Mapping[str, Any]] | None) -> list[Arc]:
    """Arcs in order, with neighbours of equal multiplier joined across ±180°.

    An absent or empty list is uniform 1× (SIM_SPEC §4.1). A merged arc that wraps
    keeps ``from_deg > to_deg`` (e.g. 135 → -135 for the fighter's engine arc).
    """
    if not raw:
        return [Arc(-180.0, 180.0, 1.0)]
    arcs = [
        Arc(float(a["from_deg"]), float(a["to_deg"]), float(a["mult"])) for a in raw
    ]
    merged: list[Arc] = []
    for arc in arcs:
        if merged and merged[-1].mult == arc.mult and merged[-1].to_deg == arc.from_deg:
            merged[-1] = Arc(merged[-1].from_deg, arc.to_deg, arc.mult)
        else:
            merged.append(arc)
    if len(merged) > 1 and merged[0].mult == merged[-1].mult:
        merged[0] = Arc(merged[-1].from_deg, merged[0].to_deg, merged[0].mult)
        merged.pop()
    return merged


def arc_name(arc: Arc) -> str:
    """Where an arc points: nose, rear, port, starboard, or all round."""
    span = (arc.to_deg - arc.from_deg) % 360 or 360.0
    if span >= 359.0:
        return "all round"
    centre = math.degrees(
        math.atan2(
            math.sin(math.radians(arc.from_deg + span / 2)),
            math.cos(math.radians(arc.from_deg + span / 2)),
        )
    )
    if span > 180:
        return "rest of hull"
    if abs(centre) <= 45:
        return "nose"
    if abs(centre) >= 135:
        return "rear"
    return "port" if centre > 0 else "starboard"


def thrust_numbers(hull: Mapping[str, Any]) -> dict[str, float]:
    """Accelerations from the thrusters at full throttle and an even power split.

    Forward/reverse/lateral are m/s²; ``turn`` is the smaller of the two directions'
    angular accelerations in deg/s² (torque about the centre of mass at the origin).
    """
    mass = float(hull["mass"])
    inertia = float(hull["inertia"])
    forward = reverse = port = starboard = ccw = cw = 0.0
    for t in hull.get("thrusters") or []:
        fx = float(t["dir"][0]) * float(t["max_force"])
        fy = float(t["dir"][1]) * float(t["max_force"])
        x, y = float(t["pos"][0]), float(t["pos"][1])
        forward += max(0.0, fx)
        reverse += max(0.0, -fx)
        port += max(0.0, fy)
        starboard += max(0.0, -fy)
        torque = x * fy - y * fx
        ccw += max(0.0, torque)
        cw += max(0.0, -torque)
    return {
        "forward": round(forward / mass, 1),
        "reverse": round(reverse / mass, 1),
        "lateral": round(min(port, starboard) / mass, 1),
        "turn": round(math.degrees(min(ccw, cw) / inertia), 1),
    }


def _weapon_entry(name: str, w: Mapping[str, Any]) -> dict[str, Any]:
    interval = float(w["interval"])
    return {
        "name": name,
        "kind": str(w["kind"]),
        "kind_label": WEAPON_KINDS.get(str(w["kind"]), str(w["kind"])),
        "damage": float(w["damage"]),
        "range": float(w["range"]),
        "speed": float(w["speed"]),
        "interval": interval,
        "rate": round(1.0 / interval, 2),
        "dps": round(float(w["damage"]) / interval, 1),
        "spread_deg": float(w.get("spread_deg", 0.0)),
        "burst_radius": float(w.get("burst_radius", 0.0)),
    }


def load_weapons(path: Path) -> dict[str, dict[str, Any]]:
    """``assets/weapons.yaml`` as ``{name: entry}`` with rate and DPS added."""
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise CatalogueError(f"{path}: expected a mapping of weapons")
    out = {}
    for name, w in data.items():
        _require(w, ("kind", "speed", "range", "damage", "interval"), path)
        if float(w["interval"]) <= 0:
            raise CatalogueError(f"{path}: {name}.interval must be > 0")
        out[str(name)] = _weapon_entry(str(name), w)
    return out


def _join(items: Sequence[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _count(n: int, word: str) -> str:
    names = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
    return f"{names.get(n, str(n))} {word}{'' if n == 1 else 's'}"


def flying_notes(hull: Mapping[str, Any], thrust: Mapping[str, float]) -> list[str]:
    """Sentences on how the hull is flown, each one read straight off the data."""
    notes = []
    mains = [t for t in hull["thrusters"] if float(t["dir"][0]) > 0.5]
    side = [t for t in hull["thrusters"] if abs(float(t["dir"][1])) > 0.5]
    main_word = (
        "main engine" if len(mains) == 1 else f"{_count(len(mains), 'main engine')}"
    )
    if thrust["lateral"] > thrust["forward"]:
        notes.append(
            f"It moves sideways harder than it moves forward: its lateral thruster "
            f"pairs give {thrust['lateral']:g} m/s² to either side, the weak "
            f"{main_word} {thrust['forward']:g} m/s² ahead. Firing a front and a rear "
            f"thruster on opposite sides turns it, at up to {thrust['turn']:.0f}°/s²."
        )
    else:
        notes.append(
            f"The {main_word} push{'es' if len(mains) == 1 else ''} it ahead at "
            f"{thrust['forward']:g} m/s²; {_count(len(side), 'side thruster')} give "
            f"{thrust['lateral']:g} m/s² to either side and turn it at up to "
            f"{thrust['turn']:.0f}°/s²."
        )
    notes.append(
        f"Speed is soft-capped at {float(hull['speed_cap']):g} m/s with an even power "
        f"split, and higher with power shifted to the engines."
    )
    fixed = [t for t in hull["turrets"] if float(t["arc_deg"]) == 0]
    turning = [t for t in hull["turrets"] if float(t["arc_deg"]) > 0]
    if fixed and not turning:
        weapons = _join(
            sorted(
                {WEAPON_NAMES.get(str(t["weapon"]), str(t["weapon"])) for t in fixed}
            )
        )
        notes.append(
            f"The {weapons} is fixed to the nose, so aiming means pointing the whole ship."
        )
    if turning:
        parts = [
            f"{str(t['id']).split('.')[-1]} {t['weapon']} ({float(t['arc_deg']):g}° arc, "
            f"{float(t['slew_deg_s']):g}°/s)"
            for t in turning
        ]
        notes.append(
            f"{_count(len(turning), 'turret').capitalize()} slew independently of the "
            f"hull: {_join(parts)}. Each is aimed on its own, so the guns can track "
            f"while the hull points elsewhere."
        )
    shield = hull.get("shield")
    if shield:
        notes.append(
            f"A {float(shield['hp']):g} hp shield takes hits first and recharges at "
            f"{float(shield['regen_rate']):g} hp/s after {float(shield['regen_delay']):g} s "
            f"without a hit."
        )
    return notes


def build_hull(path: Path, weapons: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """One hull's catalogue entry from its ``hull.yaml``.

    Raises:
        CatalogueError: a required field is missing or a turret names an unknown weapon.
    """
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise CatalogueError(f"{path}: expected a mapping")
    _require(
        data,
        ("name", "role", "hp", "mass", "inertia", "speed_cap", "cost", "collision"),
        path,
    )
    data.setdefault("thrusters", [])
    data.setdefault("turrets", [])
    for turret in data["turrets"]:
        if turret["weapon"] not in weapons:
            raise CatalogueError(f"{path}: turret {turret['id']} uses unknown weapon")
    name = str(data["name"])
    thrust = thrust_numbers(data)
    role, scheme = DESIGN_ROLES.get(name, (str(data["role"]).capitalize(), ""))
    bound = max(
        math.hypot(float(c["pos"][0]), float(c["pos"][1])) + float(c["r"])
        for c in data["collision"]
    )
    shield = data.get("shield")
    return {
        "name": name,
        "role": str(data["role"]),
        "role_label": role,
        "control_scheme": scheme,
        "flying": flying_notes(data, thrust),
        "hp": float(data["hp"]),
        "shield": (
            None
            if not shield
            else {
                k: float(shield[k])
                for k in ("hp", "regen_rate", "regen_delay", "radius")
            }
        ),
        "mass": float(data["mass"]),
        "inertia": float(data["inertia"]),
        "speed_cap": float(data["speed_cap"]),
        "cost": float(data["cost"]),
        "static": bool(data.get("static", False)),
        "bound_radius": round(bound, 2),
        "thrust": thrust,
        "armour": [
            arc.__dict__ | {"name": arc_name(arc)}
            for arc in merge_arcs(data.get("armour"))
        ],
        "impact": [
            arc.__dict__ | {"name": arc_name(arc)}
            for arc in merge_arcs(data.get("impact"))
        ],
        "collision": [
            {"pos": [float(v) for v in c["pos"]], "r": float(c["r"])}
            for c in data["collision"]
        ],
        "thrusters": [
            {
                "id": str(t["id"]),
                "pos": [float(v) for v in t["pos"]],
                "dir": [float(v) for v in t["dir"]],
                "max_force": float(t["max_force"]),
            }
            for t in data["thrusters"]
        ],
        "turrets": [
            {
                "id": str(t["id"]),
                "pos": [float(v) for v in t["pos"]],
                "rest_deg": float(t["rest_deg"]),
                "arc_deg": float(t["arc_deg"]),
                "slew_deg_s": float(t["slew_deg_s"]),
                "weapon": str(t["weapon"]),
            }
            for t in data["turrets"]
        ],
        "source": f"{GITHUB_BLOB}/assets/hulls/{path.parent.name}/hull.yaml",
    }


def build_catalogue(assets: Path, out_dir: Path) -> dict[str, Any]:
    """Write ``hulls.json`` (hulls cheapest and lightest first) and return it."""
    weapons = load_weapons(assets / "weapons.yaml")
    paths = sorted((assets / "hulls").glob("*/hull.yaml"))
    if not paths:
        raise CatalogueError(f"{assets / 'hulls'}: no hull.yaml files")
    hulls = [build_hull(p, weapons) for p in paths]
    hulls.sort(key=lambda h: (h["cost"], h["mass"], h["name"]))
    used = {t["weapon"] for h in hulls for t in h["turrets"]}
    catalogue = {
        "schema": SCHEMA,
        "hulls": hulls,
        "weapons": {k: v for k, v in weapons.items() if k in used},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hulls.json").write_text(
        json.dumps(catalogue, ensure_ascii=False, indent=1)
    )
    return catalogue


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--assets", type=Path, default=REPO_ROOT / "assets")
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "web" / "public" / "hulls" / "data"
    )
    args = parser.parse_args(argv)
    catalogue = build_catalogue(args.assets, args.out)
    names = ", ".join(h["name"] for h in catalogue["hulls"])
    print(
        f"wrote {len(catalogue['hulls'])} hulls ({names}) to {args.out / 'hulls.json'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
