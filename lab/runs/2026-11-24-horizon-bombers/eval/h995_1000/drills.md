# Order drills: h995_1000

**Gate: pass.** h995_1000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.83 +/- 0.02 (219/265) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.81 +/- 0.03 (111/137; 16 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (20/127; 26 killed first, not counted)
- Lift from seeing the order: +0.65
- Near: 0.74 +/- 0.05 (55/74; 5 killed first, not counted)
- Far: 0.89 +/- 0.04 (56/63; 11 killed first, not counted)
- Enemies around the route: 0.73 +/- 0.05 (55/75; 10 killed first, not counted)
- Deadline in the order: 0.79 (74/94)
- No deadline (judged by 2x + 10 s): 0.86 (37/43)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.63 (17/27) |
| medium (2.5 to 4.5) | 0.79 (30/38) |
| loose (over 4.5) | 0.93 (27/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 137 | 94 | 43 | 12 |
| In time | 0.81 | 0.79 | 0.86 | 0.67 |
| Near miss (within 60 m) | 0.17 | 0.18 | 0.14 | 0.25 |
| At the enemy instead | 0.01 | 0.02 | 0.00 | 0.08 |
| Neither | 0.01 | 0.01 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.97 +/- 0.02 (124/128)
- Swap test, flipped, groups busy with a freighter: 0.93 +/- 0.04 (42/45)
- Swap test, flipped, groups flying at the pilots: 0.68 +/- 0.11 (13/19)
- Damage on the named target per pilot: 60.0 +/- 6.2 (n=128)
- On other enemies per pilot (not judged): 46.2 +/- 4.5 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.03 +/- 0.02 (4/128)
- Swap test, flipped with the order: 0.86 +/- 0.04 (55/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.89 +/- 0.03 (114/128)
- On the named ward's attackers per pilot: 74.1 +/- 6.4 (n=128)
- On the other's per pilot: 9.2 +/- 2.5 (n=128)
- Chose the named side: 0.91 +/- 0.02 (117/128)
- Chose the other side: 0.05 +/- 0.02 (6/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.83 +/- 0.05 (53/64)
- Swap test, one side whatever was named: 0.09 +/- 0.04 (6/64)

## Dock, alone (64 drills)

- Docked: 0.47 +/- 0.06 (30/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.47 +/- 0.06 (30/64)
- Docked, of those not shot down: 0.50 +/- 0.06 (30/60)
- Came within 30 m of the dock point: 0.66 +/- 0.06 (42/64); of those, docked: 0.71 +/- 0.07 (30/42)
- Closest approach: median 18 m (10th to 90th percentile 9 to 84 m)
- Time from the order to the dock: median 12.8 s (10th to 90th percentile 9.4 to 21.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.35 +/- 0.02 (n=30)
- Damage dealt per drill: 0.4 +/- 0.4 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.44

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.47 (15/32) | 0.03 |
| station | 0.40 (6/15) | 0.07 |
| citadel | 0.53 (9/17) | 0.12 |
| fighter | 0.79 (11/14) | 0.14 |
| strafer | 0.89 (17/19) | 0.05 |
| gunship | 0.13 (2/15) | 0.00 |
| bomber | 0.00 (0/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.14 +/- 0.04 (9/64)
- Shot down first: 0.34 +/- 0.06 (22/64)
- Out of time: 0.52 +/- 0.06 (33/64)
- Docked, of those not shot down: 0.21 +/- 0.06 (9/42)
- Came within 30 m of the dock point: 0.39 +/- 0.06 (25/64); of those, docked: 0.36 +/- 0.10 (9/25)
- Closest approach: median 37 m (10th to 90th percentile 8 to 191 m)
- Time from the order to the dock: median 23.3 s (10th to 90th percentile 15.8 to 43.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.24 +/- 0.03 (n=9)
- Damage dealt per drill: 42.2 +/- 12.1 (n=64)
- Same drills, order hidden, docked: 0.06 +/- 0.03 (4/64)
- Lift from seeing the order: +0.08

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.12 (4/33) | 0.39 |
| station | 0.07 (1/14) | 0.21 |
| citadel | 0.24 (4/17) | 0.35 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.75 |
| gunship | 0.27 (7/26) | 0.00 |
| bomber | 0.00 (0/16) | 0.38 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.810 | met |
| goto_lift | 0.653 | met |
| attack_target_hit | 0.969 | met |
| attack_side | 0.930 | met |
| attack_flip | 0.859 | met |
| defend_more_on_named | 0.891 | met |
| defend_side | 0.914 | met |
| defend_flip | 0.828 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.469 | unset |
| dock_calm_lift | 0.438 | unset |
| dock_threat_docked | 0.141 | unset |
| dock_threat_docked_of_survivors | 0.214 | unset |
