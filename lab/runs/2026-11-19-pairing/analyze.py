"""Tables of the pairing grid (run.sh): cell scores, the commander x pilot interaction
with paired-bootstrap errors, one pilot a side against the per-ship draw, pilot pairs
with no commander, and what the season's WAR fit predicts for the same matches. Run
from the repo root:

    PYTHONPATH=. .venv/bin/python lab/runs/2026-11-19-pairing/analyze.py \\
        [--cells lab/runs/2026-11-19-pairing/cells] [--war <war.json>] [--boot 2000]

Writes ``analysis.json`` beside ``cells/`` and prints Markdown tables. A cell's score is
side a's mean over its matches (a draw is half), the three missions weighted alike
(every cell has the same matches per mission). Every cell of a mission plays the same
seeds, rosters, sides and side-b pilots, so the bootstrap resamples match indices per
mission and applies the same resample to every cell: the errors are paired.

The interaction of commander ``c`` and pilot ``p`` is ``cell - row mean - column mean +
grand mean`` over the cells with one pilot a side (not the per-ship column). It is zero
for every cell when a pairing is worth exactly its commander's part plus its pilot's.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

HERE = Path(__file__).resolve().parent
MISSIONS = ("deathmatch", "carrier_battle", "convoy_escort")
WAR = (
    HERE.parents[1]
    / "population"
    / "2026-11-sim6"
    / "war"
    / "goto-school-2"
    / "war.json"
)
MIXED = "mixed"
ROW_ORDER = ("scripted", "unseen", "c1_shaped", "c1_outcome")


def load_cells(root: Path) -> dict[str, dict[str, dict[str, Any]]]:
    """``name -> mission -> cell`` for every cell with all three missions done."""
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for mission in MISSIONS:
        for path in sorted((root / mission).glob("*.json")):
            out.setdefault(path.stem, {})[mission] = json.loads(path.read_text())
    done = {k: v for k, v in out.items() if len(v) == len(MISSIONS)}
    return truncate(done)


PER_MATCH = ("score", "a_team", "roster", "counts", "end_reason")


def truncate(
    cells: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Every cell cut to its mission's smallest ``n``: the first matches, which have the
    same rosters, sides and side-b pilots in every cell (a block of all rosters on both
    sides repeats, and the pilot draw is made in env order)."""
    for mission in MISSIONS:
        n = min(c[mission]["n"] for c in cells.values())
        for c in cells.values():
            cell = c[mission]
            if cell["n"] > n:
                for key in PER_MATCH:
                    cell[key] = cell[key][:n]
                cell["n_played"] = cell["n"]
                cell["n"] = n
    return cells


