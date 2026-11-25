# Order drills: h995_2000

**Gate: pass.** h995_2000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.90 +/- 0.02 (237/264) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.88 +/- 0.03 (119/136; 17 killed first, not counted)
- Same seeds, order hidden: 0.11 +/- 0.03 (14/127; 26 killed first, not counted)
- Lift from seeing the order: +0.76
- Near: 0.87 +/- 0.04 (62/71; 8 killed first, not counted)
- Far: 0.88 +/- 0.04 (57/65; 9 killed first, not counted)
- Enemies around the route: 0.80 +/- 0.05 (59/74; 11 killed first, not counted)
- Deadline in the order: 0.86 (81/94)
- No deadline (judged by 2x + 10 s): 0.90 (38/42)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.63 (17/27) |
| medium (2.5 to 4.5) | 0.92 (35/38) |
| loose (over 4.5) | 1.00 (29/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 136 | 94 | 42 | 11 |
| In time | 0.88 | 0.86 | 0.90 | 0.73 |
| Near miss (within 60 m) | 0.10 | 0.11 | 0.10 | 0.18 |
| At the enemy instead | 0.02 | 0.03 | 0.00 | 0.09 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.74 +/- 0.10 (14/19)
- Damage on the named target per pilot: 56.8 +/- 5.5 (n=128)
- On other enemies per pilot (not judged): 32.6 +/- 3.9 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.87 +/- 0.03 (111/128)
- On the named ward's attackers per pilot: 72.9 +/- 6.2 (n=128)
- On the other's per pilot: 3.5 +/- 1.1 (n=128)
- Chose the named side: 0.97 +/- 0.02 (124/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.94 +/- 0.03 (60/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Dock, alone (64 drills)

- Docked: 0.52 +/- 0.06 (33/64)
- Shot down first: 0.11 +/- 0.04 (7/64)
- Out of time: 0.38 +/- 0.06 (24/64)
- Docked, of those not shot down: 0.58 +/- 0.07 (33/57)
- Came within 30 m of the dock point: 0.69 +/- 0.06 (44/64); of those, docked: 0.75 +/- 0.07 (33/44)
- Closest approach: median 10 m (10th to 90th percentile 2 to 53 m)
- Time from the order to the dock: median 14.4 s (10th to 90th percentile 10.3 to 27.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=33)
- Damage dealt per drill: 2.3 +/- 2.3 (n=64)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/64)
- Lift from seeing the order: +0.52

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.50 (16/32) | 0.12 |
| station | 0.40 (6/15) | 0.07 |
| citadel | 0.65 (11/17) | 0.12 |
| fighter | 0.50 (7/14) | 0.29 |
| strafer | 0.79 (15/19) | 0.11 |
| gunship | 0.40 (6/15) | 0.00 |
| bomber | 0.31 (5/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.16 +/- 0.05 (10/64)
- Shot down first: 0.41 +/- 0.06 (26/64)
- Out of time: 0.44 +/- 0.06 (28/64)
- Docked, of those not shot down: 0.26 +/- 0.07 (10/38)
- Came within 30 m of the dock point: 0.45 +/- 0.06 (29/64); of those, docked: 0.34 +/- 0.09 (10/29)
- Closest approach: median 34 m (10th to 90th percentile 5 to 202 m)
- Time from the order to the dock: median 23.0 s (10th to 90th percentile 13.5 to 39.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.04 (n=10)
- Damage dealt per drill: 35.4 +/- 11.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.12

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.15 (5/33) | 0.45 |
| station | 0.07 (1/14) | 0.36 |
| citadel | 0.24 (4/17) | 0.35 |
| fighter | 0.00 (0/14) | 0.93 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.27 (7/26) | 0.00 |
| bomber | 0.06 (1/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.875 | met |
| goto_lift | 0.765 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.938 | met |
| attack_flip | 0.906 | met |
| defend_more_on_named | 0.867 | met |
| defend_side | 0.969 | met |
| defend_flip | 0.938 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.516 | unset |
| dock_calm_lift | 0.516 | unset |
| dock_threat_docked | 0.156 | unset |
| dock_threat_docked_of_survivors | 0.263 | unset |
