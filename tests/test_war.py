"""Wins above replacement: the fit on made-up matches, the WAR cull rule, the report,
choosing live pilots by WAR, and the war-fit command's JSON round trip."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from spacefight.population.__main__ import main
from spacefight.population.culling import (
    ACTIVE_CAP,
    FOUNDER_CAP,
    RULE_BELOW_REPLACEMENT,
    RULE_FOUNDER_CAP,
    RULE_OVER_CAP,
    war_shadow_cull,
    write_shadow_report,
)
from spacefight.population.records import (
    ARCHIVED,
    SCRIPT_ID,
    Member,
    Population,
    new_child,
    new_founder,
    script_member,
)
from spacefight.population.report import render_report
from spacefight.population.war import (
    DRAW,
    MatchRecord,
    PilotWar,
    WarDocument,
    build_design,
    fit_logistic,
    fit_war,
    read_war,
    write_war,
)
from tools.live_pilots import LivePilotsError, select_members_by_war

SHA = "a" * 64
TRUE = {"ace": 0.6, "even": 0.0, "weak": -0.4}
SIDES = {"r0": 0.0, "r1": 0.5, "r2": -0.5}


def synthetic(
    n: int, seed: int = 1, coefs: dict[str, float] = TRUE, draw_share: float = 0.05
) -> list[MatchRecord]:
    """Matches whose result follows the module's model with known coefficients."""
    rng = np.random.default_rng(seed)
    pool = [*coefs, SCRIPT_ID]
    records = []
    for i in range(n):
        mission = ("deathmatch", "carrier_battle")[i % 2]
        roster = f"r{i % 3}"
        ships: tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]] = ({}, {})
        eta = SIDES[roster]
        for team, sign in ((0, 1.0), (1, -1.0)):
            for _ in range(4):
                pilot = pool[int(rng.integers(len(pool)))]
                hulls = ships[team].setdefault(pilot, {})
                hulls["fighter"] = hulls.get("fighter", 0) + 1
                eta += sign * coefs.get(pilot, 0.0)
        p = 1.0 / (1.0 + np.exp(-eta))
        u = rng.random()
        if u < draw_share:
            winner = DRAW
        else:
            winner = 0 if rng.random() < p else 1
        records.append(
            MatchRecord(mission, roster, ("scripted", "scripted"), ships, winner)
        )
    return records


@pytest.fixture(scope="module")
def big_fit():
    return fit_war(synthetic(4000), n_bootstrap=40)


def test_the_fit_recovers_known_per_ship_coefficients(big_fit) -> None:
    for pilot, coef in TRUE.items():
        got = big_fit.pilot(pilot)
        assert abs(got.coef - coef) < 3 * got.coef_sd + 0.02, (pilot, got.coef)
        assert got.prior_weight < 0.01, "at this size the data decides, not the prior"
    for name, side in SIDES.items():
        for mission in ("deathmatch", "carrier_battle"):
            assert abs(big_fit.nuisance[f"side {mission} / {name}"] - side) < 0.25


def test_the_script_is_exactly_replacement(big_fit) -> None:
    script = big_fit.pilot(SCRIPT_ID)
    assert (script.war, script.coef, script.ci_low, script.ci_high) == (0, 0, 0, 0)
    assert script.ships > 0 and script.matches > 0
    assert SCRIPT_ID not in build_design(synthetic(20)).pilots


def test_war_has_the_right_sign_order_and_an_interval_around_it(big_fit) -> None:
    ace, even, weak = (big_fit.pilot(p) for p in ("ace", "even", "weak"))
    assert ace.war > 5.0 and weak.war < -5.0 and abs(even.war) < 3.0
    order = [p.pilot for p in big_fit.pilots]
    assert order[0] == "ace" and order[-1] == "weak"
    for p in (ace, even, weak):
        assert p.ci_low <= p.war <= p.ci_high
        assert p.se > 0.0
    assert ace.ci_low > 0.0 > weak.ci_high
    assert set(ace.by_mission) == {"deathmatch", "carrier_battle"}


def _one_pilot_matches(wins_per_side: int, n_per_side: int) -> list[MatchRecord]:
    """``ace``'s one ship against the script's, on each side equally often."""
    records = []
    for ace_team in (0, 1):
        for k in range(n_per_side):
            ships: tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]] = (
                {},
                {},
            )
            ships[ace_team]["ace"] = {"fighter": 1}
            ships[1 - ace_team][SCRIPT_ID] = {"fighter": 1}
            winner = ace_team if k < wins_per_side else 1 - ace_team
            records.append(
                MatchRecord("deathmatch", "r", ("scripted", "scripted"), ships, winner)
            )
    return records


