"""``tools/build_notebook.py``: lab runs become the notebook's index and run JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.build_notebook import (
    MAX_POINTS,
    METRICS,
    NotebookError,
    build_notebook,
    classify_artefact,
    load_champions,
    parse_sim_version_text,
    parse_summary,
    parse_verdict,
    read_log,
    series_for,
)
from tools.lab_markdown import LinkContext, render_markdown

REPO_ROOT = Path(__file__).resolve().parent.parent
WIN = next(m for m in METRICS if m.id == "win_vs_script")
REWARD = next(m for m in METRICS if m.id == "reward")


def _no_git(_: Path) -> int | None:
    return None


def _duel(sim_version: int, win: float) -> dict[str, Any]:
    return {
        "schema": "rlf.eval.duel/1",
        "a": "policy",
        "b": "script",
        "config": {"n": 512, "sim_version": sim_version},
        "match": {"length_median": 300.0, "draw_rate": 0.0},
        "side_a": {"win_rate": win, "hit_rate": 0.6, "passes": 1.0},
        "side_b": {"win_rate": 1 - win, "hit_rate": 0.5},
    }


def _write_run(root: Path, run_id: str, results: str, **files: Any) -> Path:
    run = root / "lab" / "runs" / run_id
    run.mkdir(parents=True)
    if results:
        (run / "results.md").write_text(results)
    for rel, content in files.items():
        path = run / rel.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content))
    return run


# --- results.md metadata ---------------------------------------------------


def test_verdict_reads_the_header_line_the_table_row_or_shipped() -> None:
    assert parse_verdict("# T\n\nDate x · verdict: **PASS**\n\n## A\n") == "PASS"
    assert (
        parse_verdict("# T\n\n| | |\n|---|---|\n| Verdict | **partial** on x |\n")
        == "PARTIAL"
    )
    assert (
        parse_verdict("# T\n\nRun x. Shipped: **arm A**.\n\n## A\nFAIL later\n")
        == "shipped"
    )
    assert parse_verdict("# T\n\nNo call yet.\n\n## Results\nverdict: FAIL\n") is None


def test_sim_version_text_accepts_both_spellings() -> None:
    assert parse_sim_version_text("| SIM_VERSION | 2 |") == 2
    assert parse_sim_version_text("- **Sim v3.** crashes hurt") == 3
    assert parse_sim_version_text("no version here") is None


def test_summary_prefers_comment_then_what_we_asked_then_first_section() -> None:
    explicit = "# T\n<!-- summary: Short and sweet. -->\n## What we asked\nOther.\n"
    assert parse_summary(explicit) == "Short and sweet."
    asked = (
        "# T\n\n## What we did\nStuff.\n\n## What we asked\n\n"
        "<!-- hand:asked -->Can a small net fly a fighter with no autopilot at all? "
        "We tried three routes.<!-- /hand:asked -->\n"
    )
    assert (
        parse_summary(asked)
        == "Can a small net fly a fighter with no autopilot at all?"
    )
    first = "# T\n\nRun x.\n\n## What changed\n\n- **Sim v3.** Contacts now do damage.\n- b\n"
    assert parse_summary(first) == "Sim v3. Contacts now do damage."


# --- Markdown --------------------------------------------------------------


def test_markdown_drops_hand_markers_wraps_tables_and_fixes_loose_lists() -> None:
    md = (
        "# <!-- hand:title -->Title<!-- /hand:title -->\n\nBacklog added:\n- one\n- two\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n"
    )
    rendered = render_markdown(md)
    assert rendered.title == "Title"
    assert "hand:" not in rendered.body
    assert "<li>one</li>" in rendered.body
    assert '<div class="table-scroll"><table>' in rendered.body
    assert "<h1>" not in rendered.body_without_title


def test_inline_code_paths_link_to_the_notebook_or_github(tmp_path: Path) -> None:
    run = _write_run(tmp_path, "2026-01-02-b", "# B\n", **{"plan.md": "# plan"})
    _write_run(tmp_path, "2026-01-01-a", "# A\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "SPEC.md").write_text("spec")
    ctx = LinkContext(tmp_path, run, frozenset({"2026-01-01-a", "2026-01-02-b"}))
    body = render_markdown(
        "See `plan.md`, `lab/runs/2026-01-01-a/results.md`, `docs/SPEC.md`, "
        "`docs/SPEC.md:12`, `missing/file.py` and `x < y`.",
        ctx,
    ).body
    assert 'href="/notebook/#2026-01-02-b/plan"' in body
    assert 'href="/notebook/#2026-01-01-a"' in body
    assert (
        body.count("https://github.com/tcgarvin/rl-fighter/blob/main/docs/SPEC.md") == 2
    )
    assert (
        "<code>missing/file.py</code>" in body
        and "missing/file.py</code></a>" not in body
    )


# --- learning curves -------------------------------------------------------


def test_series_bins_to_at_most_max_points_and_weights_by_episodes() -> None:
    rows = [
        {
            "update": u,
            "vs_scripted_win": 1.0 if u % 2 else 0.0,
            "vs_scripted_episodes": u % 2 + 1,
        }
        for u in range(1, 1201)
    ]
    series = series_for(rows, WIN)
    assert series is not None
    assert len(series["points"]) <= MAX_POINTS
    assert series["points"][-1][0] == 1200.0
    # Each bin of 4 holds two odd updates (weight 2, win 1) and two even (weight 1, win 0).
    assert series["points"][0][1] == pytest.approx(4 / 6, abs=1e-4)
    assert len(series["smoothed"]) == len(series["points"])


def test_series_leaves_gaps_where_no_episodes_finished_and_skips_absent_metrics() -> (
    None
):
    rows = [
        {
            "update": 1,
            "vs_scripted_win": None,
            "vs_scripted_episodes": 0,
            "reward_mean": 0.1,
        }
    ]
    rows += [
        {
            "update": 2,
            "vs_scripted_win": 0.5,
            "vs_scripted_episodes": 4,
            "reward_mean": 0.2,
        }
    ]
    series = series_for(rows, WIN)
    assert series is not None and series["points"] == [[1.0, None], [2.0, 0.5]]
    assert series_for([{"update": 1}], REWARD) is None


def test_bad_log_lines_name_the_file_and_line(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"
    log.write_text('{"update": 1}\n{not json\n')
    with pytest.raises(NotebookError, match=r"log.jsonl:2"):
        read_log(log)


# --- artefacts and champions ----------------------------------------------


def test_artefacts_are_classified_by_their_fields() -> None:
    assert classify_artefact(_duel(2, 0.5)) == "duel"
    assert classify_artefact({"n": 128, "contacts_per_match": 0.2}) == "survey"
    assert classify_artefact({"holdout_rows": 1, "groups": {}}) == "bc"
    assert classify_artefact({"best_round": 3, "rounds": []}) == "dagger"
    assert classify_artefact([1, 2]) == "other"


def test_champions_are_optional_but_must_be_complete(tmp_path: Path) -> None:
    assert load_champions(tmp_path / "absent") == []
    bad = tmp_path / "champions" / "c1"
    bad.mkdir(parents=True)
    (bad / "champion.json").write_text(json.dumps({"id": "c1", "name": "x"}))
    with pytest.raises(NotebookError, match="missing run"):
        load_champions(tmp_path / "champions")


# --- end to end ------------------------------------------------------------


def _champion(
    champions: Path, cid: str, run: str, promoted: str, sim_version: int = 3
) -> None:
    d = champions / cid
    d.mkdir(parents=True)
    fields = {
        "id": cid,
        "name": cid.upper(),
        "run": f"lab/runs/{run}",
        "sim_version": sim_version,
    }
    fields |= {"hulls": ["fighter"], "promoted": promoted, "eval": {}}
    (d / "champion.json").write_text(json.dumps(fields))


def test_build_writes_index_newest_first_with_champion_links(tmp_path: Path) -> None:
    log = "\n".join(
        json.dumps({"update": u, "vs_scripted_win": 0.5, "vs_scripted_episodes": 2})
        for u in range(1, 11)
    )
    _write_run(
        tmp_path,
        "2026-01-01-old",
        "# Old run\n\nSIM_VERSION 2 · verdict: FAIL\n\n## What we asked\n\nDid it fly at all?\n",
    )
    _write_run(
        tmp_path,
        "2026-01-02-new",
        "# New run\n\nShipped.\n\n## What changed\n\n- Crashes hurt now.\n",
        **{
            "plan.md": "# The plan\n",
            "arm__log.jsonl": log,
            "eval__x_vs_script.json": _duel(3, 1),
        },
    )
    (tmp_path / "lab" / "runs" / "2026-01-03-empty").mkdir()
    champions = tmp_path / "lab" / "champions"
    _champion(champions, "v2", "2026-01-01-old", "2026-01-01T07:00")
    _champion(champions, "v3", "2026-01-02-new", "2026-01-02T07:00")
    out = tmp_path / "out"
    out.mkdir()
    (out / "2025-12-31-renamed.json").write_text("{}")

    index = build_notebook(tmp_path / "lab" / "runs", champions, out, tmp_path, _no_git)

    assert [r["id"] for r in index["runs"]] == ["2026-01-02-new", "2026-01-01-old"]
    new, old = index["runs"]
    assert (new["verdict"], new["sim_version"], new["summary"]) == (
        "shipped",
        3,
        "Crashes hurt now.",
    )
    assert (old["verdict"], old["sim_version"]) == ("FAIL", 2)
    assert (
        new["champions"][0]["href"] == "/"
        and old["champions"][0]["href"] == "/?champion=v2"
    )
    assert index["current_champion"]["id"] == "v3"
    assert sorted(p.name for p in out.iterdir()) == [
        "2026-01-01-old.json",
        "2026-01-02-new.json",
        "index.json",
    ]
    page = json.loads((out / "2026-01-02-new.json").read_text())
    assert page["plan_title"] == "The plan"
    assert [c["id"] for c in page["charts"]] == ["win_vs_script"]
    assert page["artefacts"][0]["metrics"]["win"] == 1.0
    assert "<h1>" not in page["results_html"]


def test_same_day_runs_order_by_commit_time_with_uncommitted_first(
    tmp_path: Path,
) -> None:
    for name in ("2026-01-01-a", "2026-01-01-b", "2026-01-01-c"):
        _write_run(tmp_path, name, f"# {name}\n")
    stamps = {"2026-01-01-a": 200, "2026-01-01-b": 100, "2026-01-01-c": None}
    index = build_notebook(
        tmp_path / "lab" / "runs",
        tmp_path / "none",
        tmp_path / "out",
        tmp_path,
        lambda p: stamps[p.parent.name],
    )
    assert [r["id"] for r in index["runs"]] == [
        "2026-01-01-c",
        "2026-01-01-a",
        "2026-01-01-b",
    ]


def test_the_real_lab_runs_build(tmp_path: Path) -> None:
    index = build_notebook(
        REPO_ROOT / "lab" / "runs", REPO_ROOT / "lab" / "champions", tmp_path, REPO_ROOT
    )
    runs = {r["id"]: r for r in index["runs"]}
    assert {"2026-10-28-learnability-spike", "2026-10-28-sim-v2"} <= set(runs)
    assert runs["2026-10-28-learnability-spike"]["verdict"] == "PASS"
    assert runs["2026-10-28-sim-v2"]["sim_version"] == 2
    spike = json.loads((tmp_path / "2026-10-28-learnability-spike.json").read_text())
    arms = {s["arm"] for c in spike["charts"] for s in c["series"]}
    assert arms == {"ppo_bc", "ppo_scratch"}
    assert all(
        len(s["points"]) <= MAX_POINTS for c in spike["charts"] for s in c["series"]
    )


def test_only_same_season_champions_get_a_watch_link(tmp_path: Path) -> None:
    for run in ("2026-01-01-a", "2026-01-02-b", "2026-01-03-c"):
        _write_run(tmp_path, run, f"# Run {run}\n\nShipped.\n")
    champions = tmp_path / "lab" / "champions"
    _champion(champions, "v2", "2026-01-01-a", "2026-01-01", sim_version=2)
    _champion(champions, "v3a", "2026-01-02-b", "2026-01-02")
    _champion(champions, "v3b", "2026-01-03-c", "2026-01-03")
    out = tmp_path / "out"

    index = build_notebook(tmp_path / "lab" / "runs", champions, out, tmp_path, _no_git)

    watch = {r["id"]: r["champions"][0]["watchable"] for r in index["runs"]}
    assert watch == {"2026-01-03-c": True, "2026-01-02-b": True, "2026-01-01-a": False}
