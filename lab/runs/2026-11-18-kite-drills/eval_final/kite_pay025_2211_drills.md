# Order drills: kite_pay025_2211

**Gate: pass.** kite_pay025_2211 passed the drill gate: every bar met.

Pilot `policy:ppo_bc_2211.pt`, seed 500000, sim version 9. Overall: 0.84 +/- 0.02 (225/268) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.86 +/- 0.03 (120/140; 13 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.03 (23/137; 16 killed first, not counted)
- Lift from seeing the order: +0.69
- Near: 0.82 +/- 0.05 (59/72; 7 killed first, not counted)
- Far: 0.90 +/- 0.04 (61/68; 6 killed first, not counted)
- Enemies around the route: 0.81 +/- 0.04 (61/75; 10 killed first, not counted)
- Deadline in the order: 0.88 (83/94)
- No deadline (judged by 2x + 10 s): 0.80 (37/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.78 (21/27) |
| medium (2.5 to 4.5) | 0.86 (31/36) |
| loose (over 4.5) | 1.00 (31/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 140 | 94 | 46 | 10 |
| In time | 0.86 | 0.88 | 0.80 | 1.00 |
| Near miss (within 60 m) | 0.13 | 0.11 | 0.17 | 0.00 |
| At the enemy instead | 0.01 | 0.01 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 0.87 +/- 0.05 (39/45)
- Swap test, flipped, groups flying at the pilots: 0.74 +/- 0.10 (14/19)
- Damage on the named target per pilot: 72.5 +/- 7.3 (n=128)
- On other enemies per pilot (not judged): 59.1 +/- 5.1 (n=128)
- Chose the named side: 0.90 +/- 0.03 (115/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.06 +/- 0.02 (8/128)
- Swap test, flipped with the order: 0.83 +/- 0.05 (53/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.87 +/- 0.03 (111/128)
- On the named ward's attackers per pilot: 90.3 +/- 7.7 (n=128)
- On the other's per pilot: 10.6 +/- 2.2 (n=128)
- Chose the named side: 0.91 +/- 0.03 (116/128)
- Chose the other side: 0.05 +/- 0.02 (7/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.81 +/- 0.05 (52/64)
- Swap test, one side whatever was named: 0.11 +/- 0.04 (7/64)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.857 | met |
| goto_lift | 0.689 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.898 | met |
| attack_flip | 0.828 | met |
| defend_more_on_named | 0.867 | met |
| defend_side | 0.906 | met |
| defend_flip | 0.812 | met |
