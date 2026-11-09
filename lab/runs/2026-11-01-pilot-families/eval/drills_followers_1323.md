# Order drills: followers_1323

**Gate: fail.** followers_1323 failed the drill gate: goto_arrival, goto_lift, defend_more_on_named.

Pilot `policy:ppo_bc_1323.pt`, seed 500000, sim version 6. Overall: 0.63 +/- 0.01 (697/1100) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.47 +/- 0.02 (274/588; 72 killed first, not counted)
- Same seeds, order hidden: 0.18 +/- 0.02 (109/591; 69 killed first, not counted)
- Lift from seeing the order: +0.28
- Near: 0.47 +/- 0.03 (154/328; 27 killed first, not counted)
- Far: 0.46 +/- 0.03 (120/260; 45 killed first, not counted)
- Enemies around the route: 0.51 +/- 0.03 (157/310; 36 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.97 +/- 0.01 (497/512)
- Swap test, flipped, groups busy with a freighter: 0.87 +/- 0.02 (173/198)
- Swap test, flipped, groups flying at the pilots: 0.59 +/- 0.06 (34/58)
- Damage on the named target per pilot: 66.7 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 64.7 +/- 3.2 (n=512)
- Chose the named side: 0.90 +/- 0.01 (459/512)
- Chose the other side: 0.06 +/- 0.01 (29/512)
- Chose neither: 0.05 +/- 0.01 (24/512)
- Swap test, flipped with the order: 0.81 +/- 0.02 (207/256)
- Swap test, one side whatever was named: 0.10 +/- 0.02 (26/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.02 (432/512)
- On the named ward's attackers per pilot: 97.7 +/- 4.0 (n=512)
- On the other's per pilot: 17.8 +/- 1.7 (n=512)
- Chose the named side: 0.92 +/- 0.01 (472/512)
- Chose the other side: 0.04 +/- 0.01 (19/512)
- Chose neither: 0.04 +/- 0.01 (21/512)
- Swap test, flipped with the order: 0.84 +/- 0.02 (216/256)
- Swap test, one side whatever was named: 0.07 +/- 0.02 (19/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.466 | failed |
| goto_lift | 0.282 | failed |
| attack_target_hit | 0.971 | met |
| attack_side | 0.896 | met |
| attack_flip | 0.809 | met |
| defend_more_on_named | 0.844 | failed |
| defend_side | 0.922 | met |
| defend_flip | 0.844 | met |
