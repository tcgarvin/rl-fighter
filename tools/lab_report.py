"""Fill a learnability-spike ``results.md`` from the eval JSONs and PPO logs.

Plan ``lab/runs/2026-10-28-learnability-spike/plan.md`` §1 (criteria and verdict
rules), §6.2 (matrix) and §6.4 (results template). Reads, under ``--run-dir``:

- ``eval/<a>[_argmax]_vs_<b>.json``: ``DuelResult`` JSONs (``rlf.eval.duel/1``),
  written by ``tools/spike_eval_matrix.py``; the ``_argmax`` files have both sides
  take the argmax action. Missing files become "—" cells.
- ``ppo_bc/log.jsonl``, ``ppo_scratch/log.jsonl`` (and their ``config.yaml``): the
  per-update PPO logs (``spacefight.rl.spike_ppo.LOG_KEYS``), partial logs allowed.
- ``bc/bc_eval.json``, ``bc_dagger/dagger_eval.json`` for the "What we did" section.

Writes ``results.md`` and ``learning_curves.csv``. Sections the coordinator writes
by hand sit between ``<!-- hand:NAME -->`` and ``<!-- /hand:NAME -->`` markers and
are carried over when the report is regenerated.

    python -m tools.lab_report --run-dir lab/runs/2026-10-28-learnability-spike
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from spacefight.eval.duel import MARKDOWN_HEADER, DuelResult, SideMetrics

# ---------------------------------------------------------------------------
# Policies and the eval matrix (shared with tools/spike_eval_matrix.py)
# ---------------------------------------------------------------------------

SCRIPT = "script"
BC = "bc"
BC_DAGGER = "bc_dagger"
PPO_BC_FINAL = "ppo_bc_final"
PPO_BC_BEST = "ppo_bc_best"
PPO_BC_400 = "ppo_bc_400"
PPO_BC_800 = "ppo_bc_800"
PPO_SCRATCH_FINAL = "ppo_scratch_final"

# Which §1 column a policy is judged against.
COLUMN_BC = "bc"
COLUMN_PPO = "ppo"


@dataclass(frozen=True)
class PolicySpec:
    """One policy of the matrix: file-name key, table label and §1 column."""

    name: str
    label: str
    column: str


POLICIES: tuple[PolicySpec, ...] = (
    PolicySpec(BC, "BC", COLUMN_BC),
    PolicySpec(BC_DAGGER, "BC + DAgger", COLUMN_BC),
    PolicySpec(PPO_BC_FINAL, "PPO-BC final", COLUMN_PPO),
    PolicySpec(PPO_BC_BEST, "PPO-BC best", COLUMN_PPO),
    PolicySpec(PPO_BC_400, "PPO-BC 400", COLUMN_PPO),
    PolicySpec(PPO_BC_800, "PPO-BC 800", COLUMN_PPO),
    PolicySpec(PPO_SCRATCH_FINAL, "PPO-scratch final", COLUMN_PPO),
)
LABELS: dict[str, str] = {p.name: p.label for p in POLICIES} | {SCRIPT: "script"}

# The PPO-BC checkpoints the matrix evaluates at fixed updates (plan §6.2's
# 500/1000/1500 scaled to the 1200-update run).
FIXED_PPO_BC_UPDATES: dict[str, int] = {PPO_BC_400: 400, PPO_BC_800: 800}
EXTRA_OPPONENTS: tuple[tuple[str, str], ...] = (
    (PPO_BC_FINAL, BC_DAGGER),
    (PPO_BC_FINAL, PPO_BC_400),
    (PPO_BC_FINAL, PPO_BC_800),
    (PPO_SCRATCH_FINAL, PPO_BC_FINAL),
)


@dataclass(frozen=True)
class Pairing:
    """One eval of the matrix; ``argmax`` applies to both sides."""

    a: str
    b: str
    argmax: bool

    @property
    def stem(self) -> str:
        """File stem under ``eval/`` (matches the baseline files' naming)."""
        mode = "_argmax" if self.argmax else ""
        return f"{self.a}{mode}_vs_{self.b}"

    @property
    def label(self) -> str:
        """Human label, e.g. ``PPO-BC final (argmax) vs script``."""
        mode = " (argmax)" if self.argmax else ""
        return f"{LABELS[self.a]}{mode} vs {LABELS[self.b]}"


def matrix_pairings() -> list[Pairing]:
    """Every pairing of the adapted §6.2 matrix, in table order.

    The script is deterministic, so script vs script has no argmax row.
    """
    pairs = [Pairing(SCRIPT, SCRIPT, False)]
    for policy in POLICIES:
        pairs += [
            Pairing(policy.name, SCRIPT, False),
            Pairing(policy.name, SCRIPT, True),
        ]
    for a, b in EXTRA_OPPONENTS:
        pairs += [Pairing(a, b, False), Pairing(a, b, True)]
    return pairs


# ---------------------------------------------------------------------------
# PPO logs and the best checkpoint
# ---------------------------------------------------------------------------

SMOOTH_WINDOW = 50


def read_log(path: Path) -> list[dict[str, Any]]:
    """Rows of a ``log.jsonl``; a missing file gives no rows.

    A truncated last line (the trainer is appending) is dropped; any other bad
    line raises.

    Raises:
        ValueError: A line other than the last is not JSON.
    """
    if not path.is_file():
        return []
    lines = path.read_text().splitlines()
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            if i == len(lines) - 1:
                break
            raise ValueError(f"{path}:{i + 1}: not JSON") from exc
    return rows


def smoothed_win(
    rows: Sequence[Mapping[str, Any]], update: int, window: int = SMOOTH_WINDOW
) -> float | None:
    """Episode-weighted mean rollout ``vs_scripted_win`` over updates
    ``(update - window, update]``; ``None`` when no episode vs the script finished
    in the window.
    """
    wins = 0.0
    episodes = 0
    for row in rows:
        u = int(row["update"])
        n = int(row["vs_scripted_episodes"])
        if update - window < u <= update and n > 0:
            wins += float(row["vs_scripted_win"]) * n
            episodes += n
    return wins / episodes if episodes else None


@dataclass(frozen=True)
class BestCheckpoint:
    """The checkpoint update with the highest smoothed rollout win rate."""

    update: int
    smoothed_win: float


def checkpoint_updates(
    rows: Sequence[Mapping[str, Any]], every: int, n_updates: int
) -> list[int]:
    """Updates with a checkpoint among the logged ones: every ``every`` and the last
    (``n_updates``)."""
    logged = {int(row["update"]) for row in rows}
    return sorted(u for u in logged if u % every == 0 or u == n_updates)


def best_checkpoint(
    rows: Sequence[Mapping[str, Any]],
    candidates: Iterable[int],
    window: int = SMOOTH_WINDOW,
) -> BestCheckpoint:
    """Pick the candidate update with the highest ``smoothed_win`` (earliest on ties).

    Raises:
        ValueError: No candidate has a smoothed win rate.
    """
    best: BestCheckpoint | None = None
    for update in sorted(candidates):
        win = smoothed_win(rows, update, window)
        if win is not None and (best is None or win > best.smoothed_win):
            best = BestCheckpoint(update, win)
    if best is None:
        raise ValueError("no candidate checkpoint has rollout episodes vs the script")
    return best


@dataclass(frozen=True)
class RunLog:
    """One PPO run's config and log rows."""

    name: str
    config: dict[str, Any]
    rows: list[dict[str, Any]]

    @property
    def last_update(self) -> int:
        """Highest logged update (0 before the first)."""
        return max((int(r["update"]) for r in self.rows), default=0)

    @property
    def finished(self) -> bool:
        """The log reached the configured ``n_updates``."""
        return bool(self.config) and self.last_update >= int(self.config["n_updates"])

    def best(self) -> BestCheckpoint | None:
        """Best checkpoint so far, ``None`` before any scored checkpoint."""
        if not self.config:
            return None
        candidates = checkpoint_updates(
            self.rows,
            int(self.config["checkpoint_every"]),
            int(self.config["n_updates"]),
        )
        try:
            return best_checkpoint(self.rows, candidates)
        except ValueError:
            return None


def load_run(run_dir: Path, name: str) -> RunLog:
    """Config and log of ``run_dir/name`` (empty when the run has not started)."""
    config_path = run_dir / name / "config.yaml"
    config = yaml.safe_load(config_path.read_text()) if config_path.is_file() else {}
    return RunLog(name, config or {}, read_log(run_dir / name / "log.jsonl"))


# ---------------------------------------------------------------------------
# §1 criteria and the verdict
# ---------------------------------------------------------------------------

METRICS: tuple[tuple[str, str], ...] = (
    ("win", "win rate"),
    ("draw", "draw rate"),
    ("engagement", "engagement"),
    ("hit", "hit rate"),
    ("outside", "outside arena"),
    ("kill", "kill endings"),
    ("duty", "engine duty"),
)
WATCHABILITY = ("engagement", "hit", "outside", "kill")


@dataclass(frozen=True)
class Rule:
    """One §1 cell: ``kind`` "min", "max", "band" or "report" (no threshold).

    ``of_script`` scales ``low`` (and ``high``) by the script's value of the metric.
    """

    kind: str
    low: float = 0.0
    high: float = 0.0
    of_script: bool = False

    def check(self, value: float, script: float | None) -> bool | None:
        """Pass/fail of ``value``; ``None`` for "report" rules or a missing script
        reference."""
        if self.kind == "report":
            return None
        scale = 1.0
        if self.of_script:
            if script is None:
                return None
            scale = script
        low, high = self.low * scale, self.high * scale
        if self.kind == "min":
            return value >= low
        if self.kind == "max":
            return value <= low
        if self.kind == "band":
            return low <= value <= high
        raise ValueError(f"unknown rule kind {self.kind!r}")

    def describe(self) -> str:
        """Short threshold text for the table header."""
        unit = " × script" if self.of_script else ""
        if self.kind == "min":
            return f"≥ {self.low:g}{unit}"
        if self.kind == "max":
            return f"≤ {self.low:g}{unit}"
        if self.kind == "band":
            return f"{self.low:g}–{self.high:g}{unit}"
        return "report"


COLUMNS: dict[str, dict[str, Rule]] = {
    COLUMN_BC: {
        "win": Rule("min", 0.35),
        "draw": Rule("max", 0.15),
        "engagement": Rule("min", 0.5, of_script=True),
        "hit": Rule("min", 0.5, of_script=True),
        "outside": Rule("max", 0.02),
        "kill": Rule("min", 0.8),
        "duty": Rule("report"),
    },
    COLUMN_PPO: {
        "win": Rule("min", 0.60),
        "draw": Rule("max", 0.10),
        "engagement": Rule("min", 0.4),
        "hit": Rule("min", 0.6, of_script=True),
        "outside": Rule("max", 0.02),
        "kill": Rule("min", 0.9),
        "duty": Rule("band", 0.2, 0.95),
    },
}
STRONG: dict[str, Rule] = {
    "win": Rule("min", 0.75),
    "draw": Rule("max", 0.10),
    "engagement": Rule("min", 0.5),
    "hit": Rule("min", 1.0, of_script=True),
    "outside": Rule("max", 0.01),
    "kill": Rule("min", 0.95),
    "duty": Rule("band", 0.2, 0.95),
}
H2_MARGIN = 0.15


def metric_values(result: DuelResult) -> dict[str, float]:
    """The §1 metrics of side "a" of ``result``."""
    s: SideMetrics = result.side_a
    return {
        "win": s.win_rate,
        "draw": result.match.draw_rate,
        "engagement": s.engagement_rate,
        "hit": s.hit_rate,
        "outside": s.outside_share,
        "kill": result.match.kill_rate,
        "duty": s.main_engine_duty,
    }


def script_reference(results: Mapping[str, DuelResult]) -> dict[str, float]:
    """Script-vs-script side-a metrics (the "× script" denominators); empty if the
    baseline is missing."""
    base = results.get(Pairing(SCRIPT, SCRIPT, False).stem)
    return metric_values(base) if base is not None else {}


def check_cells(
    result: DuelResult, rules: Mapping[str, Rule], script: Mapping[str, float]
) -> dict[str, bool | None]:
    """Pass/fail per metric (``None`` where the rule reports only or lacks a
    reference)."""
    values = metric_values(result)
    return {key: rules[key].check(values[key], script.get(key)) for key, _ in METRICS}


def meets(
    cells: Mapping[str, bool | None],
    rules: Mapping[str, Rule],
    keys: Iterable[str] | None = None,
) -> bool:
    """Every cell of ``keys`` (default all) passed; "report" cells always count as
    met, a threshold cell without its script reference does not."""
    chosen = list(keys) if keys is not None else list(cells)
    return all(cells[k] is True or rules[k].kind == "report" for k in chosen)


@dataclass(frozen=True)
class Verdict:
    """The §1 verdict and the hypothesis statements, with the reasons."""

    level: str  # PASS, PARTIAL, FAIL or PENDING
    reasons: list[str]
    hypotheses: list[str]


def _vs_script(results: Mapping[str, DuelResult], name: str) -> DuelResult | None:
    return results.get(Pairing(name, SCRIPT, False).stem)


def compute_verdict(results: Mapping[str, DuelResult]) -> Verdict:
    """Apply the §1 verdict rules to the stochastic vs-script results.

    "BC" is the PPO-BC init, BC + DAgger; "BC + PPO" is PPO-BC final for PASS, and
    any evaluated PPO-BC checkpoint for "PPO wins" / "PPO never above 0.5".
    """
    script = script_reference(results)
    bc = _vs_script(results, BC_DAGGER)
    final = _vs_script(results, PPO_BC_FINAL)
    hypotheses = _hypotheses(results, script)
    if not script or bc is None or final is None:
        needed = [(SCRIPT, bool(script)), (BC_DAGGER, bc is not None)]
        needed.append((PPO_BC_FINAL, final is not None))
        missing = [Pairing(n, SCRIPT, False).stem for n, have in needed if not have]
        return Verdict("PENDING", [f"missing {', '.join(missing)}"], hypotheses)

    reasons: list[str] = []
    bc_cells = check_cells(bc, COLUMNS[COLUMN_BC], script)
    bc_ok = meets(bc_cells, COLUMNS[COLUMN_BC])
    bc_failed = [k for k, ok in bc_cells.items() if ok is False]
    reasons.append(
        "BC + DAgger reaches the BC column"
        if bc_ok
        else f"BC + DAgger misses the BC column on {', '.join(bc_failed)}"
    )
    final_cells = check_cells(final, COLUMNS[COLUMN_PPO], script)
    if meets(final_cells, COLUMNS[COLUMN_PPO]):
        reasons.append("PPO-BC final reaches every pass cell")
        return Verdict("PASS", reasons, hypotheses)
    final_failed = [k for k, ok in final_cells.items() if ok is not True]
    reasons.append(f"PPO-BC final misses pass cells: {', '.join(final_failed)}")

    winners = []
    for name in (PPO_BC_FINAL, PPO_BC_BEST, PPO_BC_400, PPO_BC_800):
        res = _vs_script(results, name)
        if res is not None and res.side_a.win_rate > 0.5:
            cells = check_cells(res, COLUMNS[COLUMN_PPO], script)
            winners.append((name, meets(cells, COLUMNS[COLUMN_PPO], WATCHABILITY)))
    unwatchable = [name for name, watchable in winners if not watchable]
    if unwatchable:
        reasons.append(
            f"PPO wins (> 0.5) but fails a watchability row: {', '.join(unwatchable)}"
        )
    elif not winners:
        reasons.append("no evaluated PPO-BC checkpoint is above 0.5 vs the script")
    if bc_ok or unwatchable:
        return Verdict("PARTIAL", reasons, hypotheses)
    return Verdict("FAIL", reasons, hypotheses)


def _hypotheses(
    results: Mapping[str, DuelResult], script: Mapping[str, float]
) -> list[str]:
    bc = _vs_script(results, BC_DAGGER)
    final = _vs_script(results, PPO_BC_FINAL)
    scratch = _vs_script(results, PPO_SCRATCH_FINAL)
    out = []
    if bc is None or final is None or not script:
        out.append("**H1** pending (needs BC + DAgger, PPO-BC final and the baseline).")
    else:
        bc_ok = meets(check_cells(bc, COLUMNS[COLUMN_BC], script), COLUMNS[COLUMN_BC])
        beats = final.side_a.win_rate > 0.5
        holds = "holds" if bc_ok and beats else "does not hold"
        out.append(
            f"**H1** {holds}: BC + DAgger {'reaches' if bc_ok else 'misses'} the BC "
            f"column (win {bc.side_a.win_rate:.3f}); PPO-BC final "
            f"{'beats' if beats else 'does not beat'} the script "
            f"(win {final.side_a.win_rate:.3f})."
        )
    if final is None or scratch is None:
        out.append("**H2** pending (needs PPO-BC final and PPO-scratch final).")
    else:
        lead = final.side_a.win_rate - scratch.side_a.win_rate
        holds = "holds" if lead >= H2_MARGIN else "does not hold"
        out.append(
            f"**H2** {holds}: BC + PPO leads scratch by {lead:+.3f} win rate vs the "
            f"script at equal updates (rule: ≥ {H2_MARGIN})."
        )
    learned = [
        (LABELS[p.name], res.side_a.win_rate)
        for p in POLICIES
        if (res := _vs_script(results, p.name)) is not None
    ]
    if final is None or scratch is None:
        out.append("**H0** pending (needs PPO-BC final and PPO-scratch final).")
    else:
        top_label, top_win = max(learned, key=lambda item: item[1])
        holds = "holds" if top_win <= 0.5 else "is rejected"
        out.append(
            f"**H0** {holds}: best learned policy vs the script is {top_label} at "
            f"{top_win:.3f} (sampled)."
        )
    return out


# ---------------------------------------------------------------------------
# Loading and rendering
# ---------------------------------------------------------------------------

DASH = "—"


def load_results(eval_dir: Path) -> dict[str, DuelResult]:
    """Every ``eval/*.json`` that parses as a ``DuelResult``, keyed by file stem.

    Raises:
        ValueError: A JSON file in ``eval_dir`` is not a valid ``DuelResult``
            (other than ``matrix.json``, the matrix manifest).
    """
    out: dict[str, DuelResult] = {}
    for path in sorted(eval_dir.glob("*.json")):
        if path.name == MANIFEST_NAME:
            continue
        try:
            out[path.stem] = DuelResult.from_json(path.read_text())
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"{path}: not a DuelResult JSON") from exc
    return out


