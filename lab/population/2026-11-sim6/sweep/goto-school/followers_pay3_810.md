# Go-to deadline sweep: followers_pay3_810

Pilot `policy:ppo_bc_810.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.32 +/- 0.01 (387/1224)
- Arrival-time ratio, slack 8 over slack 1.5: 1.12 (median 11.6 s over 10.3 s, on the 9 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.05 at slack 1.5, 0.05 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +27.6 +/- 3.0, three +72.1 +/- 10.8. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 20.1 | 57.3 |
| 1 | 0.02 | - | - | 26.4 | 64.2 |
| 1.5 | 0.06 | - | - | 39.8 | 79.9 |
| 2 | 0.09 | - | - | 52.6 | 88.1 |
| 3 | 0.24 | - | 25.2 | 68.6 | 93.9 |
| 5 | 0.56 | 0.91 | 21.0 | 81.4 | 94.9 |
| 8 | 0.75 | 0.55 | 19.6 | 91.6 | 97.3 |
| none | 0.26 | 1.62 | 19.6 | 78.3 | 96.4 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.26 arrive by that rule, median time to arrive 37.0 s; 0.77 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.2 | 0.0 |
| 1 | 0.01 | - | - | 0.9 | 0.0 |
| 1.5 | 0.01 | - | - | 6.7 | 0.0 |
| 2 | 0.04 | - | - | 14.7 | 0.0 |
| 3 | 0.14 | - | - | 30.2 | 0.0 |
| 5 | 0.36 | - | 36.0 | 50.1 | 0.0 |
| 8 | 0.60 | 0.83 | 28.1 | 62.3 | 0.0 |
| none | 0.05 | 2.08 | 31.8 | 35.0 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.04 | - | 21.3 | 17.4 | 48.5 |
| 1 | 0.03 | - | 19.1 | 22.1 | 58.5 |
| 1.5 | 0.09 | - | 14.4 | 37.5 | 72.1 |
| 2 | 0.15 | - | 14.4 | 47.3 | 80.8 |
| 3 | 0.37 | - | 14.4 | 58.8 | 85.4 |
| 5 | 0.71 | 0.71 | 12.5 | 63.9 | 81.9 |
| 8 | 0.88 | 0.46 | 14.4 | 65.1 | 86.2 |
| none | 0.49 | 1.01 | 12.6 | 64.6 | 94.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 42.8 | 123.5 |
| 1 | 0.02 | - | - | 56.1 | 134.1 |
| 1.5 | 0.09 | - | - | 75.3 | 167.6 |
| 2 | 0.08 | - | - | 95.8 | 183.6 |
| 3 | 0.21 | - | - | 116.8 | 196.4 |
| 5 | 0.85 | 0.55 | - | 130.1 | 203.0 |
| 8 | 0.93 | 0.32 | 39.2 | 147.4 | 205.6 |
| none | 0.22 | - | 35.5 | 135.5 | 194.6 |

Killed before the deadline, by slack (of 324): 0.8 7, 1 17, 1.5 43, 2 59, 3 85, 5 105, 8 104, none 82.
