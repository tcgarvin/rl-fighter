"""Print the results.md tables from out/*.json (station_eval.py, swap_eval.py)."""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"


def load(name: str) -> dict | None:
    path = OUT / f"{name}.json"
    return json.loads(path.read_text()) if path.is_file() else None


def reasons(d: dict) -> str:
    short = {
        "station_destroyed": "station",
        "assault_repelled": "repelled",
        "time_limit": "clock",
        "eliminated": "elim",
        "carrier_destroyed": "carrier",
    }
    return ", ".join(f"{short.get(k, k)} {v:.2f}" for k, v in d.items())


def station_table(rows: list[tuple[str, str]]) -> None:
    print(
        "| Run | Attacker win | End reasons | Median s | p90 s | Station damage per match "
        "(bomber / gunship / fighter / strafer / carrier) |"
    )
    print("|---|---|---|---|---|---|")
    for label, name in rows:
        d = load(name)
        if d is None:
            continue
        s = d["station_damage_by_hull_per_match"]
        dmg = " / ".join(
            f"{s.get(h, 0):.0f}"
            for h in ("bomber", "gunship", "fighter", "strafer", "carrier")
        )
        print(
            f"| {label} | {d['attacker_win_rate']:.3f} ± {d['attacker_win_ci95']:.3f} | "
            f"{reasons(d['end_reasons'])} | {d['length_median_s']:.0f} | "
            f"{d['length_p90_s']:.0f} | {dmg} |"
        )


def survival_table(rows: list[tuple[str, str]]) -> None:
    print(
        "| Run | Attacker survival (bomber / fighter / gunship / carrier) | "
        "Defender survival (fighter / strafer / gunship) | Bomber damage per ship: "
        "capital / strike craft |"
    )
    print("|---|---|---|---|")
    for label, name in rows:
        d = load(name)
        if d is None:
            continue
        a, f = d["survival"]["attacker"], d["survival"]["defender"]
        dd = d["damage_dealt_per_ship"]["attacker"]
        cap = dd["bomber_vs_capital"]
        print(
            f"| {label} | {a['bomber']:.2f} / {a['fighter']:.2f} / {a['gunship']:.2f} / "
            f"{a['carrier']:.2f} | {f['fighter']:.2f} / {f['strafer']:.2f} / "
            f"{f['gunship']:.2f} | {cap:.0f} / {dd['bomber'] - cap:.0f} |"
        )


def swap_table(rows: list[tuple[str, str]]) -> None:
    print(
        "| Mission | Pilots | n | Side X with gunship | with bomber | Delta (paired) | "
        "Swapped slot's damage, gunship: capital / strike | bomber: capital / strike |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for label, name in rows:
        d = load(name)
        if d is None:
            continue
        b, s = d["base"], d["swap"]
        print(
            f"| {label} | {d['pilots'].split('/')[-1]} | {d['n']} | {b['x_score']:.3f} | "
            f"{s['x_score']:.3f} | {d['delta']:+.3f} ± {d['delta_ci95']:.3f} | "
            f"{b['slot_damage_to_capital']:.0f} / {b['slot_damage_to_strike']:.0f} | "
            f"{s['slot_damage_to_capital']:.0f} / {s['slot_damage_to_strike']:.0f} |"
        )


def main() -> None:
    station = [
        ("script v script, as carrier", "balance_script_carrier"),
        ("script v script, as convoy", "balance_script_convoy"),
        ("live pilots, as carrier", "pilots_carrier"),
        ("live pilots, as convoy", "pilots_convoy"),
        ("live pilots, attacker unseen", "pilots_carrier_attacker_unseen"),
        ("live pilots, defender unseen", "pilots_carrier_defender_unseen"),
    ]
    station_table(station)
    print()
    survival_table(station)
    print()
    swap_table(
        [
            ("3 v 3 deathmatch", "swap_dm_script"),
            ("carrier battle", "swap_carrier_script"),
            ("3 v 3 deathmatch", "swap_dm_pilots"),
            ("carrier battle", "swap_carrier_pilots"),
        ]
    )


if __name__ == "__main__":
    main()