MANIFEST_NAME = "matrix.json"


def _fmt(key: str, value: float) -> str:
    return f"{value:.4f}" if key == "outside" else f"{value:.3f}"


def criteria_table(results: Mapping[str, DuelResult], argmax: bool = False) -> str:
    """The §1 table: one row per policy, cells marked ✓/✗ against its column
    (BC column for BC and BC + DAgger, pass column for the PPO policies)."""
    script = script_reference(results)
    head = "| policy | column | " + " | ".join(t for _, t in METRICS) + " | strong |"
    lines = [head, "|" + "---|" * (len(METRICS) + 3)]
    base = results.get(Pairing(SCRIPT, SCRIPT, False).stem)
    if base is not None and not argmax:
        values = metric_values(base)
        cells = [_fmt(k, values[k]) for k, _ in METRICS]
        lines.append("| script (baseline) | — | " + " | ".join(cells) + " | — |")
    for policy in POLICIES:
        res = results.get(Pairing(policy.name, SCRIPT, argmax).stem)
        label = policy.label + (" (argmax)" if argmax else "")
        column = "BC" if policy.column == COLUMN_BC else "pass"
        if res is None:
            lines.append(
                f"| {label} | {column} | "
                + " | ".join(DASH for _ in METRICS)
                + " | — |"
            )
            continue
        values = metric_values(res)
        checks = check_cells(res, COLUMNS[policy.column], script)
        cells = [f"{_fmt(k, values[k])} {_mark(checks[k])}".strip() for k, _ in METRICS]
        strong = DASH
        if policy.column == COLUMN_PPO:
            strong_cells = check_cells(res, STRONG, script)
            strong = "yes" if meets(strong_cells, STRONG) else "no"
        lines.append(f"| {label} | {column} | " + " | ".join(cells) + f" | {strong} |")
    return "\n".join(lines)


