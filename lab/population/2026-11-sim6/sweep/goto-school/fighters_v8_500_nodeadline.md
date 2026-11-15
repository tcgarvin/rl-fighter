# Go-to deadline sweep: fighters_v8_500_nodeadline

Pilot `policy:ppo_bc_500.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.21 +/- 0.01 (238/1127)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 10.7 s over 10.7 s, on the 4 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.01 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +15.9 +/- 2.0, three +62.1 +/- 13.8. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 38.5 | 63.4 |
| 1 | 0.00 | - | - | 46.4 | 70.8 |
| 1.5 | 0.02 | - | - | 66.4 | 83.9 |
| 2 | 0.04 | - | - | 79.5 | 90.2 |
| 3 | 0.14 | - | - | 94.1 | 96.3 |
| 5 | 0.40 | - | 28.4 | 104.2 | 97.4 |
| 8 | 0.59 | 0.80 | 29.4 | 109.5 | 98.2 |
| none | 0.14 | 2.09 | 28.2 | 97.3 | 96.7 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.14 arrive by that rule, median time to arrive 52.9 s; 0.67 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 4.4 | 0.0 |
| 1 | 0.01 | - | - | 7.1 | 0.0 |
| 1.5 | 0.02 | - | - | 23.5 | 0.0 |
| 2 | 0.02 | - | - | 33.7 | 0.0 |
| 3 | 0.14 | - | - | 51.1 | 0.0 |
| 5 | 0.37 | - | 42.0 | 66.2 | 0.0 |
| 8 | 0.55 | 0.85 | 34.6 | 74.8 | 0.0 |
| none | 0.08 | 2.13 | 31.4 | 53.3 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 40.3 | 59.7 |
| 1 | 0.00 | - | - | 45.7 | 65.6 |
| 1.5 | 0.00 | - | - | 54.3 | 75.6 |
| 2 | 0.02 | - | - | 59.8 | 82.1 |
| 3 | 0.10 | - | 26.7 | 66.0 | 86.5 |
| 5 | 0.35 | - | 24.2 | 68.6 | 89.8 |
| 8 | 0.58 | 0.87 | 22.6 | 70.2 | 90.7 |
| none | 0.19 | 1.95 | 22.6 | 67.9 | 89.1 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 70.9 | 130.7 |
| 1 | 0.00 | - | 24.0 | 86.6 | 146.9 |
| 1.5 | 0.03 | - | - | 121.3 | 176.1 |
| 2 | 0.11 | - | 34.6 | 144.9 | 188.4 |
| 3 | 0.21 | - | 48.5 | 165.1 | 202.3 |
| 5 | 0.80 | 0.70 | 30.2 | 177.8 | 202.5 |
| 8 | 0.94 | 0.47 | 40.4 | 183.4 | 203.8 |
| none | 0.26 | 1.71 | 42.4 | 170.7 | 201.0 |

Killed before the deadline, by slack (of 324): 0.8 11, 1 25, 1.5 60, 2 80, 3 102, 5 124, 8 127, none 113.
