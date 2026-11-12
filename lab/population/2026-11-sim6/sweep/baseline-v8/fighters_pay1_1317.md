# Go-to deadline sweep: fighters_pay1_1317

Pilot `policy:ppo_bc_1317.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.08 +/- 0.01 (97/1158)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 4.6 s over 4.6 s, on the 2 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.01 at slack 1.5, 0.01 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +11.2 +/- 2.0, three +91.4 +/- 17.2. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 42.4 | 58.8 |
| 1 | 0.01 | - | - | 51.7 | 65.8 |
| 1.5 | 0.01 | - | - | 74.3 | 77.0 |
| 2 | 0.03 | - | - | 91.7 | 79.9 |
| 3 | 0.04 | - | - | 108.5 | 84.0 |
| 5 | 0.15 | - | - | 120.3 | 85.8 |
| 8 | 0.22 | - | 47.4 | 126.1 | 86.2 |
| none | 0.05 | - | 43.4 | 110.2 | 84.5 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.05 arrive by that rule, median time to arrive - s; 0.28 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 2.9 | 0.0 |
| 1 | 0.01 | - | - | 7.6 | 0.0 |
| 1.5 | 0.01 | - | - | 25.1 | 0.0 |
| 2 | 0.01 | - | - | 37.4 | 0.0 |
| 3 | 0.02 | - | - | 53.5 | 0.0 |
| 5 | 0.09 | - | - | 67.7 | 0.0 |
| 8 | 0.16 | - | 41.4 | 78.1 | 0.0 |
| none | 0.04 | - | 36.7 | 58.4 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 42.2 | 51.4 |
| 1 | 0.01 | - | - | 46.3 | 56.5 |
| 1.5 | 0.01 | - | - | 55.4 | 65.2 |
| 2 | 0.04 | - | - | 59.5 | 67.6 |
| 3 | 0.06 | - | - | 62.5 | 73.1 |
| 5 | 0.24 | - | 23.1 | 66.2 | 73.8 |
| 8 | 0.31 | - | 22.7 | 66.6 | 73.8 |
| none | 0.06 | - | 22.7 | 65.5 | 73.5 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 82.1 | 125.1 |
| 1 | 0.00 | - | - | 101.3 | 140.8 |
| 1.5 | 0.00 | - | - | 142.3 | 165.8 |
| 2 | 0.04 | - | - | 178.3 | 172.0 |
| 3 | 0.05 | - | - | 209.6 | 178.9 |
| 5 | 0.11 | - | - | 226.9 | 183.6 |
| 8 | 0.18 | - | - | 233.7 | 184.9 |
| none | 0.06 | - | - | 206.7 | 179.9 |

Killed before the deadline, by slack (of 324): 0.8 19, 1 39, 1.5 67, 2 81, 3 97, 5 109, 8 108, none 102.
