# Order drills: scratch_417

**Gate: fail.** scratch_417 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_scratch_417.pt`, seed 500000, sim version 6. Overall: 0.07 +/- 0.01 (76/1078) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.06 +/- 0.01 (32/566; 94 killed first, not counted)
- Same seeds, order hidden: 0.05 +/- 0.01 (28/575; 85 killed first, not counted)
- Lift from seeing the order: +0.01
- Near: 0.10 +/- 0.02 (31/324; 31 killed first, not counted)
- Far: 0.00 +/- 0.00 (1/242; 63 killed first, not counted)
- Enemies around the route: 0.05 +/- 0.01 (16/295; 51 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.48 +/- 0.02 (248/512)
- Swap test, flipped, groups busy with a freighter: 0.10 +/- 0.02 (19/198)
- Swap test, flipped, groups flying at the pilots: 0.03 +/- 0.02 (2/58)
- Damage on the named target per pilot: 4.1 +/- 0.4 (n=512)
- On other enemies per pilot (not judged): 11.5 +/- 0.9 (n=512)
- Chose the named side: 0.38 +/- 0.02 (194/512)
- Chose the other side: 0.43 +/- 0.02 (221/512)
- Chose neither: 0.19 +/- 0.02 (97/512)
- Swap test, flipped with the order: 0.08 +/- 0.02 (21/256)
- Swap test, one side whatever was named: 0.48 +/- 0.03 (123/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.32 +/- 0.02 (166/512)
- On the named ward's attackers per pilot: 3.8 +/- 0.4 (n=512)
- On the other's per pilot: 4.3 +/- 0.4 (n=512)
- Chose the named side: 0.40 +/- 0.02 (205/512)
- Chose the other side: 0.43 +/- 0.02 (220/512)
- Chose neither: 0.17 +/- 0.02 (87/512)
- Swap test, flipped with the order: 0.09 +/- 0.02 (23/256)
- Swap test, one side whatever was named: 0.49 +/- 0.03 (125/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.057 | failed |
| goto_lift | 0.008 | failed |
| attack_target_hit | 0.484 | failed |
| attack_side | 0.379 | failed |
| attack_flip | 0.082 | failed |
| defend_more_on_named | 0.324 | failed |
| defend_side | 0.400 | failed |
| defend_flip | 0.090 | failed |
