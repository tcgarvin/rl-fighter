# Order drills: nobomb_3000

**Gate: pass.** nobomb_3000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_3000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.93 +/- 0.02 (250/269) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.94 +/- 0.02 (132/141; 12 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.03 (15/130; 23 killed first, not counted)
- Lift from seeing the order: +0.82
- Near: 0.92 +/- 0.03 (70/76; 3 killed first, not counted)
- Far: 0.95 +/- 0.03 (62/65; 9 killed first, not counted)
- Enemies around the route: 0.90 +/- 0.03 (70/78; 7 killed first, not counted)
- Deadline in the order: 0.93 (88/95)
- No deadline (judged by 2x + 10 s): 0.96 (44/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (22/26) |
| medium (2.5 to 4.5) | 0.92 (34/37) |
| loose (over 4.5) | 1.00 (32/32) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 141 | 95 | 46 | 13 |
| In time | 0.94 | 0.93 | 0.96 | 0.92 |
| Near miss (within 60 m) | 0.06 | 0.07 | 0.04 | 0.08 |
| At the enemy instead | 0.00 | 0.00 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 1.00 +/- 0.00 (45/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 65.6 +/- 7.1 (n=128)
- On other enemies per pilot (not judged): 41.8 +/- 4.4 (n=128)
- Chose the named side: 0.97 +/- 0.02 (124/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.02 +/- 0.01 (3/128)
- Swap test, flipped with the order: 0.94 +/- 0.03 (60/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.93 +/- 0.02 (119/128)
- On the named ward's attackers per pilot: 82.2 +/- 6.4 (n=128)
- On the other's per pilot: 4.5 +/- 1.3 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Dock, alone (64 drills)

- Docked: 0.64 +/- 0.06 (41/64)
- Shot down first: 0.11 +/- 0.04 (7/64)
- Out of time: 0.25 +/- 0.05 (16/64)
- Docked, of those not shot down: 0.72 +/- 0.06 (41/57)
- Came within 30 m of the dock point: 0.75 +/- 0.05 (48/64); of those, docked: 0.85 +/- 0.05 (41/48)
- Closest approach: median 10 m (10th to 90th percentile 4 to 41 m)
- Time from the order to the dock: median 9.0 s (10th to 90th percentile 5.9 to 22.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.34 +/- 0.01 (n=41)
- Damage dealt per drill: 1.4 +/- 1.4 (n=64)
- Same drills, order hidden, docked: 0.12 +/- 0.04 (8/64)
- Lift from seeing the order: +0.52

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.72 (23/32) | 0.06 |
| station | 0.60 (9/15) | 0.07 |
| citadel | 0.53 (9/17) | 0.24 |
| fighter | 0.71 (10/14) | 0.29 |
| strafer | 0.79 (15/19) | 0.16 |
| gunship | 0.60 (9/15) | 0.00 |
| bomber | 0.44 (7/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.33 +/- 0.06 (21/64)
- Shot down first: 0.41 +/- 0.06 (26/64)
- Out of time: 0.27 +/- 0.06 (17/64)
- Docked, of those not shot down: 0.55 +/- 0.08 (21/38)
- Came within 30 m of the dock point: 0.45 +/- 0.06 (29/64); of those, docked: 0.72 +/- 0.08 (21/29)
- Closest approach: median 33 m (10th to 90th percentile 3 to 216 m)
- Time from the order to the dock: median 18.5 s (10th to 90th percentile 9.8 to 36.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.03 (n=21)
- Damage dealt per drill: 26.7 +/- 8.1 (n=64)
- Same drills, order hidden, docked: 0.08 +/- 0.03 (5/64)
- Lift from seeing the order: +0.25

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.33 (11/33) | 0.39 |
| station | 0.29 (4/14) | 0.36 |
| citadel | 0.35 (6/17) | 0.47 |
| fighter | 0.14 (2/14) | 0.86 |
| strafer | 0.12 (1/8) | 0.75 |
| gunship | 0.62 (16/26) | 0.00 |
| bomber | 0.12 (2/16) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.936 | met |
| goto_lift | 0.821 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.969 | met |
| attack_flip | 0.938 | met |
| defend_more_on_named | 0.930 | met |
| defend_side | 0.953 | met |
| defend_flip | 0.906 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.641 | unset |
| dock_calm_lift | 0.516 | unset |
| dock_threat_docked | 0.328 | unset |
| dock_threat_docked_of_survivors | 0.553 | unset |
