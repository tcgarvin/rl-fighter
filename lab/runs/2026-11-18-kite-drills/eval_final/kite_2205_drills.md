# Order drills: kite_2205

**Gate: pass.** kite_2205 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_2205.pt`, seed 500000, sim version 9. Overall: 0.89 +/- 0.02 (237/267) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.83 +/- 0.03 (116/139; 14 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (20/129; 24 killed first, not counted)
- Lift from seeing the order: +0.68
- Near: 0.80 +/- 0.05 (59/74; 5 killed first, not counted)
- Far: 0.88 +/- 0.04 (57/65; 9 killed first, not counted)
- Enemies around the route: 0.83 +/- 0.04 (62/75; 10 killed first, not counted)
- Deadline in the order: 0.91 (86/95)
- No deadline (judged by 2x + 10 s): 0.68 (30/44)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.81 (21/26) |
| medium (2.5 to 4.5) | 0.89 (34/38) |
| loose (over 4.5) | 1.00 (31/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 139 | 95 | 44 | 12 |
| In time | 0.83 | 0.91 | 0.68 | 0.83 |
| Near miss (within 60 m) | 0.13 | 0.07 | 0.25 | 0.08 |
| At the enemy instead | 0.04 | 0.02 | 0.07 | 0.08 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.89 +/- 0.07 (17/19)
- Damage on the named target per pilot: 72.2 +/- 7.4 (n=128)
- On other enemies per pilot (not judged): 50.9 +/- 5.4 (n=128)
- Chose the named side: 0.97 +/- 0.02 (124/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.94 +/- 0.03 (60/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (113/128)
- On the named ward's attackers per pilot: 84.2 +/- 7.0 (n=128)
- On the other's per pilot: 5.8 +/- 1.8 (n=128)
- Chose the named side: 0.98 +/- 0.01 (125/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.95 +/- 0.03 (61/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.835 | met |
| goto_lift | 0.679 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.969 | met |
| attack_flip | 0.938 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.977 | met |
| defend_flip | 0.953 | met |
