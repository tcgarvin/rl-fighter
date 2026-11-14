# Order drills: fighters_1832

**Gate: fail.** fighters_1832 failed the drill gate: goto_arrival, goto_lift, attack_flip, defend_more_on_named, defend_side, defend_flip.

Pilot `policy:ppo_bc_1832.pt`, seed 500000, sim version 8. Overall: 0.52 +/- 0.02 (540/1042) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.38 +/- 0.02 (202/530; 130 killed first, not counted)
- Same seeds, order hidden: 0.18 +/- 0.02 (106/576; 84 killed first, not counted)
- Lift from seeing the order: +0.20
- Near: 0.37 +/- 0.03 (114/312; 43 killed first, not counted)
- Far: 0.40 +/- 0.03 (88/218; 87 killed first, not counted)
- Enemies around the route: 0.41 +/- 0.03 (114/281; 65 killed first, not counted)
- Deadline in the order: 0.42 (159/379)
- No deadline (judged by 2x + 10 s): 0.28 (43/151)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.28 (26/92) |
| medium (2.5 to 4.5) | 0.38 (61/162) |
| loose (over 4.5) | 0.58 (72/125) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 530 | 379 | 151 | 40 |
| In time | 0.38 | 0.42 | 0.28 | 0.33 |
| Near miss (within 60 m) | 0.25 | 0.23 | 0.31 | 0.20 |
| At the enemy instead | 0.35 | 0.34 | 0.38 | 0.47 |
| Neither | 0.01 | 0.01 | 0.02 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.91 +/- 0.01 (464/512)
- Swap test, flipped, groups busy with a freighter: 0.72 +/- 0.03 (143/198)
- Swap test, flipped, groups flying at the pilots: 0.41 +/- 0.06 (24/58)
- Damage on the named target per pilot: 54.2 +/- 2.6 (n=512)
- On other enemies per pilot (not judged): 61.2 +/- 3.2 (n=512)
- Chose the named side: 0.81 +/- 0.02 (417/512)
- Chose the other side: 0.12 +/- 0.01 (61/512)
- Chose neither: 0.07 +/- 0.01 (34/512)
- Swap test, flipped with the order: 0.65 +/- 0.03 (167/256)
- Swap test, one side whatever was named: 0.22 +/- 0.03 (57/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.83 +/- 0.02 (425/512)
- On the named ward's attackers per pilot: 80.9 +/- 3.4 (n=512)
- On the other's per pilot: 19.9 +/- 2.0 (n=512)
- Chose the named side: 0.82 +/- 0.02 (418/512)
- Chose the other side: 0.10 +/- 0.01 (51/512)
- Chose neither: 0.08 +/- 0.01 (43/512)
- Swap test, flipped with the order: 0.67 +/- 0.03 (171/256)
- Swap test, one side whatever was named: 0.18 +/- 0.02 (45/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.381 | failed |
| goto_lift | 0.197 | failed |
| attack_target_hit | 0.906 | met |
| attack_side | 0.814 | met |
| attack_flip | 0.652 | failed |
| defend_more_on_named | 0.830 | failed |
| defend_side | 0.816 | failed |
| defend_flip | 0.668 | failed |
