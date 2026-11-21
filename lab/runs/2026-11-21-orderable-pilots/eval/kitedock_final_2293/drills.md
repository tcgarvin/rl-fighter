# Order drills: kitedock_final_2293

**Gate: pass.** kitedock_final_2293 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2293.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.89 +/- 0.01 (505/566) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (128 drills, ship by ship)

- Arrival by the deadline, order shown: 0.86 +/- 0.02 (267/310; 24 killed first, not counted)
- Same seeds, order hidden: 0.16 +/- 0.02 (47/298; 36 killed first, not counted)
- Lift from seeing the order: +0.70
- Near: 0.81 +/- 0.03 (139/171; 9 killed first, not counted)
- Far: 0.92 +/- 0.02 (128/139; 15 killed first, not counted)
- Enemies around the route: 0.86 +/- 0.03 (149/174; 18 killed first, not counted)
- Deadline in the order: 0.89 (197/222)
- No deadline (judged by 2x + 10 s): 0.80 (70/88)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.75 (39/52) |
| medium (2.5 to 4.5) | 0.92 (94/102) |
| loose (over 4.5) | 0.94 (64/68) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 310 | 222 | 88 | 19 |
| In time | 0.86 | 0.89 | 0.80 | 0.89 |
| Near miss (within 60 m) | 0.11 | 0.09 | 0.16 | 0.11 |
| At the enemy instead | 0.03 | 0.02 | 0.05 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (128 swap pairs)

- Any damage on the named target: 0.96 +/- 0.01 (246/256)
- Swap test, flipped, groups busy with a freighter: 0.97 +/- 0.02 (93/96)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.06 (27/32)
- Damage on the named target per pilot: 59.9 +/- 4.9 (n=256)
- On other enemies per pilot (not judged): 41.3 +/- 3.8 (n=256)
- Chose the named side: 0.97 +/- 0.01 (248/256)
- Chose the other side: 0.02 +/- 0.01 (5/256)
- Chose neither: 0.01 +/- 0.01 (3/256)
- Swap test, flipped with the order: 0.94 +/- 0.02 (120/128)
- Swap test, one side whatever was named: 0.04 +/- 0.02 (5/128)

## Defend (128 swap pairs)

- Named ward's attackers took more than the other's: 0.89 +/- 0.02 (227/256)
- On the named ward's attackers per pilot: 78.4 +/- 4.9 (n=256)
- On the other's per pilot: 8.5 +/- 1.4 (n=256)
- Chose the named side: 0.96 +/- 0.01 (246/256)
- Chose the other side: 0.02 +/- 0.01 (4/256)
- Chose neither: 0.02 +/- 0.01 (6/256)
- Swap test, flipped with the order: 0.92 +/- 0.02 (118/128)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (4/128)

## Dock, alone (128 drills)

- Docked: 0.18 +/- 0.03 (23/128)
- Shot down first: 0.12 +/- 0.03 (15/128)
- Out of time: 0.70 +/- 0.04 (90/128)
- Docked, of those not shot down: 0.20 +/- 0.04 (23/113)
- Came within 30 m of the dock point: 0.55 +/- 0.04 (70/128); of those, docked: 0.33 +/- 0.06 (23/70)
- Closest approach: median 26 m (10th to 90th percentile 3 to 80 m)
- Time from the order to the dock: median 18.5 s (10th to 90th percentile 10.2 to 31.8 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.0 (n=128); drills with one: 0.13 +/- 0.03 (17/128)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=23)
- Damage dealt per drill: 3.0 +/- 2.0 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (2/128)
- Lift from seeing the order: +0.16

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.13 (8/60) | 0.12 |
| station | 0.16 (5/31) | 0.10 |
| citadel | 0.27 (10/37) | 0.14 |
| fighter | 0.03 (1/31) | 0.16 |
| strafer | 0.15 (5/34) | 0.21 |
| gunship | 0.47 (15/32) | 0.03 |
| bomber | 0.06 (2/31) | 0.06 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.09 +/- 0.02 (11/128)
- Shot down first: 0.39 +/- 0.04 (50/128)
- Out of time: 0.52 +/- 0.04 (67/128)
- Docked, of those not shot down: 0.14 +/- 0.04 (11/78)
- Came within 30 m of the dock point: 0.32 +/- 0.04 (41/128); of those, docked: 0.27 +/- 0.07 (11/41)
- Closest approach: median 52 m (10th to 90th percentile 10 to 199 m)
- Time from the order to the dock: median 25.8 s (10th to 90th percentile 13.2 to 33.2 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=128); drills with one: 0.07 +/- 0.02 (9/128)
- Hull at the dock (fraction of its maximum): 0.23 +/- 0.03 (n=11)
- Damage dealt per drill: 37.7 +/- 6.2 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.09

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.06 (4/64) | 0.36 |
| station | 0.09 (3/34) | 0.47 |
| citadel | 0.13 (4/30) | 0.37 |
| fighter | 0.04 (1/27) | 0.63 |
| strafer | 0.04 (1/26) | 0.58 |
| gunship | 0.23 (9/39) | 0.10 |
| bomber | 0.00 (0/36) | 0.39 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.861 | met |
| goto_lift | 0.704 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.969 | met |
| attack_flip | 0.938 | met |
| defend_more_on_named | 0.887 | met |
| defend_side | 0.961 | met |
| defend_flip | 0.922 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.180 | unset |
| dock_calm_lift | 0.164 | unset |
| dock_threat_docked | 0.086 | unset |
| dock_threat_docked_of_survivors | 0.141 | unset |
