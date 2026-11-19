# Station mix: both seeds learn the station and the bomber, and neither keeps every old-mission bar

Verdict: **PARTIAL**. Both arms clear the station and bomber bars by a wide margin at
every measured update. Attacking the station against `followers_school_1052`, they win
0.86 to 0.87 at their finals (bar 0.45). The 3 v 3 bomber swap costs −0.09 (`mix_s1`)
and +0.12 (`mix_s2`), where the bar is −0.15 and the parent scored −0.28. Neither final
keeps every no-regression bar. `mix_s1` 2422 misses only the carrier battle (0.417
against 1052, bar 0.45, ± 0.07 at 192 matches). `mix_s2` 2447 misses the convoy (0.406),
the 3 v 3 (0.312) and the drill gate (defend_more_on_named 0.844). The plan needs both
seeds to pass, so this is not a PASS. The only checkpoint that meets every bar is
`mix_s2` 725, and its station gain is the smallest of all. The runs trained and were
measured at `SIM_VERSION` 9.

<!-- summary: We fine-tuned the pilot on the new station assault and on flying bombers, with two copies on different random seeds. Both learned it well: attacking the station they now win about 0.86 of the time against their parent (0.23 before), and their bombers hit capital ships as hard as the script's. Both also got somewhat worse at the old missions against their parent, one seed more than the other, so neither is a clean pass. -->

The plan is in [plan.md](plan.md). Both arms start fresh from `followers_school_1052`
with the same config and different seeds (191, 192). A quarter of matches are station
assaults, read half as a carrier battle and half as a convoy. A fifth of strike slots,
and a fifth of attack and defend drill pilots, are bombers. Both ran on Beast (cuda:0 /
cuda:1, 3 + 3 threads, about 12.5 s an update) from 05:34 until the 14:00 deadline. They
stopped at updates **2422** (`mix_s1`) and **2447** (`mix_s2`).

Zero-shot context (from [the station and bomber results](../2026-11-19-station-bomber/results.md)
and `eval_before/`): the live pilots won 0.36 to 0.39 attacking the station, and the
script won 0.55. Flying both sides, 1052 attacks at 0.23. A bomber in place of a gunship
cost 1052's side −0.28 in a 3 v 3 deathmatch and −0.21 in a carrier battle. In a bomber,
1052 hit its attack-drill target 0.16 of the time.

## The bars

`eval.sh` on each checkpoint. Its outputs are in `eval/<arm>_<update>/`, and
`summary.py <dir>` prints each line. ± is 1.96 standard errors where summary.py gives
one. The old-mission cells have no ± printed: at 192 matches a mission it is about
± 0.07, and **the 3 v 3 fleet cell is only 48 matches (about ± 0.14)**.

| Checkpoint | (a) Station attack vs 1052 (≥ 0.45) | (b) 3 v 3 bomber swap (> −0.15) | (c) Carrier vs 1052 (≥ 0.45) | (c) Convoy vs 1052 (≥ 0.45) | (c) 3 v 3 vs 1052, n 48 (≥ 0.45) | (c) Drill gate | All bars |
|---|---|---|---|---|---|---|---|
| 1052 (parent, `eval_before`) | (both sides 0.227 ± 0.036) | −0.276 ± 0.057 | 0.5 by symmetry | 0.5 | 0.5 | pass | |
| mix_s1 725 | 0.500 ± 0.043 | −0.107 ± 0.057 | 0.484 | 0.474 | **0.417** | pass | no |
| mix_s2 725 | 0.543 ± 0.043 | −0.140 ± 0.063 | 0.458 | 0.453 | 0.500 | pass | **yes** |
| mix_s1 2200 | 0.852 ± 0.030 | +0.021 ± 0.060 | **0.432** | **0.391** | **0.417** | pass | no |
| mix_s2 2200 | 0.809 ± 0.034 | +0.130 ± 0.057 | **0.302** | **0.323** | **0.323** | **fail** (attack_target_hit 0.898, defend_more_on_named 0.844) | no |
| **mix_s1 2422 (final)** | 0.873 ± 0.029 | −0.086 ± 0.060 | **0.417** | 0.464 | 0.479 | pass | no |
| **mix_s2 2447 (final)** | 0.855 ± 0.031 | +0.116 ± 0.059 | 0.458 | **0.406** | **0.312** | **fail** (defend_more_on_named 0.844) | no |

