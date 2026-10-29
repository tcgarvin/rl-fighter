"""Entry point of the learnability spike (plan §8): ``python -m spacefight.train_spike``.

Subcommands:

- ``bc``: behaviour cloning from the scripted fighter (plan §4.1).

Each subcommand lives in its own ``add_*_parser`` / ``run_*`` pair.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path


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
    parser.set_defaults(func=run_bc)


def run_bc(args: argparse.Namespace) -> None:
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
    )
    print(json.dumps(result.eval["groups"], indent=2))
    print(f"wrote {result.checkpoint} and {result.eval_path}")


def build_parser() -> argparse.ArgumentParser:
    """The top-level parser with every subcommand."""
    parser = argparse.ArgumentParser(prog="python -m spacefight.train_spike")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_bc_parser(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Parse ``argv`` and run the chosen subcommand."""
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
