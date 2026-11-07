# First pilot families

Planned 2026-11-01, before any of this was trained. The full plan is
`docs/PILOT_TRAINING.md`. This file is the exact run. **Nothing starts until the owner says
the machine is free.**

## Steps

1. **Check the whole repo:** `scripts/check.sh` and the full pytest suite, which have not
   run on the merged code, including the wasm build.
2. **Measure (`measure.sh`):** drills on the script, founders, `reward_300` and `hide_644`,
   then the round robin across 9 existing pilots. Set the bars in
   `spacefight/eval/drill_bars.yaml` from the drill results.
3. **Speed and memory check:** `run.sh` for about 10 minutes, all arms. Read update time
   and memory. Each learner's rollout obs buffer is about 2 GB at 256 envs and 20 slots,
   and the machine has 29 GB. If memory is tight, set `N_ENVS` lower for all arms.
4. **First night (`run.sh`):** resumes from step 3.
5. **Morning:** drill evals on each arm's latest checkpoint, add those that train usefully
   to the population, round robin into a new results directory, report with shadow culls.

## What the measuring found (2026-11-01 evening)

- **Checks:** `scripts/check.sh` and the full pytest suite pass (690 passed, 1 skipped).
- **Drills:** the script and `transit_300` flip with the order at 0.87 to 1.00; `f995_701`,
  `reward_300` and `hide_644` at 0.10 to 0.18. Bars are set between them, and `transit_300`
  passes (`docs/PILOT_TRAINING.md` section 2, `eval/`).
- **Round robin:** a straight ladder with no cycles: `f995_701` +270, `f995_400` +260,
  `f99_696` +232, `hide_644` +1, `reward_300` -42, `transit_300` -74, `w1_400` -94, v1 -159,
  script -394.
- **Speed:** 36 s an update for `fighters` and `followers`, 42 s for `scratch`, all three
  running. About 2.8 GB per learner, 13 GB free.
- **Drill share counts matches, not rows.** Drills are short and small, so 0.10 of matches is
  about 0.03 of `fighters`' rows and 0.25 is about 0.06 of `followers`'. Read
  `drill_rows_share` in `log.jsonl` before raising it.

## What the first night found (2026-11-02)

Trained 18:51 to 21:34 and 01:40 to 06:00, about 7 hours after the owner needed the machine
for 4: `fighters` 506 updates, `followers` 513, `scratch` 417.

| Pilot | Combat | Go-to arrival | Attack flip | Defend flip | Gate |
|---|---|---|---|---|---|
| `f995_701` (parent) | +277 | 0.22 | 0.14 | 0.11 | Failed (exempt) |
| `fighters_506` | **+314** | 0.21 | 0.32 | 0.36 | Failed |
| `transit_300` (parent) | -71 | 0.70 | 0.87 | 1.00 | Passed (exempt) |
| `followers_513` | **+144** | 0.62 | 0.88 | 0.86 | **Passed** |
| Script | -357 | 1.00 | 0.97 | 1.00 | Report only |
| `scratch_417` | -543 | 0.06 | 0.08 | 0.09 | Failed |

- **Does `fighters` learn orders?** Partly. Attack and defend flips rose, go-to did not move
  (lift 0.07 before and after).
- **Does `fighters` keep combat?** It gained. It beats `f995_701` 0.62 in deathmatch, 0.62 in
  carrier and 0.53 in convoy.
- **Does `followers` gain combat?** Yes, +215 points. It beats `transit_300` 0.82, 0.70, 0.86.
- **Does `followers` keep following?** Mostly. Go-to fell from 0.70 to 0.62, 0.02 above its
  bar, and defend flip from 1.00 to 0.86. Attack flip held.
- **Is `scratch` alive?** Barely. 0.00 in deathmatch against the script. Under this plan's
  rule its slot goes to another family.
- **Variety:** still no cycles in any mode. Sibling lines are not yet rock-paper-scissors.

`f995_701` stays live: `fighters_506` beats it but fails the gate, and `followers_513` passes
the gate but loses to it. The gate archived `fighters_506` and `scratch_417`, and the
`fighters` line continues from `fighters_506`'s checkpoint regardless.

**Next night, unless the owner says otherwise:** `fighters` from update 506 with
`drill_share` 0.25, the plan's fallback, since go-to did not move; `followers` from update
513 unchanged; `scratch`'s slot goes to a second `fighters` line at order pay 1, which tests
whether pay 3 was what moved following. Add `fighters_506` and `followers_513` to the enemy
pool.

## Night 2 (prepared 2026-11-06)

