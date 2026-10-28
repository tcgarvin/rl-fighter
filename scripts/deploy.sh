#!/usr/bin/env bash
# Deploy the static site to production at rl-fighter.tcgarvin.com.
# Needs NETLIFY_AUTH_TOKEN in the environment or in the repo's gitignored .env.
set -euo pipefail

SITE_ID="fc4f1b89-61db-4eab-89b8-f3c4bfdf6080"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

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
MESSAGE="$(git log -1 --format='%h %s')"
if [[ -n "$(git status --porcelain -- prototypes/story netlify.toml)" ]]; then
    MESSAGE="$MESSAGE (+ uncommitted changes)"
fi
netlify deploy --prod --no-build --site "$SITE_ID" --dir prototypes/story --message "$MESSAGE"
