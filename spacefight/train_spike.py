"""Learnability-spike entry point (plan ``lab/runs/2026-10-28-learnability-spike``).

Subcommands register themselves through ``add_<name>_parser(subparsers)`` and run
through ``args.func(args)``::

    python -m spacefight.train_spike bc --out DIR --rows 2000000
    python -m spacefight.train_spike dagger --out DIR --init DIR/bc.pt --threads 4
    python -m spacefight.train_spike ppo --run-dir RUN --init bc.pt
    python -m spacefight.train_spike ppo --run-dir RUN --init scratch
    python -m spacefight.train_spike ppo --run-dir RUN --resume

Fleets: ``bc`` and ``dagger`` take ``--rosters fleet_v1`` (every present ship of a
1-4-a-side mixed fleet is a row, labelled by its hull's script); ``ppo`` takes
``--set rosters=fleet_v1 --set critic=fleet``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import signal
import sys
from collections.abc import Sequence
from pathlib import Path
from types import FrameType

import yaml  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------- bc


def add_bc_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``bc`` subcommand."""
    parser = subparsers.add_parser(
        "bc", help="behaviour cloning from the scripted fighter (plan §4.1)"
    )
    parser.add_argument("--rows", type=int, default=2_000_000, help="rows to collect")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--threads", type=int, default=12, help="sim + torch threads")
    parser.add_argument("--n-envs", type=int, default=256)
    parser.add_argument("--dart-p", type=float, default=0.15)
    parser.add_argument(
        "--obs-dtype", choices=("float16", "float32"), default="float16"
    )
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--lr-final", type=float, default=1e-4)
    parser.add_argument("--label-smoothing", type=float, default=0.02)
    parser.add_argument(
        "--fire-pos-weight",
        type=float,
        default=1.0,
        help="loss weight of fire=1 labels (plan §7 fire-collapse mitigation)",
    )
    parser.add_argument(
        "--throttle-change-weight",
        type=float,
        default=1.0,
        help="loss weight of throttle increase/decrease labels (§7 hold collapse)",
    )
    parser.add_argument(
        "--save-dataset", action="store_true", help="also write bc_dataset.npz"
    )
    parser.add_argument(
        "--rosters",
        default="",
        help="roster preset for fleets (e.g. fleet_v1); default: fighter duels",
    )
    parser.set_defaults(func=run_bc)


def run_bc(args: argparse.Namespace) -> int:
    """Run the ``bc`` subcommand and print the eval summary."""
    from spacefight.rl import bc

    config = bc.TrainConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        lr_final=args.lr_final,
        label_smoothing=args.label_smoothing,
        fire_pos_weight=args.fire_pos_weight,
        throttle_change_weight=args.throttle_change_weight,
        seed=args.seed,
    )
    result = bc.run(
        args.out,
        n_rows=args.rows,
        seed=args.seed,
        n_threads=args.threads,
        n_envs=args.n_envs,
        dart_p=args.dart_p,
        obs_dtype=args.obs_dtype,
        config=config,
        save_dataset=args.save_dataset,
        rosters=args.rosters,
    )
    print(json.dumps(result.eval["groups"], indent=2))
    print(f"wrote {result.checkpoint} and {result.eval_path}")
    return 0


# ------------------------------------------------------------------------ dagger


