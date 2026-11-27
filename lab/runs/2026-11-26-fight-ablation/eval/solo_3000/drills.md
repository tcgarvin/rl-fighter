# Order drills: solo_3000

**Gate: pass.** solo_3000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_3000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.85 +/- 0.02 (220/258) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.83 +/- 0.03 (108/130; 23 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.03 (16/122; 31 killed first, not counted)
- Lift from seeing the order: +0.70
- Near: 0.78 +/- 0.05 (53/68; 11 killed first, not counted)
- Far: 0.89 +/- 0.04 (55/62; 12 killed first, not counted)
- Enemies around the route: 0.78 +/- 0.05 (52/67; 18 killed first, not counted)
- Deadline in the order: 0.86 (74/86)
- No deadline (judged by 2x + 10 s): 0.77 (34/44)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.83 (20/24) |
| medium (2.5 to 4.5) | 0.82 (27/33) |
| loose (over 4.5) | 0.93 (27/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 130 | 86 | 44 | 12 |
| In time | 0.83 | 0.86 | 0.77 | 0.58 |
| Near miss (within 60 m) | 0.15 | 0.12 | 0.20 | 0.42 |
| At the enemy instead | 0.02 | 0.02 | 0.02 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.68 +/- 0.11 (13/19)
- Damage on the named target per pilot: 55.5 +/- 6.2 (n=128)
- On other enemies per pilot (not judged): 31.3 +/- 3.3 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.08 +/- 0.03 (5/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.94 +/- 0.02 (120/128)
- On the named ward's attackers per pilot: 74.0 +/- 6.1 (n=128)
- On the other's per pilot: 2.2 +/- 0.7 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.01 +/- 0.01 (1/128)
- Chose neither: 0.07 +/- 0.02 (9/128)
- Swap test, flipped with the order: 0.86 +/- 0.04 (55/64)
- Swap test, one side whatever was named: 0.02 +/- 0.02 (1/64)

## Dock, alone (64 drills)

- Docked: 0.45 +/- 0.06 (29/64)
- Shot down first: 0.08 +/- 0.03 (5/64)
- Out of time: 0.47 +/- 0.06 (30/64)
- Docked, of those not shot down: 0.49 +/- 0.07 (29/59)
- Came within 30 m of the dock point: 0.75 +/- 0.05 (48/64); of those, docked: 0.60 +/- 0.07 (29/48)
- Closest approach: median 19 m (10th to 90th percentile 2 to 38 m)
- Time from the order to the dock: median 13.4 s (10th to 90th percentile 8.3 to 29.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.34 +/- 0.02 (n=29)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.41

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.47 (15/32) | 0.03 |
| station | 0.47 (7/15) | 0.07 |
| citadel | 0.41 (7/17) | 0.18 |
| fighter | 0.36 (5/14) | 0.21 |
| strafer | 0.68 (13/19) | 0.11 |
| gunship | 0.40 (6/15) | 0.00 |
| bomber | 0.31 (5/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.34 +/- 0.06 (22/64)
- Shot down first: 0.34 +/- 0.06 (22/64)
- Out of time: 0.31 +/- 0.06 (20/64)
- Docked, of those not shot down: 0.52 +/- 0.08 (22/42)
- Came within 30 m of the dock point: 0.47 +/- 0.06 (30/64); of those, docked: 0.73 +/- 0.08 (22/30)
- Closest approach: median 33 m (10th to 90th percentile 3 to 153 m)
- Time from the order to the dock: median 25.5 s (10th to 90th percentile 17.3 to 36.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.16 +/- 0.05 (10/64)
- Hull at the dock (fraction of its maximum): 0.27 +/- 0.02 (n=22)
- Damage dealt per drill: 45.8 +/- 11.1 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.30

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.18 (6/33) | 0.42 |
| station | 0.57 (8/14) | 0.14 |
| citadel | 0.47 (8/17) | 0.35 |
| fighter | 0.14 (2/14) | 0.50 |
| strafer | 0.00 (0/8) | 0.88 |
| gunship | 0.58 (15/26) | 0.04 |
| bomber | 0.31 (5/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.831 | met |
| goto_lift | 0.700 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.945 | met |
| attack_flip | 0.891 | met |
| defend_more_on_named | 0.938 | met |
| defend_side | 0.922 | met |
| defend_flip | 0.859 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.453 | unset |
| dock_calm_lift | 0.406 | unset |
| dock_threat_docked | 0.344 | unset |
| dock_threat_docked_of_survivors | 0.524 | unset |
