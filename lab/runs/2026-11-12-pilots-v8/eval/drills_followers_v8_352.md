# Order drills: followers_v8_352

**Gate: fail.** followers_v8_352 failed the drill gate: goto_arrival, goto_lift, defend_more_on_named.

Pilot `policy:ppo_bc_352.pt`, seed 500000, sim version 8. Overall: 0.62 +/- 0.01 (670/1088) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.51 +/- 0.02 (292/576; 84 killed first, not counted)
- Same seeds, order hidden: 0.18 +/- 0.02 (110/597; 63 killed first, not counted)
- Lift from seeing the order: +0.32
- Near: 0.42 +/- 0.03 (138/326; 29 killed first, not counted)
- Far: 0.62 +/- 0.03 (154/250; 55 killed first, not counted)
- Enemies around the route: 0.51 +/- 0.03 (151/298; 48 killed first, not counted)
- Deadline in the order: 0.56 (232/417)
- No deadline (judged by 2x + 10 s): 0.38 (60/159)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.30 (29/96) |
| medium (2.5 to 4.5) | 0.55 (100/182) |
| loose (over 4.5) | 0.74 (103/139) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 576 | 417 | 159 | 41 |
| In time | 0.51 | 0.56 | 0.38 | 0.41 |
| Near miss (within 60 m) | 0.26 | 0.24 | 0.31 | 0.22 |
| At the enemy instead | 0.21 | 0.18 | 0.30 | 0.34 |
| Neither | 0.02 | 0.02 | 0.01 | 0.02 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.93 +/- 0.01 (476/512)
- Swap test, flipped, groups busy with a freighter: 0.77 +/- 0.03 (152/198)
- Swap test, flipped, groups flying at the pilots: 0.55 +/- 0.07 (32/58)
- Damage on the named target per pilot: 58.6 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 54.9 +/- 2.8 (n=512)
- Chose the named side: 0.85 +/- 0.02 (434/512)
- Chose the other side: 0.08 +/- 0.01 (40/512)
- Chose neither: 0.07 +/- 0.01 (38/512)
- Swap test, flipped with the order: 0.72 +/- 0.03 (184/256)
- Swap test, one side whatever was named: 0.13 +/- 0.02 (33/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.83 +/- 0.02 (426/512)
- On the named ward's attackers per pilot: 81.4 +/- 3.8 (n=512)
- On the other's per pilot: 12.2 +/- 1.3 (n=512)
- Chose the named side: 0.87 +/- 0.01 (446/512)
- Chose the other side: 0.05 +/- 0.01 (28/512)
- Chose neither: 0.07 +/- 0.01 (38/512)
- Swap test, flipped with the order: 0.76 +/- 0.03 (194/256)
- Swap test, one side whatever was named: 0.11 +/- 0.02 (28/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.507 | failed |
| goto_lift | 0.323 | failed |
| attack_target_hit | 0.930 | met |
| attack_side | 0.848 | met |
| attack_flip | 0.719 | met |
| defend_more_on_named | 0.832 | failed |
| defend_side | 0.871 | met |
| defend_flip | 0.758 | met |
