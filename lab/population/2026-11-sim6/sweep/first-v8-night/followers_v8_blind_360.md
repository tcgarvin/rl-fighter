# Go-to deadline sweep: followers_v8_blind_360

Pilot `policy:ppo_bc_360.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.27 +/- 0.01 (368/1361)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 10.0 s over 10.0 s, on the 22 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.08 at slack 1.5, 0.09 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +39.5 +/- 2.7, three +99.4 +/- 16.1. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | 17.2 | 18.8 | 55.5 |
| 1 | 0.02 | - | 16.4 | 22.7 | 62.1 |
| 1.5 | 0.09 | - | 14.9 | 36.1 | 75.6 |
| 2 | 0.13 | - | 15.0 | 53.7 | 84.6 |
| 3 | 0.17 | - | 14.3 | 77.6 | 95.3 |
| 5 | 0.42 | - | 14.1 | 93.0 | 101.5 |
| 8 | 0.60 | 0.77 | 14.1 | 100.5 | 102.9 |
| none | 0.21 | 1.82 | 14.1 | 74.7 | 95.3 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.21 arrive by that rule, median time to arrive 43.5 s; 0.69 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 0.5 | 0.0 |
| 1 | 0.03 | - | - | 2.4 | 0.0 |
| 1.5 | 0.05 | - | - | 7.9 | 0.0 |
| 2 | 0.07 | - | - | 20.0 | 0.0 |
| 3 | 0.09 | - | - | 34.9 | 0.0 |
| 5 | 0.23 | - | 49.4 | 48.1 | 0.0 |
| 8 | 0.41 | - | 40.0 | 62.0 | 0.0 |
| none | 0.08 | 2.70 | 29.1 | 35.4 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | 10.0 | 12.6 | 48.5 |
| 1 | 0.02 | - | 9.6 | 14.5 | 54.5 |
| 1.5 | 0.06 | - | 9.4 | 23.5 | 68.9 |
| 2 | 0.14 | - | 9.4 | 31.1 | 82.0 |
| 3 | 0.17 | - | 9.4 | 47.0 | 100.3 |
| 5 | 0.53 | 0.92 | 9.4 | 56.6 | 108.8 |
| 8 | 0.73 | 0.59 | 9.4 | 63.0 | 111.4 |
| none | 0.25 | 1.47 | 9.4 | 49.9 | 99.1 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | 19.5 | 43.2 | 117.9 |
| 1 | 0.01 | - | 19.8 | 51.2 | 131.8 |
| 1.5 | 0.17 | - | 18.1 | 77.1 | 157.8 |
| 2 | 0.22 | - | 17.4 | 110.0 | 171.8 |
| 3 | 0.33 | - | 17.4 | 150.8 | 185.7 |
| 5 | 0.62 | 0.69 | 17.4 | 174.3 | 195.7 |
| 8 | 0.78 | 0.37 | 17.4 | 176.5 | 197.4 |
| none | 0.41 | 1.67 | 17.4 | 138.9 | 186.8 |

Killed before the deadline, by slack (of 324): 0.8 1, 1 8, 1.5 26, 2 41, 3 48, 5 72, 8 72, none 57.