def thresholds_table() -> str:
    """The §1 thresholds, for reading the marks."""
    lines = ["| column | " + " | ".join(t for _, t in METRICS) + " |"]
    lines.append("|" + "---|" * (len(METRICS) + 1))
    for name, rules in (("BC", COLUMNS[COLUMN_BC]), ("pass", COLUMNS[COLUMN_PPO])):
        lines.append(
            f"| {name} | " + " | ".join(rules[k].describe() for k, _ in METRICS) + " |"
        )
    lines.append(
        "| strong | " + " | ".join(STRONG[k].describe() for k, _ in METRICS) + " |"
    )
    return "\n".join(lines)


def _mark(ok: bool | None) -> str:
    return "✓" if ok is True else "✗" if ok is False else ""


def matrix_table(results: Mapping[str, DuelResult]) -> str:
    """Every matrix pairing as a ``DuelResult.markdown_row`` (side a), "—" if not
    run."""
    width = MARKDOWN_HEADER.splitlines()[0].count("|") - 1
    lines = [MARKDOWN_HEADER]
    for pair in matrix_pairings():
        res = results.get(pair.stem)
        a_label = LABELS[pair.a] + (" (argmax)" if pair.argmax else "")
        if res is None:
            row = [a_label, LABELS[pair.b]] + [DASH] * (width - 2)
            lines.append("| " + " | ".join(row) + " |")
        else:
            lines.append(replace(res, a=a_label, b=LABELS[pair.b]).markdown_row("a"))
    return "\n".join(lines)


