# Go-to deadline sweep: fighters_1832

Pilot `policy:ppo_bc_1832.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.15 +/- 0.01 (186/1230)
- Arrival-time ratio, slack 8 over slack 1.5: 0.96 (median 9.0 s over 9.4 s, on the 3 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.02 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +8.6 +/- 2.0, three +83.9 +/- 15.1. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 41.6 | 60.2 |
| 1 | 0.01 | - | - | 50.1 | 67.6 |
| 1.5 | 0.03 | - | - | 67.7 | 77.8 |
| 2 | 0.04 | - | - | 78.9 | 83.2 |
| 3 | 0.09 | - | - | 99.8 | 89.9 |
| 5 | 0.25 | - | 34.5 | 109.6 | 91.4 |
| 8 | 0.40 | - | 30.2 | 117.4 | 90.0 |
| none | 0.08 | - | 30.3 | 99.6 | 88.9 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.08 arrive by that rule, median time to arrive - s; 0.22 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 2.9 | 0.0 |
| 1 | 0.02 | - | - | 6.3 | 0.0 |
| 1.5 | 0.02 | - | - | 22.7 | 0.0 |
| 2 | 0.02 | - | - | 38.2 | 0.0 |
| 3 | 0.04 | - | - | 56.1 | 0.0 |
| 5 | 0.16 | - | 47.9 | 68.6 | 0.0 |
| 8 | 0.31 | - | 36.6 | 79.5 | 0.0 |
| none | 0.01 | - | 33.8 | 60.9 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 52.8 | 53.7 |
| 1 | 0.00 | - | - | 57.6 | 57.0 |
| 1.5 | 0.04 | - | - | 67.7 | 62.9 |
| 2 | 0.05 | - | - | 70.8 | 65.3 |
| 3 | 0.09 | - | 28.0 | 73.6 | 67.8 |
| 5 | 0.27 | - | 22.3 | 77.1 | 69.3 |
| 8 | 0.45 | - | 19.8 | 76.3 | 68.2 |
| none | 0.11 | - | 24.4 | 75.6 | 68.9 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 69.1 | 126.9 |
| 1 | 0.01 | - | - | 86.4 | 145.7 |
| 1.5 | 0.03 | - | - | 112.6 | 170.6 |
| 2 | 0.09 | - | - | 127.6 | 184.3 |
| 3 | 0.24 | - | - | 169.6 | 202.0 |
| 5 | 0.57 | 0.65 | - | 183.0 | 205.0 |
| 8 | 0.68 | 0.49 | 60.3 | 196.5 | 201.7 |
| none | 0.22 | - | - | 162.4 | 197.8 |

Killed before the deadline, by slack (of 324): 0.8 9, 1 19, 1.5 47, 2 63, 3 85, 5 91, 8 104, none 82.
