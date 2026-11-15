# Go-to deadline sweep: followers_school_600

Pilot `policy:ppo_bc_600.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.31 +/- 0.01 (373/1211)
- Arrival-time ratio, slack 8 over slack 1.5: 1.01 (median 12.7 s over 12.7 s, on the 16 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.08 at slack 1.5, 0.07 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +35.5 +/- 2.9, three +58.9 +/- 9.7. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | 77.9 | 14.6 | 56.6 |
| 1 | 0.03 | - | 21.9 | 18.9 | 65.2 |
| 1.5 | 0.09 | - | 18.1 | 30.9 | 78.8 |
| 2 | 0.12 | - | 15.5 | 43.7 | 88.6 |
| 3 | 0.22 | - | 15.0 | 59.5 | 95.9 |
| 5 | 0.54 | 0.89 | 16.4 | 71.5 | 101.1 |
| 8 | 0.73 | 0.60 | 15.2 | 81.7 | 102.7 |
| none | 0.27 | 1.53 | 14.7 | 71.8 | 94.8 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.27 arrive by that rule, median time to arrive 35.5 s; 0.80 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.2 | 0.0 |
| 1 | 0.01 | - | - | 0.2 | 0.0 |
| 1.5 | 0.02 | - | - | 2.6 | 0.0 |
| 2 | 0.02 | - | - | 7.2 | 0.0 |
| 3 | 0.04 | - | - | 21.8 | 0.0 |
| 5 | 0.29 | - | 48.1 | 45.3 | 0.0 |
| 8 | 0.58 | 0.90 | 32.3 | 60.7 | 0.0 |
| none | 0.03 | 2.02 | 28.6 | 35.2 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.03 | - | 9.4 | 10.4 | 50.3 |
| 1 | 0.06 | - | 9.6 | 13.4 | 58.3 |
| 1.5 | 0.17 | - | 9.1 | 23.5 | 72.7 |
| 2 | 0.21 | - | 9.0 | 38.6 | 81.2 |
| 3 | 0.38 | - | 9.2 | 46.9 | 93.0 |
| 5 | 0.75 | 0.67 | 9.4 | 56.3 | 100.2 |
| 8 | 0.88 | 0.42 | 9.5 | 59.0 | 100.7 |
| none | 0.52 | 1.00 | 10.4 | 59.6 | 89.3 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 33.1 | 119.7 |
| 1 | 0.02 | - | - | 43.0 | 137.2 |
| 1.5 | 0.07 | - | - | 66.6 | 163.6 |
| 2 | 0.14 | - | - | 85.2 | 184.5 |
| 3 | 0.32 | - | - | 109.7 | 194.7 |
| 5 | 0.95 | 0.43 | 27.3 | 113.0 | 203.2 |
| 8 | 0.92 | 0.29 | 30.1 | 125.5 | 207.5 |
| none | 0.36 | - | - | 120.7 | 195.1 |

Killed before the deadline, by slack (of 324): 0.8 14, 1 22, 1.5 35, 2 61, 3 85, 5 111, 8 117, none 88.
