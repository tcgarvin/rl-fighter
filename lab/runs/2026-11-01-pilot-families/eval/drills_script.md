# Order drills: script

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

Pilot `script`, seed 500000, sim version 6. Overall: 0.99 +/- 0.00 (1116/1124) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 1.00 +/- 0.00 (611/612; 48 killed first, not counted)
- Hidden pass not run (the script flies orders it cannot see).
- Near: 1.00 +/- 0.00 (347/348; 7 killed first, not counted)
- Far: 1.00 +/- 0.00 (264/264; 41 killed first, not counted)
- Enemies around the route: 1.00 +/- 0.00 (315/316; 30 killed first, not counted)

## Attack (256 swap pairs)

- Any damage on the named target: 0.98 +/- 0.01 (504/512)
- Swap test, flipped, groups busy with a freighter: 0.99 +/- 0.01 (196/198)
- Swap test, flipped, groups flying at the pilots: 0.91 +/- 0.04 (53/58)
- Damage on the named target per pilot: 62.2 +/- 2.3 (n=512)
- On other enemies per pilot (not judged): 44.4 +/- 1.8 (n=512)
- Chose the named side: 0.99 +/- 0.01 (505/512)
- Chose the other side: 0.01 +/- 0.00 (3/512)
- Chose neither: 0.01 +/- 0.00 (4/512)
- Swap test, flipped with the order: 0.97 +/- 0.01 (249/256)
- Swap test, one side whatever was named: 0.01 +/- 0.01 (3/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.99 +/- 0.01 (505/512)
- On the named ward's attackers per pilot: 89.1 +/- 2.4 (n=512)
- On the other's per pilot: 2.1 +/- 0.4 (n=512)
- Chose the named side: 1.00 +/- 0.00 (512/512)
- Chose the other side: 0.00 +/- 0.00 (0/512)
- Chose neither: 0.00 +/- 0.00 (0/512)
- Swap test, flipped with the order: 1.00 +/- 0.00 (256/256)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (0/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.998 | unset |
| goto_lift | n/a | unset |
| attack_target_hit | 0.984 | unset |
| attack_side | 0.986 | unset |
| attack_flip | 0.973 | unset |
| defend_more_on_named | 0.986 | unset |
| defend_side | 1.000 | unset |
| defend_flip | 1.000 | unset |
