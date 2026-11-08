"""Play the WAR matches: live-page matches with the script in the pilot draw.

Matches are the commander eval's (``spacefight.commander.eval.play_matches``): live
rosters, orders shown, capital ships by the sim's scripts. Each strike craft's pilot is
drawn uniformly from the candidates plus the script, which is the only difference from
the live page, and it is what anchors replacement level. Each side's commander is drawn
uniformly per match from the commanders given (by default the live stable,
``lab/live_commanders.json``).

Each mission plays ``n_per_mission`` matches, match ``g`` on roster ``g % R`` (deathmatch:
``deathmatch_drafts`` of the live page's drafts, the same for the whole run). They are
played in chunks of ``chunk`` matches, each written to ``matches/<mission>-<k>.json`` when
it ends, so a long run resumes from the last finished chunk. ``config.json`` fixes the
pool, commanders, sizes and seed; a different config raises rather than mixing results.
When every chunk is in, ``war.json`` (``rlf.population.war/1``) and ``war.md`` are written.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import numpy as np
import rlf_sim

from spacefight.commander.eval import (
    ASSETS,
    Commander,
    MatchesPlayed,
    named_mission_rosters,
    play_matches,
)
from spacefight.commander.train import LEARNED, MISSIONS
from spacefight.env.rosters import RANDOM, SCRIPTED, hull_names_by_id
from spacefight.population.records import (
    SCRIPT_ID,
    Population,
    resolve_checkpoint,
    sha256_of,
)
from spacefight.population.war import (
    DEFAULT_BOOTSTRAP,
    DEFAULT_NUISANCE_PRIOR_SD,
    DEFAULT_PRIOR_SD,
    MatchRecord,
    WarDocument,
    fit_war,
    write_war,
)

CONFIG_SCHEMA: Final = "rlf.population.war_config/1"
CHUNK_SCHEMA: Final = "rlf.population.war_chunk/1"
CONFIG_FILENAME: Final = "config.json"
MATCHES_DIRNAME: Final = "matches"
WAR_FILENAME: Final = "war.json"
LIVE: Final = "live"
DEFAULT_LIVE_COMMANDERS: Final = Path("lab/live_commanders.json")
_MISSION_STRIDE: Final = 100_003
_CHUNK_STRIDE: Final = 7_919
_COMMANDER_DRAW: Final = 3


@dataclass(frozen=True)
class WarConfig:
    """Everything that changes a WAR run's matches.

    Attributes:
        pilots: ``(id, sha256)`` of the candidates; the script joins them in the draw.
        commanders: ``(label, mode, sha256)`` of the commanders each side draws from;
            sha256 is empty for the scripted and random commanders.
        n_per_mission: Matches per mission; a multiple of every mission's roster count.
        chunk: Matches per chunk file.
        deathmatch_drafts: Live-page drafts deathmatch cycles through.
        seed: Base seed.
        missions: Missions played.
        sim_version: The sim's version.
    """

    pilots: tuple[tuple[str, str], ...]
    commanders: tuple[tuple[str, str, str], ...]
    n_per_mission: int
    chunk: int
    deathmatch_drafts: int
    seed: int
    missions: tuple[str, ...] = MISSIONS
    sim_version: int = int(rlf_sim.SIM_VERSION)

    def __post_init__(self) -> None:
        ids = [p for p, _ in self.pilots]
        if not ids or SCRIPT_ID in ids or len(set(ids)) != len(ids):
            raise ValueError(f"need distinct candidates other than the script: {ids}")
        labels = [c for c, _, _ in self.commanders]
        if not labels or len(set(labels)) != len(labels):
            raise ValueError(f"need distinct commander labels: {labels}")
        if self.n_per_mission <= 0 or self.chunk <= 0 or self.deathmatch_drafts <= 0:
            raise ValueError("sizes must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict, schema first."""
        raw = asdict(self)
        return {
            "schema": CONFIG_SCHEMA,
            **raw,
            "pilots": [list(p) for p in self.pilots],
            "commanders": [list(c) for c in self.commanders],
            "missions": list(self.missions),
        }

    def mission_seed(self, mission: str) -> int:
        """The seed a mission's rosters and chunks start from."""
        return self.seed + _MISSION_STRIDE * self.missions.index(mission)

    def chunks(self) -> int:
        """Chunks per mission."""
        return -(-self.n_per_mission // self.chunk)


def resolve_commanders(
    specs: Sequence[str], live_registry: Path = DEFAULT_LIVE_COMMANDERS
) -> list[tuple[Commander, str]]:
    """Commanders and their sha256 from specs: ``live`` (the live stable), ``scripted``,
    ``random`` or a commander checkpoint.

    Raises:
        ValueError: No commanders, or two with the same label.
        FileNotFoundError: A checkpoint is missing.
    """
    # Loaded here: only a run with the live stable needs the registry's tools.
    from spacefight.commander.policy import load_commander
    from tools.live_commanders import fetch_checkpoint, load_registry

    out: list[tuple[Commander, str]] = []
    for spec in specs:
        if spec == LIVE:
            stable, _ = load_registry(live_registry)
            for c in stable:
                if c.kind == LEARNED:
                    actor, _ = load_commander(fetch_checkpoint(c))
                    out.append((Commander(c.id, LEARNED, actor), c.sha256))
                else:
                    out.append((Commander(c.id, SCRIPTED), ""))
        elif spec in (SCRIPTED, RANDOM):
            out.append((Commander(spec, spec), ""))
        else:
            out.append((Commander.from_spec(spec), sha256_of(Path(spec))))
    labels = [c.label for c, _ in out]
    if not labels or len(set(labels)) != len(labels):
        raise ValueError(f"need distinct commanders, got {labels}")
    return out


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n")
    os.replace(tmp, path)


def _check_config(out_dir: Path, cfg: WarConfig) -> None:
    """Write the directory's config, or refuse one that differs from it."""
    path = out_dir / CONFIG_FILENAME
    wanted = cfg.to_dict()
    if not path.exists():
        _write_json(path, wanted)
        return
    found = json.loads(path.read_text())
    if found != wanted:
        raise ValueError(
            f"{path} has a different config; use a new directory.\n"
            f"found: {found}\nwanted: {wanted}"
        )


def chunk_path(out_dir: Path, mission: str, k: int) -> Path:
    """Where chunk ``k`` of ``mission`` lives."""
    return out_dir / MATCHES_DIRNAME / f"{mission}-{k:03d}.json"


def records_from_play(
    played: MatchesPlayed,
    pilot_ids: Sequence[str],
    mission: str,
    roster_names: Sequence[str],
    commander_labels: Sequence[tuple[str, str]],
    hull_names: Sequence[str],
) -> list[MatchRecord]:
    """One ``MatchRecord`` per match played, counting strike craft by pilot and hull."""
    names = [*pilot_ids]
    records = []
    for i in range(played.winner.shape[0]):
        ships: tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]] = ({}, {})
        for s in np.flatnonzero(played.strike[i]):
            k = int(played.assign[i, s])
            pilot = SCRIPT_ID if k == played.script else names[k]
            hull = hull_names[int(played.hull_id[i, s])]
            by_hull = ships[int(played.team[i, s])].setdefault(pilot, {})
            by_hull[hull] = by_hull.get(hull, 0) + 1
        records.append(
            MatchRecord(
                mission=mission,
                roster=roster_names[i],
                commanders=commander_labels[i],
                ships=ships,
                winner=int(played.winner[i]),
                end_reason=int(played.end_reason[i]),
            )
        )
    return records


