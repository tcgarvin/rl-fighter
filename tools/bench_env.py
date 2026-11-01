"""Throughput benchmark for the Rust batched env (docs/SIM_SPEC.md §13).

Random valid actions, obs on, events off, N = 256 matches, 100 warm-up steps then
2000 timed steps. One step = all N matches advance one tick. Random actions are
drawn with numpy into a bank before timing and copied into `env.actions` each step,
so the timed loop measures the env plus the per-step Python call and copy, not the
random number generator.

SIM_VERSION 5 adds the stage B training shapes (M3 plan, "Stage B decisions"): carrier
battle and convoy escort rosters padded to ``MAX_TRAIN_SHIPS`` = 12 slots, one team
under the random commander and one under the script, and a 4v4 deathmatch padded to
12. They also call ``scripted_actions()`` every step before the random actions go in,
as the trainer does for its script labels, so their steps/s is the sim side of a
stage B rollout step.

``pilots_v1 @20 +labels`` plays the live-roster training preset (``docs/PILOT_TRAINING.md``
§3): every match padded to the 20 slots of the biggest live roster, a fresh roster
queued from Python when a match ends, as in training. ``pilot rows/s`` counts strike
craft whose action counts (``act_mask``, no capital ships), on both teams: what a
learner flying both sides of every match could train on, before torch. ``--threads``
overrides each scenario's thread count, for measuring on a shared machine.

    uv run maturin develop -m crates/sim-py/Cargo.toml --release
    uv run python tools/bench_env.py [--assert-floors]
"""

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import rlf_sim

# Run as a script from anywhere (``tools/`` is on sys.path, the repo root is not).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spacefight.env.rosters import (  # noqa: E402
    capital_hull_ids,
    make_sampler,
    resolve_distribution,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
ACTION_HIGHS = np.array([3] * 8 + [3] * 6 + [2] * 6 + [7], dtype=np.int64)
ACTION_BANK = 64
# Steps between counts of the pilot rows (each count is outside the timed loop).
ROW_COUNT_EVERY = 16


@dataclass(frozen=True)
class Scenario:
    name: str
    fleets: list[list[str]]
    n_threads: int
    target: float
    floor: float
    # SIM_VERSION 5 training shapes (module docstring).
    mission: str | None = None
    max_ships: int | None = None
    labels: bool = False
    # A roster preset: every env draws its next match from it, through RustVecEnv.
    preset: str | None = None


# Stage B training rosters (M3 plan): carrier + 5 strike craft a side (2 jump in, 3
# docked); convoy of 4 freighters + 3 escorts against 5. Both fill 12 slots.
CARRIER_SIDE = ["carrier", "fighter", "strafer", "fighter", "gunship", "fighter"]
CONVOY_TRAIN = [
    ["freighter"] * 4 + ["fighter", "strafer", "fighter"],
    ["fighter", "fighter", "strafer", "gunship", "fighter"],
]
TRAIN_SLOTS = 12


SCENARIOS = [
    Scenario("1v1 fighter", [["fighter"], ["fighter"]], 16, 6000, 3000),
    Scenario(
        "2v2 fighter+strafer",
        [["fighter", "strafer"], ["fighter", "strafer"]],
        16,
        4000,
        2000,
    ),
    Scenario("single-thread 1v1", [["fighter"], ["fighter"]], 1, 600, 300),
    # SIM_VERSION 4 (MAX_SHIPS 20): the largest fleet-pilot training roster, 8 ships.
    # Measured at 2,200 steps/s before and after the cap went from 8 to 20.
    Scenario(
        "4v4 mixed",
        [
            ["fighter", "strafer", "gunship", "fighter"],
            ["fighter", "strafer", "gunship", "fighter"],
        ],
        16,
        2000,
        1000,
    ),
    # SIM_VERSION 5, measured 2026-10-30 (see SIM_SPEC §13).
    Scenario(
        "4v4 mixed @12 +labels",
        [
            ["fighter", "strafer", "gunship", "fighter"],
            ["fighter", "strafer", "gunship", "fighter"],
        ],
        16,
        1200,
        600,
        max_ships=TRAIN_SLOTS,
        labels=True,
    ),
    Scenario(
        "carrier @12 +labels",
        [CARRIER_SIDE, CARRIER_SIDE],
        16,
        600,
        300,
        mission="carrier_battle",
        max_ships=TRAIN_SLOTS,
        labels=True,
    ),
    Scenario(
        "convoy @12 +labels",
        CONVOY_TRAIN,
        16,
        600,
        300,
        mission="convoy_escort",
        max_ships=TRAIN_SLOTS,
        labels=True,
    ),
    # No target or floor yet: both wait for a measurement on a free machine.
    Scenario(
        "pilots_v1 @20 +labels",
        [["fighter"], ["fighter"]],
        16,
        0,
        0,
        labels=True,
        preset="pilots_v1",
    ),
]


