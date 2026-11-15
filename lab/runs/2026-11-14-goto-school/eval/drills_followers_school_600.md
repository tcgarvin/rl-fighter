# Order drills: followers_school_600

**Gate: pass.** followers_school_600 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_600.pt`, seed 500000, sim version 8. Overall: 0.78 +/- 0.01 (856/1096) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.70 +/- 0.02 (408/584; 76 killed first, not counted)
- Same seeds, order hidden: 0.19 +/- 0.02 (110/584; 76 killed first, not counted)
- Lift from seeing the order: +0.51
- Near: 0.63 +/- 0.03 (204/323; 32 killed first, not counted)
- Far: 0.78 +/- 0.03 (204/261; 44 killed first, not counted)
- Enemies around the route: 0.69 +/- 0.03 (205/298; 48 killed first, not counted)
- Deadline in the order: 0.72 (302/417)
- No deadline (judged by 2x + 10 s): 0.63 (106/167)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.60 (58/97) |
| medium (2.5 to 4.5) | 0.68 (122/179) |
| loose (over 4.5) | 0.87 (122/141) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 584 | 417 | 167 | 41 |
| In time | 0.70 | 0.72 | 0.63 | 0.41 |
| Near miss (within 60 m) | 0.19 | 0.17 | 0.23 | 0.22 |
| At the enemy instead | 0.10 | 0.09 | 0.14 | 0.37 |
| Neither | 0.01 | 0.01 | 0.00 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.95 +/- 0.01 (485/512)
- Swap test, flipped, groups busy with a freighter: 0.89 +/- 0.02 (176/198)
- Swap test, flipped, groups flying at the pilots: 0.74 +/- 0.06 (43/58)
- Damage on the named target per pilot: 61.4 +/- 2.9 (n=512)
- On other enemies per pilot (not judged): 51.0 +/- 3.0 (n=512)
- Chose the named side: 0.93 +/- 0.01 (474/512)
- Chose the other side: 0.04 +/- 0.01 (21/512)
- Chose neither: 0.03 +/- 0.01 (17/512)
- Swap test, flipped with the order: 0.86 +/- 0.02 (219/256)
- Swap test, one side whatever was named: 0.08 +/- 0.02 (21/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.01 (449/512)
- On the named ward's attackers per pilot: 82.6 +/- 3.6 (n=512)
- On the other's per pilot: 8.3 +/- 1.2 (n=512)
- Chose the named side: 0.95 +/- 0.01 (485/512)
- Chose the other side: 0.03 +/- 0.01 (14/512)
- Chose neither: 0.03 +/- 0.01 (13/512)
- Swap test, flipped with the order: 0.89 +/- 0.02 (229/256)
- Swap test, one side whatever was named: 0.05 +/- 0.01 (14/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.699 | met |
| goto_lift | 0.510 | met |
| attack_target_hit | 0.947 | met |
| attack_side | 0.926 | met |
| attack_flip | 0.855 | met |
| defend_more_on_named | 0.877 | met |
| defend_side | 0.947 | met |
| defend_flip | 0.895 | met |
