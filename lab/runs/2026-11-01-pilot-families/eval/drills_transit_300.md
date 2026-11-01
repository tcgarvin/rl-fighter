# Order drills: transit_300

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

Pilot `policy:ppo_bc_300.pt`, seed 500000, sim version 6. Overall: 0.81 +/- 0.01 (872/1074) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.70 +/- 0.02 (395/562; 98 killed first, not counted)
- Same seeds, order hidden: 0.11 +/- 0.01 (63/565; 95 killed first, not counted)
- Lift from seeing the order: +0.59
- Near: 0.70 +/- 0.03 (234/333; 22 killed first, not counted)
- Far: 0.70 +/- 0.03 (161/229; 76 killed first, not counted)
- Enemies around the route: 0.74 +/- 0.03 (219/294; 52 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.98 +/- 0.01 (503/512)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.01 (194/198)
- Swap test, flipped, groups flying at the pilots: 0.48 +/- 0.07 (28/58)
- Damage on the named target per pilot: 62.4 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 32.4 +/- 2.2 (n=512)
- Chose the named side: 0.92 +/- 0.01 (471/512)
- Chose the other side: 0.04 +/- 0.01 (18/512)
- Chose neither: 0.04 +/- 0.01 (23/512)
- Swap test, flipped with the order: 0.87 +/- 0.02 (222/256)
- Swap test, one side whatever was named: 0.06 +/- 0.01 (15/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.98 +/- 0.01 (501/512)
- On the named ward's attackers per pilot: 67.3 +/- 3.4 (n=512)
- On the other's per pilot: 1.9 +/- 0.4 (n=512)
- Chose the named side: 1.00 +/- 0.00 (511/512)
- Chose the other side: 0.00 +/- 0.00 (1/512)
- Chose neither: 0.00 +/- 0.00 (0/512)
- Swap test, flipped with the order: 1.00 +/- 0.00 (255/256)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (1/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.703 | unset |
| goto_lift | 0.591 | unset |
| attack_target_hit | 0.982 | unset |
| attack_side | 0.920 | unset |
| attack_flip | 0.867 | unset |
| defend_more_on_named | 0.979 | unset |
| defend_side | 0.998 | unset |
| defend_flip | 0.996 | unset |
