# Order drills: fighters_v8_362

**Gate: fail.** fighters_v8_362 failed the drill gate: goto_arrival, goto_lift, defend_more_on_named.

Pilot `policy:ppo_bc_362.pt`, seed 500000, sim version 8. Overall: 0.58 +/- 0.02 (608/1055) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.42 +/- 0.02 (227/543; 117 killed first, not counted)
- Same seeds, order hidden: 0.21 +/- 0.02 (120/572; 88 killed first, not counted)
- Lift from seeing the order: +0.21
- Near: 0.39 +/- 0.03 (123/319; 36 killed first, not counted)
- Far: 0.46 +/- 0.03 (104/224; 81 killed first, not counted)
- Enemies around the route: 0.43 +/- 0.03 (122/286; 60 killed first, not counted)
- Deadline in the order: 0.48 (187/393)
- No deadline (judged by 2x + 10 s): 0.27 (40/150)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.33 (31/95) |
| medium (2.5 to 4.5) | 0.40 (68/168) |
| loose (over 4.5) | 0.68 (88/130) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 543 | 393 | 150 | 38 |
| In time | 0.42 | 0.48 | 0.27 | 0.24 |
| Near miss (within 60 m) | 0.27 | 0.24 | 0.34 | 0.26 |
| At the enemy instead | 0.31 | 0.28 | 0.39 | 0.50 |
| Neither | 0.00 | 0.00 | 0.01 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.91 +/- 0.01 (467/512)
- Swap test, flipped, groups busy with a freighter: 0.77 +/- 0.03 (152/198)
- Swap test, flipped, groups flying at the pilots: 0.60 +/- 0.06 (35/58)
- Damage on the named target per pilot: 55.0 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 57.3 +/- 3.3 (n=512)
- Chose the named side: 0.86 +/- 0.02 (442/512)
- Chose the other side: 0.10 +/- 0.01 (51/512)
- Chose neither: 0.04 +/- 0.01 (19/512)
- Swap test, flipped with the order: 0.73 +/- 0.03 (187/256)
- Swap test, one side whatever was named: 0.20 +/- 0.02 (51/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.85 +/- 0.02 (435/512)
- On the named ward's attackers per pilot: 77.7 +/- 3.5 (n=512)
- On the other's per pilot: 17.1 +/- 2.1 (n=512)
- Chose the named side: 0.87 +/- 0.01 (447/512)
- Chose the other side: 0.07 +/- 0.01 (36/512)
- Chose neither: 0.06 +/- 0.01 (29/512)
- Swap test, flipped with the order: 0.76 +/- 0.03 (194/256)
- Swap test, one side whatever was named: 0.14 +/- 0.02 (36/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.418 | failed |
| goto_lift | 0.208 | failed |
| attack_target_hit | 0.912 | met |
| attack_side | 0.863 | met |
| attack_flip | 0.730 | met |
| defend_more_on_named | 0.850 | failed |
| defend_side | 0.873 | met |
| defend_flip | 0.758 | met |