def add_dagger_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the ``dagger`` subcommand."""
    parser = subparsers.add_parser(
        "dagger",
        help="DAgger on top of BC: on-policy rows labelled by the script",
        description=(
            "Round 0 re-collects the scripted DART dataset (and trains on it unless "
            "--init is given); each round then collects on-policy rows with the "
            "current actor vs the script, aggregates and retrains, and evaluates "
            "agreement on the on-policy holdout plus duels vs the script."
        ),
    )
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--rows-per-round", type=int, default=2_000_000)
    parser.add_argument("--base-rows", type=int, default=2_000_000)
    parser.add_argument("--max-rows", type=int, default=8_000_000)
    parser.add_argument("--seed", type=int, default=0, help="round-0 seed (as bc)")
    parser.add_argument("--threads", type=int, default=4, help="sim + torch threads")
    parser.add_argument("--n-envs", type=int, default=256)
    parser.add_argument("--dart-p", type=float, default=0.15)
    parser.add_argument(
        "--beta-first", type=float, default=0.0, help="round-1 script mixing β"
    )
    parser.add_argument("--mode", choices=("finetune", "scratch"), default="finetune")
    parser.add_argument(
        "--init", type=Path, default=None, help="round-0 checkpoint (skip training)"
    )
    parser.add_argument("--epochs", type=int, default=8, help="round-0 / scratch")
    parser.add_argument("--finetune-epochs", type=int, default=2)
    parser.add_argument("--finetune-lr", type=float, default=3e-4)
    parser.add_argument("--finetune-lr-final", type=float, default=3e-5)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--lr-final", type=float, default=1e-4)
    parser.add_argument("--label-smoothing", type=float, default=0.02)
    parser.add_argument("--fire-pos-weight", type=float, default=1.0)
    parser.add_argument("--throttle-change-weight", type=float, default=1.0)
    parser.add_argument("--duel-n", type=int, default=512)
    parser.add_argument(
        "--duel-argmax", action="store_true", help="also duel the argmax policy"
    )
    parser.add_argument(
        "--rosters",
        default="",
        help="roster preset for fleets (e.g. fleet_v1); rounds are then scored on "
        "the fleet eval",
    )
    parser.add_argument("--fleet-suite", default="fleet_v1")
    parser.add_argument("--fleet-n-per-roster", type=int, default=32)
    parser.set_defaults(func=run_dagger)


def run_dagger(args: argparse.Namespace) -> int:
    """Run the ``dagger`` subcommand, printing one line per finished round."""
    from spacefight.rl import bc

    base_train = bc.TrainConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        lr_final=args.lr_final,
        label_smoothing=args.label_smoothing,
        fire_pos_weight=args.fire_pos_weight,
        throttle_change_weight=args.throttle_change_weight,
        seed=args.seed,
    )
    config = bc.DaggerConfig(
        rounds=args.rounds,
        rows_per_round=args.rows_per_round,
        base_rows=args.base_rows,
        seed=args.seed,
        n_envs=args.n_envs,
        dart_p=args.dart_p,
        beta_first=args.beta_first,
        mode=args.mode,
        base_train=base_train,
        finetune_train=dataclasses.replace(
            base_train,
            epochs=args.finetune_epochs,
            lr=args.finetune_lr,
            lr_final=args.finetune_lr_final,
        ),
        max_rows=args.max_rows,
        duel_n=args.duel_n,
        duel_argmax=args.duel_argmax,
        rosters=args.rosters,
        fleet_suite=args.fleet_suite,
        fleet_n_per_roster=args.fleet_n_per_roster,
    )

    def report(row: dict[str, object]) -> None:
        duel = row["duel"]
        if not isinstance(duel, dict):
            raise TypeError("round row has no duel dict")
        scored = row.get("fleet")
        fleet_part = (
            f" fleet {json.dumps(scored['summary'])}"
            if isinstance(scored, dict)
            else ""
        )
        print(
            f"round {row['round']} ({row['wall_s']:.0f}s, {row['aggregate_rows']} rows) "
            f"agreement {json.dumps(row['holdout_agreement'])} "
            f"duel {json.dumps(duel['sample']['summary'])}{fleet_part}",
            flush=True,
        )

    result = bc.dagger(
        args.out, config, n_threads=args.threads, init=args.init, on_round=report
    )
    print(f"best round {result.best_round} -> {result.best}; wrote {result.eval_path}")
    return 0


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
    add_bc_parser(subparsers)
    add_dagger_parser(subparsers)
    add_ppo_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    sys.exit(main())
