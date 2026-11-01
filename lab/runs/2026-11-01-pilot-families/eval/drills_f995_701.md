# Order drills: f995_701

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

Pilot `policy:ppo_bc_701.pt`, seed 500000, sim version 6. Overall: 0.18 +/- 0.01 (192/1086) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.22 +/- 0.02 (128/574; 86 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.02 (88/575; 85 killed first, not counted)
- Lift from seeing the order: +0.07
- Near: 0.26 +/- 0.02 (86/325; 30 killed first, not counted)
- Far: 0.17 +/- 0.02 (42/249; 56 killed first, not counted)
- Enemies around the route: 0.31 +/- 0.03 (93/304; 42 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.81 +/- 0.02 (414/512)
- Swap test, flipped, groups busy with a freighter: 0.15 +/- 0.03 (30/198)
- Swap test, flipped, groups flying at the pilots: 0.10 +/- 0.04 (6/58)
- Damage on the named target per pilot: 55.6 +/- 3.0 (n=512)
- On other enemies per pilot (not judged): 101.9 +/- 4.2 (n=512)
- Chose the named side: 0.53 +/- 0.02 (270/512)
- Chose the other side: 0.37 +/- 0.02 (187/512)
- Chose neither: 0.11 +/- 0.01 (55/512)
- Swap test, flipped with the order: 0.14 +/- 0.02 (36/256)
- Swap test, one side whatever was named: 0.67 +/- 0.03 (171/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.57 +/- 0.02 (290/512)
- On the named ward's attackers per pilot: 79.6 +/- 4.1 (n=512)
- On the other's per pilot: 67.9 +/- 4.2 (n=512)
- Chose the named side: 0.49 +/- 0.02 (253/512)
- Chose the other side: 0.38 +/- 0.02 (195/512)
- Chose neither: 0.12 +/- 0.01 (64/512)
- Swap test, flipped with the order: 0.11 +/- 0.02 (28/256)
- Swap test, one side whatever was named: 0.68 +/- 0.03 (174/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.223 | unset |
| goto_lift | 0.070 | unset |
| attack_target_hit | 0.809 | unset |
| attack_side | 0.527 | unset |
| attack_flip | 0.141 | unset |
| defend_more_on_named | 0.566 | unset |
| defend_side | 0.494 | unset |
| defend_flip | 0.109 | unset |
