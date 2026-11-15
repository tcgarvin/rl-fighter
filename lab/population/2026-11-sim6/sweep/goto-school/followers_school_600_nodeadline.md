# Go-to deadline sweep: followers_school_600_nodeadline

Pilot `policy:ppo_bc_600.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.34 +/- 0.01 (414/1228)
- Arrival-time ratio, slack 8 over slack 1.5: 1.03 (median 11.9 s over 11.6 s, on the 24 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.09 at slack 1.5, 0.08 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +22.0 +/- 2.2, three +49.9 +/- 10.4. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 26.7 | 58.4 |
| 1 | 0.05 | - | 32.7 | 31.3 | 65.5 |
| 1.5 | 0.10 | - | 28.0 | 44.6 | 79.0 |
| 2 | 0.14 | - | 18.3 | 57.6 | 88.3 |
| 3 | 0.29 | - | 15.2 | 74.2 | 94.8 |
| 5 | 0.53 | 0.95 | 14.7 | 82.5 | 97.1 |
| 8 | 0.74 | 0.59 | 14.7 | 89.1 | 98.8 |
| none | 0.27 | 1.53 | 14.7 | 71.8 | 94.8 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.27 arrive by that rule, median time to arrive 35.5 s; 0.80 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.2 | 0.0 |
| 1 | 0.02 | - | - | 1.1 | 0.0 |
| 1.5 | 0.03 | - | - | 5.9 | 0.0 |
| 2 | 0.04 | - | - | 15.7 | 0.0 |
| 3 | 0.06 | - | - | 33.6 | 0.0 |
| 5 | 0.26 | - | 34.1 | 53.2 | 0.0 |
| 8 | 0.56 | 0.89 | 30.5 | 67.5 | 0.0 |
| none | 0.03 | 2.02 | 28.6 | 35.2 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.03 | - | 11.4 | 26.3 | 53.7 |
| 1 | 0.08 | - | 11.1 | 31.0 | 59.6 |
| 1.5 | 0.18 | - | 10.4 | 39.5 | 73.8 |
| 2 | 0.22 | - | 10.4 | 50.3 | 85.7 |
| 3 | 0.52 | 0.97 | 10.4 | 57.9 | 90.2 |
| 5 | 0.80 | 0.59 | 10.4 | 58.5 | 90.1 |
| 8 | 0.91 | 0.41 | 10.4 | 61.5 | 94.2 |
| none | 0.52 | 1.00 | 10.4 | 59.6 | 89.3 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 53.6 | 121.6 |
| 1 | 0.03 | - | - | 61.8 | 136.9 |
| 1.5 | 0.11 | - | - | 88.4 | 163.1 |
| 2 | 0.19 | - | 31.4 | 106.7 | 179.3 |
| 3 | 0.38 | - | 47.0 | 131.0 | 194.3 |
| 5 | 0.74 | 0.40 | - | 135.7 | 201.2 |
| 8 | 0.94 | 0.23 | - | 138.3 | 202.2 |
| none | 0.36 | - | - | 120.7 | 195.1 |

Killed before the deadline, by slack (of 324): 0.8 10, 1 16, 1.5 37, 2 59, 3 87, 5 101, 8 108, none 88.
