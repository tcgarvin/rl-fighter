# Order drills: followers_955

**Gate: fail.** followers_955 failed the drill gate: goto_arrival, goto_lift.

Pilot `policy:ppo_bc_955.pt`, seed 500000, sim version 6. Overall: 0.64 +/- 0.01 (685/1074) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.50 +/- 0.02 (281/562; 98 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.02 (95/577; 83 killed first, not counted)
- Lift from seeing the order: +0.34
- Near: 0.55 +/- 0.03 (179/325; 30 killed first, not counted)
- Far: 0.43 +/- 0.03 (102/237; 68 killed first, not counted)
- Enemies around the route: 0.53 +/- 0.03 (154/289; 57 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.97 +/- 0.01 (496/512)
- Swap test, flipped, groups busy with a freighter: 0.85 +/- 0.03 (169/198)
- Swap test, flipped, groups flying at the pilots: 0.66 +/- 0.06 (38/58)
- Damage on the named target per pilot: 72.2 +/- 3.3 (n=512)
- On other enemies per pilot (not judged): 65.0 +/- 3.2 (n=512)
- Chose the named side: 0.90 +/- 0.01 (459/512)
- Chose the other side: 0.05 +/- 0.01 (26/512)
- Chose neither: 0.05 +/- 0.01 (27/512)
- Swap test, flipped with the order: 0.81 +/- 0.02 (207/256)
- Swap test, one side whatever was named: 0.09 +/- 0.02 (23/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.87 +/- 0.01 (446/512)
- On the named ward's attackers per pilot: 100.8 +/- 4.1 (n=512)
- On the other's per pilot: 14.3 +/- 1.6 (n=512)
- Chose the named side: 0.88 +/- 0.01 (449/512)
- Chose the other side: 0.05 +/- 0.01 (25/512)
- Chose neither: 0.07 +/- 0.01 (38/512)
- Swap test, flipped with the order: 0.77 +/- 0.03 (197/256)
- Swap test, one side whatever was named: 0.10 +/- 0.02 (25/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.500 | failed |
| goto_lift | 0.335 | failed |
| attack_target_hit | 0.969 | met |
| attack_side | 0.896 | met |
| attack_flip | 0.809 | met |
| defend_more_on_named | 0.871 | met |
| defend_side | 0.877 | met |
| defend_flip | 0.770 | met |
