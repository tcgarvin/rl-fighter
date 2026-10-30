#!/usr/bin/env bash
# Web gate: build the site from the current champion (scripts/build_site.sh: bundle,
# policy export, headless smoke matches, notebook + hull data, typecheck + Vite), then
# serve web/dist and screenshot every page at 390x844 and 1440x900 into web/shots/
# (live: tools/web/live_shots.mjs; notebook, hulls and pilot: tools/web/page_shots.mjs).
# Fails on a build, smoke or typecheck failure, a page error, or sideways page scroll.
#
# Usage: scripts/check_web.sh   (env: RLF_SKIP_WASM=1 reuses the last wasm build,
#        RLF_WEB_PORT (default 4179), RLF_GPU=1 for the host GPU in screenshots)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
PORT="${RLF_WEB_PORT:-4179}"
BASE="http://localhost:$PORT"

step() { printf '\n==> %s\n' "$*"; }

scripts/build_site.sh

step "serve web/dist at $BASE"
# Something already answering on the port would be screenshotted instead of this build.
if curl -s -o /dev/null "$BASE/"; then
    echo "Error: port $PORT is already in use; stop that server or set RLF_WEB_PORT" >&2
    exit 1
fi
# vite itself, not npx: killing an npx wrapper leaves the vite child serving the port.
(cd web && exec ./node_modules/.bin/vite preview --port "$PORT" --strictPort) >/dev/null 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null || true' EXIT
for _ in $(seq 1 50); do
    kill -0 "$SERVER" 2>/dev/null || break
    curl -sf "$BASE/" >/dev/null && break
    sleep 0.2
done
kill -0 "$SERVER" 2>/dev/null && curl -sf "$BASE/" >/dev/null \
    || { echo "Error: preview server did not start on $PORT" >&2; exit 1; }

rm -rf web/shots/live web/shots/pages
step "screenshots: live page (web/shots/live)"
node tools/web/live_shots.mjs "$BASE" web/shots/live

step "screenshots: notebook, hulls and pilot (web/shots/pages)"
node tools/web/page_shots.mjs "$BASE" web/shots/pages

step "web checks passed"
