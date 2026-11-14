# Go-to school: the second night on v8

Prepared 2026-11-14, 01:20. Still the pilots' turn. The owner gave the machine until 09:00.

## Why

The first v8 night (`lab/runs/2026-11-12-pilots-v8/results.md`) put a deadline in the
go-to order and let pilots see it. Nobody learned to fly by it: go-to drills in time went
0.49 to 0.51 on the `followers` line, 0.38 to 0.42 on `fighters`, and a lone ship still
fights first (sweep, in time at an allowance of 2: 0.06). Two things read from the logs:

- **A night holds little of this lesson.** An update finishes about 16 matches, 5 of them
  go-to drills. Over the night an arm saw about 1,800 go-to drills and 3,300 ships under
  a deadline. The share that missed was flat from the first hour to the last.
- **At order pay 1 a deadline is worth about one kill.** In a drill a fighter kill pays
  about 0.8; making the deadline pays +1 and missing it costs 1. Fighting first is close
  to a wash. Last night does not show that more pay helps: `fighters_v8` (order pay 3, a
  deadline worth 3) gained 0.04 on go-to drills and `fighters_pay1_v8` (pay 1) gained
  0.06. Those two lines differ in more than pay, so it is not a clean comparison.

Neither is tested yet. Tonight tests both, the pay on one line with nothing else changed.

## Arms

Each continues one of last night's runs: its directory starts as a copy of that run's, so
the update count carries on, the optimiser keeps its state and the four deadline inputs
keep their 3 times faster step. Three arms, 5 threads each (four at 3 last night).

| Arm | From | Go-to share of training starts | Deadline worth |
|---|---|---|---|
| `followers_school` | `followers_v8_352` | 0.53 (drills 0.7, go-to weighted 6 of 8) | 3 |
| `followers_pay3` | `followers_v8_352` | 0.21 (drills 0.35, go-to 3 of 5), as last night | 3 |
| `fighters_v8` | `fighters_v8_362` | 0.18 (drills 0.35, go-to 2 of 4), as last night | 3, as last night (order pay 3) |

- `followers_school` against `followers_pay3`: what 2.5 times the go-to drills buys at
  the same pay. In rehearsal drills were 52% of its rows (15% to 19% last night).
- `followers_pay3` against last night's `followers_v8`: what the pay buys alone.
- `fighters_v8`: a second night of the same, the control for "it only needed more time".
- Attack and defend pay stay at order pay 1 on the followers arms; only the go-to
  deadline is worth 3 (`goto_timed_bonus`, `goto_miss_penalty`).
- The two changed arms freeze the actor for 10 updates so the critic can learn what a
  go-to row is now worth.
- Not changed: the drills themselves. Squads are still 1 to 4 ships, so about one go-to
  drill in four is a ship alone, which is the case the sweep measures and pilots do worst.

Training stops at 07:20 (about 6 hours, perhaps 430 updates at the rehearsal's pace); the
morning script takes about 90 minutes and must be off the machine by 09:00.

## What the morning reads

Baselines are last night's files: the script and both parents on the same drills and sweep
seeds (`lab/runs/2026-11-12-pilots-v8/eval/`, `lab/population/2026-11-sim6/sweep/first-v8-night/`).

1. **Go-to drills, in time, by tight, medium and loose deadline.** Parent `followers_v8_352`:
   0.30, 0.55, 0.74. Does school move the tight band, and do near misses (0.26) and "at
   the enemy instead" (0.21) fall?
2. **Sweep, one ship alone:** in time at allowances of 2 to 8 (parent 0.06, 0.23, 0.43,
   0.69), and against itself with the deadline inputs zeroed.
3. **`drill_goto_missed` through the night**: does it fall this time?
4. **WAR for the live ten, the parents and tonight's three:** what school costs in combat.
5. Attack and defend flips: do they fade when go-to is most of the drills?

Nothing is published or archived by the morning script.