def play_chunk(
    cfg: WarConfig,
    mission: str,
    k: int,
    pilots: Sequence[tuple[str, Path]],
    commanders: Sequence[Commander],
    n_threads: int,
) -> list[MatchRecord]:
    """Play chunk ``k`` of ``mission`` (module docstring).

    Raises:
        ValueError: ``n_per_mission`` is not a multiple of the mission's rosters.
        RuntimeError: A match did not end within its clock.
    """
    base = cfg.mission_seed(mission)
    named = named_mission_rosters(mission, cfg.deathmatch_drafts, base)
    if cfg.n_per_mission % len(named):
        raise ValueError(
            f"n_per_mission must be a multiple of {len(named)} for {mission}, "
            f"got {cfg.n_per_mission}"
        )
    games = np.arange(k * cfg.chunk, min(cfg.n_per_mission, (k + 1) * cfg.chunk))
    entries = games % len(named)
    seed = base + _CHUNK_STRIDE * (k + 1)
    rng = np.random.default_rng(seed + _COMMANDER_DRAW)
    side_commander = rng.integers(0, len(commanders), size=(games.size, 2))
    played = play_matches(
        [named[e][1] for e in entries],
        mission,
        commanders,
        side_commander,
        seed,
        n_threads,
        pilots,
        include_script=True,
    )
    labels = [
        (commanders[a].label, commanders[b].label) for a, b in side_commander.tolist()
    ]
    return records_from_play(
        played,
        [p for p, _ in pilots],
        mission,
        [named[e][0] for e in entries],
        labels,
        hull_names_by_id(ASSETS),
    )


def _read_chunk(path: Path, mission: str, k: int, size: int) -> list[MatchRecord]:
    """A finished chunk, checked against what it should hold.

    Raises:
        ValueError: Wrong schema, mission, chunk or match count.
    """
    data = json.loads(path.read_text())
    if data.get("schema") != CHUNK_SCHEMA or (data["mission"], data["chunk"]) != (
        mission,
        k,
    ):
        raise ValueError(f"{path} is not chunk {k} of {mission}")
    records = [MatchRecord.from_dict(r) for r in data["records"]]
    if len(records) != size:
        raise ValueError(f"{path} holds {len(records)} matches, not {size}")
    return records