def test_war_reads_as_wins_added_per_100_matches() -> None:
    # Winning 3 in 4 where the script would win 1 in 2 is 25 wins per 100 added.
    fit = fit_war(_one_pilot_matches(300, 400), prior_sd=10.0, n_bootstrap=20)
    ace = fit.pilot("ace")
    assert ace.war == pytest.approx(25.0, abs=0.2)
    assert ace.coef == pytest.approx(np.log(3.0), abs=0.02)
    assert ace.matches == 800 and ace.ships == 800
    losing = fit_war(_one_pilot_matches(100, 400), prior_sd=10.0, n_bootstrap=20)
    assert losing.pilot("ace").war == pytest.approx(-25.0, abs=0.2)


def test_a_draw_is_two_half_weight_rows() -> None:
    records = synthetic(300, seed=3, draw_share=0.3)
    design = build_design(records)
    assert any(r.winner == DRAW for r in records)
    assert set(design.score) == {0.0, 0.5, 1.0}
    precision = np.ones(design.x.shape[1])
    theta, _ = fit_logistic(design.x, design.score, precision)
    # Every match twice; a draw as one win and one loss. Doubling the data doubles the
    # likelihood, so the prior doubles too for the same posterior mode.
    doubled_x = np.vstack([design.x, design.x])
    doubled_y = np.concatenate(
        [
            np.where(design.score == 0.5, 1.0, design.score),
            np.where(design.score == 0.5, 0.0, design.score),
        ]
    )
    doubled, _ = fit_logistic(doubled_x, doubled_y, 2.0 * precision)
    np.testing.assert_allclose(theta, doubled, atol=1e-9)
    assert fit_war(records, n_bootstrap=5).draws == sum(
        r.winner == DRAW for r in records
    )


def test_commanders_get_a_term_per_mission_against_the_scripted_one() -> None:
    records = synthetic(200, seed=4)
    records[0] = replace(records[0], commanders=("random", "scripted"))
    records[1] = replace(records[1], commanders=("scripted", "random"))
    design = build_design(records)
    assert "commander random in deathmatch" in design.nuisance
    assert "commander random in carrier_battle" in design.nuisance
    assert not any("scripted" in name for name in design.nuisance)
    column = design.nuisance.index("commander random in deathmatch")
    assert design.nuisance_x[0, column] == 1.0


def test_records_round_trip_and_bad_ones_are_refused() -> None:
    record = synthetic(1)[0]
    assert MatchRecord.from_dict(json.loads(json.dumps(record.to_dict()))) == record
    with pytest.raises(ValueError, match="winner"):
        replace(record, winner=2)
    with pytest.raises(ValueError, match="ship counts"):
        replace(record, ships=({"ace": {"fighter": 0}}, {}))
    with pytest.raises(ValueError, match="bad match record"):
        MatchRecord.from_dict({"mission": "deathmatch"})
    with pytest.raises(ValueError, match="only the script"):
        build_design([replace(record, ships=({SCRIPT_ID: {"fighter": 1}}, {}))])


def test_war_fit_refits_the_saved_matches_and_round_trips(tmp_path: Path) -> None:
    records = tuple(synthetic(400, seed=5))
    first = fit_war(records, n_bootstrap=10)
    path, table = write_war(
        tmp_path / "run" / "war.json", WarDocument({"seed": 1}, records, first), "test"
    )
    assert read_war(path).fit == first
    assert "| Pilot | WAR |" in table.read_text()

    out = tmp_path / "refit" / "war.json"
    code = main(
        ["war-fit", "--war", str(path), "--out", str(out), "--bootstrap", "12"]
        + ["--prior-sd", "0.5", "--bootstrap-seed", "3"]
    )
    assert code == 0
    again = read_war(out)
    assert again.records == records
    assert again.config == {"seed": 1}
    assert again.fit == fit_war(records, 0.5, n_bootstrap=12, bootstrap_seed=3)
    assert out.with_suffix(".md").is_file()
    with pytest.raises(ValueError, match="schema"):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"schema": "x"}))
        read_war(bad)


# ----- the WAR cull rule ------------------------------------------------------------


def pilot_war(name: str, war: float, half_width: float = 3.0) -> PilotWar:
    return PilotWar(
        pilot=name,
        war=war,
        ci_low=war - half_width,
        ci_high=war + half_width,
        se=half_width / 2,
        coef=war / 50,
        coef_sd=0.05,
        prior_weight=0.01,
        matches=500,
        ships=700,
    )


def script_war() -> PilotWar:
    return replace(pilot_war(SCRIPT_ID, 0.0, 0.0), coef=0.0, se=0.0)


def member(name: str, family: str) -> Member:
    return new_founder(name, family, f"x/{name}.pt", SHA)


def kid(name: str, parent: Member) -> Member:
    return new_child(parent, name, f"x/{name}.pt", SHA, 1)


def season(*members: Member) -> Population:
    every = [script_member(), *members]
    return Population(
        Path("season"), {m.id: m for m in sorted(every, key=lambda m: m.id)}
    )


def culled(report) -> dict[str, str]:
    return {c.member: c.rule for c in report.culls}


