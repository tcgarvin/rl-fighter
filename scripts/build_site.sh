#!/usr/bin/env bash
# Assemble the static site in dist/ (gitignored) for scripts/deploy.sh:
#   /         the live page (web/, built by Vite) with the champion bundle at /bundle/
#             (scripts/build_bundle.sh); /notebook/ and /hulls/ come from web/ too
#   /story/   prototypes/story/ (the scripted story demo: where the match is going)
#   /duel/    redirects to /?fleets=duel (web/public/_redirects)
#
# Usage: scripts/build_site.sh                 the current champion (lab/champions;
#                                              weights fetched by tools/champion.py)
#        scripts/build_site.sh <checkpoint.pt> <run-id> [eval.json]
#   (the arguments of scripts/build_bundle.sh, which runs first; its env applies)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
DIST="$REPO_ROOT/dist"

if [[ $# -eq 1 || $# -gt 3 ]]; then
    echo "usage: scripts/build_site.sh [<checkpoint.pt> <run-id> [eval.json]]" >&2
    exit 2
fi

step() { printf '\n==> %s\n' "$*"; }

if [[ $# -eq 0 ]]; then
    step "current champion (lab/champions)"
    CHAMPION_ENV="$("${PYTHON:-$REPO_ROOT/.venv/bin/python}" -m tools.champion env)"
    eval "$CHAMPION_ENV"
    export RLF_CHAMPION_ID RLF_CHAMPION_NAME RLF_CHAMPION_HULLS
    echo "$RLF_CHAMPION_ID ($RLF_CHAMPION_HULLS): $CHAMPION_CHECKPOINT"
    set -- "$CHAMPION_CHECKPOINT" "$CHAMPION_RUN" "$CHAMPION_EVAL_JSON"
fi

scripts/build_bundle.sh "$@"

# Past champions of this sim season, replayable at /?champion=<id>; their bundles go
# to /champions/<id>/ and reuse the wasm just built.
PY="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
rm -rf web/public/champions
for past in $("$PY" -m tools.champion past); do
    step "past champion $past -> /champions/$past/"
    PAST_ENV="$("$PY" -m tools.champion env "$past")"
    (
        eval "$PAST_ENV"
        export RLF_CHAMPION_ID RLF_CHAMPION_NAME RLF_CHAMPION_HULLS
        RLF_SKIP_WASM=1 RLF_SMOKE_MATCHES=1 RLF_BUNDLE_DIR="$REPO_ROOT/web/public/champions/$past" \
            scripts/build_bundle.sh "$CHAMPION_CHECKPOINT" "$CHAMPION_RUN" "$CHAMPION_EVAL_JSON"
    )
done

step "notebook and hull catalogue data (lab/runs, lab/champions, assets)"
scripts/build_pages_data.sh

step "web: npm run build (typecheck + Vite)"
if [[ ! -d web/node_modules ]]; then
    npm --prefix web ci --no-audit --no-fund
fi
npm --prefix web run build

step "assemble $DIST (live at /, story at /story/)"
rm -rf "$DIST"
cp -R web/dist "$DIST"
mkdir -p "$DIST/story"
cp -R prototypes/story/. "$DIST/story/"
rm -f "$DIST/story/README.md"

step "built $DIST ($(du -sh "$DIST" | cut -f1)); preview: python3 -m http.server -d dist 8000"
