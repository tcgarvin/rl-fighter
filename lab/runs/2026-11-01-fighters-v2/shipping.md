# Shipping `reward_300` (plan §1)

`reward_300` went live 2026-11-01 01:06 and was replaced at 07:38 by `f995_701`, with the
escort count retuned (`convoy_balance.md`, `results.md`). The rosters below are the earlier ones.

Prepared 2026-10-31 22:45 to 2026-11-01 00:30, on a machine shared with this run's
training (load about 30 on 16 threads). The promotion and the deploy are separate steps,
not done here. **Until the promotion lands, the site build and two tests fail on purpose**
(see "Order of the remaining steps").

## What changed

- **Convoy rosters** (`crates/sim/src/mission.rs`): 5, 6 or 7 freighters, `F S F G F S`
  escorts v `F F S G F S` raiders. Numbers per roster: `convoy_balance.md`. Target met on
  all three. No `SIM_VERSION` bump, goldens untouched.
- **First v6 champion through the pipeline.** The bundle build itself needed nothing for
  583 inputs: export, wasm width check and JS forward pass already handled it. The snags
  were at the edges:
  - `tools/export_policy.summarize_eval` knew only duel evals, and both the export and
    `tools.champion promote` call it. It now reads `rlf.eval.fleet/1`. A fleet eval has a
    win rate and a draw count, not wins and losses: `wins` is derived, 922 of 1024.
  - `tools/pilot_facts.py` sized the network from the constant 385. It now uses the
    current champion's sim version, so the facts follow promotions. The browser arithmetic
    now states the biggest default roster (18 pilots) rather than the 8-ship fleet.
  - `RLF_CHAMPIONS_DIR` points every registry reader at a copy, so a build can be rehearsed
    without writing the record.
- **`/pilot/`** rewritten for this pilot: 583 inputs and 230,973 weights, three new obs
  blocks, redrawn figures, training lineage, and a plain statement that it reads orders
  and follows them only a little (go-to 0.51 vs 0.39 hidden, script 0.90; threat share 0.37
  vs 0.34, script 0.65; attack share no better).
- **Jump-point label** no longer runs under the site nav or over the result banner. The
  shots showed both.
- **Tests:** parity on the real 583-input checkpoint, the fleet eval summary, and the
  18-pilot fact.

## Numbers

| check | result |
|---|---|
| convoy, `reward_300` mirror | attackers 0.632 / 0.504 / 0.415; median 48 / 50 / 59 s; time limit 0 |
| carrier battle | rosters unchanged; the 4 headless carrier battles on the final bundle ended in carrier kills at 94-107 s |
| JS inference at 18 pilots | mean 18-20 ms, p95 20-36 ms, worst single tick 72-106 ms (three runs, the page's own `policy.act` on real obs), of 33.3 ms, on the loaded machine |
| JS inference as actually played | no match reaches 18 pilots: convoy 12, carrier about 8 to 10 ships on the field; smoke mean tick 2.6-10.6 ms |
| worst page tick, soak | 38.7 ms: the highest per-match figure, a convoy with 17 ships on the field; the other convoys 17-21 ms (headless, software WebGL, loaded machine) |
| soak, 10 min at speed 8, 4 min warm-up | 12 matches; heap +5.9 %; GPU and DOM flat; bundle swap and broken manifest both fine |
| bundle | 2.4 MB, weights 924 kB (was 721 kB), wasm 1397 KiB |

Inference has no uncontended number: this machine was at load 30 throughout. By
arithmetic the new pilot costs 28 % more per ship than v1 (230,400 against 180,000
multiply-adds per forward pass). No phone was measured.

Headless matches on the final bundle (`live_smoke.mjs`, 4 from the bundle build + 12): every
match ended for its proper reason: carrier kills, `convoy_destroyed`, or eliminations.
None went to the clock. No smoke match or screenshot ended in `convoy_through`, so its banner
was not looked at on these rosters; the survey counts those endings (4-15 %) and that
code did not change. Screens read in `web/shots/live/`.

Tests, against the rehearsal registry: `pytest tests/` 479 passed, 2 skipped;
`scripts/check.sh` passed (fmt, clippy, native and wasip1 tests, wasm smoke against the
goldens, 95 Rust-env tests). `test_web_policy.py` includes parity on the real checkpoint.

## Unresolved

1. **v1's replay can no longer stop a convoy.** On the new rosters v1's raiders win 0-0.4 %
   (`convoy_balance.md`). Replays use the current build's rosters. It plays to a proper end,
   so it is left alone, but `/?champion=2026-10-30-fleet-pilot-v1` convoys are a walkover.
   The past-champion bundles of v3 and v1 build, play and load on sim 6; v1's one smoke
   deathmatch (strafers) ran the full 90 s with no deaths.
2. **Few convoys get through**, 4-15 % of matches; defenders mostly win by killing the raid.
   The mission is balanced, but a win rarely looks like a convoy reaching the jump point.
3. **Short convoy matches remain.** The median meets the bound, but a seed reached an
   elimination at 22.7 s with 7 freighters. There is no per-match floor.
4. **The commander layer overstates what pilots do.** `Show commands` draws orders these
   pilots mostly do not follow. `/pilot/` says so; the live page's caption does not.
5. **This run's gates need the new rosters.** Plan §4 measures against R "on the live default
   rosters as rebalanced". The main checkout's `rlf_sim` predates them, and it must not be
   rebuilt during training. Evals need a build with these rosters after PPO stops.

## Order of the remaining steps

`/pilot/` describes the record `promote` will write, so until it exists
`tests/test_pilot_page.py` has 2 failures and `scripts/build_pages_data.sh` (hence
`build_site.sh`) stops at the facts check. Every check here ran against a scratch copy of
the registry with `RLF_CHAMPIONS_DIR`; `promote` itself ran against that copy, with a store
that uploads nothing, so the fleet eval path is exercised. The record it wrote:
`sim_version` 6, `parent` `2026-10-30-fleet-pilot-v1`, 922 wins of 1024, sha256
`2b87e1f7...2400`.

1. `uv run python -m tools.champion promote --id 2026-11-01-reward-300 --name "mission pilot · reward, update 300" --run 2026-11-01-order-pilot-b3 --checkpoint lab/runs/2026-11-01-order-pilot-b3/reward/checkpoints/ppo_bc_300.pt --hulls fighter,strafer,gunship --eval-json lab/runs/2026-11-01-order-pilot-b3/eval/reward_300_fleet_vs_script.json --parent 2026-10-30-fleet-pilot-v1`,
   from a checkout that holds that gitignored checkpoint (in this worktree, copy it to that
   path first, because the record stores the path as given), and commit the record.
2. `scripts/build_site.sh` (current champion), then `scripts/deploy.sh`.

`dist/` in this worktree was built by the rehearsal and is otherwise what step 2 produces,
apart from the record's copy in the notebook data.
