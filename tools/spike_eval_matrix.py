"""Run the learnability spike's eval matrix (plan §6.2, adapted; health §6.3).

Every pairing of ``tools.lab_report.matrix_pairings()`` is one ``evaluate(a, b)``
duel (n = 512, base seed 100 000, sides swapped) written as
``<run-dir>/eval/<a>[_argmax]_vs_<b>.json`` (schema ``rlf.eval.duel/1``). Pairings
whose JSON exists are skipped, so the tool is resumable; a pairing whose
checkpoint does not exist yet (training unfinished) is reported as blocked.

Policies: ``bc/bc.pt``, ``bc_dagger/best.pt``, PPO-BC final / 400 / 800 and the
best checkpoint by rollout ``vs_scripted_win`` (``lab_report.best_checkpoint``),
PPO-scratch final. Before the matrix, a determinism check steps the same fighter
duel at ``n_threads`` 1 and ``--threads`` and compares ``state_hash`` (the
``test_thread_count_does_not_change_state`` regression). The exit code is non-zero
if a pairing is blocked, the determinism check fails, or any eval (new or
existing) has ``nan_or_stuck`` matches.

    python -m tools.spike_eval_matrix --run-dir lab/runs/2026-10-28-learnability-spike
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from spacefight.env.rust_env import ACTION_HIGHS, RustVecEnv
from spacefight.eval.controllers import Controller, Policy, Scripted
from spacefight.eval.duel import ASSETS, FLEETS, MARKDOWN_HEADER, DuelResult, evaluate
from spacefight.rl.spike_ppo import checkpoint_path
from tools.lab_report import (
    BC,
    BC_DAGGER,
    FIXED_PPO_BC_UPDATES,
    MANIFEST_NAME,
    PPO_BC_BEST,
    PPO_BC_FINAL,
    PPO_SCRATCH_FINAL,
    SCRIPT,
    Pairing,
    health_lines,
    load_results,
    load_run,
    matrix_pairings,
)

EVAL_N = 512
EVAL_SEED = 100_000


@dataclass(frozen=True)
class Resolved:
    """Checkpoint paths of the matrix policies, and why the others are missing."""

    paths: dict[str, Path]
    missing: dict[str, str]
    best_update: int | None
    best_smoothed_win: float | None


def resolve_policies(run_dir: Path) -> Resolved:
    """Map every matrix policy to its checkpoint (``missing`` says why one is not
    available yet)."""
    paths: dict[str, Path] = {}
    missing: dict[str, str] = {}

    def offer(name: str, path: Path) -> None:
        if path.is_file():
            paths[name] = path
        else:
            missing[name] = f"{path} does not exist"

    offer(BC, run_dir / "bc" / "bc.pt")
    offer(BC_DAGGER, run_dir / "bc_dagger" / "best.pt")
    ppo_bc = load_run(run_dir, "ppo_bc")
    scratch = load_run(run_dir, "ppo_scratch")
    best_update: int | None = None
    best_win: float | None = None
    for run, final_name in ((ppo_bc, PPO_BC_FINAL), (scratch, PPO_SCRATCH_FINAL)):
        if not run.config:
            missing[final_name] = f"{run.name} has no config.yaml"
        elif not run.finished:
            missing[final_name] = (
                f"{run.name} at update {run.last_update} of {run.config['n_updates']}"
            )
        else:
            offer(
                final_name,
                checkpoint_path(
                    run_dir / run.name, run.config["tag"], int(run.config["n_updates"])
                ),
            )
    if ppo_bc.config:
        tag = ppo_bc.config["tag"]
        for name, update in FIXED_PPO_BC_UPDATES.items():
            offer(name, checkpoint_path(run_dir / "ppo_bc", tag, update))
        best = ppo_bc.best()
        if not ppo_bc.finished:
            missing[PPO_BC_BEST] = (
                "ppo_bc unfinished (best is chosen over the full run)"
            )
        elif best is None:
            missing[PPO_BC_BEST] = "no checkpoint has rollout episodes vs the script"
        else:
            best_update, best_win = best.update, best.smoothed_win
            offer(PPO_BC_BEST, checkpoint_path(run_dir / "ppo_bc", tag, best.update))
    else:
        for name in (*FIXED_PPO_BC_UPDATES, PPO_BC_BEST):
            missing[name] = "ppo_bc has no config.yaml"
    return Resolved(paths, missing, best_update, best_win)


def make(name: str, resolved: Resolved, argmax: bool) -> Controller:
    """Controller for a matrix policy name."""
    if name == SCRIPT:
        return Scripted()
    return Policy(resolved.paths[name], sample=not argmax)


def check_determinism(
    n_threads: int, n_envs: int = 32, steps: int = 600, seed: int = 9
) -> None:
    """Step the fighter duel at ``n_threads`` 1 and ``n_threads`` with the same
    alternating scripted / random actions and compare ``state_hash`` every 50 steps.

    Raises:
        RuntimeError: The hashes differ.
    """
    envs = [
        RustVecEnv(ASSETS, n_envs, [list(t) for t in FLEETS], seed, n_threads=t)
        for t in (1, n_threads)
    ]
    rng = np.random.default_rng(3)
    highs = ACTION_HIGHS.astype(np.int64) + 1
    for t in range(steps):
        if t % 2:
            for env in envs:
                env.scripted_actions()
        else:
            acts = rng.integers(0, highs, size=envs[0].actions.shape).astype(np.int8)
            for env in envs:
                env.actions[:] = acts
        for env in envs:
            env.step()
        if t % 50 == 0 or t == steps - 1:
            one, many = (env.raw.state_hash() for env in envs)
            if not np.array_equal(one, many):
                raise RuntimeError(
                    f"state_hash differs between n_threads 1 and {n_threads} at "
                    f"step {t} in {int((one != many).sum())} envs"
                )


def run_pairing(
    pair: Pairing, resolved: Resolved, n: int, seed: int, n_threads: int
) -> DuelResult:
    """One duel of the matrix, labelled with the matrix names."""
    a = make(pair.a, resolved, pair.argmax)
    b = make(pair.b, resolved, pair.argmax)
    result = evaluate(a, b, n=n, seed=seed, n_threads=n_threads)
    mode = ":argmax" if pair.argmax else ""
    return replace(result, a=f"{pair.a}{mode}", b=f"{pair.b}{mode}")


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def _check_existing(path: Path, n: int, seed: int) -> None:
    result = DuelResult.from_json(path.read_text())
    if (result.config.n, result.config.seed) != (n, seed):
        raise ValueError(
            f"{path} was run with n={result.config.n} seed={result.config.seed}, "
            f"not n={n} seed={seed}; move it aside to rerun"
        )


@dataclass
class MatrixOutcome:
    """What one ``run_matrix`` call did."""

    ran: list[str]
    skipped: list[str]
    blocked: dict[str, str]


def run_matrix(
    run_dir: Path,
    pairings: Sequence[Pairing],
    n: int = EVAL_N,
    seed: int = EVAL_SEED,
    n_threads: int = 12,
) -> MatrixOutcome:
    """Run the pairings whose ``eval/<stem>.json`` is missing; write the manifest.

    Raises:
        ValueError: An existing eval JSON was run with another ``n`` or ``seed``.
    """
    eval_dir = run_dir / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    resolved = resolve_policies(run_dir)
    outcome = MatrixOutcome([], [], {})
    for pair in pairings:
        path = eval_dir / f"{pair.stem}.json"
        if path.is_file():
            _check_existing(path, n, seed)
            outcome.skipped.append(pair.stem)
            continue
        absent = [
            x for x in (pair.a, pair.b) if x != SCRIPT and x not in resolved.paths
        ]
        if absent:
            outcome.blocked[pair.stem] = "; ".join(
                f"{x}: {resolved.missing[x]}" for x in absent
            )
            continue
        t0 = time.perf_counter()
        result = run_pairing(pair, resolved, n, seed, n_threads)
        _write_atomic(path, result.to_json())
        outcome.ran.append(pair.stem)
        print(
            f"{pair.label} ({time.perf_counter() - t0:.0f}s)\n"
            f"{result.markdown_row('a')}",
            flush=True,
        )
    _write_manifest(eval_dir / MANIFEST_NAME, resolved, n, seed)
    return outcome


def _write_manifest(path: Path, resolved: Resolved, n: int, seed: int) -> None:
    manifest: dict[str, Any] = {
        "n": n,
        "seed": seed,
        "policies": {name: str(p) for name, p in sorted(resolved.paths.items())},
        "missing": resolved.missing,
        "ppo_bc_best": {
            "update": resolved.best_update,
            "smoothed_vs_scripted_win": resolved.best_smoothed_win,
        },
    }
    _write_atomic(path, json.dumps(manifest, indent=1))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; non-zero on blocked pairings or failed health checks."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=12, help="sim + torch threads")
    parser.add_argument("--n", type=int, default=EVAL_N)
    parser.add_argument("--seed", type=int, default=EVAL_SEED)
    parser.add_argument("--skip-determinism", action="store_true")
    args = parser.parse_args(argv)

    import torch

    torch.set_num_threads(args.threads)
    failures: list[str] = []
    if not args.skip_determinism:
        try:
            check_determinism(args.threads)
            print(f"determinism: state_hash equal at n_threads 1 and {args.threads}")
        except RuntimeError as exc:
            failures.append(f"determinism: {exc}")

    print(MARKDOWN_HEADER)
    outcome = run_matrix(
        args.run_dir, matrix_pairings(), args.n, args.seed, args.threads
    )
    print(
        f"ran {len(outcome.ran)}, skipped {len(outcome.skipped)} existing, "
        f"blocked {len(outcome.blocked)}"
    )
    failures += [f"blocked {stem}: {why}" for stem, why in outcome.blocked.items()]
    failures += [
        f"health {line}" for line in health_lines(load_results(args.run_dir / "eval"))
    ]
    for line in failures:
        print(f"FAIL {line}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
