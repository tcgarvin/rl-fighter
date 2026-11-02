"""Population records: one plain JSON file per member, and the family tree.

A season lives under ``lab/population/<season>/`` with ``members/<id>.json`` (schema
``rlf.population.member/1``). Records are committed; weights are not: ``checkpoint`` is
a path relative to a checkpoint root (a checkout holding ``lab/runs``), and ``sha256``
pins the file's content.

Loading validates every record and the whole tree, and a bad record raises
``PopulationError`` rather than being skipped.

**Who counts as what.**

- ``founder`` is the id of the member a family starts from; a founder names itself.
  A founder's ``parent`` may be outside its family (``f995_701``'s is in ``history``)
  or empty (a from-scratch line, unrelated to everyone else).
- ``family`` ``history`` holds pilots from before the population, kept because tree
  distance needs them and the first round robin plays some of them. They are always
  archived, and their ``founder`` is the script.
- ``relation`` says what the edge to ``parent`` is: ``clone`` (behaviour cloning, with
  the parent as teacher or as starting weights), ``fork`` (PPO from the parent's
  weights) or ``continued`` (a later checkpoint of the same run).

**The script has no children, with one historical exception.** It does not train, so no
new member may name it as parent (``add_member`` refuses, and validation refuses an
active child). All neural pilots do descend from it, though: the first neural pilot
began as a clone of it. That edge is real and tree distance needs it, so validation
allows the script as parent only on an archived record with relation ``clone``.

**Tree distance** between two members is the number of edges on the path between them
through their nearest common ancestor: 1 for parent and child, 2 for siblings. Members
in different trees are ``UNRELATED``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Any, Final

MEMBER_SCHEMA: Final = "rlf.population.member/1"
MEMBERS_DIRNAME: Final = "members"

SCRIPT_ID: Final = "script"
SCRIPT_CHECKPOINT: Final = "script"
SCRIPT_FAMILY: Final = "script"
HISTORY_FAMILY: Final = "history"

ACTIVE: Final = "active"
ARCHIVED: Final = "archived"
STATUSES: Final = (ACTIVE, ARCHIVED)

# ``relation`` values. A member with no parent has relation ``NO_RELATION``.
NO_RELATION: Final = ""
CLONE: Final = "clone"
FORK: Final = "fork"
CONTINUED: Final = "continued"
RELATIONS: Final = (CLONE, FORK, CONTINUED)

# ``fork_update`` of a member with no parent.
NO_FORK: Final = -1
# Tree distance between members of different trees; larger than any real path.
UNRELATED: Final = sys.maxsize

_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PopulationError(ValueError):
    """A population record or the tree they form is invalid."""


@dataclass(frozen=True)
class RatingEntry:
    """A member's combat rating at the end of one phase.

    Attributes:
        phase: Phase name.
        date: ``YYYY-MM-DD``.
        rating: Rating points (``rating.py``), relative to that phase's field.
        sd: One standard deviation of the rating.
        matches: Matches behind it.
    """

    phase: str
    date: str
    rating: float
    sd: float
    matches: int


@dataclass(frozen=True)
class DrillEntry:
    """A member's drill results at the end of one phase.

    Attributes:
        phase: Phase name.
        date: ``YYYY-MM-DD``.
        scores: Drill name -> result, higher is better.
        passed: Whether it passed the drill gate.
    """

    phase: str
    date: str
    scores: dict[str, float]
    passed: bool


@dataclass(frozen=True)
class Member:
    """One pilot of the population (module docstring).

    Attributes:
        id: Unique lower-case id, also the file name.
        family: Family name.
        founder: Id of the family's founder (its own id if this is the founder).
        parent: Parent's id, or empty for a tree root.
        relation: What the edge to ``parent`` is, or ``NO_RELATION``.
        fork_update: The parent's update at the fork, or ``NO_FORK``.
        settings_changed: Training settings changed from the parent.
        checkpoint: Path relative to a checkpoint root, or ``SCRIPT_CHECKPOINT``.
        sha256: Checkpoint content hash; empty for the script.
        status: ``active`` or ``archived``.
        archived_reason: Why it was archived; empty if active.
        archived_date: When (``YYYY-MM-DD``); empty if active.
        note: Free text about where the pilot came from.
        ratings: Combat ratings per phase, oldest first.
        drills: Drill results per phase, oldest first.
    """

    id: str
    family: str
    founder: str
    parent: str
    relation: str
    fork_update: int
    settings_changed: dict[str, Any]
    checkpoint: str
    sha256: str
    status: str
    archived_reason: str = ""
    archived_date: str = ""
    note: str = ""
    ratings: tuple[RatingEntry, ...] = ()
    drills: tuple[DrillEntry, ...] = ()

    @property
    def is_script(self) -> bool:
        """Whether this is the script pilot."""
        return self.id == SCRIPT_ID

    @property
    def is_founder(self) -> bool:
        """Whether this member starts its family."""
        return self.founder == self.id

    @property
    def is_active(self) -> bool:
        """Whether it is in the population now."""
        return self.status == ACTIVE

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict, schema first."""
        return {"schema": MEMBER_SCHEMA, **asdict(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Member:
        """Parse and validate one record (tree checks are ``validate_tree``'s).

        Raises:
            PopulationError: Wrong schema, missing or unknown keys, wrong types or
                inconsistent fields.
        """
        raw = dict(data)
        schema = raw.pop("schema", "")
        if schema != MEMBER_SCHEMA:
            raise PopulationError(f"expected schema {MEMBER_SCHEMA!r}, got {schema!r}")
        try:
            ratings = tuple(RatingEntry(**r) for r in raw.pop("ratings", ()))
            drills = tuple(DrillEntry(**d) for d in raw.pop("drills", ()))
            member = cls(**raw, ratings=ratings, drills=drills)
        except TypeError as err:
            raise PopulationError(f"bad record {data.get('id')!r}: {err}") from err
        validate_member(member)
        return member


def _require(condition: bool, member: Member, problem: str) -> None:
    if not condition:
        raise PopulationError(f"member {member.id!r}: {problem}")


def _check_types(member: Member) -> None:
    for name in (
        "id",
        "family",
        "founder",
        "parent",
        "relation",
        "checkpoint",
        "sha256",
        "status",
        "archived_reason",
        "archived_date",
        "note",
    ):
        value = getattr(member, name)
        _require(isinstance(value, str), member, f"{name} must be text, got {value!r}")
    _require(
        isinstance(member.fork_update, int)
        and not isinstance(member.fork_update, bool),
        member,
        f"fork_update must be an integer, got {member.fork_update!r}",
    )
    _require(
        isinstance(member.settings_changed, dict),
        member,
        "settings_changed must be a dict",
    )


def _check_checkpoint(member: Member) -> None:
    if member.is_script or member.checkpoint == SCRIPT_CHECKPOINT:
        _require(
            member.is_script and member.checkpoint == SCRIPT_CHECKPOINT,
            member,
            f"only {SCRIPT_ID!r} flies the script, and it flies nothing else",
        )
        _require(member.sha256 == "", member, "the script has no checkpoint hash")
        return
    path = PurePosixPath(member.checkpoint)
    _require(
        bool(member.checkpoint) and not path.is_absolute() and ".." not in path.parts,
        member,
        f"checkpoint must be a relative path, got {member.checkpoint!r}",
    )
    _require(
        bool(_SHA256.match(member.sha256)),
        member,
        f"sha256 must be 64 hex characters, got {member.sha256!r}",
    )


def _check_history(member: Member) -> None:
    entries: tuple[RatingEntry | DrillEntry, ...] = (*member.ratings, *member.drills)
    for entry in entries:
        _require(bool(entry.phase), member, "a history entry has no phase")
        _require(
            bool(_DATE.match(entry.date)), member, f"bad history date {entry.date!r}"
        )
    for rating in member.ratings:
        _require(rating.sd >= 0.0, member, f"negative rating sd in {rating.phase}")
        _require(rating.matches >= 0, member, f"negative matches in {rating.phase}")
    for drill in member.drills:
        _require(bool(drill.scores), member, f"no drill scores in {drill.phase}")


def validate_member(member: Member) -> None:
    """Check one record on its own.

    Raises:
        PopulationError: The first problem found.
    """
    _check_types(member)
    _require(bool(_ID.match(member.id)), member, "id must be lower-case and tidy")
    _require(bool(member.family), member, "family is empty")
    _require(bool(member.founder), member, "founder is empty")
    _require(member.status in STATUSES, member, f"unknown status {member.status!r}")
    if member.parent:
        _require(
            member.relation in RELATIONS,
            member,
            f"relation must be one of {RELATIONS}, got {member.relation!r}",
        )
        _require(member.fork_update >= 0, member, "a child needs a fork update >= 0")
        _require(
            member.parent != member.id, member, "a member cannot be its own parent"
        )
    else:
        _require(member.relation == NO_RELATION, member, "a root has no relation")
        _require(member.fork_update == NO_FORK, member, "a root has no fork update")
        _require(
            member.is_founder,
            member,
            "a member with no parent must found its own family",
        )
    if member.is_active:
        _require(
            not member.archived_reason and not member.archived_date,
            member,
            "an active member has no archive reason or date",
        )
    else:
        _require(bool(member.archived_reason), member, "archived without a reason")
        _require(
            bool(_DATE.match(member.archived_date)),
            member,
            f"bad archive date {member.archived_date!r}",
        )
    if member.is_script:
        _require(member.family == SCRIPT_FAMILY, member, "wrong family for the script")
        _require(member.is_founder, member, "the script founds its own family")
        _require(not member.parent, member, "the script has no parent")
    if member.family == HISTORY_FAMILY:
        _require(not member.is_active, member, "a history pilot is always archived")
        _require(
            member.founder == SCRIPT_ID,
            member,
            "a history pilot's founder is the script",
        )
    _check_checkpoint(member)
    _check_history(member)


def _check_parent_rules(member: Member, members: Mapping[str, Member]) -> None:
    parent = members.get(member.parent)
    _require(parent is not None, member, f"unknown parent {member.parent!r}")
    if member.parent == SCRIPT_ID:
        _require(
            member.relation == CLONE and not member.is_active,
            member,
            "the script cannot have children; only an archived clone may name it",
        )


def _check_founder_rules(member: Member, members: Mapping[str, Member]) -> None:
    founder = members.get(member.founder)
    _require(founder is not None, member, f"unknown founder {member.founder!r}")
    if member.family == HISTORY_FAMILY or founder is None:
        return
    _require(
        founder.family == member.family,
        member,
        f"family {member.family!r} differs from its founder's {founder.family!r}",
    )
    if not member.is_founder:
        _require(bool(member.parent), member, "only a founder may have no parent")
        parent = members[member.parent]
        _require(
            parent.founder == member.founder,
            member,
            f"founder {member.founder!r} differs from its parent's {parent.founder!r}",
        )


def _check_no_cycles(members: Mapping[str, Member]) -> None:
    for member in members.values():
        seen = {member.id}
        cursor = member
        while cursor.parent:
            if cursor.parent in seen:
                raise PopulationError(f"ancestry cycle through {cursor.parent!r}")
            seen.add(cursor.parent)
            cursor = members[cursor.parent]


def validate_tree(members: Mapping[str, Member]) -> None:
    """Check the records against each other.

    Raises:
        PopulationError: Unknown parent or founder, a family or founder mismatch, a
            forbidden child of the script, or an ancestry cycle.
    """
    for key, member in members.items():
        if key != member.id:
            raise PopulationError(f"record key {key!r} holds member {member.id!r}")
        if member.parent:
            _check_parent_rules(member, members)
        _check_founder_rules(member, members)
    _check_no_cycles(members)


@dataclass(frozen=True)
class Population:
    """All of a season's members and the tree they form.

    Attributes:
        season_dir: ``lab/population/<season>``.
        members: Member id -> record, in id order.
    """

    season_dir: Path
    members: dict[str, Member] = field(default_factory=dict)

    @property
    def season(self) -> str:
        """The season's name."""
        return self.season_dir.name

    def member(self, member_id: str) -> Member:
        """The record of ``member_id``.

        Raises:
            PopulationError: Unknown id.
        """
        if member_id not in self.members:
            raise PopulationError(
                f"unknown member {member_id!r}; known: {sorted(self.members)}"
            )
        return self.members[member_id]

    def active(self) -> list[Member]:
        """Active members, in id order."""
        return [m for m in self.members.values() if m.is_active]

    def children(self, member_id: str) -> list[Member]:
        """Direct children of ``member_id``, in id order."""
        return [m for m in self.members.values() if m.parent == member_id]

    def roots(self) -> list[Member]:
        """Members with no parent, in id order."""
        return [m for m in self.members.values() if not m.parent]

    def lineage(self, member_id: str) -> list[str]:
        """``member_id`` then its ancestors, nearest first.

        Raises:
            PopulationError: Unknown id.
        """
        chain = [self.member(member_id).id]
        while self.members[chain[-1]].parent:
            chain.append(self.members[chain[-1]].parent)
        return chain

    def tree_distance(self, a: str, b: str) -> int:
        """Edges from ``a`` to ``b`` through their nearest common ancestor.

        Returns:
            The path length, or ``UNRELATED`` if they share no ancestor.

        Raises:
            PopulationError: Unknown id.
        """
        steps_from_a = {m: k for k, m in enumerate(self.lineage(a))}
        for steps_from_b, ancestor in enumerate(self.lineage(b)):
            if ancestor in steps_from_a:
                return steps_from_a[ancestor] + steps_from_b
        return UNRELATED


def member_path(season_dir: Path, member_id: str) -> Path:
    """Where ``member_id``'s record lives."""
    return season_dir / MEMBERS_DIRNAME / f"{member_id}.json"


def load_population(season_dir: Path) -> Population:
    """Load and validate every record of a season.

    Raises:
        FileNotFoundError: No members directory, or it has no records.
        PopulationError: Any bad record, a file named differently from its member, or
            an invalid tree.
    """
    directory = season_dir / MEMBERS_DIRNAME
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"no member records in {directory}")
    members: dict[str, Member] = {}
    for path in paths:
        try:
            member = Member.from_dict(json.loads(path.read_text()))
        except json.JSONDecodeError as err:
            raise PopulationError(f"{path} is not JSON: {err}") from err
        except PopulationError as err:
            raise PopulationError(f"{path}: {err}") from err
        if member.id != path.stem:
            raise PopulationError(f"{path} holds member {member.id!r}")
        members[member.id] = member
    validate_tree(members)
    return Population(season_dir, members)


def write_member(season_dir: Path, member: Member) -> Path:
    """Write one record atomically; returns its path."""
    path = member_path(season_dir, member.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(member.to_dict(), indent=1) + "\n")
    os.replace(tmp, path)
    return path


def add_member(
    season_dir: Path, member: Member, historical_clone_of_script: bool = False
) -> Member:
    """Validate ``member`` against the season's tree and write its record.

    This is the door new members come through, so it is stricter than validation of
    records already on disk: nothing new may name the script as parent.

    Args:
        season_dir: The season.
        member: The new record.
        historical_clone_of_script: Allow an archived clone to name the script. Only for
            recording the true start of the tree; the CLI never sets it.

    Raises:
        PopulationError: The member exists, is invalid, breaks the tree, or names the
            script as parent.
    """
    if member.parent == SCRIPT_ID and not historical_clone_of_script:
        raise PopulationError(
            f"member {member.id!r}: the script pilot cannot have children"
        )
    directory = season_dir / MEMBERS_DIRNAME
    population = (
        load_population(season_dir)
        if any(directory.glob("*.json"))
        else Population(season_dir)
    )
    if member.id in population.members:
        raise PopulationError(f"member {member.id!r} already exists in {season_dir}")
    validate_member(member)
    validate_tree({**population.members, member.id: member})
    write_member(season_dir, member)
    return member


def script_member() -> Member:
    """The script pilot's record: the tree's root, which never trains."""
    return Member(
        id=SCRIPT_ID,
        family=SCRIPT_FAMILY,
        founder=SCRIPT_ID,
        parent="",
        relation=NO_RELATION,
        fork_update=NO_FORK,
        settings_changed={},
        checkpoint=SCRIPT_CHECKPOINT,
        sha256="",
        status=ACTIVE,
        note="The sim's scripted pilot. Yardstick, and it follows. Cannot have children.",
    )


def new_founder(
    member_id: str,
    family: str,
    checkpoint: str,
    sha256: str,
    parent: str = "",
    relation: str = NO_RELATION,
    fork_update: int = NO_FORK,
    settings_changed: Mapping[str, Any] | None = None,
    note: str = "",
) -> Member:
    """An active member founding ``family`` (no ``parent``: a from-scratch line)."""
    return Member(
        id=member_id,
        family=family,
        founder=member_id,
        parent=parent,
        relation=relation,
        fork_update=fork_update,
        settings_changed=dict(settings_changed or {}),
        checkpoint=checkpoint,
        sha256=sha256,
        status=ACTIVE,
        note=note,
    )


def new_child(
    parent: Member,
    member_id: str,
    checkpoint: str,
    sha256: str,
    fork_update: int,
    settings_changed: Mapping[str, Any] | None = None,
    note: str = "",
) -> Member:
    """An active member forked from ``parent``, in its family and under its founder."""
    return Member(
        id=member_id,
        family=parent.family,
        founder=parent.founder,
        parent=parent.id,
        relation=FORK,
        fork_update=fork_update,
        settings_changed=dict(settings_changed or {}),
        checkpoint=checkpoint,
        sha256=sha256,
        status=ACTIVE,
        note=note,
    )


def archive_member(season_dir: Path, member_id: str, reason: str, date: str) -> Member:
    """Archive a member with its reason. Its record and place in the tree stay.

    Raises:
        PopulationError: Unknown member, already archived, or no reason or date.
    """
    member = load_population(season_dir).member(member_id)
    if member.status == ARCHIVED:
        raise PopulationError(f"member {member_id!r} is already archived")
    archived = replace(
        member, status=ARCHIVED, archived_reason=reason, archived_date=date
    )
    validate_member(archived)
    write_member(season_dir, archived)
    return archived


def sha256_of(path: Path) -> str:
    """Content hash of a file.

    Raises:
        FileNotFoundError: No such file.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_checkpoint(member: Member, checkpoint_root: Path) -> Path:
    """The verified checkpoint file of a neural member.

    Args:
        member: The member.
        checkpoint_root: The checkout whose ``lab/runs`` holds the weights.

    Raises:
        PopulationError: The script has no file, or the file's hash differs from the
            record's.
        FileNotFoundError: The file is not under ``checkpoint_root``.
    """
    if member.is_script:
        raise PopulationError("the script has no checkpoint file")
    path = checkpoint_root / member.checkpoint
    if not path.is_file():
        raise FileNotFoundError(f"checkpoint of {member.id!r} not found: {path}")
    actual = sha256_of(path)
    if actual != member.sha256:
        raise PopulationError(
            f"checkpoint of {member.id!r} changed: {path} is {actual}, "
            f"the record says {member.sha256}"
        )
    return path


def record_ratings(
    season_dir: Path, entries: Mapping[str, RatingEntry]
) -> list[Member]:
    """Append one phase's ratings to the members' records.

    History only: this never changes a member's status.

    Returns:
        The updated members.

    Raises:
        PopulationError: Unknown member, or the member already has a rating for that
            phase.
    """
    population = load_population(season_dir)
    updated = []
    for member_id, entry in entries.items():
        member = population.member(member_id)
        if any(r.phase == entry.phase for r in member.ratings):
            raise PopulationError(f"{member_id!r} already rated in {entry.phase!r}")
        updated.append(replace(member, ratings=(*member.ratings, entry)))
    for member in updated:
        write_member(season_dir, member)
    return updated


def record_drills(season_dir: Path, entries: Mapping[str, DrillEntry]) -> list[Member]:
    """Append one phase's drill results to the members' records.

    History only: this never changes a member's status.

    Returns:
        The updated members.

    Raises:
        PopulationError: Unknown member, or it already has drills for that phase.
    """
    population = load_population(season_dir)
    updated = []
    for member_id, entry in entries.items():
        member = population.member(member_id)
        if any(d.phase == entry.phase for d in member.drills):
            raise PopulationError(f"{member_id!r} already drilled in {entry.phase!r}")
        updated.append(replace(member, drills=(*member.drills, entry)))
    for member in updated:
        write_member(season_dir, member)
    return updated
