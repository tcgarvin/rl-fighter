# Order drills: h999_final_5334

**Gate: pass.** h999_final_5334 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_5334.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.89 +/- 0.01 (499/563) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.88 +/- 0.02 (271/307; 27 killed first, not counted)
- Same seeds, order hidden: 0.18 +/- 0.02 (51/291; 43 killed first, not counted)
- Lift from seeing the order: +0.71
- Near: 0.82 +/- 0.03 (140/171; 9 killed first, not counted)
- Far: 0.96 +/- 0.02 (131/136; 18 killed first, not counted)
- Enemies around the route: 0.85 +/- 0.03 (150/177; 15 killed first, not counted)
- Deadline in the order: 0.90 (195/216)
- No deadline (judged by 2x + 10 s): 0.84 (76/91)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (45/53) |
| medium (2.5 to 4.5) | 0.90 (87/97) |
| loose (over 4.5) | 0.95 (63/66) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 307 | 216 | 91 | 23 |
| In time | 0.88 | 0.90 | 0.84 | 0.87 |
| Near miss (within 60 m) | 0.11 | 0.09 | 0.16 | 0.09 |
| At the enemy instead | 0.01 | 0.01 | 0.00 | 0.04 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.95 +/- 0.01 (244/256)
- Swap test, flipped, groups busy with a freighter: 0.92 +/- 0.03 (88/96)
- Swap test, flipped, groups flying at the pilots: 0.81 +/- 0.07 (26/32)
- Damage on the named target per pilot: 46.3 +/- 2.9 (n=256)
- On other enemies per pilot (not judged): 30.4 +/- 2.7 (n=256)
- Chose the named side: 0.94 +/- 0.01 (241/256)
- Chose the other side: 0.03 +/- 0.01 (8/256)
- Chose neither: 0.03 +/- 0.01 (7/256)
- Swap test, flipped with the order: 0.89 +/- 0.03 (114/128)
- Swap test, one side whatever was named: 0.05 +/- 0.02 (7/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.02 (232/256)
- On the named ward's attackers per pilot: 55.5 +/- 3.0 (n=256)
- On the other's per pilot: 3.5 +/- 1.0 (n=256)
- Chose the named side: 0.95 +/- 0.01 (242/256)
- Chose the other side: 0.02 +/- 0.01 (4/256)
- Chose neither: 0.04 +/- 0.01 (10/256)
- Swap test, flipped with the order: 0.89 +/- 0.03 (114/128)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (4/128)

## Dock, alone (128 drills)

- Docked: 0.67 +/- 0.04 (86/128)
- Shot down first: 0.05 +/- 0.02 (7/128)
- Out of time: 0.27 +/- 0.04 (35/128)
- Docked, of those not shot down: 0.71 +/- 0.04 (86/121)
- Came within 30 m of the dock point: 0.74 +/- 0.04 (95/128); of those, docked: 0.91 +/- 0.03 (86/95)
- Closest approach: median 10 m (10th to 90th percentile 5 to 43 m)
- Time from the order to the dock: median 11.6 s (10th to 90th percentile 7.5 to 23.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.04 +/- 0.02 (5/128)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.01 (n=86)
- Damage dealt per drill: 3.4 +/- 2.4 (n=128)
- Same drills, order hidden, docked: 0.07 +/- 0.02 (9/128)
- Lift from seeing the order: +0.60

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.75 (45/60) | 0.03 |
| station | 0.74 (23/31) | 0.06 |
| citadel | 0.49 (18/37) | 0.08 |
| fighter | 0.87 (27/31) | 0.06 |
| strafer | 0.85 (29/34) | 0.12 |
| gunship | 0.53 (17/32) | 0.03 |
| bomber | 0.42 (13/31) | 0.00 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.23 +/- 0.04 (30/128)
- Shot down first: 0.41 +/- 0.04 (52/128)
- Out of time: 0.36 +/- 0.04 (46/128)
- Docked, of those not shot down: 0.39 +/- 0.06 (30/76)
- Came within 30 m of the dock point: 0.48 +/- 0.04 (62/128); of those, docked: 0.48 +/- 0.06 (30/62)
- Closest approach: median 31 m (10th to 90th percentile 6 to 115 m)
- Time from the order to the dock: median 22.2 s (10th to 90th percentile 10.1 to 30.6 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.10 +/- 0.03 (13/128)
- Hull at the dock (fraction of its maximum): 0.26 +/- 0.02 (n=30)
- Damage dealt per drill: 31.4 +/- 6.9 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (2/128)
- Lift from seeing the order: +0.22

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.20 (13/64) | 0.42 |
| station | 0.26 (9/34) | 0.35 |
| citadel | 0.27 (8/30) | 0.43 |
| fighter | 0.00 (0/27) | 0.81 |
| strafer | 0.27 (7/26) | 0.65 |
| gunship | 0.38 (15/39) | 0.10 |
| bomber | 0.22 (8/36) | 0.25 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.883 | met |
| goto_lift | 0.707 | met |
| attack_target_hit | 0.953 | met |
| attack_side | 0.941 | met |
| attack_flip | 0.891 | met |
| defend_more_on_named | 0.906 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.672 | unset |
| dock_calm_lift | 0.602 | unset |
| dock_threat_docked | 0.234 | unset |
| dock_threat_docked_of_survivors | 0.395 | unset |