def play_all(
    cfg: WarConfig,
    out_dir: Path,
    pilots: Sequence[tuple[str, Path]],
    commanders: Sequence[Commander],
    n_threads: int,
) -> list[MatchRecord]:
    """Play every unfinished chunk, writing each as it ends; every match in order.

    Raises:
        ValueError: A config differing from the directory's, or a bad chunk file.
        RuntimeError: A match did not end within its clock.
    """
    _check_config(out_dir, cfg)
    records: list[MatchRecord] = []
    for mission in cfg.missions:
        for k in range(cfg.chunks()):
            size = min(cfg.chunk, cfg.n_per_mission - k * cfg.chunk)
            path = chunk_path(out_dir, mission, k)
            if path.exists():
                records += _read_chunk(path, mission, k, size)
                print(f"{mission} chunk {k}: done", flush=True)
                continue
            start = time.perf_counter()
            chunk = play_chunk(cfg, mission, k, pilots, commanders, n_threads)
            secs = time.perf_counter() - start
            _write_json(
                path,
                {
                    "schema": CHUNK_SCHEMA,
                    "mission": mission,
                    "chunk": k,
                    "secs": secs,
                    "records": [r.to_dict() for r in chunk],
                },
            )
            records += chunk
            print(
                f"{mission} chunk {k + 1}/{cfg.chunks()}: {len(chunk)} matches in "
                f"{secs:.0f}s ({len(chunk) / secs:.2f}/s)",
                flush=True,
            )
    return records


def run_war(
    population: Population,
    member_ids: Sequence[str],
    commanders: Sequence[tuple[Commander, str]],
    out_dir: Path,
    n_per_mission: int,
    seed: int,
    n_threads: int,
    checkpoint_root: Path = Path("."),
    chunk: int = 96,
    deathmatch_drafts: int = 24,
    prior_sd: float = DEFAULT_PRIOR_SD,
    nuisance_prior_sd: float = DEFAULT_NUISANCE_PRIOR_SD,
    n_bootstrap: int = DEFAULT_BOOTSTRAP,
    missions: Sequence[str] = MISSIONS,
) -> WarDocument:
    """Play (or resume) a WAR measurement of ``member_ids`` and fit it.

    Args:
        population: The records; each candidate's checkpoint is verified against it.
        member_ids: Candidates; the script is always in the draw and is dropped here.
        commanders: ``(commander, sha256)`` each side draws from (``resolve_commanders``).
        out_dir: Results directory; a run resumes from what it finds here.
        n_per_mission: Matches per mission.
        seed: Base seed; also the bootstrap's.
        n_threads: Sim threads.
        checkpoint_root: The checkout holding the weights.
        chunk: Matches per chunk file.
        deathmatch_drafts: Live-page drafts deathmatch cycles through.
        prior_sd: Ridge prior per pilot, logits per ship.
        nuisance_prior_sd: Prior on side and commander terms, logits.
        n_bootstrap: Bootstrap refits.
        missions: Missions played.

    Returns:
        The written document (``out_dir/war.json``, table beside it).

    Raises:
        PopulationError: Unknown member or a checkpoint that differs from its record.
        FileNotFoundError: A checkpoint is missing.
        ValueError: No candidates, a size that does not cycle a mission's rosters
            evenly, or a config differing from the directory's.
    """
    ids = sorted({m for m in member_ids if m != SCRIPT_ID})
    members = [population.member(m) for m in ids]
    # Fail before any match rather than an hour in.
    pilots = [(m.id, resolve_checkpoint(m, checkpoint_root)) for m in members]
    cfg = WarConfig(
        pilots=tuple((m.id, m.sha256) for m in members),
        commanders=tuple((c.label, c.mode, sha) for c, sha in commanders),
        n_per_mission=n_per_mission,
        chunk=chunk,
        deathmatch_drafts=deathmatch_drafts,
        seed=seed,
        missions=tuple(missions),
    )
    for mission in cfg.missions:
        rosters = named_mission_rosters(mission, deathmatch_drafts, 0)
        if n_per_mission % len(rosters):
            raise ValueError(
                f"n_per_mission must be a multiple of {len(rosters)} for {mission}"
            )
    records = play_all(cfg, out_dir, pilots, [c for c, _ in commanders], n_threads)
    fit = fit_war(records, prior_sd, nuisance_prior_sd, n_bootstrap, seed)
    document = WarDocument(cfg.to_dict(), tuple(records), fit)
    write_war(out_dir / WAR_FILENAME, document, population.season)
    return document
