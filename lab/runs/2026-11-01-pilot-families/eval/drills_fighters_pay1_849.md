# Order drills: fighters_pay1_849

**Gate: fail.** fighters_pay1_849 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_849.pt`, seed 500000, sim version 6. Overall: 0.25 +/- 0.01 (257/1029) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.21 +/- 0.02 (108/517; 143 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.02 (93/564; 96 killed first, not counted)
- Lift from seeing the order: +0.04
- Near: 0.30 +/- 0.03 (94/309; 46 killed first, not counted)
- Far: 0.07 +/- 0.02 (14/208; 97 killed first, not counted)
- Enemies around the route: 0.28 +/- 0.03 (76/271; 75 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.85 +/- 0.02 (433/512)
- Swap test, flipped, groups busy with a freighter: 0.30 +/- 0.03 (59/198)
- Swap test, flipped, groups flying at the pilots: 0.33 +/- 0.06 (19/58)
- Damage on the named target per pilot: 56.3 +/- 3.1 (n=512)
- On other enemies per pilot (not judged): 95.7 +/- 4.2 (n=512)
- Chose the named side: 0.63 +/- 0.02 (324/512)
- Chose the other side: 0.25 +/- 0.02 (129/512)
- Chose neither: 0.12 +/- 0.01 (59/512)
- Swap test, flipped with the order: 0.30 +/- 0.03 (78/256)
- Swap test, one side whatever was named: 0.49 +/- 0.03 (126/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.60 +/- 0.02 (309/512)
- On the named ward's attackers per pilot: 80.0 +/- 3.6 (n=512)
- On the other's per pilot: 58.2 +/- 3.5 (n=512)
- Chose the named side: 0.61 +/- 0.02 (310/512)
- Chose the other side: 0.29 +/- 0.02 (146/512)
- Chose neither: 0.11 +/- 0.01 (56/512)
- Swap test, flipped with the order: 0.28 +/- 0.03 (71/256)
- Swap test, one side whatever was named: 0.50 +/- 0.03 (129/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.209 | failed |
| goto_lift | 0.044 | failed |
| attack_target_hit | 0.846 | failed |
| attack_side | 0.633 | failed |
| attack_flip | 0.305 | failed |
| defend_more_on_named | 0.604 | failed |
| defend_side | 0.605 | failed |
| defend_flip | 0.277 | failed |
