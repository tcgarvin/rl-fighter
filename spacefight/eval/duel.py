"""Fixed 1v1 fighter duel eval (learnability spike plan §6.1).

``evaluate(a, b)`` runs ``n`` one-episode duels in one ``RustVecEnv`` (env ``i`` is
match ``i`` of base seed ``seed``; every env is read only until its first ``done``).
Env ``i`` puts ``a`` on team ``i % 2``, so exactly half the matches have ``a`` on
each side and arrival-side bias cancels. The result carries match-level numbers and
per-side metrics, serialises to versioned JSON and prints as a Markdown row.

    python -m spacefight.eval.duel --a script --b script --n 512 --out script.json
    python -m spacefight.eval.duel --a checkpoints/bc.pt --b script --argmax

Metric definitions (per side, over that side's ships, until the match's first end):

- *win rate*: (wins + ½ draws) / n; a draw is ``winner == -1`` (mutual kill, or equal
  value at the time limit).
- *kill rate*: share of matches that ended with a ``Death`` event on the final step;
  the rest ended on the time limit.
- *passes*: entries into gun range, i.e. transitions of the distance to the nearest
  present enemy from ``>=`` to ``<`` the ship's gun range (shared with
  ``tools/duel_sweep.py``); mean per match.
- *shots*: ``Fire`` events; *hits*, *damage dealt*: rows of the ``hits`` buffer with
  the side as shooter (hull damage after armour; shield damage separately); means
  per match. *hit rate*: total hits / total shots.
- *live tick*: a post-step tick where the ship is present (active) and the match is
  still running. *engagement rate*: share of live ticks with an enemy present within
  1.2 × gun range. *outside share*: live ticks with ``|pos| > R``.
  *main-engine duty*: mean ``thrust_level`` of the strongest thruster over live
  ticks. *mean speed*: m/s over live ticks.
- *fire rate*: share of decisions (rows with ``act_mask`` true) whose action pulls
  the trigger of at least one present turret. *shots per s*: shots / live seconds.
- *nan_or_stuck*: matches where a ship of the side had a NaN in its obs, or moved
  slower than 1 m/s for more than 10 s straight while an enemy was present.

Match-level crash numbers (SIM_VERSION 3 collision damage, SIM_SPEC §5.5):

- *crashes per match*: ``Collision`` events (damaging contacts) per match.
- *crash hp share*: collision hull damage over all weapon plus collision hull damage
  (both sides; arena drain is not counted).

Schema ``rlf.eval.duel/2`` adds those two to ``match``; ``from_dict`` still reads
``/1`` files and fills them with 0, which is exact for the SIM_VERSION <= 2 sims
those were written with (collisions did no damage).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Self, TypeVar

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.rust_env import (
    ACTION_LAYOUT,
    OBS_LAYOUT,
    OBS_SLOTS,
    RustVecEnv,
)
from spacefight.eval import features as F
from spacefight.eval.controllers import Controller, idle_actions, make_controller

ASSETS = Path(__file__).resolve().parents[2] / "assets"
SCHEMA = "rlf.eval.duel/2"
# Older schemas ``from_dict`` still reads, with the defaults for the keys they lack.
LEGACY_MATCH_DEFAULTS: dict[str, dict[str, float]] = {
    "rlf.eval.duel/1": {"crashes_per_match": 0.0, "crash_hp_share": 0.0},
}
FLEETS: tuple[tuple[str, ...], ...] = (("fighter",), ("fighter",))
TICK_HZ = 30
ENGAGEMENT_RANGE_FACTOR = 1.2
STUCK_SPEED = 1.0  # m/s
STUCK_SECONDS = 10.0

_T = TypeVar("_T")


@dataclass(frozen=True)
class EvalConfig:
    """The scenario of one evaluation (everything that changes its numbers)."""

    n: int = 512
    seed: int = 100_000
    reaction_ticks: int = 2
    arena_radius: float = 450.0
    time_limit_s: float = 90.0
    fleets: tuple[tuple[str, ...], ...] = FLEETS
    sim_version: int = int(rlf_sim.SIM_VERSION)


@dataclass
class MatchRecords:
    """Raw per-match ``[N]`` and per-ship ``[N, S]`` measurements of one evaluation.

    Counters cover each match from reset to its first ``done`` (the done step
    included for events and hits; post-step obs only while the match runs).
    """

    a_team: NDArray[np.int64]  # [N] team index driven by controller ``a``
    team: NDArray[np.int64]  # [N, S] team of each ship slot
    length: NDArray[np.int64]  # [N] steps until the first done
    winner: NDArray[np.int64]  # [N] -1 draw, else winning team
    killed: NDArray[np.bool_]  # [N] ended with a death on the final step
    passes: NDArray[np.int64]
    shots: NDArray[np.int64]
    hits: NDArray[np.int64]
    hull_damage: NDArray[np.float64]  # dealt, after armour
    shield_damage: NDArray[np.float64]  # dealt
    crashes: NDArray[np.int64]  # [N] Collision events (v3)
    crash_damage: NDArray[np.float64]  # taken from collisions, hull, after impact arcs
    live_ticks: NDArray[np.int64]
    engaged_ticks: NDArray[np.int64]
    outside_ticks: NDArray[np.int64]
    engine_level: NDArray[np.float64]  # sum over live ticks
    speed: NDArray[np.float64]  # sum over live ticks, m/s
    decisions: NDArray[np.int64]
    triggers: NDArray[np.int64]
    nan: NDArray[np.bool_]
    stuck: NDArray[np.bool_]


@dataclass(frozen=True)
class MatchMetrics:
    """Match-level numbers (shared by both sides)."""

    length_median: float
    length_p10: float
    length_p90: float
    kill_rate: float
    time_limit_rate: float
    draw_rate: float
    a_win_rate_team0: float  # a's win rate in the matches where a is team 0
    a_win_rate_team1: float
    crashes_per_match: float  # damaging collisions (v3)
    crash_hp_share: float  # collision share of weapon + collision hull damage


@dataclass(frozen=True)
class SideMetrics:
    """Per-side numbers; counts are per match means unless named ``*_rate``."""

    wins: int
    draws: int
    losses: int
    win_rate: float
    passes: float
    shots: float
    hits: float
    hit_rate: float
    damage_dealt: float
    shield_damage_dealt: float
    engagement_rate: float
    outside_share: float
    main_engine_duty: float
    fire_rate: float
    shots_per_s: float
    mean_speed: float
    nan_matches: int
    stuck_matches: int
    nan_or_stuck: int


MARKDOWN_HEADER = (
    "| a | b | n | win | draw | loss | length med (p10–p90) | kill | passes | shots "
    "| hits | hit rate | dmg | engage | outside | engine | fire | speed | nan/stuck |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
)


@dataclass(frozen=True)
class DuelResult:
    """Outcome of ``evaluate(a, b)``; JSON schema ``SCHEMA``."""

    a: str
    b: str
    config: EvalConfig
    match: MatchMetrics
    side_a: SideMetrics
    side_b: SideMetrics
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict (tuples become lists)."""
        return asdict(self)

    def to_json(self) -> str:
        """Indented JSON text of ``to_dict``."""
        return json.dumps(self.to_dict(), indent=1)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Rebuild a result from ``to_dict`` output.

        Reads the current ``SCHEMA`` and the legacy schemas of
        ``LEGACY_MATCH_DEFAULTS`` (whose missing match keys get those defaults); the
        result always carries the current ``SCHEMA``.

        Raises:
            ValueError: Unknown schema version or missing/unknown keys.
        """
        schema = data.get("schema")
        if schema == SCHEMA:
            match_data = data["match"]
        elif isinstance(schema, str) and schema in LEGACY_MATCH_DEFAULTS:
            defaults = LEGACY_MATCH_DEFAULTS[schema]
            clash = sorted(set(defaults) & set(data["match"]))
            if clash:
                raise ValueError(f"{schema} match has newer keys {clash}")
            match_data = {**data["match"], **defaults}
        else:
            known = [SCHEMA, *LEGACY_MATCH_DEFAULTS]
            raise ValueError(f"expected schema in {known!r}, got {schema!r}")
        _check_keys(cls, data)
        cfg = dict(data["config"])
        _check_keys(EvalConfig, cfg)
        cfg["fleets"] = tuple(tuple(team) for team in cfg["fleets"])
        return cls(
            a=data["a"],
            b=data["b"],
            config=EvalConfig(**cfg),
            match=_build(MatchMetrics, match_data),
            side_a=_build(SideMetrics, data["side_a"]),
            side_b=_build(SideMetrics, data["side_b"]),
        )

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Parse ``to_json`` output (see ``from_dict``)."""
        return cls.from_dict(json.loads(text))

    def markdown_row(self, side: str = "a") -> str:
        """One ``MARKDOWN_HEADER`` row from the point of view of ``side`` ("a"/"b").

        Raises:
            ValueError: ``side`` is not "a" or "b".
        """
        if side not in ("a", "b"):
            raise ValueError(f"side must be 'a' or 'b', got {side!r}")
        me, other = (self.a, self.b) if side == "a" else (self.b, self.a)
        s = self.side_a if side == "a" else self.side_b
        m = self.match
        n = self.config.n
        return (
            f"| {me} | {other} | {n} | {s.win_rate:.3f} | {s.draws / n:.3f} "
            f"| {s.losses / n:.3f} | {m.length_median:.0f} "
            f"({m.length_p10:.0f}–{m.length_p90:.0f}) | {m.kill_rate:.3f} "
            f"| {s.passes:.2f} | {s.shots:.1f} | {s.hits:.1f} | {s.hit_rate:.3f} "
            f"| {s.damage_dealt:.1f} | {s.engagement_rate:.3f} "
            f"| {s.outside_share:.4f} | {s.main_engine_duty:.3f} "
            f"| {s.fire_rate:.3f} | {s.mean_speed:.1f} | {s.nan_or_stuck} |"
        )


