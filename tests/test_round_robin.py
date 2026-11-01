"""Round robin: no-commander envs, resuming, and tiny real matches."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from spacefight.env.rust_env import OBS_LAYOUT
from spacefight.eval.controllers import Controller, make_controller
from spacefight.eval.fleet import ShipMetrics
from spacefight.population.__main__ import main
from spacefight.population.records import (
    Population,
    PopulationError,
    add_member,
    new_founder,
    script_member,
    sha256_of,
)
from spacefight.population.round_robin import (
    RoundRobinConfig,
    build_no_commander_env,
    config_from_file,
    load_results,
    pair_path,
    play_pair_in_sim,
    rosters_for,
    run_round_robin,
)

TINY_MISSIONS = ("deathmatch", "carrier_battle", "convoy_escort")


def metrics(ships: int = 4, fire: float = 0.1) -> dict[str, Any]:
    return {
        "ships": ships,
        "damage_dealt": 1.0,
        "shield_damage_dealt": 1.0,
        "survival": 0.5,
        "shots": 1.0,
        "hits": 1.0,
        "hit_rate": 0.5,
        "engagement_rate": 0.5,
        "outside_share": 0.0,
        "engine_duty": 0.5,
        "passes": 1.0,
        "crash_damage_taken": 0.0,
        "crash_contacts": 0.0,
        "fire_rate": fire,
    }


class StandIn:
    """Plays a pair without the sim and remembers what it was asked."""

    def __init__(self, score: float = 0.75) -> None:
        self.calls = 0
        self.score = score

    def __call__(
        self, a: Controller, b: Controller, cfg: RoundRobinConfig, threads: int, _: Path
    ) -> dict[str, dict[str, Any]]:
        self.calls += 1
        return {
            mission: {
                "n": cfg.n_per_mission,
                "score_rate": self.score,
                "score_rate_team0": self.score,
                "score_rate_team1": self.score,
                "draw_rate": 0.0,
                "time_limit_rate": 0.0,
                "stalemate_rate": 0.0,
                "length_median_s": 30.0,
                "nan_matches": 0,
                "stuck_matches": 0,
                "ships_a": metrics(fire=0.2),
                "ships_b": metrics(fire=0.4),
                "secs": 0.1,
            }
            for mission in cfg.missions
        }


@pytest.fixture
def weights_root(tmp_path: Path) -> Path:
    """Where the fake checkpoints go; the stand-in player never loads them."""
    root = tmp_path / "root"
    root.mkdir()
    return root


def fake_population(tmp_path: Path, root: Path, names: tuple[str, ...]) -> Population:
    members = {"script": script_member()}
    for name in names:
        path = root / f"{name}.pt"
        path.write_bytes(name.encode())
        members[name] = new_founder(name, name, f"{name}.pt", sha256_of(path))
    return Population(tmp_path / "season", members)


@pytest.fixture
def no_controllers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake checkpoints can't be loaded, so hand out scripted controllers."""
    monkeypatch.setattr(
        "spacefight.population.round_robin.make_controller",
        lambda spec, sample=True: make_controller("script"),
    )


@pytest.mark.usefixtures("no_controllers")
def test_finished_pairs_are_skipped_on_resume(
    tmp_path: Path, weights_root: Path
) -> None:
    population = fake_population(tmp_path, weights_root, ("a", "b"))
    out = tmp_path / "out"
    stand_in = StandIn()
    played = run_round_robin(
        population, ["a", "b"], out, RoundRobinConfig(), weights_root, play=stand_in
    )
    assert played == ["a__b.json"]
    assert stand_in.calls == 1

    again = run_round_robin(
        population,
        ["a", "b", "script"],
        out,
        RoundRobinConfig(),
        weights_root,
        play=stand_in,
    )
    assert sorted(again) == ["a__script.json", "b__script.json"]
    assert stand_in.calls == 3

    final = run_round_robin(
        population,
        ["script", "b", "a"],
        out,
        RoundRobinConfig(),
        weights_root,
        play=stand_in,
    )
    assert final == []
    assert stand_in.calls == 3


@pytest.mark.usefixtures("no_controllers")
def test_a_crash_mid_run_keeps_the_pairs_already_written(
    tmp_path: Path, weights_root: Path
) -> None:
    population = fake_population(tmp_path, weights_root, ("a", "b"))
    out = tmp_path / "out"
    stand_in = StandIn()

    def fails_on_second(*args: Any) -> dict[str, dict[str, Any]]:
        if stand_in.calls == 1:
            raise RuntimeError("the machine went away")
        return stand_in(*args)

    with pytest.raises(RuntimeError):
        run_round_robin(
            population,
            ["a", "b", "script"],
            out,
            RoundRobinConfig(),
            weights_root,
            play=fails_on_second,
        )
    assert pair_path(out, "a", "b").exists()
    assert not list((out / "pairs").glob("*.tmp"))
    again = run_round_robin(
        population,
        ["a", "b", "script"],
        out,
        RoundRobinConfig(),
        weights_root,
        play=stand_in,
    )
    assert sorted(again) == ["a__script.json", "b__script.json"]


