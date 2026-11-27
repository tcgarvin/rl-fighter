# Order drills: solo_1000

**Gate: pass.** solo_1000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.87 +/- 0.02 (233/267) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (121/139; 14 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.03 (21/128; 25 killed first, not counted)
- Lift from seeing the order: +0.71
- Near: 0.83 +/- 0.04 (60/72; 7 killed first, not counted)
- Far: 0.91 +/- 0.03 (61/67; 7 killed first, not counted)
- Enemies around the route: 0.81 +/- 0.05 (60/74; 11 killed first, not counted)
- Deadline in the order: 0.90 (83/92)
- No deadline (judged by 2x + 10 s): 0.81 (38/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (22/26) |
| medium (2.5 to 4.5) | 0.89 (32/36) |
| loose (over 4.5) | 0.97 (29/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 139 | 92 | 47 | 10 |
| In time | 0.87 | 0.90 | 0.81 | 0.60 |
| Near miss (within 60 m) | 0.09 | 0.07 | 0.15 | 0.20 |
| At the enemy instead | 0.04 | 0.03 | 0.04 | 0.20 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 0.96 +/- 0.03 (43/45)
- Swap test, flipped, groups flying at the pilots: 0.68 +/- 0.11 (13/19)
- Damage on the named target per pilot: 57.3 +/- 5.6 (n=128)
- On other enemies per pilot (not judged): 40.1 +/- 4.4 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.88 +/- 0.03 (112/128)
- On the named ward's attackers per pilot: 81.5 +/- 6.8 (n=128)
- On the other's per pilot: 6.4 +/- 2.5 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Dock, alone (64 drills)

- Docked: 0.45 +/- 0.06 (29/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.48 +/- 0.06 (31/64)
- Docked, of those not shot down: 0.48 +/- 0.06 (29/60)
- Came within 30 m of the dock point: 0.50 +/- 0.06 (32/64); of those, docked: 0.91 +/- 0.05 (29/32)
- Closest approach: median 30 m (10th to 90th percentile 4 to 118 m)
- Time from the order to the dock: median 17.1 s (10th to 90th percentile 10.5 to 22.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.02 (n=29)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.09 +/- 0.04 (6/64)
- Lift from seeing the order: +0.36

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.50 (16/32) | 0.06 |
| station | 0.40 (6/15) | 0.00 |
| citadel | 0.41 (7/17) | 0.12 |
| fighter | 0.64 (9/14) | 0.14 |
| strafer | 0.68 (13/19) | 0.11 |
| gunship | 0.47 (7/15) | 0.00 |
| bomber | 0.00 (0/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.19 +/- 0.05 (12/64)
- Shot down first: 0.28 +/- 0.06 (18/64)
- Out of time: 0.53 +/- 0.06 (34/64)
- Docked, of those not shot down: 0.26 +/- 0.06 (12/46)
- Came within 30 m of the dock point: 0.45 +/- 0.06 (29/64); of those, docked: 0.41 +/- 0.09 (12/29)
- Closest approach: median 42 m (10th to 90th percentile 7 to 184 m)
- Time from the order to the dock: median 19.8 s (10th to 90th percentile 11.0 to 33.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.30 +/- 0.04 (n=12)
- Damage dealt per drill: 33.6 +/- 9.3 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.16

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.21 (7/33) | 0.30 |
| station | 0.00 (0/14) | 0.21 |
| citadel | 0.29 (5/17) | 0.29 |
| fighter | 0.14 (2/14) | 0.71 |
| strafer | 0.12 (1/8) | 0.75 |
| gunship | 0.31 (8/26) | 0.00 |
| bomber | 0.06 (1/16) | 0.12 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.871 | met |
| goto_lift | 0.706 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.922 | met |
| attack_flip | 0.875 | met |
| defend_more_on_named | 0.875 | met |
| defend_side | 0.938 | met |
| defend_flip | 0.875 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.453 | unset |
| dock_calm_lift | 0.359 | unset |
| dock_threat_docked | 0.188 | unset |
| dock_threat_docked_of_survivors | 0.261 | unset |
