#!/usr/bin/env bash
# Generate the static data the /notebook/ and /hulls/ pages fetch at runtime:
#   web/public/notebook/data/index.json and <run-id>.json  (tools/build_notebook.py)
#   web/public/hulls/data/hulls.json                        (tools/build_catalogue.py)
# Both directories are gitignored; run this before `npm run build` in web/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

uv run python -m tools.build_notebook \
    --runs lab/runs --champions lab/champions --out web/public/notebook/data
uv run python -m tools.build_catalogue --assets assets --out web/public/hulls/data
