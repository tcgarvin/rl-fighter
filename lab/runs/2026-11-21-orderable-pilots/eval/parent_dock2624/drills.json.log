# Order drills: parent_dock2624

**Gate: fail.** parent_dock2624 failed the drill gate: defend_more_on_named.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2624.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.86 +/- 0.01 (482/563) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.84 +/- 0.02 (259/307; 27 killed first, not counted)
- Same seeds, order hidden: 0.17 +/- 0.02 (49/292; 42 killed first, not counted)
- Lift from seeing the order: +0.68
- Near: 0.78 +/- 0.03 (135/172; 8 killed first, not counted)
- Far: 0.92 +/- 0.02 (124/135; 19 killed first, not counted)
- Enemies around the route: 0.85 +/- 0.03 (148/174; 18 killed first, not counted)
- Deadline in the order: 0.86 (184/215)
- No deadline (judged by 2x + 10 s): 0.82 (75/92)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.77 (41/53) |
| medium (2.5 to 4.5) | 0.88 (85/97) |
| loose (over 4.5) | 0.89 (58/65) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 307 | 215 | 92 | 18 |
| In time | 0.84 | 0.86 | 0.82 | 0.61 |
| Near miss (within 60 m) | 0.15 | 0.14 | 0.18 | 0.39 |
| At the enemy instead | 0.00 | 0.00 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.95 +/- 0.01 (244/256)
- Swap test, flipped, groups busy with a freighter: 0.92 +/- 0.03 (88/96)
- Swap test, flipped, groups flying at the pilots: 0.78 +/- 0.07 (25/32)
- Damage on the named target per pilot: 62.5 +/- 4.7 (n=256)
- On other enemies per pilot (not judged): 51.2 +/- 4.0 (n=256)
- Chose the named side: 0.94 +/- 0.01 (241/256)
- Chose the other side: 0.04 +/- 0.01 (10/256)
- Chose neither: 0.02 +/- 0.01 (5/256)
- Swap test, flipped with the order: 0.88 +/- 0.03 (113/128)
- Swap test, one side whatever was named: 0.08 +/- 0.02 (10/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.02 (216/256)
- On the named ward's attackers per pilot: 82.5 +/- 5.0 (n=256)
- On the other's per pilot: 11.2 +/- 1.7 (n=256)
- Chose the named side: 0.93 +/- 0.02 (238/256)
- Chose the other side: 0.03 +/- 0.01 (7/256)
- Chose neither: 0.04 +/- 0.01 (11/256)
- Swap test, flipped with the order: 0.86 +/- 0.03 (110/128)
- Swap test, one side whatever was named: 0.05 +/- 0.02 (7/128)

## Dock, alone (128 drills)

- Docked: 0.57 +/- 0.04 (73/128)
- Shot down first: 0.09 +/- 0.02 (11/128)
- Out of time: 0.34 +/- 0.04 (44/128)
- Docked, of those not shot down: 0.62 +/- 0.04 (73/117)
- Came within 30 m of the dock point: 0.67 +/- 0.04 (86/128); of those, docked: 0.85 +/- 0.04 (73/86)
- Closest approach: median 18 m (10th to 90th percentile 3 to 57 m)
- Time from the order to the dock: median 16.1 s (10th to 90th percentile 8.9 to 28.6 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.08 +/- 0.02 (10/128)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.01 (n=73)
- Damage dealt per drill: 2.9 +/- 1.6 (n=128)
- Same drills, order hidden, docked: 0.05 +/- 0.02 (6/128)
- Lift from seeing the order: +0.52

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.67 (40/60) | 0.03 |
| station | 0.39 (12/31) | 0.16 |
| citadel | 0.57 (21/37) | 0.11 |
| fighter | 0.48 (15/31) | 0.19 |
| strafer | 0.59 (20/34) | 0.03 |
| gunship | 0.66 (21/32) | 0.00 |
| bomber | 0.55 (17/31) | 0.13 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.27 +/- 0.04 (34/128)
- Shot down first: 0.50 +/- 0.04 (64/128)
- Out of time: 0.23 +/- 0.04 (30/128)
- Docked, of those not shot down: 0.53 +/- 0.06 (34/64)
- Came within 30 m of the dock point: 0.41 +/- 0.04 (53/128); of those, docked: 0.64 +/- 0.07 (34/53)
- Closest approach: median 49 m (10th to 90th percentile 3 to 206 m)
- Time from the order to the dock: median 19.7 s (10th to 90th percentile 10.6 to 34.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.10 +/- 0.03 (13/128)
- Hull at the dock (fraction of its maximum): 0.28 +/- 0.02 (n=34)
- Damage dealt per drill: 44.5 +/- 8.3 (n=128)
- Same drills, order hidden, docked: 0.05 +/- 0.02 (6/128)
- Lift from seeing the order: +0.22

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.28 (18/64) | 0.47 |
| station | 0.18 (6/34) | 0.56 |
| citadel | 0.33 (10/30) | 0.50 |
| fighter | 0.04 (1/27) | 0.70 |
| strafer | 0.15 (4/26) | 0.69 |
| gunship | 0.51 (20/39) | 0.15 |
| bomber | 0.25 (9/36) | 0.58 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.844 | met |
| goto_lift | 0.676 | met |
| attack_target_hit | 0.953 | met |
| attack_side | 0.941 | met |
| attack_flip | 0.883 | met |
| defend_more_on_named | 0.844 | failed |
| defend_side | 0.930 | met |
| defend_flip | 0.859 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.570 | unset |
| dock_calm_lift | 0.523 | unset |
| dock_threat_docked | 0.266 | unset |
| dock_threat_docked_of_survivors | 0.531 | unset |