def health_lines(results: Mapping[str, DuelResult]) -> list[str]:
    """One line per eval with ``nan_or_stuck`` matches (empty when healthy)."""
    bad = []
    for stem, res in sorted(results.items()):
        if res.side_a.nan_or_stuck or res.side_b.nan_or_stuck:
            bad.append(
                f"{stem}: nan_or_stuck a={res.side_a.nan_or_stuck} "
                f"b={res.side_b.nan_or_stuck}"
            )
    return bad


ENTROPY_KEYS = (
    "entropy_throttle",
    "entropy_slew",
    "entropy_fire",
    "entropy_power",
    "entropy_mean",
)
CURVE_FIELDS = (
    "run",
    "update",
    "samples_cum",
    "vs_scripted_win",
    "vs_scripted_episodes",
    "vs_scripted_win_smoothed",
) + ENTROPY_KEYS


def curve_rows(run: RunLog) -> list[dict[str, Any]]:
    """Learning-curve rows of one run (rollout win vs the script, smoothed over
    ``SMOOTH_WINDOW`` updates, and entropy per head group)."""
    out = []
    samples = 0
    for row in sorted(run.rows, key=lambda r: int(r["update"])):
        samples += int(row["samples"])
        update = int(row["update"])
        out.append(
            {
                "run": run.name,
                "update": update,
                "samples_cum": samples,
                "vs_scripted_win": row["vs_scripted_win"],
                "vs_scripted_episodes": row["vs_scripted_episodes"],
                "vs_scripted_win_smoothed": smoothed_win(run.rows, update),
            }
            | {key: row[key] for key in ENTROPY_KEYS}
        )
    return out


