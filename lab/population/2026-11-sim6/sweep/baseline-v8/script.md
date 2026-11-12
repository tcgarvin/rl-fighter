# Go-to deadline sweep: script

Pilot `script`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.94 +/- 0.01 (1105/1173)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 10.2 s over 10.2 s, on the 181 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.56 at slack 1.5, 0.56 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +0.6 +/- 0.3, three +0.2 +/- 0.1. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.13 | - | 6.7 | 12.3 | 72.4 |
| 1 | 0.24 | - | 6.7 | 13.7 | 80.5 |
| 1.5 | 0.76 | 0.88 | 6.6 | 15.9 | 89.8 |
| 2 | 0.96 | 0.70 | 6.6 | 16.1 | 91.6 |
| 3 | 1.00 | 0.50 | 6.6 | 16.1 | 91.7 |
| 5 | 1.00 | 0.31 | 6.6 | 16.1 | 91.8 |
| 8 | 1.00 | 0.20 | 6.6 | 16.1 | 91.8 |
| none | 1.00 | 0.48 | 6.6 | 16.1 | 91.8 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 1.00 arrive by that rule, median time to arrive 10.9 s; 1.00 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.12 | - | 6.5 | 0.0 | 0.0 |
| 1 | 0.27 | - | 6.5 | 0.0 | 0.0 |
| 1.5 | 0.82 | 0.87 | 6.5 | 0.0 | 0.0 |
| 2 | 0.97 | 0.69 | 6.5 | 0.0 | 0.0 |
| 3 | 1.00 | 0.49 | 6.5 | 0.0 | 0.0 |
| 5 | 1.00 | 0.30 | 6.5 | 0.0 | 0.0 |
| 8 | 1.00 | 0.19 | 6.5 | 0.0 | 0.0 |
| none | 1.00 | 0.48 | 6.5 | 0.0 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.13 | - | 6.2 | 13.2 | 66.4 |
| 1 | 0.22 | - | 6.2 | 14.9 | 76.4 |
| 1.5 | 0.71 | 0.89 | 6.2 | 17.0 | 86.7 |
| 2 | 0.93 | 0.70 | 6.2 | 17.5 | 89.2 |
| 3 | 0.99 | 0.50 | 6.2 | 17.5 | 89.6 |
| 5 | 1.00 | 0.31 | 6.2 | 17.5 | 89.7 |
| 8 | 1.00 | 0.20 | 6.2 | 17.5 | 89.7 |
| none | 1.00 | 0.47 | 6.2 | 17.5 | 89.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.14 | - | 8.2 | 23.7 | 150.8 |
| 1 | 0.23 | 1.37 | 8.2 | 26.3 | 165.1 |
| 1.5 | 0.68 | 0.92 | 7.5 | 30.6 | 182.6 |
| 2 | 1.00 | 0.70 | 7.5 | 30.8 | 185.6 |
| 3 | 1.00 | 0.49 | 7.5 | 30.8 | 185.6 |
| 5 | 1.00 | 0.31 | 7.5 | 30.8 | 185.6 |
| 8 | 1.00 | 0.20 | 7.5 | 30.8 | 185.6 |
| none | 1.00 | 0.51 | 7.5 | 30.8 | 185.6 |

Killed before the deadline, by slack (of 324): 0.8 51, 1 66, 1.5 85, 2 90, 3 90, 5 91, 8 91, none 91.
