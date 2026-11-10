# Order drills: followers_1793

**Gate: fail.** followers_1793 failed the drill gate: goto_arrival, goto_lift, defend_more_on_named, defend_flip.

Pilot `policy:ppo_bc_1793.pt`, seed 500000, sim version 7. Overall: 0.55 +/- 0.02 (596/1085) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.39 +/- 0.02 (222/573; 87 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.01 (77/604; 56 killed first, not counted)
- Lift from seeing the order: +0.26
- Near: 0.38 +/- 0.03 (125/328; 27 killed first, not counted)
- Far: 0.40 +/- 0.03 (97/245; 60 killed first, not counted)
- Enemies around the route: 0.41 +/- 0.03 (123/298; 48 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.94 +/- 0.01 (480/512)
- Swap test, flipped, groups busy with a freighter: 0.80 +/- 0.03 (158/198)
- Swap test, flipped, groups flying at the pilots: 0.47 +/- 0.07 (27/58)
- Damage on the named target per pilot: 57.6 +/- 2.7 (n=512)
- On other enemies per pilot (not judged): 52.5 +/- 2.9 (n=512)
- Chose the named side: 0.85 +/- 0.02 (435/512)
- Chose the other side: 0.08 +/- 0.01 (39/512)
- Chose neither: 0.07 +/- 0.01 (38/512)
- Swap test, flipped with the order: 0.72 +/- 0.03 (185/256)
- Swap test, one side whatever was named: 0.14 +/- 0.02 (36/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.02 (429/512)
- On the named ward's attackers per pilot: 80.9 +/- 3.5 (n=512)
- On the other's per pilot: 15.4 +/- 1.8 (n=512)
- Chose the named side: 0.86 +/- 0.02 (438/512)
- Chose the other side: 0.07 +/- 0.01 (37/512)
- Chose neither: 0.07 +/- 0.01 (37/512)
- Swap test, flipped with the order: 0.74 +/- 0.03 (189/256)
- Swap test, one side whatever was named: 0.13 +/- 0.02 (34/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.387 | failed |
| goto_lift | 0.260 | failed |
| attack_target_hit | 0.938 | met |
| attack_side | 0.850 | met |
| attack_flip | 0.723 | met |
| defend_more_on_named | 0.838 | failed |
| defend_side | 0.855 | met |
| defend_flip | 0.738 | failed |
