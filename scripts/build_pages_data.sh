#!/usr/bin/env bash
# Generate the static data the /notebook/ and /hulls/ pages fetch at runtime:
#   web/public/notebook/data/index.json and <run-id>.json  (tools/build_notebook.py)
#   web/public/hulls/data/hulls.json                        (tools/build_catalogue.py)
# Both directories are gitignored; run this before `npm run build` in web/.
# It also checks the static /pilot/ page (web/pilot/index.html) against the code and,
# when the champion bundle has been built, against the exported champion weights
# (tools/pilot_facts.py), and the static /commander/ page (web/commander/index.html)
# against spacefight.commander and docs/COMMANDER.md (tools/commander_facts.py), and
# fails if either page has gone stale.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

uv run python -m tools.build_notebook \
    --runs lab/runs --champions "${RLF_CHAMPIONS_DIR:-lab/champions}" --out web/public/notebook/data
uv run python -m tools.build_catalogue --assets assets --out web/public/hulls/data

POLICY_MANIFEST=web/public/bundle/policy/manifest.json
if [[ -f $POLICY_MANIFEST ]]; then
    uv run python -m tools.pilot_facts --page web/pilot/index.html \
        --policy-manifest "$POLICY_MANIFEST"
else
    echo "pilot page: no $POLICY_MANIFEST (bundle not built); checking against the code only"
    uv run python -m tools.pilot_facts --page web/pilot/index.html
fi
uv run python -m tools.commander_facts --page web/commander/index.html
