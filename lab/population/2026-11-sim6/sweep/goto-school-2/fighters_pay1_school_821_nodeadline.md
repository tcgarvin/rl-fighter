# Go-to deadline sweep: fighters_pay1_school_821_nodeadline

Pilot `policy:ppo_bc_821.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.34 +/- 0.01 (441/1282)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 7.1 s over 7.1 s, on the 8 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.04 at slack 1.5, 0.03 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +10.5 +/- 1.8, three +67.0 +/- 14.8. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 40.4 | 56.8 |
| 1 | 0.01 | - | - | 49.3 | 63.0 |
| 1.5 | 0.04 | - | - | 74.3 | 73.2 |
| 2 | 0.12 | - | - | 89.3 | 79.6 |
| 3 | 0.29 | - | 22.0 | 101.4 | 86.1 |
| 5 | 0.59 | 0.88 | 20.9 | 113.0 | 87.1 |
| 8 | 0.78 | 0.52 | 19.8 | 117.8 | 87.7 |
| none | 0.32 | 1.42 | 19.8 | 106.8 | 85.7 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.32 arrive by that rule, median time to arrive 33.5 s; 0.85 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 4.2 | 0.0 |
| 1 | 0.02 | - | - | 8.9 | 0.0 |
| 1.5 | 0.03 | - | - | 26.4 | 0.0 |
| 2 | 0.04 | - | - | 42.2 | 0.0 |
| 3 | 0.15 | - | 54.5 | 57.4 | 0.0 |
| 5 | 0.43 | - | 26.1 | 72.4 | 0.0 |
| 8 | 0.60 | 0.73 | 24.7 | 79.6 | 0.0 |
| none | 0.08 | 1.81 | 24.6 | 65.4 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 50.4 | 44.4 |
| 1 | 0.01 | - | - | 56.1 | 48.4 |
| 1.5 | 0.07 | - | 17.0 | 66.1 | 56.5 |
| 2 | 0.22 | - | 14.8 | 70.7 | 57.4 |
| 3 | 0.49 | - | 14.6 | 74.0 | 60.1 |
| 5 | 0.73 | 0.60 | 13.9 | 76.4 | 60.2 |
| 8 | 0.92 | 0.36 | 13.9 | 76.6 | 60.3 |
| none | 0.58 | 0.92 | 13.9 | 76.1 | 60.1 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 66.6 | 126.0 |
| 1 | 0.01 | - | - | 82.7 | 140.5 |
| 1.5 | 0.03 | - | - | 130.3 | 163.1 |
| 2 | 0.10 | - | - | 155.0 | 181.3 |
| 3 | 0.17 | - | 43.8 | 172.7 | 198.4 |
| 5 | 0.76 | 0.71 | - | 190.1 | 201.2 |
| 8 | 1.00 | 0.42 | 51.0 | 197.3 | 202.8 |
| none | 0.20 | 1.70 | 50.5 | 179.0 | 197.1 |

Killed before the deadline, by slack (of 324): 0.8 6, 1 15, 1.5 33, 2 52, 3 76, 5 85, 8 92, none 80.
