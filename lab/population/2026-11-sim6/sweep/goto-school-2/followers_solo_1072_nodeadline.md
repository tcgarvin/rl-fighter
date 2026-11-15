# Go-to deadline sweep: followers_solo_1072_nodeadline

Pilot `policy:ppo_bc_1072.pt:no_deadline`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.37 +/- 0.01 (447/1218)
- Arrival-time ratio, slack 8 over slack 1.5: 0.97 (median 13.0 s over 13.4 s, on the 24 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.10 at slack 1.5, 0.10 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +16.0 +/- 2.4, three +35.3 +/- 9.0. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | 12.9 | 22.5 | 56.6 |
| 1 | 0.04 | - | 12.4 | 27.2 | 64.7 |
| 1.5 | 0.11 | - | 12.1 | 37.8 | 80.5 |
| 2 | 0.18 | - | 11.5 | 45.9 | 88.8 |
| 3 | 0.35 | - | 11.6 | 56.4 | 94.2 |
| 5 | 0.57 | 0.85 | 11.6 | 68.0 | 97.0 |
| 8 | 0.78 | 0.55 | 11.6 | 70.5 | 96.6 |
| none | 0.33 | 1.39 | 11.6 | 60.7 | 94.7 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.33 arrive by that rule, median time to arrive 35.3 s; 0.78 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | 22.9 | 0.6 | 0.0 |
| 1 | 0.01 | - | 35.2 | 2.2 | 0.0 |
| 1.5 | 0.03 | - | 28.4 | 8.5 | 0.0 |
| 2 | 0.02 | - | 28.8 | 14.5 | 0.0 |
| 3 | 0.11 | - | 26.9 | 31.9 | 0.0 |
| 5 | 0.32 | - | 24.0 | 46.9 | 0.0 |
| 8 | 0.58 | 0.83 | 21.5 | 55.5 | 0.0 |
| none | 0.05 | 2.24 | 21.5 | 33.7 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | 10.9 | 25.9 | 55.3 |
| 1 | 0.04 | - | 10.5 | 31.8 | 64.7 |
| 1.5 | 0.10 | - | 10.2 | 41.9 | 82.9 |
| 2 | 0.21 | - | 9.8 | 47.7 | 91.8 |
| 3 | 0.52 | 0.98 | 9.9 | 54.2 | 100.0 |
| 5 | 0.74 | 0.67 | 9.9 | 56.8 | 102.3 |
| 8 | 0.93 | 0.44 | 9.9 | 57.9 | 103.0 |
| none | 0.54 | 0.95 | 9.9 | 56.5 | 101.0 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.04 | - | 17.6 | 41.0 | 114.4 |
| 1 | 0.06 | - | 17.0 | 47.6 | 129.5 |
| 1.5 | 0.23 | - | 14.6 | 62.9 | 158.7 |
| 2 | 0.38 | - | 13.4 | 75.4 | 174.6 |
| 3 | 0.59 | 0.68 | 14.1 | 82.9 | 182.5 |
| 5 | 0.86 | 0.38 | 13.8 | 100.4 | 188.6 |
| 8 | 1.00 | 0.21 | 13.8 | 98.2 | 186.8 |
| none | 0.65 | 0.67 | 13.8 | 92.1 | 183.1 |

Killed before the deadline, by slack (of 324): 0.8 8, 1 11, 1.5 33, 2 54, 3 88, 5 110, 8 117, none 90.
