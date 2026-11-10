# Order drills: fighters_1832

**Gate: fail.** fighters_1832 failed the drill gate: goto_arrival, goto_lift, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_1832.pt`, seed 500000, sim version 7. Overall: 0.45 +/- 0.02 (484/1079) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.26 +/- 0.02 (146/567; 93 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.01 (80/607; 53 killed first, not counted)
- Lift from seeing the order: +0.13
- Near: 0.30 +/- 0.03 (98/324; 31 killed first, not counted)
- Far: 0.20 +/- 0.03 (48/243; 62 killed first, not counted)
- Enemies around the route: 0.28 +/- 0.03 (83/292; 54 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.91 +/- 0.01 (464/512)
- Swap test, flipped, groups busy with a freighter: 0.72 +/- 0.03 (143/198)
- Swap test, flipped, groups flying at the pilots: 0.41 +/- 0.06 (24/58)
- Damage on the named target per pilot: 54.2 +/- 2.6 (n=512)
- On other enemies per pilot (not judged): 61.2 +/- 3.2 (n=512)
- Chose the named side: 0.81 +/- 0.02 (417/512)
- Chose the other side: 0.12 +/- 0.01 (61/512)
- Chose neither: 0.07 +/- 0.01 (34/512)
- Swap test, flipped with the order: 0.65 +/- 0.03 (167/256)
- Swap test, one side whatever was named: 0.22 +/- 0.03 (57/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.83 +/- 0.02 (425/512)
- On the named ward's attackers per pilot: 80.9 +/- 3.4 (n=512)
- On the other's per pilot: 19.9 +/- 2.0 (n=512)
- Chose the named side: 0.82 +/- 0.02 (418/512)
- Chose the other side: 0.10 +/- 0.01 (51/512)
- Chose neither: 0.08 +/- 0.01 (43/512)
- Swap test, flipped with the order: 0.67 +/- 0.03 (171/256)
- Swap test, one side whatever was named: 0.18 +/- 0.02 (45/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.257 | failed |
| goto_lift | 0.126 | failed |
| attack_target_hit | 0.906 | met |
| attack_side | 0.814 | met |
| attack_flip | 0.652 | failed |
| defend_more_on_named | 0.830 | failed |
| defend_side | 0.816 | failed |
| defend_flip | 0.668 | failed |
