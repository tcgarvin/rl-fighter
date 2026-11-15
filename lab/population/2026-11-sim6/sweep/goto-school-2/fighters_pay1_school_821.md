# Go-to deadline sweep: fighters_pay1_school_821

Pilot `policy:ppo_bc_821.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.34 +/- 0.01 (436/1292)
- Arrival-time ratio, slack 8 over slack 1.5: 1.03 (median 3.4 s over 3.3 s, on the 2 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.02 at slack 1.5, 0.04 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +21.9 +/- 2.6, three +95.0 +/- 18.0. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 31.9 | 55.9 |
| 1 | 0.01 | - | - | 41.2 | 62.2 |
| 1.5 | 0.02 | - | - | 67.2 | 74.3 |
| 2 | 0.12 | - | 41.4 | 83.4 | 78.8 |
| 3 | 0.29 | - | 22.1 | 98.4 | 86.0 |
| 5 | 0.58 | 0.83 | 20.4 | 127.3 | 87.7 |
| 8 | 0.78 | 0.59 | 19.1 | 124.9 | 87.6 |
| none | 0.32 | 1.42 | 19.8 | 106.8 | 85.7 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.32 arrive by that rule, median time to arrive 33.5 s; 0.85 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 3.6 | 0.0 |
| 1 | 0.02 | - | - | 8.6 | 0.0 |
| 1.5 | 0.02 | - | - | 23.6 | 0.0 |
| 2 | 0.03 | - | - | 36.7 | 0.0 |
| 3 | 0.14 | - | - | 53.6 | 0.0 |
| 5 | 0.42 | - | 33.4 | 67.8 | 0.0 |
| 8 | 0.61 | 0.73 | 26.6 | 79.8 | 0.0 |
| none | 0.08 | 1.81 | 24.6 | 65.4 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 33.7 | 45.1 |
| 1 | 0.00 | - | - | 41.9 | 49.4 |
| 1.5 | 0.04 | - | 15.9 | 55.9 | 58.0 |
| 2 | 0.24 | - | 16.9 | 65.5 | 59.0 |
| 3 | 0.45 | - | 14.5 | 73.6 | 64.4 |
| 5 | 0.73 | 0.65 | 14.9 | 76.7 | 67.3 |
| 8 | 0.92 | 0.47 | 14.8 | 77.8 | 67.0 |
| none | 0.58 | 0.92 | 13.9 | 76.1 | 60.1 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | 20.1 | 58.2 | 122.7 |
| 1 | 0.01 | - | 16.5 | 73.1 | 137.1 |
| 1.5 | 0.01 | - | 19.6 | 122.1 | 164.9 |
| 2 | 0.07 | - | 24.7 | 147.8 | 177.5 |
| 3 | 0.27 | - | 23.7 | 168.1 | 193.6 |
| 5 | 0.70 | 0.67 | 19.1 | 237.3 | 195.8 |
| 8 | 0.88 | 0.47 | 16.3 | 217.2 | 195.7 |
| none | 0.20 | 1.70 | 50.5 | 179.0 | 197.1 |

Killed before the deadline, by slack (of 324): 0.8 2, 1 11, 1.5 34, 2 49, 3 73, 5 88, 8 84, none 80.
