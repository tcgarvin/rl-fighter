# Order drills: s2_725

**Gate: pass.** s2_725 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_725.pt`, seed 500000, sim version 9. Overall: 0.87 +/- 0.02 (228/263) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.84 +/- 0.03 (114/135; 18 killed first, not counted)
- Same seeds, order hidden: 0.19 +/- 0.03 (26/136; 17 killed first, not counted)
- Lift from seeing the order: +0.65
- Near: 0.81 +/- 0.05 (59/73; 6 killed first, not counted)
- Far: 0.89 +/- 0.04 (55/62; 12 killed first, not counted)
- Enemies around the route: 0.80 +/- 0.05 (61/76; 9 killed first, not counted)
- Deadline in the order: 0.85 (79/93)
- No deadline (judged by 2x + 10 s): 0.83 (35/42)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.79 (22/28) |
| medium (2.5 to 4.5) | 0.78 (28/36) |
| loose (over 4.5) | 1.00 (29/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 135 | 93 | 42 | 10 |
| In time | 0.84 | 0.85 | 0.83 | 0.80 |
| Near miss (within 60 m) | 0.12 | 0.11 | 0.14 | 0.00 |
| At the enemy instead | 0.04 | 0.04 | 0.02 | 0.20 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 1.00 +/- 0.00 (45/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 61.2 +/- 6.2 (n=128)
- On other enemies per pilot (not judged): 48.9 +/- 4.5 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.90 +/- 0.03 (115/128)
- On the named ward's attackers per pilot: 80.8 +/- 7.1 (n=128)
- On the other's per pilot: 4.8 +/- 1.2 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.05 +/- 0.02 (6/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.09 +/- 0.04 (6/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.844 | met |
| goto_lift | 0.653 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.945 | met |
| attack_flip | 0.891 | met |
| defend_more_on_named | 0.898 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |
