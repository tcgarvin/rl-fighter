# Go-to deadline sweep: fighters_pay1_1317

Pilot `policy:ppo_bc_1317.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.09 +/- 0.01 (104/1175)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 4.6 s over 4.6 s, on the 2 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.01 at slack 1.5, 0.01 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +10.9 +/- 2.5, three +89.4 +/- 17.0. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 42.5 | 60.6 |
| 1 | 0.01 | - | - | 52.1 | 65.5 |
| 1.5 | 0.01 | - | - | 75.0 | 75.9 |
| 2 | 0.02 | - | - | 93.4 | 79.6 |
| 3 | 0.05 | - | - | 104.7 | 86.3 |
| 5 | 0.17 | - | - | 117.7 | 87.3 |
| 8 | 0.22 | - | 47.4 | 126.1 | 86.2 |
| none | 0.04 | - | 42.0 | 108.7 | 86.0 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.04 arrive by that rule, median time to arrive - s; 0.23 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 2.8 | 0.0 |
| 1 | 0.01 | - | - | 6.6 | 0.0 |
| 1.5 | 0.01 | - | - | 24.9 | 0.0 |
| 2 | 0.01 | - | - | 40.4 | 0.0 |
| 3 | 0.04 | - | - | 54.0 | 0.0 |
| 5 | 0.10 | - | 42.4 | 66.4 | 0.0 |
| 8 | 0.16 | - | 41.4 | 78.1 | 0.0 |
| none | 0.01 | - | 34.4 | 59.1 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 42.7 | 52.1 |
| 1 | 0.01 | - | - | 47.4 | 55.3 |
| 1.5 | 0.02 | - | - | 55.8 | 64.5 |
| 2 | 0.04 | - | - | 60.5 | 64.7 |
| 3 | 0.08 | - | 49.5 | 65.4 | 70.0 |
| 5 | 0.25 | - | 23.4 | 68.5 | 71.9 |
| 8 | 0.31 | - | 22.7 | 66.6 | 73.8 |
| none | 0.08 | - | 24.0 | 67.5 | 70.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 82.1 | 129.7 |
| 1 | 0.00 | - | - | 102.4 | 141.2 |
| 1.5 | 0.00 | - | - | 144.3 | 163.2 |
| 2 | 0.02 | - | - | 179.2 | 174.1 |
| 3 | 0.00 | - | - | 194.8 | 189.1 |
| 5 | 0.20 | - | - | 218.3 | 190.0 |
| 8 | 0.18 | - | - | 233.7 | 184.9 |
| none | 0.06 | - | - | 199.5 | 187.2 |

Killed before the deadline, by slack (of 324): 0.8 28, 1 38, 1.5 66, 2 73, 3 92, 5 106, 8 108, none 98.
