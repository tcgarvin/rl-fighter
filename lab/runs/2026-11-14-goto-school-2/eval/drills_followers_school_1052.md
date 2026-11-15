# Order drills: followers_school_1052

**Gate: pass.** followers_school_1052 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_1052.pt`, seed 500000, sim version 8. Overall: 0.89 +/- 0.01 (983/1105) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.86 +/- 0.01 (509/593; 67 killed first, not counted)
- Same seeds, order hidden: 0.19 +/- 0.02 (115/602; 58 killed first, not counted)
- Lift from seeing the order: +0.67
- Near: 0.81 +/- 0.02 (270/335; 20 killed first, not counted)
- Far: 0.93 +/- 0.02 (239/258; 47 killed first, not counted)
- Enemies around the route: 0.86 +/- 0.02 (262/303; 43 killed first, not counted)
- Deadline in the order: 0.89 (383/431)
- No deadline (judged by 2x + 10 s): 0.78 (126/162)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.84 (83/99) |
| medium (2.5 to 4.5) | 0.88 (165/187) |
| loose (over 4.5) | 0.93 (135/145) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 593 | 431 | 162 | 37 |
| In time | 0.86 | 0.89 | 0.78 | 0.51 |
| Near miss (within 60 m) | 0.10 | 0.08 | 0.15 | 0.24 |
| At the enemy instead | 0.04 | 0.03 | 0.07 | 0.24 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.97 +/- 0.01 (497/512)
- Swap test, flipped, groups busy with a freighter: 0.94 +/- 0.02 (187/198)
- Swap test, flipped, groups flying at the pilots: 0.83 +/- 0.05 (48/58)
- Damage on the named target per pilot: 64.0 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 50.7 +/- 2.9 (n=512)
- Chose the named side: 0.96 +/- 0.01 (490/512)
- Chose the other side: 0.02 +/- 0.01 (11/512)
- Chose neither: 0.02 +/- 0.01 (11/512)
- Swap test, flipped with the order: 0.92 +/- 0.02 (235/256)
- Swap test, one side whatever was named: 0.04 +/- 0.01 (11/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.90 +/- 0.01 (461/512)
- On the named ward's attackers per pilot: 82.7 +/- 3.5 (n=512)
- On the other's per pilot: 5.8 +/- 0.9 (n=512)
- Chose the named side: 0.97 +/- 0.01 (495/512)
- Chose the other side: 0.02 +/- 0.01 (11/512)
- Chose neither: 0.01 +/- 0.00 (6/512)
- Swap test, flipped with the order: 0.93 +/- 0.02 (239/256)
- Swap test, one side whatever was named: 0.04 +/- 0.01 (11/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.858 | met |
| goto_lift | 0.667 | met |
| attack_target_hit | 0.971 | met |
| attack_side | 0.957 | met |
| attack_flip | 0.918 | met |
| defend_more_on_named | 0.900 | met |
| defend_side | 0.967 | met |
| defend_flip | 0.934 | met |
