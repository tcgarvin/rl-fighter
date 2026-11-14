# Go-to deadline sweep: followers_v8_352

Pilot `policy:ppo_bc_352.pt`, seed 700000, sim version 8. One ship alone with a go-to: 324 layouts, each flown at 8 time allowances. Slack 1 is a straight line at the hull's speed cap plus 3 s to turn.

## Headlines

- In time at slack 1.5 and over: 0.26 +/- 0.01 (310/1173)
- Arrival-time ratio, slack 8 over slack 1.5: 0.96 (median 7.0 s over 7.3 s, on the 6 layouts inside the circle within the slack-1.5 allowance at both). 1 means it ignores the allowance.
- Inside the circle within the slack-1.5 allowance, of all layouts: 0.03 at slack 1.5, 0.02 at slack 8. The same share means it ignores the allowance; fewer at the looser one means it used the time.
- Hits bought by slack (damage dealt before arriving or the deadline, slack 8 minus slack 1.5, by enemies): one +24.0 +/- 2.8, three +48.8 +/- 11.9. A ship that never arrives also deals more with a later deadline, so read this with the in-time share.

## Every layout

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 21.6 | 60.4 |
| 1 | 0.01 | - | - | 25.8 | 66.8 |
| 1.5 | 0.04 | - | - | 38.6 | 83.0 |
| 2 | 0.06 | - | - | 51.6 | 88.5 |
| 3 | 0.23 | - | 44.8 | 67.1 | 99.3 |
| 5 | 0.43 | - | 27.7 | 86.8 | 102.2 |
| 8 | 0.69 | 0.72 | 25.5 | 82.8 | 102.7 |
| none | 0.26 | 1.64 | 25.5 | 71.0 | 95.1 |

In time: of the ships alive at the deadline. Arrive / allowed: median time to the circle over the time allowed (- if half or more never got there by 20 s after the deadline). Leave s: median seconds until half the distance was covered. Dealt, taken: mean gun damage before arriving or the deadline. The `none` row has no deadline and is judged by twice the straight-line time plus 10 s.

No deadline: 0.26 arrive by that rule, median time to arrive 37.5 s; 0.77 get there within 20 s more.

## Enemies: parked

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.01 | - | - | 0.6 | 0.0 |
| 1 | 0.02 | - | - | 1.1 | 0.0 |
| 1.5 | 0.03 | - | - | 4.2 | 0.0 |
| 2 | 0.04 | - | - | 16.8 | 0.0 |
| 3 | 0.11 | - | - | 34.6 | 0.0 |
| 5 | 0.32 | - | 45.5 | 52.9 | 0.0 |
| 8 | 0.55 | 0.91 | 32.9 | 64.1 | 0.0 |
| none | 0.04 | 2.22 | 32.9 | 33.3 | 0.0 |

## Enemies: one

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.02 | - | 15.1 | 17.9 | 52.4 |
| 1 | 0.00 | - | 12.3 | 20.7 | 58.5 |
| 1.5 | 0.04 | - | 11.0 | 33.5 | 79.6 |
| 2 | 0.09 | - | 12.6 | 44.0 | 81.1 |
| 3 | 0.34 | - | 10.9 | 54.5 | 97.0 |
| 5 | 0.55 | 0.96 | 11.7 | 61.2 | 98.2 |
| 8 | 0.84 | 0.59 | 10.9 | 57.5 | 97.1 |
| none | 0.46 | 1.03 | 11.5 | 64.4 | 87.7 |

## Enemies: three

| Slack | In time | Arrive / allowed | Leave s | Dealt | Taken |
|---|---|---|---|---|---|
| 0.8 | 0.00 | - | - | 46.2 | 128.9 |
| 1 | 0.00 | - | - | 55.6 | 142.0 |
| 1.5 | 0.05 | - | - | 78.1 | 169.4 |
| 2 | 0.06 | - | - | 93.9 | 184.5 |
| 3 | 0.32 | - | - | 112.2 | 200.9 |
| 5 | 0.40 | - | - | 146.4 | 208.6 |
| 8 | 0.89 | 0.33 | - | 126.9 | 211.1 |
| none | 0.39 | 2.43 | - | 115.2 | 197.7 |

Killed before the deadline, by slack (of 324): 0.8 17, 1 29, 1.5 53, 2 67, 3 99, 5 110, 8 118, none 81.
