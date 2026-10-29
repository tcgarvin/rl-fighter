"""Duel balance sweep: scripted fighter vs scripted fighter (spike plan §2.3, SIM_SPEC WP15).

Runs N one-episode 1v1 fighter duels in one ``rlf_sim.VecEnv`` per cell (both sides
driven by ``scripted_actions()``), for every combination of reaction delay and
balance tuple asked for, and prints one table row per cell with the plan's gate
columns. Balance tuples are applied to a temporary copy of ``assets/`` (YAML patched
there), so the sweep never edits the real asset files.

    uv run maturin develop -m crates/sim-py/Cargo.toml --release
    uv run python tools/duel_sweep.py --n 200 --reaction-ticks 2
    uv run python tools/duel_sweep.py --n 200 --reaction-ticks 0 2 4 --damage 3 4 --range 220 260

Exit status is 1 if any cell whose reaction delay is in ``--gate-reaction-ticks``
(default: 2, the production default) fails a gate, else 0.

Definitions (per match, measured until its first ``done``):

- *length*: ticks until the match ended (the arrival phase included).
- *mutual kill*: both ships died on the same tick (winner -1 by kill); *time limit*:
  the match hit ``time_limit_s`` with no death on the final step.
- *pass*: an entry into gun range, i.e. a transition of the ship–ship distance from
  ``>= range`` to ``< range`` (plan §2.3); a duel that starts inside range counts
  that as one. *Closest approaches* (reported, not gated) are local distance minima
  under gun range followed by a rise of at least ``APPROACH_PROMINENCE`` metres.
- *damage per pass*: hull damage a ship took, as a share of its hp, divided by the
  match's passes; the mean of the two ships.
"""

from __future__ import annotations

import argparse
import itertools
import json
import shutil
import sys
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import numpy as np
import rlf_sim
import yaml
from numpy.typing import NDArray

ASSETS = Path(__file__).resolve().parent.parent / "assets"

FLEETS = [["fighter"], ["fighter"]]
TICK_HZ = 30

# Obs features read by the sweep (SIM_SPEC §7.2): self block feature 19 is
# (R - |pos|)/R, ships block slot 0 is the nearest other ship (present, ..., dist/R).
_SELF_OFFSET = rlf_sim.OBS_LAYOUT["self"][0]
_SHIPS_OFFSET, _SHIPS_WIDTH = rlf_sim.OBS_LAYOUT["ships"]
_SHIP_RECORD = _SHIPS_WIDTH // rlf_sim.OBS_SLOTS["ships"]
_SELF_PRESENT = _SELF_OFFSET + 0
_SELF_EDGE_MARGIN = _SELF_OFFSET + 19
_NEAREST_PRESENT = _SHIPS_OFFSET + 0
_NEAREST_DIST = _SHIPS_OFFSET + 11

# Flat event columns from VecEnv.events(): [match, kind, a, b, x, y, s5, s6, extra].
_EV_MATCH, _EV_KIND, _EV_A, _EV_SLOT5, _EV_EXTRA = 0, 1, 2, 6, 8
_KIND_FIRE, _KIND_HIT, _KIND_DEATH = 0, 2, 5

# A closest approach must be followed by this much opening (m) to count.
APPROACH_PROMINENCE = 20.0


@dataclass(frozen=True)
class Balance:
    """The duel balance knobs: gauss weapon numbers and fighter hull hp."""

    damage: float = 3.0
    interval: float = 0.20
    range: float = 220.0
    speed: float = 200.0
    spread_deg: float = 1.0
    hp: float = 80.0
    armour: bool = True

    def label(self) -> str:
        armour = "" if self.armour else " no-armour"
        return (
            f"dmg {self.damage:g} / {self.interval:g} s / {self.range:g} m / "
            f"{self.speed:g} m/s / {self.spread_deg:g}° / hp {self.hp:g}{armour}"
        )


@dataclass(frozen=True)
class SweepConfig:
    """Everything except the balance tuple that defines one cell's runs."""

    n: int = 200
    seed: int = 0
    reaction_ticks: int = 2
    arena_radius: float = 450.0
    time_limit_s: float = 90.0
    n_threads: int = 12


@dataclass(frozen=True)
class Gates:
    """Plan §2.3 acceptance gates."""

    median_length: tuple[int, int] = (450, 1500)
    max_draw_rate: float = 0.10
    max_time_limit_rate: float = 0.10
    min_median_passes: float = 3.0
    damage_per_pass: tuple[float, float] = (0.10, 0.40)


