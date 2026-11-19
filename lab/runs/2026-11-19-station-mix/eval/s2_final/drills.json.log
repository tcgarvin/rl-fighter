# Order drills: s2_final

**Gate: fail.** s2_final failed the drill gate: defend_more_on_named.

Pilot `policy:ppo_bc_2447.pt`, seed 500000, sim version 9. Overall: 0.86 +/- 0.02 (228/264) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (118/136; 17 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (20/132; 21 killed first, not counted)
- Lift from seeing the order: +0.72
- Near: 0.83 +/- 0.04 (59/71; 8 killed first, not counted)
- Far: 0.91 +/- 0.04 (59/65; 9 killed first, not counted)
- Enemies around the route: 0.85 +/- 0.04 (63/74; 11 killed first, not counted)
- Deadline in the order: 0.91 (84/92)
- No deadline (judged by 2x + 10 s): 0.77 (34/44)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.89 (25/28) |
| medium (2.5 to 4.5) | 0.85 (29/34) |
| loose (over 4.5) | 1.00 (30/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 136 | 92 | 44 | 10 |
| In time | 0.87 | 0.91 | 0.77 | 0.90 |
| Near miss (within 60 m) | 0.12 | 0.09 | 0.20 | 0.10 |
| At the enemy instead | 0.01 | 0.00 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.94 +/- 0.02 (120/128)
- Swap test, flipped, groups busy with a freighter: 0.87 +/- 0.05 (39/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 51.8 +/- 5.1 (n=128)
- On other enemies per pilot (not judged): 43.6 +/- 4.5 (n=128)
- Chose the named side: 0.89 +/- 0.03 (114/128)
- Chose the other side: 0.05 +/- 0.02 (7/128)
- Chose neither: 0.05 +/- 0.02 (7/128)
- Swap test, flipped with the order: 0.80 +/- 0.05 (51/64)
- Swap test, one side whatever was named: 0.11 +/- 0.04 (7/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.03 (108/128)
- On the named ward's attackers per pilot: 70.4 +/- 6.0 (n=128)
- On the other's per pilot: 7.2 +/- 1.9 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.868 | met |
| goto_lift | 0.716 | met |
| attack_target_hit | 0.938 | met |
| attack_side | 0.891 | met |
| attack_flip | 0.797 | met |
| defend_more_on_named | 0.844 | failed |
| defend_side | 0.961 | met |
| defend_flip | 0.922 | met |
