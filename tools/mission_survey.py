"""Mission survey (M3 stage A, WP-S2): do the carrier battle and the convoy escort
play out as missions, and are they balanced?

Plays every default roster of each mission (``rlf_sim.mission_rosters``, the ones
the live page drafts) ``n`` times with the scripted commanders, in one of two modes:

- ``script``: the scripted pilots fly every ship (script vs script; the teacher
  stage B will learn order-following from);
- ``live``: what visitors see. A learned pilot (the current champion, fleet pilot v1,
  by default) flies every strike craft on both sides, sampling its heads as the live
  page does; the Rust scripts fly the carriers and freighters.

Per mission and roster it reports win rates per side, the end-reason distribution,
the time-limit rate, match length (median / p90), launches over time, and for convoys
transports escaped / destroyed, route progress and how often a defender win had a
transport escape. JSON schema ``rlf.survey.mission/1``.

    uv run python tools/mission_survey.py --mode script --n 128 \\
        --out lab/runs/2026-10-30-mission-survey/survey/script.json
    uv run python tools/mission_survey.py --mode live --n 64 \\
        --out lab/runs/2026-10-30-mission-survey/survey/live.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import yaml  # type: ignore[import-untyped]
from numpy.typing import NDArray

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "assets"
SCHEMA = "rlf.survey.mission/1"
TICK_HZ = 30.0
MISSIONS: tuple[str, ...] = ("carrier_battle", "convoy_escort")
MODES: tuple[str, ...] = ("script", "live")
CAPITAL_ROLES: frozenset[str] = frozenset({"carrier", "transport"})
# Launches are binned over the match in this many seconds per bin.
LAUNCH_BIN_S = 30.0
# Convoy progress is sampled every this many ticks (the last sample is the end).
PROGRESS_EVERY = 30
END_REASONS: tuple[str, ...] = tuple(rlf_sim.END_REASONS)
KIND_DEATH = int(rlf_sim.EVENT_KINDS["death"])
KIND_LAUNCH = int(rlf_sim.EVENT_KINDS["launch"])
KIND_JUMP_OUT = int(rlf_sim.EVENT_KINDS["jump_out"])


@dataclass(frozen=True)
class RosterSpec:
    """One roster of a mission: hull names per team, slot order."""

    name: str
    mission: str
    fleets: tuple[tuple[str, ...], tuple[str, ...]]

    @property
    def n_ships(self) -> int:
        return len(self.fleets[0]) + len(self.fleets[1])


def default_rosters(mission: str) -> list[RosterSpec]:
    """The sim's default rosters of ``mission`` (``rlf_sim.mission_rosters``)."""
    return [
        RosterSpec(
            name=r["name"],
            mission=r["mission"],
            fleets=(tuple(r["fleets"][0]), tuple(r["fleets"][1])),
        )
        for r in rlf_sim.mission_rosters(mission)
    ]


def load_roles(assets_dir: Path = ASSETS) -> dict[str, str]:
    """Hull name -> role from every ``hulls/*/hull.yaml``.

    Raises:
        FileNotFoundError: No hull YAML under ``assets_dir``.
        ValueError: A hull YAML without a role.
    """
    paths = sorted((assets_dir / "hulls").glob("*/hull.yaml"))
    if not paths:
        raise FileNotFoundError(f"no hulls/*/hull.yaml under {assets_dir}")
    roles: dict[str, str] = {}
    for path in paths:
        raw = yaml.safe_load(path.read_text())
        role = raw.get("role") if isinstance(raw, dict) else None
        if not isinstance(role, str):
            raise ValueError(f"{path} has no role")
        roles[raw["name"]] = role
    return roles


@dataclass
class MatchRecord:
    """One match, measured from tick 0 to its end."""

    roster: str
    length: int  # ticks
    winner: int  # 0, 1, or -1 for a draw
    end_reason: str
    launch_ticks: list[int] = field(default_factory=list)
    transports: int = 0
    escaped: int = 0
    destroyed: int = 0
    progress: float = 0.0  # convoy route progress at the end (0..1)
    carrier_travel: tuple[float, float] = (0.0, 0.0)  # per team, metres sampled


def quantile(values: Sequence[float], q: float) -> float:
    """``q``-quantile (linear) of ``values``; 0.0 when empty."""
    if not values:
        return 0.0
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


def launch_histogram(
    launch_ticks: Sequence[Sequence[int]], horizon_s: float, bin_s: float = LAUNCH_BIN_S
) -> list[float]:
    """Mean launches per match in each ``bin_s`` bin of the first ``horizon_s``.

    ``launch_ticks`` holds one list of launch ticks per match.
    """
    n_bins = max(1, int(np.ceil(horizon_s / bin_s)))
    counts = np.zeros(n_bins, dtype=np.float64)
    for ticks in launch_ticks:
        for t in ticks:
            counts[min(n_bins - 1, int(t / TICK_HZ / bin_s))] += 1
    return (counts / max(1, len(launch_ticks))).round(3).tolist()


