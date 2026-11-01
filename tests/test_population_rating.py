"""Combat rating and transitivity, on made-up results."""

from __future__ import annotations

import math

import pytest

from spacefight.population.rating import POINTS_PER_LOGIT, PairScore, rate
from spacefight.population.standings import (
    MAX_CYCLES_LISTED,
    make_matrix,
    overall_matrix,
    transitivity,
)


def by_name(ratings: list) -> dict:
    return {r.member: r for r in ratings}


def test_a_stronger_record_rates_higher_with_the_gap_matching_the_odds() -> None:
    ratings = by_name(rate([PairScore("a", "b", 750.0, 1000)], prior_sd_logit=100.0))
    gap = ratings["a"].rating - ratings["b"].rating
    assert gap == pytest.approx(math.log(3.0) * POINTS_PER_LOGIT, rel=1e-3)


def test_ratings_are_centred_and_sorted_strongest_first() -> None:
    ratings = rate(
        [
            PairScore("a", "b", 70.0, 100),
            PairScore("b", "c", 70.0, 100),
            PairScore("a", "c", 85.0, 100),
        ]
    )
    assert [r.member for r in ratings] == ["a", "b", "c"]
    assert sum(r.rating for r in ratings) == pytest.approx(0.0, abs=1e-6)


def test_an_undefeated_pilot_has_a_finite_rating() -> None:
    ratings = by_name(rate([PairScore("a", "b", 200.0, 200)]))
    assert math.isfinite(ratings["a"].rating)
    assert ratings["a"].rating > ratings["b"].rating
    assert math.isfinite(ratings["a"].sd)


def test_uncertainty_shrinks_with_more_matches() -> None:
    few = by_name(rate([PairScore("a", "b", 6.0, 10)]))
    many = by_name(rate([PairScore("a", "b", 600.0, 1000)]))
    assert many["a"].sd < few["a"].sd / 3.0


def test_a_sparse_pair_is_rated_with_more_uncertainty_than_a_well_played_one() -> None:
    ratings = by_name(
        rate(
            [
                PairScore("a", "b", 500.0, 1000),
                PairScore("b", "c", 500.0, 1000),
                PairScore("c", "sparse", 2.0, 4),
            ]
        )
    )
    assert ratings["sparse"].sd > 2.0 * ratings["b"].sd
    assert ratings["sparse"].matches == 4


def test_a_member_with_no_matches_sits_at_the_mean_with_the_priors_width() -> None:
    ratings = by_name(rate([PairScore("a", "b", 50.0, 100)], members=["idle"]))
    assert ratings["idle"].rating == pytest.approx(0.0, abs=1e-6)
    assert ratings["idle"].matches == 0
    assert ratings["idle"].sd > ratings["a"].sd


def test_disconnected_groups_still_get_ratings() -> None:
    ratings = by_name(
        rate([PairScore("a", "b", 90.0, 100), PairScore("c", "d", 90.0, 100)])
    )
    assert ratings["a"].rating > ratings["b"].rating
    assert ratings["c"].rating > ratings["d"].rating
    assert ratings["a"].rating == pytest.approx(ratings["c"].rating, abs=1e-6)


def test_a_pure_cycle_rates_all_three_equal() -> None:
    cycle = [
        PairScore("a", "b", 80.0, 100),
        PairScore("b", "c", 80.0, 100),
        PairScore("c", "a", 80.0, 100),
    ]
    ratings = rate(cycle)
    for r in ratings:
        assert r.rating == pytest.approx(0.0, abs=1e-6)
        assert r.matches == 200
        assert r.sd > 0.0


def test_results_given_either_way_round_rate_the_same() -> None:
    forward = by_name(rate([PairScore("a", "b", 70.0, 100)]))
    backward = by_name(rate([PairScore("b", "a", 30.0, 100)]))
    assert forward["a"].rating == pytest.approx(backward["a"].rating)
    assert forward["a"].sd == pytest.approx(backward["a"].sd)


def test_rating_refuses_bad_input() -> None:
    with pytest.raises(ValueError, match="itself"):
        PairScore("a", "a", 1.0, 2)
    with pytest.raises(ValueError, match="outside"):
        PairScore("a", "b", 3.0, 2)
    with pytest.raises(ValueError, match="positive"):
        PairScore("a", "b", 0.0, 0)
    with pytest.raises(ValueError, match="nothing to rate"):
        rate([])
    with pytest.raises(ValueError, match="prior"):
        rate([PairScore("a", "b", 1.0, 2)], prior_sd_logit=0.0)


