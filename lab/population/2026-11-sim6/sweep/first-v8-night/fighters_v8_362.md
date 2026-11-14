# Go-to deadline sweep: fighters_v8_362

Pilot `policy:ppo_bc_362.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.19 +/- 0.01 (219/1175)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 3.1 s over 3.1 s, on the 1 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.02 at slack 1.5, 0.01 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +13.1 +/- 2.1, three +65.2 +/- 16.8. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 38.6 | 61.9 |
| 1 | 0.00 | - | - | 47.5 | 69.3 |
| 1.5 | 0.02 | - | - | 61.0 | 82.3 |
| 2 | 0.05 | - | - | 78.5 | 85.2 |
| 3 | 0.12 | - | - | 88.3 | 92.1 |
| 5 | 0.34 | - | 38.4 | 97.8 | 92.4 |
| 8 | 0.46 | - | 38.2 | 104.4 | 95.1 |
| none | 0.11 | - | 28.0 | 87.2 | 92.4 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.11 arrive by that rule, median time to arrive - s; 0.46 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 4.3 | 0.0 |
| 1 | 0.01 | - | - | 7.4 | 0.0 |
| 1.5 | 0.01 | - | - | 18.1 | 0.0 |
| 2 | 0.01 | - | - | 31.8 | 0.0 |
| 3 | 0.08 | - | - | 47.8 | 0.0 |
| 5 | 0.28 | - | 49.6 | 59.7 | 0.0 |
| 8 | 0.41 | - | 46.5 | 70.1 | 0.0 |
| none | 0.04 | - | 32.0 | 54.9 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 48.0 | 58.2 |
| 1 | 0.00 | - | - | 53.3 | 62.9 |
| 1.5 | 0.05 | - | - | 61.5 | 70.4 |
| 2 | 0.09 | - | - | 65.8 | 73.7 |
| 3 | 0.14 | - | 29.6 | 73.4 | 76.8 |
| 5 | 0.38 | - | 22.8 | 73.8 | 78.0 |
| 8 | 0.48 | - | 21.5 | 74.6 | 82.4 |
| none | 0.16 | - | 22.4 | 73.4 | 77.3 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 63.4 | 127.6 |
| 1 | 0.00 | - | - | 81.7 | 145.2 |
| 1.5 | 0.00 | - | - | 103.5 | 176.4 |
| 2 | 0.04 | - | - | 137.9 | 181.9 |
| 3 | 0.23 | - | - | 143.6 | 199.4 |
| 5 | 0.53 | 0.80 | - | 159.8 | 199.3 |
| 8 | 0.72 | 0.51 | - | 168.6 | 202.9 |
| none | 0.25 | 2.09 | - | 133.2 | 199.8 |

Killed before the deadline, by slack (of 324): 0.8 10, 1 22, 1.5 61, 2 71, 3 95, 5 106, 8 112, none 102.