def write_curves_csv(path: Path, runs: Sequence[RunLog]) -> None:
    """Both runs' ``curve_rows`` as one CSV (empty cells for nulls)."""
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CURVE_FIELDS)
        writer.writeheader()
        for run in runs:
            for row in curve_rows(run):
                writer.writerow({k: "" if v is None else v for k, v in row.items()})


def curve_table(runs: Sequence[RunLog], every: int = 100) -> str:
    """Smoothed rollout win and entropies at every ``every`` updates, both runs."""
    head = "| update | run | samples | win vs script (50-upd) | H throttle | H fire | H power | H mean |"
    lines = [head, "|---|---|---|---|---|---|---|---|"]
    for run in runs:
        for row in curve_rows(run):
            if row["update"] % every:
                continue
            cells = [
                _opt(row[key])
                for key in (
                    "vs_scripted_win_smoothed",
                    "entropy_throttle",
                    "entropy_fire",
                    "entropy_power",
                    "entropy_mean",
                )
            ]
            lines.append(
                f"| {row['update']} | {run.name} | {row['samples_cum']:,} | "
                + " | ".join(cells)
                + " |"
            )
    return "\n".join(lines)


def _opt(value: float | None) -> str:
    return DASH if value is None else f"{value:.3f}"


def numbers_lines(runs: Sequence[RunLog]) -> list[str]:
    """Compute used per PPO run: updates, samples, wall time, throughput."""
    out = []
    for run in runs:
        if not run.rows:
            out.append(f"- `{run.name}`: no log yet.")
            continue
        samples = sum(int(r["samples"]) for r in run.rows)
        wall = sum(float(r["update_seconds"]) for r in run.rows)
        target = run.config.get("n_updates", "?")
        out.append(
            f"- `{run.name}`: {run.last_update} / {target} updates, "
            f"{samples:,} learner samples, {wall / 3600:.2f} h of update time "
            f"({wall / max(run.last_update, 1):.2f} s/update, "
            f"{samples / wall:,.0f} samples/s), threads "
            f"{run.config.get('sim_threads')} sim + {run.config.get('torch_threads')} torch."
        )
    return out


