"""Mission eval: two pilots fly the strike craft of carrier battles and convoys.

``evaluate(a, b, cfg)`` plays every mission of ``cfg`` with the sim's live default
rosters (``rlf_sim.mission_rosters``, the ones the live page drafts), the commander
mode of ``cfg`` on both teams, the capital ships (carriers, freighters) flown by the
sim's scripts, and ``a`` / ``b`` flying every strike craft of their side. Env ``i``
of a mission plays roster ``i % R`` with ``a`` on team ``(i // R) % 2``, so with
``n_per_mission`` a multiple of ``2 R`` every roster is played equally often from
each side (a convoy's defenders are team 0). Every env is read until its first
``done``. Stage B's gate "mission win rate against v1 pilots under the same
commander" is ``evaluate(candidate, v1)`` (``lab/runs/2026-10-31-order-pilot``).

    python -m spacefight.eval.missions --a ckpt.pt --b v1.pt --out missions.json
    python -m spacefight.eval.missions --a script --b script   # baseline

Metrics (JSON schema ``rlf.eval.mission/1``), per mission and overall:

- *win rate* of ``a`` (wins + ½ draws), overall and per side (team 0 / team 1:
  defenders / attackers in a convoy), and per roster;
- *end reasons* (shares of ``rlf_sim.END_REASONS``), *time-limit rate*, *stalemate
  rate* (a time-limit ending with no hull or shield damage landed by anyone in the
  last ``STALEMATE_S`` seconds), *draw rate*, length median and p90 (seconds);
- per side over its strike craft, the fleet eval's per-ship metrics
  (``fleet.ShipMetrics``: damage, survival, hit rate, engagement, outside share,
  engine duty, passes, crashes, fire rate), per hull and pooled; NaN and stuck
  matches.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Self

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.rosters import (
    CARRIER_BATTLE,
    CONVOY_ESCORT,
    SCRIPTED,
    Roster,
    capital_hull_ids,
)
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval.controllers import Controller, make_controller
from spacefight.eval.fleet import (
    ShipMetrics,
    _FleetTracker,
    ship_metrics,
)

ASSETS = Path(__file__).resolve().parents[2] / "assets"
SCHEMA = "rlf.eval.mission/1"
TICK_HZ = 30
STALEMATE_S = 30.0
DEFAULT_SEED = 300_000
DEFAULT_MISSIONS: tuple[str, ...] = (CARRIER_BATTLE, CONVOY_ESCORT)
END_REASONS: tuple[str, ...] = tuple(rlf_sim.END_REASONS)
TIME_LIMIT_CODE = END_REASONS.index("time_limit")


def default_rosters(mission: str) -> list[tuple[str, Roster]]:
    """``(name, roster)`` of the sim's live default rosters of ``mission``."""
    return [
        (
            str(r["name"]),
            Roster.of(r["fleets"][0], r["fleets"][1], mission=str(r["mission"])),
        )
        for r in rlf_sim.mission_rosters(mission)
    ]


@dataclass(frozen=True)
class MissionEvalConfig:
    """The scenario of one mission evaluation."""

    missions: tuple[str, ...] = DEFAULT_MISSIONS
    n_per_mission: int = 516
    seed: int = DEFAULT_SEED
    commanders: str = SCRIPTED
    reaction_ticks: int = 2
    sim_version: int = int(rlf_sim.SIM_VERSION)


@dataclass
class MissionEnv:
    """One mission's env and who flies what in it.

    Attributes:
        env: The env (``n`` matches, the default rosters, the mission's clock).
        names: Roster names; ``entry[i]`` indexes them.
        entry: [N] roster of each env.
        a_team: [N] side ``a``'s team.
        capital: [N, S] slots the capital-ship scripts fly.
        time_limit_s: The mission's clock.
    """

    env: RustVecEnv
    names: list[str]
    entry: NDArray[np.int64]
    a_team: NDArray[np.int64]
    capital: NDArray[np.bool_]
    time_limit_s: float


