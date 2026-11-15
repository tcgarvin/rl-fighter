# Go-to deadline sweep: followers_solo_1072

Pilot `policy:ppo_bc_1072.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.38 +/- 0.01 (463/1207)
- Arrival-time ratio, slack 8 over slack 1.5: 1.00 (median 14.5 s over 14.6 s, on the 22 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.12 at slack 1.5, 0.11 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +28.5 +/- 2.7, three +52.7 +/- 11.3. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.03 | - | 10.7 | 10.6 | 55.9 |
| 1 | 0.07 | - | 10.2 | 12.4 | 64.0 |
| 1.5 | 0.14 | - | 11.2 | 22.2 | 80.5 |
| 2 | 0.22 | - | 10.5 | 28.6 | 88.8 |
| 3 | 0.30 | - | 10.6 | 47.4 | 97.8 |
| 5 | 0.62 | 0.83 | 10.6 | 59.3 | 98.1 |
| 8 | 0.80 | 0.55 | 10.8 | 64.6 | 96.9 |
| none | 0.33 | 1.39 | 11.6 | 60.7 | 94.7 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.33 arrive by that rule, median time to arrive 35.3 s; 0.78 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | 41.3 | 0.0 | 0.0 |
| 1 | 0.02 | - | 35.9 | 0.3 | 0.0 |
| 1.5 | 0.03 | - | 47.3 | 3.8 | 0.0 |
| 2 | 0.05 | - | 12.6 | 9.5 | 0.0 |
| 3 | 0.10 | - | 26.0 | 20.8 | 0.0 |
| 5 | 0.39 | - | 17.0 | 41.4 | 0.0 |
| 8 | 0.58 | 0.88 | 24.2 | 49.8 | 0.0 |
| none | 0.05 | 2.24 | 21.5 | 33.7 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.05 | - | 7.5 | 9.6 | 52.5 |
| 1 | 0.07 | - | 7.5 | 14.8 | 65.1 |
| 1.5 | 0.14 | - | 9.2 | 24.0 | 85.8 |
| 2 | 0.29 | - | 8.1 | 33.1 | 99.3 |
| 3 | 0.45 | - | 8.8 | 48.1 | 105.8 |
| 5 | 0.79 | 0.61 | 8.2 | 52.5 | 105.2 |
| 8 | 0.97 | 0.39 | 8.4 | 52.5 | 105.4 |
| none | 0.54 | 0.95 | 9.9 | 56.5 | 101.0 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.03 | - | 13.6 | 22.1 | 115.0 |
| 1 | 0.12 | - | 12.4 | 22.1 | 127.0 |
| 1.5 | 0.29 | - | 12.4 | 38.7 | 155.8 |
| 2 | 0.40 | - | 12.8 | 43.1 | 167.1 |
| 3 | 0.46 | - | 12.9 | 73.3 | 187.7 |
| 5 | 0.87 | 0.32 | 12.6 | 84.0 | 189.2 |
| 8 | 1.00 | 0.20 | 12.9 | 91.4 | 185.2 |
| none | 0.65 | 0.67 | 13.8 | 92.1 | 183.1 |

Killed before the deadline, by slack (of 324): 0.8 7, 1 13, 1.5 36, 2 62, 3 85, 5 111, 8 119, none 90.