@dataclass
class DuelRecords:
    """Raw per-match measurements of one cell (arrays of length N)."""

    length: NDArray[np.int64]
    winner: NDArray[np.int64]
    killed: NDArray[np.bool_]
    passes: NDArray[np.int64]
    approaches: NDArray[np.int64]
    shots: NDArray[np.int64]
    hits: NDArray[np.int64]
    hull_damage: NDArray[np.float64]  # [N, 2] hull damage taken per ship
    outside_ticks: NDArray[np.int64]  # ship-ticks outside the arena
    live_ticks: NDArray[np.int64]  # ship-ticks present
    mult_counts: dict[float, int] = field(default_factory=dict)


@dataclass(frozen=True)
class CellSummary:
    """One table row."""

    balance: Balance
    reaction_ticks: int
    n: int
    median_length: float
    p10_length: float
    p90_length: float
    q25_length: float
    q75_length: float
    draw_rate: float
    time_limit_rate: float
    team0_win_share: float
    median_passes: float
    median_approaches: float
    hits_per_pass: float
    damage_per_pass: float
    shots_per_match: float
    hit_rate: float
    outside_share: float
    mult_mix: dict[str, float]
    failures: tuple[str, ...]


@contextmanager
def patched_assets(balance: Balance, src: Path = ASSETS) -> Iterator[Path]:
    """Yield a temporary copy of ``src`` with ``balance`` written into its YAML.

    Patches ``weapons.yaml`` (gauss) and ``hulls/fighter/hull.yaml`` (hp, and
    ``armour`` removed when ``balance.armour`` is false). The copy is deleted on exit.
    """
    with tempfile.TemporaryDirectory(prefix="duel_sweep_") as tmp:
        dst = Path(tmp) / "assets"
        shutil.copytree(src, dst)
        weapons_path = dst / "weapons.yaml"
        weapons = yaml.safe_load(weapons_path.read_text())
        weapons["gauss"].update(
            damage=balance.damage,
            interval=balance.interval,
            range=balance.range,
            speed=balance.speed,
            spread_deg=balance.spread_deg,
        )
        weapons_path.write_text(yaml.safe_dump(weapons, sort_keys=False))
        hull_path = dst / "hulls" / "fighter" / "hull.yaml"
        hull = yaml.safe_load(hull_path.read_text())
        hull["hp"] = balance.hp
        if not balance.armour:
            hull.pop("armour", None)
        hull_path.write_text(yaml.safe_dump(hull, sort_keys=False))
        yield dst


def run_duels(assets_dir: Path, cfg: SweepConfig, gun_range: float) -> DuelRecords:
    """Run ``cfg.n`` scripted 1v1 fighter duels to their first end; measure each."""
    env = rlf_sim.VecEnv(
        str(assets_dir),
        cfg.n,
        FLEETS,
        cfg.seed,
        arena_radius=cfg.arena_radius,
        time_limit_s=cfg.time_limit_s,
        n_threads=cfg.n_threads,
        record_events=True,
        reaction_ticks=cfg.reaction_ticks,
    )
    env.reset()
    n = cfg.n
    max_steps = int(round(cfg.time_limit_s * TICK_HZ)) + 1
    radius = cfg.arena_radius

    running = np.ones(n, dtype=bool)
    length = np.zeros(n, dtype=np.int64)
    winner = np.full(n, -2, dtype=np.int64)
    killed = np.zeros(n, dtype=bool)
    passes = np.zeros(n, dtype=np.int64)
    approaches = np.zeros(n, dtype=np.int64)
    shots = np.zeros(n, dtype=np.int64)
    hits = np.zeros(n, dtype=np.int64)
    hull_damage = np.zeros((n, 2), dtype=np.float64)
    outside_ticks = np.zeros(n, dtype=np.int64)
    live_ticks = np.zeros(n, dtype=np.int64)
    mult_counts: dict[float, int] = {}

    in_range = np.zeros(n, dtype=bool)
    run_min = np.full(n, np.inf)

    for step in range(1, max_steps + 1):
        env.scripted_actions()
        env.step()
        events = env.events()
        dones = env.dones.copy()
        ending = running & dones
        _count_events(events, running, shots, hits, hull_damage, mult_counts)
        deaths = events[events[:, _EV_KIND] == _KIND_DEATH]
        died = np.zeros(n, dtype=bool)
        died[deaths[:, _EV_MATCH].astype(np.int64)] = True

        length[ending] = step
        winner[ending] = env.winner[ending]
        killed[ending] = died[ending]

        # Geometry from the post-step obs, only for matches still mid-episode (a
        # finished match's obs already belong to its reset successor).
        live = running & ~dones
        obs = env.obs
        both_present = (obs[:, 0, _SELF_PRESENT] > 0.5) & (
            obs[:, 0, _NEAREST_PRESENT] > 0.5
        )
        measured = live & both_present
        dist = obs[:, 0, _NEAREST_DIST] * radius
        now_in = dist < gun_range
        passes += measured & now_in & ~in_range
        in_range = np.where(measured, now_in, in_range)

        run_min = np.where(measured, np.minimum(run_min, dist), run_min)
        turned = (
            measured & (run_min < gun_range) & (dist > run_min + APPROACH_PROMINENCE)
        )
        approaches += turned
        run_min = np.where(turned, dist, run_min)

        present = obs[:, :, _SELF_PRESENT] > 0.5
        outside = present & (obs[:, :, _SELF_EDGE_MARGIN] < 0.0)
        live_ticks += np.where(live, present.sum(axis=1), 0)
        outside_ticks += np.where(live, outside.sum(axis=1), 0)

        running &= ~dones
        if not running.any():
            break
    if running.any():
        raise RuntimeError(
            f"{int(running.sum())} matches did not end within {max_steps} steps"
        )
    return DuelRecords(
        length=length,
        winner=winner,
        killed=killed,
        passes=passes,
        approaches=approaches,
        shots=shots,
        hits=hits,
        hull_damage=hull_damage,
        outside_ticks=outside_ticks,
        live_ticks=live_ticks,
        mult_counts=mult_counts,
    )