@pytest.mark.usefixtures("no_controllers")
def test_a_different_config_in_the_same_directory_raises(
    tmp_path: Path, weights_root: Path
) -> None:
    population = fake_population(tmp_path, weights_root, ("a", "b"))
    out = tmp_path / "out"
    run_round_robin(
        population, ["a", "b"], out, RoundRobinConfig(), weights_root, play=StandIn()
    )
    with pytest.raises(ValueError, match="different config"):
        run_round_robin(
            population,
            ["a", "b"],
            out,
            RoundRobinConfig(n_per_mission=24),
            weights_root,
            play=StandIn(),
        )


@pytest.mark.usefixtures("no_controllers")
def test_a_changed_checkpoint_stops_the_run_before_any_match(
    tmp_path: Path, weights_root: Path
) -> None:
    population = fake_population(tmp_path, weights_root, ("a", "b"))
    (weights_root / "b.pt").write_bytes(b"new weights")
    stand_in = StandIn()
    with pytest.raises(PopulationError, match="changed"):
        run_round_robin(
            population,
            ["a", "b"],
            tmp_path / "out",
            RoundRobinConfig(),
            weights_root,
            play=stand_in,
        )
    assert stand_in.calls == 0


@pytest.mark.usefixtures("no_controllers")
def test_finished_pairs_of_other_weights_are_refused(
    tmp_path: Path, weights_root: Path
) -> None:
    population = fake_population(tmp_path, weights_root, ("a", "b"))
    out = tmp_path / "out"
    run_round_robin(
        population, ["a", "b"], out, RoundRobinConfig(), weights_root, play=StandIn()
    )
    path = pair_path(out, "a", "b")
    data = json.loads(path.read_text())
    data["a_sha256"] = "b" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(PopulationError, match="other weights"):
        run_round_robin(
            population,
            ["a", "b"],
            out,
            RoundRobinConfig(),
            weights_root,
            play=StandIn(),
        )
    with pytest.raises(PopulationError, match="other weights"):
        load_results(out, population)


def test_a_pair_needs_two_distinct_members(tmp_path: Path, weights_root: Path) -> None:
    population = fake_population(tmp_path, weights_root, ("a",))
    with pytest.raises(ValueError, match="two distinct"):
        run_round_robin(
            population, ["a"], tmp_path / "o", RoundRobinConfig(), weights_root
        )
    with pytest.raises(ValueError, match="two distinct"):
        run_round_robin(
            population, ["a", "a"], tmp_path / "o", RoundRobinConfig(), weights_root
        )


@pytest.mark.usefixtures("no_controllers")
def test_results_add_up_to_matrices_ratings_and_behaviour(
    tmp_path: Path, weights_root: Path
) -> None:
    population = fake_population(tmp_path, weights_root, ("a", "b"))
    out = tmp_path / "out"
    run_round_robin(
        population,
        ["a", "b", "script"],
        out,
        RoundRobinConfig(),
        weights_root,
        play=StandIn(score=0.75),
    )
    results = load_results(out, population)
    assert results.pairs == 3
    assert results.matches == 3 * 3 * 12
    assert set(results.by_mission) == set(TINY_MISSIONS)
    assert results.overall.rate[("a", "b")] == pytest.approx(0.75)
    assert results.overall.rate[("b", "a")] == pytest.approx(0.25)
    assert results.overall.n[("a", "b")] == 36
    assert [r.member for r in results.ratings][0] == "a"
    # "a" is always side a (fire 0.2); "script" always side b (fire 0.4).
    assert results.behaviour["a"].fire_rate == pytest.approx(0.2)
    assert results.behaviour["script"].fire_rate == pytest.approx(0.4)
    assert results.transitivity_overall.beats_everyone == ("a",)
    dumped = json.loads(json.dumps(results.to_dict()))
    assert dumped["win_matrix"]["overall"]["a"]["b"] == pytest.approx(0.75)
    assert dumped["win_matrix"]["deathmatch"]["b"]["a"] == pytest.approx(0.25)


def test_load_results_refuses_an_empty_directory(
    tmp_path: Path, weights_root: Path
) -> None:
    population = fake_population(tmp_path, weights_root, ("a", "b"))
    out = tmp_path / "out"
    out.mkdir()
    (out / "config.json").write_text(json.dumps(RoundRobinConfig().to_dict()))
    with pytest.raises(FileNotFoundError, match="no finished pairs"):
        load_results(out, population)


