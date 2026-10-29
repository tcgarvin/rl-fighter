"""Fixed fleet eval: mixed skirmishes of 1-4 ships a side (fleet pilot v1).

``evaluate(a, b)`` plays every roster of a fixed suite ``n_per_roster`` times in one
``RustVecEnv`` (env ``i`` is match ``i`` of base seed ``seed``; every env is read only
until its first ``done``). Inside each roster's block of envs, env ``i`` puts ``a`` on
team ``i % 2``, so ``a`` flies each side of every roster (the small and the large
side of an uneven one) equally often. Arena radii follow the shared rule
(``spacefight.env.rosters.arena_radius_for``).

    python -m spacefight.eval.fleet --a ckpt.pt --b script --out fleet.json
    python -m spacefight.eval.fleet --a script --b script --suite survey

Metrics (``a``'s side unless named per side; JSON schema ``rlf.eval.fleet/1``):

- *win rate*: (wins + ½ draws) / matches, per roster, per roster class and overall
  (every roster weighs the same). A time-limit ending goes to the team with more
  ``hp + ½ shield`` left (SIM_SPEC §5.8); a *draw* is ``winner == -1``.
  ``team0_win_rate`` is the roster's first team's rate whoever flies it (balance).
- per hull and side, averaged over ship-matches: *damage dealt* (hull, after armour),
  *shield damage dealt*, *survival* (alive when the match ends), *hit rate* (hits /
  shots; a beam pulse is a shot), *shots*, *engagement* (share of live ticks with an
  enemy within 1.2 × the ship's longest weapon range), *outside share*, *engine duty*
  (mean level of the strongest thruster), *passes* (entries into gun range of the
  nearest enemy, as in the duel eval), *crash damage taken* and *crash contacts*
  (damaging ``Collision`` events the ship was in).
- per side over all ships: the same, plus *fire rate* (decisions that pull a
  present turret's trigger) and NaN / stuck matches (stuck: slower than 1 m/s for
  more than 10 s straight with an enemy present).
- match-level: length median / p10 / p90, draw rate, time-limit rate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Self

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.rosters import Roster
from spacefight.env.rust_env import ACTION_LAYOUT, OBS_LAYOUT, OBS_SLOTS, RustVecEnv
from spacefight.eval import features as F
from spacefight.eval.controllers import Controller, idle_actions, make_controller

ASSETS = Path(__file__).resolve().parents[2] / "assets"
SCHEMA = "rlf.eval.fleet/1"
TICK_HZ = 30
ENGAGEMENT_RANGE_FACTOR = 1.2
STUCK_SPEED = 1.0  # m/s
STUCK_SECONDS = 10.0
DEFAULT_SEED = 200_000
DEFAULT_N_PER_ROSTER = 64


@dataclass(frozen=True)
class SuiteEntry:
    """One roster of a suite.

    Attributes:
        name: Unique label, e.g. ``"2v2 FS v FS"``.
        klass: Roster class the gates group by (``"1v1"``, ``"2v2"``, ...).
        roster: The teams.
    """

    name: str
    klass: str
    roster: Roster


def _entry(klass: str, team0: str, team1: str) -> SuiteEntry:
    """``team0``/``team1`` as hull letters, e.g. ``_entry("2v2", "FS", "FS")``."""
    full = {"F": "fighter", "S": "strafer", "G": "gunship"}
    roster = Roster.of([full[c] for c in team0], [full[c] for c in team1])
    return SuiteEntry(f"{klass} {team0} v {team1}", klass, roster)


# The fixed yardstick of fleet pilot v1 (lab/runs/2026-10-30-fleet-pilot/plan.md):
# 1v1 of each hull, 2v2 and 3v3 mixed, uneven 2v3, budget drafts, 4v4.
SUITES: dict[str, tuple[SuiteEntry, ...]] = {
    "fleet_v1": (
        _entry("1v1", "F", "F"),
        _entry("1v1", "S", "S"),
        _entry("1v1", "G", "G"),
        _entry("2v2", "FS", "FS"),
        _entry("2v2", "FG", "SS"),
        _entry("2v2", "SG", "FF"),
        _entry("3v3", "FSG", "FSG"),
        _entry("3v3", "FFS", "SSF"),
        _entry("3v3", "FFG", "SSG"),
        _entry("2v3", "FG", "FFS"),
        _entry("2v3", "SS", "FFF"),
        _entry("draft", "G", "FFF"),
        _entry("draft", "G", "SSS"),
        _entry("draft", "GF", "FFSS"),
        _entry("4v4", "FFSS", "FFSS"),
        _entry("4v4", "FSGF", "SSFG"),
    ),
    # Script-vs-script balance survey (plan §2): every 1v1 pairing, cost-matched
    # drafts, mixed fleets.
    "survey": (
        _entry("1v1", "F", "F"),
        _entry("1v1", "S", "S"),
        _entry("1v1", "G", "G"),
        _entry("1v1x", "F", "S"),
        _entry("1v1x", "F", "G"),
        _entry("1v1x", "S", "G"),
        _entry("draft", "G", "FFF"),
        _entry("draft", "G", "SSS"),
        _entry("draft", "G", "FFS"),
        _entry("draft", "GF", "FFSS"),
        _entry("draft", "GS", "SSFF"),
        _entry("draft", "GG", "FFFF"),
        _entry("2v2", "FF", "SS"),
        _entry("2v2", "FS", "FS"),
        _entry("2v2", "FG", "SG"),
        _entry("2v2", "GG", "GG"),
        _entry("3v3", "FFF", "SSS"),
        _entry("3v3", "FSG", "FSG"),
        _entry("2v3", "FS", "FFS"),
        _entry("4v4", "FFFF", "SSSS"),
        _entry("4v4", "FFSS", "FFSS"),
        _entry("4v4", "FSGF", "SSFG"),
    ),
}


@dataclass(frozen=True)
class FleetEvalConfig:
    """The scenario of one evaluation (everything that changes its numbers)."""

    suite: str = "fleet_v1"
    n_per_roster: int = DEFAULT_N_PER_ROSTER
    seed: int = DEFAULT_SEED
    reaction_ticks: int = 2
    time_limit_s: float = 90.0
    # Arena radius in metres for every roster; 0 = the shared rule (surveys only).
    arena_radius: float = 0.0
    sim_version: int = int(rlf_sim.SIM_VERSION)

    def entries(self) -> tuple[SuiteEntry, ...]:
        """The suite's rosters.

        Raises:
            KeyError: Unknown suite name.
        """
        if self.suite not in SUITES:
            raise KeyError(f"unknown suite {self.suite!r}; known: {list(SUITES)}")
        return SUITES[self.suite]


@dataclass(frozen=True)
class RosterOutcome:
    """Results of one roster (side ``a``'s view)."""

    name: str
    klass: str
    label: str
    n: int
    wins: int
    draws: int
    losses: int
    win_rate: float
    team0_win_rate: float  # the roster's first team, whoever flies it
    draw_rate: float
    time_limit_rate: float
    length_median: float


@dataclass(frozen=True)
class ClassOutcome:
    """Results of one roster class (rosters weigh the same)."""

    klass: str
    rosters: int
    n: int
    win_rate: float
    draw_rate: float
    time_limit_rate: float
    length_median: float


@dataclass(frozen=True)
class ShipMetrics:
    """Per-ship means over a set of ship-matches (one hull, or a whole side)."""

    ships: int  # ship-matches
    damage_dealt: float
    shield_damage_dealt: float
    survival: float
    shots: float
    hits: float
    hit_rate: float
    engagement_rate: float
    outside_share: float
    engine_duty: float
    passes: float
    crash_damage_taken: float
    crash_contacts: float
    fire_rate: float


@dataclass(frozen=True)
class SideSummary:
    """One side: overall win rate, all its ships, and per hull."""

    win_rate: float
    draws: int
    all_ships: ShipMetrics
    hulls: dict[str, ShipMetrics]
    nan_matches: int
    stuck_matches: int


@dataclass(frozen=True)
class MatchSummary:
    """Match-level numbers over the whole suite."""

    n: int
    length_median: float
    length_p10: float
    length_p90: float
    draw_rate: float
    time_limit_rate: float


@dataclass(frozen=True)
class FleetResult:
    """Outcome of ``evaluate(a, b)``; JSON schema ``SCHEMA``."""

    a: str
    b: str
    config: FleetEvalConfig
    match: MatchSummary
    classes: dict[str, ClassOutcome]
    rosters: list[RosterOutcome]
    side_a: SideSummary
    side_b: SideSummary
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return asdict(self)

    def to_json(self) -> str:
        """Indented JSON text of ``to_dict``."""
        return json.dumps(self.to_dict(), indent=1)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Rebuild a result from ``to_dict`` output.

        Raises:
            ValueError: Wrong schema or missing / unknown keys.
        """
        if data.get("schema") != SCHEMA:
            raise ValueError(f"expected schema {SCHEMA!r}, got {data.get('schema')!r}")
        _check_keys(cls, data)

        def side(raw: dict[str, Any]) -> SideSummary:
            _check_keys(SideSummary, raw)
            return SideSummary(
                win_rate=raw["win_rate"],
                draws=raw["draws"],
                all_ships=_build(ShipMetrics, raw["all_ships"]),
                hulls={h: _build(ShipMetrics, m) for h, m in raw["hulls"].items()},
                nan_matches=raw["nan_matches"],
                stuck_matches=raw["stuck_matches"],
            )

        return cls(
            a=data["a"],
            b=data["b"],
            config=_build(FleetEvalConfig, data["config"]),
            match=_build(MatchSummary, data["match"]),
            classes={k: _build(ClassOutcome, v) for k, v in data["classes"].items()},
            rosters=[_build(RosterOutcome, r) for r in data["rosters"]],
            side_a=side(data["side_a"]),
            side_b=side(data["side_b"]),
        )

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Parse ``to_json`` output."""
        return cls.from_dict(json.loads(text))

    def markdown(self) -> str:
        """Class table and per-hull table, Markdown."""
        lines = [
            f"**{self.a}** vs **{self.b}**: win {self.side_a.win_rate:.3f}, draws "
            f"{self.match.draw_rate:.3f}, time limit {self.match.time_limit_rate:.3f}, "
            f"median {self.match.length_median:.0f} ticks (n = {self.match.n})",
            "",
            "| class | rosters | n | win | draw | time limit | median ticks |",
            "|---|---|---|---|---|---|---|",
        ]
        for c in self.classes.values():
            lines.append(
                f"| {c.klass} | {c.rosters} | {c.n} | {c.win_rate:.3f} | "
                f"{c.draw_rate:.3f} | {c.time_limit_rate:.3f} | {c.length_median:.0f} |"
            )
        lines += [
            "",
            "| side | hull | ships | dmg | shield dmg | survival | hit rate | shots "
            "| engage | outside | engine | passes | crash dmg | fire |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for label, side in (("a", self.side_a), ("b", self.side_b)):
            for hull, m in [*side.hulls.items(), ("all", side.all_ships)]:
                lines.append(
                    f"| {label} | {hull} | {m.ships} | {m.damage_dealt:.1f} | "
                    f"{m.shield_damage_dealt:.1f} | {m.survival:.2f} | "
                    f"{m.hit_rate:.3f} | {m.shots:.1f} | {m.engagement_rate:.2f} | "
                    f"{m.outside_share:.4f} | {m.engine_duty:.2f} | {m.passes:.2f} | "
                    f"{m.crash_damage_taken:.1f} | {m.fire_rate:.3f} |"
                )
        return "\n".join(lines)


def _check_keys(cls: type, data: dict[str, Any]) -> None:
    expected = {f.name for f in fields(cls)}
    if set(data) != expected:
        missing = sorted(expected - set(data))
        unknown = sorted(set(data) - expected)
        raise ValueError(
            f"{cls.__name__}: missing keys {missing}, unknown keys {unknown}"
        )


def _build(cls: type, data: dict[str, Any]) -> Any:
    _check_keys(cls, data)
    return cls(**data)


# ---------------------------------------------------------------------------
# Running the matches
# ---------------------------------------------------------------------------


@dataclass
class FleetRecords:
    """Raw per-match ``[N]`` and per-slot ``[N, S]`` measurements.

    ``team`` and ``hull`` are each env's first match (the one measured); -1 marks
    padding slots. ``hull_names`` maps the hull ids that occur to names.
    """

    hull_names: dict[int, str]
    entry: NDArray[np.int64]  # [N] suite index
    a_team: NDArray[np.int64]  # [N]
    team: NDArray[np.int64]  # [N, S]
    hull: NDArray[np.int64]  # [N, S]
    length: NDArray[np.int64]
    winner: NDArray[np.int64]
    timed_out: NDArray[np.bool_]
    died: NDArray[np.bool_]
    passes: NDArray[np.int64]
    shots: NDArray[np.int64]
    hits: NDArray[np.int64]
    hull_damage: NDArray[np.float64]
    shield_damage: NDArray[np.float64]
    crash_damage: NDArray[np.float64]
    crash_contacts: NDArray[np.int64]
    live_ticks: NDArray[np.int64]
    engaged_ticks: NDArray[np.int64]
    outside_ticks: NDArray[np.int64]
    engine_level: NDArray[np.float64]
    decisions: NDArray[np.int64]
    triggers: NDArray[np.int64]
    nan: NDArray[np.bool_]
    stuck: NDArray[np.bool_]


def build_env(
    cfg: FleetEvalConfig, n_threads: int, assets_dir: Path = ASSETS
) -> tuple[RustVecEnv, NDArray[np.int64]]:
    """The suite's env (every roster ``n_per_roster`` times) and each env's entry.

    Raises:
        ValueError: ``n_per_roster`` odd or < 2.
    """
    if cfg.n_per_roster < 2 or cfg.n_per_roster % 2:
        raise ValueError(f"n_per_roster must be even and >= 2, got {cfg.n_per_roster}")
    entries = cfg.entries()
    entry = np.repeat(np.arange(len(entries), dtype=np.int64), cfg.n_per_roster)
    env = RustVecEnv(
        assets_dir,
        entry.size,
        [["fighter"], ["fighter"]],
        cfg.seed,
        time_limit_s=cfg.time_limit_s,
        n_threads=n_threads,
        record_events=True,
        reaction_ticks=cfg.reaction_ticks,
        max_ships=max(e.roster.n_ships for e in entries),
    )
    for i, k in enumerate(entry):
        radius = cfg.arena_radius if cfg.arena_radius > 0 else None
        env.set_next_roster(i, entries[int(k)].roster, arena_radius=radius)
    env.reset()
    return env, entry


def run_matches(
    a: Controller,
    b: Controller,
    cfg: FleetEvalConfig,
    n_threads: int = 12,
    assets_dir: Path = ASSETS,
) -> FleetRecords:
    """Play the suite once and return the raw records.

    Raises:
        RuntimeError: A match did not end within the time limit.
    """
    env, entry = build_env(cfg, n_threads, assets_dir)
    a.reset(cfg.seed)
    b.reset(cfg.seed + 1)
    tracker = _FleetTracker(env, entry)
    max_steps = int(round(cfg.time_limit_s * TICK_HZ)) + 1
    for _ in range(max_steps):
        actions = tracker.choose(env, a, b)
        _, _, dones, info = env.step(actions)
        tracker.observe(env, dones.copy(), info)
        if not tracker.running.any():
            return tracker.records
    raise RuntimeError(
        f"{int(tracker.running.sum())} matches did not end within {max_steps} steps"
    )


def hull_names_by_id(env: RustVecEnv) -> dict[int, str]:
    """Hull id -> name for every hull present in ``env``'s current matches."""
    names: dict[int, str] = {}
    hull_id = env.hull_id
    for hid in np.unique(hull_id[hull_id >= 0]):
        i, s = (int(x[0]) for x in np.nonzero(hull_id == hid))
        names[int(hid)] = str(env.raw.render_state(i)["ships"][s]["hull"])
    return names


def _span(name: str) -> tuple[int, int]:
    offset, width = OBS_LAYOUT[name]
    return offset, offset + width


def _block(obs: NDArray[np.float32], name: str) -> NDArray[np.float32]:
    lo, hi = _span(name)
    slots = OBS_SLOTS[name]
    return obs[..., lo:hi].reshape(*obs.shape[:-1], slots, (hi - lo) // slots)


class _FleetTracker:
    """Accumulates ``FleetRecords`` step by step for the still-running matches."""

    def __init__(self, env: RustVecEnv, entry: NDArray[np.int64]) -> None:
        n, s = env.n_envs, env.n_ships
        self.radius = env.arena_radius.astype(np.float64).copy()
        self.stuck_ticks = int(round(STUCK_SECONDS * TICK_HZ))
        self.running = np.ones(n, dtype=bool)
        self.in_range = np.zeros((n, s), dtype=bool)
        self.slow_run = np.zeros((n, s), dtype=np.int64)
        team = env.team.astype(np.int64).copy()
        # Alternate a's side inside each roster's block of envs.
        block_start = np.searchsorted(entry, entry, side="left")
        a_team = (np.arange(n) - block_start) % 2
        self.a_rows = team == a_team[:, None]
        self.b_rows = team == (1 - a_team)[:, None]

        def zi() -> NDArray[np.int64]:
            return np.zeros((n, s), dtype=np.int64)

        def zf() -> NDArray[np.float64]:
            return np.zeros((n, s), dtype=np.float64)

        self.records = FleetRecords(
            hull_names=hull_names_by_id(env),
            entry=entry,
            a_team=a_team.astype(np.int64),
            team=team,
            hull=env.hull_id.astype(np.int64).copy(),
            length=np.zeros(n, dtype=np.int64),
            winner=np.full(n, -2, dtype=np.int64),
            timed_out=np.zeros(n, dtype=bool),
            died=np.zeros((n, s), dtype=bool),
            passes=zi(),
            shots=zi(),
            hits=zi(),
            hull_damage=zf(),
            shield_damage=zf(),
            crash_damage=zf(),
            crash_contacts=zi(),
            live_ticks=zi(),
            engaged_ticks=zi(),
            outside_ticks=zi(),
            engine_level=zf(),
            decisions=zi(),
            triggers=zi(),
            nan=np.zeros((n, s), dtype=bool),
            stuck=np.zeros((n, s), dtype=bool),
        )
        self.steps = 0

    def choose(self, env: RustVecEnv, a: Controller, b: Controller) -> NDArray[np.int8]:
        """Assemble this step's actions and count the decisions they make."""
        n, s = env.n_envs, env.n_ships
        decide = self.running[:, None] & env.act_mask
        actions = idle_actions(n * s).reshape(n, s, -1)
        for ctrl, side in ((a, self.a_rows), (b, self.b_rows)):
            rows = decide & side
            if rows.any():
                actions[rows] = ctrl.act(env, rows)
        offset, width = ACTION_LAYOUT["fire"]
        fire = actions[..., offset : offset + width] > 0
        pulled = (fire & env.turret_mask).any(axis=-1)
        self.records.decisions += decide
        self.records.triggers += decide & pulled
        return actions

    def observe(self, env: RustVecEnv, dones: NDArray[np.bool_], info: Any) -> None:
        """Fold one step's events, hits, collisions and post-step obs in."""
        self.steps += 1
        r = self.records
        running = self.running
        events = env.events()
        events = events[running[events[:, F.EV_MATCH].astype(np.int64)]]
        self._count_events(events)
        self._count_hits(info.hits, info.hit_count)
        r.crash_damage += np.where(running[:, None], info.collision_damage, 0.0)

        ending = running & dones
        r.length[ending] = self.steps
        r.winner[ending] = info.winner[ending]
        live_match = running & ~dones
        self._count_obs(env.obs, live_match)
        # A match that ends with ships of both teams alive ended on the time limit.
        alive_end = r.team >= 0
        alive_end = alive_end & ~r.died
        both = ((alive_end & (r.team == 0)).any(1)) & (
            (alive_end & (r.team == 1)).any(1)
        )
        r.timed_out[ending] = both[ending]
        self.running = running & ~dones

    def _count_events(self, events: NDArray[np.float32]) -> None:
        r = self.records
        kind = events[:, F.EV_KIND]
        match = events[:, F.EV_MATCH].astype(np.int64)
        ship_a = events[:, F.EV_A].astype(np.int64)
        shot = (kind == F.KIND_FIRE) | (kind == F.KIND_BEAM)
        np.add.at(r.shots, (match[shot], ship_a[shot]), 1)
        death = kind == F.KIND_DEATH
        r.died[match[death], ship_a[death]] = True
        crash = kind == F.KIND_COLLISION
        ship_b = events[:, F.EV_B].astype(np.int64)
        np.add.at(r.crash_contacts, (match[crash], ship_a[crash]), 1)
        np.add.at(r.crash_contacts, (match[crash], ship_b[crash]), 1)

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
        self, all_obs: NDArray[np.float32], live_match: NDArray[np.bool_]
    ) -> None:
        idx = np.flatnonzero(live_match)
        if idx.size == 0:
            return
        r = self.records
        obs = all_obs[idx]
        radius = self.radius[idx][:, None]
        present = obs[..., F.SELF_PRESENT] > 0.5
        live = present & (r.team[idx] >= 0)
        r.nan[idx] |= np.isnan(obs).any(axis=-1) & (r.team[idx] >= 0)

        ships = _block(obs, "ships")
        enemy = (ships[..., F.SHIP_PRESENT] > 0.5) & (ships[..., F.SHIP_IS_ENEMY] > 0.5)
        enemy_dist = np.where(
            enemy, ships[..., F.SHIP_DIST] * radius[..., None], np.inf
        )
        dist = enemy_dist.min(axis=-1)
        enemy_present = enemy.any(axis=-1)

        turret_present = _block(obs, "turrets")[..., 0] > 0.5
        lo, hi = _span("turret_range")
        ranges = obs[..., lo:hi] * radius[..., None]
        gun_range = np.where(turret_present, ranges, 0.0).max(axis=-1)

        measured = live & enemy_present
        entered, self.in_range[idx] = F.range_entries(
            measured, dist < gun_range, self.in_range[idx]
        )
        r.passes[idx] += entered
        r.engaged_ticks[idx] += measured & (dist < ENGAGEMENT_RANGE_FACTOR * gun_range)
        r.live_ticks[idx] += live
        r.outside_ticks[idx] += live & (obs[..., F.SELF_EDGE_MARGIN] < 0.0)

        thrusters = _block(obs, "thrusters")
        accel = np.where(
            thrusters[..., F.THRUSTER_PRESENT] > 0.5,
            thrusters[..., F.THRUSTER_ACCEL],
            -np.inf,
        )
        main = accel.argmax(axis=-1)[..., None]
        level = np.take_along_axis(thrusters[..., F.THRUSTER_LEVEL], main, axis=-1)
        r.engine_level[idx] += np.where(live, level[..., 0], 0.0)

        speed = obs[..., F.SELF_SPEED] * F.VELOCITY_SCALE
        slow = measured & (speed < STUCK_SPEED)
        self.slow_run[idx] = np.where(slow, self.slow_run[idx] + 1, 0)
        r.stuck[idx] |= self.slow_run[idx] > self.stuck_ticks


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def _ratio(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def ship_metrics(r: FleetRecords, rows: NDArray[np.bool_]) -> ShipMetrics:
    """Per-ship means over the ship-matches selected by ``rows`` ([N, S] bool)."""

    def total(x: NDArray[Any]) -> float:
        return float(np.where(rows, x, 0).sum())

    ships = int(rows.sum())
    live = total(r.live_ticks)
    return ShipMetrics(
        ships=ships,
        damage_dealt=_ratio(total(r.hull_damage), ships),
        shield_damage_dealt=_ratio(total(r.shield_damage), ships),
        survival=_ratio(total(~r.died), ships),
        shots=_ratio(total(r.shots), ships),
        hits=_ratio(total(r.hits), ships),
        hit_rate=_ratio(total(r.hits), total(r.shots)),
        engagement_rate=_ratio(total(r.engaged_ticks), live),
        outside_share=_ratio(total(r.outside_ticks), live),
        engine_duty=_ratio(total(r.engine_level), live),
        passes=_ratio(total(r.passes), ships),
        crash_damage_taken=_ratio(total(r.crash_damage), ships),
        crash_contacts=_ratio(total(r.crash_contacts), ships),
        fire_rate=_ratio(total(r.triggers), total(r.decisions)),
    )


def _side(
    r: FleetRecords,
    side_team: NDArray[np.int64],
    score: NDArray[np.float64],
) -> SideSummary:
    rows = r.team == side_team[:, None]
    hulls: dict[str, ShipMetrics] = {}
    for hid, name in sorted(r.hull_names.items(), key=lambda kv: kv[1]):
        sel = rows & (r.hull == hid)
        if sel.any():
            hulls[name] = ship_metrics(r, sel)
    per_entry = [score[r.entry == k].mean() for k in np.unique(r.entry)]
    return SideSummary(
        win_rate=float(np.mean(per_entry)),
        draws=int((r.winner == -1).sum()),
        all_ships=ship_metrics(r, rows),
        hulls=hulls,
        nan_matches=int((r.nan & rows).any(axis=1).sum()),
        stuck_matches=int((r.stuck & rows).any(axis=1).sum()),
    )


def summarise(
    r: FleetRecords,
    cfg: FleetEvalConfig,
    a_label: str,
    b_label: str,
) -> FleetResult:
    """Reduce ``r`` to a ``FleetResult``."""
    entries = cfg.entries()
    a_won = r.winner == r.a_team
    draw = r.winner == -1
    a_score = a_won + 0.5 * draw
    b_score = (~a_won & ~draw) + 0.5 * draw
    team0_score = (r.winner == 0) + 0.5 * draw
    rosters: list[RosterOutcome] = []
    for k, e in enumerate(entries):
        sel = r.entry == k
        n = int(sel.sum())
        wins, draws = int(a_won[sel].sum()), int(draw[sel].sum())
        rosters.append(
            RosterOutcome(
                name=e.name,
                klass=e.klass,
                label=e.roster.label,
                n=n,
                wins=wins,
                draws=draws,
                losses=n - wins - draws,
                win_rate=float(a_score[sel].mean()),
                team0_win_rate=float(team0_score[sel].mean()),
                draw_rate=float(draw[sel].mean()),
                time_limit_rate=float(r.timed_out[sel].mean()),
                length_median=float(np.median(r.length[sel])),
            )
        )
    classes: dict[str, ClassOutcome] = {}
    for klass in dict.fromkeys(e.klass for e in entries):
        members = [x for x in rosters if x.klass == klass]
        sel = np.isin(r.entry, [k for k, e in enumerate(entries) if e.klass == klass])
        classes[klass] = ClassOutcome(
            klass=klass,
            rosters=len(members),
            n=int(sel.sum()),
            win_rate=float(np.mean([x.win_rate for x in members])),
            draw_rate=float(draw[sel].mean()),
            time_limit_rate=float(r.timed_out[sel].mean()),
            length_median=float(np.median(r.length[sel])),
        )
    q10, q50, q90 = np.percentile(r.length, [10, 50, 90])
    return FleetResult(
        a=a_label,
        b=b_label,
        config=cfg,
        match=MatchSummary(
            n=int(r.length.size),
            length_median=float(q50),
            length_p10=float(q10),
            length_p90=float(q90),
            draw_rate=float(draw.mean()),
            time_limit_rate=float(r.timed_out.mean()),
        ),
        classes=classes,
        rosters=rosters,
        side_a=_side(r, r.a_team, a_score),
        side_b=_side(r, 1 - r.a_team, b_score),
    )


def evaluate(
    a: Controller,
    b: Controller,
    cfg: FleetEvalConfig | None = None,
    n_threads: int = 12,
    assets_dir: Path = ASSETS,
) -> FleetResult:
    """Play ``cfg``'s suite of ``a`` against ``b`` and summarise it."""
    cfg = cfg or FleetEvalConfig()
    records = run_matches(a, b, cfg, n_threads=n_threads, assets_dir=assets_dir)
    return summarise(records, cfg, a.label, b.label)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--a", default="script", help="script, random or a checkpoint")
    p.add_argument("--b", default="script", help="script, random or a checkpoint")
    p.add_argument("--suite", default="fleet_v1", choices=sorted(SUITES))
    p.add_argument("--n-per-roster", type=int, default=DEFAULT_N_PER_ROSTER)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="base env seed")
    p.add_argument("--n-threads", type=int, default=12)
    p.add_argument("--reaction-ticks", type=int, default=2)
    p.add_argument(
        "--arena-radius",
        type=float,
        default=0.0,
        help="one arena radius (m) for every roster; 0 = the shared rule",
    )
    p.add_argument("--argmax", action="store_true", help="policies take the argmax")
    p.add_argument("--out", type=Path, help="write the FleetResult JSON here")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: run one evaluation, print Markdown, write JSON."""
    args = parse_args(argv)
    sample = not args.argmax
    cfg = FleetEvalConfig(
        suite=args.suite,
        n_per_roster=args.n_per_roster,
        seed=args.seed,
        reaction_ticks=args.reaction_ticks,
        arena_radius=args.arena_radius,
    )
    result = evaluate(
        make_controller(args.a, sample=sample, seed=0),
        make_controller(args.b, sample=sample, seed=1),
        cfg,
        n_threads=args.n_threads,
    )
    print(result.markdown())
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result.to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