def build_mission_env(
    mission: str,
    n: int,
    seed: int,
    commanders: str,
    n_threads: int,
    reaction_ticks: int = 2,
    assets_dir: Path = ASSETS,
) -> MissionEnv:
    """The env of one mission (module docstring for the layout).

    Raises:
        ValueError: ``n`` is not a positive multiple of twice the roster count.
    """
    rosters = default_rosters(mission)
    block = 2 * len(rosters)
    if n < block or n % block:
        raise ValueError(f"n must be a positive multiple of {block} for {mission}")
    idx = np.arange(n, dtype=np.int64)
    entry = idx % len(rosters)
    a_team = (idx // len(rosters)) % 2
    first = rosters[0][1]
    time_limit_s = float(rlf_sim.mission_time_limit_s(mission))
    modes = (commanders, commanders)
    env = RustVecEnv(
        assets_dir,
        n,
        first.fleets(),
        seed,
        time_limit_s=time_limit_s,
        n_threads=n_threads,
        record_events=True,
        reaction_ticks=reaction_ticks,
        max_ships=max(r.n_ships for _, r in rosters),
        commanders=modes,
    )
    for i, k in enumerate(entry):
        roster = rosters[int(k)][1]
        env.set_next_roster(i, Roster(roster.teams, mission, modes))
    env.reset()
    capital = np.isin(env.hull_id, capital_hull_ids(assets_dir))
    return MissionEnv(
        env=env,
        names=[name for name, _ in rosters],
        entry=entry,
        a_team=a_team,
        capital=capital,
        time_limit_s=time_limit_s,
    )


@dataclass(frozen=True)
class SideMetrics:
    """One side's strike craft in one mission."""

    win_rate: float
    all_ships: ShipMetrics
    hulls: dict[str, ShipMetrics]
    nan_matches: int
    stuck_matches: int


@dataclass(frozen=True)
class MissionSummary:
    """One mission (``a``'s view)."""

    mission: str
    n: int
    time_limit_s: float
    win_rate: float
    win_rate_team0: float  # a as team 0 (a convoy's defenders)
    win_rate_team1: float
    win_rate_by_roster: dict[str, float]
    draw_rate: float
    time_limit_rate: float
    stalemate_rate: float
    end_reasons: dict[str, float]
    length_median_s: float
    length_p90_s: float
    side_a: SideMetrics
    side_b: SideMetrics


@dataclass(frozen=True)
class MissionResult:
    """Outcome of ``evaluate``; JSON schema ``SCHEMA``."""

    a: str
    b: str
    config: MissionEvalConfig
    missions: dict[str, MissionSummary]
    win_rate_mean: float  # missions weigh the same
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return asdict(self)

    def to_json(self) -> str:
        """Indented JSON text."""
        return json.dumps(self.to_dict(), indent=1)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Rebuild from ``to_dict`` output.

        Raises:
            ValueError: Wrong schema.
            KeyError / TypeError: Missing or unknown keys.
        """
        if data.get("schema") != SCHEMA:
            raise ValueError(f"expected schema {SCHEMA!r}, got {data.get('schema')!r}")

        def side(raw: dict[str, Any]) -> SideMetrics:
            return SideMetrics(
                win_rate=raw["win_rate"],
                all_ships=ShipMetrics(**raw["all_ships"]),
                hulls={h: ShipMetrics(**m) for h, m in raw["hulls"].items()},
                nan_matches=raw["nan_matches"],
                stuck_matches=raw["stuck_matches"],
            )

        missions = {}
        for name, raw in data["missions"].items():
            fields_ = {k: v for k, v in raw.items() if k not in ("side_a", "side_b")}
            missions[name] = MissionSummary(
                **fields_, side_a=side(raw["side_a"]), side_b=side(raw["side_b"])
            )
        config = dict(data["config"])
        config["missions"] = tuple(config["missions"])
        return cls(
            a=data["a"],
            b=data["b"],
            config=MissionEvalConfig(**config),
            missions=missions,
            win_rate_mean=data["win_rate_mean"],
        )

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Parse ``to_json`` output."""
        return cls.from_dict(json.loads(text))

    def markdown(self) -> str:
        """Mission table and per-hull table, Markdown."""
        lines = [
            f"**{self.a}** vs **{self.b}** ({self.config.commanders} commanders): "
            f"mean win {self.win_rate_mean:.3f}",
            "",
            "| mission | n | win | as team 0 | as team 1 | draw | time limit "
            "| stalemate | median s | p90 s | end reasons |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for m in self.missions.values():
            reasons = ", ".join(f"{k} {v:.2f}" for k, v in m.end_reasons.items())
            lines.append(
                f"| {m.mission} | {m.n} | {m.win_rate:.3f} | {m.win_rate_team0:.3f} "
                f"| {m.win_rate_team1:.3f} | {m.draw_rate:.3f} | "
                f"{m.time_limit_rate:.3f} | {m.stalemate_rate:.3f} | "
                f"{m.length_median_s:.0f} | {m.length_p90_s:.0f} | {reasons} |"
            )
        lines += [
            "",
            "| mission | side | hull | ships | dmg | shield dmg | survival | hit rate "
            "| engage | outside | engine | passes | fire |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for m in self.missions.values():
            for label, side in (("a", m.side_a), ("b", m.side_b)):
                for hull, s in [*side.hulls.items(), ("all", side.all_ships)]:
                    lines.append(
                        f"| {m.mission} | {label} | {hull} | {s.ships} | "
                        f"{s.damage_dealt:.1f} | {s.shield_damage_dealt:.1f} | "
                        f"{s.survival:.2f} | {s.hit_rate:.3f} | "
                        f"{s.engagement_rate:.2f} | {s.outside_share:.4f} | "
                        f"{s.engine_duty:.2f} | {s.passes:.2f} | {s.fire_rate:.3f} |"
                    )
        return "\n".join(lines)


@dataclass
class _MissionRecords:
    """Per-env match outcomes that ``_FleetTracker`` does not keep."""

    end_reason: NDArray[np.int64]
    last_damage_step: NDArray[np.int64]
    stalemate: NDArray[np.bool_] = field(init=False)

    def __post_init__(self) -> None:
        self.stalemate = np.zeros(self.end_reason.shape, dtype=bool)


def run_mission(
    a: Controller,
    b: Controller,
    mission: str,
    cfg: MissionEvalConfig,
    n_threads: int,
    assets_dir: Path = ASSETS,
) -> MissionSummary:
    """Play one mission's matches and summarise them.

    Raises:
        RuntimeError: A match did not end within its clock.
    """
    k = cfg.missions.index(mission)
    me = build_mission_env(
        mission,
        cfg.n_per_mission,
        cfg.seed + 100_003 * k,
        cfg.commanders,
        n_threads,
        cfg.reaction_ticks,
        assets_dir,
    )
    env = me.env
    tracker = _FleetTracker(env, me.entry, a_team=me.a_team, scripted=me.capital)
    n = env.n_envs
    rec = _MissionRecords(
        end_reason=np.zeros(n, dtype=np.int64),
        last_damage_step=np.zeros(n, dtype=np.int64),
    )
    stale_steps = int(round(STALEMATE_S * TICK_HZ))
    max_steps = int(round(me.time_limit_s * TICK_HZ)) + 2
    for step in range(1, max_steps + 1):
        running = tracker.running.copy()
        actions = tracker.choose(env, a, b)
        _, _, dones, info = env.step(actions)
        rec.last_damage_step[running & (info.hit_count > 0)] = step
        ending = running & dones
        rec.end_reason[ending] = env.end_reason[ending]
        tracker.observe(env, dones.copy(), info)
        if not tracker.running.any():
            break
    else:
        raise RuntimeError(
            f"{mission}: {int(tracker.running.sum())} matches did not end in time"
        )
    r = tracker.records
    timed_out = rec.end_reason == TIME_LIMIT_CODE
    rec.stalemate = timed_out & (r.length - rec.last_damage_step >= stale_steps)
    return _summarise(mission, me, r, rec, timed_out)


def _side_metrics(
    r: Any, rows: NDArray[np.bool_], score: NDArray[np.float64]
) -> SideMetrics:
    hulls: dict[str, ShipMetrics] = {}
    for hid, name in sorted(r.hull_names.items(), key=lambda kv: kv[1]):
        sel = rows & (r.hull == hid)
        if sel.any():
            hulls[name] = ship_metrics(r, sel)
    return SideMetrics(
        win_rate=float(score.mean()),
        all_ships=ship_metrics(r, rows),
        hulls=hulls,
        nan_matches=int((r.nan & rows).any(axis=1).sum()),
        stuck_matches=int((r.stuck & rows).any(axis=1).sum()),
    )


def _summarise(
    mission: str,
    me: MissionEnv,
    r: Any,
    rec: _MissionRecords,
    timed_out: NDArray[np.bool_],
) -> MissionSummary:
    a_won = r.winner == me.a_team
    draw = r.winner == -1
    a_score = a_won + 0.5 * draw
    b_score = (~a_won & ~draw) + 0.5 * draw
    strike = (r.team >= 0) & ~me.capital
    a_rows = strike & (r.team == me.a_team[:, None])
    b_rows = strike & (r.team == (1 - me.a_team)[:, None])
    lengths = r.length / TICK_HZ
    reasons = {
        name: float(np.mean(rec.end_reason == code))
        for code, name in enumerate(END_REASONS)
        if code > 0 and (rec.end_reason == code).any()
    }
    return MissionSummary(
        mission=mission,
        n=int(r.length.size),
        time_limit_s=me.time_limit_s,
        win_rate=float(a_score.mean()),
        win_rate_team0=float(a_score[me.a_team == 0].mean()),
        win_rate_team1=float(a_score[me.a_team == 1].mean()),
        win_rate_by_roster={
            name: float(a_score[me.entry == k].mean())
            for k, name in enumerate(me.names)
        },
        draw_rate=float(draw.mean()),
        time_limit_rate=float(timed_out.mean()),
        stalemate_rate=float(rec.stalemate.mean()),
        end_reasons=reasons,
        length_median_s=float(np.median(lengths)),
        length_p90_s=float(np.percentile(lengths, 90)),
        side_a=_side_metrics(r, a_rows, a_score),
        side_b=_side_metrics(r, b_rows, b_score),
    )


def evaluate(
    a: Controller,
    b: Controller,
    cfg: MissionEvalConfig | None = None,
    n_threads: int = 12,
    assets_dir: Path = ASSETS,
) -> MissionResult:
    """Play every mission of ``cfg`` with ``a`` against ``b``."""
    cfg = cfg or MissionEvalConfig()
    a.reset(cfg.seed)
    b.reset(cfg.seed + 1)
    missions = {
        m: run_mission(a, b, m, cfg, n_threads, assets_dir) for m in cfg.missions
    }
    return MissionResult(
        a=a.label,
        b=b.label,
        config=cfg,
        missions=missions,
        win_rate_mean=float(np.mean([m.win_rate for m in missions.values()])),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: run one evaluation, print Markdown, write JSON."""
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--a", default="script", help="script, a checkpoint, blank:<ckpt>")
    p.add_argument("--b", default="script")
    p.add_argument("--missions", nargs="+", default=list(DEFAULT_MISSIONS))
    p.add_argument("--n-per-mission", type=int, default=516)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--commanders", default=SCRIPTED, help="scripted or random")
    p.add_argument("--n-threads", type=int, default=12)
    p.add_argument("--argmax", action="store_true")
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    cfg = MissionEvalConfig(
        missions=tuple(args.missions),
        n_per_mission=args.n_per_mission,
        seed=args.seed,
        commanders=args.commanders,
    )
    sample = not args.argmax
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