def test_the_config_round_trips_through_its_file(tmp_path: Path) -> None:
    cfg = RoundRobinConfig(n_per_mission=24, seed=5)
    (tmp_path / "config.json").write_text(json.dumps(cfg.to_dict()))
    assert config_from_file(tmp_path) == cfg


def test_rosters_are_live_for_missions_and_sampled_the_same_for_deathmatch() -> None:
    cfg = RoundRobinConfig(deathmatch_rosters=4)
    first = rosters_for("deathmatch", cfg)
    assert len(first) == 4
    assert first == rosters_for("deathmatch", cfg)
    assert len({name for name, _ in first}) == 4
    assert rosters_for("carrier_battle", cfg)
    with pytest.raises(ValueError, match="deathmatch_rosters"):
        rosters_for("deathmatch", RoundRobinConfig(deathmatch_rosters=0))


def test_the_env_size_must_cover_every_roster_from_both_sides() -> None:
    with pytest.raises(ValueError, match="multiple of"):
        build_no_commander_env("carrier_battle", RoundRobinConfig(n_per_mission=7), 1)


@pytest.mark.parametrize("mission", TINY_MISSIONS)
def test_no_commander_envs_hide_orders_from_both_teams_and_balance_sides(
    mission: str,
) -> None:
    me = build_no_commander_env(mission, RoundRobinConfig(), 1)
    env = me.env
    offset, width = OBS_LAYOUT["order"]
    for _ in range(90):
        assert not np.any(env.obs[..., offset : offset + width])
        env.step(env.scripted_actions())
    assert (me.a_team == 0).sum() == (me.a_team == 1).sum()
    for entry in np.unique(me.entry):
        sides = me.a_team[me.entry == entry]
        assert (sides == 0).sum() == (sides == 1).sum()
    if mission == "deathmatch":
        assert not me.capital.any()
    else:
        assert me.capital.any()


def test_a_tiny_real_round_robin_of_the_script_against_itself() -> None:
    a, b = make_controller("script"), make_controller("script")
    results = play_pair_in_sim(a, b, RoundRobinConfig(), 2)
    assert set(results) == set(TINY_MISSIONS)
    for result in results.values():
        assert result["n"] == 12
        assert 0.0 <= result["score_rate"] <= 1.0
        assert ShipMetrics(**result["ships_a"]).ships > 0
        assert result["nan_matches"] == 0


def test_the_same_seed_plays_the_same_results() -> None:
    cfg = RoundRobinConfig(missions=("deathmatch",))
    first = play_pair_in_sim(
        make_controller("script"), make_controller("script"), cfg, 2
    )
    second = play_pair_in_sim(
        make_controller("script"), make_controller("script"), cfg, 2
    )
    assert first["deathmatch"]["score_rate"] == second["deathmatch"]["score_rate"]
    assert first["deathmatch"]["ships_a"] == second["deathmatch"]["ships_a"]


CHECKOUT_ROOT = Path("/home/timg/code/rl-fighter")
V1 = "lab/runs/2026-10-30-fleet-pilot/arm_warm/checkpoints/ppo_bc_400.pt"


@pytest.mark.skipif(
    not (CHECKOUT_ROOT / V1).is_file(), reason="fleet pilot v1's weights are not here"
)
def test_a_v1_width_pilot_plays_a_tiny_pair_against_the_script_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    season = tmp_path / "season"
    add_member(season, script_member())
    add_member(
        season,
        new_founder(
            "v1",
            "fleet",
            V1,
            sha256_of(CHECKOUT_ROOT / V1),
            note="the fleet pilot, to prove a 385-wide pilot runs",
        ),
    )
    out = tmp_path / "out"
    args = [
        "round-robin",
        "--season",
        str(season),
        "--out",
        str(out),
        "--members",
        "v1,script",
        "--checkpoint-root",
        str(CHECKOUT_ROOT),
    ]
    assert main(args) == 0
    assert "v1 v script" not in capsys.readouterr().err
    pair = json.loads(pair_path(out, "script", "v1").read_text())
    assert set(pair["missions"]) == set(TINY_MISSIONS)

    report_args = [
        "report",
        "--season",
        str(season),
        "--results",
        str(out),
        "--phase",
        "tiny",
        "--date",
        "2026-11-01",
    ]
    before = sorted(p.read_bytes() for p in (season / "members").glob("*.json"))
    assert main(report_args) == 0
    assert sorted(p.read_bytes() for p in (season / "members").glob("*.json")) == before
    assert (out / "summary.json").is_file()
    assert (season / "shadow/tiny.json").is_file()
    assert "## Who beats whom" in (season / "report.md").read_text()
    # A rerun of the phase keeps the first shadow report and says so.
    assert main(report_args) == 2