# ---------------------------------------------------------------------------
# results.md
# ---------------------------------------------------------------------------

HAND_RE = re.compile(r"<!-- hand:([\w-]+) -->(.*?)<!-- /hand:\1 -->", re.DOTALL)
HAND_DEFAULTS = {
    "title": "TODO(coordinator): a title that states the finding",
    "asked": (
        "TODO(coordinator): two sentences for a visitor: can a small MLP learn to "
        "fly, aim and fire a fighter by driving its thrusters and trigger directly, "
        "in one night on a laptop CPU?"
    ),
    "looked-like": (
        "TODO(coordinator): two or three observations from render_state replays: "
        "does it lead its shots, does it turn to re-engage, what does it do at the "
        "edge. Do not fill from the numbers alone."
    ),
    "learned": "TODO(coordinator): bullets on which of H1/H2/H0 held, and surprises.",
    "next": (
        "TODO(coordinator): the one experiment this result argues for; backlog "
        "items added."
    ),
}


def hand(name: str, previous: Mapping[str, str]) -> str:
    """A hand-written block, carried over from the previous ``results.md``."""
    body = previous.get(name, HAND_DEFAULTS[name])
    return f"<!-- hand:{name} -->{body}<!-- /hand:{name} -->"


def previous_hand_blocks(path: Path) -> dict[str, str]:
    """Hand blocks of an existing ``results.md`` (empty if there is none)."""
    if not path.is_file():
        return {}
    return {m.group(1): m.group(2) for m in HAND_RE.finditer(path.read_text())}


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout
    return out.strip()


