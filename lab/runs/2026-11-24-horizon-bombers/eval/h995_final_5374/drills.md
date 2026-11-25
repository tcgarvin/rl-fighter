# Order drills: h995_final_5374

**Gate: fail.** h995_final_5374 failed the drill gate: defend_more_on_named.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_5374.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.91 +/- 0.01 (523/574) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.92 +/- 0.02 (291/318; 16 killed first, not counted)
- Same seeds, order hidden: 0.11 +/- 0.02 (34/299; 35 killed first, not counted)
- Lift from seeing the order: +0.80
- Near: 0.88 +/- 0.02 (155/176; 4 killed first, not counted)
- Far: 0.96 +/- 0.02 (136/142; 12 killed first, not counted)
- Enemies around the route: 0.90 +/- 0.02 (163/181; 11 killed first, not counted)
- Deadline in the order: 0.93 (206/221)
- No deadline (judged by 2x + 10 s): 0.88 (85/97)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.86 (48/56) |
| medium (2.5 to 4.5) | 0.94 (91/97) |
| loose (over 4.5) | 0.99 (67/68) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 318 | 221 | 97 | 23 |
| In time | 0.92 | 0.93 | 0.88 | 0.87 |
| Near miss (within 60 m) | 0.07 | 0.05 | 0.11 | 0.00 |
| At the enemy instead | 0.01 | 0.01 | 0.01 | 0.13 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.91 +/- 0.02 (232/256)
- Swap test, flipped, groups busy with a freighter: 0.94 +/- 0.02 (90/96)
- Swap test, flipped, groups flying at the pilots: 0.75 +/- 0.08 (24/32)
- Damage on the named target per pilot: 49.9 +/- 4.1 (n=256)
- On other enemies per pilot (not judged): 34.3 +/- 3.2 (n=256)
- Chose the named side: 0.94 +/- 0.02 (240/256)
- Chose the other side: 0.03 +/- 0.01 (8/256)
- Chose neither: 0.03 +/- 0.01 (8/256)
- Swap test, flipped with the order: 0.89 +/- 0.03 (114/128)
- Swap test, one side whatever was named: 0.06 +/- 0.02 (8/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.84 +/- 0.02 (216/256)
- On the named ward's attackers per pilot: 69.0 +/- 4.5 (n=256)
- On the other's per pilot: 9.2 +/- 1.3 (n=256)
- Chose the named side: 0.96 +/- 0.01 (246/256)
- Chose the other side: 0.01 +/- 0.01 (3/256)
- Chose neither: 0.03 +/- 0.01 (7/256)
- Swap test, flipped with the order: 0.92 +/- 0.02 (118/128)
- Swap test, one side whatever was named: 0.02 +/- 0.01 (3/128)

## Dock, alone (128 drills)

- Docked: 0.73 +/- 0.04 (94/128)
- Shot down first: 0.05 +/- 0.02 (7/128)
- Out of time: 0.21 +/- 0.04 (27/128)
- Docked, of those not shot down: 0.78 +/- 0.04 (94/121)
- Came within 30 m of the dock point: 0.92 +/- 0.02 (118/128); of those, docked: 0.80 +/- 0.04 (94/118)
- Closest approach: median 10 m (10th to 90th percentile 3 to 27 m)
- Time from the order to the dock: median 13.9 s (10th to 90th percentile 7.5 to 24.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.09 +/- 0.03 (12/128)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.01 (n=94)
- Damage dealt per drill: 2.1 +/- 1.3 (n=128)
- Same drills, order hidden, docked: 0.01 +/- 0.01 (1/128)
- Lift from seeing the order: +0.73

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.82 (49/60) | 0.03 |
| station | 0.61 (19/31) | 0.10 |
| citadel | 0.70 (26/37) | 0.05 |
| fighter | 0.68 (21/31) | 0.10 |
| strafer | 0.88 (30/34) | 0.06 |
| gunship | 0.66 (21/32) | 0.03 |
| bomber | 0.71 (22/31) | 0.03 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.34 +/- 0.04 (43/128)
- Shot down first: 0.45 +/- 0.04 (57/128)
- Out of time: 0.22 +/- 0.04 (28/128)
- Docked, of those not shot down: 0.61 +/- 0.06 (43/71)
- Came within 30 m of the dock point: 0.52 +/- 0.04 (66/128); of those, docked: 0.65 +/- 0.06 (43/66)
- Closest approach: median 29 m (10th to 90th percentile 4 to 186 m)
- Time from the order to the dock: median 19.5 s (10th to 90th percentile 9.2 to 33.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.09 +/- 0.03 (12/128)
- Hull at the dock (fraction of its maximum): 0.26 +/- 0.02 (n=43)
- Damage dealt per drill: 30.0 +/- 6.6 (n=128)
- Same drills, order hidden, docked: 0.01 +/- 0.01 (1/128)
- Lift from seeing the order: +0.33

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.38 (24/64) | 0.44 |
| station | 0.26 (9/34) | 0.47 |
| citadel | 0.33 (10/30) | 0.43 |
| fighter | 0.11 (3/27) | 0.78 |
| strafer | 0.15 (4/26) | 0.62 |
| gunship | 0.64 (25/39) | 0.15 |
| bomber | 0.31 (11/36) | 0.39 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.915 | met |
| goto_lift | 0.801 | met |
| attack_target_hit | 0.906 | met |
| attack_side | 0.938 | met |
| attack_flip | 0.891 | met |
| defend_more_on_named | 0.844 | failed |
| defend_side | 0.961 | met |
| defend_flip | 0.922 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.734 | unset |
| dock_calm_lift | 0.727 | unset |
| dock_threat_docked | 0.336 | unset |
| dock_threat_docked_of_survivors | 0.606 | unset |
