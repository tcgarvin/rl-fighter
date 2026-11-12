# Go-to deadline sweep: followers_1793

Pilot `policy:ppo_bc_1793.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.28 +/- 0.01 (349/1225)
- Arrival-time ratio, slack 8 over slack 1.5: 0.96 (median 7.9 s over 8.3 s, on the 6 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.04 at slack 1.5, 0.03 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +27.2 +/- 3.0, three +73.1 +/- 15.4. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 23.3 | 58.4 |
| 1 | 0.01 | - | - | 28.9 | 65.9 |
| 1.5 | 0.05 | - | - | 43.5 | 80.8 |
| 2 | 0.09 | - | 36.4 | 55.9 | 89.6 |
| 3 | 0.24 | - | 21.6 | 75.7 | 98.0 |
| 5 | 0.50 | - | 19.4 | 88.6 | 99.4 |
| 8 | 0.66 | 0.68 | 19.9 | 97.4 | 100.8 |
| none | 0.22 | 1.63 | 19.1 | 77.5 | 98.1 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.22 arrive by that rule, median time to arrive 38.0 s; 0.58 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.3 | 0.0 |
| 1 | 0.01 | - | - | 1.7 | 0.0 |
| 1.5 | 0.01 | - | - | 11.2 | 0.0 |
| 2 | 0.01 | - | - | 22.4 | 0.0 |
| 3 | 0.08 | - | - | 43.2 | 0.0 |
| 5 | 0.32 | - | 47.2 | 59.2 | 0.0 |
| 8 | 0.51 | 0.97 | 36.3 | 72.7 | 0.0 |
| none | 0.03 | - | 30.4 | 46.9 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | 11.6 | 15.3 | 49.8 |
| 1 | 0.02 | - | 12.0 | 19.6 | 58.6 |
| 1.5 | 0.09 | - | 11.3 | 29.5 | 75.6 |
| 2 | 0.15 | - | 10.7 | 40.2 | 84.3 |
| 3 | 0.40 | - | 10.6 | 49.5 | 93.8 |
| 5 | 0.62 | 0.77 | 10.9 | 57.5 | 97.5 |
| 8 | 0.83 | 0.48 | 10.7 | 56.7 | 96.5 |
| none | 0.40 | 1.18 | 10.6 | 55.3 | 94.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 54.3 | 125.5 |
| 1 | 0.00 | - | - | 65.4 | 139.0 |
| 1.5 | 0.03 | - | - | 89.8 | 166.7 |
| 2 | 0.12 | - | - | 105.3 | 184.5 |
| 3 | 0.26 | - | - | 134.4 | 200.2 |
| 5 | 0.78 | 0.56 | - | 149.2 | 200.8 |
| 8 | 0.71 | 0.38 | - | 162.9 | 205.8 |
| none | 0.26 | - | - | 130.4 | 199.7 |

Killed before the deadline, by slack (of 324): 0.8 15, 1 26, 1.5 43, 2 62, 3 87, 5 97, 8 106, none 87.