def cycle_matrix(rate_ab: float = 0.8, rate_bc: float = 0.7, rate_ca: float = 0.6):
    return make_matrix(
        {
            ("a", "b"): (rate_ab, 100),
            ("b", "c"): (rate_bc, 100),
            ("c", "a"): (rate_ca, 100),
        }
    )


def test_a_cycle_is_found_and_its_strength_is_the_weakest_edge() -> None:
    summary = transitivity(cycle_matrix())
    assert summary.triads == 1
    assert summary.cyclic == 1
    assert summary.cyclic_share == 1.0
    found = summary.cycles[0]
    assert found.cycle == ("a", "b", "c")
    assert found.strength == pytest.approx(0.1)
    assert found.z == pytest.approx(0.1 / (0.5 / 10.0))
    assert summary.beats_everyone == ()
    assert summary.undefeated == ()
    assert summary.record["a"] == (1, 1, 0)


def test_a_cycle_running_the_other_way_is_found_too() -> None:
    summary = transitivity(cycle_matrix(0.2, 0.3, 0.4))
    assert summary.cyclic == 1
    assert summary.cycles[0].cycle == ("a", "c", "b")


def test_a_ladder_has_no_cycles_and_a_dominant_pilot_is_named() -> None:
    matrix = make_matrix(
        {("a", "b"): (0.9, 50), ("a", "c"): (0.9, 50), ("b", "c"): (0.7, 50)}
    )
    summary = transitivity(matrix)
    assert summary.triads == 1
    assert summary.cyclic == 0
    assert summary.beats_everyone == ("a",)
    assert summary.undefeated == ("a",)


def test_a_cycle_inside_the_margin_does_not_count() -> None:
    summary = transitivity(cycle_matrix(0.53, 0.53, 0.53))
    assert summary.triads == 0
    assert summary.cyclic == 0
    assert summary.cyclic_share == 0.0
    assert transitivity(cycle_matrix(0.53, 0.53, 0.53), margin=0.01).cyclic == 1


def test_an_unplayed_pair_leaves_its_triad_undecided_and_nobody_beats_everyone() -> (
    None
):
    matrix = make_matrix({("a", "b"): (0.9, 50), ("a", "c"): (0.9, 50)})
    summary = transitivity(matrix)
    assert summary.triads == 0
    assert summary.beats_everyone == ("a",)
    assert summary.record["b"] == (0, 1, 0)
    sparse = make_matrix({("a", "b"): (0.9, 50), ("c", "d"): (0.9, 50)})
    assert transitivity(sparse).beats_everyone == ()


def test_the_list_of_cycles_is_capped_with_the_strongest_first() -> None:
    results = {}
    names = [f"m{k:02d}" for k in range(12)]
    # A rotation in which each beats the next five makes many cycles.
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i < j:
                ahead = (j - i) % 12
                results[(a, b)] = (0.9 if ahead <= 5 else 0.1, 100)
    summary = transitivity(make_matrix(results))
    assert summary.cyclic > MAX_CYCLES_LISTED
    assert len(summary.cycles) == MAX_CYCLES_LISTED
    strengths = [c.strength for c in summary.cycles]
    assert strengths == sorted(strengths, reverse=True)


def test_the_overall_matrix_weighs_missions_equally_and_adds_matches() -> None:
    by_mission = {
        "deathmatch": make_matrix({("a", "b"): (1.0, 100)}),
        "carrier": make_matrix({("b", "a"): (1.0, 10)}),
    }
    overall = overall_matrix(by_mission)
    assert overall.rate[("a", "b")] == pytest.approx(0.5)
    assert overall.n[("a", "b")] == 110
    assert overall.pair_scores()[0].score == pytest.approx(55.0)


def test_the_overall_matrix_refuses_a_pair_missing_from_a_mission() -> None:
    by_mission = {
        "deathmatch": make_matrix({("a", "b"): (1.0, 100)}),
        "carrier": make_matrix({("a", "c"): (1.0, 10)}),
    }
    with pytest.raises(ValueError, match="no results"):
        overall_matrix(by_mission)


def test_make_matrix_refuses_bad_input() -> None:
    with pytest.raises(ValueError, match="both ways"):
        make_matrix({("a", "b"): (0.5, 2), ("b", "a"): (0.5, 2)})
    with pytest.raises(ValueError, match="itself"):
        make_matrix({("a", "a"): (0.5, 2)})
    with pytest.raises(ValueError, match="outside"):
        make_matrix({("a", "b"): (1.5, 2)})
    with pytest.raises(ValueError, match="positive"):
        make_matrix({("a", "b"): (0.5, 0)})