def _check_keys(cls: type, data: dict[str, Any]) -> None:
    expected = {f.name for f in fields(cls)}
    if set(data) != expected:
        missing = sorted(expected - set(data))
        unknown = sorted(set(data) - expected)
        raise ValueError(
            f"{cls.__name__}: missing keys {missing}, unknown keys {unknown}"
        )


def _build(cls: type[_T], data: dict[str, Any]) -> _T:
    _check_keys(cls, data)
    return cls(**data)


def evaluate(
    a: Controller,
    b: Controller,
    n: int = 512,
    seed: int = 100_000,
    n_threads: int = 12,
    *,
    reaction_ticks: int = 2,
    assets_dir: Path = ASSETS,
) -> DuelResult:
    """Run ``n`` one-episode fighter duels of ``a`` against ``b`` and summarise them.

    Args:
        a: Controller under test (side "a").
        b: Opponent controller.
        n: Matches; must be even (half with ``a`` on each team).
        seed: ``RustVecEnv`` base seed; match ``i`` is its env ``i``.
        n_threads: Sim worker threads (does not change any number).
        reaction_ticks: Sim reaction delay (plan §3: 2).
        assets_dir: Asset directory (hulls, weapons).

    Raises:
        ValueError: ``n`` is odd or < 2.
        RuntimeError: A match did not end within the time limit.
    """
    cfg = EvalConfig(n=n, seed=seed, reaction_ticks=reaction_ticks)
    records = run_matches(a, b, cfg, n_threads=n_threads, assets_dir=assets_dir)
    return summarise(records, cfg, a.label, b.label)


