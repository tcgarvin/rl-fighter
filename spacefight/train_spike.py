"""Learnability-spike entry point (plan ``lab/runs/2026-10-28-learnability-spike``).

Subcommands register themselves through ``add_<name>_parser(subparsers)`` and run
through ``args.func(args)``::

    python -m spacefight.train_spike ppo --run-dir RUN --init bc.pt
    python -m spacefight.train_spike ppo --run-dir RUN --init scratch
    python -m spacefight.train_spike ppo --run-dir RUN --resume
"""

from __future__ import annotations

import argparse
import dataclasses
import signal
import sys
from collections.abc import Sequence
from pathlib import Path
from types import FrameType

import yaml  # type: ignore[import-untyped]

# --------------------------------------------------------------------------- ppo


def add_ppo_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the ``ppo`` subcommand (plan §4.2)."""
    parser = subparsers.add_parser(
        "ppo",
        help="PPO from a BC checkpoint or from scratch (plan §4.2)",
        description=(
            "PPO with masked heads, decision-tick credit, script pull and the "
            "opponent schedule. Every number lives in PPOConfig; flags left unset "
            "keep the preset (new run) or the run's config.yaml (--resume)."
        ),
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--init",
        default=None,
        help="'scratch' or a save_policy checkpoint (bc.pt); required unless --resume",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="continue from the run dir's latest checkpoint and config.yaml",
    )
    parser.add_argument("--n-updates", type=int, default=None)
    parser.add_argument("--n-envs", type=int, default=None)
    parser.add_argument("--n-steps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--sim-threads", type=int, default=None)
    parser.add_argument("--torch-threads", type=int, default=None)
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="override any PPOConfig field; VALUE is parsed as YAML "
        "(e.g. --set critic_warmup_updates=60 --set 'opponent_bands=[[0,1,0,0]]')",
    )
    parser.set_defaults(func=run_ppo)


def _ppo_overrides(args: argparse.Namespace) -> dict[str, object]:
    from spacefight.rl.spike_ppo import PPOConfig

    known = {f.name for f in dataclasses.fields(PPOConfig)}
    out: dict[str, object] = {}
    flags = {
        "n_updates": args.n_updates,
        "n_envs": args.n_envs,
        "n_steps": args.n_steps,
        "seed": args.seed,
        "sim_threads": args.sim_threads,
        "torch_threads": args.torch_threads,
    }
    out.update({key: value for key, value in flags.items() if value is not None})
    for item in args.overrides:
        key, sep, raw = item.partition("=")
        if not sep or key not in known:
            raise SystemExit(f"--set expects KEY=VALUE with a PPOConfig field: {item}")
        if key in ("init", "tag"):
            raise SystemExit(f"--set cannot change {key}; use --init")
        out[key] = yaml.safe_load(raw)
    return out


def run_ppo(args: argparse.Namespace) -> int:
    """Run (or resume) PPO training; returns the process exit code."""
    from spacefight.rl.spike_ppo import PPOConfig, SpikeTrainer, read_config

    overrides = _ppo_overrides(args)
    run_dir: Path = args.run_dir
    if args.resume:
        if args.init is not None:
            raise SystemExit("--resume takes the init from the run's config.yaml")
        base = read_config(run_dir / "config.yaml").to_dict()
        base.update(overrides)
        config = PPOConfig.from_dict(base)
    else:
        if args.init is None:
            raise SystemExit("--init scratch|PATH is required for a new run")
        if (run_dir / "config.yaml").exists():
            raise SystemExit(f"{run_dir} already holds a run; use --resume")
        config = PPOConfig.preset(args.init, **overrides)

    trainer = SpikeTrainer(config, run_dir, resume=args.resume)

    def on_signal(signum: int, frame: FrameType | None) -> None:
        print(f"signal {signum}: checkpointing after this update", flush=True)
        trainer.request_stop()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def report(_: SpikeTrainer, row: dict[str, object]) -> None:
        print(
            f"update {row['update']} {row['update_seconds']:.2f}s "
            f"(rollout {row['rollout_seconds']:.2f} gae {row['gae_credit_seconds']:.2f} "
            f"ppo {row['ppo_seconds']:.2f}) samples/s {row['samples_per_s']:.0f} "
            f"reward {row['reward_mean']:.4f} vs_scripted_win {row['vs_scripted_win']}",
            flush=True,
        )

    finished = trainer.train(on_update_end=report)
    print(f"stopped at update {finished} of {config.n_updates}", flush=True)
    return 0


# -------------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    """Top-level parser with every subcommand."""
    parser = argparse.ArgumentParser(prog="python -m spacefight.train_spike")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_ppo_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
