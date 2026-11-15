# Order drills: fighters_pay1_school_821

**Gate: fail.** fighters_pay1_school_821 failed the drill gate: goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_821.pt`, seed 500000, sim version 8. Overall: 0.48 +/- 0.02 (520/1081) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.48 +/- 0.02 (275/569; 91 killed first, not counted)
- Same seeds, order hidden: 0.23 +/- 0.02 (134/594; 66 killed first, not counted)
- Lift from seeing the order: +0.26
- Near: 0.42 +/- 0.03 (139/330; 25 killed first, not counted)
- Far: 0.57 +/- 0.03 (136/239; 66 killed first, not counted)
- Enemies around the route: 0.55 +/- 0.03 (166/301; 45 killed first, not counted)
- Deadline in the order: 0.52 (213/406)
- No deadline (judged by 2x + 10 s): 0.38 (62/163)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.40 (38/96) |
| medium (2.5 to 4.5) | 0.50 (88/175) |
| loose (over 4.5) | 0.64 (87/135) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 569 | 406 | 163 | 36 |
| In time | 0.48 | 0.52 | 0.38 | 0.36 |
| Near miss (within 60 m) | 0.24 | 0.24 | 0.24 | 0.28 |
| At the enemy instead | 0.26 | 0.22 | 0.35 | 0.36 |
| Neither | 0.02 | 0.01 | 0.03 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.89 +/- 0.01 (458/512)
- Swap test, flipped, groups busy with a freighter: 0.46 +/- 0.04 (91/198)
- Swap test, flipped, groups flying at the pilots: 0.24 +/- 0.06 (14/58)
- Damage on the named target per pilot: 56.1 +/- 2.8 (n=512)
- On other enemies per pilot (not judged): 79.5 +/- 3.6 (n=512)
- Chose the named side: 0.67 +/- 0.02 (345/512)
- Chose the other side: 0.18 +/- 0.02 (94/512)
- Chose neither: 0.14 +/- 0.02 (73/512)
- Swap test, flipped with the order: 0.41 +/- 0.03 (105/256)
- Swap test, one side whatever was named: 0.32 +/- 0.03 (82/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.74 +/- 0.02 (379/512)
- On the named ward's attackers per pilot: 89.7 +/- 4.1 (n=512)
- On the other's per pilot: 32.7 +/- 2.6 (n=512)
- Chose the named side: 0.76 +/- 0.02 (388/512)
- Chose the other side: 0.14 +/- 0.02 (74/512)
- Chose neither: 0.10 +/- 0.01 (50/512)
- Swap test, flipped with the order: 0.55 +/- 0.03 (140/256)
- Swap test, one side whatever was named: 0.28 +/- 0.03 (72/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.483 | failed |
| goto_lift | 0.258 | failed |
| attack_target_hit | 0.895 | failed |
| attack_side | 0.674 | failed |
| attack_flip | 0.410 | failed |
| defend_more_on_named | 0.740 | failed |
| defend_side | 0.758 | failed |
| defend_flip | 0.547 | failed |
