"""Population records and the family tree (no sim, no weights)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from spacefight.population.__main__ import main
from spacefight.population.records import (
    ARCHIVED,
    CLONE,
    FORK,
    HISTORY_FAMILY,
    NO_FORK,
    NO_RELATION,
    SCRIPT_ID,
    UNRELATED,
    DrillEntry,
    Member,
    PopulationError,
    RatingEntry,
    add_member,
    load_population,
    member_path,
    new_founder,
    record_drills,
    record_ratings,
    resolve_checkpoint,
    script_member,
    sha256_of,
    write_member,
)

SEASON_ON_DISK = Path(__file__).resolve().parents[1] / "lab/population/2026-11-sim6"
SHA = "a" * 64


def clone_of_script(member_id: str = "clone") -> Member:
    return Member(
        id=member_id,
        family=HISTORY_FAMILY,
        founder=SCRIPT_ID,
        parent=SCRIPT_ID,
        relation=CLONE,
        fork_update=0,
        settings_changed={},
        checkpoint=f"lab/runs/x/{member_id}.pt",
        sha256=SHA,
        status=ARCHIVED,
        archived_reason="history",
        archived_date="2026-11-01",
    )


def founder_from(parent: str, member_id: str, family: str) -> Member:
    return new_founder(
        member_id,
        family,
        f"lab/runs/x/{member_id}.pt",
        SHA,
        parent=parent,
        relation=FORK,
        fork_update=10,
    )


def child_of(parent: Member, member_id: str) -> Member:
    return Member(
        id=member_id,
        family=parent.family,
        founder=parent.founder,
        parent=parent.id,
        relation=FORK,
        fork_update=5,
        settings_changed={"gamma": 0.995},
        checkpoint=f"lab/runs/x/{member_id}.pt",
        sha256=SHA,
        status="active",
    )


@pytest.fixture
def season(tmp_path: Path) -> Path:
    """script > clone > founder_a > child_a; clone > founder_b; a separate scratch."""
    directory = tmp_path / "test-season"
    add_member(directory, script_member())
    add_member(directory, clone_of_script(), historical_clone_of_script=True)
    founder_a = founder_from("clone", "founder_a", "fighters")
    add_member(directory, founder_a)
    add_member(directory, child_of(founder_a, "child_a"))
    add_member(directory, founder_from("clone", "founder_b", "followers"))
    add_member(directory, new_founder("scratch", "scratch", "lab/runs/x/s.pt", SHA))
    return directory


def edit_record(directory: Path, member_id: str, **changes: object) -> None:
    path = member_path(directory, member_id)
    data = json.loads(path.read_text())
    data.update(changes)
    path.write_text(json.dumps(data))


def test_records_round_trip_through_their_files(season: Path) -> None:
    population = load_population(season)
    assert sorted(population.members) == [
        "child_a",
        "clone",
        "founder_a",
        "founder_b",
        "scratch",
        "script",
    ]
    assert population.member("child_a").settings_changed == {"gamma": 0.995}
    assert population.season == "test-season"
    assert [m.id for m in population.children("clone")] == ["founder_a", "founder_b"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"schema": "wrong"}, "schema"),
        ({"status": "retired"}, "unknown status"),
        ({"sha256": "abc"}, "sha256"),
        ({"checkpoint": "/abs/path.pt"}, "relative"),
        ({"checkpoint": "../up.pt"}, "relative"),
        ({"checkpoint": "script"}, "flies the script"),
        ({"parent": "nobody"}, "unknown parent"),
        ({"founder": "nobody"}, "unknown founder"),
        ({"fork_update": -1}, "fork update"),
        ({"relation": "adopted"}, "relation"),
        ({"archived_reason": "because"}, "active member"),
        ({"surprise": 1}, "bad record"),
        ({"family": "other"}, "differs from its founder"),
    ],
)
def test_a_bad_record_raises_at_load_rather_than_being_skipped(
    season: Path, change: dict[str, object], message: str
) -> None:
    edit_record(season, "child_a", **change)
    with pytest.raises(PopulationError, match=message):
        load_population(season)


def test_a_record_with_invalid_json_raises(season: Path) -> None:
    member_path(season, "child_a").write_text("{not json")
    with pytest.raises(PopulationError, match="not JSON"):
        load_population(season)


def test_a_file_named_differently_from_its_member_raises(season: Path) -> None:
    text = member_path(season, "child_a").read_text()
    (member_path(season, "child_a").parent / "other.json").write_text(text)
    with pytest.raises(PopulationError, match="holds member"):
        load_population(season)


def test_an_ancestry_cycle_raises(season: Path) -> None:
    edit_record(season, "founder_a", parent="child_a")
    with pytest.raises(PopulationError, match="cycle"):
        load_population(season)


def test_an_archived_member_needs_a_reason_and_date(season: Path) -> None:
    edit_record(season, "child_a", status=ARCHIVED)
    with pytest.raises(PopulationError, match="without a reason"):
        load_population(season)


def test_add_member_refuses_a_child_of_the_script(season: Path) -> None:
    with pytest.raises(PopulationError, match="cannot have children"):
        add_member(season, clone_of_script("clone2"))
    assert not member_path(season, "clone2").exists()


def test_load_refuses_an_active_or_trained_child_of_the_script(season: Path) -> None:
    active = replace(
        clone_of_script("rogue"),
        family="fighters",
        founder="founder_a",
        status="active",
        archived_reason="",
        archived_date="",
    )
    write_member(season, active)
    with pytest.raises(PopulationError, match="script cannot have children"):
        load_population(season)


def test_load_refuses_a_forked_child_of_the_script(season: Path) -> None:
    write_member(season, replace(clone_of_script("rogue"), relation=FORK))
    with pytest.raises(PopulationError, match="script cannot have children"):
        load_population(season)


def test_add_member_refuses_a_duplicate(season: Path) -> None:
    with pytest.raises(PopulationError, match="already exists"):
        add_member(season, founder_from("clone", "founder_a", "fighters"))


def test_only_the_script_id_may_fly_the_script(season: Path) -> None:
    impostor = new_founder("impostor", "script", "script", "")
    with pytest.raises(PopulationError, match="flies the script"):
        add_member(season, impostor)


def test_a_history_pilot_cannot_be_active(season: Path) -> None:
    edit_record(season, "clone", status="active", archived_reason="", archived_date="")
    with pytest.raises(PopulationError, match="always archived"):
        load_population(season)


def test_a_child_cannot_claim_another_family_founder(season: Path) -> None:
    parent = load_population(season).member("founder_a")
    wrong = replace(child_of(parent, "wrong"), family="followers", founder="founder_b")
    with pytest.raises(PopulationError, match="differs from its parent"):
        add_member(season, wrong)


def test_tree_distance_counts_edges_through_the_nearest_common_ancestor(
    season: Path,
) -> None:
    population = load_population(season)
    assert population.tree_distance("founder_a", "founder_a") == 0
    assert population.tree_distance("founder_a", "child_a") == 1
    assert population.tree_distance("child_a", "founder_a") == 1
    assert population.tree_distance("founder_a", "founder_b") == 2
    assert population.tree_distance("child_a", "founder_b") == 3
    assert population.tree_distance("child_a", SCRIPT_ID) == 3


def test_a_from_scratch_line_is_unrelated_to_everyone(season: Path) -> None:
    population = load_population(season)
    assert population.tree_distance("scratch", SCRIPT_ID) == UNRELATED
    assert population.tree_distance("child_a", "scratch") == UNRELATED
    assert population.member("scratch").parent == ""
    assert population.member("scratch").fork_update == NO_FORK
    assert population.member("scratch").relation == NO_RELATION


def test_resolve_checkpoint_checks_the_hash(tmp_path: Path) -> None:
    weights = tmp_path / "lab/w.pt"
    weights.parent.mkdir()
    weights.write_bytes(b"weights")
    member = new_founder("a", "f", "lab/w.pt", sha256_of(weights))
    assert resolve_checkpoint(member, tmp_path) == weights
    weights.write_bytes(b"other weights")
    with pytest.raises(PopulationError, match="changed"):
        resolve_checkpoint(member, tmp_path)
    weights.unlink()
    with pytest.raises(FileNotFoundError):
        resolve_checkpoint(member, tmp_path)
    with pytest.raises(PopulationError, match="no checkpoint"):
        resolve_checkpoint(script_member(), tmp_path)


def test_history_appends_per_phase_and_refuses_a_repeat(season: Path) -> None:
    rating = RatingEntry("p1", "2026-11-02", 12.0, 3.0, 40)
    record_ratings(season, {"child_a": rating})
    record_drills(
        season, {"child_a": DrillEntry("p1", "2026-11-02", {"attack": 0.7}, True)}
    )
    member = load_population(season).member("child_a")
    assert member.ratings == (rating,)
    assert member.drills[0].scores == {"attack": 0.7}
    assert member.status == "active"
    with pytest.raises(PopulationError, match="already rated"):
        record_ratings(season, {"child_a": rating})


def test_the_committed_season_holds_the_plans_founders_and_true_ancestry() -> None:
    population = load_population(SEASON_ON_DISK)
    # The season grows every phase, so this names only who must always be there.
    assert {m.id for m in population.active()} >= {
        SCRIPT_ID,
        "f995_701",
        "transit_300",
    }
    assert population.lineage("f995_701") == [
        "f995_701",
        "f995_400",
        "reward_300",
        "w1_400",
        "v1",
        "v1_clone",
        "v3_600",
        "spike_1200",
        "spike_clone",
        SCRIPT_ID,
    ]
    assert population.lineage("transit_300")[:3] == ["transit_300", "w1_400", "v1"]
    assert population.tree_distance("f995_701", "transit_300") == 4
    for member in population.members.values():
        if member.id != SCRIPT_ID and member.family != "scratch":
            assert SCRIPT_ID in population.lineage(member.id)


def test_cli_lists_the_tree_and_adds_a_founder(
    season: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    weights = tmp_path / "w.pt"
    weights.write_bytes(b"weights")
    assert main(["list", "--season", str(season)]) == 0
    assert "founder_a" in capsys.readouterr().out
    code = main(
        [
            "add-founder",
            "--season",
            str(season),
            "--id",
            "new_line",
            "--family",
            "newline",
            "--checkpoint",
            "w.pt",
            "--checkpoint-root",
            str(tmp_path),
        ]
    )
    assert code == 0
    assert load_population(season).member("new_line").is_founder


def test_cli_reports_a_refused_founder_instead_of_tracing(
    season: Path, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "w.pt").write_bytes(b"weights")
    code = main(
        [
            "add-founder",
            "--season",
            str(season),
            "--id",
            "script_child",
            "--family",
            "bad",
            "--checkpoint",
            "w.pt",
            "--checkpoint-root",
            str(tmp_path),
            "--parent",
            SCRIPT_ID,
            "--fork-update",
            "0",
        ]
    )
    assert code == 2
    assert "cannot have children" in capsys.readouterr().err


def test_cli_adds_a_child_under_its_parents_founder_and_archives_it(
    season: Path, tmp_path: Path
) -> None:
    checkpoint = tmp_path / "x.pt"
    checkpoint.write_bytes(b"weights")
    common = ["--season", str(season)]
    code = main(
        [
            "add-child",
            *common,
            "--id",
            "grandchild",
            "--parent",
            "child_a",
            "--fork-update",
            "50",
            "--checkpoint",
            "x.pt",
            "--checkpoint-root",
            str(tmp_path),
        ]
    )
    assert code == 0
    member = load_population(season).member("grandchild")
    assert (member.family, member.founder) == ("fighters", "founder_a")
    assert (member.parent, member.fork_update) == ("child_a", 50)
    assert member.is_active

    archive = ["archive", *common, "--id", "grandchild", "--reason", "gate"]
    assert main([*archive, "--date", "2026-11-02"]) == 0
    member = load_population(season).member("grandchild")
    assert (member.status, member.archived_reason) == ("archived", "gate")
    assert main([*archive, "--date", "2026-11-03"]) == 2, "already archived"

    restore = ["restore", *common, "--id", "grandchild", "--reason", "gate dropped"]
    assert main([*restore, "--date", "2026-11-07"]) == 0
    member = load_population(season).member("grandchild")
    assert member.is_active and not member.archived_reason
    assert "Archived 2026-11-02: gate Restored 2026-11-07: gate dropped" in member.note
    assert main([*restore, "--date", "2026-11-08"]) == 2, "not archived"


def test_cli_records_drills_judged_by_the_bars_it_is_given(
    season: Path, tmp_path: Path
) -> None:
    rate = {"rate": 0.8}
    kinds = {
        "goto": {"shown": rate, "lift": 0.8},
        "attack": {"target_hit": rate, "chose_named": rate, "flip": rate},
        "defend": {"more_on_named": rate, "chose_named": rate, "flip": rate},
    }
    drills = tmp_path / "drills.json"
    drills.write_text(json.dumps({"kinds": kinds}))
    bars = tmp_path / "bars.yaml"
    names = (
        "goto_arrival",
        "goto_lift",
        "attack_target_hit",
        "attack_side",
        "attack_flip",
        "defend_more_on_named",
        "defend_side",
    )
    bars.write_text("".join(f"{n}: 0.5\n" for n in names) + "defend_flip: 0.5\n")
    base = ["record-drills", "--season", str(season), "--drills", str(drills)]
    base += ["--bars", str(bars), "--date", "2026-11-02"]
    assert main([*base, "--id", "child_a", "--phase", "p1"]) == 0
    entry = load_population(season).member("child_a").drills[-1]
    assert entry.passed
    assert entry.scores["defend_flip"] == pytest.approx(0.8)

    bars.write_text("defend_flip: 0.9\n")
    assert main([*base, "--id", "child_a", "--phase", "p2"]) == 0
    assert not load_population(season).member("child_a").drills[-1].passed
