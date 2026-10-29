"""Tests for the spike write-up tooling (tools/lab_report.py, tools/spike_eval_matrix.py)."""

import json
from pathlib import Path
from typing import Any

import pytest

from spacefight.eval.duel import DuelResult, EvalConfig, MatchMetrics, SideMetrics
from tools.lab_report import (
    BC_DAGGER,
    PPO_BC_FINAL,
    PPO_BC_400,
    PPO_SCRATCH_FINAL,
    SCRIPT,
    BestCheckpoint,
    Pairing,
    best_checkpoint,
    checkpoint_updates,
    compute_verdict,
    load_results,
    matrix_pairings,
    read_log,
    smoothed_win,
    write_report,
)
from tools.spike_eval_matrix import run_matrix

SCRIPT_STEM = Pairing(SCRIPT, SCRIPT, False).stem


def side(**overrides: Any) -> SideMetrics:
    values: dict[str, Any] = dict(
        wins=0,
        draws=0,
        losses=0,
        win_rate=0.5,
        passes=3.0,
        shots=45.0,
        hits=27.0,
        hit_rate=0.6,
        damage_dealt=75.0,
        shield_damage_dealt=0.0,
        engagement_rate=0.86,
        outside_share=0.0,
        main_engine_duty=0.85,
        fire_rate=0.085,
        shots_per_s=1.0,
        mean_speed=39.0,
        nan_matches=0,
        stuck_matches=0,
        nan_or_stuck=0,
    )
    values.update(overrides)
    return SideMetrics(**values)


def duel(
    a: str, *, b: str = SCRIPT, draw: float = 0.02, kill: float = 0.99, **a_side: Any
) -> DuelResult:
    match = MatchMetrics(
        length_median=1300.0,
        length_p10=1000.0,
        length_p90=1700.0,
        kill_rate=kill,
        time_limit_rate=1.0 - kill,
        draw_rate=draw,
        a_win_rate_team0=0.5,
        a_win_rate_team1=0.5,
    )
    return DuelResult(a, b, EvalConfig(), match, side(**a_side), side())


GOOD_BC: dict[str, Any] = dict(win_rate=0.40, hit_rate=0.40, engagement_rate=0.80)
GOOD_PPO: dict[str, Any] = dict(win_rate=0.70, hit_rate=0.50, engagement_rate=0.60)


def results(**by_name: DuelResult) -> dict[str, DuelResult]:
    out = {SCRIPT_STEM: duel(SCRIPT)}
    out.update({Pairing(name, SCRIPT, False).stem: r for name, r in by_name.items()})
    return out


def test_verdict_pass_when_ppo_reaches_every_pass_cell() -> None:
    verdict = compute_verdict(
        results(
            **{BC_DAGGER: duel(BC_DAGGER, **GOOD_BC)},
            **{PPO_BC_FINAL: duel(PPO_BC_FINAL, **GOOD_PPO)},
        )
    )
    assert verdict.level == "PASS"


def test_verdict_partial_when_only_bc_reaches_its_column() -> None:
    verdict = compute_verdict(
        results(
            **{BC_DAGGER: duel(BC_DAGGER, **GOOD_BC)},
            **{PPO_BC_FINAL: duel(PPO_BC_FINAL, **(GOOD_PPO | {"win_rate": 0.45}))},
        )
    )
    assert verdict.level == "PARTIAL"
    assert any("misses pass cells: win" in r for r in verdict.reasons)


def test_verdict_partial_when_ppo_wins_but_leaves_the_arena() -> None:
    bad_bc: dict[str, Any] = GOOD_BC | {"win_rate": 0.1}
    edge: dict[str, Any] = GOOD_PPO | {"outside_share": 0.05}
    verdict = compute_verdict(
        results(
            **{BC_DAGGER: duel(BC_DAGGER, **bad_bc)},
            **{PPO_BC_FINAL: duel(PPO_BC_FINAL, **edge)},
        )
    )
    assert verdict.level == "PARTIAL"
    assert any("watchability" in r for r in verdict.reasons)


def test_verdict_fail_when_bc_misses_and_ppo_never_beats_the_script() -> None:
    verdict = compute_verdict(
        results(
            **{BC_DAGGER: duel(BC_DAGGER, **(GOOD_BC | {"win_rate": 0.15}))},
            **{PPO_BC_FINAL: duel(PPO_BC_FINAL, **(GOOD_PPO | {"win_rate": 0.45}))},
            **{PPO_BC_400: duel(PPO_BC_400, **(GOOD_PPO | {"win_rate": 0.48}))},
        )
    )
    assert verdict.level == "FAIL"


def test_hit_rate_is_judged_relative_to_the_script() -> None:
    # 0.35 < 0.6 × the script's 0.6 (pass column needs 0.36).
    weak_aim: dict[str, Any] = GOOD_PPO | {"hit_rate": 0.35}
    verdict = compute_verdict(
        results(
            **{BC_DAGGER: duel(BC_DAGGER, **GOOD_BC)},
            **{PPO_BC_FINAL: duel(PPO_BC_FINAL, **weak_aim)},
        )
    )
    assert verdict.level == "PARTIAL"
    assert any("hit" in r for r in verdict.reasons)


def test_verdict_pending_without_the_required_evals() -> None:
    verdict = compute_verdict({SCRIPT_STEM: duel(SCRIPT)})
    assert verdict.level == "PENDING"
    assert "bc_dagger_vs_script" in verdict.reasons[0]


