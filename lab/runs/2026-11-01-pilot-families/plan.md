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

## What the second night found (2026-11-07)

Trained 01:17 to 07:30: `fighters` to update 959, `followers` to 955, `fighters_pay1` to 462.
Morning evals ran unattended, 07:30 to 08:51. Ratings are in the second-night field
(15 members, 105 pairs), so they are not comparable with the first night's.

| Pilot | Combat | Go-to arrival | Attack flip | Defend flip | Gate |
|---|---|---|---|---|---|
| `fighters_pay1_462` | **+300** | 0.20 | 0.25 | 0.21 | Failed |
| `fighters_506` | +255 | 0.21 | 0.32 | 0.36 | Failed |
| `fighters_959` | +240 | 0.30 | 0.50 | 0.56 | Failed |
| `f995_701` | +214 | 0.22 | 0.14 | 0.11 | Failed (exempt) |
| `followers_955` | +146 | 0.50 | 0.81 | 0.77 | Failed on go-to |
| `followers_513` | +80 | 0.62 | 0.88 | 0.86 | Passed |
| `transit_300` | -122 | 0.70 | 0.87 | 1.00 | Passed (exempt) |

- **Was pay 3 what moved following?** Partly. At pay 1, `fighters_pay1_462` flips less on
  attack and defend (0.25 and 0.21 against `fighters_506`'s 0.32 and 0.36), the same on go-to,
  and is the strongest pilot in the field: it beats `fighters_506` 0.60, 0.61 and 0.57. One
  run each, so the size of the trade is rough.
- **Did drills 0.25 move go-to?** Yes, a little: arrival 0.21 to 0.30, lift 0.07 to 0.15, and
  attack and defend flips to about half. `drill_rows_share` averaged 0.09. Combat dipped:
  `fighters_959` wins 0.46, 0.47 and 0.54 against `fighters_506`. It still fails every bar.
- **Does `followers` keep following?** No. Go-to fell again, 0.62 to 0.50, under its 0.60
  bar. Combat rose: it beats `followers_513` 0.69, 0.61, 0.55.
- **Variety:** one cycle, in convoy escort only, on an edge at z 1.9.

All three failed the gate and are archived. Would-be culls are `transit_300` and
`followers_513`, at the bottom of their families. The live page took the ten highest rated
(logbook `lab/runs/2026-11-07-second-night`), dropping `transit_300`, `w1_400` and `v1`.

**Next, for the owner to choose:** the drill share has now been raised and following
improved only slowly, so the plan's fallback is separate skill networks
(`docs/PILOT_TRAINING.md` section 4). For `followers`, go-to falls each night that combat
rises, so it may need go-to drills weighted up, or a go-to bar it trains against.

## Night 3 (prepared 2026-11-08)

The owner's plan: pilots train under the learned commanders that went live this morning
(`lab/runs/2026-11-08-commander-1`), with more drills weighted to go-to, and the morning
judges them by wins above replacement (WAR) in live-like matches instead of the drill
gate and round robin. All three lines resume.

| Arm | Starts from | Drills | Go-to : attack : defend | Commander | Order pay |
|---|---|---|---|---|---|
| `fighters` | its update 959 | **0.35** (0.25) | **2 : 1 : 1** | 0.22 | 3 |
| `followers` | its update 955 | **0.35** (0.25) | **3 : 1 : 1** | 0.43 | 1 |
| `fighters_pay1` | its update 462 | **0.25** (0.10) | **2 : 1 : 1** | 0.25 | 1 |

- **Commanders:** every non-drill match that shows orders draws each side's commander from
  the live stable (the script, `c1_shaped`, `c1_outcome`, `c1_shaped_s1`), as the live page
  does (`commander_stable=[live]`). Hidden-orders matches and drills are unchanged.
- **Pool seeds:** night 2's plus `fighters_959`, `followers_955`, `fighters_pay1_462` and
  `f99_696`, the top pilot by WAR.
- **Why go-to:** it is every line's weakest order. `followers` lost go-to two nights
  running as its combat rose, so it gets the heaviest weighting.

**WAR before the night** (`lab/population/2026-11-sim6/war/2026-11-08-live-eleven`, 4,320
matches, the ten live pilots and `transit_300` under the live commander stable): `f99_696`
+20.6, `f995_701` +19.3, `fighters_pay1_462` +18.7, `f995_400` +18.1, `fighters_506` and
`fighters_959` +16.8, `followers_955` +14.8, `reward_300` +14.3, `hide_644` +8.7,
`followers_513` +8.5, `transit_300` +0.9 (about ±3). The live list is already the top ten.
The WAR shadow cull takes nobody.

**Morning, unattended (`morning.sh`):** drill evals on each arm's latest checkpoint (a
report; the gate archives nobody), the three as members, WAR at 1,440 matches per mission
for the eleven above plus the three, and the report with WAR shadow culls. About 1.5 hours.

```bash
cd ~/code/rl-fighter && DEADLINE="07:00" PHASE=third-night nohup setsid bash -c \
  'lab/runs/2026-11-01-pilot-families/run.sh >> lab/runs/2026-11-01-pilot-families/run.out 2>&1 &&
   lab/runs/2026-11-01-pilot-families/morning.sh > lab/runs/2026-11-01-pilot-families/morning.out 2>&1' \
  > /dev/null 2>&1 &
```

Checked before launch: `SMOKE=1 N_UPDATES=8 run.sh` (all three resumed with the new
settings, learned commander decisions reached the sim) and `morning.sh` rehearsed end to
end on the smoke checkpoints against a copy of the season (WAR at 24 per mission).

