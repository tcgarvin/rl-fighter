"""Population CLI: list the tree, add a founder, run a round robin, write the report.

    python -m spacefight.population list --season lab/population/2026-11-sim6
    python -m spacefight.population add-founder --season lab/population/2026-11-sim6 \
        --id scratch_a --family scratch --checkpoint lab/runs/<run>/checkpoints/x.pt
    python -m spacefight.population round-robin --season lab/population/2026-11-sim6 \
        --out lab/population/2026-11-sim6/round_robin/first --members all
    python -m spacefight.population report --season lab/population/2026-11-sim6 \
        --results lab/population/2026-11-sim6/round_robin/first \
        --phase first --date 2026-11-02

``report`` writes ``report.md`` and a shadow-cull report, and changes no member's status.
``--record`` also appends the phase's ratings to the members' histories.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from spacefight.population.culling import shadow_cull, write_shadow_report
from spacefight.population.rating import Rating
from spacefight.population.records import (
    FORK,
    NO_FORK,
    NO_RELATION,
    Population,
    PopulationError,
    RatingEntry,
    add_member,
    load_population,
    new_founder,
    record_ratings,
    sha256_of,
)
from spacefight.population.report import family_tree_lines, render_report

REPORT_FILENAME = "report.md"
DEFAULT_ROOT = Path(".")


def _cmd_list(args: argparse.Namespace) -> int:
    population = load_population(args.season)
    print("\n".join(family_tree_lines(population)))
    print()
    for member in population.active():
        print(f"{member.id}: {member.family}, founder {member.founder}")
    return 0


def _cmd_add_founder(args: argparse.Namespace) -> int:
    checkpoint_path = args.checkpoint_root / args.checkpoint
    settings = json.loads(args.settings)
    if not isinstance(settings, dict):
        raise PopulationError(f"--settings must be a JSON object, got {args.settings}")
    member = new_founder(
        args.id,
        args.family,
        args.checkpoint,
        sha256_of(checkpoint_path),
        parent=args.parent,
        relation=FORK if args.parent else NO_RELATION,
        fork_update=args.fork_update if args.parent else NO_FORK,
        settings_changed=settings,
        note=args.note,
    )
    add_member(args.season, member)
    print(f"added {member.id} ({member.family}) to {args.season}")
    return 0


def _member_ids(population: Population, spec: str) -> list[str]:
    """``all`` (every member, history included), ``active`` or a comma list of ids."""
    if spec == "all":
        return sorted(population.members)
    if spec == "active":
        return [m.id for m in population.active()]
    return [name.strip() for name in spec.split(",") if name.strip()]


def _cmd_round_robin(args: argparse.Namespace) -> int:
    # Loaded here so the other commands don't need the sim or torch.
    import torch

    from spacefight.population.round_robin import RoundRobinConfig, run_round_robin

    torch.set_num_threads(args.n_threads)
    population = load_population(args.season)
    cfg = RoundRobinConfig(
        n_per_mission=args.n_per_mission,
        deathmatch_rosters=args.deathmatch_rosters,
        seed=args.seed,
    )
    run_round_robin(
        population,
        _member_ids(population, args.members),
        args.out,
        cfg,
        args.checkpoint_root,
        args.n_threads,
    )
    return 0


def _ratings_entry(rating: Rating, phase: str, date: str) -> RatingEntry:
    return RatingEntry(phase, date, rating.rating, rating.sd, rating.matches)


def _cmd_report(args: argparse.Namespace) -> int:
    population = load_population(args.season)
    path = args.season / REPORT_FILENAME
    if args.results is None:
        path.write_text(render_report(population, caveats=args.caveat))
        print(f"wrote {path}")
        return 0

    from spacefight.population.round_robin import load_results, write_summary

    results = load_results(args.results, population)
    write_summary(args.results, results)
    shadow = shadow_cull(
        population, results.ratings, args.phase, args.date, results.behaviour
    )
    write_shadow_report(args.season, shadow)
    if args.record:
        record_ratings(
            args.season,
            {
                r.member: _ratings_entry(r, args.phase, args.date)
                for r in results.ratings
            },
        )
        population = load_population(args.season)
    path.write_text(
        render_report(population, args.phase, args.date, results, shadow, args.caveat)
    )
    print(f"wrote {path}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str, handler: object, text: str) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, help=text)
        sub.add_argument(
            "--season", type=Path, required=True, help="lab/population/<season>"
        )
        sub.set_defaults(handler=handler)
        return sub

    command("list", _cmd_list, "print the family tree")

    founder = command("add-founder", _cmd_add_founder, "add a founder")
    founder.add_argument("--id", required=True)
    founder.add_argument("--family", required=True)
    founder.add_argument(
        "--checkpoint", required=True, help="path relative to --checkpoint-root"
    )
    founder.add_argument("--checkpoint-root", type=Path, default=DEFAULT_ROOT)
    founder.add_argument(
        "--parent", default="", help="its parent; empty for a from-scratch line"
    )
    founder.add_argument("--fork-update", type=int, default=NO_FORK)
    founder.add_argument(
        "--settings", default="{}", help="JSON of settings changed from the parent"
    )
    founder.add_argument("--note", default="")

    robin = command("round-robin", _cmd_round_robin, "play all pairs, resumable")
    robin.add_argument("--out", type=Path, required=True, help="results directory")
    robin.add_argument(
        "--members", default="active", help="all, active, or a comma list of ids"
    )
    robin.add_argument("--checkpoint-root", type=Path, default=DEFAULT_ROOT)
    robin.add_argument("--n-per-mission", type=int, default=12)
    robin.add_argument("--deathmatch-rosters", type=int, default=6)
    robin.add_argument("--seed", type=int, default=400_000)
    robin.add_argument("--n-threads", type=int, default=2)

    report = command("report", _cmd_report, "write report.md (changes no status)")
    report.add_argument("--results", type=Path, help="a round-robin directory")
    report.add_argument("--phase", default="")
    report.add_argument("--date", default="")
    report.add_argument(
        "--record", action="store_true", help="append the ratings to member histories"
    )
    report.add_argument("--caveat", action="append", default=[])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command; a bad record or argument ends it with a message."""
    args = _parser().parse_args(argv)
    if args.command == "report" and args.results is not None:
        if not args.phase or not args.date:
            raise SystemExit("report --results needs --phase and --date")
    try:
        return int(args.handler(args))
    except (PopulationError, FileExistsError, FileNotFoundError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