def _count_events(
    events: NDArray[np.float32],
    running: NDArray[np.bool_],
    shots: NDArray[np.int64],
    hits: NDArray[np.int64],
    hull_damage: NDArray[np.float64],
    mult_counts: dict[float, int],
) -> None:
    """Accumulate this step's Fire/Hit events of still-running matches (in place)."""
    if events.shape[0] == 0:
        return
    match = events[:, _EV_MATCH].astype(np.int64)
    keep = running[match]
    events, match = events[keep], match[keep]
    kind = events[:, _EV_KIND]
    np.add.at(shots, match[kind == _KIND_FIRE], 1)
    hit_rows = kind == _KIND_HIT
    hit_match = match[hit_rows]
    np.add.at(hits, hit_match, 1)
    target = events[hit_rows, _EV_A].astype(np.int64)
    np.add.at(hull_damage, (hit_match, target), events[hit_rows, _EV_EXTRA])
    for mult in np.round(events[hit_rows, _EV_SLOT5], 3):
        mult_counts[float(mult)] = mult_counts.get(float(mult), 0) + 1


def summarise(
    records: DuelRecords, balance: Balance, cfg: SweepConfig, gates: Gates
) -> CellSummary:
    """Reduce one cell's records to its table row and gate failures."""
    n = records.length.shape[0]
    time_limited = ~records.killed
    draws = records.killed & (records.winner == -1)
    decided = records.killed & (records.winner >= 0)
    passes = np.maximum(records.passes, 1)
    dmg_share = records.hull_damage / balance.hp
    dmg_per_pass = dmg_share.mean(axis=1) / passes
    total_hits = int(records.hits.sum())
    mult_total = max(sum(records.mult_counts.values()), 1)
    q = np.percentile(records.length, [10, 25, 50, 75, 90])
    summary = CellSummary(
        balance=balance,
        reaction_ticks=cfg.reaction_ticks,
        n=n,
        median_length=float(q[2]),
        p10_length=float(q[0]),
        p90_length=float(q[4]),
        q25_length=float(q[1]),
        q75_length=float(q[3]),
        draw_rate=float(draws.mean()),
        time_limit_rate=float(time_limited.mean()),
        team0_win_share=(
            float((records.winner[decided] == 0).mean()) if decided.any() else 0.0
        ),
        median_passes=float(np.median(records.passes)),
        median_approaches=float(np.median(records.approaches)),
        hits_per_pass=float(np.median(records.hits / passes)),
        damage_per_pass=float(np.median(dmg_per_pass)),
        shots_per_match=float(records.shots.mean()),
        hit_rate=total_hits / max(int(records.shots.sum()), 1),
        outside_share=float(records.outside_ticks.sum())
        / max(int(records.live_ticks.sum()), 1),
        mult_mix={
            f"{m:g}": c / mult_total for m, c in sorted(records.mult_counts.items())
        },
        failures=(),
    )
    return replace(summary, failures=gate_failures(summary, gates))