@pytest.mark.parametrize("scratch_win, holds", [(0.54, True), (0.56, False)])
def test_h2_needs_a_lead_of_015(scratch_win: float, holds: bool) -> None:
    verdict = compute_verdict(
        results(
            **{BC_DAGGER: duel(BC_DAGGER, **GOOD_BC)},
            **{PPO_BC_FINAL: duel(PPO_BC_FINAL, **GOOD_PPO)},
            **{PPO_SCRATCH_FINAL: duel(PPO_SCRATCH_FINAL, win_rate=scratch_win)},
        )
    )
    h2 = next(h for h in verdict.hypotheses if h.startswith("**H2**"))
    assert ("does not hold" not in h2) is holds


def log_row(update: int, win: float | None, episodes: int) -> dict[str, Any]:
    return {
        "update": update,
        "samples": 1000,
        "update_seconds": 1.0,
        "vs_scripted_win": win,
        "vs_scripted_episodes": episodes,
        "entropy_throttle": 0.5,
        "entropy_slew": 0.0,
        "entropy_fire": 0.3,
        "entropy_power": 1.0,
        "entropy_mean": 0.5,
    }


def write_log(path: Path, rows: list[dict[str, Any]], tail: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows) + tail)


def synthetic_log() -> list[dict[str, Any]]:
    # Win climbs to update 200, then falls; update 300 has a lucky single episode.
    rows = []
    for u in range(1, 301):
        if u % 3 == 0:
            rows.append(log_row(u, None, 0))
        elif u <= 200:
            rows.append(log_row(u, u / 400, 10))
        else:
            rows.append(log_row(u, 0.2, 10))
    rows[299] = log_row(300, 1.0, 1)
    return rows


def test_best_checkpoint_from_a_log_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    write_log(path, synthetic_log(), tail='{"update": 301, "samp')
    rows = read_log(path)
    assert len(rows) == 300  # the half-written last line is dropped
    candidates = checkpoint_updates(rows, every=100, n_updates=1200)
    assert candidates == [100, 200, 300]
    best = best_checkpoint(rows, candidates)
    assert best.update == 200
    expected = [u / 400 for u in range(151, 201) if u % 3]
    assert best.smoothed_win == pytest.approx(sum(expected) / len(expected))


def test_smoothing_weights_by_episodes_and_skips_empty_updates() -> None:
    rows = [log_row(1, None, 0), log_row(2, 1.0, 1), log_row(3, 0.0, 3)]
    assert smoothed_win(rows, 3, window=50) == pytest.approx(0.25)
    assert smoothed_win(rows, 1, window=50) is None


def test_best_checkpoint_raises_without_episodes() -> None:
    with pytest.raises(ValueError):
        best_checkpoint([log_row(100, None, 0)], [100])
    assert best_checkpoint(
        [log_row(100, 0.5, 2), log_row(200, 0.5, 2)], [100, 200], window=50
    ) == BestCheckpoint(100, 0.5)


def test_report_tolerates_missing_evals_and_keeps_hand_sections(tmp_path: Path) -> None:
    run = tmp_path / "2026-10-28-test-run"
    (run / "eval").mkdir(parents=True)
    (run / "eval" / f"{SCRIPT_STEM}.json").write_text(duel(SCRIPT).to_json())
    write_log(run / "ppo_bc" / "log.jsonl", synthetic_log()[:150])
    out = run / "results.md"
    write_report(run, out)
    text = out.read_text()
    assert "verdict: **PENDING**" in text
    assert "| PPO-BC final | pass | — |" in text
    assert (run / "learning_curves.csv").is_file()

    edited = text.replace(
        "TODO(coordinator): bullets on which of H1/H2/H0 held, and surprises.",
        "H1 held.",
    )
    out.write_text(edited)
    write_report(run, out)
    assert "<!-- hand:learned -->H1 held.<!-- /hand:learned -->" in out.read_text()


def test_matrix_pairings_cover_the_adapted_plan() -> None:
    stems = {p.stem for p in matrix_pairings()}
    assert {"script_vs_script", "bc_vs_script", "bc_argmax_vs_script"} <= stems
    assert "ppo_bc_final_vs_bc_dagger" in stems
    assert "ppo_scratch_final_argmax_vs_ppo_bc_final" in stems
    assert "script_argmax_vs_script" not in stems
    assert len(stems) == 23


def test_matrix_runs_missing_pairings_once_and_blocks_absent_checkpoints(
    tmp_path: Path,
) -> None:
    pairs = [Pairing(SCRIPT, SCRIPT, False), Pairing(BC_DAGGER, SCRIPT, False)]
    first = run_matrix(tmp_path, pairs, n=4, seed=7, n_threads=1)
    assert first.ran == [SCRIPT_STEM]
    assert "bc_dagger_vs_script" in first.blocked
    loaded = load_results(tmp_path / "eval")
    assert set(loaded) == {SCRIPT_STEM}
    assert loaded[SCRIPT_STEM].a == "script"

    second = run_matrix(tmp_path, pairs[:1], n=4, seed=7, n_threads=1)
    assert second.ran == [] and second.skipped == [SCRIPT_STEM]
    with pytest.raises(ValueError, match="n=4 seed=7"):
        run_matrix(tmp_path, pairs[:1], n=6, seed=7, n_threads=1)
