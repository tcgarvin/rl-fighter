# Order drills: followers_pay3_810

**Gate: fail.** followers_pay3_810 failed the drill gate: goto_arrival, goto_lift, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_810.pt`, seed 500000, sim version 8. Overall: 0.66 +/- 0.01 (709/1070) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.59 +/- 0.02 (332/558; 102 killed first, not counted)
- Same seeds, order hidden: 0.20 +/- 0.02 (115/584; 76 killed first, not counted)
- Lift from seeing the order: +0.40
- Near: 0.54 +/- 0.03 (177/325; 30 killed first, not counted)
- Far: 0.67 +/- 0.03 (155/233; 72 killed first, not counted)
- Enemies around the route: 0.61 +/- 0.03 (180/296; 50 killed first, not counted)
- Deadline in the order: 0.63 (256/405)
- No deadline (judged by 2x + 10 s): 0.50 (76/153)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.46 (44/95) |
| medium (2.5 to 4.5) | 0.62 (111/178) |
| loose (over 4.5) | 0.77 (101/132) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 558 | 405 | 153 | 36 |
| In time | 0.59 | 0.63 | 0.50 | 0.39 |
| Near miss (within 60 m) | 0.25 | 0.23 | 0.29 | 0.25 |
| At the enemy instead | 0.15 | 0.13 | 0.20 | 0.36 |
| Neither | 0.01 | 0.01 | 0.01 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.93 +/- 0.01 (474/512)
- Swap test, flipped, groups busy with a freighter: 0.79 +/- 0.03 (156/198)
- Swap test, flipped, groups flying at the pilots: 0.60 +/- 0.06 (35/58)
- Damage on the named target per pilot: 59.1 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 54.1 +/- 2.9 (n=512)
- Chose the named side: 0.86 +/- 0.02 (441/512)
- Chose the other side: 0.05 +/- 0.01 (28/512)
- Chose neither: 0.08 +/- 0.01 (43/512)
- Swap test, flipped with the order: 0.75 +/- 0.03 (191/256)
- Swap test, one side whatever was named: 0.11 +/- 0.02 (27/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.83 +/- 0.02 (423/512)
- On the named ward's attackers per pilot: 87.8 +/- 4.0 (n=512)
- On the other's per pilot: 13.9 +/- 1.4 (n=512)
- Chose the named side: 0.85 +/- 0.02 (434/512)
- Chose the other side: 0.06 +/- 0.01 (32/512)
- Chose neither: 0.09 +/- 0.01 (46/512)
- Swap test, flipped with the order: 0.73 +/- 0.03 (186/256)
- Swap test, one side whatever was named: 0.12 +/- 0.02 (30/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.595 | failed |
| goto_lift | 0.398 | failed |
| attack_target_hit | 0.926 | met |
| attack_side | 0.861 | met |
| attack_flip | 0.746 | met |
| defend_more_on_named | 0.826 | failed |
| defend_side | 0.848 | failed |
| defend_flip | 0.727 | failed |
