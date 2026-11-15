# Go-to deadline sweep: followers_school_1052_nodeadline

Pilot `policy:ppo_bc_1052.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.38 +/- 0.01 (469/1223)
- Arrival-time ratio, slack 8 over slack 1.5: 1.12 (median 13.9 s over 12.4 s, on the 33 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.13 at slack 1.5, 0.11 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +20.9 +/- 2.1, three +30.0 +/- 7.1. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.04 | - | 14.9 | 27.0 | 59.8 |
| 1 | 0.07 | - | 14.4 | 33.2 | 66.9 |
| 1.5 | 0.15 | - | 12.3 | 46.9 | 79.5 |
| 2 | 0.20 | - | 13.2 | 55.7 | 86.4 |
| 3 | 0.36 | - | 12.3 | 68.8 | 94.0 |
| 5 | 0.60 | 0.76 | 12.1 | 77.3 | 96.8 |
| 8 | 0.72 | 0.47 | 12.1 | 81.3 | 98.0 |
| none | 0.38 | 1.24 | 12.1 | 70.0 | 95.4 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.38 arrive by that rule, median time to arrive 31.0 s; 0.78 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 0.6 | 0.0 |
| 1 | 0.04 | - | - | 1.7 | 0.0 |
| 1.5 | 0.05 | - | - | 6.9 | 0.0 |
| 2 | 0.06 | - | - | 17.4 | 0.0 |
| 3 | 0.13 | - | - | 34.4 | 0.0 |
| 5 | 0.35 | - | 47.6 | 46.9 | 0.0 |
| 8 | 0.47 | - | 36.3 | 59.1 | 0.0 |
| none | 0.11 | 2.03 | 31.1 | 36.6 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.08 | - | 9.2 | 20.2 | 52.1 |
| 1 | 0.12 | - | 8.9 | 24.3 | 58.6 |
| 1.5 | 0.24 | - | 8.6 | 37.8 | 72.8 |
| 2 | 0.30 | - | 8.5 | 45.4 | 81.6 |
| 3 | 0.58 | 0.87 | 8.5 | 52.4 | 88.0 |
| 5 | 0.82 | 0.57 | 8.5 | 57.3 | 95.0 |
| 8 | 0.93 | 0.37 | 8.5 | 58.6 | 97.0 |
| none | 0.62 | 0.88 | 8.5 | 57.2 | 93.0 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | 16.6 | 60.3 | 127.2 |
| 1 | 0.03 | - | 16.4 | 73.5 | 142.2 |
| 1.5 | 0.17 | - | 15.9 | 96.1 | 165.8 |
| 2 | 0.29 | - | 15.6 | 104.2 | 177.6 |
| 3 | 0.46 | - | 15.4 | 119.6 | 194.0 |
| 5 | 0.91 | 0.36 | 15.4 | 127.9 | 195.4 |
| 8 | 1.00 | 0.23 | 15.4 | 126.1 | 197.0 |
| none | 0.61 | 0.72 | 15.4 | 116.1 | 193.3 |

Killed before the deadline, by slack (of 324): 0.8 15, 1 20, 1.5 41, 2 61, 3 85, 5 100, 8 110, none 91.