Bold marks a missed bar.

### The station assault in detail

Scripted commanders on both sides, 256 matches a reading, both readings pooled (512).
"Self" is the candidate on both teams.

| Checkpoint | Attack vs 1052 | 1052 attacking it (its defender win) | Self, attacker win | Bomber dmg to capital ships, a bomber (self / attacking 1052) |
|---|---|---|---|---|
| 1052 | | | 0.227 ± 0.036 | 38 / – |
| mix_s1 725 | 0.500 | 0.822 | 0.498 | 139 / 139 |
| mix_s2 725 | 0.543 | 0.859 | 0.414 | 125 / 122 |
| mix_s1 2200 | 0.852 | 0.811 | 0.730 | 257 / 240 |
| mix_s2 2200 | 0.809 | 0.840 | 0.820 | 331 / 310 |
| mix_s1 2422 | 0.873 | 0.836 | 0.742 | 293 / 262 |
| mix_s2 2447 | 0.855 | 0.828 | 0.824 | 371 / 343 |

For comparison, the script deals 305 a bomber and the live pilots 36.

- **The attack is learned.** It rises from 0.50 to 0.54 at 725 to 0.85 to 0.87 at the
  finals, against the same 1052 defence. The bomber's damage to capital ships goes from
  38 to 262 to 371 a bomber, which is the script's level (305).
- **The defence moved much less.** When 1052 attacks a candidate, 1052 wins 0.14 to 0.19
  (defender win 0.81 to 0.86). Flying both sides, 1052 attacked at 0.23. So the
  candidates defend a little better than 1052 does, and attack much better.
- **Trained pilots on both sides make the mission lopsided.** With a candidate on both
  teams, the attacker wins 0.74 (`s1`) and 0.82 (`s2`). The script on both sides gives
  0.55. Matches also stopped running out the clock: time-limit ends fell from 0.27 to
  0.33 for 1052 to 0.00 to 0.04. The station balance was tuned with the script, so a
  page that flies these pilots on both sides will see the station fall most of the time.
- The two readings differ by up to 0.11 on a row (`summary.py` prints them apart), and
  neither is consistently the easier one.

### The bomber

| Checkpoint | Swap delta, 3 v 3 dm (512 pairs) | Swap delta, carrier (516) | Bomber drills: attack target_hit (as drawn) | Bomber drills: defend more_on_named (as drawn) |
|---|---|---|---|---|
| 1052 | −0.276 ± 0.057 | −0.212 ± 0.049 | 0.156 (0.961) | 0.203 (0.945) |
| mix_s1 725 | −0.107 ± 0.057 | −0.105 ± 0.052 | 0.336 (1.000) | 0.414 (0.891) |
| mix_s2 725 | −0.140 ± 0.063 | −0.079 ± 0.049 | 0.359 (0.961) | 0.375 (0.898) |
| mix_s1 2200 | +0.021 ± 0.060 | −0.083 ± 0.054 | 0.492 (0.984) | 0.508 (0.914) |
| mix_s2 2200 | +0.130 ± 0.057 | −0.035 ± 0.054 | 0.516 (0.898) | 0.633 (0.844) |
| mix_s1 2422 | −0.086 ± 0.060 | −0.063 ± 0.053 | 0.555 (0.977) | 0.602 (0.883) |
| mix_s2 2447 | +0.116 ± 0.059 | +0.014 ± 0.055 | 0.547 (0.938) | 0.586 (0.844) |

- **A bomber no longer costs a side the deathmatch.** The swap delta goes from −0.28 to
  between −0.11 and +0.13. In `s2` the bomber side is now ahead, which suggests the bomber
  is the stronger hull in a pilot's hands, not only the equal of the gunship. (The bomber
  slot's own damage to strike craft in the deathmatch doubles, from 31 to 101 to 147 a match.)
- **Bomber drills are half learned.** The attack target is hit 0.55 of the time in a
  bomber, against 0.16 for the parent. That is still well below the 0.94 to 0.98 in the
  old hulls, and below the script's 0.97 in a bomber (plan.md). Drills are only a fifth
  bombers in training, and the drill gate does not test them.

### Old missions in detail (against 1052)

