# Order drills: parent_kite2205

**Gate: pass.** parent_kite2205 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2205.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.92 +/- 0.01 (522/567) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.89 +/- 0.02 (278/311; 23 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.02 (48/304; 30 killed first, not counted)
- Lift from seeing the order: +0.74
- Near: 0.84 +/- 0.03 (145/172; 8 killed first, not counted)
- Far: 0.96 +/- 0.02 (133/139; 15 killed first, not counted)
- Enemies around the route: 0.87 +/- 0.03 (152/175; 17 killed first, not counted)
- Deadline in the order: 0.91 (197/216)
- No deadline (judged by 2x + 10 s): 0.85 (81/95)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.81 (43/53) |
| medium (2.5 to 4.5) | 0.94 (90/96) |
| loose (over 4.5) | 0.96 (64/67) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 311 | 216 | 95 | 22 |
| In time | 0.89 | 0.91 | 0.85 | 0.77 |
| Near miss (within 60 m) | 0.10 | 0.09 | 0.14 | 0.18 |
| At the enemy instead | 0.00 | 0.00 | 0.01 | 0.05 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.95 +/- 0.01 (243/256)
- Swap test, flipped, groups busy with a freighter: 0.99 +/- 0.01 (95/96)
- Swap test, flipped, groups flying at the pilots: 0.88 +/- 0.06 (28/32)
- Damage on the named target per pilot: 65.6 +/- 4.9 (n=256)
- On other enemies per pilot (not judged): 49.2 +/- 4.0 (n=256)
- Chose the named side: 0.98 +/- 0.01 (251/256)
- Chose the other side: 0.01 +/- 0.01 (3/256)
- Chose neither: 0.01 +/- 0.01 (2/256)
- Swap test, flipped with the order: 0.96 +/- 0.02 (123/128)
- Swap test, one side whatever was named: 0.02 +/- 0.01 (3/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.02 (232/256)
- On the named ward's attackers per pilot: 84.9 +/- 5.1 (n=256)
- On the other's per pilot: 4.8 +/- 1.0 (n=256)
- Chose the named side: 0.97 +/- 0.01 (249/256)
- Chose the other side: 0.01 +/- 0.01 (3/256)
- Chose neither: 0.02 +/- 0.01 (4/256)
- Swap test, flipped with the order: 0.95 +/- 0.02 (121/128)
- Swap test, one side whatever was named: 0.02 +/- 0.01 (3/128)

## Dock, alone (128 drills)

- Docked: 0.04 +/- 0.02 (5/128)
- Shot down first: 0.21 +/- 0.04 (27/128)
- Out of time: 0.75 +/- 0.04 (96/128)
- Docked, of those not shot down: 0.05 +/- 0.02 (5/101)
- Came within 30 m of the dock point: 0.29 +/- 0.04 (37/128); of those, docked: 0.14 +/- 0.06 (5/37)
- Closest approach: median 49 m (10th to 90th percentile 9 to 175 m)
- Time from the order to the dock: median 22.1 s (10th to 90th percentile 15.9 to 30.6 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.09 +/- 0.02 (11/128)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.07 (n=5)
- Damage dealt per drill: 2.0 +/- 1.2 (n=128)
- Same drills, order hidden, docked: 0.01 +/- 0.01 (1/128)
- Lift from seeing the order: +0.03

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.03 (2/60) | 0.22 |
| station | 0.06 (2/31) | 0.13 |
| citadel | 0.03 (1/37) | 0.27 |
| fighter | 0.03 (1/31) | 0.61 |
| strafer | 0.03 (1/34) | 0.24 |
| gunship | 0.09 (3/32) | 0.00 |
| bomber | 0.00 (0/31) | 0.00 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.02 +/- 0.01 (3/128)
- Shot down first: 0.51 +/- 0.04 (65/128)
- Out of time: 0.47 +/- 0.04 (60/128)
- Docked, of those not shot down: 0.05 +/- 0.03 (3/63)
- Came within 30 m of the dock point: 0.19 +/- 0.03 (24/128); of those, docked: 0.12 +/- 0.07 (3/24)
- Closest approach: median 76 m (10th to 90th percentile 20 to 230 m)
- Time from the order to the dock: median 13.3 s (10th to 90th percentile 8.5 to 15.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.02 +/- 0.01 (3/128)
- Hull at the dock (fraction of its maximum): 0.24 +/- 0.03 (n=3)
- Damage dealt per drill: 52.1 +/- 8.0 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.02

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.02 (1/64) | 0.47 |
| station | 0.00 (0/34) | 0.44 |
| citadel | 0.07 (2/30) | 0.67 |
| fighter | 0.00 (0/27) | 0.70 |
| strafer | 0.00 (0/26) | 0.73 |
| gunship | 0.05 (2/39) | 0.23 |
| bomber | 0.03 (1/36) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.894 | met |
| goto_lift | 0.736 | met |
| attack_target_hit | 0.949 | met |
| attack_side | 0.980 | met |
| attack_flip | 0.961 | met |
| defend_more_on_named | 0.906 | met |
| defend_side | 0.973 | met |
| defend_flip | 0.945 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.039 | unset |
| dock_calm_lift | 0.031 | unset |
| dock_threat_docked | 0.023 | unset |
| dock_threat_docked_of_survivors | 0.048 | unset |
