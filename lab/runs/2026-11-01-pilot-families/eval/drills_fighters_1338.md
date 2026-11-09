# Order drills: fighters_1338

**Gate: fail.** fighters_1338 failed the drill gate: goto_arrival, goto_lift, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_1338.pt`, seed 500000, sim version 6. Overall: 0.42 +/- 0.02 (460/1085) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.24 +/- 0.02 (137/573; 87 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.01 (98/610; 50 killed first, not counted)
- Lift from seeing the order: +0.08
- Near: 0.29 +/- 0.03 (95/328; 27 killed first, not counted)
- Far: 0.17 +/- 0.02 (42/245; 60 killed first, not counted)
- Enemies around the route: 0.27 +/- 0.03 (83/302; 44 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.93 +/- 0.01 (475/512)
- Swap test, flipped, groups busy with a freighter: 0.66 +/- 0.03 (131/198)
- Swap test, flipped, groups flying at the pilots: 0.34 +/- 0.06 (20/58)
- Damage on the named target per pilot: 60.8 +/- 3.0 (n=512)
- On other enemies per pilot (not judged): 73.4 +/- 3.4 (n=512)
- Chose the named side: 0.79 +/- 0.02 (402/512)
- Chose the other side: 0.12 +/- 0.01 (63/512)
- Chose neither: 0.09 +/- 0.01 (47/512)
- Swap test, flipped with the order: 0.59 +/- 0.03 (151/256)
- Swap test, one side whatever was named: 0.24 +/- 0.03 (62/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.80 +/- 0.02 (410/512)
- On the named ward's attackers per pilot: 89.4 +/- 3.8 (n=512)
- On the other's per pilot: 27.5 +/- 2.5 (n=512)
- Chose the named side: 0.83 +/- 0.02 (426/512)
- Chose the other side: 0.11 +/- 0.01 (56/512)
- Chose neither: 0.06 +/- 0.01 (30/512)
- Swap test, flipped with the order: 0.67 +/- 0.03 (172/256)
- Swap test, one side whatever was named: 0.21 +/- 0.03 (54/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.239 | failed |
| goto_lift | 0.078 | failed |
| attack_target_hit | 0.928 | met |
| attack_side | 0.785 | met |
| attack_flip | 0.590 | failed |
| defend_more_on_named | 0.801 | failed |
| defend_side | 0.832 | failed |
| defend_flip | 0.672 | failed |
