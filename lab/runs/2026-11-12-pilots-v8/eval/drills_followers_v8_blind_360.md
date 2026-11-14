# Order drills: followers_v8_blind_360

**Gate: fail.** followers_v8_blind_360 failed the drill gate: goto_arrival, goto_lift.

Pilot `policy:ppo_bc_360.pt`, seed 500000, sim version 8. Overall: 0.64 +/- 0.01 (699/1085) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.51 +/- 0.02 (290/573; 87 killed first, not counted)
- Same seeds, order hidden: 0.21 +/- 0.02 (125/593; 67 killed first, not counted)
- Lift from seeing the order: +0.30
- Near: 0.45 +/- 0.03 (147/329; 26 killed first, not counted)
- Far: 0.59 +/- 0.03 (143/244; 61 killed first, not counted)
- Enemies around the route: 0.52 +/- 0.03 (157/302; 44 killed first, not counted)
- Deadline in the order: 0.53 (221/414)
- No deadline (judged by 2x + 10 s): 0.43 (69/159)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.32 (30/94) |
| medium (2.5 to 4.5) | 0.50 (92/185) |
| loose (over 4.5) | 0.73 (99/135) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 573 | 414 | 159 | 39 |
| In time | 0.51 | 0.53 | 0.43 | 0.36 |
| Near miss (within 60 m) | 0.25 | 0.23 | 0.30 | 0.13 |
| At the enemy instead | 0.23 | 0.22 | 0.25 | 0.51 |
| Neither | 0.01 | 0.01 | 0.01 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.92 +/- 0.01 (469/512)
- Swap test, flipped, groups busy with a freighter: 0.85 +/- 0.03 (168/198)
- Swap test, flipped, groups flying at the pilots: 0.67 +/- 0.06 (39/58)
- Damage on the named target per pilot: 58.1 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 52.9 +/- 2.9 (n=512)
- Chose the named side: 0.90 +/- 0.01 (462/512)
- Chose the other side: 0.05 +/- 0.01 (27/512)
- Chose neither: 0.04 +/- 0.01 (23/512)
- Swap test, flipped with the order: 0.81 +/- 0.02 (207/256)
- Swap test, one side whatever was named: 0.11 +/- 0.02 (27/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.86 +/- 0.02 (440/512)
- On the named ward's attackers per pilot: 82.3 +/- 3.6 (n=512)
- On the other's per pilot: 12.7 +/- 1.7 (n=512)
- Chose the named side: 0.89 +/- 0.01 (455/512)
- Chose the other side: 0.06 +/- 0.01 (32/512)
- Chose neither: 0.05 +/- 0.01 (25/512)
- Swap test, flipped with the order: 0.79 +/- 0.03 (202/256)
- Swap test, one side whatever was named: 0.11 +/- 0.02 (29/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.506 | failed |
| goto_lift | 0.295 | failed |
| attack_target_hit | 0.916 | met |
| attack_side | 0.902 | met |
| attack_flip | 0.809 | met |
| defend_more_on_named | 0.859 | met |
| defend_side | 0.889 | met |
| defend_flip | 0.789 | met |
