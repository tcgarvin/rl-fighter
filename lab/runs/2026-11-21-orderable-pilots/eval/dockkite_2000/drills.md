# Order drills: dockkite_2000

**Gate: pass.** dockkite_2000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.83 +/- 0.02 (220/266) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.83 +/- 0.03 (115/138; 15 killed first, not counted)
- Same seeds, order hidden: 0.10 +/- 0.03 (13/130; 23 killed first, not counted)
- Lift from seeing the order: +0.73
- Near: 0.79 +/- 0.05 (59/75; 4 killed first, not counted)
- Far: 0.89 +/- 0.04 (56/63; 11 killed first, not counted)
- Enemies around the route: 0.84 +/- 0.04 (62/74; 11 killed first, not counted)
- Deadline in the order: 0.89 (85/95)
- No deadline (judged by 2x + 10 s): 0.70 (30/43)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.77 (20/26) |
| medium (2.5 to 4.5) | 0.97 (36/37) |
| loose (over 4.5) | 0.91 (29/32) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 138 | 95 | 43 | 9 |
| In time | 0.83 | 0.89 | 0.70 | 0.78 |
| Near miss (within 60 m) | 0.14 | 0.09 | 0.23 | 0.22 |
| At the enemy instead | 0.03 | 0.01 | 0.07 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.95 +/- 0.02 (121/128)
- Swap test, flipped, groups busy with a freighter: 0.87 +/- 0.05 (39/45)
- Swap test, flipped, groups flying at the pilots: 0.63 +/- 0.11 (12/19)
- Damage on the named target per pilot: 62.2 +/- 6.0 (n=128)
- On other enemies per pilot (not judged): 50.5 +/- 4.8 (n=128)
- Chose the named side: 0.89 +/- 0.03 (114/128)
- Chose the other side: 0.05 +/- 0.02 (6/128)
- Chose neither: 0.06 +/- 0.02 (8/128)
- Swap test, flipped with the order: 0.80 +/- 0.05 (51/64)
- Swap test, one side whatever was named: 0.09 +/- 0.04 (6/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.85 +/- 0.03 (109/128)
- On the named ward's attackers per pilot: 73.4 +/- 5.9 (n=128)
- On the other's per pilot: 12.8 +/- 2.1 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.84 +/- 0.05 (54/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Dock, alone (64 drills)

- Docked: 0.38 +/- 0.06 (24/64)
- Shot down first: 0.20 +/- 0.05 (13/64)
- Out of time: 0.42 +/- 0.06 (27/64)
- Docked, of those not shot down: 0.47 +/- 0.07 (24/51)
- Came within 30 m of the dock point: 0.61 +/- 0.06 (39/64); of those, docked: 0.62 +/- 0.08 (24/39)
- Closest approach: median 24 m (10th to 90th percentile 7 to 115 m)
- Time from the order to the dock: median 15.9 s (10th to 90th percentile 8.8 to 31.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.02 (n=24)
- Damage dealt per drill: 3.3 +/- 2.5 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.34

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.50 (16/32) | 0.09 |
| station | 0.20 (3/15) | 0.33 |
| citadel | 0.29 (5/17) | 0.29 |
| fighter | 0.07 (1/14) | 0.71 |
| strafer | 0.68 (13/19) | 0.16 |
| gunship | 0.60 (9/15) | 0.00 |
| bomber | 0.06 (1/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.20 +/- 0.05 (13/64)
- Shot down first: 0.42 +/- 0.06 (27/64)
- Out of time: 0.38 +/- 0.06 (24/64)
- Docked, of those not shot down: 0.35 +/- 0.08 (13/37)
- Came within 30 m of the dock point: 0.36 +/- 0.06 (23/64); of those, docked: 0.57 +/- 0.10 (13/23)
- Closest approach: median 39 m (10th to 90th percentile 8 to 197 m)
- Time from the order to the dock: median 20.1 s (10th to 90th percentile 13.3 to 37.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.26 +/- 0.03 (n=13)
- Damage dealt per drill: 51.4 +/- 10.9 (n=64)
- Same drills, order hidden, docked: 0.06 +/- 0.03 (4/64)
- Lift from seeing the order: +0.14

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.15 (5/33) | 0.45 |
| station | 0.14 (2/14) | 0.43 |
| citadel | 0.35 (6/17) | 0.35 |
| fighter | 0.00 (0/14) | 0.71 |
| strafer | 0.12 (1/8) | 0.75 |
| gunship | 0.35 (9/26) | 0.15 |
| bomber | 0.19 (3/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.833 | met |
| goto_lift | 0.733 | met |
| attack_target_hit | 0.945 | met |
| attack_side | 0.891 | met |
| attack_flip | 0.797 | met |
| defend_more_on_named | 0.852 | met |
| defend_side | 0.922 | met |
| defend_flip | 0.844 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.375 | unset |
| dock_calm_lift | 0.344 | unset |
| dock_threat_docked | 0.203 | unset |
| dock_threat_docked_of_survivors | 0.351 | unset |