def test_a_pilot_surely_below_replacement_would_go_and_the_script_never() -> None:
    pop = season(member("good", "a"), member("bad", "b"), member("unsure", "c"))
    report = war_shadow_cull(
        pop,
        [
            pilot_war("good", 8.0),
            pilot_war("bad", -6.0),
            pilot_war("unsure", -2.0),
            script_war(),
        ],
        "p",
        "2026-11-09",
    )
    assert culled(report) == {"bad": RULE_BELOW_REPLACEMENT}
    assert [p.member for p in report.protected] == [SCRIPT_ID]
    assert [s.member for s in report.standings] == ["good", "unsure", "bad"]
    assert not report.leaves_no_pilot


def test_one_founder_over_its_cap_loses_its_lowest() -> None:
    lead = member("f0", "fighters")
    kids = [kid(f"f{k}", lead) for k in range(1, FOUNDER_CAP + 2)]
    pop = season(lead, *kids, member("other", "followers"))
    wars = [pilot_war(m.id, 20.0 - k) for k, m in enumerate([lead, *kids])]
    report = war_shadow_cull(pop, [*wars, pilot_war("other", 1.0)], "p", "2026-11-09")
    assert culled(report) == {
        m.id: RULE_FOUNDER_CAP for m in [lead, *kids][FOUNDER_CAP:]
    }


def test_over_the_cap_the_lowest_goes_but_the_last_of_a_family_stays() -> None:
    names = [f"m{k}" for k in range(ACTIVE_CAP + 1)]
    # Every member founds its own line in one of two families, so no founder cap.
    members = [member(n, "fighters") for n in names[:-1]] + [
        member(names[-1], "scratch")
    ]
    pop = season(*members)
    wars = [pilot_war(n, 30.0 - k) for k, n in enumerate(names)]
    report = war_shadow_cull(pop, [*wars, script_war()], "p", "2026-11-09")
    # The lowest is the only scratch pilot, so the next lowest goes in its place.
    assert culled(report) == {names[-2]: RULE_OVER_CAP}
    assert any(
        p.member == names[-1] and "last of family scratch" in p.reason
        for p in report.protected
    )
    assert report.culls[0].close_call, "1 WAR apart with an sd of 1.5 is noise"


def test_archived_pilots_are_not_judged_and_unmeasured_ones_are_listed() -> None:
    gone = replace(
        member("gone", "a"),
        status=ARCHIVED,
        archived_reason="x",
        archived_date="2026-11-01",
    )
    pop = season(gone, member("new", "b"), member("rated", "c"))
    report = war_shadow_cull(
        pop, [pilot_war("gone", -50.0), pilot_war("rated", 2.0)], "p", "2026-11-09"
    )
    assert not report.culls
    assert report.unmeasured == ("new",)
    with pytest.raises(ValueError, match="more than once"):
        war_shadow_cull(pop, [pilot_war("rated", 1.0)] * 2, "p", "2026-11-09")


def test_the_war_shadow_report_is_written_and_reads_on_a_phone(tmp_path: Path) -> None:
    pop = replace(season(member("good", "a"), member("bad", "b")), season_dir=tmp_path)
    pilots = [pilot_war("good", 8.0), pilot_war("bad", -6.0), script_war()]
    report = war_shadow_cull(pop, pilots, "p1", "2026-11-09", "war.json")
    path = write_shadow_report(tmp_path, report)
    assert json.loads(path.read_text())["schema"] == "rlf.population.shadow_war/1"
    fit = replace(fit_war(synthetic(100), n_bootstrap=5), pilots=tuple(pilots))
    text = render_report(pop, "p1", "2026-11-09", war=fit, war_shadow=report)
    assert "## Wins above replacement" in text
    assert "## Would-be culls on WAR (p1)" in text
    assert "**bad**, Below replacement" in text
    assert "## Combat ratings" not in text
    assert "|" not in text


# ----- choosing live pilots by WAR --------------------------------------------------


def test_live_pilots_can_be_chosen_by_war(tmp_path: Path) -> None:
    pop = season(member("ace", "a"), member("mid", "b"), member("low", "c"))
    pilots = (
        pilot_war("low", -3.0),
        pilot_war("ace", 9.0),
        script_war(),
        pilot_war("mid", 1.0),
    )
    fit = replace(fit_war(synthetic(100), n_bootstrap=5), pilots=pilots)
    path, _ = write_war(tmp_path / "war.json", WarDocument({}, (), fit))
    chosen = select_members_by_war(pop, path, 2)
    assert [(m.id, war) for m, war in chosen] == [("ace", 9.0), ("mid", 1.0)]
    stranger = replace(fit, pilots=(*pilots, pilot_war("stranger", 50.0)))
    write_war(path, WarDocument({}, (), stranger))
    with pytest.raises(LivePilotsError, match="not members"):
        select_members_by_war(pop, path, 2)