def run_matches(
    a: Controller,
    b: Controller,
    cfg: EvalConfig,
    n_threads: int = 12,
    assets_dir: Path = ASSETS,
) -> MatchRecords:
    """Play the matches of ``cfg`` and return the raw per-match records.

    Raises:
        ValueError: ``cfg.n`` is odd or < 2.
        RuntimeError: A match did not end within the time limit.
    """
    if cfg.n < 2 or cfg.n % 2:
        raise ValueError(f"n must be even and >= 2, got {cfg.n}")
    env = RustVecEnv(
        assets_dir,
        cfg.n,
        [list(t) for t in cfg.fleets],
        cfg.seed,
        arena_radius=cfg.arena_radius,
        time_limit_s=cfg.time_limit_s,
        n_threads=n_threads,
        record_events=True,
        reaction_ticks=cfg.reaction_ticks,
    )
    a.reset(cfg.seed)
    b.reset(cfg.seed + 1)
    tracker = _Tracker(env, cfg)
    max_steps = int(round(cfg.time_limit_s * TICK_HZ)) + 1
    for _ in range(max_steps):
        actions = tracker.choose(env, a, b)
        _, _, dones, info = env.step(actions)
        tracker.observe(
            env,
            dones.copy(),
            info.winner,
            info.hits,
            info.hit_count,
            info.collision_damage,
        )
        if not tracker.running.any():
            return tracker.records
    raise RuntimeError(
        f"{int(tracker.running.sum())} matches did not end within {max_steps} steps"
    )


