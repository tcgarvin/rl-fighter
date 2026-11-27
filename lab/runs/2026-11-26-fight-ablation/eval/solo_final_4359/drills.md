# Order drills: solo_final_4359

**Gate: pass.** solo_final_4359 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_4359.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.85 +/- 0.02 (477/563) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.83 +/- 0.02 (256/307; 27 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.02 (44/289; 45 killed first, not counted)
- Lift from seeing the order: +0.68
- Near: 0.78 +/- 0.03 (135/174; 6 killed first, not counted)
- Far: 0.91 +/- 0.02 (121/133; 21 killed first, not counted)
- Enemies around the route: 0.79 +/- 0.03 (135/170; 22 killed first, not counted)
- Deadline in the order: 0.87 (186/214)
- No deadline (judged by 2x + 10 s): 0.75 (70/93)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.76 (41/54) |
| medium (2.5 to 4.5) | 0.86 (83/96) |
| loose (over 4.5) | 0.97 (62/64) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 307 | 214 | 93 | 25 |
| In time | 0.83 | 0.87 | 0.75 | 0.72 |
| Near miss (within 60 m) | 0.13 | 0.09 | 0.22 | 0.16 |
| At the enemy instead | 0.04 | 0.04 | 0.03 | 0.12 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.94 +/- 0.02 (240/256)
- Swap test, flipped, groups busy with a freighter: 0.92 +/- 0.03 (88/96)
- Swap test, flipped, groups flying at the pilots: 0.72 +/- 0.08 (23/32)
- Damage on the named target per pilot: 53.6 +/- 4.1 (n=256)
- On other enemies per pilot (not judged): 29.5 +/- 2.6 (n=256)
- Chose the named side: 0.93 +/- 0.02 (239/256)
- Chose the other side: 0.04 +/- 0.01 (9/256)
- Chose neither: 0.03 +/- 0.01 (8/256)
- Swap test, flipped with the order: 0.87 +/- 0.03 (111/128)
- Swap test, one side whatever was named: 0.07 +/- 0.02 (9/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.02 (232/256)
- On the named ward's attackers per pilot: 76.1 +/- 4.8 (n=256)
- On the other's per pilot: 5.2 +/- 1.1 (n=256)
- Chose the named side: 0.93 +/- 0.02 (238/256)
- Chose the other side: 0.03 +/- 0.01 (8/256)
- Chose neither: 0.04 +/- 0.01 (10/256)
- Swap test, flipped with the order: 0.86 +/- 0.03 (110/128)
- Swap test, one side whatever was named: 0.06 +/- 0.02 (8/128)

## Dock, alone (128 drills)

- Docked: 0.48 +/- 0.04 (62/128)
- Shot down first: 0.15 +/- 0.03 (19/128)
- Out of time: 0.37 +/- 0.04 (47/128)
- Docked, of those not shot down: 0.57 +/- 0.05 (62/109)
- Came within 30 m of the dock point: 0.76 +/- 0.04 (97/128); of those, docked: 0.64 +/- 0.05 (62/97)
- Closest approach: median 18 m (10th to 90th percentile 2 to 45 m)
- Time from the order to the dock: median 12.1 s (10th to 90th percentile 7.2 to 23.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.07 +/- 0.02 (9/128)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.01 (n=62)
- Damage dealt per drill: 5.2 +/- 2.8 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (3/128)
- Lift from seeing the order: +0.46

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.57 (34/60) | 0.12 |
| station | 0.35 (11/31) | 0.19 |
| citadel | 0.46 (17/37) | 0.16 |
| fighter | 0.32 (10/31) | 0.23 |
| strafer | 0.56 (19/34) | 0.26 |
| gunship | 0.53 (17/32) | 0.03 |
| bomber | 0.52 (16/31) | 0.06 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.24 +/- 0.04 (31/128)
- Shot down first: 0.43 +/- 0.04 (55/128)
- Out of time: 0.33 +/- 0.04 (42/128)
- Docked, of those not shot down: 0.42 +/- 0.06 (31/73)
- Came within 30 m of the dock point: 0.42 +/- 0.04 (54/128); of those, docked: 0.57 +/- 0.07 (31/54)
- Closest approach: median 35 m (10th to 90th percentile 2 to 227 m)
- Time from the order to the dock: median 16.5 s (10th to 90th percentile 10.9 to 30.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.09 +/- 0.02 (11/128)
- Hull at the dock (fraction of its maximum): 0.24 +/- 0.02 (n=31)
- Damage dealt per drill: 49.8 +/- 7.5 (n=128)
- Same drills, order hidden, docked: 0.01 +/- 0.01 (1/128)
- Lift from seeing the order: +0.23

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.19 (12/64) | 0.44 |
| station | 0.32 (11/34) | 0.38 |
| citadel | 0.27 (8/30) | 0.47 |
| fighter | 0.07 (2/27) | 0.56 |
| strafer | 0.31 (8/26) | 0.65 |
| gunship | 0.38 (15/39) | 0.13 |
| bomber | 0.17 (6/36) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.834 | met |
| goto_lift | 0.682 | met |
| attack_target_hit | 0.938 | met |
| attack_side | 0.934 | met |
| attack_flip | 0.867 | met |
| defend_more_on_named | 0.906 | met |
| defend_side | 0.930 | met |
| defend_flip | 0.859 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.484 | unset |
| dock_calm_lift | 0.461 | unset |
| dock_threat_docked | 0.242 | unset |
| dock_threat_docked_of_survivors | 0.425 | unset |
