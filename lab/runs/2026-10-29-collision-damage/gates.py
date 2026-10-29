"""Gate table of plan.md §4 from the JSONs that ``eval.sh`` writes.

    .venv/bin/python lab/runs/2026-10-29-collision-damage/gates.py [name ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parent / "eval"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def row(name: str) -> dict[str, float | bool | str]:
    script = load(EVAL / f"{name}_vs_script.json")
    champ = load(EVAL / f"{name}_vs_champ_v2.json")
    survey = load(EVAL / f"{name}_survey_vs_script.json")
    a, overall = script["side_a"], script["match"]
    fast = survey["contacts_per_match"] * survey["closing_share"][">30"]
    out: dict[str, float | bool | str] = {
        "name": name,
        "win_script": a["win_rate"],
        "win_champ_v2": champ["side_a"]["win_rate"],
        "fast_contacts": fast,
        "crash_death_matches": survey.get("matches_with_crash_death", float("nan")),
        "duty": a["main_engine_duty"],
        "outside": a["outside_share"],
        "draws": overall["draw_rate"],
        "passes": a["passes"],
        "median_ticks": overall["length_median"],
        "hit_rate": a["hit_rate"],
        "crash_hp_share": overall["crash_hp_share"],
    }
    out["G1"] = fast <= 0.3
    out["G2"] = out["win_script"] >= 0.90 and out["win_champ_v2"] > 0.5
    out["G3"] = 0.2 <= out["duty"] <= 0.95 and out["outside"] < 0.05 and out["draws"] < 0.10
    return out


def main() -> None:
    names = sys.argv[1:] or sorted(
        p.name.removesuffix("_vs_script.json") for p in EVAL.glob("*_vs_script.json")
    )
    rows = [row(n) for n in names if (EVAL / f"{n}_survey_vs_script.json").is_file()]
    if not rows:
        raise SystemExit(f"no complete evals in {EVAL}")
    keys = list(rows[0])
    print("| " + " | ".join(keys) + " |")
    print("|" + "---|" * len(keys))
    for r in rows:
        cells = [f"{v:.3f}" if isinstance(v, float) else str(v) for v in r.values()]
        print("| " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
