# Order drills: fighters_959

**Gate: fail.** fighters_959 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_959.pt`, seed 500000, sim version 6. Overall: 0.41 +/- 0.02 (434/1063) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.30 +/- 0.02 (163/551; 109 killed first, not counted)
- Same seeds, order hidden: 0.14 +/- 0.01 (83/589; 71 killed first, not counted)
- Lift from seeing the order: +0.15
- Near: 0.36 +/- 0.03 (117/321; 34 killed first, not counted)
- Far: 0.20 +/- 0.03 (46/230; 75 killed first, not counted)
- Enemies around the route: 0.34 +/- 0.03 (96/285; 61 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.89 +/- 0.01 (455/512)
- Swap test, flipped, groups busy with a freighter: 0.54 +/- 0.04 (106/198)
- Swap test, flipped, groups flying at the pilots: 0.38 +/- 0.06 (22/58)
- Damage on the named target per pilot: 58.5 +/- 3.1 (n=512)
- On other enemies per pilot (not judged): 84.6 +/- 3.9 (n=512)
- Chose the named side: 0.73 +/- 0.02 (376/512)
- Chose the other side: 0.17 +/- 0.02 (86/512)
- Chose neither: 0.10 +/- 0.01 (50/512)
- Swap test, flipped with the order: 0.50 +/- 0.03 (128/256)
- Swap test, one side whatever was named: 0.31 +/- 0.03 (79/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.71 +/- 0.02 (361/512)
- On the named ward's attackers per pilot: 84.9 +/- 3.7 (n=512)
- On the other's per pilot: 43.0 +/- 3.3 (n=512)
- Chose the named side: 0.76 +/- 0.02 (391/512)
- Chose the other side: 0.16 +/- 0.02 (81/512)
- Chose neither: 0.08 +/- 0.01 (40/512)
- Swap test, flipped with the order: 0.56 +/- 0.03 (143/256)
- Swap test, one side whatever was named: 0.30 +/- 0.03 (77/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.296 | failed |
| goto_lift | 0.155 | failed |
| attack_target_hit | 0.889 | failed |
| attack_side | 0.734 | failed |
| attack_flip | 0.500 | failed |
| defend_more_on_named | 0.705 | failed |
| defend_side | 0.764 | failed |
| defend_flip | 0.559 | failed |
