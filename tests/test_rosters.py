"""Rosters, the roster sampler and per-env rosters in RustVecEnv."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest
import rlf_sim

from spacefight.env.rosters import (
    BOMBER,
    DEFAULT_ASSETS,
    FLEET_HULLS,
    MAX_FLEET_SHIPS,
    MAX_PER_SIDE,
    MISSIONS,
    ROSTER_PRESETS,
    STATION_ASSAULT,
    STRIKE_HULLS,
    Roster,
    RosterDistribution,
    RosterSampler,
    arena_radius_for,
    capital_hull_ids,
    hull_names_by_id,
    load_hull_costs,
    mission_weights_of,
    resolve_distribution,
)
from spacefight.env.rust_env import RustVecEnv

ASSETS = "assets"
DUEL = [["fighter"], ["fighter"]]


def hull_names() -> list[str]:
    """Hull names in hull-id order (the sim's catalogue order)."""
    return hull_names_by_id()


def test_arena_rule_is_the_duel_arena_for_every_fleet_size() -> None:
    for n in range(2, 9):
        assert arena_radius_for(n) == 450.0
    assert Roster.of(["gunship", "fighter"], ["fighter"] * 3).arena_radius == 450.0


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
        Roster.of(["fighter"] * 11, ["fighter"] * 10)


def test_hull_costs_come_from_the_yaml() -> None:
    assert load_hull_costs() == {
        "bomber": 25.0,
        "carrier": 120.0,
        "citadel": 320.0,
        "dreadnought": 180.0,
        "fighter": 10.0,
        "freighter": 40.0,
        "gunship": 30.0,
        "station": 200.0,
        "strafer": 10.0,
    }


def test_hull_ids_keep_the_legacy_hulls_first() -> None:
    """SIM_VERSION 9: the v4 hulls keep their ids, the new ones follow by name, as the
    sim numbers them (``rlf_sim.LEGACY_HULL_ORDER``, ``sim::data::hull_order``); v10
    freezes the v9 ones too (bomber 5, station 6) and adds citadel 7, dreadnought 8."""
    names = hull_names_by_id()
    assert names == [
        "carrier",
        "fighter",
        "freighter",
        "gunship",
        "strafer",
        "bomber",
        "station",
        "citadel",
        "dreadnought",
    ]
    assert names[:7] == list(rlf_sim.LEGACY_HULL_ORDER)
    # The ids the sim gives the hulls of a match agree.
    env = rlf_sim.VecEnv(
        str(DEFAULT_ASSETS),
        1,
        [["station", "bomber"], ["carrier", "strafer"]],
        1,
        mission="station_assault",
    )
    assert [names[h] for h in env.hull_id[0]] == [
        "station",
        "bomber",
        "carrier",
        "strafer",
    ]
    assert capital_hull_ids() == [0, 2, 6, 7, 8]


def test_the_citadel_roster_is_the_training_default() -> None:
    """SIM_VERSION 10: a station assault trains on the citadel's roster (19 ships in a
    550 m arena) by default, as the live page plays it; ``citadel_share`` 0 keeps the
    sim's v9 roster, and a share between mixes them."""
    from spacefight.env.rosters import PilotsDistribution, citadel_roster, make_sampler

    citadel = citadel_roster()
    assert citadel.teams[0][0] == "citadel" and "dreadnought" in citadel.teams[1]
    assert citadel.n_ships == 19 and citadel.arena_radius == 550.0
    assert citadel.n_ships <= PilotsDistribution().max_ships
    station_only = (0.0, 0.0, 0.0, 1.0)
    default = make_sampler(PilotsDistribution(mission_weights=station_only), 3)
    assert all(r.teams == citadel.teams for r in default.sample_many(200))
    v9 = make_sampler(
        PilotsDistribution(mission_weights=station_only, citadel_share=0.0), 3
    )
    assert all(r.teams[0][0] == "station" for r in v9.sample_many(200))
    mixed = make_sampler(
        PilotsDistribution(mission_weights=station_only, citadel_share=0.5), 3
    )
    stations = Counter(r.teams[0][0] for r in mixed.sample_many(400))
    assert set(stations) == {"station", "citadel"}
    assert 140 < stations["citadel"] < 260
    with pytest.raises(ValueError, match="max_ships"):
        PilotsDistribution(
            mission_weights=station_only, citadel_share=0.5, max_ships=16
        )


def test_the_default_pilots_mix_plays_every_live_mission() -> None:
    """The owner's rule (2026-11-21): what ships, the defaults pick up. ``pilots_v1``
    trains all four missions the live page rotates, its station assaults the citadel's,
    and dock drills among the drills."""
    from spacefight.env.rosters import (
        ROSTER_PRESETS,
        PilotsDistribution,
        citadel_roster,
        make_sampler,
    )

    d = PilotsDistribution()
    assert ROSTER_PRESETS["pilots_v1"] == d
    assert d.mission_weights == (0.3, 0.25, 0.25, 0.2)
    assert d.citadel_share == 1.0 and d.drill_dock_share == 0.25
    drawn = make_sampler(d, 8).sample_many(2000)
    shares = Counter(r.mission for r in drawn)
    assert set(shares) == set(MISSIONS)
    assert shares[STATION_ASSAULT] / len(drawn) == pytest.approx(0.2, abs=0.03)
    citadel = citadel_roster().teams
    assert all(r.teams == citadel for r in drawn if r.mission == STATION_ASSAULT)


def test_bomber_is_an_opt_in_strike_hull() -> None:
    assert BOMBER not in FLEET_HULLS and BOMBER in STRIKE_HULLS
    assert MISSIONS[-1] == STATION_ASSAULT


def test_station_roster_carries_its_obs_mapping() -> None:
    teams = (("station", "fighter"), ("carrier", "bomber"))
    r = Roster(teams, STATION_ASSAULT)
    assert r.mission_spec == {"kind": STATION_ASSAULT, "as": "carrier"}
    convoy = Roster(teams, STATION_ASSAULT, station_as="convoy")
    assert convoy.mission_spec == {"kind": STATION_ASSAULT, "as": "convoy"}
    assert convoy.label == "station as convoy: XF v CB"
    assert Roster(teams[:1] + (("fighter",),)).mission_spec is None
    with pytest.raises(ValueError):
        Roster(teams, STATION_ASSAULT, station_as="duel")


def test_three_mission_weights_draw_as_before_v9() -> None:
    """A trailing zero weight leaves numpy's draws exactly as the three-weight ones."""
    three = np.asarray([0.4, 0.3, 0.3])
    four = np.asarray([0.4, 0.3, 0.3, 0.0])
    a, b = np.random.default_rng(5), np.random.default_rng(5)
    draws_a = [int(a.choice(3, p=three / three.sum())) for _ in range(2000)]
    draws_b = [int(b.choice(4, p=four / four.sum())) for _ in range(2000)]
    assert draws_a == draws_b
    assert mission_weights_of((0.4, 0.3, 0.3)) == (0.4, 0.3, 0.3, 0.0)
    with pytest.raises(ValueError):
        mission_weights_of((1.0, 1.0))


def test_fleet_rosters_draw_strike_craft_only() -> None:
    """Capital ships (SIM_VERSION 4) never enter a fleet (deathmatch) roster."""
    for name, dist in ROSTER_PRESETS.items():
        if not isinstance(dist, RosterDistribution):
            continue  # mission mixes: tests/test_orders_training.py
        for roster in RosterSampler(dist, 0).sample_many(300):
            hulls = set(roster.teams[0]) | set(roster.teams[1])
            assert hulls <= set(FLEET_HULLS), (name, hulls)


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
    assert env.n_ships == MAX_FLEET_SHIPS == 8
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
        RustVecEnv(ASSETS, 2, DUEL, 0, max_ships=rlf_sim.MAX_SHIPS + 1)