def gate_failures(s: CellSummary, gates: Gates) -> tuple[str, ...]:
    """Names of the plan §2.3 gates ``s`` fails (empty when all pass)."""
    out = []
    lo, hi = gates.median_length
    if not lo <= s.median_length <= hi:
        out.append("length")
    if s.draw_rate >= gates.max_draw_rate:
        out.append("draws")
    if s.time_limit_rate >= gates.max_time_limit_rate:
        out.append("time-limit")
    if s.median_passes < gates.min_median_passes:
        out.append("passes")
    lo_d, hi_d = gates.damage_per_pass
    if not lo_d <= s.damage_per_pass <= hi_d:
        out.append("dmg/pass")
    return tuple(out)


def run_cell(
    balance: Balance, cfg: SweepConfig, gates: Gates, src: Path = ASSETS
) -> CellSummary:
    """Patch the assets with ``balance``, run the duels and summarise them."""
    with patched_assets(balance, src) as assets_dir:
        records = run_duels(assets_dir, cfg, balance.range)
    return summarise(records, balance, cfg, gates)


TABLE_HEADER = (
    "| tuple | d | median (p25–p75) | p10–p90 | mutual kill | time limit | team-0 wins "
    "| passes | approaches | hits/pass | dmg/pass | shots | hit rate | outside "
    "| mult 0.5/1/1.5 | gate |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
)


def table_row(s: CellSummary) -> str:
    mix = "/".join(f"{s.mult_mix.get(k, 0.0):.2f}" for k in ("0.5", "1", "1.5"))
    gate = "pass" if not s.failures else "FAIL " + ",".join(s.failures)
    return (
        f"| {s.balance.label()} | {s.reaction_ticks} | {s.median_length:.0f} "
        f"({s.q25_length:.0f}–{s.q75_length:.0f}) | {s.p10_length:.0f}–{s.p90_length:.0f} "
        f"| {s.draw_rate:.1%} | {s.time_limit_rate:.1%} | {s.team0_win_share:.2f} "
        f"| {s.median_passes:g} | {s.median_approaches:g} | {s.hits_per_pass:.1f} "
        f"| {s.damage_per_pass:.0%} | {s.shots_per_match:.0f} | {s.hit_rate:.2f} "
        f"| {s.outside_share:.3f} | {mix} | {gate} |"
    )


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    d = Balance()
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--n", type=int, default=200, help="duels (seeds) per cell")
    p.add_argument("--seed", type=int, default=0, help="VecEnv base seed")
    p.add_argument("--reaction-ticks", type=int, nargs="+", default=[2])
    p.add_argument("--gate-reaction-ticks", type=int, nargs="*", default=[2])
    p.add_argument("--arena-radius", type=float, default=450.0)
    p.add_argument("--time-limit-s", type=float, default=90.0)
    p.add_argument("--n-threads", type=int, default=12)
    p.add_argument("--damage", type=float, nargs="+", default=[d.damage])
    p.add_argument("--interval", type=float, nargs="+", default=[d.interval])
    p.add_argument("--range", type=float, nargs="+", default=[d.range])
    p.add_argument("--speed", type=float, nargs="+", default=[d.speed])
    p.add_argument("--spread-deg", type=float, nargs="+", default=[d.spread_deg])
    p.add_argument("--hp", type=float, nargs="+", default=[d.hp])
    p.add_argument(
        "--no-armour", action="store_true", help="strip the fighter's armour"
    )
    p.add_argument("--json", type=Path, help="also write every cell's summary here")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    gates = Gates()
    balances = [
        Balance(dmg, iv, rng, spd, spr, hp, armour=not args.no_armour)
        for dmg, iv, rng, spd, spr, hp in itertools.product(
            args.damage, args.interval, args.range, args.speed, args.spread_deg, args.hp
        )
    ]
    print(TABLE_HEADER, flush=True)
    summaries = []
    for balance in balances:
        for d in args.reaction_ticks:
            cfg = SweepConfig(
                n=args.n,
                seed=args.seed,
                reaction_ticks=d,
                arena_radius=args.arena_radius,
                time_limit_s=args.time_limit_s,
                n_threads=args.n_threads,
            )
            s = run_cell(balance, cfg, gates)
            summaries.append(s)
            print(table_row(s), flush=True)
    if args.json is not None:
        args.json.write_text(json.dumps([asdict(s) for s in summaries], indent=1))
    gated = [s for s in summaries if s.reaction_ticks in args.gate_reaction_ticks]
    return 1 if any(s.failures for s in gated) else 0


if __name__ == "__main__":
    sys.exit(main())
