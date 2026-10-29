"""Rosters, the roster sampler and per-env rosters in RustVecEnv."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest
import rlf_sim

from spacefight.env.rosters import (
    FLEET_HULLS,
    MAX_PER_SIDE,
    ROSTER_PRESETS,
    Roster,
    RosterDistribution,
    RosterSampler,
    arena_radius_for,
    load_hull_costs,
    resolve_distribution,
)
from spacefight.env.rust_env import RustVecEnv

ASSETS = "assets"
DUEL = [["fighter"], ["fighter"]]


def hull_names() -> list[str]:
    """Hull names in hull-id order (the catalogue sorts them by name)."""
    return sorted(load_hull_costs())


def test_arena_rule_keeps_the_duel_and_grows_per_ship() -> None:
    assert arena_radius_for(2) == 450.0
    assert arena_radius_for(4) == 500.0
    assert arena_radius_for(8) == 600.0
    assert Roster.of(["gunship"], ["fighter"] * 3).arena_radius == 500.0
    assert Roster.of(["gunship", "fighter"], ["fighter"] * 3).arena_radius == 525.0


def test_roster_properties_and_validation() -> None:
    roster = Roster.of(["fighter", "gunship"], ["strafer", "strafer", "fighter"])
    assert roster.n_ships == 5
    assert roster.size_class == "2v3"
    assert roster.swapped().size_class == "2v3"
    assert roster.label == "FG v SSF"
    assert roster.cost(load_hull_costs()) == (40.0, 30.0)
    with pytest.raises(ValueError):
        Roster.of([], ["fighter"])
    with pytest.raises(ValueError):
        Roster.of(["fighter"] * 5, ["fighter"] * 4)


def test_hull_costs_come_from_the_yaml() -> None:
    assert load_hull_costs() == {"fighter": 10.0, "strafer": 10.0, "gunship": 30.0}


def test_sampler_is_deterministic_per_seed() -> None:
    dist = ROSTER_PRESETS["fleet_v1"]
    a = RosterSampler(dist, 3).sample_many(200)
    b = RosterSampler(dist, 3).sample_many(200)
    c = RosterSampler(dist, 4).sample_many(200)
    assert a == b
    assert a != c


def test_sampler_covers_sizes_hulls_and_uneven_sides() -> None:
    rosters = RosterSampler(ROSTER_PRESETS["fleet_v1"], 0).sample_many(3000)
    sizes = Counter(len(t) for r in rosters for t in r.teams)
    assert set(sizes) == set(range(1, MAX_PER_SIDE + 1))
    hulls = Counter(h for r in rosters for t in r.teams for h in t)
    assert set(hulls) == set(FLEET_HULLS)
    uneven = np.mean([len(r.teams[0]) != len(r.teams[1]) for r in rosters])
    assert 0.15 < uneven < 0.45
    # Symmetric in the teams: team 0 is the larger side about half the time.
    bigger0 = [len(r.teams[0]) > len(r.teams[1]) for r in rosters]
    bigger1 = [len(r.teams[0]) < len(r.teams[1]) for r in rosters]
    assert abs(sum(bigger0) - sum(bigger1)) < 0.25 * (sum(bigger0) + sum(bigger1))


def test_drafts_spend_at_most_the_budget() -> None:
    dist = RosterDistribution(draft_p=1.0, duel_p=0.0, draft_budgets=(30.0,))
    costs = load_hull_costs()
    for roster in RosterSampler(dist, 1).sample_many(300):
        for spent in roster.cost(costs):
            # Nothing cheaper than 10 fits once less than 10 is left.
            assert 20.0 < spent <= 30.0


def test_distribution_round_trips_and_rejects_bad_values() -> None:
    dist = ROSTER_PRESETS["fleet_v1"]
    assert RosterDistribution.from_dict(dist.to_dict()) == dist
    assert resolve_distribution("fleet_v1") == dist
    assert resolve_distribution(dist.to_dict()) == dist
    with pytest.raises(KeyError):
        resolve_distribution("nope")
    with pytest.raises(ValueError):
        RosterDistribution(size_weights=(1.0, 1.0))
    with pytest.raises(ValueError):
        RosterDistribution(uneven_p=1.5)
    with pytest.raises(ValueError):
        RosterDistribution.from_dict({"bogus": 1})


def _check_buffers_match_rosters(env: RustVecEnv) -> None:
    names = hull_names()
    for i, roster in enumerate(env.rosters):
        k = roster.n_ships
        team = env.team[i]
        expected_team = [0] * len(roster.teams[0]) + [1] * len(roster.teams[1])
        assert team[:k].tolist() == expected_team
        assert (team[k:] == -1).all()
        hulls = [names[h] for h in env.hull_id[i, :k]]
        assert hulls == list(roster.teams[0] + roster.teams[1])
        assert env.arena_radius[i] == pytest.approx(roster.arena_radius)
        assert not env.thruster_mask[i, k:].any()
        assert not env.act_mask[i, k:].any()
        assert not env.raw.alive[i, k:].any()
        assert (env.obs[i, k:] == 0).all()


def test_sampled_env_buffers_follow_each_envs_roster() -> None:
    sampler = RosterSampler(ROSTER_PRESETS["fleet_v1"], 5)
    env = RustVecEnv(
        ASSETS, 12, DUEL, 7, n_threads=2, time_limit_s=6.0, roster_sampler=sampler
    )
    assert env.n_ships == rlf_sim.MAX_SHIPS
    _check_buffers_match_rosters(env)
    seen: set[str] = set()
    for _ in range(400):  # 6 s limit: every env resets twice
        env.scripted_actions()
        _, rewards, dones, info = env.step()
        assert (rewards[env.team < 0] == 0).all() or dones.any()
        seen.update(r.label for r in env.rosters)
    assert int(env.raw.episode_count.min()) >= 2
    _check_buffers_match_rosters(env)
    assert len(seen) > 12


def test_sampled_envs_are_deterministic() -> None:
    def run() -> np.ndarray:
        sampler = RosterSampler(ROSTER_PRESETS["fleet_v1"], 2)
        env = RustVecEnv(
            ASSETS, 6, DUEL, 3, n_threads=2, time_limit_s=4.0, roster_sampler=sampler
        )
        for _ in range(250):
            env.scripted_actions()
            env.step()
        return env.raw.state_hash()

    assert (run() == run()).all()


def test_prev_team_describes_the_finished_match() -> None:
    sampler = RosterSampler(RosterDistribution(duel_p=0.0, draft_p=0.0), 9)
    env = RustVecEnv(
        ASSETS, 8, DUEL, 1, n_threads=2, time_limit_s=2.0, roster_sampler=sampler
    )
    before = [env.rosters[i] for i in range(8)]
    done_seen = False
    for _ in range(70):
        env.scripted_actions()
        _, _, dones, info = env.step()
        for i in np.flatnonzero(dones):
            k = before[i].n_ships
            assert (info.prev_team[i, :k] >= 0).all()
            assert (info.prev_team[i, k:] == -1).all()
            done_seen = True
        before = list(env.rosters)
    assert done_seen


def test_padded_fixed_fleet_matches_the_unpadded_env() -> None:
    plain = RustVecEnv(ASSETS, 4, DUEL, 11, n_threads=2)
    padded = RustVecEnv(ASSETS, 4, DUEL, 11, n_threads=2, max_ships=5)
    assert padded.n_ships == 5
    for _ in range(200):
        plain.scripted_actions()
        plain.step()
        padded.scripted_actions()
        padded.step()
    assert (plain.raw.state_hash() == padded.raw.state_hash()).all()
    assert np.array_equal(plain.obs, padded.obs[:, :2])


def test_rosters_that_do_not_fit_are_rejected() -> None:
    env = RustVecEnv(ASSETS, 2, DUEL, 0, max_ships=3)
    with pytest.raises(ValueError, match="slots"):
        env.set_next_roster(
            0, Roster.of(["fighter", "fighter"], ["gunship", "fighter"])
        )
    with pytest.raises(IndexError):
        env.set_next_roster(5, Roster.of(["fighter"], ["fighter"]))
    with pytest.raises(ValueError, match="max_ships"):
        RustVecEnv(ASSETS, 2, DUEL, 0, max_ships=9)
