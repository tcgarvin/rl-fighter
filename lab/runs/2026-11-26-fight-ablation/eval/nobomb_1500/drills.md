# Order drills: nobomb_1500

**Gate: pass.** nobomb_1500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.88 +/- 0.02 (238/269) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (123/141; 12 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (19/126; 27 killed first, not counted)
- Lift from seeing the order: +0.72
- Near: 0.82 +/- 0.04 (62/76; 3 killed first, not counted)
- Far: 0.94 +/- 0.03 (61/65; 9 killed first, not counted)
- Enemies around the route: 0.78 +/- 0.05 (62/79; 6 killed first, not counted)
- Deadline in the order: 0.91 (86/95)
- No deadline (judged by 2x + 10 s): 0.80 (37/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.77 (20/26) |
| medium (2.5 to 4.5) | 0.92 (34/37) |
| loose (over 4.5) | 1.00 (32/32) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 141 | 95 | 46 | 12 |
| In time | 0.87 | 0.91 | 0.80 | 0.83 |
| Near miss (within 60 m) | 0.11 | 0.07 | 0.17 | 0.00 |
| At the enemy instead | 0.02 | 0.02 | 0.02 | 0.17 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.74 +/- 0.10 (14/19)
- Damage on the named target per pilot: 60.9 +/- 6.1 (n=128)
- On other enemies per pilot (not judged): 45.5 +/- 4.7 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.92 +/- 0.02 (118/128)
- On the named ward's attackers per pilot: 88.4 +/- 7.4 (n=128)
- On the other's per pilot: 6.1 +/- 1.7 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.55 +/- 0.06 (35/64)
- Shot down first: 0.11 +/- 0.04 (7/64)
- Out of time: 0.34 +/- 0.06 (22/64)
- Docked, of those not shot down: 0.61 +/- 0.06 (35/57)
- Came within 30 m of the dock point: 0.75 +/- 0.05 (48/64); of those, docked: 0.73 +/- 0.06 (35/48)
- Closest approach: median 10 m (10th to 90th percentile 3 to 119 m)
- Time from the order to the dock: median 10.2 s (10th to 90th percentile 6.7 to 21.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.06 +/- 0.03 (4/64)
- Hull at the dock (fraction of its maximum): 0.35 +/- 0.02 (n=35)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.09 +/- 0.04 (6/64)
- Lift from seeing the order: +0.45

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.56 (18/32) | 0.09 |
| station | 0.60 (9/15) | 0.07 |
| citadel | 0.47 (8/17) | 0.18 |
| fighter | 0.71 (10/14) | 0.29 |
| strafer | 0.74 (14/19) | 0.16 |
| gunship | 0.60 (9/15) | 0.00 |
| bomber | 0.12 (2/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.20 +/- 0.05 (13/64)
- Shot down first: 0.38 +/- 0.06 (24/64)
- Out of time: 0.42 +/- 0.06 (27/64)
- Docked, of those not shot down: 0.33 +/- 0.07 (13/40)
- Came within 30 m of the dock point: 0.44 +/- 0.06 (28/64); of those, docked: 0.46 +/- 0.09 (13/28)
- Closest approach: median 33 m (10th to 90th percentile 2 to 182 m)
- Time from the order to the dock: median 19.3 s (10th to 90th percentile 9.0 to 30.6 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.12 +/- 0.04 (8/64)
- Hull at the dock (fraction of its maximum): 0.26 +/- 0.03 (n=13)
- Damage dealt per drill: 31.6 +/- 9.7 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.17

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.21 (7/33) | 0.45 |
| station | 0.07 (1/14) | 0.29 |
| citadel | 0.29 (5/17) | 0.29 |
| fighter | 0.14 (2/14) | 0.64 |
| strafer | 0.12 (1/8) | 0.88 |
| gunship | 0.38 (10/26) | 0.00 |
| bomber | 0.00 (0/16) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.872 | met |
| goto_lift | 0.722 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.930 | met |
| attack_flip | 0.906 | met |
| defend_more_on_named | 0.922 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.547 | unset |
| dock_calm_lift | 0.453 | unset |
| dock_threat_docked | 0.203 | unset |
| dock_threat_docked_of_survivors | 0.325 | unset |
