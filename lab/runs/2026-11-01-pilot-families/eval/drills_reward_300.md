# Order drills: reward_300

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

Pilot `policy:ppo_bc_300.pt`, seed 500000, sim version 6. Overall: 0.12 +/- 0.01 (124/1063) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.12 +/- 0.01 (66/551; 109 killed first, not counted)
- Same seeds, order hidden: 0.11 +/- 0.01 (62/569; 91 killed first, not counted)
- Lift from seeing the order: +0.01
- Near: 0.20 +/- 0.02 (64/320; 35 killed first, not counted)
- Far: 0.01 +/- 0.01 (2/231; 74 killed first, not counted)
- Enemies around the route: 0.16 +/- 0.02 (49/298; 48 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.75 +/- 0.02 (385/512)
- Swap test, flipped, groups busy with a freighter: 0.14 +/- 0.02 (28/198)
- Swap test, flipped, groups flying at the pilots: 0.07 +/- 0.03 (4/58)
- Damage on the named target per pilot: 48.7 +/- 3.1 (n=512)
- On other enemies per pilot (not judged): 97.2 +/- 4.4 (n=512)
- Chose the named side: 0.50 +/- 0.02 (258/512)
- Chose the other side: 0.38 +/- 0.02 (195/512)
- Chose neither: 0.12 +/- 0.01 (59/512)
- Swap test, flipped with the order: 0.12 +/- 0.02 (32/256)
- Swap test, one side whatever was named: 0.68 +/- 0.03 (174/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.54 +/- 0.02 (276/512)
- On the named ward's attackers per pilot: 69.7 +/- 3.9 (n=512)
- On the other's per pilot: 63.5 +/- 3.8 (n=512)
- Chose the named side: 0.50 +/- 0.02 (257/512)
- Chose the other side: 0.42 +/- 0.02 (214/512)
- Chose neither: 0.08 +/- 0.01 (41/512)
- Swap test, flipped with the order: 0.10 +/- 0.02 (26/256)
- Swap test, one side whatever was named: 0.77 +/- 0.03 (198/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.120 | unset |
| goto_lift | 0.011 | unset |
| attack_target_hit | 0.752 | unset |
| attack_side | 0.504 | unset |
| attack_flip | 0.125 | unset |
| defend_more_on_named | 0.539 | unset |
| defend_side | 0.502 | unset |
| defend_flip | 0.102 | unset |
