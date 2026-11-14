# Go-to deadline sweep: fighters_pay1_v8_351

Pilot `policy:ppo_bc_351.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.19 +/- 0.01 (235/1210)
- Arrival-time ratio, slack 8 over slack 1.5: 0.89 (median 3.8 s over 4.3 s, on the 2 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.01 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +18.0 +/- 2.7, three +51.1 +/- 16.2. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 31.9 | 63.8 |
| 1 | 0.01 | - | - | 39.3 | 69.7 |
| 1.5 | 0.02 | - | - | 56.7 | 79.2 |
| 2 | 0.05 | - | - | 71.6 | 86.2 |
| 3 | 0.13 | - | - | 85.9 | 88.4 |
| 5 | 0.33 | - | 26.3 | 100.2 | 92.2 |
| 8 | 0.49 | - | 25.0 | 101.1 | 91.3 |
| none | 0.11 | - | 23.6 | 98.9 | 88.2 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.11 arrive by that rule, median time to arrive - s; 0.48 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 2.2 | 0.0 |
| 1 | 0.01 | - | - | 4.5 | 0.0 |
| 1.5 | 0.01 | - | - | 12.8 | 0.0 |
| 2 | 0.01 | - | - | 26.5 | 0.0 |
| 3 | 0.07 | - | - | 43.0 | 0.0 |
| 5 | 0.29 | - | 25.4 | 64.9 | 0.0 |
| 8 | 0.46 | - | 23.5 | 77.2 | 0.0 |
| none | 0.05 | 2.53 | 22.6 | 65.6 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 35.4 | 58.1 |
| 1 | 0.01 | - | - | 42.9 | 63.7 |
| 1.5 | 0.01 | - | - | 58.3 | 69.2 |
| 2 | 0.10 | - | 27.9 | 65.4 | 70.6 |
| 3 | 0.21 | - | 20.1 | 75.2 | 69.9 |
| 5 | 0.40 | - | 15.6 | 78.5 | 69.8 |
| 8 | 0.51 | 0.96 | 16.9 | 76.3 | 72.3 |
| none | 0.18 | - | 16.9 | 77.0 | 64.3 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 58.0 | 133.1 |
| 1 | 0.01 | - | - | 70.5 | 145.5 |
| 1.5 | 0.04 | - | - | 98.8 | 168.3 |
| 2 | 0.05 | - | - | 122.9 | 187.9 |
| 3 | 0.06 | - | - | 139.4 | 195.2 |
| 5 | 0.20 | - | - | 157.2 | 206.9 |
| 8 | 0.50 | - | - | 150.0 | 201.5 |
| none | 0.12 | - | - | 154.3 | 200.2 |

Killed before the deadline, by slack (of 324): 0.8 15, 1 32, 1.5 64, 2 72, 3 81, 5 93, 8 100, none 87.
