#!/usr/bin/env bash
# Rust workspace gate: formatting, lints, native tests, the sim under wasmtime on
# wasm32-wasip1 (same code the browser runs), and a sim-wasm browser build.
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

step "cargo test (native)"
cargo test --workspace --all-features

step "cargo test -p sim (wasm32-wasip1 under wasmtime)"
cargo test -p sim --target wasm32-wasip1

step "wasm-pack build crates/sim-wasm --target web"
# Output goes under target/ so it stays out of git.
wasm-pack --quiet build crates/sim-wasm --target web --out-dir "$REPO_ROOT/target/wasm-pack/sim-wasm"

step "all checks passed"