class _Tracker:
    """Accumulates ``MatchRecords`` step by step for the still-running matches."""

    def __init__(self, env: RustVecEnv, cfg: EvalConfig) -> None:
        n, s = env.n_envs, env.n_ships
        self.radius = cfg.arena_radius
        self.stuck_ticks = int(round(STUCK_SECONDS * TICK_HZ))
        self.running = np.ones(n, dtype=bool)
        self.in_range = np.zeros((n, s), dtype=bool)
        self.slow_run = np.zeros((n, s), dtype=np.int64)
        team = env.team.astype(np.int64)
        a_team = np.arange(n, dtype=np.int64) % 2
        self.a_rows = team == a_team[:, None]
        self.records = MatchRecords(
            a_team=a_team,
            team=team,
            length=np.zeros(n, dtype=np.int64),
            winner=np.full(n, -2, dtype=np.int64),
            killed=np.zeros(n, dtype=bool),
            passes=np.zeros((n, s), dtype=np.int64),
            shots=np.zeros((n, s), dtype=np.int64),
            hits=np.zeros((n, s), dtype=np.int64),
            hull_damage=np.zeros((n, s), dtype=np.float64),
            shield_damage=np.zeros((n, s), dtype=np.float64),
            crashes=np.zeros(n, dtype=np.int64),
            crash_damage=np.zeros((n, s), dtype=np.float64),
            live_ticks=np.zeros((n, s), dtype=np.int64),
            engaged_ticks=np.zeros((n, s), dtype=np.int64),
            outside_ticks=np.zeros((n, s), dtype=np.int64),
            engine_level=np.zeros((n, s), dtype=np.float64),
            speed=np.zeros((n, s), dtype=np.float64),
            decisions=np.zeros((n, s), dtype=np.int64),
            triggers=np.zeros((n, s), dtype=np.int64),
            nan=np.zeros((n, s), dtype=bool),
            stuck=np.zeros((n, s), dtype=bool),
        )
        self.steps = 0

    def choose(self, env: RustVecEnv, a: Controller, b: Controller) -> NDArray[np.int8]:
        """Assemble this step's actions and count the decisions they make."""
        n, s = env.n_envs, env.n_ships
        decide = self.running[:, None] & env.act_mask
        actions = idle_actions(n * s).reshape(n, s, -1)
        for ctrl, side in ((a, self.a_rows), (b, ~self.a_rows)):
            rows = decide & side
            actions[rows] = ctrl.act(env, rows)
        offset, width = ACTION_LAYOUT["fire"]
        fire = actions[..., offset : offset + width] > 0
        pulled = (fire & env.turret_mask).any(axis=-1)
        self.records.decisions += decide
        self.records.triggers += decide & pulled
        return actions

    def observe(
        self,
        env: RustVecEnv,
        dones: NDArray[np.bool_],
        winner: NDArray[np.int8],
        hits: NDArray[np.int32],
        hit_count: NDArray[np.int32],
        collision_damage: NDArray[np.float32],
    ) -> None:
        """Fold one step's events, hits, collision damage and post-step obs into
        the records."""
        self.steps += 1
        r = self.records
        running = self.running
        events = env.events()
        events = events[running[events[:, F.EV_MATCH].astype(np.int64)]]
        self._count_events(events)
        self._count_hits(hits, hit_count)
        r.crash_damage += np.where(running[:, None], collision_damage, 0.0)

        ending = running & dones
        died = np.zeros_like(running)
        deaths = events[events[:, F.EV_KIND] == F.KIND_DEATH]
        died[deaths[:, F.EV_MATCH].astype(np.int64)] = True
        r.length[ending] = self.steps
        r.winner[ending] = winner[ending]
        r.killed[ending] = died[ending]

        # Post-step obs of a finished match already belong to its successor.
        live_match = running & ~dones
        self._count_obs(env.obs, live_match)
        self.running = running & ~dones

    def _count_events(self, events: NDArray[np.float32]) -> None:
        fire = events[events[:, F.EV_KIND] == F.KIND_FIRE]
        np.add.at(
            self.records.shots,
            (fire[:, F.EV_MATCH].astype(np.int64), fire[:, F.EV_A].astype(np.int64)),
            1,
        )
        crash = events[events[:, F.EV_KIND] == F.KIND_COLLISION]
        np.add.at(self.records.crashes, crash[:, F.EV_MATCH].astype(np.int64), 1)

    def _count_hits(
        self, hits: NDArray[np.int32], hit_count: NDArray[np.int32]
    ) -> None:
        r = self.records
        valid = (np.arange(hits.shape[1]) < hit_count[:, None]) & self.running[:, None]
        match, _ = np.nonzero(valid)
        rows = hits[valid]
        shooter = rows[:, F.HIT_SHOOTER].astype(np.int64)
        damage = rows[:, F.HIT_DAMAGE] / float(rlf_sim.HIT_DAMAGE_SCALE)
        shield = rows[:, F.HIT_SHIELD] != 0
        np.add.at(r.hits, (match, shooter), 1)
        np.add.at(r.hull_damage, (match[~shield], shooter[~shield]), damage[~shield])
        np.add.at(r.shield_damage, (match[shield], shooter[shield]), damage[shield])

    def _count_obs(
        self, obs: NDArray[np.float32], live_match: NDArray[np.bool_]
    ) -> None:
        r = self.records
        present = obs[..., F.SELF_PRESENT] > 0.5
        live = live_match[:, None] & present
        r.nan |= live_match[:, None] & np.isnan(obs).any(axis=-1)

        ships = _block(obs, "ships")
        enemy = (ships[..., F.SHIP_PRESENT] > 0.5) & (ships[..., F.SHIP_IS_ENEMY] > 0.5)
        enemy_dist = np.where(enemy, ships[..., F.SHIP_DIST] * self.radius, np.inf)
        dist = enemy_dist.min(axis=-1)
        enemy_present = enemy.any(axis=-1)

        turret_present = _block(obs, "turrets")[..., 0] > 0.5
        ranges = obs[..., slice(*_span("turret_range"))] * self.radius
        gun_range = np.where(turret_present, ranges, 0.0).max(axis=-1)

        measured = live & enemy_present
        entered, self.in_range = F.range_entries(
            measured, dist < gun_range, self.in_range
        )
        r.passes += entered
        r.engaged_ticks += measured & (dist < ENGAGEMENT_RANGE_FACTOR * gun_range)
        r.live_ticks += live
        r.outside_ticks += live & (obs[..., F.SELF_EDGE_MARGIN] < 0.0)

        thrusters = _block(obs, "thrusters")
        accel = np.where(
            thrusters[..., F.THRUSTER_PRESENT] > 0.5,
            thrusters[..., F.THRUSTER_ACCEL],
            -np.inf,
        )
        main = accel.argmax(axis=-1)[..., None]
        level = np.take_along_axis(thrusters[..., F.THRUSTER_LEVEL], main, axis=-1)
        r.engine_level += np.where(live, level[..., 0], 0.0)

        speed = obs[..., F.SELF_SPEED] * F.VELOCITY_SCALE
        r.speed += np.where(live, speed, 0.0)
        slow = measured & (speed < STUCK_SPEED)
        self.slow_run = np.where(slow, self.slow_run + 1, 0)
        r.stuck |= self.slow_run > self.stuck_ticks


