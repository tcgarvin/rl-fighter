"""Tests for the duel balance sweep (tools/duel_sweep.py, spike plan §2.3)."""

from dataclasses import replace
from typing import Any

import pytest
import yaml

from tools.duel_sweep import (
    ASSETS,
    Balance,
    CellSummary,
    Gates,
    SweepConfig,
    gate_failures,
    main,
    patched_assets,
    run_cell,
    table_row,
)

TINY = SweepConfig(n=16, seed=0, reaction_ticks=2, n_threads=2)


def test_patched_assets_writes_the_tuple_into_a_copy_only() -> None:
    real_weapons = (ASSETS / "weapons.yaml").read_text()
    real_hull = (ASSETS / "hulls" / "fighter" / "hull.yaml").read_text()
    balance = Balance(damage=7, interval=0.3, range=150, speed=210, spread_deg=2, hp=55)
    with patched_assets(balance) as assets:
        gauss = yaml.safe_load((assets / "weapons.yaml").read_text())["gauss"]
        hull = yaml.safe_load((assets / "hulls" / "fighter" / "hull.yaml").read_text())
        assert assets != ASSETS
    assert gauss["damage"] == 7
    assert gauss["interval"] == 0.3
    assert gauss["range"] == 150
    assert gauss["speed"] == 210
    assert gauss["spread_deg"] == 2
    assert hull["hp"] == 55
    assert len(hull["armour"]) == 5
    assert not assets.exists()
    assert (ASSETS / "weapons.yaml").read_text() == real_weapons
    assert (ASSETS / "hulls" / "fighter" / "hull.yaml").read_text() == real_hull


def test_shipped_balance_reads_the_asset_files() -> None:
    shipped = Balance.shipped()
    gauss = yaml.safe_load((ASSETS / "weapons.yaml").read_text())["gauss"]
    assert (shipped.damage, shipped.range, shipped.interval) == (
        gauss["damage"],
        gauss["range"],
        gauss["interval"],
    )
    assert shipped.armour


def test_patched_assets_can_strip_the_armour() -> None:
    with patched_assets(replace(Balance.shipped(), armour=False)) as assets:
        hull = yaml.safe_load((assets / "hulls" / "fighter" / "hull.yaml").read_text())
    assert "armour" not in hull


def test_tiny_sweep_ends_duels_in_kills_with_plausible_metrics() -> None:
    summary = run_cell(Balance.shipped(), TINY, Gates())
    assert summary.n == 16
    assert summary.draw_rate <= 0.5
    assert summary.time_limit_rate <= 0.5
    assert summary.median_length > 300
    assert summary.median_passes >= 1
    assert 0.0 < summary.hit_rate <= 1.0
    assert summary.shots_per_match > 0
    assert sum(summary.mult_mix.values()) == pytest.approx(1.0)
    assert set(summary.mult_mix) <= {"0.5", "1", "1.5"}
    assert "|" in table_row(summary)


def test_sweep_is_deterministic() -> None:
    assert run_cell(Balance.shipped(), TINY, Gates()) == run_cell(
        Balance.shipped(), TINY, Gates()
    )


def _passing_summary() -> CellSummary:
    return CellSummary(
        balance=Balance.shipped(),
        reaction_ticks=2,
        n=200,
        median_length=1000,
        p10_length=800,
        p90_length=1200,
        q25_length=900,
        q75_length=1100,
        draw_rate=0.02,
        time_limit_rate=0.0,
        team0_win_share=0.5,
        median_passes=4,
        median_approaches=30,
        hits_per_pass=15,
        damage_per_pass=0.25,
        shots_per_match=90,
        hit_rate=0.6,
        outside_share=0.0,
        mult_mix={"0.5": 1.0},
        failures=(),
    )


@pytest.mark.parametrize(
    ("change", "gate"),
    [
        ({"median_length": 400}, "length"),
        ({"median_length": 1600}, "length"),
        ({"draw_rate": 0.10}, "draws"),
        ({"time_limit_rate": 0.2}, "time-limit"),
        ({"median_passes": 2.5}, "passes"),
        ({"damage_per_pass": 0.05}, "dmg/pass"),
        ({"damage_per_pass": 0.5}, "dmg/pass"),
    ],
)
def test_gate_failures_names_each_failed_gate(
    change: dict[str, Any], gate: str
) -> None:
    assert gate_failures(_passing_summary(), Gates()) == ()
    assert gate_failures(replace(_passing_summary(), **change), Gates()) == (gate,)


def test_main_exit_status_follows_the_gated_cells(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 16 seeds of a 300-tick time limit cannot meet the 450-tick median gate.
    args = ["--n", "16", "--n-threads", "2", "--time-limit-s", "10"]
    assert main(args) == 1
    assert main([*args, "--gate-reaction-ticks"]) == 0
    assert "| tuple |" in capsys.readouterr().out
