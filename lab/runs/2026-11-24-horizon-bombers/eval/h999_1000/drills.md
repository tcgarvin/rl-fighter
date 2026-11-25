# Order drills: h999_1000

**Gate: pass.** h999_1000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.89 +/- 0.02 (240/270) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.89 +/- 0.03 (126/142; 11 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (19/131; 22 killed first, not counted)
- Lift from seeing the order: +0.74
- Near: 0.83 +/- 0.04 (62/75; 4 killed first, not counted)
- Far: 0.96 +/- 0.03 (64/67; 7 killed first, not counted)
- Enemies around the route: 0.85 +/- 0.04 (67/79; 6 killed first, not counted)
- Deadline in the order: 0.91 (86/94)
- No deadline (judged by 2x + 10 s): 0.83 (40/48)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.93 (25/27) |
| medium (2.5 to 4.5) | 0.86 (32/37) |
| loose (over 4.5) | 0.97 (29/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 142 | 94 | 48 | 12 |
| In time | 0.89 | 0.91 | 0.83 | 0.83 |
| Near miss (within 60 m) | 0.11 | 0.07 | 0.17 | 0.17 |
| At the enemy instead | 0.01 | 0.01 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 52.7 +/- 4.9 (n=128)
- On other enemies per pilot (not judged): 32.0 +/- 3.7 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.01 +/- 0.01 (1/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.93 +/- 0.02 (119/128)
- On the named ward's attackers per pilot: 79.0 +/- 6.3 (n=128)
- On the other's per pilot: 5.0 +/- 1.3 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.86 +/- 0.04 (55/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.47 +/- 0.06 (30/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.47 +/- 0.06 (30/64)
- Docked, of those not shot down: 0.50 +/- 0.06 (30/60)
- Came within 30 m of the dock point: 0.72 +/- 0.06 (46/64); of those, docked: 0.65 +/- 0.07 (30/46)
- Closest approach: median 18 m (10th to 90th percentile 4 to 74 m)
- Time from the order to the dock: median 14.5 s (10th to 90th percentile 8.3 to 23.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=30)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.44

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.59 (19/32) | 0.00 |
| station | 0.40 (6/15) | 0.07 |
| citadel | 0.29 (5/17) | 0.18 |
| fighter | 0.50 (7/14) | 0.14 |
| strafer | 0.84 (16/19) | 0.11 |
| gunship | 0.27 (4/15) | 0.00 |
| bomber | 0.19 (3/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.20 +/- 0.05 (13/64)
- Shot down first: 0.41 +/- 0.06 (26/64)
- Out of time: 0.39 +/- 0.06 (25/64)
- Docked, of those not shot down: 0.34 +/- 0.08 (13/38)
- Came within 30 m of the dock point: 0.38 +/- 0.06 (24/64); of those, docked: 0.54 +/- 0.10 (13/24)
- Closest approach: median 35 m (10th to 90th percentile 10 to 181 m)
- Time from the order to the dock: median 21.0 s (10th to 90th percentile 9.6 to 32.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=64); drills with one: 0.02 +/- 0.02 (1/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.03 (n=13)
- Damage dealt per drill: 22.3 +/- 7.5 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.19

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.21 (7/33) | 0.45 |
| station | 0.29 (4/14) | 0.36 |
| citadel | 0.12 (2/17) | 0.35 |
| fighter | 0.07 (1/14) | 0.79 |
| strafer | 0.00 (0/8) | 0.88 |
| gunship | 0.42 (11/26) | 0.04 |
| bomber | 0.06 (1/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.887 | met |
| goto_lift | 0.742 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.961 | met |
| attack_flip | 0.922 | met |
| defend_more_on_named | 0.930 | met |
| defend_side | 0.930 | met |
| defend_flip | 0.859 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.469 | unset |
| dock_calm_lift | 0.438 | unset |
| dock_threat_docked | 0.203 | unset |
| dock_threat_docked_of_survivors | 0.342 | unset |
