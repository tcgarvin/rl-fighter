# Order drills: parent_dock2676

**Gate: pass.** parent_dock2676 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2676.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.87 +/- 0.01 (487/561) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.85 +/- 0.02 (259/305; 29 killed first, not counted)
- Same seeds, order hidden: 0.20 +/- 0.02 (58/290; 44 killed first, not counted)
- Lift from seeing the order: +0.65
- Near: 0.77 +/- 0.03 (133/173; 7 killed first, not counted)
- Far: 0.95 +/- 0.02 (126/132; 22 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.03 (146/174; 18 killed first, not counted)
- Deadline in the order: 0.89 (188/212)
- No deadline (judged by 2x + 10 s): 0.76 (71/93)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.75 (39/52) |
| medium (2.5 to 4.5) | 0.89 (83/93) |
| loose (over 4.5) | 0.99 (66/67) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 305 | 212 | 93 | 22 |
| In time | 0.85 | 0.89 | 0.76 | 0.59 |
| Near miss (within 60 m) | 0.12 | 0.09 | 0.19 | 0.23 |
| At the enemy instead | 0.02 | 0.01 | 0.04 | 0.18 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.96 +/- 0.01 (246/256)
- Swap test, flipped, groups busy with a freighter: 0.95 +/- 0.02 (91/96)
- Swap test, flipped, groups flying at the pilots: 0.69 +/- 0.08 (22/32)
- Damage on the named target per pilot: 62.8 +/- 4.6 (n=256)
- On other enemies per pilot (not judged): 46.0 +/- 3.7 (n=256)
- Chose the named side: 0.94 +/- 0.02 (240/256)
- Chose the other side: 0.03 +/- 0.01 (7/256)
- Chose neither: 0.04 +/- 0.01 (9/256)
- Swap test, flipped with the order: 0.88 +/- 0.03 (113/128)
- Swap test, one side whatever was named: 0.05 +/- 0.02 (7/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.02 (226/256)
- On the named ward's attackers per pilot: 83.8 +/- 5.0 (n=256)
- On the other's per pilot: 9.6 +/- 1.9 (n=256)
- Chose the named side: 0.95 +/- 0.01 (243/256)
- Chose the other side: 0.02 +/- 0.01 (6/256)
- Chose neither: 0.03 +/- 0.01 (7/256)
- Swap test, flipped with the order: 0.90 +/- 0.03 (115/128)
- Swap test, one side whatever was named: 0.05 +/- 0.02 (6/128)

## Dock, alone (128 drills)

- Docked: 0.38 +/- 0.04 (49/128)
- Shot down first: 0.15 +/- 0.03 (19/128)
- Out of time: 0.47 +/- 0.04 (60/128)
- Docked, of those not shot down: 0.45 +/- 0.05 (49/109)
- Came within 30 m of the dock point: 0.48 +/- 0.04 (61/128); of those, docked: 0.80 +/- 0.05 (49/61)
- Closest approach: median 31 m (10th to 90th percentile 6 to 109 m)
- Time from the order to the dock: median 12.2 s (10th to 90th percentile 8.5 to 23.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.09 +/- 0.03 (12/128)
- Hull at the dock (fraction of its maximum): 0.28 +/- 0.02 (n=49)
- Damage dealt per drill: 2.3 +/- 1.6 (n=128)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (4/128)
- Lift from seeing the order: +0.35

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.43 (26/60) | 0.10 |
| station | 0.48 (15/31) | 0.13 |
| citadel | 0.22 (8/37) | 0.24 |
| fighter | 0.65 (20/31) | 0.29 |
| strafer | 0.71 (24/34) | 0.26 |
| gunship | 0.12 (4/32) | 0.00 |
| bomber | 0.03 (1/31) | 0.03 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.14 +/- 0.03 (18/128)
- Shot down first: 0.48 +/- 0.04 (61/128)
- Out of time: 0.38 +/- 0.04 (49/128)
- Docked, of those not shot down: 0.27 +/- 0.05 (18/67)
- Came within 30 m of the dock point: 0.38 +/- 0.04 (48/128); of those, docked: 0.38 +/- 0.07 (18/48)
- Closest approach: median 43 m (10th to 90th percentile 5 to 208 m)
- Time from the order to the dock: median 22.2 s (10th to 90th percentile 9.2 to 30.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.10 +/- 0.03 (13/128)
- Hull at the dock (fraction of its maximum): 0.23 +/- 0.02 (n=18)
- Damage dealt per drill: 51.6 +/- 8.3 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (2/128)
- Lift from seeing the order: +0.12

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.17 (11/64) | 0.47 |
| station | 0.18 (6/34) | 0.38 |
| citadel | 0.03 (1/30) | 0.60 |
| fighter | 0.11 (3/27) | 0.78 |
| strafer | 0.31 (8/26) | 0.65 |
| gunship | 0.18 (7/39) | 0.13 |
| bomber | 0.00 (0/36) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.849 | met |
| goto_lift | 0.649 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.938 | met |
| attack_flip | 0.883 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.949 | met |
| defend_flip | 0.898 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.383 | unset |
| dock_calm_lift | 0.352 | unset |
| dock_threat_docked | 0.141 | unset |
| dock_threat_docked_of_survivors | 0.269 | unset |