def check_paired(cells: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> None:
    """Every cell of a mission must have the same seed, rosters and sides.

    Raises:
        ValueError: Two cells of a mission do not pair match by match.
    """
    for mission in MISSIONS:
        ref = None
        for name, cell in cells.items():
            c = cell[mission]
            key = (c["seed"], c["n"], tuple(c["roster"]), tuple(c["a_team"]))
            if ref is None:
                ref = key
            elif key != ref:
                raise ValueError(f"{mission}/{name} does not pair with the other cells")


def scores(
    cell: Mapping[str, Mapping[str, Any]], idx: Sequence[NDArray[np.int64]]
) -> float:
    """A cell's score over the resampled match indices ``idx`` (one array a mission)."""
    return float(
        np.mean([np.asarray(cell[m]["score"])[i].mean() for m, i in zip(MISSIONS, idx)])
    )


def interaction(grid: NDArray[np.float64]) -> NDArray[np.float64]:
    """``cell - row mean - column mean + grand mean`` of an [R, C] grid."""
    return (
        grid - grid.mean(axis=1, keepdims=True) - grid.mean(axis=0, keepdims=True)
    ) + grid.mean()


def sigmoid(z: NDArray[np.float64]) -> NDArray[np.float64]:
    return 1.0 / (1.0 + np.exp(-z))


def war_prediction(cell: Mapping[str, Any], war: Mapping[str, Any]) -> float:
    """Side a's mean win chance over a cell's matches as the WAR fit predicts it: the
    roster's side term (deathmatch drafts differ from WAR's, so 0), each ship's pilot
    coefficient, and each side's commander term (``unseen`` has none; it takes 0).
    """
    fit = war["fit"]
    coef = {p["pilot"]: p["coef"] for p in fit["pilots"]}
    nuisance = fit["nuisance"]
    ids = cell["pilots"]
    beta = np.array([coef.get(p, 0.0) for p in ids] + [0.0])
    counts = np.asarray(cell["counts"], dtype=np.float64)
    a_team = np.asarray(cell["a_team"])
    mission = cell["mission"]
    side = np.array(
        [nuisance.get(f"side {mission} / {r}", 0.0) for r in cell["roster"]]
    )
    side = np.where(mission == "deathmatch", 0.0, side)
    team_sign = np.where(a_team == 0, 1.0, -1.0)

    def commander(spec: str) -> float:
        name = commander_id(spec)
        return float(nuisance.get(f"commander {name} in {mission}", 0.0))

    delta = commander(cell["a_spec"]) - commander(cell["b_spec"])
    logit = team_sign * side + (counts[:, 0] - counts[:, 1]) @ beta + delta
    return float(sigmoid(logit).mean())


def commander_id(spec: str) -> str:
    """``scripted``, ``unseen`` or the live stable's id of a commander checkpoint."""
    if spec.endswith(".pt"):
        run = Path(spec).parent.parent.name
        return {"shaped": "c1_shaped", "outcome": "c1_outcome"}.get(run, run)
    return spec


def chi2_sf(x: float, df: int) -> float:
    """Upper tail of chi-squared (Wilson-Hilferty; no scipy in the venv)."""
    z = ((x / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    return 0.5 * math.erfc(z / math.sqrt(2))


def analyze(root: Path, war_path: Path, n_boot: int, seed: int) -> dict[str, Any]:
    cells = load_cells(root)
    check_paired(cells)
    n = {m: next(iter(cells.values()))[m]["n"] for m in MISSIONS}
    grid_names = {k: k.split("__")[1:] for k in cells if k.startswith("grid__")}
    rows = [r for r in ROW_ORDER if any(v[0] == r for v in grid_names.values())]
    pilots = []
    for _, p in grid_names.values():
        if p != MIXED and p not in pilots:
            pilots.append(p)
    # Only rows and columns that are complete make the grid.
    pilots = [p for p in pilots if all(f"grid__{r}__{p}" in cells for r in rows)]
    rows = [r for r in rows if all(f"grid__{r}__{p}" in cells for p in pilots)]
    pairs = [k for k in cells if k.startswith("pair__")]
    mixed = [r for r in rows if f"grid__{r}__{MIXED}" in cells]
    full = [np.arange(n[m]) for m in MISSIONS]

    def grid_of(idx: Sequence[NDArray[np.int64]]) -> NDArray[np.float64]:
        return np.array(
            [[scores(cells[f"grid__{r}__{p}"], idx) for p in pilots] for r in rows]
        )

    def extras(idx: Sequence[NDArray[np.int64]]) -> NDArray[np.float64]:
        g = grid_of(idx)
        mix = [scores(cells[f"grid__{r}__{MIXED}"], idx) for r in mixed]
        pair = [scores(cells[k], idx) for k in pairs]
        return np.concatenate([g.ravel(), interaction(g).ravel(), mix, pair])

    observed = extras(full)
    rng = np.random.default_rng(seed)
    boot = np.stack(
        [extras([rng.integers(0, n[m], n[m]) for m in MISSIONS]) for _ in range(n_boot)]
    )
    se = boot.std(axis=0, ddof=1)
    k = len(rows) * len(pilots)
    g, g_se = observed[:k].reshape(len(rows), -1), se[:k].reshape(len(rows), -1)
    inter = observed[k : 2 * k].reshape(len(rows), -1)
    inter_se = se[k : 2 * k].reshape(len(rows), -1)
    boot_grid = boot[:, :k].reshape(n_boot, len(rows), -1)
    row_mean_boot = boot_grid.mean(axis=2)
    col_mean_boot = boot_grid.mean(axis=1)
    mix_obs = observed[2 * k : 2 * k + len(mixed)]
    mix_boot = boot[:, 2 * k : 2 * k + len(mixed)]
    pair_obs = observed[2 * k + len(mixed) :]
    pair_se = se[2 * k + len(mixed) :]
    # The whole grid's interaction against its noise: a sum of squared z-scores.
    stat = float(((inter / inter_se) ** 2).sum())
    df = (len(rows) - 1) * (len(pilots) - 1)
    # The interaction's spread beyond noise: sd of observed minus the noise's share.
    noise_var = float((inter_se**2).mean())
    excess_sd = math.sqrt(max(0.0, float((inter**2).mean()) - noise_var))
    war = json.loads(war_path.read_text()) if war_path.is_file() else None
    out: dict[str, Any] = {
        "schema": "rlf.pairing.analysis/1",
        "sim_version": next(iter(cells.values()))["deathmatch"]["sim_version"],
        "n_per_mission": n,
        "n_boot": n_boot,
        "rows": rows,
        "pilots": pilots,
        "grid": g.tolist(),
        "grid_se": g_se.tolist(),
        "row_mean": g.mean(axis=1).tolist(),
        "row_mean_se": row_mean_boot.std(axis=0, ddof=1).tolist(),
        "col_mean": g.mean(axis=0).tolist(),
        "col_mean_se": col_mean_boot.std(axis=0, ddof=1).tolist(),
        "grand_mean": float(g.mean()),
        "interaction": inter.tolist(),
        "interaction_se": inter_se.tolist(),
        "interaction_chi2": stat,
        "interaction_df": df,
        "interaction_p": chi2_sf(stat, df) if df else 1.0,
        "interaction_rms": math.sqrt(float((inter**2).mean())),
        "interaction_noise_rms": math.sqrt(noise_var),
        "interaction_excess_sd": excess_sd,
        "mixed": {
            r: {
                "score": float(mix_obs[i]),
                "se": float(mix_boot[:, i].std(ddof=1)),
                "minus_row_mean": float(mix_obs[i] - g[rows.index(r)].mean()),
                "minus_row_mean_se": float(
                    (mix_boot[:, i] - row_mean_boot[:, rows.index(r)]).std(ddof=1)
                ),
            }
            for i, r in enumerate(mixed)
        },
        "pairs": {
            k: {"score_a": float(pair_obs[i]), "se": float(pair_se[i])}
            for i, k in enumerate(pairs)
        },
        "by_mission": {
            m: [
                [float(np.mean(cells[f"grid__{r}__{p}"][m]["score"])) for p in pilots]
                for r in rows
            ]
            for m in MISSIONS
        },
        "secs": {m: float(sum(c[m]["secs"] for c in cells.values())) for m in MISSIONS},
    }
    if war is not None:
        out["war"] = str(war_path.relative_to(HERE.parents[2]))
        war_rows = [r for r in rows if r != "unseen"]
        pred = np.array(
            [
                [
                    np.mean(
                        [
                            war_prediction(cells[f"grid__{r}__{p}"][m], war)
                            for m in MISSIONS
                        ]
                    )
                    for p in pilots
                ]
                for r in war_rows
            ]
        )
        out["war_rows"] = war_rows
        out["war_grid"] = pred.tolist()
        out["war_interaction"] = interaction(pred).tolist()
        out["war_col_mean"] = pred.mean(axis=0).tolist()
        out["war_mixed"] = {
            r: float(
                np.mean(
                    [
                        war_prediction(cells[f"grid__{r}__{MIXED}"][m], war)
                        for m in MISSIONS
                    ]
                )
            )
            for r in mixed
            if r != "unseen"
        }
        for k in pairs:
            out["pairs"][k]["war"] = float(
                np.mean([war_prediction(cells[k][m], war) for m in MISSIONS])
            )
    return out


def signed(x: float) -> str:
    return f"{x:+.3f}".replace("-", "−")


def tables(a: Mapping[str, Any]) -> str:
    """The Markdown tables of an analysis."""
    rows, pilots = a["rows"], a["pilots"]
    lines = [
        "| Commander \\ pilot | "
        + " | ".join(f"`{p}`" for p in pilots)
        + " | Row mean | Per-ship draw |",
        "|---" * (len(pilots) + 3) + "|",
    ]
    for i, r in enumerate(rows):
        cells = [
            f"{a['grid'][i][j]:.3f} ({signed(a['interaction'][i][j])})"
            for j in range(len(pilots))
        ]
        mix = a["mixed"].get(r)
        mixed = f"{mix['score']:.3f}" if mix else ""
        lines.append(
            f"| `{r}` | " + " | ".join(cells) + f" | {a['row_mean'][i]:.3f} | {mixed} |"
        )
    lines.append(
        "| Column mean | "
        + " | ".join(f"{x:.3f}" for x in a["col_mean"])
        + f" | {a['grand_mean']:.3f} | |"
    )
    se = np.asarray(a["grid_se"])
    ise = np.asarray(a["interaction_se"])
    lines += [
        "",
        f"Cell ± (1.96 SE): {1.96 * se.min():.3f} to {1.96 * se.max():.3f}. "
        f"Interaction ± (1.96 SE): {1.96 * ise.min():.3f} to {1.96 * ise.max():.3f}. "
        f"Row mean ±: {1.96 * max(a['row_mean_se']):.3f}; "
        f"column mean ±: {1.96 * max(a['col_mean_se']):.3f}.",
        "",
        f"Interaction over the grid: rms {a['interaction_rms']:.3f} against "
        f"{a['interaction_noise_rms']:.3f} from noise alone; sum of squared z "
        f"{a['interaction_chi2']:.1f} on {a['interaction_df']} df, p ≈ "
        f"{a['interaction_p']:.2f}; spread beyond noise ≈ "
        f"{a['interaction_excess_sd']:.3f}.",
        "",
        "| Commander | Per-ship draw | Minus its row mean (one pilot a side) |",
        "|---|---|---|",
    ]
    for r, m in a["mixed"].items():
        lines.append(
            f"| `{r}` | {m['score']:.3f} ± {1.96 * m['se']:.3f} | "
            f"{signed(m['minus_row_mean'])} ± {1.96 * m['minus_row_mean_se']:.3f} |"
        )
    lines += ["", "| Mission | " + " | ".join(f"`{r}`" for r in rows) + " |"]
    lines.append("|---" * (len(rows) + 1) + "|")
    for m, g in a["by_mission"].items():
        lines.append(
            f"| {m} | " + " | ".join(f"{np.mean(row):.3f}" for row in g) + " |"
        )
    if "war_grid" in a:
        lines += [
            "",
            "WAR's prediction (" + a["war"] + "), same matches:",
            "",
            "| Commander \\ pilot | "
            + " | ".join(f"`{p}`" for p in pilots)
            + " | Per-ship draw |",
            "|---" * (len(pilots) + 2) + "|",
        ]
        for i, r in enumerate(a["war_rows"]):
            cells = [
                f"{a['war_grid'][i][j]:.3f} ({signed(a['war_interaction'][i][j])})"
                for j in range(len(pilots))
            ]
            mix = a["war_mixed"].get(r)
            lines.append(
                f"| `{r}` | " + " | ".join(cells) + f" | {mix:.3f} |"
                if mix is not None
                else f"| `{r}` | " + " | ".join(cells) + " | |"
            )
    lines += [
        "",
        "| Pilot pair (no commander), a v b | a's score | WAR predicts |",
        "|---|---|---|",
    ]
    for k, p in a["pairs"].items():
        _, pa, pb = k.split("__")
        war = f"{p['war']:.3f}" if "war" in p else ""
        lines.append(
            f"| `{pa}` v `{pb}` | {p['score_a']:.3f} ± {1.96 * p['se']:.3f} | {war} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--cells", type=Path, default=HERE / "cells")
    p.add_argument("--war", type=Path, default=WAR)
    p.add_argument("--boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20261119)
    p.add_argument("--out", type=Path, default=HERE / "analysis.json")
    args = p.parse_args(argv)
    a = analyze(args.cells, args.war, args.boot, args.seed)
    args.out.write_text(json.dumps(a, indent=1) + "\n")
    print(tables(a))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