## What the third night found (2026-11-09)

Ran 01:15 to 07:00: `fighters` 960-1338, `followers` 956-1323, `fighters_pay1` 463-849.
The morning took until 09:17. WAR at 14 threads ran about twice as slowly in carrier battle
as the day before.

**WAR** (`lab/population/2026-11-sim6/war/third-night`, 4,320 matches, the eleven plus the
three new, about ±3): `f99_696` +20.8, `f995_701` +19.8, `f995_400` +18.3,
`fighters_pay1_462` +16.7, **`fighters_1338` +16.2**, **`followers_1323` +15.5**,
**`fighters_pay1_849` +14.9**, `fighters_506` and `fighters_959` +14.4, `followers_955`
+11.4, `reward_300` +10.0, `followers_513` +7.5, `hide_644` +7.1, `transit_300` +0.2.
Every pilot measured in both fields dropped 1 to 4 points, so compare within one
measurement.

- `followers` gained most: +4.1 over its parent, now level with the fighters.
  `fighters` +1.8, `fighters_pay1` -1.8, both within the noise.
- **Go-to did not move** (arrival, order shown): `followers` 0.50 to 0.47, `fighters`
  0.30 to 0.24, `fighters_pay1` 0.20 to 0.21. Attack and defend flips rose for `fighters`
  (0.50 to 0.59, 0.56 to 0.67) and defend for `followers` (0.77 to 0.84). More of the same
  drill does not teach go-to. Look at what the go-to drill rewards and what the pilot sees
  of the point before adding more.
- **Learned commanders vs the script** in the WAR matches: 0.575 (1,572 matches, ±0.025),
  up from 0.538 the day before (deathmatch 0.49 to 0.54, convoy 0.52 to 0.58, carrier 0.60
  both days). Training logs over each line's last 40 updates: own side's win rate 0.64 to
  0.69 under a learned commander, 0.46 to 0.61 under the script.

**Decisions (2026-11-09):**
- WAR culls applied, the first real ones: `fighters_959` and `fighters_506` archived on
  the founder cap (`f995_701`'s six active, cap 4). Nobody below replacement.
  `transit_300` at +0.2 stays (its CI spans 0). Active: four `fighters`, four
  `followers`, the script.
- Live list by WAR (`publish --war`, `"rated_by": "war"`; the inspector now reads
  "+16 wins per 100 matches over the script"): in `fighters_1338`, `followers_1323`,
  `fighters_pay1_849`; out `reward_300`, `followers_513`, `hide_644`. Logbook entry
  `lab/runs/2026-11-09-third-night`.
- Next by the loop: commander round 2, against these pilots.

## Night 4 (prepared 2026-11-09): the price of a shot

The owner's plan: ships fire into empty space a lot, so a shot should cost more. The sim's
`FIRE_COST` (0.002 per shot fired) makes a gauss shot worth taking at a hit rate of about
4% on hull, 8% on shields, and recent evals show 5-40% hit rates with triggers held
35-80% of decisions. The sim is unchanged (a recharging capacitor was considered and
turned down); the trainer adds `extra_fire_cost` per shot fired as shaping.

| Arm | Starts from | Fire cost per shot | Else |
|---|---|---|---|
| `fighters` | its update 1338 | **0.004** (2x) | night 3's |
| `followers` | its update 1323 | **0.004** (2x) | night 3's |
| `fighters_pay1` | its update 849 | **0.004** (2x) | night 3's |
| `fighters_fire4` | a copy of `fighters` at 1338 | **0.008** (4x) | `fighters`' |

- **`fighters_fire4`** is `fighters`' run dir copied by `run.sh` before any arm starts
  (checkpoints, optimiser and rng state), so it differs from `fighters` only in its fire
  cost. The owner's question for it: does 4x cost combat rating against 2x?
- Four arms, so 3 sim + 3 torch threads each (was 4 + 4 for three): expect about three
  quarters of night 3's updates per arm.
- Pool seeds and commanders as night 3.

**Morning, unattended (`morning.sh`):** drills, the four as members, then a **shooting
eval** of each against its parent (`eval/shooting_<id>.{json,md}`: carrier battle and
convoy, 516 each, both sides in the same matches; hit rate, shots and trigger share by
hull), then WAR at 1,440 per mission for the ten live pilots, `transit_300` and the four.

**What the morning reads:**
- Did 2x shoot less into nothing? Each 2x pilot's trigger share and shots down against
  its parent's, hit rate up, in the same matches. Strafers (hit rate 5-15%) should move
  most.
- Did it cost combat? WAR of each 2x pilot against its parent (about ±3 each, so a gap
  under about 4 is noise).
- 4x vs 2x: `fighters_fire4_<N>` against `fighters_<N>` in WAR and in shooting.

```bash
cd ~/code/rl-fighter && DEADLINE="07:00" PHASE=fourth-night nohup setsid bash -c \
  'lab/runs/2026-11-01-pilot-families/run.sh >> lab/runs/2026-11-01-pilot-families/run.out 2>&1 &&
   lab/runs/2026-11-01-pilot-families/morning.sh > lab/runs/2026-11-01-pilot-families/morning.out 2>&1' \
  > /dev/null 2>&1 &
```

Checked before launch: `tests/test_spike_ppo.py` (with a test that `extra_fire_cost`
charges each shot fired), `SMOKE=1 N_UPDATES=10 run.sh` (all four arms, the configs read
0.002 / 0.006), and `morning.sh` rehearsed end to end on the smoke checkpoints against a
copy of the season (shooting at 12, WAR at 24 per mission).

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
