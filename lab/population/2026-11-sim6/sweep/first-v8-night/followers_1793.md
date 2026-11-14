# Go-to deadline sweep: followers_1793

Pilot `policy:ppo_bc_1793.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.27 +/- 0.01 (333/1222)
- Arrival-time ratio, slack 8 over slack 1.5: 1.01 (median 9.2 s over 9.2 s, on the 9 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.05 at slack 1.5, 0.03 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +28.4 +/- 2.7, three +74.7 +/- 14.2. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 23.9 | 57.8 |
| 1 | 0.02 | - | - | 29.3 | 65.6 |
| 1.5 | 0.05 | - | - | 42.6 | 78.0 |
| 2 | 0.08 | - | 26.0 | 55.2 | 86.9 |
| 3 | 0.21 | - | 24.2 | 77.0 | 94.9 |
| 5 | 0.46 | - | 21.1 | 89.0 | 100.0 |
| 8 | 0.66 | 0.68 | 19.9 | 97.4 | 100.8 |
| none | 0.23 | 1.58 | 19.9 | 76.8 | 96.3 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.23 arrive by that rule, median time to arrive 37.4 s; 0.76 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.4 | 0.0 |
| 1 | 0.01 | - | - | 2.0 | 0.0 |
| 1.5 | 0.01 | - | - | 11.2 | 0.0 |
| 2 | 0.01 | - | - | 22.2 | 0.0 |
| 3 | 0.07 | - | - | 43.4 | 0.0 |
| 5 | 0.30 | - | 39.8 | 59.5 | 0.0 |
| 8 | 0.51 | 0.97 | 36.3 | 72.7 | 0.0 |
| none | 0.04 | 2.02 | 31.6 | 44.8 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | 13.1 | 15.7 | 47.7 |
| 1 | 0.04 | - | 12.6 | 18.8 | 56.9 |
| 1.5 | 0.11 | - | 11.4 | 28.4 | 66.3 |
| 2 | 0.14 | - | 10.8 | 37.9 | 79.1 |
| 3 | 0.36 | - | 10.7 | 49.6 | 86.6 |
| 5 | 0.64 | 0.79 | 10.7 | 55.0 | 94.9 |
| 8 | 0.83 | 0.48 | 10.7 | 56.7 | 96.5 |
| none | 0.41 | 1.16 | 10.7 | 50.5 | 91.1 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 55.8 | 125.5 |
| 1 | 0.00 | - | - | 67.1 | 139.8 |
| 1.5 | 0.03 | - | - | 88.1 | 167.7 |
| 2 | 0.10 | - | - | 105.4 | 181.6 |
| 3 | 0.22 | - | - | 138.0 | 198.2 |
| 5 | 0.56 | 0.56 | - | 152.5 | 204.9 |
| 8 | 0.71 | 0.38 | - | 162.9 | 205.8 |
| none | 0.31 | - | - | 135.1 | 197.8 |

Killed before the deadline, by slack (of 324): 0.8 19, 1 24, 1.5 41, 2 65, 3 84, 5 102, 8 106, none 88.
