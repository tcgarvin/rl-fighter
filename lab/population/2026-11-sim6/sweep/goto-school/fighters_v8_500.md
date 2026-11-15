# Go-to deadline sweep: fighters_v8_500

Pilot `policy:ppo_bc_500.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.25 +/- 0.01 (312/1224)
- Arrival-time ratio, slack 8 over slack 1.5: 1.20 (median 17.4 s over 14.5 s, on the 2 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.03 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +13.4 +/- 2.2, three +84.7 +/- 15.5. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 41.7 | 61.6 |
| 1 | 0.02 | - | - | 48.6 | 69.1 |
| 1.5 | 0.03 | - | - | 68.4 | 81.1 |
| 2 | 0.08 | - | - | 86.1 | 84.2 |
| 3 | 0.17 | - | 46.2 | 101.4 | 90.0 |
| 5 | 0.45 | - | 31.1 | 109.5 | 93.6 |
| 8 | 0.65 | 0.74 | 25.6 | 117.8 | 92.7 |
| none | 0.14 | 2.09 | 28.2 | 97.3 | 96.7 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.14 arrive by that rule, median time to arrive 52.9 s; 0.67 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 3.0 | 0.0 |
| 1 | 0.03 | - | - | 6.1 | 0.0 |
| 1.5 | 0.02 | - | - | 13.2 | 0.0 |
| 2 | 0.03 | - | - | 23.8 | 0.0 |
| 3 | 0.10 | - | - | 40.0 | 0.0 |
| 5 | 0.30 | - | - | 51.5 | 0.0 |
| 8 | 0.44 | - | 44.6 | 63.4 | 0.0 |
| none | 0.08 | 2.13 | 31.4 | 53.3 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 44.1 | 57.9 |
| 1 | 0.01 | - | - | 48.6 | 65.8 |
| 1.5 | 0.07 | - | - | 61.1 | 73.4 |
| 2 | 0.15 | - | 32.1 | 66.4 | 77.0 |
| 3 | 0.23 | - | 18.4 | 72.0 | 78.5 |
| 5 | 0.61 | 0.90 | 17.0 | 75.2 | 80.5 |
| 8 | 0.82 | 0.61 | 18.1 | 74.6 | 83.0 |
| none | 0.19 | 1.95 | 22.6 | 67.9 | 89.1 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 78.1 | 126.9 |
| 1 | 0.02 | - | - | 91.2 | 141.5 |
| 1.5 | 0.00 | - | - | 130.8 | 170.0 |
| 2 | 0.05 | - | - | 168.2 | 175.8 |
| 3 | 0.20 | - | 24.6 | 192.1 | 191.5 |
| 5 | 0.50 | - | 46.0 | 201.8 | 200.2 |
| 8 | 0.91 | 0.45 | 21.1 | 215.5 | 195.0 |
| none | 0.26 | 1.71 | 42.4 | 170.7 | 201.0 |

Killed before the deadline, by slack (of 324): 0.8 6, 1 25, 1.5 45, 2 61, 3 83, 5 104, 8 103, none 113.
