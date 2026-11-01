"""Round robin: all pairs of members in no-commander matches.

Every pair plays deathmatch, carrier battle and convoy escort with no commander on
either side (``docs/PILOT_TRAINING.md`` section 5): ``hide_orders`` on both teams, the
script doing logistics, capital ships flown by the sim's scripts. Env ``i`` of a mission
plays roster ``i % R`` with ``a`` on team ``(i // R) % 2``, so with ``n_per_mission`` a
multiple of ``2 R`` each pilot flies every roster from each side equally often, which in
a convoy means both defending and raiding.

Rosters: carrier and convoy use the sim's live rosters (``rlf_sim.mission_rosters``).
Deathmatch has none there, so it draws ``deathmatch_rosters`` rosters from a fleet preset,
the same draw for every pair. A pair therefore differs only in who flies.

Resumable: each pair is written atomically to ``pairs/<a>__<b>.json`` as it finishes,
and finished pairs are skipped. A directory's ``config.json`` fixes the sizes and seed; a
different config raises instead of mixing results. New members can join an existing
directory, and only their new pairs are played. A pair whose checkpoint hash differs from
the record raises, since those results are of other weights.

**The script is not blind in these matches.** ``hide_orders`` only changes what a pilot
*observes* (``crates/sim/src/obs.rs``). The script reads its squad's order from the match
state (``scripted::orders::active_order``), so in carrier and convoy it still flies the
scripted commander's orders while neural pilots see none. Deathmatch orders are advisory,
so the script ignores them there. The script's mission results therefore carry an
advantage the neural pilots lack. This has to be weighed when reading its numbers.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Final

import numpy as np
import rlf_sim

from spacefight.env.rosters import (
    CARRIER_BATTLE,
    CONVOY_ESCORT,
    DEATHMATCH,
    SCRIPTED,
    Roster,
    capital_hull_ids,
    make_sampler,
    resolve_distribution,
)
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval.controllers import Controller, make_controller
from spacefight.eval.fleet import ShipMetrics
from spacefight.eval.missions import (
    ASSETS,
    MissionEnv,
    MissionSummary,
    default_rosters,
    play_mission_env,
)
from spacefight.population.culling import BehaviourFeatures
from spacefight.population.rating import rate
from spacefight.population.records import (
    Member,
    Population,
    PopulationError,
    resolve_checkpoint,
)
from spacefight.population.standings import (
    RoundRobinResults,
    make_matrix,
    overall_matrix,
    transitivity,
)

PAIR_SCHEMA: Final = "rlf.population.pair/1"
CONFIG_SCHEMA: Final = "rlf.population.round_robin/1"
PAIRS_DIRNAME: Final = "pairs"
CONFIG_FILENAME: Final = "config.json"
SUMMARY_FILENAME: Final = "summary.json"
ROUND_ROBIN_MISSIONS: Final = (DEATHMATCH, CARRIER_BATTLE, CONVOY_ESCORT)
_SEED_STRIDE: Final = 100_003
# Hidden on both teams in every match of the round robin.
HIDE_BOTH: Final = (True, True)


@dataclass(frozen=True)
class RoundRobinConfig:
    """Everything that changes a round robin's numbers. The defaults are tiny, for tests.

    Attributes:
        missions: Missions every pair plays.
        n_per_mission: Matches per pair per mission. Must be a multiple of ``2 R`` for
            every mission's roster count ``R``.
        deathmatch_rosters: Rosters drawn for deathmatch.
        deathmatch_preset: The fleet preset they are drawn from.
        seed: Base seed; every pair uses the same matches.
        reaction_ticks: Sim reaction ticks.
        sample: Sample from policies' heads (the eval's primary numbers), else argmax.
        sim_version: The sim's version when the config was made.
    """

    missions: tuple[str, ...] = ROUND_ROBIN_MISSIONS
    n_per_mission: int = 12
    deathmatch_rosters: int = 6
    deathmatch_preset: str = "fleet_v1"
    seed: int = 400_000
    reaction_ticks: int = 2
    sample: bool = True
    sim_version: int = int(rlf_sim.SIM_VERSION)

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return {
            "schema": CONFIG_SCHEMA,
            **asdict(self),
            "missions": list(self.missions),
        }


def rosters_for(mission: str, cfg: RoundRobinConfig) -> list[tuple[str, Roster]]:
    """``(unique name, roster)`` of ``mission`` under ``cfg`` (module docstring).

    Raises:
        ValueError: ``deathmatch_rosters`` not positive.
    """
    if mission != DEATHMATCH:
        return default_rosters(mission)
    if cfg.deathmatch_rosters <= 0:
        raise ValueError(
            f"deathmatch_rosters must be positive, got {cfg.deathmatch_rosters}"
        )
    sampler = make_sampler(resolve_distribution(cfg.deathmatch_preset), cfg.seed)
    drawn = [sampler.sample() for _ in range(cfg.deathmatch_rosters)]
    return [(f"{k}: {roster.label}", roster) for k, roster in enumerate(drawn)]


def build_no_commander_env(
    mission: str,
    cfg: RoundRobinConfig,
    n_threads: int,
    assets_dir: Path = ASSETS,
) -> MissionEnv:
    """One mission's env with orders hidden from both teams and scripted logistics.

    Raises:
        ValueError: ``n_per_mission`` is not a positive multiple of twice the roster
            count.
    """
    rosters = rosters_for(mission, cfg)
    block = 2 * len(rosters)
    n = cfg.n_per_mission
    if n < block or n % block:
        raise ValueError(
            f"n_per_mission must be a positive multiple of {block} for {mission}, "
            f"got {n}"
        )
    index = np.arange(n, dtype=np.int64)
    entry = index % len(rosters)
    a_team = (index // len(rosters)) % 2
    time_limit_s = float(rlf_sim.mission_time_limit_s(mission))
    modes = (SCRIPTED, SCRIPTED)
    seed = cfg.seed + _SEED_STRIDE * cfg.missions.index(mission)
    env = RustVecEnv(
        assets_dir,
        n,
        rosters[0][1].fleets(),
        seed,
        time_limit_s=time_limit_s,
        n_threads=n_threads,
        record_events=True,
        reaction_ticks=cfg.reaction_ticks,
        max_ships=max(roster.n_ships for _, roster in rosters),
        commanders=modes,
        hide_orders=HIDE_BOTH,
    )
    for i, k in enumerate(entry):
        roster = rosters[int(k)][1]
        env.set_next_roster(
            i, Roster(roster.teams, mission, modes), hide_orders=HIDE_BOTH
        )
    env.reset()
    return MissionEnv(
        env=env,
        names=[name for name, _ in rosters],
        entry=entry,
        a_team=a_team,
        capital=np.isin(env.hull_id, capital_hull_ids(assets_dir)),
        time_limit_s=time_limit_s,
    )


def _mission_result(summary: MissionSummary, secs: float) -> dict[str, Any]:
    return {
        "n": summary.n,
        "score_rate": summary.win_rate,
        "score_rate_team0": summary.win_rate_team0,
        "score_rate_team1": summary.win_rate_team1,
        "draw_rate": summary.draw_rate,
        "time_limit_rate": summary.time_limit_rate,
        "stalemate_rate": summary.stalemate_rate,
        "length_median_s": summary.length_median_s,
        "nan_matches": summary.side_a.nan_matches + summary.side_b.nan_matches,
        "stuck_matches": summary.side_a.stuck_matches + summary.side_b.stuck_matches,
        "ships_a": asdict(summary.side_a.all_ships),
        "ships_b": asdict(summary.side_b.all_ships),
        "secs": secs,
    }


def play_pair_in_sim(
    a: Controller,
    b: Controller,
    cfg: RoundRobinConfig,
    n_threads: int,
    assets_dir: Path = ASSETS,
) -> dict[str, dict[str, Any]]:
    """Play every mission of ``cfg`` with ``a`` against ``b``.

    Returns:
        Mission -> results from ``a``'s side.

    Raises:
        RuntimeError: A match did not end within its clock.
    """
    results = {}
    for k, mission in enumerate(cfg.missions):
        start = time.perf_counter()
        env_seed = cfg.seed + _SEED_STRIDE * k
        a.reset(env_seed)
        b.reset(env_seed + 1)
        me = build_no_commander_env(mission, cfg, n_threads, assets_dir)
        summary = play_mission_env(a, b, mission, me)
        results[mission] = _mission_result(summary, time.perf_counter() - start)
    return results


PairPlayer = Callable[
    [Controller, Controller, RoundRobinConfig, int, Path], dict[str, dict[str, Any]]
]


def pair_path(out_dir: Path, a: str, b: str) -> Path:
    """Where the pair's results live; ``a`` sorts before ``b``."""
    return out_dir / PAIRS_DIRNAME / f"{a}__{b}.json"


