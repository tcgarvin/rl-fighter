# Order drills: kite_pay025_2200

**Gate: fail.** kite_pay025_2200 failed the drill gate: defend_more_on_named.

Pilot `policy:ppo_bc_2200.pt`, seed 500000, sim version 9. Overall: 0.81 +/- 0.02 (220/270) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.81 +/- 0.03 (115/142; 11 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.03 (23/133; 20 killed first, not counted)
- Lift from seeing the order: +0.64
- Near: 0.73 +/- 0.05 (53/73; 6 killed first, not counted)
- Far: 0.90 +/- 0.04 (62/69; 5 killed first, not counted)
- Enemies around the route: 0.72 +/- 0.05 (55/76; 9 killed first, not counted)
- Deadline in the order: 0.82 (80/97)
- No deadline (judged by 2x + 10 s): 0.78 (35/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.73 (19/26) |
| medium (2.5 to 4.5) | 0.82 (33/40) |
| loose (over 4.5) | 0.90 (28/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 142 | 97 | 45 | 11 |
| In time | 0.81 | 0.82 | 0.78 | 0.82 |
| Near miss (within 60 m) | 0.17 | 0.15 | 0.20 | 0.18 |
| At the enemy instead | 0.02 | 0.02 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.97 +/- 0.02 (124/128)
- Swap test, flipped, groups busy with a freighter: 0.93 +/- 0.04 (42/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 70.8 +/- 6.8 (n=128)
- On other enemies per pilot (not judged): 66.3 +/- 5.8 (n=128)
- Chose the named side: 0.91 +/- 0.03 (116/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.06 +/- 0.02 (8/128)
- Swap test, flipped with the order: 0.84 +/- 0.05 (54/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.03 (107/128)
- On the named ward's attackers per pilot: 92.8 +/- 8.0 (n=128)
- On the other's per pilot: 10.8 +/- 2.0 (n=128)
- Chose the named side: 0.90 +/- 0.03 (115/128)
- Chose the other side: 0.05 +/- 0.02 (7/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.80 +/- 0.05 (51/64)
- Swap test, one side whatever was named: 0.11 +/- 0.04 (7/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.810 | met |
| goto_lift | 0.637 | met |
| attack_target_hit | 0.969 | met |
| attack_side | 0.906 | met |
| attack_flip | 0.844 | met |
| defend_more_on_named | 0.836 | failed |
| defend_side | 0.898 | met |
| defend_flip | 0.797 | met |
