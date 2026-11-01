# Order drills: hide_644

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

Pilot `policy:ppo_bc_644.pt`, seed 500000, sim version 6. Overall: 0.15 +/- 0.01 (164/1062) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.13 +/- 0.01 (71/550; 110 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.01 (68/568; 92 killed first, not counted)
- Lift from seeing the order: +0.01
- Near: 0.17 +/- 0.02 (54/315; 40 killed first, not counted)
- Far: 0.07 +/- 0.02 (17/235; 70 killed first, not counted)
- Enemies around the route: 0.17 +/- 0.02 (51/293; 53 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.81 +/- 0.02 (416/512)
- Swap test, flipped, groups busy with a freighter: 0.21 +/- 0.03 (42/198)
- Swap test, flipped, groups flying at the pilots: 0.07 +/- 0.03 (4/58)
- Damage on the named target per pilot: 40.1 +/- 2.5 (n=512)
- On other enemies per pilot (not judged): 53.9 +/- 2.8 (n=512)
- Chose the named side: 0.53 +/- 0.02 (272/512)
- Chose the other side: 0.35 +/- 0.02 (178/512)
- Chose neither: 0.12 +/- 0.01 (62/512)
- Swap test, flipped with the order: 0.18 +/- 0.02 (46/256)
- Swap test, one side whatever was named: 0.59 +/- 0.03 (152/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.64 +/- 0.02 (328/512)
- On the named ward's attackers per pilot: 51.4 +/- 2.9 (n=512)
- On the other's per pilot: 23.8 +/- 2.0 (n=512)
- Chose the named side: 0.55 +/- 0.02 (284/512)
- Chose the other side: 0.34 +/- 0.02 (175/512)
- Chose neither: 0.10 +/- 0.01 (53/512)
- Swap test, flipped with the order: 0.18 +/- 0.02 (47/256)
- Swap test, one side whatever was named: 0.63 +/- 0.03 (161/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.129 | unset |
| goto_lift | 0.009 | unset |
| attack_target_hit | 0.812 | unset |
| attack_side | 0.531 | unset |
| attack_flip | 0.180 | unset |
| defend_more_on_named | 0.641 | unset |
| defend_side | 0.555 | unset |
| defend_flip | 0.184 | unset |
