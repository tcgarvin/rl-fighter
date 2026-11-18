# Order drills: control_725

**Gate: pass.** control_725 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_725.pt`, seed 500000, sim version 8. Overall: 0.86 +/- 0.02 (227/263) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.84 +/- 0.03 (114/135; 18 killed first, not counted)
- Same seeds, order hidden: 0.19 +/- 0.03 (26/140; 13 killed first, not counted)
- Lift from seeing the order: +0.66
- Near: 0.81 +/- 0.05 (58/72; 7 killed first, not counted)
- Far: 0.89 +/- 0.04 (56/63; 11 killed first, not counted)
- Enemies around the route: 0.79 +/- 0.05 (57/72; 13 killed first, not counted)
- Deadline in the order: 0.87 (77/89)
- No deadline (judged by 2x + 10 s): 0.80 (37/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.78 (21/27) |
| medium (2.5 to 4.5) | 0.91 (30/33) |
| loose (over 4.5) | 0.90 (26/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 135 | 89 | 46 | 11 |
| In time | 0.84 | 0.87 | 0.80 | 0.73 |
| Near miss (within 60 m) | 0.11 | 0.10 | 0.13 | 0.09 |
| At the enemy instead | 0.04 | 0.03 | 0.04 | 0.18 |
| Neither | 0.01 | 0.00 | 0.02 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.97 +/- 0.02 (124/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 63.7 +/- 6.4 (n=128)
- On other enemies per pilot (not judged): 55.0 +/- 5.3 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.00 +/- 0.00 (0/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (0/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.90 +/- 0.03 (115/128)
- On the named ward's attackers per pilot: 79.3 +/- 6.5 (n=128)
- On the other's per pilot: 6.7 +/- 1.7 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.84 +/- 0.05 (54/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.844 | met |
| goto_lift | 0.659 | met |
| attack_target_hit | 0.969 | met |
| attack_side | 0.961 | met |
| attack_flip | 0.922 | met |
| defend_more_on_named | 0.898 | met |
| defend_side | 0.922 | met |
| defend_flip | 0.844 | met |