Carrier battle and convoy escort are 192 matches a mission (scripted commanders). The
fleet_v1 suite is 256 matches over six classes, 32 to 48 each. The table shows the small
classes too, because `s2`'s drop is largest there.

| Checkpoint | Carrier | Convoy | Fleet 1 v 1 (48) | 2 v 2 (48) | 3 v 3 (48) | 4 v 4 (32) | All fleet (256) |
|---|---|---|---|---|---|---|---|
| mix_s1 725 | 0.484 | 0.474 | 0.188 | 0.333 | 0.417 | 0.562 | 0.367 |
| mix_s2 725 | 0.458 | 0.453 | 0.417 | 0.250 | 0.500 | 0.359 | 0.424 |
| mix_s1 2200 | 0.432 | 0.391 | 0.385 | 0.417 | 0.417 | 0.531 | 0.443 |
| mix_s2 2200 | 0.302 | 0.323 | 0.073 | 0.354 | 0.323 | 0.344 | 0.314 |
| mix_s1 2422 | 0.417 | 0.464 | 0.396 | 0.438 | 0.479 | 0.562 | 0.480 |
| mix_s2 2447 | 0.458 | 0.406 | **0.042** | **0.146** | 0.312 | 0.375 | 0.273 |

- **`mix_s1` stays close to 1052.** Its final is 0.42 to 0.48 on every old measure,
  within about one standard error of 0.45 or above it. Its carrier miss (0.417) is
  0.033 under the bar, against a ± 0.07.
- **`mix_s2` lost the small fights.** Against 1052 it wins 0.04 of 1 v 1s and 0.15 of
  2 v 2s at its final (48 matches each), and 0.31 to 0.32 of the convoy and 3 v 3 at
  2200. Its drill gate fails at 2200 and at the final. `s1` has none of this, at the same
  config. So at least part of the regression comes from the seed, not from the station
  mix as such. With two seeds, we can't say how often a seed goes the way `s2` did.
- **The regression grows with training.** At 725 both arms are within the bars except
  `s1`'s 48-match 3 v 3. By 2200 both have dropped on the carrier and the convoy. `s1`
  recovers some of it by 2422. `s2` recovers the carrier but loses the small fleets.

## Training telemetry (`log.jsonl`)

From `telemetry.py`: windows of 500 updates, the learner side's win rate by class
(weighted by episodes, n in brackets), drill pass rates, and the bomber's hit rate and
damage per sample relative to the gunship's. Opponents are the usual mix of self,
snapshots, pool seeds and the script, so these are not wins against 1052.

| Arm | Updates | Station attack win (n) | Station defend win (n) | Carrier win (n) | Convoy attack (n) | Convoy defend (n) | Deathmatch (n) | Drill attack | Drill defend | Drill goto | Bomber hit rate | Bomber / gunship dmg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mix_s1 | 1–500 | 0.51 (837) | 0.57 (865) | 0.51 (1543) | 0.68 (779) | 0.53 (809) | 0.53 (2084) | 0.88 | 0.85 | 0.77 | 0.053 | 0.37 |
| mix_s1 | 501–1000 | 0.60 (874) | 0.52 (909) | 0.53 (1642) | 0.69 (835) | 0.54 (749) | 0.54 (2094) | 0.90 | 0.85 | 0.76 | 0.084 | 0.70 |
| mix_s1 | 1001–1500 | 0.64 (895) | 0.55 (895) | 0.57 (1685) | 0.74 (835) | 0.49 (796) | 0.54 (2093) | 0.88 | 0.83 | 0.79 | 0.088 | 0.84 |
| mix_s1 | 1501–2000 | 0.73 (927) | 0.50 (931) | 0.58 (1642) | 0.71 (819) | 0.57 (820) | 0.57 (2317) | 0.88 | 0.84 | 0.78 | 0.121 | 1.03 |
| mix_s1 | 2001–2422 | 0.73 (786) | 0.46 (809) | 0.58 (1455) | 0.72 (738) | 0.54 (709) | 0.58 (1928) | 0.88 | 0.81 | 0.78 | 0.144 | 1.10 |
| mix_s2 | 1–500 | 0.49 (822) | 0.58 (803) | 0.55 (1529) | 0.69 (782) | 0.50 (789) | 0.55 (2128) | 0.90 | 0.84 | 0.76 | 0.058 | 0.44 |
| mix_s2 | 501–1000 | 0.63 (912) | 0.56 (881) | 0.56 (1636) | 0.72 (828) | 0.51 (805) | 0.54 (2051) | 0.90 | 0.84 | 0.75 | 0.079 | 0.70 |
| mix_s2 | 1001–1500 | 0.60 (891) | 0.61 (869) | 0.54 (1599) | 0.71 (819) | 0.52 (747) | 0.55 (2097) | 0.88 | 0.83 | 0.76 | 0.100 | 0.91 |
| mix_s2 | 1501–2000 | 0.64 (864) | 0.47 (910) | 0.56 (1626) | 0.71 (808) | 0.51 (741) | 0.54 (2120) | 0.89 | 0.87 | 0.80 | 0.108 | 1.05 |
| mix_s2 | 2001–2447 | 0.74 (797) | 0.45 (776) | 0.58 (1403) | 0.68 (719) | 0.52 (730) | 0.55 (1991) | 0.88 | 0.79 | 0.80 | 0.121 | 1.25 |