def _read_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.is_file() else None


def what_we_did(run_dir: Path, runs: Sequence[RunLog]) -> list[str]:
    """Facts about the stages from their own outputs."""
    out = [
        "- **Balance (pre-gate, plan §2):** gauss 5 dmg / 0.20 s / 220 m / 200 m/s / "
        "1.0°, fighter 80 hp, plus the scripted pilot extending after a merge; every "
        "tried tuple and the before/after sweep is in "
        "`lab/runs/2026-10-28-sim-v2/results.md`.",
    ]
    bc_eval = _read_json(run_dir / "bc" / "bc_eval.json")
    if bc_eval is not None:
        groups = bc_eval["groups"]
        agreement = ", ".join(
            f"{name} {g['agreement']:.3f}"
            for name, g in groups.items()
            if g.get("agreement") is not None
        )
        fire = groups["fire"]
        out.append(
            f"- **BC:** {bc_eval['collect']['rows']:,} DART rows (p = "
            f"{bc_eval['setup']['dart_p']}); held-out agreement {agreement}; fire "
            f"precision {fire['precision']:.3f} / recall {fire['recall']:.3f}."
        )
    dagger = _read_json(run_dir / "bc_dagger" / "dagger_eval.json")
    if dagger is not None:
        per_round = "; ".join(
            f"r{r['round']} {r['duel']['sample']['summary']['win_rate']:.3f}"
            for r in dagger["rounds"]
        )
        out.append(
            f"- **DAgger:** {dagger['config']['rounds']} rounds × "
            f"{dagger['config']['rows_per_round']:,} on-policy rows labelled by the "
            f"script; sampled win rate vs the script per round: {per_round}; best "
            f"round {dagger['best_round']} → `bc_dagger/best.pt` (PPO-BC's init)."
        )
    for run in runs:
        if not run.config:
            out.append(f"- **{run.name}:** not started.")
            continue
        c = run.config
        out.append(
            f"- **{run.name}:** init `{c['init']}`, {c['n_updates']} updates of "
            f"{c['n_envs']} × {c['n_steps']}, actor LR {c['actor_lr']}, β "
            f"{c['beta_start']} → {c['beta_end']} over {c['beta_decay_start']}–"
            f"{c['beta_decay_end']}, critic warm-up {c['critic_warmup_updates']}, "
            f"opponent bands `{c['opponent_bands']}`."
        )
    return out


DEVIATIONS = """\
- **Ran interactively in the evening**, not on the 03:00 night schedule of §5.
- **DAgger added** between BC and PPO (not in the plan): BC alone won 0.6 % vs the
  script (compounding error off the expert's state distribution), so three DAgger
  rounds of 2 M on-policy rows each were run on top of `bc/bc.pt`; round 3 (sampled
  win 0.154) is `bc_dagger/best.pt` and the PPO-BC init. The verdict's "BC" stage is
  BC + DAgger; plain BC is still reported.
- **1200 PPO updates instead of 2000** for both runs, per the §7 throughput row:
  thermal throttling, ~2.8 s/update measured with one run alone. The comparison
  stays at equal updates.
- **Opponent bands scaled × 0.6** to the shorter run:
  `[[0,1,0,0],[360,0.5,0.3,0.2],[720,0.3,0.4,0.3]]`.
- **β decay end 420** (700 × 0.6) for PPO-BC.
- **Engine-duty band top 0.95** instead of 0.9 (the script runs at 0.85; changed
  before any learned policy was evaluated, §1).
- **Thread split:** both PPO runs concurrently at 6 sim + 6 torch threads.
- **Matrix adapted (§6.2):** PPO-BC at 400 / 800 instead of 500 / 1000 / 1500;
  PPO-BC final also plays BC + DAgger (its init) instead of BC; the best checkpoint
  is the 100-update checkpoint with the highest rollout `vs_scripted_win`
  (episode-weighted over the 50 updates up to it)."""


