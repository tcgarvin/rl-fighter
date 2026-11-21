"""``pilots_v1`` keys for the station assault and the bomber (SIM_VERSION 9):
``station_as_convoy_share`` and ``bomber_share`` (``docs/PILOT_TRAINING.md`` §3), and a
trainer that draws both.

The extension must be built into the venv first:

    uv run maturin develop -m crates/sim-py/Cargo.toml --release
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pytest

rlf_sim = pytest.importorskip(
    "rlf_sim",
    reason=(
        "rlf_sim extension not built; run "
        "`uv run maturin develop -m crates/sim-py/Cargo.toml --release`"
    ),
)

from spacefight.env.rosters import (  # noqa: E402
    BOMBER,
    DEATHMATCH,
    FLEET_HULLS,
    MAX_SHIPS,
    STATION_AS_CARRIER,
    STATION_AS_CONVOY,
    STATION_ASSAULT,
    DRILL_DOCK,
    PilotsDistribution,
    PilotsRosterSampler,
    capital_hull_ids,
    citadel_roster,
    hull_names_by_id,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402
from spacefight.rl.spike_ppo import PPOConfig, SpikeTrainer  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ASSETS = str(REPO / "assets")
MIX = (0.3, 0.225, 0.225, 0.25)
# The mission weights before 2026-11-21: no station assault.
NO_STATION = (0.4, 0.3, 0.3, 0.0)


def _sampler(seed: int = 0, **overrides: object) -> PilotsRosterSampler:
    return PilotsRosterSampler(PilotsDistribution(**overrides), seed)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"drill_share": 0.3, "commander_p": 0.667, "mixed_p": 0.5},
        # A station weight with both shares 0: every assault is the sim's own roster,
        # read as a carrier battle, and nothing extra is drawn.
        {"mission_weights": MIX},
    ],
)
def test_shares_zero_leave_every_draw_and_the_generator_as_they_were(
    extra: dict[str, object],
) -> None:
    plain = _sampler(seed=7, **extra)
    zero = _sampler(seed=7, station_as_convoy_share=0.0, bomber_share=0.0, **extra)
    assert plain.sample_many(500) == zero.sample_many(500)
    assert plain.rng.bit_generator.state == zero.rng.bit_generator.state


def test_without_a_station_weight_the_convoy_share_draws_nothing() -> None:
    plain = _sampler(seed=2, commander_p=0.667, mission_weights=NO_STATION)
    split = _sampler(
        seed=2,
        commander_p=0.667,
        mission_weights=NO_STATION,
        station_as_convoy_share=0.5,
    )
    assert plain.sample_many(500) == split.sample_many(500)
    assert plain.rng.bit_generator.state == split.rng.bit_generator.state


def test_the_station_share_and_its_reading_follow_the_settings() -> None:
    rosters = _sampler(
        seed=3, mission_weights=MIX, station_as_convoy_share=0.5
    ).sample_many(6000)
    station = [r for r in rosters if r.mission == STATION_ASSAULT]
    assert len(station) / len(rosters) == pytest.approx(0.25, abs=0.03)
    reads = Counter(r.station_as for r in station)
    assert set(reads) == {STATION_AS_CARRIER, STATION_AS_CONVOY}
    assert reads[STATION_AS_CONVOY] / len(station) == pytest.approx(0.5, abs=0.05)
    # The citadel's roster (``citadel_share`` 1 by default, as live).
    sim_roster = citadel_roster().teams
    assert all(r.teams == sim_roster for r in station)
    assert all(r.station_as == STATION_AS_CARRIER for r in rosters if r not in station)


def test_bombers_replace_that_share_of_strike_slots_outside_the_station() -> None:
    rosters = _sampler(
        seed=4, mission_weights=MIX, bomber_share=0.2, drill_share=0.3
    ).sample_many(6000)
    strike = bombers = 0
    for r in rosters:
        if r.drill is not None:
            # A dock drill draws its own hull (a bomber among them).
            if r.drill.kind != DRILL_DOCK:
                assert BOMBER not in r.teams[0] + r.teams[1], "drills are unchanged"
            continue
        if r.mission == STATION_ASSAULT:
            assert r.teams == citadel_roster().teams
            continue
        for h in r.teams[0] + r.teams[1]:
            strike += h in FLEET_HULLS or h == BOMBER
            bombers += h == BOMBER
    assert bombers / strike == pytest.approx(0.2, abs=0.02)


def test_a_bomber_roster_keeps_its_size_capitals_and_mission() -> None:
    plain = _sampler(seed=9, mission_weights=MIX).sample_many(300)
    swapped = _sampler(seed=9, mission_weights=MIX, bomber_share=1.0).sample_many(300)
    # Share 1 draws one number per strike slot, so the draws drift apart; compare
    # only what the swap keeps.
    for r in swapped:
        assert r.mission in {p.mission for p in plain}
        if r.mission != STATION_ASSAULT and r.drill is None:
            assert not any(h in FLEET_HULLS for h in r.teams[0] + r.teams[1])
    first = swapped[0]
    if first.mission == DEATHMATCH:
        assert set(first.teams[0] + first.teams[1]) == {BOMBER}


@pytest.mark.parametrize("bad", [-0.1, 1.5])
@pytest.mark.parametrize(
    "key", ["station_as_convoy_share", "bomber_share", "drill_bomber_share"]
)
def test_a_bad_share_is_rejected(key: str, bad: float) -> None:
    with pytest.raises(ValueError, match=key):
        PilotsDistribution(**{key: bad})  # type: ignore[arg-type]


def test_the_distribution_round_trips_with_the_new_keys() -> None:
    d = PilotsDistribution(
        mission_weights=MIX,
        station_as_convoy_share=0.5,
        bomber_share=0.2,
        drill_bomber_share=0.2,
    )
    assert PilotsDistribution.from_dict(d.to_dict()) == d


def test_the_env_plays_every_drawn_station_and_bomber_roster() -> None:
    sampler = _sampler(
        seed=11, mission_weights=MIX, station_as_convoy_share=0.5, bomber_share=0.3
    )
    env = RustVecEnv(
        ASSETS, 8, [["fighter"], ["fighter"]], 11, n_threads=1, roster_sampler=sampler
    )
    names = hull_names_by_id(Path(ASSETS))
    for _ in range(30):
        env.scripted_actions()
        env.step()
    seen = set()
    for i, roster in enumerate(env.rosters):
        hulls = [names[int(h)] for h in env.hull_id[i, : roster.n_ships]]
        assert hulls == list(roster.teams[0] + roster.teams[1])
        seen.update(hulls)
        seen.add(roster.mission)
    assert BOMBER in seen


def _config(**overrides: object) -> PPOConfig:
    base: dict[str, object] = {
        "assets_dir": ASSETS,
        "n_envs": 6,
        "n_steps": 16,
        "t_tail": 40,
        "n_updates": 2,
        "minibatch": 128,
        "sim_threads": 1,
        "torch_threads": 1,
        "env_warmup_steps": 60,
        "rosters": "pilots_v1",
        "critic": "fleet",
        "learner_side": "random",
        "order_reward_weight": 1.0,
    }
    base.update(overrides)
    return PPOConfig.preset("scratch", **base)


def test_trains_on_station_assaults_and_bombers(tmp_path: Path) -> None:
    config = _config(
        roster_overrides={
            "mission_weights": [0.0, 0.0, 0.0, 1.0],
            "station_as_convoy_share": 0.5,
            "commander_p": 0.667,
        }
    )
    trainer = SpikeTrainer(config, tmp_path / "station")
    capital = capital_hull_ids(Path(ASSETS))
    bomber = hull_names_by_id(Path(ASSETS)).index(BOMBER)

    def check(t: SpikeTrainer, row: dict[str, object]) -> None:
        store = t.storage
        assert row["samples"] != 0
        assert np.isfinite(float(row["value_loss"]))  # type: ignore[arg-type]
        assert not (store.learner & np.isin(store.hull, capital)).any()
        assert (store.learner & (store.hull == bomber)).any(), "pilots fly bombers"

    assert trainer.train(check) == 2
    assert all(r.mission == STATION_ASSAULT for r in trainer.env.rosters)


def test_drill_bomber_share_zero_draws_nothing_and_a_share_swaps_pilots_only() -> None:
    # Order drills only: a dock drill draws its own hull, bombers among them.
    extra = {
        "drill_share": 0.5,
        "drill_weights": (1.0, 1.0, 1.0),
        "drill_dock_share": 0.0,
    }
    plain = _sampler(seed=5, **extra)
    zero = _sampler(seed=5, drill_bomber_share=0.0, **extra)
    assert plain.sample_many(300) == zero.sample_many(300)
    assert plain.rng.bit_generator.state == zero.rng.bit_generator.state
    rosters = _sampler(seed=5, drill_bomber_share=0.5, **extra).sample_many(3000)
    drills = [r for r in rosters if r.drill is not None]
    pilots = bombers = 0
    for r in drills:
        assert r.drill is not None
        if r.drill.kind == "goto":
            assert BOMBER not in r.teams[0]
            continue
        assert BOMBER not in r.teams[1], "the enemies keep their hulls"
        others = [h for k, h in enumerate(r.teams[0]) if k not in r.drill.pilots]
        assert BOMBER not in others, "wards keep their hulls"
        pilots += len(r.drill.pilots)
        bombers += sum(r.teams[0][k] == BOMBER for k in r.drill.pilots)
    assert bombers / pilots == pytest.approx(0.5, abs=0.04)
    # Matches keep their hulls (a station assault's roster has bombers of its own).
    assert all(
        BOMBER not in r.teams[0] + r.teams[1]
        for r in rosters
        if r.drill is None and r.mission != STATION_ASSAULT
    )


def test_the_env_plays_a_bomber_drill_from_its_layout() -> None:
    sampler = _sampler(
        seed=6,
        drill_share=1.0,
        drill_weights=(0.0, 1.0, 1.0),
        drill_bomber_share=1.0,
        drill_dock_share=0.0,
    )
    env = RustVecEnv(
        ASSETS, 4, [["fighter"], ["fighter"]], 6, n_threads=1, roster_sampler=sampler
    )
    names = hull_names_by_id(Path(ASSETS))
    for _ in range(10):
        env.scripted_actions()
        env.step()
    for i, roster in enumerate(env.rosters):
        assert roster.drill is not None
        hulls = [names[int(h)] for h in env.hull_id[i, : roster.n_ships]]
        assert hulls == list(roster.teams[0] + roster.teams[1])
        assert all(hulls[k] == BOMBER for k in roster.drill.pilots)
