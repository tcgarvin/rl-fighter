#!/usr/bin/env bash
# Deploy the static site in dist/ to production at rl-fighter.tcgarvin.com.
# dist/ is assembled by scripts/build_site.sh (story demo at /, live duel at /duel/).
#
# Usage: scripts/deploy.sh [<checkpoint.pt> [eval.json]]
#   With a checkpoint, rebuilds dist/ first (scripts/build_site.sh); without one,
#   deploys the dist/ already built.
# Needs NETLIFY_AUTH_TOKEN in the environment or in the repo's gitignored .env.
set -euo pipefail

SITE_ID="fc4f1b89-61db-4eab-89b8-f3c4bfdf6080"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$REPO_ROOT/dist"

if [[ -z "${NETLIFY_AUTH_TOKEN:-}" && -f "$REPO_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    . "$REPO_ROOT/.env"
    set +a
fi
if [[ -z "${NETLIFY_AUTH_TOKEN:-}" ]]; then
    echo "Error: NETLIFY_AUTH_TOKEN is not set (export it or put it in $REPO_ROOT/.env)" >&2
    exit 1
fi

cd "$REPO_ROOT"
if [[ $# -ge 1 ]]; then
    scripts/build_site.sh "$@"
fi
for required in index.html duel/index.html duel/pkg/sim_wasm_bg.wasm duel/policy/manifest.json duel/policy/weights.bin duel/assets/catalogue.json duel/notes.html; do
    if [[ ! -f "$DIST/$required" ]]; then
        echo "Error: $DIST/$required is missing; run scripts/build_site.sh <checkpoint.pt> first" >&2
        exit 1
    fi
done

POLICY="$(node -e "const m = require('$DIST/duel/policy/manifest.json'); console.log(require('path').basename(m.source.checkpoint) + ' ' + m.source.sha256.slice(0, 8))")"
MESSAGE="$(git log -1 --format='%h %s') · pilot $POLICY"
if [[ -n "$(git status --porcelain -- prototypes/story web/duel netlify.toml)" ]]; then
    MESSAGE="$MESSAGE (+ uncommitted changes)"
fi
netlify deploy --prod --no-build --site "$SITE_ID" --dir "$DIST" --message "$MESSAGE"