def render(run_dir: Path, previous: Mapping[str, str], curves_note: str) -> str:
    """The full ``results.md`` text."""
    results = load_results(run_dir / "eval")
    runs = [load_run(run_dir, "ppo_bc"), load_run(run_dir, "ppo_scratch")]
    verdict = compute_verdict(results)
    script = results.get(Pairing(SCRIPT, SCRIPT, False).stem)
    sim_version = script.config.sim_version if script is not None else "?"
    best = runs[0].best()
    best_line = (
        f"PPO-BC best checkpoint so far: update {best.update} (rollout win vs the "
        f"script {best.smoothed_win:.3f}, 50-update smoothed)."
        if best is not None
        else "PPO-BC best checkpoint: none scored yet."
    )
    status = [
        f"`{r.name}` {r.last_update}/{r.config.get('n_updates', '?')}"
        + ("" if r.finished else " (unfinished)")
        for r in runs
    ]
    health = health_lines(results)
    health_text = (
        "No NaNs or stuck ships in any eval."
        if not health
        else "**Health failures:**\n\n" + "\n".join(f"- {h}" for h in health)
    )
    parts = [
        f"# {hand('title', previous)}",
        "",
        f"Date {run_dir.name[:10]} · run dir `{run_dir.name}` · branch `{_git('branch', '--show-current')}` "
        f"· commit `{_git('rev-parse', '--short', 'HEAD')}` (report) · SIM_VERSION "
        f"{sim_version} · verdict: **{verdict.level}**",
        "",
        f"Training: {', '.join(status)}. Evals present: {len(results)} of "
        f"{len(matrix_pairings())} matrix pairings.",
        "",
        "## What we asked",
        "",
        hand("asked", previous),
        "",
        "## What we did",
        "",
        *what_we_did(run_dir, runs),
        "",
        "### Deviations from plan",
        "",
        DEVIATIONS,
        "",
        "## Results",
        "",
        "### Verdict",
        "",
        f"**{verdict.level}**. " + "; ".join(verdict.reasons) + ".",
        "",
        *[f"- {h}" for h in verdict.hypotheses],
        "",
        best_line,
        "",
        "### §1 criteria (sampled actions, n = 512 vs the script, sides swapped)",
        "",
        "✓/✗ against the policy's column (BC for BC and BC + DAgger, pass for the "
        "PPO policies); 'strong' = every strong cell met; '—' = not evaluated yet.",
        "",
        criteria_table(results),
        "",
        "Argmax rows (second row per §6.1, not used for the verdict):",
        "",
        criteria_table(results, argmax=True),
        "",
        thresholds_table(),
        "",
        "### Eval matrix",
        "",
        "Side a's numbers; '(argmax)' rows have both sides take the argmax.",
        "",
        matrix_table(results),
        "",
        health_text,
        "",
        "### Learning curves",
        "",
        curves_note,
        "",
        curve_table(runs),
        "",
        "## What it looked like",
        "",
        hand("looked-like", previous),
        "",
        "## What we learned",
        "",
        hand("learned", previous),
        "",
        "## Next",
        "",
        hand("next", previous),
        "",
        "## Numbers",
        "",
        *numbers_lines(runs),
        "",
    ]
    return "\n".join(parts)


def write_report(run_dir: Path, out: Path) -> Path:
    """Write ``out`` (``results.md``) and ``learning_curves.csv`` next to it."""
    runs = [load_run(run_dir, "ppo_bc"), load_run(run_dir, "ppo_scratch")]
    csv_path = out.parent / "learning_curves.csv"
    write_curves_csv(csv_path, runs)
    note = (
        f"matplotlib is not installed in the venv, so no PNGs: the per-update "
        f"curves (rollout win vs the script, raw and {SMOOTH_WINDOW}-update "
        f"smoothed, and entropy per head group, both runs) are in "
        f"`{csv_path.name}`. Every 100 updates:"
    )
    text = render(run_dir, previous_hand_blocks(out), note)
    out.write_text(text)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--out", type=Path, default=None, help="default <run-dir>/results.md"
    )
    args = parser.parse_args(argv)
    out = write_report(args.run_dir, args.out or args.run_dir / "results.md")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
