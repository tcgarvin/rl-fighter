# Order drills: fighters_pay1_1317

**Gate: fail.** fighters_pay1_1317 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_1317.pt`, seed 500000, sim version 8. Overall: 0.24 +/- 0.01 (253/1073) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.25 +/- 0.02 (140/561; 99 killed first, not counted)
- Same seeds, order hidden: 0.19 +/- 0.02 (111/575; 85 killed first, not counted)
- Lift from seeing the order: +0.06
- Near: 0.23 +/- 0.02 (75/320; 35 killed first, not counted)
- Far: 0.27 +/- 0.03 (65/241; 64 killed first, not counted)
- Enemies around the route: 0.27 +/- 0.03 (78/290; 56 killed first, not counted)
- Deadline in the order: 0.29 (115/403)
- No deadline (judged by 2x + 10 s): 0.16 (25/158)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.17 (16/93) |
| medium (2.5 to 4.5) | 0.27 (46/173) |
| loose (over 4.5) | 0.39 (53/137) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 561 | 403 | 158 | 36 |
| In time | 0.25 | 0.29 | 0.16 | 0.08 |
| Near miss (within 60 m) | 0.25 | 0.26 | 0.25 | 0.22 |
| At the enemy instead | 0.47 | 0.44 | 0.57 | 0.69 |
| Neither | 0.02 | 0.02 | 0.03 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.84 +/- 0.02 (429/512)
- Swap test, flipped, groups busy with a freighter: 0.23 +/- 0.03 (45/198)
- Swap test, flipped, groups flying at the pilots: 0.17 +/- 0.05 (10/58)
- Damage on the named target per pilot: 51.4 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 90.1 +/- 4.0 (n=512)
- Chose the named side: 0.56 +/- 0.02 (289/512)
- Chose the other side: 0.29 +/- 0.02 (148/512)
- Chose neither: 0.15 +/- 0.02 (75/512)
- Swap test, flipped with the order: 0.21 +/- 0.03 (55/256)
- Swap test, one side whatever was named: 0.52 +/- 0.03 (133/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.62 +/- 0.02 (317/512)
- On the named ward's attackers per pilot: 83.3 +/- 4.3 (n=512)
- On the other's per pilot: 53.1 +/- 3.5 (n=512)
- Chose the named side: 0.57 +/- 0.02 (292/512)
- Chose the other side: 0.29 +/- 0.02 (148/512)
- Chose neither: 0.14 +/- 0.02 (72/512)
- Swap test, flipped with the order: 0.23 +/- 0.03 (58/256)
- Swap test, one side whatever was named: 0.54 +/- 0.03 (139/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.250 | failed |
| goto_lift | 0.057 | failed |
| attack_target_hit | 0.838 | failed |
| attack_side | 0.564 | failed |
| attack_flip | 0.215 | failed |
| defend_more_on_named | 0.619 | failed |
| defend_side | 0.570 | failed |
| defend_flip | 0.227 | failed |
