"""Build the ``/notebook/`` data (DESIGN §10, M2_PLAN §3) from ``lab/runs/*``.

Writes ``<out>/index.json`` (every run, newest first) and ``<out>/<run-id>.json``
(one entry: rendered write-up and plan, learning-curve series, eval artefacts). The
notebook page (``web/src/notebook/``) fetches them at runtime.

Each run directory is read as it is; the formats differ between runs:

- ``results.md``: the H1 is the title. Verdict (PASS / PARTIAL / FAIL, or
  "shipped") and SIM_VERSION come from the text before the first H2 (a
  ``verdict: **PASS**`` line or a ``| Verdict | ... |`` row). A
  ``<!-- summary: ... -->`` comment sets the index summary; otherwise it is the
  first sentence of "What we asked", or of the first section.
- ``plan.md``: rendered as the entry's plan section; the title if results are absent.
- ``*/log.jsonl``: per-update PPO logs, one arm per directory; binned to at most
  ``MAX_POINTS`` points per series.
- ``**/*.json``: eval artefacts (duel results, contact surveys, BC/DAgger evals).
- ``lab/champions/*/champion.json``: promoted pilots (may be absent).

    python -m tools.build_notebook [--runs lab/runs] [--champions lab/champions]
        [--out web/public/notebook/data]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.lab_markdown import (
    GITHUB_BLOB,
    GITHUB_TREE,
    LinkContext,
    plain_text,
    render_markdown,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_SCHEMA = "rlf.notebook.index/1"
RUN_SCHEMA = "rlf.notebook.run/1"
MAX_POINTS = 300
WIN_SMOOTHING_UPDATES = 50
TICKS_PER_SECOND = 30.0
VERDICTS = ("PASS", "PARTIAL", "FAIL")
SHIPPED = "shipped"
CHAMPION_FIELDS = ("id", "name", "run", "sim_version", "hulls", "promoted", "eval")

_RUN_ID = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9][a-z0-9-]*$")
_H2_SPLIT = re.compile(r"^##\s+(.+?)\s*$", re.M)
_SUMMARY = re.compile(r"<!--\s*summary:\s*(.*?)\s*-->", re.S)
_VERDICT_LINE = re.compile(r"verdict\W{0,6}(PASS|PARTIAL|FAIL)\b", re.I)
_VERDICT_ROW = re.compile(
    r"^\|\s*verdict\s*\|[^|\n]*?\b(PASS|PARTIAL|FAIL)\b", re.I | re.M
)
_SHIPPED = re.compile(r"\bshipped\b", re.I)
_SIM_VERSION_TEXT = re.compile(r"SIM_VERSION\W{0,4}(\d+)|\bsim v(\d+)\b", re.I)
_SENTENCE_END = re.compile(r"(?<=[.?!])\s+(?=[A-Z0-9*`(])")


class NotebookError(ValueError):
    """A lab file the notebook cannot read, with the path in the message."""


@dataclass(frozen=True)
class Metric:
    """One learning-curve chart: a ``log.jsonl`` key, optionally episode-weighted."""

    id: str
    title: str
    key: str
    weight_key: str | None
    y_min: float | None
    y_max: float | None
    format: str  # "pct" | "num"
    smooth: bool


METRICS: tuple[Metric, ...] = (
    Metric("win_vs_script", "Win rate vs the script", "vs_scripted_win",
           "vs_scripted_episodes", 0.0, 1.0, "pct", True),
    Metric("reward", "Mean reward per step", "reward_mean", None, None, None, "num", False),
    Metric("entropy", "Policy entropy, mean over heads (nats)", "entropy_mean", None,
           0.0, None, "num", False),
    Metric("hit_rate", "Hit rate (hits / shots)", "hit_rate", "shots", 0.0, 1.0, "pct", False),
)  # fmt: skip


# ---------------------------------------------------------------------------
# Small readers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise NotebookError(f"{path}: not valid JSON ({exc})") from exc


def _rel(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _github(path: Path, repo_root: Path) -> str:
    base = GITHUB_TREE if path.is_dir() else GITHUB_BLOB
    return f"{base}/{_rel(path, repo_root)}"


def git_first_commit_time(path: Path) -> int | None:
    """Unix time of the commit that added ``path``; ``None`` if it is not committed.

    Raises:
        NotebookError: git is missing or ``path`` is not inside a git checkout.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%ct", "--", path.name],
            cwd=path.parent,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise NotebookError(f"git log failed for {path}: {exc}") from exc
    stamps = result.stdout.split()
    return int(stamps[-1]) if stamps else None


