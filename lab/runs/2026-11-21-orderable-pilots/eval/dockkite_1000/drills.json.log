# Order drills: dockkite_1000

**Gate: pass.** dockkite_1000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.84 +/- 0.02 (225/269) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.79 +/- 0.03 (112/141; 12 killed first, not counted)
- Same seeds, order hidden: 0.14 +/- 0.03 (18/131; 22 killed first, not counted)
- Lift from seeing the order: +0.66
- Near: 0.74 +/- 0.05 (55/74; 5 killed first, not counted)
- Far: 0.85 +/- 0.04 (57/67; 7 killed first, not counted)
- Enemies around the route: 0.78 +/- 0.05 (61/78; 7 killed first, not counted)
- Deadline in the order: 0.83 (80/96)
- No deadline (judged by 2x + 10 s): 0.71 (32/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (23/27) |
| medium (2.5 to 4.5) | 0.76 (31/41) |
| loose (over 4.5) | 0.93 (26/28) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 141 | 96 | 45 | 12 |
| In time | 0.79 | 0.83 | 0.71 | 0.75 |
| Near miss (within 60 m) | 0.18 | 0.15 | 0.27 | 0.17 |
| At the enemy instead | 0.02 | 0.02 | 0.02 | 0.08 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.91 +/- 0.02 (117/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.89 +/- 0.07 (17/19)
- Damage on the named target per pilot: 56.3 +/- 6.6 (n=128)
- On other enemies per pilot (not judged): 45.4 +/- 4.4 (n=128)
- Chose the named side: 0.97 +/- 0.02 (124/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.94 +/- 0.03 (60/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.86 +/- 0.03 (110/128)
- On the named ward's attackers per pilot: 80.2 +/- 6.7 (n=128)
- On the other's per pilot: 10.5 +/- 1.8 (n=128)
- Chose the named side: 0.91 +/- 0.02 (117/128)
- Chose the other side: 0.03 +/- 0.02 (4/128)
- Chose neither: 0.05 +/- 0.02 (7/128)
- Swap test, flipped with the order: 0.83 +/- 0.05 (53/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Dock, alone (64 drills)

- Docked: 0.44 +/- 0.06 (28/64)
- Shot down first: 0.08 +/- 0.03 (5/64)
- Out of time: 0.48 +/- 0.06 (31/64)
- Docked, of those not shot down: 0.47 +/- 0.07 (28/59)
- Came within 30 m of the dock point: 0.66 +/- 0.06 (42/64); of those, docked: 0.67 +/- 0.07 (28/42)
- Closest approach: median 21 m (10th to 90th percentile 5 to 38 m)
- Time from the order to the dock: median 16.7 s (10th to 90th percentile 10.2 to 28.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.02 (n=28)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.39

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.50 (16/32) | 0.06 |
| station | 0.33 (5/15) | 0.13 |
| citadel | 0.41 (7/17) | 0.06 |
| fighter | 0.21 (3/14) | 0.14 |
| strafer | 0.68 (13/19) | 0.11 |
| gunship | 0.47 (7/15) | 0.00 |
| bomber | 0.31 (5/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.22 +/- 0.05 (14/64)
- Shot down first: 0.42 +/- 0.06 (27/64)
- Out of time: 0.36 +/- 0.06 (23/64)
- Docked, of those not shot down: 0.38 +/- 0.08 (14/37)
- Came within 30 m of the dock point: 0.30 +/- 0.06 (19/64); of those, docked: 0.74 +/- 0.10 (14/19)
- Closest approach: median 49 m (10th to 90th percentile 3 to 208 m)
- Time from the order to the dock: median 27.7 s (10th to 90th percentile 18.3 to 35.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.03 (n=14)
- Damage dealt per drill: 34.3 +/- 8.5 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.17

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.24 (8/33) | 0.52 |
| station | 0.07 (1/14) | 0.29 |
| citadel | 0.29 (5/17) | 0.35 |
| fighter | 0.07 (1/14) | 0.71 |
| strafer | 0.12 (1/8) | 0.75 |
| gunship | 0.38 (10/26) | 0.04 |
| bomber | 0.12 (2/16) | 0.62 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.794 | met |
| goto_lift | 0.657 | met |
| attack_target_hit | 0.914 | met |
| attack_side | 0.969 | met |
| attack_flip | 0.938 | met |
| defend_more_on_named | 0.859 | met |
| defend_side | 0.914 | met |
| defend_flip | 0.828 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.438 | unset |
| dock_calm_lift | 0.391 | unset |
| dock_threat_docked | 0.219 | unset |
| dock_threat_docked_of_survivors | 0.378 | unset |