The next night above, with one choice made: `fighters_pay1` starts from `f995_701`, not
from `fighters_506`, with night 1's drills (0.10) and pool. Its only difference from night
1's `fighters` is order pay 1 rather than 3, so comparing the two at the same update
answers whether pay 3 moved following. It is also a new branch under `f995_701`, rather
than another child of the top pilot.

| Arm | Starts from | Drills | Commander | No commander | Order pay | Pool seeds |
|---|---|---|---|---|---|---|
| `fighters` | its update 506 (resume) | **0.25** | 0.25 | 0.50 | 3 | night 1's + `fighters_506`, `followers_513` |
| `followers` | its update 513 (resume) | 0.25 | 0.50 | 0.25 | 1 | night 1's + `fighters_506`, `followers_513` |
| `fighters_pay1` | `f995_701` | 0.10 | 0.30 | 0.60 | **1** | night 1's |

**A resume bug, fixed first.** Before this fix, a resume rebuilt the enemy pool from the
checkpoint and ignored a changed `pool_seed`, but took the count of seeds from the config. So the
two new seeds would never have been drawn, and the run's own update-50 and update-100
snapshots would have been sampled as seeds. `reseed_pool` (`spacefight/rl/spike_ppo.py`)
now puts the config's seeds first and moves the weighted-sampling results with their
entries. On the real checkpoints all 14 and 15 results carry over and the new seeds
start even.

**Morning, unattended:** `morning.sh` runs drills on each arm's latest checkpoint, adds
the three as members with their drill records, plays the round robin seeded with
`first-night`'s 66 pairs (39 new pairs), and writes the report with shadow culls. It
archives nothing; gate archiving is decided when reading the report. Expect about 1.5 hours
at 12 threads (night 1's pairs took about 2 minutes each), so the PPO deadline sits that
far before the results are wanted.

```bash
cd ~/code/rl-fighter && DEADLINE="07:30" PHASE=second-night nohup setsid bash -c \
  'lab/runs/2026-11-01-pilot-families/run.sh >> lab/runs/2026-11-01-pilot-families/run.out 2>&1 &&
   lab/runs/2026-11-01-pilot-families/morning.sh > lab/runs/2026-11-01-pilot-families/morning.out 2>&1' \
  > /dev/null 2>&1 &
```

Checked before launch: full pytest (714 passed), `SMOKE=1 N_UPDATES=5 run.sh` (both
resumed arms took the new settings and the 7-seed pool), and `morning.sh` rehearsed end
to end on the smoke checkpoints against a copy of the season.

## Arms (night 1)

All arms: preset `pilots_v1`, discount 0.995 with order pay following it, no script pull,
no KL anchor, constant LR, 4 sim + 4 torch threads, checkpoints every 50 updates.

| Arm | Starts from | Drills | Commander | No commander | Order pay | Enemies |
|---|---|---|---|---|---|---|
| `fighters` | `f995_701` | 0.10 | 0.30 | 0.60 | 3 | 0.2 script, 0.4 self, 0.4 pool (weighted) |
| `followers` | `transit_300` | 0.25 | 0.50 | 0.25 | 1 | same |
| `scratch` | Random weights | 0.10 | 0.30 | 0.60 | 1 | 0.5 script, 0.5 self |

Pool: `f995_701`, `transit_300`, `reward_300`, `w1_400`, v1 for half of draws, this run's
checkpoints for the rest.

**Why these settings:**

- **`fighters` at order pay 3:** this is the plan's first question. Can a small share of
  drills give a strong fighter some following while it keeps its combat? Pay of 3 gives
  the question a real chance. If combat falls badly, the next try is 1.
- **`followers` at order pay 1:** it already follows and needs combat, so team reward
  should dominate. Its script pull ends here.
- **`scratch`:** actor LR 3e-4 rather than 1e-4, since it starts from nothing, and no
  frozen pool at first, since strong enemies would give it nothing to learn from.

## What each morning reads

| Question | Measure |
|---|---|
| Does `fighters` learn orders? | Drill flip rates and go-to lift against `f995_701` |
| Does `fighters` keep combat? | No-commander matches against `f995_701` |
| Does `followers` gain combat? | No-commander matches against `transit_300` |
| Does `followers` keep following? | Its drill results against `transit_300`'s |
| Is `scratch` alive? | Deathmatch against the script. If it can't beat the script by morning, its slot goes to another family |

**Fighters' fallback:** if following does not improve, raise the drill share. If that fails,
move to separate skill networks (`docs/PILOT_TRAINING.md` section 4).

`f995_701` stays live throughout. Nothing here deploys.
