# Order drills: fighters_pay1_v8_351

**Gate: fail.** fighters_pay1_v8_351 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_351.pt`, seed 500000, sim version 8. Overall: 0.30 +/- 0.01 (324/1075) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.31 +/- 0.02 (173/563; 97 killed first, not counted)
- Same seeds, order hidden: 0.19 +/- 0.02 (107/565; 95 killed first, not counted)
- Lift from seeing the order: +0.12
- Near: 0.30 +/- 0.03 (95/322; 33 killed first, not counted)
- Far: 0.32 +/- 0.03 (78/241; 64 killed first, not counted)
- Enemies around the route: 0.33 +/- 0.03 (99/296; 50 killed first, not counted)
- Deadline in the order: 0.34 (137/406)
- No deadline (judged by 2x + 10 s): 0.23 (36/157)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.20 (18/91) |
| medium (2.5 to 4.5) | 0.30 (53/179) |
| loose (over 4.5) | 0.49 (66/136) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 563 | 406 | 157 | 37 |
| In time | 0.31 | 0.34 | 0.23 | 0.19 |
| Near miss (within 60 m) | 0.24 | 0.25 | 0.20 | 0.19 |
| At the enemy instead | 0.44 | 0.39 | 0.55 | 0.62 |
| Neither | 0.02 | 0.02 | 0.02 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.86 +/- 0.02 (442/512)
- Swap test, flipped, groups busy with a freighter: 0.29 +/- 0.03 (57/198)
- Swap test, flipped, groups flying at the pilots: 0.16 +/- 0.05 (9/58)
- Damage on the named target per pilot: 54.9 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 86.4 +/- 3.7 (n=512)
- Chose the named side: 0.60 +/- 0.02 (305/512)
- Chose the other side: 0.26 +/- 0.02 (132/512)
- Chose neither: 0.15 +/- 0.02 (75/512)
- Swap test, flipped with the order: 0.26 +/- 0.03 (66/256)
- Swap test, one side whatever was named: 0.48 +/- 0.03 (122/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.67 +/- 0.02 (342/512)
- On the named ward's attackers per pilot: 82.9 +/- 4.0 (n=512)
- On the other's per pilot: 43.8 +/- 3.0 (n=512)
- Chose the named side: 0.64 +/- 0.02 (330/512)
- Chose the other side: 0.22 +/- 0.02 (115/512)
- Chose neither: 0.13 +/- 0.01 (67/512)
- Swap test, flipped with the order: 0.33 +/- 0.03 (85/256)
- Swap test, one side whatever was named: 0.43 +/- 0.03 (110/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.307 | failed |
| goto_lift | 0.118 | failed |
| attack_target_hit | 0.863 | failed |
| attack_side | 0.596 | failed |
| attack_flip | 0.258 | failed |
| defend_more_on_named | 0.668 | failed |
| defend_side | 0.645 | failed |
| defend_flip | 0.332 | failed |
