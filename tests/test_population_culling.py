"""Shadow culling and the phone report, on made-up populations."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from spacefight.population.culling import (
    BOTTOM_N,
    DIVERSITY_BONUS_CAP,
    DIVERSITY_BONUS_PER_EDGE,
    FOUNDER_CAP,
    RULE_BOTTOM,
    RULE_FOUNDER_CAP,
    BehaviourFeatures,
    behaviour_log,
    diversity_bonus,
    matched_drills,
    shadow_cull,
    write_shadow_report,
)
from spacefight.population.rating import Rating
from spacefight.population.records import (
    ACTIVE,
    ARCHIVED,
    CLONE,
    FORK,
    HISTORY_FAMILY,
    MEMBERS_DIRNAME,
    SCRIPT_ID,
    UNRELATED,
    DrillEntry,
    Member,
    Population,
    add_member,
    load_population,
    new_founder,
    script_member,
)
from spacefight.population.report import LINE_WIDTH, render_report
from spacefight.population.standings import (
    RoundRobinResults,
    make_matrix,
    transitivity,
)

SHA = "a" * 64
DRILL = "2026-11-02"


def history(member_id: str, parent: str) -> Member:
    return Member(
        id=member_id,
        family=HISTORY_FAMILY,
        founder=SCRIPT_ID,
        parent=parent,
        relation=CLONE,
        fork_update=0,
        settings_changed={},
        checkpoint=f"x/{member_id}.pt",
        sha256=SHA,
        status=ARCHIVED,
        archived_reason="history",
        archived_date="2026-11-01",
    )


def founder(member_id: str, family: str, parent: str = "base") -> Member:
    return new_founder(
        member_id,
        family,
        f"x/{member_id}.pt",
        SHA,
        parent=parent,
        relation=FORK if parent else "",
        fork_update=1 if parent else -1,
    )


def child(member_id: str, parent: Member, depth_parent: str = "") -> Member:
    return Member(
        id=member_id,
        family=parent.family,
        founder=parent.founder,
        parent=depth_parent or parent.id,
        relation=FORK,
        fork_update=1,
        settings_changed={},
        checkpoint=f"x/{member_id}.pt",
        sha256=SHA,
        status=ACTIVE,
    )


def population(*members: Member, tmp: Path = Path("season")) -> Population:
    base = [script_member(), history("base", SCRIPT_ID), *members]
    return Population(tmp, {m.id: m for m in sorted(base, key=lambda m: m.id)})


def ratings(**points: float) -> list[Rating]:
    return [Rating(name, value, 5.0, 100) for name, value in points.items()]


def cull_names(report) -> list[str]:
    return [c.member for c in report.culls]


def test_diversity_bonus_rises_with_distance_up_to_its_cap() -> None:
    assert diversity_bonus(0) == 0.0
    assert diversity_bonus(1) == DIVERSITY_BONUS_PER_EDGE
    assert diversity_bonus(1000) == DIVERSITY_BONUS_CAP
    assert diversity_bonus(UNRELATED) == DIVERSITY_BONUS_CAP
    with pytest.raises(ValueError):
        diversity_bonus(-1)


def test_the_bottom_two_on_combat_would_go() -> None:
    a, b, c, d = (founder(n, n) for n in ("a", "b", "c", "d"))
    report = shadow_cull(
        population(a, b, c, d), ratings(a=300, b=200, c=-100, d=-200), "p", DRILL
    )
    assert cull_names(report) == ["d", "c"]
    assert {c.rule for c in report.culls} == {RULE_BOTTOM}
    assert len(report.culls) == BOTTOM_N


def test_the_bonus_can_save_a_distant_member_over_a_close_relative() -> None:
    # far is a from-scratch line; near_1 and near_2 are the top's close kin. Near_2 rates
    # higher than far, and still goes below it after the bonus.
    top = founder("top", "fighters")
    near_1 = child("near_1", top)
    near_2 = child("near_2", top)
    far = founder("far", "scratch", parent="")
    other = founder("other", "followers")
    report = shadow_cull(
        population(top, near_1, near_2, far, other),
        ratings(top=500, near_1=-50, near_2=-60, far=-90, other=400),
        "p",
        DRILL,
    )
    assert "far" not in cull_names(report)
    rows = {s.member: s for s in report.standings}
    assert rows["far"].tree_distance == UNRELATED
    assert rows["far"].bonus == DIVERSITY_BONUS_CAP
    assert rows["near_1"].tree_distance == 1
    assert rows["near_1"].bonus == DIVERSITY_BONUS_PER_EDGE
    assert cull_names(report) == ["near_2", "near_1"]


def test_one_dominant_family_is_capped() -> None:
    big = founder("big", "fighters")
    kids = [child(f"kid{k}", big) for k in range(7)]
    other_1 = founder("other_1", "followers")
    other_2 = founder("other_2", "scratch", parent="")
    points = {"big": 900.0, "other_1": 100.0, "other_2": 90.0}
    points |= {f"kid{k}": 800.0 - 10.0 * k for k in range(7)}
    # The two others are the weakest, so the bottom two take them and the family's eight
    # all survive that step, over the cap.
    points["other_1"] = -900.0
    points["other_2"] = -950.0
    report = shadow_cull(
        population(big, *kids, other_1, other_2), ratings(**points), "p", DRILL
    )
    bottoms = [c.member for c in report.culls if c.rule == RULE_BOTTOM]
    capped = [c.member for c in report.culls if c.rule == RULE_FOUNDER_CAP]
    assert sorted(bottoms) == ["other_1", "other_2"]
    assert capped == ["kid6", "kid5", "kid4", "kid3"]
    survivors = {s.member for s in report.standings} - set(cull_names(report))
    family = [m for m in survivors if m == "big" or m.startswith("kid")]
    assert len(family) == FOUNDER_CAP
    assert "big" in family
    assert report.founder_counts["big"] == 8


def test_a_family_at_the_cap_is_left_alone() -> None:
    big = founder("big", "fighters")
    kids = [child(f"kid{k}", big) for k in range(3)]
    others = [founder(n, n) for n in ("x", "y", "z")]
    report = shadow_cull(
        population(big, *kids, *others),
        ratings(big=900, kid0=800, kid1=700, kid2=600, x=500, y=-500, z=-600),
        "p",
        DRILL,
    )
    assert all(c.rule == RULE_BOTTOM for c in report.culls)


def test_the_script_stays_while_it_is_not_the_worst_even_at_the_bottom_two() -> None:
    a, b, c = (founder(n, n) for n in ("a", "b", "c"))
    report = shadow_cull(
        population(a, b, c), ratings(a=300, b=200, script=-40, c=-50), "p", DRILL
    )
    assert SCRIPT_ID not in cull_names(report)
    assert cull_names(report) == ["c", "b"]
    assert "not the worst" in report.protected[0].reason


def test_the_worst_script_stays_until_someone_matches_its_drills() -> None:
    a, b, c = (founder(n, n) for n in ("a", "b", "c"))
    points = ratings(a=300, b=200, c=100, script=-500)
    report = shadow_cull(population(a, b, c), points, "p", DRILL)
    assert SCRIPT_ID not in cull_names(report)
    assert "no drill results" in report.protected[0].reason

    script = script_member()
    drilled = _with_drills(script, {"attack": 0.8, "goto": 0.9})
    behind = _with_drills(a, {"attack": 0.9, "goto": 0.5})
    report = shadow_cull(
        Population(
            Path("season"),
            {
                "script": drilled,
                "base": history("base", SCRIPT_ID),
                "a": behind,
                "b": b,
                "c": c,
            },
        ),
        points,
        "p",
        DRILL,
    )
    assert SCRIPT_ID not in cull_names(report)
    assert "nobody has matched" in report.protected[0].reason


def test_the_worst_script_goes_once_another_pilot_has_matched_its_drills() -> None:
    a, b, c = (founder(n, n) for n in ("a", "b", "c"))
    drilled = _with_drills(script_member(), {"attack": 0.8, "goto": 0.9})
    matcher = _with_drills(c, {"attack": 0.8, "goto": 0.95, "extra": 0.1})
    report = shadow_cull(
        Population(
            Path("season"),
            {
                "script": drilled,
                "base": history("base", SCRIPT_ID),
                "a": a,
                "b": b,
                "c": matcher,
            },
        ),
        ratings(a=300, b=200, c=100, script=-500),
        "p",
        DRILL,
    )
    assert report.culls[0].member == SCRIPT_ID
    assert report.protected == ()


def _with_drills(member: Member, scores: dict[str, float]) -> Member:
    return replace(member, drills=(DrillEntry("p", DRILL, scores, True),))


def test_matching_drills_needs_every_drill_the_script_has() -> None:
    assert matched_drills({"a": 0.5}, {"a": 0.5})
    assert not matched_drills({"a": 0.5, "b": 0.5}, {"a": 0.9})
    assert not matched_drills({"a": 0.5}, {"a": 0.4})
    assert not matched_drills({}, {"a": 0.9})


def test_archived_ratings_are_ignored_and_unrated_active_members_are_listed() -> None:
    a, b = founder("a", "a"), founder("b", "b")
    report = shadow_cull(
        population(a, b), ratings(a=10, base=-999, script=5), "p", DRILL
    )
    assert "base" not in {s.member for s in report.standings}
    assert report.unrated == ("b",)
    assert "base" not in cull_names(report)


def test_a_small_population_is_flagged_below_target() -> None:
    a = founder("a", "a")
    assert shadow_cull(population(a), ratings(a=1, script=2), "p", DRILL).below_target
    many = [founder(f"m{k}", f"m{k}") for k in range(9)]
    points = {f"m{k}": float(k) for k in range(9)}
    report = shadow_cull(population(*many), ratings(**points, script=99.0), "p", DRILL)
    assert not report.below_target


def test_a_close_cull_is_flagged_and_a_clear_one_is_not() -> None:
    a, b, c, d = (founder(n, n) for n in ("a", "b", "c", "d"))
    close = shadow_cull(
        population(a, b, c, d), ratings(a=300, b=4, c=3, d=2), "p", DRILL
    )
    assert any(c.close_call for c in close.culls)
    clear = shadow_cull(
        population(a, b, c, d), ratings(a=900, b=800, c=-800, d=-900), "p", DRILL
    )
    assert not any(c.close_call for c in clear.culls)


def test_a_protected_script_below_a_cull_does_not_make_it_look_close() -> None:
    a, b, c = (founder(n, n) for n in ("a", "b", "c"))
    report = shadow_cull(
        population(a, b, c), ratings(a=900, b=100, c=0, script=-800), "p", DRILL
    )
    assert SCRIPT_ID not in cull_names(report)
    assert cull_names(report) == ["c", "b"]
    assert not any(cull.close_call for cull in report.culls)


def test_the_rule_names_nobody_when_it_would_take_every_eligible_pilot() -> None:
    a, b = founder("a", "fighters"), founder("b", "followers")
    report = shadow_cull(population(a, b), ratings(a=9, b=8, script=-1), "p", DRILL)
    assert report.culls == ()
    spared = {p.member: p.reason for p in report.protected}
    assert "only 2 eligible" in spared["a"]
    assert "only 2 eligible" in spared["b"]
    assert "no drill results" in spared[SCRIPT_ID]
    assert report.below_target


def test_a_member_rated_twice_or_unknown_raises() -> None:
    a = founder("a", "a")
    with pytest.raises(ValueError, match="more than once"):
        shadow_cull(
            population(a),
            [Rating("a", 1.0, 1.0, 1), Rating("a", 2.0, 1.0, 1)],
            "p",
            DRILL,
        )
    with pytest.raises(ValueError, match="unknown member"):
        shadow_cull(population(a), ratings(nobody=1.0), "p", DRILL)


def test_shadow_culling_writes_a_report_and_changes_no_record(tmp_path: Path) -> None:
    season = tmp_path / "season"
    add_member(season, script_member())
    add_member(season, history("base", SCRIPT_ID), historical_clone_of_script=True)
    for name in ("a", "b", "c"):
        add_member(season, founder(name, name))
    directory = season / MEMBERS_DIRNAME
    before = {p.name: p.read_bytes() for p in directory.glob("*.json")}

    loaded = load_population(season)
    report = shadow_cull(loaded, ratings(a=9, b=8, c=7, script=-1), "p1", DRILL)
    assert report.culls
    path = write_shadow_report(season, report)

    assert {p.name: p.read_bytes() for p in directory.glob("*.json")} == before
    assert all(m.status == ACTIVE for m in load_population(season).active())
    written = json.loads(path.read_text())
    assert written["schema"] == "rlf.population.shadow/1"
    assert written["culls"]
    with pytest.raises(FileExistsError):
        write_shadow_report(season, report)


FEATURES = {
    "a": BehaviourFeatures(0.1, 0.5, 0.5),
    "a2": BehaviourFeatures(0.11, 0.51, 0.5),
    "b": BehaviourFeatures(0.5, 0.9, 0.1),
}


def test_behaviour_distance_is_logged_beside_tree_distance() -> None:
    a = founder("a", "fighters")
    a2 = child("a2", a)
    b = founder("b", "followers")
    log = behaviour_log(population(a, a2, b), ["a", "a2", "b", "nofeatures"], FEATURES)
    assert log.missing == ("nofeatures",)
    assert (log.pairs[0].a, log.pairs[0].b) == ("a", "a2")
    assert log.pairs[0].tree_distance == 1
    assert log.pairs[0].behaviour_distance < log.pairs[-1].behaviour_distance
    assert log.correlation_pairs == 3
    assert log.tree_behaviour_correlation > 0.0


def test_a_report_without_features_says_so_rather_than_failing() -> None:
    a = founder("a", "a")
    report = shadow_cull(population(a), ratings(a=1.0, script=2.0), "p", DRILL)
    assert report.behaviour.pairs == ()
    assert set(report.behaviour.missing) == {"a", SCRIPT_ID}


def test_non_finite_behaviour_features_are_refused() -> None:
    with pytest.raises(ValueError, match="fire_rate"):
        BehaviourFeatures(float("nan"), 0.5, 0.5)


def full_report_inputs() -> tuple[Population, RoundRobinResults, object]:
    a = founder("a_rather_long_member_name", "fighters")
    b = founder("b", "followers")
    c = founder("c", "scratch", parent="")
    pop = population(a, b, c)
    names = (a.id, "b", "c", SCRIPT_ID)
    matrix = make_matrix(
        {
            (names[0], "b"): (0.8, 100),
            ("b", "c"): (0.7, 100),
            ("c", names[0]): (0.6, 100),
            (SCRIPT_ID, names[0]): (0.2, 100),
            (SCRIPT_ID, "b"): (0.2, 100),
            (SCRIPT_ID, "c"): (0.2, 100),
        },
        names,
    )
    rated = tuple(
        Rating(name, 100.0 - 50.0 * k, 12.0, 300) for k, name in enumerate(names)
    )
    features = {
        names[0]: BehaviourFeatures(0.1, 0.5, 0.5),
        "b": BehaviourFeatures(0.2, 0.6, 0.6),
        "c": BehaviourFeatures(0.9, 0.2, 0.1),
        SCRIPT_ID: BehaviourFeatures(0.3, 0.7, 0.2),
    }
    results = RoundRobinResults(
        members=names,
        by_mission={"deathmatch": matrix},
        overall=matrix,
        transitivity_by_mission={"deathmatch": transitivity(matrix)},
        transitivity_overall=transitivity(matrix),
        ratings=rated,
        behaviour=features,
        pairs=6,
        matches=600,
        secs=60.0,
    )
    shadow = shadow_cull(pop, rated, "first", DRILL, features)
    return pop, results, shadow


def test_the_report_names_the_tree_ratings_cycles_and_would_be_culls() -> None:
    pop, results, shadow = full_report_inputs()
    text = render_report(pop, "first", DRILL, results, shadow, ["A small test run."])
    for heading in (
        "## Family tree",
        "## Combat ratings",
        "## Is there variety to protect?",
        "## Who beats whom",
        "## Would-be culls (first)",
        "## Tree against behaviour",
    ):
        assert heading in text
    assert "Shadow mode: nobody was culled" in text
    assert "A small test run." in text
    assert "Cycles: 1 of" in text


def test_the_report_reads_on_a_phone_with_short_lines_and_no_tables() -> None:
    pop, results, shadow = full_report_inputs()
    text = render_report(pop, "first", DRILL, results, shadow)
    assert "|" not in text
    assert "```" not in text
    # Indented bullets may add a little to the wrap width.
    assert max(len(line) for line in text.splitlines()) <= LINE_WIDTH + 8


def test_the_report_folds_a_chain_of_history_into_one_bullet() -> None:
    deep = Population(
        Path("season"),
        {
            "script": script_member(),
            "h1": history("h1", SCRIPT_ID),
            "h2": history("h2", "h1"),
            "h3": history("h3", "h2"),
            "a": founder("a", "fighters", parent="h3"),
        },
    )
    text = render_report(deep)
    assert "h1 > h2 > h3 > **a** (fighters, active)" in text.replace("\n", " ").replace(
        "  ", " "
    )
    assert "No ratings yet." in text
