# Go-to deadline sweep: followers_v8_352_nodeadline

Pilot `policy:ppo_bc_352.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.28 +/- 0.01 (341/1237)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 7.7 s over 7.7 s, on the 8 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.03 at slack 1.5, 0.04 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +19.3 +/- 2.0, three +50.3 +/- 14.0. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 28.0 | 59.1 |
| 1 | 0.01 | - | - | 32.7 | 66.5 |
| 1.5 | 0.03 | - | - | 48.8 | 79.8 |
| 2 | 0.07 | - | - | 54.9 | 87.6 |
| 3 | 0.22 | - | 40.4 | 71.3 | 94.2 |
| 5 | 0.47 | - | 27.6 | 85.5 | 98.2 |
| 8 | 0.66 | 0.67 | 25.4 | 92.2 | 98.5 |
| none | 0.26 | 1.64 | 25.5 | 71.0 | 95.1 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.26 arrive by that rule, median time to arrive 37.5 s; 0.77 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.9 | 0.0 |
| 1 | 0.01 | - | - | 1.6 | 0.0 |
| 1.5 | 0.02 | - | - | 8.6 | 0.0 |
| 2 | 0.01 | - | - | 16.7 | 0.0 |
| 3 | 0.05 | - | - | 32.0 | 0.0 |
| 5 | 0.24 | - | 54.9 | 53.6 | 0.0 |
| 8 | 0.46 | - | 37.9 | 69.2 | 0.0 |
| none | 0.04 | 2.22 | 32.9 | 33.3 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 27.0 | 52.0 |
| 1 | 0.01 | - | 14.8 | 31.5 | 60.1 |
| 1.5 | 0.04 | - | 13.6 | 45.1 | 76.6 |
| 2 | 0.08 | - | 12.8 | 54.6 | 81.4 |
| 3 | 0.41 | - | 11.5 | 60.0 | 85.6 |
| 5 | 0.70 | 0.70 | 11.5 | 64.5 | 89.5 |
| 8 | 0.85 | 0.44 | 11.5 | 64.4 | 88.8 |
| none | 0.46 | 1.03 | 11.5 | 64.4 | 87.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | - | 56.0 | 125.3 |
| 1 | 0.02 | - | - | 65.1 | 139.4 |
| 1.5 | 0.05 | - | - | 92.7 | 162.9 |
| 2 | 0.16 | - | - | 93.4 | 181.6 |
| 3 | 0.22 | - | - | 121.9 | 197.0 |
| 5 | 0.55 | 0.63 | - | 138.4 | 205.0 |
| 8 | 0.76 | 0.36 | - | 143.0 | 206.5 |
| none | 0.39 | 2.43 | - | 115.2 | 197.7 |

Killed before the deadline, by slack (of 324): 0.8 20, 1 27, 1.5 48, 2 65, 3 85, 5 94, 8 91, none 81.
