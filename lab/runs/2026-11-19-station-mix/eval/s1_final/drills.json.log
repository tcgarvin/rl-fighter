# Order drills: s1_final

**Gate: pass.** s1_final passed the drill gate: every bar met.

Pilot `policy:ppo_bc_2422.pt`, seed 500000, sim version 9. Overall: 0.87 +/- 0.02 (231/265) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.86 +/- 0.03 (118/137; 16 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.03 (23/137; 16 killed first, not counted)
- Lift from seeing the order: +0.69
- Near: 0.82 +/- 0.05 (58/71; 8 killed first, not counted)
- Far: 0.91 +/- 0.04 (60/66; 8 killed first, not counted)
- Enemies around the route: 0.82 +/- 0.05 (58/71; 14 killed first, not counted)
- Deadline in the order: 0.90 (83/92)
- No deadline (judged by 2x + 10 s): 0.78 (35/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (22/26) |
| medium (2.5 to 4.5) | 0.89 (32/36) |
| loose (over 4.5) | 0.97 (29/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 137 | 92 | 45 | 10 |
| In time | 0.86 | 0.90 | 0.78 | 0.70 |
| Near miss (within 60 m) | 0.11 | 0.07 | 0.20 | 0.10 |
| At the enemy instead | 0.02 | 0.02 | 0.02 | 0.20 |
| Neither | 0.01 | 0.01 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.98 +/- 0.01 (125/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 62.0 +/- 6.1 (n=128)
- On other enemies per pilot (not judged): 50.5 +/- 4.8 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.05 +/- 0.02 (7/128)
- Swap test, flipped with the order: 0.86 +/- 0.04 (55/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (113/128)
- On the named ward's attackers per pilot: 78.1 +/- 6.7 (n=128)
- On the other's per pilot: 8.0 +/- 1.8 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.02 +/- 0.01 (3/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.861 | met |
| goto_lift | 0.693 | met |
| attack_target_hit | 0.977 | met |
| attack_side | 0.930 | met |
| attack_flip | 0.859 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.953 | met |
| defend_flip | 0.906 | met |
