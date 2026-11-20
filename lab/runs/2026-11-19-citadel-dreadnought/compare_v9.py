"""Check that v10 replays the v9 entry's script-vs-script numbers exactly.

Compares each JSON of ``--new`` (the v9 station-bomber evals re-run under SIM_VERSION
10) with the file of the same name in ``--old`` (the committed v9 results), ignoring
only ``IGNORED``. Prints one line per file and exits 1 on any difference.

    uv run python lab/runs/2026-11-19-citadel-dreadnought/compare_v9.py \\
        --old lab/runs/2026-11-19-station-bomber/out --new out/v9_rerun
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# pilots_other: a field station_eval.py gained (7555847) after the v9 files were written.
IGNORED = frozenset({"sim_version", "pilots_other"})


def differences(old: Any, new: Any, path: str = "") -> list[str]:
    """Paths at which ``old`` and ``new`` differ (``IGNORED`` keys skipped)."""
    if isinstance(old, dict) and isinstance(new, dict):
        out: list[str] = []
        for key in sorted(set(old) | set(new)):
            if key in IGNORED:
                continue
            if key not in old or key not in new:
                out.append(f"{path}/{key}: only in {'new' if key in new else 'old'}")
                continue
            out.extend(differences(old[key], new[key], f"{path}/{key}"))
        return out
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [f"{path}: length {len(old)} != {len(new)}"]
        out = []
        for i, (a, b) in enumerate(zip(old, new)):
            out.extend(differences(a, b, f"{path}[{i}]"))
        return out
    return [] if old == new else [f"{path}: {old!r} != {new!r}"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--old", type=Path, required=True)
    p.add_argument("--new", type=Path, required=True)
    args = p.parse_args(argv)
    files = sorted(args.new.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"no JSON under {args.new}")
    failed = False
    for new_path in files:
        old_path = args.old / new_path.name
        diff = differences(
            json.loads(old_path.read_text()), json.loads(new_path.read_text())
        )
        failed |= bool(diff)
        status = "identical" if not diff else f"{len(diff)} differences"
        print(f"{new_path.name}: {status}")
        for line in diff[:10]:
            print(f"  {line}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
