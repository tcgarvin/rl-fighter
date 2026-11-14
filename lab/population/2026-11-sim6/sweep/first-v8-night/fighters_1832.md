# Go-to deadline sweep: fighters_1832

Pilot `policy:ppo_bc_1832.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.14 +/- 0.01 (173/1233)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 6.5 s over 6.5 s, on the 3 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.01 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +10.4 +/- 1.8, three +73.3 +/- 14.8. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 41.6 | 59.6 |
| 1 | 0.00 | - | - | 49.8 | 66.7 |
| 1.5 | 0.01 | - | - | 70.4 | 76.1 |
| 2 | 0.03 | - | - | 81.6 | 82.7 |
| 3 | 0.11 | - | - | 103.3 | 87.5 |
| 5 | 0.20 | - | 29.8 | 112.6 | 89.5 |
| 8 | 0.40 | - | 30.2 | 117.4 | 90.0 |
| none | 0.11 | - | 28.6 | 105.8 | 88.3 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.11 arrive by that rule, median time to arrive - s; 0.50 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 2.4 | 0.0 |
| 1 | 0.01 | - | - | 6.3 | 0.0 |
| 1.5 | 0.01 | - | - | 22.0 | 0.0 |
| 2 | 0.01 | - | - | 38.6 | 0.0 |
| 3 | 0.05 | - | - | 57.0 | 0.0 |
| 5 | 0.13 | - | 43.0 | 67.2 | 0.0 |
| 8 | 0.31 | - | 36.6 | 79.5 | 0.0 |
| none | 0.02 | - | 33.6 | 59.9 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 52.3 | 53.4 |
| 1 | 0.00 | - | - | 57.8 | 56.1 |
| 1.5 | 0.01 | - | - | 65.9 | 61.2 |
| 2 | 0.04 | - | - | 69.9 | 65.3 |
| 3 | 0.14 | - | 27.2 | 73.7 | 67.6 |
| 5 | 0.21 | - | 20.0 | 75.7 | 68.0 |
| 8 | 0.45 | - | 19.8 | 76.3 | 68.2 |
| none | 0.16 | 2.78 | 19.8 | 75.4 | 67.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 69.9 | 125.5 |
| 1 | 0.00 | - | - | 85.2 | 144.1 |
| 1.5 | 0.03 | - | - | 123.2 | 167.0 |
| 2 | 0.09 | - | - | 136.1 | 182.7 |
| 3 | 0.20 | - | - | 179.3 | 195.0 |
| 5 | 0.55 | 0.77 | - | 194.9 | 200.4 |
| 8 | 0.68 | 0.49 | 60.3 | 196.5 | 201.7 |
| none | 0.24 | - | 58.5 | 182.1 | 197.1 |

Killed before the deadline, by slack (of 324): 0.8 9, 1 18, 1.5 39, 2 65, 3 82, 5 97, 8 104, none 87.
