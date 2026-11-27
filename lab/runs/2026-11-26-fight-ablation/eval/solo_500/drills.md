# Order drills: solo_500

**Gate: pass.** solo_500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.88 +/- 0.02 (227/258) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.88 +/- 0.03 (114/130; 23 killed first, not counted)
- Same seeds, order hidden: 0.15 +/- 0.03 (20/130; 23 killed first, not counted)
- Lift from seeing the order: +0.72
- Near: 0.82 +/- 0.04 (61/74; 5 killed first, not counted)
- Far: 0.95 +/- 0.03 (53/56; 18 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.04 (61/73; 12 killed first, not counted)
- Deadline in the order: 0.89 (80/90)
- No deadline (judged by 2x + 10 s): 0.85 (34/40)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.84 (21/25) |
| medium (2.5 to 4.5) | 0.83 (30/36) |
| loose (over 4.5) | 1.00 (29/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 130 | 90 | 40 | 11 |
| In time | 0.88 | 0.89 | 0.85 | 0.91 |
| Near miss (within 60 m) | 0.12 | 0.11 | 0.15 | 0.09 |
| At the enemy instead | 0.00 | 0.00 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 55.1 +/- 5.3 (n=128)
- On other enemies per pilot (not judged): 46.0 +/- 4.4 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.06 +/- 0.02 (8/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (113/128)
- On the named ward's attackers per pilot: 87.5 +/- 7.4 (n=128)
- On the other's per pilot: 6.5 +/- 1.6 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.00 +/- 0.00 (0/128)
- Chose neither: 0.05 +/- 0.02 (7/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (0/64)

## Dock, alone (64 drills)

- Docked: 0.39 +/- 0.06 (25/64)
- Shot down first: 0.09 +/- 0.04 (6/64)
- Out of time: 0.52 +/- 0.06 (33/64)
- Docked, of those not shot down: 0.43 +/- 0.07 (25/58)
- Came within 30 m of the dock point: 0.55 +/- 0.06 (35/64); of those, docked: 0.71 +/- 0.08 (25/35)
- Closest approach: median 26 m (10th to 90th percentile 8 to 93 m)
- Time from the order to the dock: median 13.7 s (10th to 90th percentile 8.7 to 20.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.02 (n=25)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.38

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.50 (16/32) | 0.03 |
| station | 0.27 (4/15) | 0.13 |
| citadel | 0.29 (5/17) | 0.18 |
| fighter | 0.57 (8/14) | 0.29 |
| strafer | 0.79 (15/19) | 0.11 |
| gunship | 0.13 (2/15) | 0.00 |
| bomber | 0.00 (0/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.11 +/- 0.04 (7/64)
- Shot down first: 0.39 +/- 0.06 (25/64)
- Out of time: 0.50 +/- 0.06 (32/64)
- Docked, of those not shot down: 0.18 +/- 0.06 (7/39)
- Came within 30 m of the dock point: 0.45 +/- 0.06 (29/64); of those, docked: 0.24 +/- 0.08 (7/29)
- Closest approach: median 34 m (10th to 90th percentile 8 to 223 m)
- Time from the order to the dock: median 13.1 s (10th to 90th percentile 9.1 to 19.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.06 +/- 0.03 (4/64)
- Hull at the dock (fraction of its maximum): 0.34 +/- 0.04 (n=7)
- Damage dealt per drill: 43.7 +/- 12.0 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.09

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.15 (5/33) | 0.42 |
| station | 0.00 (0/14) | 0.29 |
| citadel | 0.12 (2/17) | 0.41 |
| fighter | 0.07 (1/14) | 0.79 |
| strafer | 0.00 (0/8) | 0.88 |
| gunship | 0.23 (6/26) | 0.00 |
| bomber | 0.00 (0/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.877 | met |
| goto_lift | 0.723 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.930 | met |
| attack_flip | 0.875 | met |
| defend_more_on_named | 0.883 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.391 | unset |
| dock_calm_lift | 0.375 | unset |
| dock_threat_docked | 0.109 | unset |
| dock_threat_docked_of_survivors | 0.179 | unset |
