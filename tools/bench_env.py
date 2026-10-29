"""Throughput benchmark for the Rust batched env (docs/SIM_SPEC.md §13).

Random valid actions, obs on, events off, N = 256 matches, 100 warm-up steps then
2000 timed steps. One step = all N matches advance one tick. Random actions are
drawn with numpy into a bank before timing and copied into `env.actions` each step,
so the timed loop measures the env plus the per-step Python call and copy, not the
random number generator.

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

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
ACTION_HIGHS = np.array([3] * 8 + [3] * 6 + [2] * 6 + [7], dtype=np.int64)
ACTION_BANK = 64


@dataclass(frozen=True)
class Scenario:
    name: str
    fleets: list[list[str]]
    n_threads: int
    target: float
    floor: float


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
]


@dataclass(frozen=True)
class Result:
    scenario: Scenario
    steps_per_s: float
    match_ticks_per_s: float
    episodes: int


def run(scenario: Scenario, n_envs: int, warmup: int, steps: int, seed: int) -> Result:
    env = rlf_sim.VecEnv(
        ASSETS, n_envs, scenario.fleets, seed, n_threads=scenario.n_threads
    )
    rng = np.random.default_rng(seed)
    bank = (rng.random((ACTION_BANK, *env.actions.shape)) * ACTION_HIGHS).astype(
        np.int8
    )
    actions = env.actions
    for k in range(warmup):
        np.copyto(actions, bank[k % ACTION_BANK])
        env.step()
    episodes_before = int(env.episode_count.sum())
    start = time.perf_counter()
    for k in range(steps):
        np.copyto(actions, bank[k % ACTION_BANK])
        env.step()
    elapsed = time.perf_counter() - start
    steps_per_s = steps / elapsed
    return Result(
        scenario=scenario,
        steps_per_s=steps_per_s,
        match_ticks_per_s=steps_per_s * n_envs,
        episodes=int(env.episode_count.sum()) - episodes_before,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--n-envs", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
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
        f"{'scenario':<22}{'threads':>8}{'steps/s':>11}{'match-ticks/s':>15}"
        f"{'target':>9}{'floor':>8}{'episodes':>10}  status"
    )
    print(header)
    failed = []
    for scenario in SCENARIOS:
        r = run(scenario, args.n_envs, args.warmup, args.steps, args.seed)
        if r.steps_per_s < scenario.floor:
            status = "BELOW FLOOR"
            failed.append(scenario.name)
        elif r.steps_per_s < scenario.target:
            status = "below target"
        else:
            status = "ok"
        print(
            f"{scenario.name:<22}{scenario.n_threads:>8}{r.steps_per_s:>11,.0f}"
            f"{r.match_ticks_per_s:>15,.0f}{scenario.target:>9,.0f}"
            f"{scenario.floor:>8,.0f}{r.episodes:>10}  {status}"
        )
    if args.assert_floors and failed:
        print(f"below floor: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
