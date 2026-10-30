# M2 — The whole site, end to end (plan, 2026-10-29)

Status: active. Branch `m2-site`. Replaces DESIGN §12's narrower M2 ("WASM client with a
scripted match"): the user asked on 2026-10-29 to get *the whole thing* working and
looking good before building the nightly automation, stubbing what we must. M4 (the
nightly lab) starts after this.

## 1. Done when

rl-fighter.tcgarvin.com is the real exhibit, not a placeholder:

- **`/` Live.** Loops forever: muster (both rosters, ~6 s, tap to skip) → jump-in →
  battle → result → next match. The Rust sim runs in WASM and **every ship is flown by
  the current champion pilot**; no script flies a ship. Mixed fleets of the three hulls
  we have (fighter, strafer, gunship), 1–4 ships a side.
- **`/notebook/` Experiment notebook** (DESIGN calls it the journal). An index of every
  run in `lab/runs/` (date, title, verdict, sim season, promoted champion) and one page
  per run: the write-up, its tables, learning-curve charts from `log.jsonl`, gate
  results, and "watch this pilot" for runs that produced a champion.
- **`/hulls/` Hull catalogue.** One card per hull: turntable model, an actuator diagram
  (thrusters with direction and force, turret arcs, armour and impact arcs), stats from
  the YAML, and its role.
- **One site.** A shared shell (nav, type, colour tokens) across the three pages,
  portrait-phone first (390×844) and good at desktop widths. The story demo moves to
  `/story/` ("where this is going"); `/duel/` redirects to `/?fleets=duel`.
- **Champion bundle.** The live page loads `bundle/manifest.json` (sim_version, champion
  id, notebook entry, catalogue, policy) and swaps a new bundle in only between matches,
  falling back to the last good one if a load fails.
- **Checks.** `scripts/check.sh` plus a web gate: `npm run build`, typecheck, the
  headless smoke match, and Playwright screenshots of all three pages at 390×844 and
  1440×900 saved for review.

## 2. Stubs (on purpose, for later milestones)

| stub | stands in for | until |
|---|---|---|
| random roster against a budget, shown as a muster card | learned drafting (M6) | M5/M6 |
| plain skirmish, last team standing or most value at 90 s | flagships, supply, bays (M5) | M5 |
| the spike MLP with masked heads, one net for all hulls | attention policy (M3) | M3 |
| fleet eval vs the script team and vs the previous champion | Elo league (M3) | M3 |
| hand-run training on this machine | nightly lab (M4) | M4 |
| a fighter-only fleet with the v3 duel champion | the fleet pilot (WP-T) | WP-T lands |

The last row is how the live page ships before the fleet pilot exists: fighters only,
2v2 to 4v4, all flown by the v3 champion. Mixed fleets switch on when WP-T promotes.

## 3. Technical choices

- **Vite + TypeScript** for `web/` (DESIGN §9). New code is TS; the renderer modules
  (treatment, hullgeo, effects, environment, thumbs) move from `prototypes/story/` into
  `web/src/render/` as JS under `allowJs`, unchanged in behaviour. three comes from npm,
  not the CDN import map. Multi-page build: `web/index.html`, `web/notebook/index.html`,
  `web/hulls/index.html`; `web/public/` for static files.
- **Generated data, static site.** `tools/build_notebook.py` turns `lab/runs/*` into
  `notebook/data/index.json` and one `notebook/data/<run>.json` per run (rendered HTML
  for the prose, structured tables, chart series); the notebook page renders them.
  Charts are hand-drawn SVG in TS (no chart library).
- **Sim and inference stay on the main thread** for M2 (8 ships × the 2×256 MLP is
  ~30 M MAC/s). The perf readout shows headroom; move them to a Worker when it shrinks.
- **Champions** live in `lab/champions/<id>/champion.json` (committed: id, sim_version,
  source run and checkpoint, sha256 of the weights, eval summary, parent). The weights
  live in a store (see §5).

## 4. Work packages

| WP | scope | files | acceptance |
|---|---|---|---|
| S | site scaffold (done first, on `m2-site`) | `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/src/shell/*`, page stubs | `npm run build` produces `web/dist/` with three pages sharing the shell |
| L | live match page | `web/index.html`, `web/src/live/*`, `web/src/render/*` | §1 Live; plays fighter fleets with the v3 champion; screenshots at both sizes; 10-minute headless soak, no heap growth beyond 10 % |
| P | notebook + hull catalogue | `tools/build_notebook.py`, `tests/test_build_notebook.py`, `web/notebook/*`, `web/hulls/*`, `web/src/notebook/*`, `web/src/hulls/*` | §1 Notebook and Hulls render every existing run and hull; screenshots |
| T | fleet pilot v1 (training infra + the run) | `spacefight/` (fleet sampling in BC/DAgger/PPO, fleet eval), `tests/`, `lab/runs/2026-10-29-fleet-pilot/` | plan.md with gates before any eval; a pilot that flies all three hulls, gated vs the script team |
| I | integration | `scripts/build_site.sh`, `scripts/check.sh`, `tools/champion.py`, `lab/champions/`, `netlify.toml` | one command builds dist/ from the current champion; deploy |

Order: S first (by the lead), then L, P, T in parallel worktrees; I last.

## 5. Open

- ~~**Weight store:**~~ Decided 2026-10-29: the user's public bucket
  `gs://storage.tcgarvin.com` (project `tcgarvin-com`), served at
  https://storage.tcgarvin.com through a proxied Cloudflare CNAME to
  `c.storage.googleapis.com`. Champion weights go under
  `rl-fighter/champions/<id>/<sha256>.pt` (content-addressed, cached as immutable);
  `tools/champion.py` uploads, registers and fetches them. First champion:
  `2026-10-29-v3-fighter`.
