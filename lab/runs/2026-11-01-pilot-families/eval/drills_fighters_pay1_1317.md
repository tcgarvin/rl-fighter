# Order drills: fighters_pay1_1317

**Gate: fail.** fighters_pay1_1317 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_1317.pt`, seed 500000, sim version 7. Overall: 0.19 +/- 0.01 (206/1082) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.16 +/- 0.02 (93/570; 90 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.02 (102/588; 72 killed first, not counted)
- Lift from seeing the order: -0.01
- Near: 0.21 +/- 0.02 (68/321; 34 killed first, not counted)
- Far: 0.10 +/- 0.02 (25/249; 56 killed first, not counted)
- Enemies around the route: 0.17 +/- 0.02 (50/301; 45 killed first, not counted)

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
| goto_arrival | 0.163 | failed |
| goto_lift | -0.010 | failed |
| attack_target_hit | 0.838 | failed |
| attack_side | 0.564 | failed |
| attack_flip | 0.215 | failed |
| defend_more_on_named | 0.619 | failed |
| defend_side | 0.570 | failed |
| defend_flip | 0.227 | failed |
