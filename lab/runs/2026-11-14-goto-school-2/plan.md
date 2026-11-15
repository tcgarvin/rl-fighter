# Go-to school, second night

Prepared 2026-11-14, 23:20. Still the pilots' turn. The owner went to bed without naming
a run or an end time, so this was chosen from last night's results. Training stops at
06:30 and the morning script should be off the machine by about 08:30.

## Why

The first night of go-to school (`lab/runs/2026-11-14-goto-school`) answered its
question. More go-to drills teach a squad to make the deadline, and more pay alone does
less:

| Pilot | Go-to drills, in time | Tight deadlines | One ship alone, allowance 2 |
|---|---|---|---|
| `followers_v8_352` (parent) | 0.51 | 0.30 | 0.06 |
| `followers_school_600` (more drills, pay 3) | 0.70 | 0.60 | 0.12 |
| `followers_pay3_810` (pay 3 only) | 0.59 | 0.46 | 0.09 |
| `fighters_v8_500` (unchanged, second night) | 0.50 | 0.42 | 0.08 |

Three things are left open.

- **It was still improving when it stopped.** The share of ships that missed a deadline
  in training fell all night on every arm (school 0.34 to 0.24) and had not levelled off.
- **Two arms stopped early.** `followers_school` died at 05:09 and `fighters_v8` at 04:31
  on a fault in the drill generator: a far go-to route is placed by trial, and about one
  far drill in 6,700 found no place in 64 tries. School draws the most go-to drills, so it
  was the likeliest to hit it. Fixed (4,096 tries; a seed that found its route keeps it).
  So school got 248 updates where it could have had about 430.
- **A ship alone still fights first.** In the drills a lone ship is in time 0.41 against
  0.70 for all ships, and "at the enemy instead" 0.37 against 0.10. In the sweep, which is
  only lone ships, school moved 0.06 to 0.12 at an allowance of 2. One go-to drill in four
  is a lone ship, but that is only one ship in ten that flies a go-to.

## Arms

Each continues one of last night's runs from its last checkpoint. Three arms, 5 threads
each.

| Arm | From | What changes |
|---|---|---|
| `followers_school` | `followers_school_600` | Nothing. A second night of school |
| `followers_solo` | `followers_school_600` | 7 go-to drills in 10 are a ship alone (`drill_goto_solo_share` 0.6) |
| `fighters_pay1_school` | `fighters_pay1_v8_351` | What `followers_school` got on its first night: drill share 0.7, go-to weighted 6 of 8, a deadline worth 3 |

- `followers_school`: does the squad number keep climbing, and does the lone ship follow
  with only more of the same?
- `followers_solo` against it: what lone-ship practice buys. Same pay, same share of
  drills. Its drills are smaller, so fewer of its training rows come from drills.
- `fighters_pay1_school`: does school work on a pilot that mostly ignores orders? Its
  parent is on the live page (+13.7), makes 0.31 of its go-to deadlines and flips with an
  attack order 0.26 of the time. It starts from the first v8 night, as `followers_school`
  did, so the two first nights of school compare like for like. Its commander share of
  matches stays at a third. The actor waits 10 updates while the critic learns what a
  go-to row is worth now. Not `fighters_v8_500`: after two nights on v8 it rates lowest
  of the fourteen (+9.4).
- New setting: `drill_goto_solo_share` in `pilots_v1` (`roster_overrides`). At 0 no extra
  number is drawn and every drill is what it was. The drill eval and the sweep keep 0.
- An arm that dies is started again from its last checkpoint, up to three times.

## What the morning reads

Baselines are the parents on the same drills and sweep seeds: `followers_school_600` in
last night's files (`lab/runs/2026-11-14-goto-school/eval/`,
`lab/population/2026-11-sim6/sweep/goto-school/`), `fighters_pay1_v8_351` in the first v8
night's (`lab/runs/2026-11-12-pilots-v8/eval/`, `.../sweep/first-v8-night/`).

1. **Go-to drills, in time**, all ships and the Solo column. Parent `followers_school_600`:
   0.70 and 0.41.
2. **Sweep, one ship alone**, at allowances 2 to 8 (parent 0.12, 0.22, 0.54, 0.73), and
   against itself with the deadline inputs zeroed. Last night seeing the deadline made
   school leave sooner and shoot less, but not arrive more.
3. **`drill_goto_missed` through the night.**
4. **WAR** for the live pilots, the two parents and tonight's three: what school costs in
   combat. Last night it cost nothing: `followers_school_600` rates +14.5 against its
   parent's +12.8 and beats it head to head (0.53).
5. Attack and defend flips: school raised them (0.72 to 0.86, 0.76 to 0.89) with fewer
   attack and defend drills. Does that hold?

The morning script publishes and archives nothing. The owner asked for the result to be
published and deployed when the night is over, so that follows by hand: the logbook entry,
the live list by this WAR, the site.