@dataclass(frozen=True)
class RosterSummary:
    """One roster's matches."""

    name: str
    n: int
    team0_win: float  # wins of team 0 (defenders in a convoy), draws count 1/2
    team1_win: float
    draw_rate: float
    time_limit_rate: float
    end_reasons: dict[str, float]
    length_median_s: float
    length_p90_s: float
    launches_per_match: float
    launch_median_s: float  # median launch time (0 without launches)
    launch_p90_s: float
    launches_by_bin: list[float]
    escaped_mean: float
    destroyed_mean: float
    progress_mean: float
    defender_wins_with_escape: float  # convoy: share of team-0 wins with an escape
    carrier_travel_m: float  # mean metres a carrier moved (both teams)


def summarise(name: str, records: Sequence[MatchRecord], horizon_s: float) -> RosterSummary:
    """Aggregate one roster's ``records``.

    Raises:
        ValueError: ``records`` is empty.
    """
    if not records:
        raise ValueError(f"roster {name!r}: no matches")
    n = len(records)
    winners = np.array([r.winner for r in records])
    draws = float(np.mean(winners == -1))
    reasons = {
        reason: round(sum(r.end_reason == reason for r in records) / n, 4)
        for reason in END_REASONS
        if reason != "not_over" and any(r.end_reason == reason for r in records)
    }
    lengths = [r.length / TICK_HZ for r in records]
    launches = [t / TICK_HZ for r in records for t in r.launch_ticks]
    defender_wins = [r for r in records if r.winner == 0 and r.transports > 0]
    return RosterSummary(
        name=name,
        n=n,
        team0_win=round(float(np.mean(winners == 0)) + draws / 2, 4),
        team1_win=round(float(np.mean(winners == 1)) + draws / 2, 4),
        draw_rate=round(draws, 4),
        time_limit_rate=reasons.get("time_limit", 0.0),
        end_reasons=reasons,
        length_median_s=round(quantile(lengths, 0.5), 1),
        length_p90_s=round(quantile(lengths, 0.9), 1),
        launches_per_match=round(len(launches) / n, 2),
        launch_median_s=round(quantile(launches, 0.5), 1),
        launch_p90_s=round(quantile(launches, 0.9), 1),
        launches_by_bin=launch_histogram([r.launch_ticks for r in records], horizon_s),
        escaped_mean=round(float(np.mean([r.escaped for r in records])), 2),
        destroyed_mean=round(float(np.mean([r.destroyed for r in records])), 2),
        progress_mean=round(float(np.mean([r.progress for r in records])), 3),
        defender_wins_with_escape=round(
            float(np.mean([r.escaped > 0 for r in defender_wins])) if defender_wins else 0.0,
            3,
        ),
        carrier_travel_m=round(
            float(np.mean([sum(r.carrier_travel) / 2 for r in records])), 1
        ),
    )


@dataclass(frozen=True)
class MissionResult:
    mission: str
    time_limit_s: float
    rosters: list[RosterSummary]
    overall: RosterSummary


