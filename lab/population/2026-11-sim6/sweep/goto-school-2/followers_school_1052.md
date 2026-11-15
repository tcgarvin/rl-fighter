# Go-to deadline sweep: followers_school_1052

Pilot `policy:ppo_bc_1052.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.37 +/- 0.01 (449/1198)
- Arrival-time ratio, slack 8 over slack 1.5: 1.11 (median 13.3 s over 11.9 s, on the 21 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.10 at slack 1.5, 0.12 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +22.5 +/- 2.7, three +45.2 +/- 13.5. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.04 | - | 11.2 | 17.1 | 58.1 |
| 1 | 0.07 | - | 11.8 | 20.8 | 67.3 |
| 1.5 | 0.12 | - | 12.1 | 33.0 | 80.3 |
| 2 | 0.20 | - | 11.2 | 41.9 | 87.4 |
| 3 | 0.33 | - | 11.4 | 57.2 | 93.8 |
| 5 | 0.58 | 0.73 | 11.8 | 68.0 | 94.9 |
| 8 | 0.77 | 0.47 | 11.4 | 70.9 | 97.9 |
| none | 0.38 | 1.24 | 12.1 | 70.0 | 95.4 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.38 arrive by that rule, median time to arrive 31.0 s; 0.78 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.3 | 0.0 |
| 1 | 0.01 | - | - | 1.0 | 0.0 |
| 1.5 | 0.01 | - | - | 5.3 | 0.0 |
| 2 | 0.01 | - | - | 12.3 | 0.0 |
| 3 | 0.10 | - | - | 27.2 | 0.0 |
| 5 | 0.31 | - | - | 41.5 | 0.0 |
| 8 | 0.56 | 0.80 | 39.0 | 51.4 | 0.0 |
| none | 0.11 | 2.03 | 31.1 | 36.6 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.08 | - | 6.8 | 8.9 | 49.5 |
| 1 | 0.13 | - | 7.1 | 11.9 | 60.2 |
| 1.5 | 0.18 | - | 7.5 | 21.9 | 74.9 |
| 2 | 0.31 | - | 7.5 | 28.2 | 81.8 |
| 3 | 0.54 | 0.94 | 8.0 | 38.8 | 89.4 |
| 5 | 0.81 | 0.54 | 7.8 | 42.5 | 89.4 |
| 8 | 0.96 | 0.38 | 7.8 | 44.4 | 99.8 |
| none | 0.62 | 0.88 | 8.5 | 57.2 | 93.0 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.03 | - | 13.2 | 42.1 | 124.8 |
| 1 | 0.08 | - | 13.9 | 49.7 | 141.6 |
| 1.5 | 0.23 | - | 13.8 | 71.7 | 165.9 |
| 2 | 0.36 | - | 13.2 | 85.4 | 180.6 |
| 3 | 0.51 | 0.93 | 12.9 | 105.5 | 191.9 |
| 5 | 0.87 | 0.33 | 13.8 | 120.0 | 195.4 |
| 8 | 0.96 | 0.22 | 14.2 | 116.9 | 193.9 |
| none | 0.61 | 0.72 | 15.4 | 116.1 | 193.3 |

Killed before the deadline, by slack (of 324): 0.8 17, 1 26, 1.5 48, 2 60, 3 88, 5 110, 8 116, none 91.
