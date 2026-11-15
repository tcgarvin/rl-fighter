# Order drills: followers_solo_1072

**Gate: pass.** followers_solo_1072 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_1072.pt`, seed 500000, sim version 8. Overall: 0.84 +/- 0.01 (935/1110) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.78 +/- 0.02 (464/598; 62 killed first, not counted)
- Same seeds, order hidden: 0.20 +/- 0.02 (116/591; 69 killed first, not counted)
- Lift from seeing the order: +0.58
- Near: 0.72 +/- 0.02 (240/335; 20 killed first, not counted)
- Far: 0.85 +/- 0.02 (224/263; 42 killed first, not counted)
- Enemies around the route: 0.78 +/- 0.02 (240/307; 39 killed first, not counted)
- Deadline in the order: 0.80 (350/435)
- No deadline (judged by 2x + 10 s): 0.70 (114/163)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.66 (65/99) |
| medium (2.5 to 4.5) | 0.78 (149/190) |
| loose (over 4.5) | 0.93 (136/146) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 598 | 435 | 163 | 45 |
| In time | 0.78 | 0.80 | 0.70 | 0.53 |
| Near miss (within 60 m) | 0.18 | 0.15 | 0.25 | 0.20 |
| At the enemy instead | 0.05 | 0.04 | 0.06 | 0.24 |
| Neither | 0.00 | 0.00 | 0.00 | 0.02 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.92 +/- 0.01 (473/512)
- Swap test, flipped, groups busy with a freighter: 0.93 +/- 0.02 (185/198)
- Swap test, flipped, groups flying at the pilots: 0.83 +/- 0.05 (48/58)
- Damage on the named target per pilot: 56.0 +/- 2.6 (n=512)
- On other enemies per pilot (not judged): 46.8 +/- 2.9 (n=512)
- Chose the named side: 0.96 +/- 0.01 (489/512)
- Chose the other side: 0.03 +/- 0.01 (13/512)
- Chose neither: 0.02 +/- 0.01 (10/512)
- Swap test, flipped with the order: 0.91 +/- 0.02 (233/256)
- Swap test, one side whatever was named: 0.05 +/- 0.01 (13/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.01 (452/512)
- On the named ward's attackers per pilot: 74.0 +/- 3.2 (n=512)
- On the other's per pilot: 7.3 +/- 1.2 (n=512)
- Chose the named side: 0.96 +/- 0.01 (494/512)
- Chose the other side: 0.02 +/- 0.01 (12/512)
- Chose neither: 0.01 +/- 0.00 (6/512)
- Swap test, flipped with the order: 0.93 +/- 0.02 (238/256)
- Swap test, one side whatever was named: 0.05 +/- 0.01 (12/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.776 | met |
| goto_lift | 0.580 | met |
| attack_target_hit | 0.924 | met |
| attack_side | 0.955 | met |
| attack_flip | 0.910 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.965 | met |
| defend_flip | 0.930 | met |