@dataclass(frozen=True)
class SurveyResult:
    mode: str
    pilot: str
    n_per_roster: int
    seed: int
    sim_version: int
    missions: list[MissionResult]
    seconds: float
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _Pilot:
    """The learned pilot for the live mode (``spacefight.eval.controllers.Policy``)."""

    def __init__(self, checkpoint: Path, seed: int) -> None:
        from spacefight.eval.controllers import Policy

        self.policy = Policy(checkpoint, sample=True)
        self.policy.reset(seed)
        self.label = self.policy.label

    def act(self, env: Any, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        return self.policy.act(env, rows)


def _carrier_slots(roster: RosterSpec, roles: dict[str, str]) -> list[int]:
    slots: list[int] = []
    for s, hull in enumerate(roster.fleets[0] + roster.fleets[1]):
        if roles[hull] == "carrier":
            slots.append(s)
    return slots


def run_mission(
    mission: str,
    rosters: Sequence[RosterSpec],
    n_per_roster: int,
    seed: int,
    pilot: _Pilot | None,
    n_threads: int = 0,
    assets_dir: Path = ASSETS,
) -> tuple[list[MatchRecord], float]:
    """Play every roster ``n_per_roster`` times; the records and the time limit (s).

    ``pilot`` None is the script mode; otherwise it flies every strike craft.

    Raises:
        ValueError: No rosters, or ``n_per_roster`` < 1.
        RuntimeError: A match did not end within its time limit.
    """
    if not rosters or n_per_roster < 1:
        raise ValueError("need at least one roster and n_per_roster >= 1")
    roles = load_roles(assets_dir)
    time_limit_s = float(rlf_sim.mission_time_limit_s(mission))
    n_envs = len(rosters) * n_per_roster
    block = np.repeat(np.arange(len(rosters)), n_per_roster)
    max_ships = max(r.n_ships for r in rosters)
    first = rosters[0]
    env = rlf_sim.VecEnv(
        str(assets_dir),
        n_envs,
        [list(first.fleets[0]), list(first.fleets[1])],
        seed,
        arena_radius=float(rlf_sim.arena_radius_for_mission(mission, first.n_ships)),
        time_limit_s=time_limit_s,
        n_threads=n_threads,
        record_events=True,
        max_ships=max_ships,
        mission=mission,
    )
    for i, k in enumerate(block):
        r = rosters[int(k)]
        radius = float(rlf_sim.arena_radius_for_mission(mission, r.n_ships))
        env.set_next_roster(i, [list(r.fleets[0]), list(r.fleets[1])], radius, mission)
    env.reset()

    hull_names = sorted({h for r in rosters for f in r.fleets for h in f})
    # Hull ids follow the catalogue (sorted by name), which may hold more hulls.
    catalogue = sorted(load_roles(assets_dir))
    strike_ids = [catalogue.index(h) for h in hull_names if roles[h] not in CAPITAL_ROLES]
    transport_ids = {catalogue.index(h) for h in hull_names if roles[h] == "transport"}
    team = np.array(env.team, dtype=np.int64)
    hull = np.array(env.hull_id, dtype=np.int64)
    strike = np.isin(hull, strike_ids) & (team >= 0)
    is_transport = np.isin(hull, list(transport_ids))
    carriers = [_carrier_slots(rosters[int(k)], roles) for k in block]

    records = [
        MatchRecord(roster=rosters[int(k)].name, length=0, winner=-2, end_reason="not_over")
        for k in block
    ]
    for i, rec in enumerate(records):
        rec.transports = int(is_transport[i].sum())
    done = np.zeros(n_envs, dtype=bool)
    last_pos: dict[tuple[int, int], tuple[float, float]] = {}
    travel = np.zeros((n_envs, 2), dtype=np.float64)
    limit = int(round(time_limit_s * TICK_HZ)) + 2
    for step in range(limit):
        if done.all():
            break
        env.scripted_actions()
        if pilot is not None:
            rows = strike & np.asarray(env.alive) & ~done[:, None]
            if rows.any():
                acts = pilot.act(env, rows)
                actions = np.asarray(env.actions)
                actions[rows] = acts
        tick = np.array(env.tick, dtype=np.int64)
        if mission == "convoy_escort" and step % PROGRESS_EVERY == 0:
            for i in np.flatnonzero(~done):
                convoy = env.mission_state(int(i))["convoy"]
                records[i].progress = float(convoy["progress"])
        if mission == "carrier_battle" and step % PROGRESS_EVERY == 0:
            for i in np.flatnonzero(~done):
                ships = env.render_state(int(i))["ships"]
                for side, slot in enumerate(carriers[i]):
                    pos = ships[slot]["pos"]
                    key = (int(i), side)
                    if key in last_pos and ships[slot]["alive"]:
                        prev = last_pos[key]
                        travel[i, side] += float(np.hypot(pos[0] - prev[0], pos[1] - prev[1]))
                    last_pos[key] = (float(pos[0]), float(pos[1]))
        env.step()
        events = env.events()
        if len(events):
            live = ~done[events[:, 0].astype(np.int64)]
            for e in events[live]:
                i, kind, ship = int(e[0]), int(e[1]), int(e[2])
                if kind == KIND_LAUNCH:
                    records[i].launch_ticks.append(int(tick[i]) + 1)
                elif kind == KIND_JUMP_OUT:
                    records[i].escaped += 1
                elif kind == KIND_DEATH and is_transport[i, ship]:
                    records[i].destroyed += 1
        dones = np.asarray(env.dones)
        winner = np.asarray(env.winner)
        reason = np.asarray(env.end_reason)
        for i in np.flatnonzero(dones & ~done):
            rec = records[i]
            rec.length = int(tick[i]) + 1
            rec.winner = int(winner[i])
            rec.end_reason = END_REASONS[int(reason[i])]
            rec.carrier_travel = (float(travel[i, 0]), float(travel[i, 1]))
            if rec.escaped and mission == "convoy_escort":
                rec.progress = max(rec.progress, rec.escaped / max(1, rec.transports))
            done[i] = True
    if not done.all():
        raise RuntimeError(f"{mission}: {int((~done).sum())} matches did not end in time")
    return records, time_limit_s


def survey(
    mode: str,
    n_per_roster: int,
    seed: int,
    checkpoint: Path | None,
    missions: Sequence[str] = MISSIONS,
    n_threads: int = 0,
) -> SurveyResult:
    """Run the survey in ``mode`` over ``missions``.

    Raises:
        ValueError: Unknown mode, or the live mode without a checkpoint.
    """
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; known: {MODES}")
    if mode == "live" and checkpoint is None:
        raise ValueError("the live mode needs a pilot checkpoint")
    start = time.time()
    pilot = _Pilot(checkpoint, seed) if mode == "live" and checkpoint else None
    results = []
    for k, mission in enumerate(missions):
        rosters = default_rosters(mission)
        records, time_limit_s = run_mission(
            mission, rosters, n_per_roster, seed + 10_000 * k, pilot, n_threads
        )
        summaries = [
            summarise(r.name, [m for m in records if m.roster == r.name], time_limit_s)
            for r in rosters
        ]
        results.append(
            MissionResult(
                mission=mission,
                time_limit_s=time_limit_s,
                rosters=summaries,
                overall=summarise("all", records, time_limit_s),
            )
        )
    return SurveyResult(
        mode=mode,
        pilot=pilot.label if pilot else "script",
        n_per_roster=n_per_roster,
        seed=seed,
        sim_version=int(rlf_sim.SIM_VERSION),
        missions=results,
        seconds=round(time.time() - start, 1),
    )


def markdown(result: SurveyResult) -> str:
    """Per-mission roster tables, Markdown."""
    out = [f"mode **{result.mode}** ({result.pilot}), n = {result.n_per_roster} per roster"]
    for m in result.missions:
        convoy = m.mission == "convoy_escort"
        side0, side1 = ("defenders", "attackers") if convoy else ("team 0", "team 1")
        out += ["", f"### {m.mission} (time limit {m.time_limit_s:.0f} s)", ""]
        head = (
            f"| roster | {side0} win | {side1} win | time limit | median s | p90 s "
            "| end reasons |"
        )
        rule = "|---|---|---|---|---|---|---|"
        if convoy:
            head += " escaped | destroyed | progress | wins w/ escape |"
            rule += "---|---|---|---|"
        else:
            head += " launches | launch median s | launch p90 s | launches per 30 s | carrier travel m |"
            rule += "---|---|---|---|---|"
        out += [head, rule]
        for r in [*m.rosters, m.overall]:
            reasons = ", ".join(f"{k} {v:.2f}" for k, v in r.end_reasons.items())
            row = (
                f"| {r.name} | {r.team0_win:.2f} | {r.team1_win:.2f} | "
                f"{r.time_limit_rate:.2f} | {r.length_median_s:.0f} | "
                f"{r.length_p90_s:.0f} | {reasons} |"
            )
            if convoy:
                row += (
                    f" {r.escaped_mean:.2f} | {r.destroyed_mean:.2f} | "
                    f"{r.progress_mean:.2f} | {r.defender_wins_with_escape:.2f} |"
                )
            else:
                bins = " ".join(f"{b:.1f}" for b in r.launches_by_bin)
                row += (
                    f" {r.launches_per_match:.1f} | {r.launch_median_s:.0f} | "
                    f"{r.launch_p90_s:.0f} | {bins} | {r.carrier_travel_m:.0f} |"
                )
            out.append(row)
    return "\n".join(out)


def _champion_checkpoint(champion_id: str) -> Path:
    from tools import champion

    return champion.fetch(champion.find_champion(champion_id))


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--mode", choices=MODES, default="script")
    p.add_argument("--n", type=int, default=64, help="matches per roster")
    p.add_argument("--seed", type=int, default=500_000)
    p.add_argument("--mission", choices=MISSIONS, nargs="+", default=list(MISSIONS))
    p.add_argument("--checkpoint", type=Path, help="live mode pilot (default: champion)")
    p.add_argument("--champion", default="current", help="champion id for --mode live")
    p.add_argument("--n-threads", type=int, default=0)
    p.add_argument("--out", type=Path, help="write the JSON result here")
    args = p.parse_args(argv)
    checkpoint = args.checkpoint
    if args.mode == "live" and checkpoint is None:
        checkpoint = _champion_checkpoint(args.champion)
    result = survey(args.mode, args.n, args.seed, checkpoint, args.mission, args.n_threads)
    print(markdown(result))
    print(f"\n({result.seconds:.0f} s)")
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result.to_dict(), indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
