# Go-to deadline sweep: fighters_pay1_v8_351_nodeadline

Pilot `policy:ppo_bc_351.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.16 +/- 0.01 (195/1212)
- Arrival-time ratio, slack 8 over slack 1.5: 0.99 (median 7.2 s over 7.3 s, on the 4 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.02 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +8.4 +/- 1.3, three +58.5 +/- 15.4. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 40.2 | 62.5 |
| 1 | 0.01 | - | - | 46.6 | 69.0 |
| 1.5 | 0.02 | - | - | 67.6 | 78.4 |
| 2 | 0.05 | - | - | 81.7 | 82.2 |
| 3 | 0.12 | - | - | 92.7 | 86.9 |
| 5 | 0.29 | - | 25.1 | 104.6 | 89.4 |
| 8 | 0.37 | - | 23.6 | 106.7 | 89.3 |
| none | 0.11 | - | 23.6 | 98.9 | 88.2 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.11 arrive by that rule, median time to arrive - s; 0.48 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 4.8 | 0.0 |
| 1 | 0.01 | - | - | 9.3 | 0.0 |
| 1.5 | 0.01 | - | - | 29.3 | 0.0 |
| 2 | 0.01 | - | - | 43.9 | 0.0 |
| 3 | 0.06 | - | 42.8 | 59.5 | 0.0 |
| 5 | 0.31 | - | 23.4 | 73.1 | 0.0 |
| 8 | 0.39 | - | 22.6 | 79.7 | 0.0 |
| none | 0.05 | 2.53 | 22.6 | 65.6 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 54.7 | 52.3 |
| 1 | 0.01 | - | - | 60.3 | 55.8 |
| 1.5 | 0.03 | - | - | 68.7 | 60.2 |
| 2 | 0.10 | - | 20.0 | 73.1 | 62.4 |
| 3 | 0.20 | - | 16.9 | 75.5 | 63.3 |
| 5 | 0.26 | - | 17.1 | 76.9 | 64.6 |
| 8 | 0.35 | - | 16.9 | 77.1 | 64.3 |
| none | 0.18 | - | 16.9 | 77.0 | 64.3 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 61.1 | 135.1 |
| 1 | 0.00 | - | - | 70.0 | 151.1 |
| 1.5 | 0.02 | - | - | 104.8 | 175.1 |
| 2 | 0.02 | - | - | 128.0 | 184.1 |
| 3 | 0.07 | - | - | 143.1 | 197.5 |
| 5 | 0.31 | - | - | 163.9 | 203.8 |
| 8 | 0.36 | - | - | 163.3 | 203.5 |
| none | 0.12 | - | - | 154.3 | 200.2 |

Killed before the deadline, by slack (of 324): 0.8 23, 1 35, 1.5 62, 2 69, 3 81, 5 97, 8 99, none 87.
