# Mission survey: carrier battles end in a carrier kill, convoys are a real contest

Run 2026-10-30, plan: `plan.md`. M3 stage A, WP-S2, `SIM_VERSION` 4, branch `m3-sim2`.

<!-- summary: With the real scripted commander, a ponderous carrier and retuned hulls and rosters, carrier battles end in a carrier kill 98 % of the time after a median 116 s, about 50/50, and convoy attackers win 52–62 % on every default roster. -->

Verdict: **PASS** in the live configuration (fleet pilot v1 on every strike craft,
scripts on the capital ships, scripted commanders): every §3 target is met. The
script-vs-script convoy is lopsided per roster, which matters for stage B, not for the
live page.

## What ran

- The WP-S1 stub commander and hull numbers as a baseline (n = 32 per roster), then
  the WP-S2 commander (`scripted/commander.rs`), order-following strike-craft scripts
  (`scripted/orders.rs`) and the retuned carrier pilot, tuned with the live mode at
  n = 32–96, and a final n = 128 per roster in both modes (`survey/*.json`, tables in
  `survey/*.md`). Different seeds for tuning and final runs (500000; seed 1 for some
  carrier steps).
- `tools/mission_survey.py --mode live|script`; the live mode samples pilot v1's
  heads as the page does.

## Final, live configuration (n = 128 per roster)

Carrier battle (150 s clock):

| roster | team 0 win | team 1 win | time limit | median s | p90 s | launches | launch median s | launch p90 s | launches per 30 s |
|---|---|---|---|---|---|---|---|---|---|
| wing of 8 | 0.52 | 0.48 | 0.01 | 120 | 138 | 12.0 | 36 | 64 | 4.9 5.3 1.8 0 0 |
| wing of 6 | 0.48 | 0.52 | 0.02 | 105 | 130 | 8.0 | 10 | 24 | 7.6 0.4 0 0 0 |
| wing of 9 | 0.48 | 0.52 | 0.03 | 124 | 139 | 14.0 | 40 | 70 | 5.0 5.8 3.1 0.1 0 |
| all | 0.49 | 0.51 | 0.02 | 116 | 136 | 11.3 | 28 | 64 | 5.8 3.8 1.6 0 0 |

Every other ending is a carrier kill. Carriers move about 270 m a match; a surviving
carrier ends with about 37 % of its hull.

Convoy escort (120 s clock):

| roster | defenders win | attackers win | time limit | median s | p90 s | escaped | destroyed | route progress | defender wins with an escape |
|---|---|---|---|---|---|---|---|---|---|
| 4 freighters | 0.39 | 0.61 | 0.00 | 64 | 72 | 1.33 | 1.38 | 0.87 | 1.00 |
| 3 freighters | 0.38 | 0.62 | 0.00 | 64 | 68 | 0.82 | 1.34 | 0.90 | 1.00 |
| 5 freighters | 0.48 | 0.52 | 0.00 | 71 | 75 | 1.66 | 2.05 | 0.93 | 1.00 |
| all | 0.42 | 0.58 | 0.00 | 67 | 72 | 1.27 | 1.59 | 0.90 | 1.00 |

Defenders win by `convoy_through` (one or two by eliminating the raiders); attackers by
`convoy_destroyed`. Nothing goes to the clock.

| target (plan §3) | result |
|---|---|
| carrier: time-limit rate ≲ 20 % | 2 % ✓ |
| carrier: median 60–150 s | 116 s ✓ |
| carrier: symmetric rosters ~50/50 | 0.48–0.52 ✓ |
| carrier: launches across the match | median 28 s, p90 64 s, some to 90 s ✓ (front-loaded, see below) |
| convoy: attackers 35–65 % on every roster | 0.61 / 0.62 / 0.52 ✓ |
| convoy: median 45–120 s | 64–71 s ✓ |
| convoy: route travelled, escapes in defender wins | progress 0.90; an escape in 100 % of defender wins ✓ |
| deathmatch unchanged | `v3_compat_*` pass untouched ✓ |

## Baseline (WP-S1 stub and hull numbers, n = 32 per roster)