# ---------------------------------------------------------------------------
# results.md metadata
# ---------------------------------------------------------------------------


def _sections(md: str) -> tuple[str, dict[str, str]]:
    """Split Markdown into the text before the first H2 and ``{h2 title: body}``."""
    parts = _H2_SPLIT.split(md)
    header = parts[0]
    sections = {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    return header, sections


def parse_verdict(md: str) -> str | None:
    """PASS / PARTIAL / FAIL from the header, ``"shipped"`` if it says so, else ``None``."""
    header, _ = _sections(md)
    for pattern in (_VERDICT_ROW, _VERDICT_LINE):
        match = pattern.search(header)
        if match is not None:
            return match.group(1).upper()
    if _SHIPPED.search(header):
        return SHIPPED
    return None


def parse_sim_version_text(md: str) -> int | None:
    """The first ``SIM_VERSION n`` / ``sim vN`` in the document, if any."""
    match = _SIM_VERSION_TEXT.search(md)
    if match is None:
        return None
    return int(match.group(1) or match.group(2))


def _first_sentences(text: str, min_chars: int = 50, max_chars: int = 260) -> str:
    sentences = _SENTENCE_END.split(text.strip())
    out = ""
    for sentence in sentences:
        candidate = f"{out} {sentence}".strip()
        if out and len(candidate) > max_chars:
            break
        out = candidate
        if len(out) >= min_chars:
            break
    return out


def _first_block(section_md: str) -> str:
    """The first paragraph or list item of a section, as Markdown."""
    for block in re.split(r"\n\s*\n", section_md.strip()):
        block = block.strip()
        if not block or block.startswith(("|", "#", "```")):
            continue
        first_item = re.split(r"\n\s*[-*]\s+", "\n" + block)
        lines = [s for s in first_item if s.strip()]
        return lines[0] if lines else block
    return ""


def parse_summary(md: str) -> str:
    """One or two sentences for the index (see the module docstring for the order)."""
    explicit = _SUMMARY.search(md)
    if explicit is not None:
        return " ".join(explicit.group(1).split())
    _, sections = _sections(md)
    asked = next(
        (body for title, body in sections.items() if "asked" in title.lower()), None
    )
    source = asked if asked is not None else next(iter(sections.values()), "")
    block = _first_block(source)
    return _first_sentences(plain_text(render_markdown(block).body))


# ---------------------------------------------------------------------------
# Learning curves
# ---------------------------------------------------------------------------


def read_log(path: Path) -> list[dict[str, Any]]:
    """Rows of a ``log.jsonl``, each checked to carry an integer ``update``."""
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise NotebookError(f"{path}:{number}: not valid JSON ({exc})") from exc
        if not isinstance(row, dict) or not isinstance(row.get("update"), int):
            raise NotebookError(f"{path}:{number}: row has no integer 'update'")
        rows.append(row)
    return rows


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _weighted_mean(rows: Sequence[Mapping[str, Any]], metric: Metric) -> float | None:
    total = 0.0
    weight = 0.0
    for row in rows:
        value = _number(row.get(metric.key))
        if value is None:
            continue
        w = (
            1.0
            if metric.weight_key is None
            else (_number(row.get(metric.weight_key)) or 0.0)
        )
        total += value * w
        weight += w
    return total / weight if weight > 0 else None


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 5)


def series_for(
    rows: Sequence[Mapping[str, Any]], metric: Metric
) -> dict[str, Any] | None:
    """Binned (and for win rate, trailing-smoothed) points for one arm and metric.

    Points are ``[update, value]`` with the update at the end of each bin and
    ``value`` ``None`` where the bin has no data (the chart breaks the line there).
    Returns ``None`` when the arm never logged the metric.
    """
    if not any(_number(r.get(metric.key)) is not None for r in rows):
        return None
    size = max(1, math.ceil(len(rows) / MAX_POINTS))
    points: list[list[float | None]] = []
    smoothed: list[list[float | None]] = []
    for start in range(0, len(rows), size):
        chunk = rows[start : start + size]
        end_update = float(chunk[-1]["update"])
        points.append([end_update, _round(_weighted_mean(chunk, metric))])
        if metric.smooth:
            window = rows[
                max(0, start + len(chunk) - WIN_SMOOTHING_UPDATES) : start + len(chunk)
            ]
            smoothed.append([end_update, _round(_weighted_mean(window, metric))])
    out: dict[str, Any] = {"points": points}
    if metric.smooth:
        out["smoothed"] = smoothed
        out["smoothing_updates"] = WIN_SMOOTHING_UPDATES
    return out


