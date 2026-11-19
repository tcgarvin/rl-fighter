# Order drills: s1_725

**Gate: pass.** s1_725 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_725.pt`, seed 500000, sim version 9. Overall: 0.87 +/- 0.02 (232/268) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.86 +/- 0.03 (120/140; 13 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (22/136; 17 killed first, not counted)
- Lift from seeing the order: +0.70
- Near: 0.82 +/- 0.05 (59/72; 7 killed first, not counted)
- Far: 0.90 +/- 0.04 (61/68; 6 killed first, not counted)
- Enemies around the route: 0.83 +/- 0.04 (62/75; 10 killed first, not counted)
- Deadline in the order: 0.84 (79/94)
- No deadline (judged by 2x + 10 s): 0.89 (41/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.80 (20/25) |
| medium (2.5 to 4.5) | 0.79 (31/39) |
| loose (over 4.5) | 0.93 (28/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 140 | 94 | 46 | 11 |
| In time | 0.86 | 0.84 | 0.89 | 0.73 |
| Near miss (within 60 m) | 0.14 | 0.15 | 0.11 | 0.18 |
| At the enemy instead | 0.01 | 0.01 | 0.00 | 0.09 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 1.00 +/- 0.00 (128/128)
- Swap test, flipped, groups busy with a freighter: 1.00 +/- 0.00 (45/45)
- Swap test, flipped, groups flying at the pilots: 0.58 +/- 0.11 (11/19)
- Damage on the named target per pilot: 62.6 +/- 5.4 (n=128)
- On other enemies per pilot (not judged): 53.0 +/- 4.9 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.89 +/- 0.03 (114/128)
- On the named ward's attackers per pilot: 77.8 +/- 7.0 (n=128)
- On the other's per pilot: 7.2 +/- 2.0 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.05 +/- 0.02 (7/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.11 +/- 0.04 (7/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.857 | met |
| goto_lift | 0.695 | met |
| attack_target_hit | 1.000 | met |
| attack_side | 0.938 | met |
| attack_flip | 0.875 | met |
| defend_more_on_named | 0.891 | met |
| defend_side | 0.938 | met |
| defend_flip | 0.875 | met |
