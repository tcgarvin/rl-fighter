# Order drills: h999_4000

**Gate: pass.** h999_4000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_4000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.88 +/- 0.02 (233/264) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.87 +/- 0.03 (118/136; 17 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.03 (17/129; 24 killed first, not counted)
- Lift from seeing the order: +0.74
- Near: 0.82 +/- 0.04 (60/73; 6 killed first, not counted)
- Far: 0.92 +/- 0.03 (58/63; 11 killed first, not counted)
- Enemies around the route: 0.85 +/- 0.04 (63/74; 11 killed first, not counted)
- Deadline in the order: 0.88 (82/93)
- No deadline (judged by 2x + 10 s): 0.84 (36/43)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.81 (21/26) |
| medium (2.5 to 4.5) | 0.86 (32/37) |
| loose (over 4.5) | 0.97 (29/30) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 136 | 93 | 43 | 10 |
| In time | 0.87 | 0.88 | 0.84 | 0.70 |
| Near miss (within 60 m) | 0.12 | 0.11 | 0.16 | 0.30 |
| At the enemy instead | 0.01 | 0.01 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.79 +/- 0.09 (15/19)
- Damage on the named target per pilot: 45.3 +/- 4.7 (n=128)
- On other enemies per pilot (not judged): 34.1 +/- 4.6 (n=128)
- Chose the named side: 0.96 +/- 0.02 (123/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.02 +/- 0.01 (3/128)
- Swap test, flipped with the order: 0.92 +/- 0.03 (59/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.03 (116/128)
- On the named ward's attackers per pilot: 60.7 +/- 5.4 (n=128)
- On the other's per pilot: 5.3 +/- 1.4 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.66 +/- 0.06 (42/64)
- Shot down first: 0.06 +/- 0.03 (4/64)
- Out of time: 0.28 +/- 0.06 (18/64)
- Docked, of those not shot down: 0.70 +/- 0.06 (42/60)
- Came within 30 m of the dock point: 0.72 +/- 0.06 (46/64); of those, docked: 0.91 +/- 0.04 (42/46)
- Closest approach: median 10 m (10th to 90th percentile 4 to 46 m)
- Time from the order to the dock: median 12.7 s (10th to 90th percentile 6.7 to 27.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=64); drills with one: 0.02 +/- 0.02 (1/64)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.02 (n=42)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.62

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.66 (21/32) | 0.00 |
| station | 0.87 (13/15) | 0.00 |
| citadel | 0.47 (8/17) | 0.24 |
| fighter | 0.71 (10/14) | 0.07 |
| strafer | 0.84 (16/19) | 0.16 |
| gunship | 0.47 (7/15) | 0.00 |
| bomber | 0.56 (9/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.33 +/- 0.06 (21/64)
- Shot down first: 0.31 +/- 0.06 (20/64)
- Out of time: 0.36 +/- 0.06 (23/64)
- Docked, of those not shot down: 0.48 +/- 0.08 (21/44)
- Came within 30 m of the dock point: 0.53 +/- 0.06 (34/64); of those, docked: 0.62 +/- 0.08 (21/34)
- Closest approach: median 29 m (10th to 90th percentile 5 to 181 m)
- Time from the order to the dock: median 18.7 s (10th to 90th percentile 9.4 to 39.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.08 +/- 0.03 (5/64)
- Hull at the dock (fraction of its maximum): 0.25 +/- 0.02 (n=21)
- Damage dealt per drill: 18.3 +/- 7.3 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.30

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.36 (12/33) | 0.39 |
| station | 0.21 (3/14) | 0.21 |
| citadel | 0.35 (6/17) | 0.24 |
| fighter | 0.29 (4/14) | 0.71 |
| strafer | 0.25 (2/8) | 0.62 |
| gunship | 0.35 (9/26) | 0.04 |
| bomber | 0.38 (6/16) | 0.25 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.868 | met |
| goto_lift | 0.736 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.961 | met |
| attack_flip | 0.922 | met |
| defend_more_on_named | 0.906 | met |
| defend_side | 0.938 | met |
| defend_flip | 0.875 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.656 | unset |
| dock_calm_lift | 0.625 | unset |
| dock_threat_docked | 0.328 | unset |
| dock_threat_docked_of_survivors | 0.477 | unset |
