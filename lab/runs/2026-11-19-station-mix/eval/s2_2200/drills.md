# Order drills: s2_2200

**Gate: fail.** s2_2200 failed the drill gate: attack_target_hit, defend_more_on_named.

Pilot `policy:ppo_bc_2200.pt`, seed 500000, sim version 9. Overall: 0.84 +/- 0.02 (220/261) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.88 +/- 0.03 (117/133; 20 killed first, not counted)
- Same seeds, order hidden: 0.20 +/- 0.04 (25/128; 25 killed first, not counted)
- Lift from seeing the order: +0.68
- Near: 0.85 +/- 0.04 (61/72; 7 killed first, not counted)
- Far: 0.92 +/- 0.04 (56/61; 13 killed first, not counted)
- Enemies around the route: 0.86 +/- 0.04 (63/73; 12 killed first, not counted)
- Deadline in the order: 0.91 (84/92)
- No deadline (judged by 2x + 10 s): 0.80 (33/41)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.81 (21/26) |
| medium (2.5 to 4.5) | 0.97 (33/34) |
| loose (over 4.5) | 0.94 (30/32) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 133 | 92 | 41 | 11 |
| In time | 0.88 | 0.91 | 0.80 | 1.00 |
| Near miss (within 60 m) | 0.10 | 0.08 | 0.15 | 0.00 |
| At the enemy instead | 0.02 | 0.01 | 0.05 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.90 +/- 0.03 (115/128)
- Swap test, flipped, groups busy with a freighter: 0.87 +/- 0.05 (39/45)
- Swap test, flipped, groups flying at the pilots: 0.58 +/- 0.11 (11/19)
- Damage on the named target per pilot: 47.4 +/- 4.4 (n=128)
- On other enemies per pilot (not judged): 43.2 +/- 4.5 (n=128)
- Chose the named side: 0.88 +/- 0.03 (112/128)
- Chose the other side: 0.05 +/- 0.02 (7/128)
- Chose neither: 0.07 +/- 0.02 (9/128)
- Swap test, flipped with the order: 0.78 +/- 0.05 (50/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.03 (108/128)
- On the named ward's attackers per pilot: 65.4 +/- 5.5 (n=128)
- On the other's per pilot: 5.4 +/- 1.8 (n=128)
- Chose the named side: 0.91 +/- 0.02 (117/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.06 +/- 0.02 (8/128)
- Swap test, flipped with the order: 0.83 +/- 0.05 (53/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.880 | met |
| goto_lift | 0.684 | met |
| attack_target_hit | 0.898 | failed |
| attack_side | 0.875 | met |
| attack_flip | 0.781 | met |
| defend_more_on_named | 0.844 | failed |
| defend_side | 0.914 | met |
| defend_flip | 0.828 | met |
