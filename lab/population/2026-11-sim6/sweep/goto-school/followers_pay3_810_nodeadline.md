# Go-to deadline sweep: followers_pay3_810_nodeadline

Pilot `policy:ppo_bc_810.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.30 +/- 0.01 (370/1239)
- Arrival-time ratio, slack 8 over slack 1.5: 1.01 (median 8.9 s over 8.8 s, on the 10 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.05 at slack 1.5, 0.04 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +17.7 +/- 2.1, three +55.9 +/- 10.4. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 27.4 | 57.2 |
| 1 | 0.02 | - | - | 34.9 | 65.6 |
| 1.5 | 0.05 | - | 43.0 | 50.8 | 78.5 |
| 2 | 0.10 | - | 28.8 | 60.7 | 86.5 |
| 3 | 0.24 | - | 22.5 | 76.2 | 94.7 |
| 5 | 0.51 | 0.98 | 20.4 | 86.3 | 99.0 |
| 8 | 0.75 | 0.63 | 19.6 | 93.0 | 100.4 |
| none | 0.26 | 1.62 | 19.6 | 78.3 | 96.4 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.26 arrive by that rule, median time to arrive 37.0 s; 0.77 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 1.3 | 0.0 |
| 1 | 0.01 | - | - | 2.4 | 0.0 |
| 1.5 | 0.02 | - | - | 8.4 | 0.0 |
| 2 | 0.02 | - | - | 16.9 | 0.0 |
| 3 | 0.06 | - | - | 32.6 | 0.0 |
| 5 | 0.25 | - | 47.6 | 47.8 | 0.0 |
| 8 | 0.56 | 0.86 | 34.2 | 61.2 | 0.0 |
| none | 0.05 | 2.08 | 31.8 | 35.0 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.03 | - | 14.6 | 29.5 | 53.5 |
| 1 | 0.05 | - | 14.1 | 34.9 | 61.2 |
| 1.5 | 0.10 | - | 11.7 | 46.6 | 74.3 |
| 2 | 0.17 | - | 12.5 | 53.8 | 81.2 |
| 3 | 0.43 | - | 12.8 | 62.9 | 89.6 |
| 5 | 0.75 | 0.63 | 12.6 | 65.6 | 96.2 |
| 8 | 0.94 | 0.41 | 12.6 | 64.3 | 96.6 |
| none | 0.49 | 1.01 | 12.6 | 64.6 | 94.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 51.4 | 118.0 |
| 1 | 0.00 | - | - | 67.4 | 135.5 |
| 1.5 | 0.04 | - | 38.4 | 97.6 | 161.2 |
| 2 | 0.10 | - | - | 111.5 | 178.4 |
| 3 | 0.23 | - | - | 133.0 | 194.6 |
| 5 | 0.59 | 0.72 | - | 145.6 | 200.7 |
| 8 | 0.73 | 0.45 | 32.0 | 153.5 | 204.5 |
| none | 0.22 | - | 35.5 | 135.5 | 194.6 |

Killed before the deadline, by slack (of 324): 0.8 7, 1 15, 1.5 29, 2 52, 3 84, 5 104, 8 112, none 82.