| mode | mission | team 0 win | time limit | median s | launch median / p90 s | launches per 30 s | escaped / destroyed |
|---|---|---|---|---|---|---|---|
| live | carrier battle | 0.44 | 0.14 | 123 | 4 / 28 | 10.4 0.9 0 0 0 | |
| live | convoy escort | 0.96 | 0.00 | 54 | | | 2.61 / 0.23 |
| script | carrier battle | 0.45 | 0.10 | 122 | 4 / 16 | 11.3 0 0 0 0 | |
| script | convoy escort | 0.95 | 0.00 | 54 | | | 2.61 / 0.19 |

The stub emptied both hangars in the first seconds, and the convoy (14 m/s freighters
with 500 hp) got through 96 % of the time.

## Tuning (live mode)

| step | change | result |
|---|---|---|
| 1 | WP-S2 commander, order-following scripts, carrier pilot (hp 1500, mains 300 N, RCS 450 N, cap 8) | carrier: time limit 0.24, launches still 8.3 of 11.3 in the first 30 s |
| 2 | freighter hp 500 → 360, cap 14 → 10 | convoy attackers 0.71 (0.47 / 0.94 / 0.72) |
| 3 | freighter 420 hp, cap 11 | attackers 0.36 |
| 4 | freighter 400 hp, cap 10.5 | attackers 0.47 overall, but 0.38 / 0.78 / 0.27 per roster |
| 5 | six candidate convoy rosters (n = 96) | 4F + 3 escorts v 6: 0.54; 3F + 4 v 5: 0.55; 5F + 4 v 8: 0.48 → the defaults (4F + 4 v 6 was 0.24, 3F + 3 v 4 0.82, 5F + 4 v 7 0.33) |
| 6 | carrier hp 1100, `WING_BASE` 4 → 3, launches ≥ 6 s apart | carrier: time limit 0.12, launch p90 52 s |
| 7 | launches ≥ 12 s apart (seed 1) | time limit 0.23 (wing of 9: 0.35): fewer ships early, slower kills |
| 8 | carrier hp 1000; the last 60 s (was 40) the carrier closes on the enemy carrier even when threatened; "winning" also on a 0.2 hull lead | time limit 0.02, median 116 s |

What decided the carrier battle: by the end both wings are spent (0.7 strike craft
left a side, hangars empty), so the result rests on the carriers' endgame. With the
stub and in step 7, a threatened carrier retreated instead of closing, and two
crippled carriers ran out the clock. Letting the clock override the retreat, with a
somewhat lighter carrier, turned nearly all of those into kills.

## Script vs script (n = 128 per roster)

| mission | roster | team 0 win | time limit | median s | notes |
|---|---|---|---|---|---|
| carrier battle | wing of 8 | 0.41 | 0.23 | 138 | |
| carrier battle | wing of 6 | 0.55 | 0.16 | 136 | |
| carrier battle | wing of 9 | 0.39 | 0.15 | 135 | |
| carrier battle | all | 0.45 | 0.18 | 136 | launch median 16 s, p90 40 s (more scrambles) |
| convoy escort | 4 freighters | 0.00 | 0.00 | 50 | the 3 scripted escorts lose every time |
| convoy escort | 3 freighters | 0.98 | 0.00 | 68 | 4 escorts against 5 raiders win every time |
| convoy escort | 5 freighters | 0.73 | 0.00 | 75 | |

The scripts play every mission to a proper end, but the scripted convoy escort is
lopsided per roster: scripted escorts guarding a transport fight far better against
5 raiders than 3 escorts do against 6. Pilot v1 does not read orders, so none of this
reaches the live page. It does matter for stage B, where the scripts are the
order-following teacher. If the teacher needs balanced convoys, that should be tuned
in the commander's guard/intercept split, not in the hulls the live balance rests on.

## Decisions and notes

- **Arena, route and clocks unchanged** (450 m, `(0, −0.55 R)` → `(0, +0.75 R)`,
  150 s and 120 s, `jump_in` 2). The balance came from hulls, rosters and the
  commander. The carrier's mounts are unchanged (they are the art contract); only its
  forces, cap and hull changed.
- **Launch spread.** Launches are paced (12 s apart outside a scramble), but pilot
  v1's dogfights empty a wing fast, so most launches come in the first minute. Wider
  spacing (step 7) brought back the clock problem. Visible launches to about 90 s
  look like a fair trade.
- **Carrier braking** relies on drag (≈ 10 s time constant). At 0.15 rad/s² a
  flip-and-burn takes longer than coasting down.
- Survey runs on a busy machine (another project's sweep was using most cores) took
  4–12 minutes each; the numbers do not depend on it.
