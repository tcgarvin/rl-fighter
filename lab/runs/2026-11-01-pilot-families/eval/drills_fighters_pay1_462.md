# Order drills: fighters_pay1_462

**Gate: fail.** fighters_pay1_462 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_462.pt`, seed 500000, sim version 6. Overall: 0.21 +/- 0.01 (219/1029) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.20 +/- 0.02 (102/517; 143 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.02 (85/564; 96 killed first, not counted)
- Lift from seeing the order: +0.05
- Near: 0.26 +/- 0.02 (81/314; 41 killed first, not counted)
- Far: 0.10 +/- 0.02 (21/203; 102 killed first, not counted)
- Enemies around the route: 0.26 +/- 0.03 (71/275; 71 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.85 +/- 0.02 (436/512)
- Swap test, flipped, groups busy with a freighter: 0.23 +/- 0.03 (46/198)
- Swap test, flipped, groups flying at the pilots: 0.29 +/- 0.06 (17/58)
- Damage on the named target per pilot: 56.4 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 101.1 +/- 4.3 (n=512)
- Chose the named side: 0.60 +/- 0.02 (308/512)
- Chose the other side: 0.30 +/- 0.02 (153/512)
- Chose neither: 0.10 +/- 0.01 (51/512)
- Swap test, flipped with the order: 0.25 +/- 0.03 (63/256)
- Swap test, one side whatever was named: 0.55 +/- 0.03 (142/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.57 +/- 0.02 (293/512)
- On the named ward's attackers per pilot: 81.2 +/- 3.8 (n=512)
- On the other's per pilot: 60.5 +/- 3.4 (n=512)
- Chose the named side: 0.58 +/- 0.02 (296/512)
- Chose the other side: 0.33 +/- 0.02 (168/512)
- Chose neither: 0.09 +/- 0.01 (48/512)
- Swap test, flipped with the order: 0.21 +/- 0.03 (54/256)
- Swap test, one side whatever was named: 0.63 +/- 0.03 (161/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.197 | failed |
| goto_lift | 0.047 | failed |
| attack_target_hit | 0.852 | failed |
| attack_side | 0.602 | failed |
| attack_flip | 0.246 | failed |
| defend_more_on_named | 0.572 | failed |
| defend_side | 0.578 | failed |
| defend_flip | 0.211 | failed |