def _check_config(out_dir: Path, cfg: RoundRobinConfig) -> None:
    """Write the directory's config, or refuse one that differs from it."""
    path = out_dir / CONFIG_FILENAME
    wanted = cfg.to_dict()
    if not path.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(wanted, indent=1) + "\n")
        return
    found = json.loads(path.read_text())
    if found != wanted:
        raise ValueError(
            f"{path} has a different config; use a new directory.\n"
            f"found: {found}\nwanted: {wanted}"
        )


def _read_finished_pair(
    path: Path, a: Member, b: Member, cfg: RoundRobinConfig
) -> dict[str, Any]:
    """Read a finished pair, checking it is what the records and config say.

    Raises:
        PopulationError: It holds other members or other weights.
        ValueError: It is not a pair file, or lacks a mission.
    """
    data: dict[str, Any] = json.loads(path.read_text())
    if data.get("schema") != PAIR_SCHEMA:
        raise ValueError(f"{path}: expected schema {PAIR_SCHEMA!r}")
    if (data["a"], data["b"]) != (a.id, b.id):
        raise PopulationError(f"{path} holds {data['a']} v {data['b']}")
    if (data["a_sha256"], data["b_sha256"]) != (a.sha256, b.sha256):
        raise PopulationError(
            f"{path} was played with other weights than the records name"
        )
    missing = set(cfg.missions) - set(data["missions"])
    if missing:
        raise ValueError(f"{path} lacks missions {sorted(missing)}")
    return data