def commanders_for(scenario: Scenario) -> list[str] | None:
    """Random v scripted (the stage B mix) where the sim has a random commander."""
    if scenario.max_ships is None:
        return None
    modes = list(getattr(rlf_sim, "COMMANDER_MODES", []))
    return ["random", "scripted"] if "random" in modes else None


@dataclass(frozen=True)
class Result:
    scenario: Scenario
    steps_per_s: float
    match_ticks_per_s: float
    pilot_rows_per_s: float
    episodes: int
    n_threads: int


def build_env(
    scenario: Scenario, n_envs: int, n_threads: int, seed: int
) -> tuple[rlf_sim.VecEnv, RustVecEnv | rlf_sim.VecEnv]:
    """The env's buffers and what to step: a preset goes through ``RustVecEnv``, whose
    ``step`` queues each finished env's next roster as training does."""
    if scenario.preset is not None:
        sampler = make_sampler(resolve_distribution(scenario.preset), seed)
        wrapped = RustVecEnv(
            ASSETS,
            n_envs,
            scenario.fleets,
            seed,
            n_threads=n_threads,
            roster_sampler=sampler,
        )
        return wrapped.raw, wrapped
    kwargs: dict[str, object] = {}
    if scenario.mission is not None:
        kwargs["mission"] = scenario.mission
        kwargs["time_limit_s"] = rlf_sim.mission_time_limit_s(scenario.mission)
    if scenario.max_ships is not None:
        kwargs["max_ships"] = scenario.max_ships
    commanders = commanders_for(scenario)
    if commanders is not None:
        kwargs["commanders"] = commanders
    env = rlf_sim.VecEnv(
        ASSETS, n_envs, scenario.fleets, seed, n_threads=n_threads, **kwargs
    )
    return env, env


def run(
    scenario: Scenario,
    n_envs: int,
    warmup: int,
    steps: int,
    seed: int,
    n_threads: int | None = None,
) -> Result:
    threads = scenario.n_threads if n_threads is None else n_threads
    env, stepper = build_env(scenario, n_envs, threads, seed)
    capital = capital_hull_ids(Path(ASSETS))
    rng = np.random.default_rng(seed)
    bank = (rng.random((ACTION_BANK, *env.actions.shape)) * ACTION_HIGHS).astype(
        np.int8
    )
    actions = env.actions
    for k in range(warmup):
        if scenario.labels:
            env.scripted_actions()
        np.copyto(actions, bank[k % ACTION_BANK])
        stepper.step()
    episodes_before = int(env.episode_count.sum())
    rows_counted = counts = 0
    excluded = 0.0
    start = time.perf_counter()
    for k in range(steps):
        if scenario.labels:
            env.scripted_actions()
        np.copyto(actions, bank[k % ACTION_BANK])
        stepper.step()
        if k % ROW_COUNT_EVERY == 0:
            count_start = time.perf_counter()
            rows_counted += int(
                np.count_nonzero(env.act_mask & ~np.isin(env.hull_id, capital))
            )
            counts += 1
            excluded += time.perf_counter() - count_start
    elapsed = time.perf_counter() - start - excluded
    steps_per_s = steps / elapsed
    return Result(
        scenario=scenario,
        steps_per_s=steps_per_s,
        match_ticks_per_s=steps_per_s * n_envs,
        pilot_rows_per_s=steps_per_s * rows_counted / counts,
        episodes=int(env.episode_count.sum()) - episodes_before,
        n_threads=threads,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--n-envs", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="sim threads for every scenario (default: each scenario's own)",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="comma-separated scenario names to run (default: all)",
    )
    parser.add_argument(
        "--assert-floors",
        action="store_true",
        help="exit non-zero if any scenario is below its SIM_SPEC §13 floor",
    )
    args = parser.parse_args()

    print(
        f"rlf_sim SIM_VERSION={rlf_sim.SIM_VERSION}  N={args.n_envs}  "
        f"warmup={args.warmup}  steps={args.steps}"
    )
    header = (
        f"{'scenario':<24}{'threads':>8}{'steps/s':>11}{'match-ticks/s':>15}"
        f"{'pilot rows/s':>14}{'target':>9}{'floor':>8}{'episodes':>10}  status"
    )
    print(header)
    failed = []
    only = set(args.only.split(",")) if args.only else None
    for scenario in SCENARIOS:
        if only is not None and scenario.name not in only:
            continue
        r = run(scenario, args.n_envs, args.warmup, args.steps, args.seed, args.threads)
        if r.steps_per_s < scenario.floor:
            status = "BELOW FLOOR"
            failed.append(scenario.name)
        elif r.steps_per_s < scenario.target:
            status = "below target"
        else:
            status = "ok"
        print(
            f"{scenario.name:<24}{r.n_threads:>8}{r.steps_per_s:>11,.0f}"
            f"{r.match_ticks_per_s:>15,.0f}{r.pilot_rows_per_s:>14,.0f}"
            f"{scenario.target:>9,.0f}"
            f"{scenario.floor:>8,.0f}{r.episodes:>10}  {status}"
        )
    if args.assert_floors and failed:
        print(f"below floor: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
