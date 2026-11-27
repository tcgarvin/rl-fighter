# Order drills: solo_2000

**Gate: pass.** solo_2000 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_2000.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.86 +/- 0.02 (227/264) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.85 +/- 0.03 (116/136; 17 killed first, not counted)
- Same seeds, order hidden: 0.14 +/- 0.03 (18/126; 27 killed first, not counted)
- Lift from seeing the order: +0.71
- Near: 0.81 +/- 0.05 (58/72; 7 killed first, not counted)
- Far: 0.91 +/- 0.04 (58/64; 10 killed first, not counted)
- Enemies around the route: 0.78 +/- 0.05 (57/73; 12 killed first, not counted)
- Deadline in the order: 0.89 (79/89)
- No deadline (judged by 2x + 10 s): 0.79 (37/47)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.84 (21/25) |
| medium (2.5 to 4.5) | 0.86 (30/35) |
| loose (over 4.5) | 0.97 (28/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 136 | 89 | 47 | 13 |
| In time | 0.85 | 0.89 | 0.79 | 0.77 |
| Near miss (within 60 m) | 0.12 | 0.10 | 0.15 | 0.08 |
| At the enemy instead | 0.03 | 0.01 | 0.06 | 0.15 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.02 (44/45)
- Swap test, flipped, groups flying at the pilots: 0.58 +/- 0.11 (11/19)
- Damage on the named target per pilot: 56.8 +/- 6.0 (n=128)
- On other enemies per pilot (not judged): 31.9 +/- 3.3 (n=128)
- Chose the named side: 0.92 +/- 0.02 (118/128)
- Chose the other side: 0.04 +/- 0.02 (5/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.86 +/- 0.04 (55/64)
- Swap test, one side whatever was named: 0.06 +/- 0.03 (4/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.91 +/- 0.03 (116/128)
- On the named ward's attackers per pilot: 78.7 +/- 6.7 (n=128)
- On the other's per pilot: 3.0 +/- 1.0 (n=128)
- Chose the named side: 0.93 +/- 0.02 (119/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.05 +/- 0.02 (6/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.48 +/- 0.06 (31/64)
- Shot down first: 0.12 +/- 0.04 (8/64)
- Out of time: 0.39 +/- 0.06 (25/64)
- Docked, of those not shot down: 0.55 +/- 0.07 (31/56)
- Came within 30 m of the dock point: 0.62 +/- 0.06 (40/64); of those, docked: 0.78 +/- 0.07 (31/40)
- Closest approach: median 22 m (10th to 90th percentile 2 to 140 m)
- Time from the order to the dock: median 17.5 s (10th to 90th percentile 9.6 to 30.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.1 (n=64); drills with one: 0.09 +/- 0.04 (6/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.02 (n=31)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.08 +/- 0.03 (5/64)
- Lift from seeing the order: +0.41

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.47 (15/32) | 0.09 |
| station | 0.53 (8/15) | 0.13 |
| citadel | 0.47 (8/17) | 0.18 |
| fighter | 0.43 (6/14) | 0.07 |
| strafer | 0.47 (9/19) | 0.37 |
| gunship | 0.80 (12/15) | 0.00 |
| bomber | 0.25 (4/16) | 0.00 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.34 +/- 0.06 (22/64)
- Shot down first: 0.36 +/- 0.06 (23/64)
- Out of time: 0.30 +/- 0.06 (19/64)
- Docked, of those not shot down: 0.54 +/- 0.08 (22/41)
- Came within 30 m of the dock point: 0.50 +/- 0.06 (32/64); of those, docked: 0.69 +/- 0.08 (22/32)
- Closest approach: median 30 m (10th to 90th percentile 1 to 181 m)
- Time from the order to the dock: median 21.4 s (10th to 90th percentile 11.8 to 30.1 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.17 +/- 0.05 (11/64)
- Hull at the dock (fraction of its maximum): 0.28 +/- 0.02 (n=22)
- Damage dealt per drill: 42.5 +/- 9.6 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.31

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.39 (13/33) | 0.39 |
| station | 0.21 (3/14) | 0.21 |
| citadel | 0.35 (6/17) | 0.41 |
| fighter | 0.14 (2/14) | 0.64 |
| strafer | 0.12 (1/8) | 0.88 |
| gunship | 0.65 (17/26) | 0.00 |
| bomber | 0.12 (2/16) | 0.44 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.853 | met |
| goto_lift | 0.710 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.922 | met |
| attack_flip | 0.859 | met |
| defend_more_on_named | 0.906 | met |
| defend_side | 0.930 | met |
| defend_flip | 0.875 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.484 | unset |
| dock_calm_lift | 0.406 | unset |
| dock_threat_docked | 0.344 | unset |
| dock_threat_docked_of_survivors | 0.537 | unset |