- **The bomber is learned steadily.** Its hit rate rises from 0.05 to 0.12 to 0.14, and
  its damage per sample from 0.4 of a gunship's to 1.1 to 1.25 of it. The trend has not
  flattened by the deadline in either arm.
- **The station attack rises and the defence falls.** Attack goes from 0.50 to 0.73,
  and defend from 0.57 to 0.45. That is the same lopsidedness the self eval shows (0.74
  to 0.82).
- **The training logs do not show the old-mission regression.** Carrier and deathmatch
  wins hold at 0.54 to 0.58 throughout, and drill passes are flat, apart from defend
  dipping to 0.79 to 0.81 in the last window of both arms. Against a pool that is itself
  changing, this can't show a loss against 1052. Only the cross eval does.

## What we learned

- **The bomber and the station can be learned in a night of fine-tuning.** Two seeds
  agree: station attack 0.86 to 0.87 against the parent, bomber damage to capital ships
  at the script's level, and no swap cost in a 3 v 3. Most of the bomber gain came after
  725, so a shorter run would leave much of it out.
- **It costs some of the old missions, and how much depends on the seed.** `s1` 2422
  sits within noise of the bars (it misses the carrier by 0.03). `s2` 2447 lost 1 v 1 and
  2 v 2 badly against 1052 and fails the drill gate. Before a config like this goes
  further, it needs a third seed, or an anchor to 1052 on the old missions (`kl_anchor`
  was off here).
- **Attack learned faster than defence.** With the new pilots on both sides, the station
  falls 0.74 to 0.82 of the time. If these pilots fly the station on the live page, the
  mission's balance (tuned on the script) needs another look.
- **Bomber drills are half passed** (0.55 target hit, against 0.97 for the script). The
  drill gate doesn't cover them, and it should before a bomber pilot is certified.
- Not measured: WAR or a rating, a third seed, the live commanders (all of this eval
  uses scripted commanders), and bomber drills at more than 64 a kind.

## Pick for the live pilots

`lab/runs/2026-11-19-station-mix/mix_s1/checkpoints/ppo_bc_2422.pt` (`mix_s1` final),
as a WAR candidate. It has the drill gate, a full-strength station attack (0.87) and
bomber (−0.09 swap, 262 to 293 to capital ships). It also has the smallest old-mission
cost of any late checkpoint: 0.42 to 0.48 against 1052 everywhere, and its one miss is
inside the noise. `mix_s2` 725 is the only checkpoint to meet every bar, but it has only
half the station and bomber gain (0.54 and 122). Neither `mix_s2` late checkpoint should
go forward, because of the small-fleet losses and the gate failure.

## Files

- `eval_before/`: 1052 on itself (no candidate-against-1052 parts).
- `eval/{s1,s2}_{725,2200,final}/`: every `eval.sh` output (JSON, `.log` beside each,
  `drills.md`), and `eval/<dir>.out` with summary.py's bar lines at the end. The finals
  ran on Beast, THREADS=4, the two in parallel, about 17 min each.
- `telemetry.py`: the training table above.
- `run_beast.out`, `mix_s1.out`, `mix_s2.out`: supervisor and trainer logs.
- Not in git: the run directories `mix_s1/` and `mix_s2/` (log.jsonl, config, checkpoints).
