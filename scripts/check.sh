#!/usr/bin/env bash
# Rust workspace gate: formatting, lints, native tests, the sim under wasmtime on
# wasm32-wasip1 (same code the browser runs), a sim-wasm browser build, and the
# rlf_sim Python extension build + its pytest suite.
# Every work package must leave this green (docs/SIM_SPEC.md §14).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# User-local tool installs (wasmtime's installer, cargo install) may not be on a
# non-interactive PATH.
export PATH="$HOME/.wasmtime/bin:$HOME/.cargo/bin:$PATH"

# pyo3 (abi3-py313) needs a >= 3.13 interpreter at build time; the system python3
# may be older. uv finds the project venv, or a managed install in a bare worktree.
if [[ -z "${PYO3_PYTHON:-}" ]]; then
    PYO3_PYTHON="$(uv python find '>=3.13')"
    export PYO3_PYTHON
fi

step() { printf '\n==> %s\n' "$*"; }

step "cargo fmt --check"
cargo fmt --all -- --check

step "cargo clippy (workspace, all targets, -D warnings)"
cargo clippy --workspace --all-targets --all-features -- -D warnings

# During a sim_version change the golden traces are regenerated once, at integration;
# work-package branches run with RLF_SKIP_GOLDEN=1 until then.
SKIP_GOLDEN=()
if [[ "${RLF_SKIP_GOLDEN:-0}" == "1" ]]; then
    SKIP_GOLDEN=(-- --skip golden_)
fi

step "cargo test (native)"
cargo test --workspace --all-features "${SKIP_GOLDEN[@]}"

step "cargo test -p sim (wasm32-wasip1 under wasmtime)"
cargo test -p sim --target wasm32-wasip1 "${SKIP_GOLDEN[@]}"

step "wasm-pack build crates/sim-wasm --target web"
# Output goes under target/ so it stays out of git.
wasm-pack --quiet build crates/sim-wasm --target web --out-dir "$REPO_ROOT/target/wasm-pack/sim-wasm"

step "node smoke: WasmMatch bundle vs native golden hashes"
# Runs the bundle just built (same bytes the browser loads); takes well under a second.
if [[ "${RLF_SKIP_GOLDEN:-0}" == "1" ]]; then
    echo "SKIPPED: RLF_SKIP_GOLDEN=1"
elif command -v node >/dev/null; then
    node crates/sim-wasm/tests/node_smoke.mjs "$REPO_ROOT/target/wasm-pack/sim-wasm"
else
    echo "SKIPPED: node not on PATH"
fi

step "maturin develop crates/sim-py (release) + pytest tests/test_rust_env{,_wrapper}.py"
# Builds the rlf_sim extension into the project venv, then runs its Python tests.
uv run maturin develop --quiet -m crates/sim-py/Cargo.toml --release
uv run python -m pytest tests/test_rust_env.py tests/test_rust_env_wrapper.py -q

# The throughput floors (SIM_SPEC §13) depend on an otherwise idle machine, so the
# benchmark is opt-in: RLF_BENCH=1 scripts/check.sh
if [[ "${RLF_BENCH:-0}" == "1" ]]; then
    step "tools/bench_env.py --assert-floors"
    uv run python tools/bench_env.py --assert-floors
fi

step "all checks passed"
