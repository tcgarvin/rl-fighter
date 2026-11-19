# Order drills: kite_2200

**Gate: pass.** kite_2200 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_2200.pt`, seed 500000, sim version 9. Overall: 0.90 +/- 0.02 (238/263) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.86 +/- 0.03 (116/135; 18 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (19/130; 23 killed first, not counted)
- Lift from seeing the order: +0.71
- Near: 0.79 +/- 0.05 (58/73; 6 killed first, not counted)
- Far: 0.94 +/- 0.03 (58/62; 12 killed first, not counted)
- Enemies around the route: 0.82 +/- 0.04 (61/74; 11 killed first, not counted)
- Deadline in the order: 0.85 (78/92)
- No deadline (judged by 2x + 10 s): 0.88 (38/43)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (22/26) |
| medium (2.5 to 4.5) | 0.78 (31/40) |
| loose (over 4.5) | 0.96 (25/26) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 135 | 92 | 43 | 10 |
| In time | 0.86 | 0.85 | 0.88 | 0.80 |
| Near miss (within 60 m) | 0.13 | 0.14 | 0.12 | 0.20 |
| At the enemy instead | 0.01 | 0.01 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.98 +/- 0.01 (125/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.95 +/- 0.05 (18/19)
- Damage on the named target per pilot: 69.9 +/- 7.5 (n=128)
- On other enemies per pilot (not judged): 55.0 +/- 5.4 (n=128)
- Chose the named side: 0.98 +/- 0.01 (126/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.97 +/- 0.02 (62/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.92 +/- 0.02 (118/128)
- On the named ward's attackers per pilot: 88.6 +/- 6.9 (n=128)
- On the other's per pilot: 3.0 +/- 1.1 (n=128)
- Chose the named side: 0.97 +/- 0.02 (124/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.94 +/- 0.03 (60/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.859 | met |
| goto_lift | 0.713 | met |
| attack_target_hit | 0.977 | met |
| attack_side | 0.984 | met |
| attack_flip | 0.969 | met |
| defend_more_on_named | 0.922 | met |
| defend_side | 0.969 | met |
| defend_flip | 0.938 | met |
