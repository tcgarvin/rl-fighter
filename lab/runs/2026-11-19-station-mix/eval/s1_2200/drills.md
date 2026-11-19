# Order drills: s1_2200

**Gate: pass.** s1_2200 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_2200.pt`, seed 500000, sim version 9. Overall: 0.86 +/- 0.02 (224/260) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.83 +/- 0.03 (110/132; 21 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.03 (21/127; 26 killed first, not counted)
- Lift from seeing the order: +0.67
- Near: 0.78 +/- 0.05 (56/72; 7 killed first, not counted)
- Far: 0.90 +/- 0.04 (54/60; 14 killed first, not counted)
- Enemies around the route: 0.78 +/- 0.05 (58/74; 11 killed first, not counted)
- Deadline in the order: 0.88 (77/88)
- No deadline (judged by 2x + 10 s): 0.75 (33/44)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.77 (20/26) |
| medium (2.5 to 4.5) | 0.89 (31/35) |
| loose (over 4.5) | 0.96 (26/27) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 132 | 88 | 44 | 11 |
| In time | 0.83 | 0.88 | 0.75 | 0.82 |
| Near miss (within 60 m) | 0.16 | 0.12 | 0.23 | 0.18 |
| At the enemy instead | 0.01 | 0.00 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.98 +/- 0.01 (126/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 62.2 +/- 5.8 (n=128)
- On other enemies per pilot (not judged): 47.3 +/- 5.0 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.86 +/- 0.04 (55/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.02 (117/128)
- On the named ward's attackers per pilot: 79.8 +/- 6.7 (n=128)
- On the other's per pilot: 6.2 +/- 1.7 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.833 | met |
| goto_lift | 0.668 | met |
| attack_target_hit | 0.984 | met |
| attack_side | 0.922 | met |
| attack_flip | 0.859 | met |
| defend_more_on_named | 0.914 | met |
| defend_side | 0.953 | met |
| defend_flip | 0.922 | met |
