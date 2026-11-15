# Order drills: fighters_v8_500

**Gate: fail.** fighters_v8_500 failed the drill gate: goto_arrival, goto_lift.

Pilot `policy:ppo_bc_500.pt`, seed 500000, sim version 8. Overall: 0.64 +/- 0.01 (673/1053) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.50 +/- 0.02 (271/541; 119 killed first, not counted)
- Same seeds, order hidden: 0.25 +/- 0.02 (144/581; 79 killed first, not counted)
- Lift from seeing the order: +0.25
- Near: 0.43 +/- 0.03 (137/319; 36 killed first, not counted)
- Far: 0.60 +/- 0.03 (134/222; 83 killed first, not counted)
- Enemies around the route: 0.50 +/- 0.03 (146/292; 54 killed first, not counted)
- Deadline in the order: 0.54 (210/390)
- No deadline (judged by 2x + 10 s): 0.40 (61/151)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.42 (39/92) |
| medium (2.5 to 4.5) | 0.49 (84/170) |
| loose (over 4.5) | 0.68 (87/128) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 541 | 390 | 151 | 37 |
| In time | 0.50 | 0.54 | 0.40 | 0.32 |
| Near miss (within 60 m) | 0.26 | 0.25 | 0.30 | 0.22 |
| At the enemy instead | 0.23 | 0.21 | 0.30 | 0.46 |
| Neither | 0.00 | 0.01 | 0.00 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.92 +/- 0.01 (470/512)
- Swap test, flipped, groups busy with a freighter: 0.79 +/- 0.03 (156/198)
- Swap test, flipped, groups flying at the pilots: 0.66 +/- 0.06 (38/58)
- Damage on the named target per pilot: 60.1 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 58.8 +/- 3.1 (n=512)
- Chose the named side: 0.88 +/- 0.01 (448/512)
- Chose the other side: 0.09 +/- 0.01 (46/512)
- Chose neither: 0.04 +/- 0.01 (18/512)
- Swap test, flipped with the order: 0.76 +/- 0.03 (194/256)
- Swap test, one side whatever was named: 0.18 +/- 0.02 (45/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.01 (451/512)
- On the named ward's attackers per pilot: 85.6 +/- 3.5 (n=512)
- On the other's per pilot: 12.0 +/- 1.7 (n=512)
- Chose the named side: 0.90 +/- 0.01 (462/512)
- Chose the other side: 0.06 +/- 0.01 (30/512)
- Chose neither: 0.04 +/- 0.01 (20/512)
- Swap test, flipped with the order: 0.81 +/- 0.02 (208/256)
- Swap test, one side whatever was named: 0.12 +/- 0.02 (30/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.501 | failed |
| goto_lift | 0.253 | failed |
| attack_target_hit | 0.918 | met |
| attack_side | 0.875 | met |
| attack_flip | 0.758 | met |
| defend_more_on_named | 0.881 | met |
| defend_side | 0.902 | met |
| defend_flip | 0.812 | met |
