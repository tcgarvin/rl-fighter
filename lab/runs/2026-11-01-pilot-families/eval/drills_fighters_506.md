# Order drills: fighters_506

**Gate: fail.** fighters_506 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_506.pt`, seed 500000, sim version 6. Overall: 0.28 +/- 0.01 (282/1023) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.21 +/- 0.02 (107/511; 149 killed first, not counted)
- Same seeds, order hidden: 0.14 +/- 0.01 (78/562; 98 killed first, not counted)
- Lift from seeing the order: +0.07
- Near: 0.30 +/- 0.03 (91/301; 54 killed first, not counted)
- Far: 0.08 +/- 0.02 (16/210; 95 killed first, not counted)
- Enemies around the route: 0.25 +/- 0.03 (69/277; 69 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.86 +/- 0.02 (442/512)
- Swap test, flipped, groups busy with a freighter: 0.35 +/- 0.03 (70/198)
- Swap test, flipped, groups flying at the pilots: 0.22 +/- 0.05 (13/58)
- Damage on the named target per pilot: 53.9 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 91.2 +/- 4.0 (n=512)
- Chose the named side: 0.63 +/- 0.02 (321/512)
- Chose the other side: 0.23 +/- 0.02 (120/512)
- Chose neither: 0.14 +/- 0.02 (71/512)
- Swap test, flipped with the order: 0.32 +/- 0.03 (83/256)
- Swap test, one side whatever was named: 0.46 +/- 0.03 (117/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.62 +/- 0.02 (320/512)
- On the named ward's attackers per pilot: 83.0 +/- 4.0 (n=512)
- On the other's per pilot: 52.7 +/- 3.2 (n=512)
- Chose the named side: 0.66 +/- 0.02 (336/512)
- Chose the other side: 0.25 +/- 0.02 (126/512)
- Chose neither: 0.10 +/- 0.01 (50/512)
- Swap test, flipped with the order: 0.36 +/- 0.03 (92/256)
- Swap test, one side whatever was named: 0.47 +/- 0.03 (121/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.209 | failed |
| goto_lift | 0.071 | failed |
| attack_target_hit | 0.863 | failed |
| attack_side | 0.627 | failed |
| attack_flip | 0.324 | failed |
| defend_more_on_named | 0.625 | failed |
| defend_side | 0.656 | failed |
| defend_flip | 0.359 | failed |
