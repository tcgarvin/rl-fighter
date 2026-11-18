# Order drills: mixed_all_725

**Gate: pass.** mixed_all_725 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_725.pt`, seed 500000, sim version 8. Overall: 0.88 +/- 0.02 (233/265) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.85 +/- 0.03 (117/137; 16 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.03 (23/135; 18 killed first, not counted)
- Lift from seeing the order: +0.68
- Near: 0.81 +/- 0.05 (57/70; 9 killed first, not counted)
- Far: 0.90 +/- 0.04 (60/67; 7 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.04 (64/76; 9 killed first, not counted)
- Deadline in the order: 0.89 (82/92)
- No deadline (judged by 2x + 10 s): 0.78 (35/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.84 (21/25) |
| medium (2.5 to 4.5) | 0.89 (32/36) |
| loose (over 4.5) | 0.94 (29/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 137 | 92 | 45 | 11 |
| In time | 0.85 | 0.89 | 0.78 | 0.82 |
| Near miss (within 60 m) | 0.13 | 0.10 | 0.20 | 0.18 |
| At the enemy instead | 0.01 | 0.01 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (122/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 64.5 +/- 6.3 (n=128)
- On other enemies per pilot (not judged): 45.7 +/- 4.6 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.86 +/- 0.03 (110/128)
- On the named ward's attackers per pilot: 78.4 +/- 6.3 (n=128)
- On the other's per pilot: 8.3 +/- 2.2 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.854 | met |
| goto_lift | 0.684 | met |
| attack_target_hit | 0.953 | met |
| attack_side | 0.953 | met |
| attack_flip | 0.906 | met |
| defend_more_on_named | 0.859 | met |
| defend_side | 0.953 | met |
| defend_flip | 0.906 | met |
