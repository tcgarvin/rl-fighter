#!/usr/bin/env bash
# Assemble the static site in dist/ (gitignored) for scripts/deploy.sh:
#   /         the live page (web/, built by Vite) with the champion bundle at /bundle/
#             (scripts/build_bundle.sh); /notebook/ and /hulls/ come from web/ too
#   /story/   prototypes/story/ (the scripted story demo: where the match is going)
#   /duel/    redirects to /?fleets=duel (web/public/_redirects)
#
# Usage: scripts/build_site.sh <checkpoint.pt> <run-id> [eval.json]
#   (the arguments of scripts/build_bundle.sh, which runs first; its env applies)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
DIST="$REPO_ROOT/dist"

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "usage: scripts/build_site.sh <checkpoint.pt> <run-id> [eval.json]" >&2
    exit 2
fi

step() { printf '\n==> %s\n' "$*"; }

scripts/build_bundle.sh "$@"

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
