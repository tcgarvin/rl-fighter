# Order drills: followers_513

**Gate: pass.** followers_513 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_513.pt`, seed 500000, sim version 6. Overall: 0.74 +/- 0.01 (792/1067) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.62 +/- 0.02 (346/555; 105 killed first, not counted)
- Same seeds, order hidden: 0.18 +/- 0.02 (102/573; 87 killed first, not counted)
- Lift from seeing the order: +0.45
- Near: 0.62 +/- 0.03 (201/323; 32 killed first, not counted)
- Far: 0.62 +/- 0.03 (145/232; 73 killed first, not counted)
- Enemies around the route: 0.63 +/- 0.03 (176/281; 65 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.99 +/- 0.00 (506/512)
- Swap test, flipped, groups busy with a freighter: 0.95 +/- 0.02 (188/198)
- Swap test, flipped, groups flying at the pilots: 0.64 +/- 0.06 (37/58)
- Damage on the named target per pilot: 69.7 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 43.6 +/- 2.4 (n=512)
- Chose the named side: 0.93 +/- 0.01 (476/512)
- Chose the other side: 0.02 +/- 0.01 (11/512)
- Chose neither: 0.05 +/- 0.01 (25/512)
- Swap test, flipped with the order: 0.88 +/- 0.02 (225/256)
- Swap test, one side whatever was named: 0.03 +/- 0.01 (8/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.95 +/- 0.01 (485/512)
- On the named ward's attackers per pilot: 80.6 +/- 3.5 (n=512)
- On the other's per pilot: 4.6 +/- 0.9 (n=512)
- Chose the named side: 0.93 +/- 0.01 (476/512)
- Chose the other side: 0.02 +/- 0.01 (8/512)
- Chose neither: 0.05 +/- 0.01 (28/512)
- Swap test, flipped with the order: 0.86 +/- 0.02 (221/256)
- Swap test, one side whatever was named: 0.03 +/- 0.01 (8/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.623 | met |
| goto_lift | 0.445 | met |
| attack_target_hit | 0.988 | met |
| attack_side | 0.930 | met |
| attack_flip | 0.879 | met |
| defend_more_on_named | 0.947 | met |
| defend_side | 0.930 | met |
| defend_flip | 0.863 | met |