def _span(name: str) -> tuple[int, int]:
    offset, width = OBS_LAYOUT[name]
    return offset, offset + width


def _block(obs: NDArray[np.float32], name: str) -> NDArray[np.float32]:
    lo, hi = _span(name)
    slots = OBS_SLOTS[name]
    return obs[..., lo:hi].reshape(*obs.shape[:-1], slots, (hi - lo) // slots)


def summarise(
    records: MatchRecords, cfg: EvalConfig, a_label: str, b_label: str
) -> DuelResult:
    """Reduce ``records`` to a ``DuelResult``."""
    r = records
    a_won = r.winner == r.a_team
    draw = r.winner == -1
    a_score = a_won + 0.5 * draw
    q10, q50, q90 = np.percentile(r.length, [10, 50, 90])
    crash_hp = float(r.crash_damage.sum())
    all_hp = crash_hp + float(r.hull_damage.sum())
    match = MatchMetrics(
        length_median=float(q50),
        length_p10=float(q10),
        length_p90=float(q90),
        kill_rate=float(r.killed.mean()),
        time_limit_rate=float((~r.killed).mean()),
        draw_rate=float(draw.mean()),
        a_win_rate_team0=float(a_score[r.a_team == 0].mean()),
        a_win_rate_team1=float(a_score[r.a_team == 1].mean()),
        crashes_per_match=float(r.crashes.mean()),
        crash_hp_share=crash_hp / all_hp if all_hp > 0 else 0.0,
    )
    a_rows = r.team == r.a_team[:, None]
    return DuelResult(
        a=a_label,
        b=b_label,
        config=cfg,
        match=match,
        side_a=_side_metrics(r, a_rows, a_won, draw),
        side_b=_side_metrics(r, ~a_rows, ~a_won & ~draw, draw),
    )


def _side_metrics(
    r: MatchRecords,
    rows: NDArray[np.bool_],
    won: NDArray[np.bool_],
    draw: NDArray[np.bool_],
) -> SideMetrics:
    n = r.length.shape[0]

    def total(x: NDArray[Any]) -> float:
        return float(np.where(rows, x, 0).sum())

    def ratio(num: float, den: float) -> float:
        return num / den if den > 0 else 0.0

    wins, draws = int(won.sum()), int(draw.sum())
    live = total(r.live_ticks)
    nan = (r.nan & rows).any(axis=1)
    stuck = (r.stuck & rows).any(axis=1)
    return SideMetrics(
        wins=wins,
        draws=draws,
        losses=n - wins - draws,
        win_rate=(wins + 0.5 * draws) / n,
        passes=total(r.passes) / n,
        shots=total(r.shots) / n,
        hits=total(r.hits) / n,
        hit_rate=ratio(total(r.hits), total(r.shots)),
        damage_dealt=total(r.hull_damage) / n,
        shield_damage_dealt=total(r.shield_damage) / n,
        engagement_rate=ratio(total(r.engaged_ticks), live),
        outside_share=ratio(total(r.outside_ticks), live),
        main_engine_duty=ratio(total(r.engine_level), live),
        fire_rate=ratio(total(r.triggers), total(r.decisions)),
        shots_per_s=ratio(total(r.shots), live / TICK_HZ),
        mean_speed=ratio(total(r.speed), live),
        nan_matches=int(nan.sum()),
        stuck_matches=int(stuck.sum()),
        nan_or_stuck=int((nan | stuck).sum()),
    )


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--a", default="script", help="script, random or a checkpoint")
    p.add_argument("--b", default="script", help="script, random or a checkpoint")
    p.add_argument("--n", type=int, default=512, help="matches (even)")
    p.add_argument("--seed", type=int, default=100_000, help="base env seed")
    p.add_argument("--n-threads", type=int, default=12)
    p.add_argument("--reaction-ticks", type=int, default=2)
    p.add_argument(
        "--argmax", action="store_true", help="policies take the argmax action"
    )
    p.add_argument("--out", type=Path, help="write the DuelResult JSON here")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run one evaluation, print Markdown rows, write JSON."""
    args = parse_args(argv)
    sample = not args.argmax
    a = make_controller(args.a, sample=sample, seed=0)
    b = make_controller(args.b, sample=sample, seed=1)
    result = evaluate(
        a,
        b,
        n=args.n,
        seed=args.seed,
        n_threads=args.n_threads,
        reaction_ticks=args.reaction_ticks,
    )
    print(MARKDOWN_HEADER)
    print(result.markdown_row("a"))
    print(result.markdown_row("b"))
    m = result.match
    print(
        f"team-0 a win rate {m.a_win_rate_team0:.3f}, team-1 {m.a_win_rate_team1:.3f}; "
        f"draws {m.draw_rate:.3f}, time limit {m.time_limit_rate:.3f}; "
        f"crashes/match {m.crashes_per_match:.2f}, crash hp share {m.crash_hp_share:.3f}"
    )
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