def _write_pair(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n")
    os.replace(tmp, path)


@dataclass
class _Pilots:
    """Builds each member's controller once, verifying its checkpoint first."""

    checkpoint_root: Path
    sample: bool
    built: dict[str, Controller] = field(default_factory=dict)

    def controller(self, member: Member) -> Controller:
        if member.id not in self.built:
            spec = (
                member.checkpoint
                if member.is_script
                else str(resolve_checkpoint(member, self.checkpoint_root))
            )
            self.built[member.id] = make_controller(spec, sample=self.sample)
        return self.built[member.id]


def run_round_robin(
    population: Population,
    member_ids: Sequence[str],
    out_dir: Path,
    cfg: RoundRobinConfig,
    checkpoint_root: Path,
    n_threads: int = 2,
    assets_dir: Path = ASSETS,
    play: PairPlayer = play_pair_in_sim,
) -> list[str]:
    """Play every unfinished pair of ``member_ids``, writing results as it goes.

    Args:
        population: The records.
        member_ids: At least two distinct members.
        out_dir: Results directory; a run resumes from what it finds here.
        cfg: Sizes and seed.
        checkpoint_root: The checkout holding the weights.
        n_threads: Sim threads.
        assets_dir: Sim assets.
        play: Plays one pair (tests pass a stand-in).

    Returns:
        The file names of the pairs played by this call.

    Raises:
        ValueError: Too few or repeated members, or a config differing from the
            directory's.
        PopulationError: Unknown member, or a checkpoint or finished pair that
            disagrees with the records.
        FileNotFoundError: A checkpoint is missing.
    """
    ids = sorted(member_ids)
    if len(ids) < 2 or len(set(ids)) != len(ids):
        raise ValueError(f"need at least two distinct members, got {list(member_ids)}")
    members = [population.member(m) for m in ids]
    # Fail before any match rather than an hour in.
    for member in members:
        if not member.is_script:
            resolve_checkpoint(member, checkpoint_root)
    _check_config(out_dir, cfg)
    pilots = _Pilots(checkpoint_root, cfg.sample)
    all_pairs = list(combinations(members, 2))
    played = []
    for k, (a, b) in enumerate(all_pairs, start=1):
        path = pair_path(out_dir, a.id, b.id)
        if path.exists():
            _read_finished_pair(path, a, b, cfg)
            print(f"[{k}/{len(all_pairs)}] {a.id} v {b.id}: done", flush=True)
            continue
        start = time.perf_counter()
        results = play(
            pilots.controller(a), pilots.controller(b), cfg, n_threads, assets_dir
        )
        secs = time.perf_counter() - start
        _write_pair(
            path,
            {
                "schema": PAIR_SCHEMA,
                "a": a.id,
                "b": b.id,
                "a_sha256": a.sha256,
                "b_sha256": b.sha256,
                "missions": results,
                "secs": secs,
            },
        )
        played.append(path.name)
        scores = " ".join(
            f"{mission}={result['score_rate']:.2f}"
            for mission, result in results.items()
        )
        print(
            f"[{k}/{len(all_pairs)}] {a.id} v {b.id}: {scores} ({secs:.0f}s)",
            flush=True,
        )
    return played


def _behaviour(
    pairs: Sequence[Mapping[str, Any]],
) -> dict[str, BehaviourFeatures]:
    """Features per member: ship-weighted means of its side's metrics."""
    totals: dict[str, np.ndarray] = {}
    ships: dict[str, float] = {}
    for pair in pairs:
        for result in pair["missions"].values():
            for name, key in ((pair["a"], "ships_a"), (pair["b"], "ships_b")):
                metrics = ShipMetrics(**result[key])
                row = np.array(
                    [metrics.fire_rate, metrics.engagement_rate, metrics.engine_duty]
                )
                totals[name] = totals.get(name, np.zeros(3)) + row * metrics.ships
                ships[name] = ships.get(name, 0.0) + metrics.ships
    features = {}
    for name, total in totals.items():
        if ships[name] <= 0.0:
            raise ValueError(f"{name} has results but flew no ships")
        fire, engagement, engine = total / ships[name]
        features[name] = BehaviourFeatures(
            float(fire), float(engagement), float(engine)
        )
    return features


def load_results(out_dir: Path, population: Population) -> RoundRobinResults:
    """Add up every finished pair in ``out_dir``, checked against the records.

    Raises:
        FileNotFoundError: No config or no finished pairs.
        PopulationError: A pair names an unknown member or other weights than the
            records.
        ValueError: A pair file of the wrong schema or lacking a mission.
    """
    cfg = config_from_file(out_dir)
    paths = sorted((out_dir / PAIRS_DIRNAME).glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"no finished pairs in {out_dir / PAIRS_DIRNAME}")
    pairs = []
    for path in paths:
        first, _, second = path.stem.partition("__")
        pairs.append(
            _read_finished_pair(
                path, population.member(first), population.member(second), cfg
            )
        )
    members = tuple(sorted({p[side] for p in pairs for side in ("a", "b")}))
    by_mission = {
        mission: make_matrix(
            {
                (p["a"], p["b"]): (
                    float(p["missions"][mission]["score_rate"]),
                    int(p["missions"][mission]["n"]),
                )
                for p in pairs
            },
            members,
        )
        for mission in cfg.missions
    }
    overall = overall_matrix(by_mission, members)
    return RoundRobinResults(
        members=members,
        by_mission=by_mission,
        overall=overall,
        transitivity_by_mission={m: transitivity(x) for m, x in by_mission.items()},
        transitivity_overall=transitivity(overall),
        ratings=tuple(rate(overall.pair_scores(), members)),
        behaviour=_behaviour(pairs),
        pairs=len(pairs),
        matches=sum(int(r["n"]) for p in pairs for r in p["missions"].values()),
        secs=sum(float(p["secs"]) for p in pairs),
    )


def config_from_file(out_dir: Path) -> RoundRobinConfig:
    """The config a results directory was started with.

    Raises:
        FileNotFoundError: No config in ``out_dir``.
        ValueError: Wrong schema.
    """
    path = out_dir / CONFIG_FILENAME
    raw = json.loads(path.read_text())
    if raw.pop("schema", "") != CONFIG_SCHEMA:
        raise ValueError(f"{path}: expected schema {CONFIG_SCHEMA!r}")
    raw["missions"] = tuple(raw["missions"])
    return RoundRobinConfig(**raw)


def write_summary(out_dir: Path, results: RoundRobinResults) -> Path:
    """Write the win matrices, transitivity, ratings and features to ``summary.json``."""
    path = out_dir / SUMMARY_FILENAME
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(results.to_dict(), indent=1) + "\n")
    os.replace(tmp, path)
    return path
