# Order drills: fighters_fire4_1827

**Gate: fail.** fighters_fire4_1827 failed the drill gate: goto_arrival, goto_lift, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_1827.pt`, seed 500000, sim version 7. Overall: 0.40 +/- 0.01 (426/1077) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.22 +/- 0.02 (126/565; 95 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.02 (103/599; 61 killed first, not counted)
- Lift from seeing the order: +0.05
- Near: 0.23 +/- 0.02 (73/321; 34 killed first, not counted)
- Far: 0.22 +/- 0.03 (53/244; 61 killed first, not counted)
- Enemies around the route: 0.25 +/- 0.03 (74/294; 52 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.91 +/- 0.01 (464/512)
- Swap test, flipped, groups busy with a freighter: 0.66 +/- 0.03 (131/198)
- Swap test, flipped, groups flying at the pilots: 0.24 +/- 0.06 (14/58)
- Damage on the named target per pilot: 56.0 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 59.5 +/- 3.1 (n=512)
- Chose the named side: 0.75 +/- 0.02 (384/512)
- Chose the other side: 0.12 +/- 0.01 (64/512)
- Chose neither: 0.12 +/- 0.01 (64/512)
- Swap test, flipped with the order: 0.57 +/- 0.03 (145/256)
- Swap test, one side whatever was named: 0.22 +/- 0.03 (56/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.79 +/- 0.02 (404/512)
- On the named ward's attackers per pilot: 78.2 +/- 3.7 (n=512)
- On the other's per pilot: 17.7 +/- 1.9 (n=512)
- Chose the named side: 0.79 +/- 0.02 (402/512)
- Chose the other side: 0.12 +/- 0.01 (62/512)
- Chose neither: 0.09 +/- 0.01 (48/512)
- Swap test, flipped with the order: 0.61 +/- 0.03 (155/256)
- Swap test, one side whatever was named: 0.21 +/- 0.03 (55/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.223 | failed |
| goto_lift | 0.051 | failed |
| attack_target_hit | 0.906 | met |
| attack_side | 0.750 | met |
| attack_flip | 0.566 | failed |
| defend_more_on_named | 0.789 | failed |
| defend_side | 0.785 | failed |
| defend_flip | 0.605 | failed |