def build_charts(
    run_dir: Path, repo_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """``(charts, arms)`` from every ``<arm>/log.jsonl`` directly under ``run_dir``."""
    logs = sorted(run_dir.glob("*/log.jsonl"))
    arms: list[dict[str, Any]] = []
    rows_by_arm: dict[str, list[dict[str, Any]]] = {}
    for log in logs:
        rows = read_log(log)
        if not rows:
            continue
        arm = log.parent.name
        rows_by_arm[arm] = rows
        last = rows[-1]
        arms.append(
            {
                "id": arm,
                "updates": int(last["update"]),
                "samples": int(sum(_number(r.get("samples")) or 0 for r in rows)),
                "wall_hours": _round((_number(last.get("wall_time")) or 0.0) / 3600.0),
                "log": _rel(log, repo_root),
                "href": _github(log, repo_root),
            }
        )
    charts: list[dict[str, Any]] = []
    for metric in METRICS:
        series = []
        for arm, rows in rows_by_arm.items():
            s = series_for(rows, metric)
            if s is not None:
                series.append({"arm": arm, **s})
        if series:
            charts.append(
                {
                    "id": metric.id,
                    "title": metric.title,
                    "key": metric.key,
                    "format": metric.format,
                    "y_min": metric.y_min,
                    "y_max": metric.y_max,
                    "series": series,
                }
            )
    return charts, arms


# ---------------------------------------------------------------------------
# Eval artefacts
# ---------------------------------------------------------------------------


def _side_label(stem: str) -> tuple[str, str]:
    stem = stem.replace("_survey", "")
    a, sep, b = stem.partition("_vs_")
    return (a, b) if sep else (stem, "")


def classify_artefact(data: Any) -> str:
    """``duel`` | ``survey`` | ``bc`` | ``dagger`` | ``matrix`` | ``other``."""
    if not isinstance(data, dict):
        return "other"
    if str(data.get("schema", "")).startswith("rlf.eval.duel/"):
        return "duel"
    if "contacts_per_match" in data:
        return "survey"
    if "holdout_rows" in data and "groups" in data:
        return "bc"
    if "best_round" in data and "rounds" in data:
        return "dagger"
    if "policies" in data and "missing" in data:
        return "matrix"
    return "other"


def _get(data: Mapping[str, Any], *keys: str) -> float | None:
    value: Any = data
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return _number(value)


def artefact_metrics(kind: str, data: Any) -> dict[str, float | None]:
    """The headline numbers for one artefact kind (``None`` where a field is absent)."""
    if kind == "duel":
        length = _get(data, "match", "length_median")
        return {
            "n": _get(data, "config", "n"),
            "win": _get(data, "side_a", "win_rate"),
            "draw": _get(data, "match", "draw_rate"),
            "hit_rate": _get(data, "side_a", "hit_rate"),
            "opp_hit_rate": _get(data, "side_b", "hit_rate"),
            "length_s": None if length is None else round(length / TICKS_PER_SECOND, 2),
            "passes": _get(data, "side_a", "passes"),
            "crashes_per_match": _get(data, "match", "crashes_per_match"),
            "sim_version": _get(data, "config", "sim_version"),
        }
    if kind == "survey":
        ticks = _get(data, "median_ticks")
        return {
            "n": _get(data, "n"),
            "win": _get(data, "a_win"),
            "contacts_per_match": _get(data, "contacts_per_match"),
            "closing_p50": _get(data, "closing_mps", "p50"),
            "head_on_share": _get(data, "head_on_share"),
            "crash_death_share": _get(data, "matches_with_crash_death"),
            "length_s": None if ticks is None else round(ticks / TICKS_PER_SECOND, 2),
        }
    if kind == "bc":
        return {
            "rows": _get(data, "collect", "rows"),
            "throttle": _get(data, "groups", "throttle", "agreement"),
            "fire": _get(data, "groups", "fire", "agreement"),
            "power": _get(data, "groups", "power", "agreement"),
        }
    if kind == "dagger":
        rounds = data.get("rounds", [])
        wins = [_get(r, "duel", "sample", "summary", "win_rate") for r in rounds]
        best = _get(data, "best_round")
        best_win = (
            wins[int(best)] if best is not None and 0 <= int(best) < len(wins) else None
        )
        return {"rounds": float(len(rounds)), "best_round": best, "best_win": best_win}
    if kind == "matrix":
        policies = data.get("policies", {})
        return {
            "policies": float(len(policies)) if isinstance(policies, dict) else None
        }
    return {}


def build_artefacts(run_dir: Path, repo_root: Path) -> list[dict[str, Any]]:
    """Every JSON file under ``run_dir`` with its kind, label and headline numbers."""
    out = []
    for path in sorted(run_dir.rglob("*.json")):
        data = _read_json(path)
        kind = classify_artefact(data)
        a, b = _side_label(path.stem)
        out.append(
            {
                "path": _rel(path, repo_root),
                "href": _github(path, repo_root),
                "group": path.parent.name if path.parent != run_dir else "",
                "kind": kind,
                "label": path.stem,
                "a": a,
                "b": b,
                "argmax": "argmax" in path.stem,
                "metrics": artefact_metrics(kind, data),
            }
        )
    return out


def eval_sim_version(artefacts: Iterable[Mapping[str, Any]]) -> int | None:
    """The highest ``config.sim_version`` among the run's duel evals."""
    versions = [
        a["metrics"].get("sim_version") for a in artefacts if a["kind"] == "duel"
    ]
    found = [int(v) for v in versions if v is not None]
    return max(found) if found else None


# ---------------------------------------------------------------------------
# Champions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Champion:
    """A promoted pilot from ``lab/champions/<id>/champion.json``."""

    id: str
    name: str
    run: str
    sim_version: int
    hulls: tuple[str, ...]
    promoted: str
    eval: Any


def load_champions(champions_dir: Path) -> list[Champion]:
    """Every champion, oldest promotion first; an absent directory means none yet.

    Raises:
        NotebookError: a ``champion.json`` is malformed or misses a field.
    """
    if not champions_dir.is_dir():
        return []
    champions = []
    for path in sorted(champions_dir.glob("*/champion.json")):
        data = _read_json(path)
        if not isinstance(data, dict):
            raise NotebookError(f"{path}: expected a JSON object")
        missing = [f for f in CHAMPION_FIELDS if f not in data]
        if missing:
            raise NotebookError(f"{path}: missing {', '.join(missing)}")
        hulls = data["hulls"]
        if not isinstance(hulls, list) or not all(isinstance(h, str) for h in hulls):
            raise NotebookError(f"{path}: 'hulls' must be a list of hull names")
        champions.append(
            Champion(
                id=str(data["id"]),
                name=str(data["name"]),
                run=Path(str(data["run"]).rstrip("/")).name,
                sim_version=int(data["sim_version"]),
                hulls=tuple(hulls),
                promoted=str(data["promoted"]),
                eval=data["eval"],
            )
        )
    return sorted(champions, key=lambda c: (c.promoted, c.id))


def champion_entry(champion: Champion, current: Champion | None) -> dict[str, Any]:
    """The notebook's view of a champion, with its "watch this pilot" link.

    Past champions of the current one's sim season are replayable on the live page
    (``scripts/build_site.sh`` builds their bundles); older seasons' are not.
    """
    is_current = current is not None and champion.id == current.id
    same_season = current is not None and champion.sim_version == current.sim_version
    return {
        "id": champion.id,
        "name": champion.name,
        "sim_version": champion.sim_version,
        "hulls": list(champion.hulls),
        "promoted": champion.promoted,
        "current": is_current,
        "watchable": is_current or same_season,
        "href": "/" if is_current else f"/?champion={champion.id}",
    }


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunEntry:
    """One run's index row and full page data, plus its sort key."""

    index: dict[str, Any]
    page: dict[str, Any]
    sort_key: tuple[Any, ...]


def build_run(
    run_dir: Path,
    run_ids: frozenset[str],
    champions: Sequence[Champion],
    current_champion: Champion | None,
    repo_root: Path,
    committed_at: Callable[[Path], int | None],
) -> RunEntry:
    """Read one run directory into its index row and page data.

    Raises:
        NotebookError: the directory name is not ``YYYY-MM-DD-slug``, or it has
            neither ``results.md`` nor ``plan.md``.
    """
    run_id = run_dir.name
    match = _RUN_ID.match(run_id)
    if match is None:
        raise NotebookError(f"{run_dir}: run directories are named YYYY-MM-DD-slug")
    results_path = run_dir / "results.md"
    plan_path = run_dir / "plan.md"
    if not results_path.is_file() and not plan_path.is_file():
        raise NotebookError(f"{run_dir}: has neither results.md nor plan.md")
    ctx = LinkContext(repo_root=repo_root, run_dir=run_dir, run_ids=run_ids)
    results_md = results_path.read_text() if results_path.is_file() else ""
    plan_md = plan_path.read_text() if plan_path.is_file() else ""
    results = render_markdown(results_md, ctx) if results_md else None
    plan = render_markdown(plan_md, ctx) if plan_md else None

    artefacts = build_artefacts(run_dir, repo_root)
    charts, arms = build_charts(run_dir, repo_root)
    primary_md = results_md or plan_md
    sim_version = eval_sim_version(artefacts) or parse_sim_version_text(primary_md)
    title = (
        results.title
        if results is not None
        else plan.title if plan is not None else run_id
    )
    run_champions = [
        champion_entry(c, current_champion)
        for c in reversed(champions)
        if c.run == run_id
    ]
    meta = {
        "id": run_id,
        "date": match.group(1),
        "title": title,
        "summary": parse_summary(primary_md),
        "verdict": parse_verdict(results_md) if results_md else None,
        "status": "done" if results_md else "in progress",
        "sim_version": sim_version,
        "champions": run_champions,
    }
    page = {
        "schema": RUN_SCHEMA,
        **meta,
        "results_html": results.body_without_title if results is not None else None,
        "plan_title": plan.title if plan is not None else None,
        "plan_html": plan.body_without_title if plan is not None else None,
        "charts": charts,
        "arms": arms,
        "artefacts": artefacts,
        "source": {
            "dir": _github(run_dir, repo_root),
            "results": _github(results_path, repo_root) if results_md else None,
            "plan": _github(plan_path, repo_root) if plan_md else None,
        },
    }
    index = {
        **meta,
        "has_plan": plan is not None,
        "n_charts": len(charts),
        "n_artefacts": len(artefacts),
    }
    stamp = committed_at(results_path if results_md else plan_path)
    # Uncommitted write-ups are the newest work; then sim season, then commit time.
    sort_key = (match.group(1), stamp is None, sim_version or 0, stamp or 0, run_id)
    return RunEntry(index=index, page=page, sort_key=sort_key)


def build_notebook(
    runs_dir: Path,
    champions_dir: Path,
    out_dir: Path,
    repo_root: Path = REPO_ROOT,
    committed_at: Callable[[Path], int | None] = git_first_commit_time,
) -> dict[str, Any]:
    """Write ``index.json`` and one ``<run>.json`` per run; return the index.

    Directories without ``results.md`` or ``plan.md`` are reported on stderr and
    skipped (a run that has just been created); malformed files raise.
    """
    run_dirs = []
    for d in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        if (d / "results.md").is_file() or (d / "plan.md").is_file():
            run_dirs.append(d)
        else:
            print(
                f"build_notebook: skipping {d} (no results.md or plan.md yet)",
                file=sys.stderr,
            )
    run_ids = frozenset(d.name for d in run_dirs)
    champions = load_champions(champions_dir)
    current = champions[-1] if champions else None
    entries = [
        build_run(d, run_ids, champions, current, repo_root, committed_at)
        for d in run_dirs
    ]
    entries.sort(key=lambda e: e.sort_key, reverse=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    # Only files this tool writes: a run that was renamed must not leave its old entry.
    for stale in out_dir.glob("*.json"):
        if stale.name == "index.json" or _RUN_ID.match(stale.stem):
            stale.unlink()
    for entry in entries:
        (out_dir / f"{entry.index['id']}.json").write_text(
            json.dumps(entry.page, ensure_ascii=False, separators=(",", ":"))
        )
    index = {
        "schema": INDEX_SCHEMA,
        "runs": [e.index for e in entries],
        "current_champion": (
            champion_entry(current, current) | {"run": current.run}
            if current is not None
            else None
        ),
    }
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    return index


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--runs", type=Path, default=REPO_ROOT / "lab" / "runs")
    parser.add_argument(
        "--champions", type=Path, default=REPO_ROOT / "lab" / "champions"
    )
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "web" / "public" / "notebook" / "data"
    )
    args = parser.parse_args(argv)
    index = build_notebook(args.runs, args.champions, args.out)
    for run in index["runs"]:
        verdict = run["verdict"] or "-"
        print(f"{run['id']}: sim v{run['sim_version']}, {verdict}, {run['title']}")
    print(f"wrote {len(index['runs'])} runs to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
