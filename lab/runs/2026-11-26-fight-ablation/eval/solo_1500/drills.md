# Order drills: solo_1500

**Gate: pass.** solo_1500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.89 +/- 0.02 (233/263) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (118/135; 18 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.03 (16/124; 29 killed first, not counted)
- Lift from seeing the order: +0.75
- Near: 0.81 +/- 0.05 (57/70; 9 killed first, not counted)
- Far: 0.94 +/- 0.03 (61/65; 9 killed first, not counted)
- Enemies around the route: 0.85 +/- 0.04 (61/72; 13 killed first, not counted)
- Deadline in the order: 0.88 (78/89)
- No deadline (judged by 2x + 10 s): 0.87 (40/46)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.84 (21/25) |
| medium (2.5 to 4.5) | 0.85 (29/34) |
| loose (over 4.5) | 0.93 (28/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 135 | 89 | 46 | 13 |
| In time | 0.87 | 0.88 | 0.87 | 0.69 |
| Near miss (within 60 m) | 0.10 | 0.09 | 0.13 | 0.23 |
| At the enemy instead | 0.02 | 0.03 | 0.00 | 0.08 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.93 +/- 0.02 (119/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.68 +/- 0.11 (13/19)
- Damage on the named target per pilot: 54.3 +/- 6.0 (n=128)
- On other enemies per pilot (not judged): 38.0 +/- 3.8 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.90 +/- 0.03 (115/128)
- On the named ward's attackers per pilot: 80.6 +/- 6.6 (n=128)
- On the other's per pilot: 4.9 +/- 1.4 (n=128)
- Chose the named side: 0.95 +/- 0.02 (122/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.91 +/- 0.04 (58/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Dock, alone (64 drills)

- Docked: 0.39 +/- 0.06 (25/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.55 +/- 0.06 (35/64)
- Docked, of those not shot down: 0.42 +/- 0.06 (25/60)
- Came within 30 m of the dock point: 0.52 +/- 0.06 (33/64); of those, docked: 0.76 +/- 0.07 (25/33)
- Closest approach: median 28 m (10th to 90th percentile 3 to 160 m)
- Time from the order to the dock: median 14.6 s (10th to 90th percentile 9.3 to 23.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.35 +/- 0.02 (n=25)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.38

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.31 (10/32) | 0.06 |
| station | 0.27 (4/15) | 0.13 |
| citadel | 0.65 (11/17) | 0.00 |
| fighter | 0.57 (8/14) | 0.00 |
| strafer | 0.53 (10/19) | 0.21 |
| gunship | 0.47 (7/15) | 0.00 |
| bomber | 0.00 (0/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.17 +/- 0.05 (11/64)
- Shot down first: 0.38 +/- 0.06 (24/64)
- Out of time: 0.45 +/- 0.06 (29/64)
- Docked, of those not shot down: 0.28 +/- 0.07 (11/40)
- Came within 30 m of the dock point: 0.38 +/- 0.06 (24/64); of those, docked: 0.46 +/- 0.10 (11/24)
- Closest approach: median 40 m (10th to 90th percentile 2 to 197 m)
- Time from the order to the dock: median 18.6 s (10th to 90th percentile 13.2 to 30.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.04 (n=11)
- Damage dealt per drill: 41.7 +/- 9.7 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.14

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.12 (4/33) | 0.33 |
| station | 0.14 (2/14) | 0.43 |
| citadel | 0.29 (5/17) | 0.41 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.12 (1/8) | 0.62 |
| gunship | 0.38 (10/26) | 0.08 |
| bomber | 0.00 (0/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.874 | met |
| goto_lift | 0.745 | met |
| attack_target_hit | 0.930 | met |
| attack_side | 0.945 | met |
| attack_flip | 0.891 | met |
| defend_more_on_named | 0.898 | met |
| defend_side | 0.953 | met |
| defend_flip | 0.906 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.391 | unset |
| dock_calm_lift | 0.375 | unset |
| dock_threat_docked | 0.172 | unset |
| dock_threat_docked_of_survivors | 0.275 | unset |
