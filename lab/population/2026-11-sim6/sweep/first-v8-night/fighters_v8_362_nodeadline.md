# Go-to deadline sweep: fighters_v8_362_nodeadline

Pilot `policy:ppo_bc_362.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.15 +/- 0.01 (174/1140)
- Arrival-time ratio, slack 8 over slack 1.5: 1.02 (median 24.2 s over 23.8 s, on the 6 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.02 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +15.1 +/- 2.1, three +53.2 +/- 13.5. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 36.4 | 62.6 |
| 1 | 0.01 | - | - | 45.0 | 70.4 |
| 1.5 | 0.03 | - | - | 58.5 | 82.1 |
| 2 | 0.05 | - | - | 68.9 | 87.9 |
| 3 | 0.10 | - | - | 84.3 | 92.1 |
| 5 | 0.22 | - | 37.5 | 95.5 | 93.5 |
| 8 | 0.40 | - | 28.9 | 99.0 | 94.0 |
| none | 0.11 | - | 28.0 | 87.2 | 92.4 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.11 arrive by that rule, median time to arrive - s; 0.46 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 2.8 | 0.0 |
| 1 | 0.01 | - | - | 7.2 | 0.0 |
| 1.5 | 0.01 | - | - | 20.1 | 0.0 |
| 2 | 0.01 | - | - | 33.8 | 0.0 |
| 3 | 0.05 | - | - | 49.9 | 0.0 |
| 5 | 0.15 | - | 44.0 | 63.2 | 0.0 |
| 8 | 0.31 | - | 33.2 | 73.3 | 0.0 |
| none | 0.04 | - | 32.0 | 54.9 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 47.8 | 57.0 |
| 1 | 0.01 | - | - | 51.5 | 61.1 |
| 1.5 | 0.06 | - | - | 59.7 | 68.5 |
| 2 | 0.10 | - | - | 64.4 | 72.9 |
| 3 | 0.13 | - | 27.4 | 69.6 | 77.6 |
| 5 | 0.28 | - | 23.5 | 74.0 | 77.9 |
| 8 | 0.49 | - | 22.4 | 74.8 | 78.2 |
| none | 0.16 | - | 22.4 | 73.4 | 77.3 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 58.4 | 130.7 |
| 1 | 0.00 | - | - | 76.5 | 150.1 |
| 1.5 | 0.00 | - | - | 95.8 | 177.7 |
| 2 | 0.05 | - | - | 108.6 | 190.7 |
| 3 | 0.25 | - | - | 133.4 | 198.7 |
| 5 | 0.43 | - | - | 149.2 | 202.4 |
| 8 | 0.60 | 0.48 | - | 148.9 | 203.9 |
| none | 0.25 | 2.09 | - | 133.2 | 199.8 |

Killed before the deadline, by slack (of 324): 0.8 13, 1 25, 1.5 69, 2 82, 3 100, 5 115, 8 114, none 102.
