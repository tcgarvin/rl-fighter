# Order drills: nobomb_500

**Gate: pass.** nobomb_500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.88 +/- 0.02 (233/265) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.84 +/- 0.03 (115/137; 16 killed first, not counted)
- Same seeds, order hidden: 0.12 +/- 0.03 (16/133; 20 killed first, not counted)
- Lift from seeing the order: +0.72
- Near: 0.75 +/- 0.05 (54/72; 7 killed first, not counted)
- Far: 0.94 +/- 0.03 (61/65; 9 killed first, not counted)
- Enemies around the route: 0.78 +/- 0.05 (57/73; 12 killed first, not counted)
- Deadline in the order: 0.83 (76/92)
- No deadline (judged by 2x + 10 s): 0.87 (39/45)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (22/26) |
| medium (2.5 to 4.5) | 0.70 (26/37) |
| loose (over 4.5) | 0.97 (28/29) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 137 | 92 | 45 | 11 |
| In time | 0.84 | 0.83 | 0.87 | 0.73 |
| Near miss (within 60 m) | 0.13 | 0.14 | 0.11 | 0.09 |
| At the enemy instead | 0.03 | 0.03 | 0.02 | 0.18 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.98 +/- 0.01 (125/128)
- Swap test, flipped, groups busy with a freighter: 1.00 +/- 0.00 (45/45)
- Swap test, flipped, groups flying at the pilots: 0.89 +/- 0.07 (17/19)
- Damage on the named target per pilot: 60.4 +/- 6.2 (n=128)
- On other enemies per pilot (not judged): 48.6 +/- 4.6 (n=128)
- Chose the named side: 0.98 +/- 0.01 (126/128)
- Chose the other side: 0.00 +/- 0.00 (0/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.97 +/- 0.02 (62/64)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (0/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.89 +/- 0.03 (114/128)
- On the named ward's attackers per pilot: 74.9 +/- 6.2 (n=128)
- On the other's per pilot: 7.2 +/- 1.9 (n=128)
- Chose the named side: 0.94 +/- 0.02 (120/128)
- Chose the other side: 0.02 +/- 0.01 (3/128)
- Chose neither: 0.04 +/- 0.02 (5/128)
- Swap test, flipped with the order: 0.88 +/- 0.04 (56/64)
- Swap test, one side whatever was named: 0.05 +/- 0.03 (3/64)

## Dock, alone (64 drills)

- Docked: 0.47 +/- 0.06 (30/64)
- Shot down first: 0.09 +/- 0.04 (6/64)
- Out of time: 0.44 +/- 0.06 (28/64)
- Docked, of those not shot down: 0.52 +/- 0.07 (30/58)
- Came within 30 m of the dock point: 0.67 +/- 0.06 (43/64); of those, docked: 0.70 +/- 0.07 (30/43)
- Closest approach: median 11 m (10th to 90th percentile 2 to 72 m)
- Time from the order to the dock: median 12.5 s (10th to 90th percentile 7.6 to 25.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.30 +/- 0.02 (n=30)
- Damage dealt per drill: 0.0 +/- 0.0 (n=64)
- Same drills, order hidden, docked: 0.02 +/- 0.02 (1/64)
- Lift from seeing the order: +0.45

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.50 (16/32) | 0.06 |
| station | 0.53 (8/15) | 0.00 |
| citadel | 0.35 (6/17) | 0.24 |
| fighter | 0.64 (9/14) | 0.21 |
| strafer | 0.84 (16/19) | 0.11 |
| gunship | 0.33 (5/15) | 0.00 |
| bomber | 0.00 (0/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.19 +/- 0.05 (12/64)
- Shot down first: 0.34 +/- 0.06 (22/64)
- Out of time: 0.47 +/- 0.06 (30/64)
- Docked, of those not shot down: 0.29 +/- 0.07 (12/42)
- Came within 30 m of the dock point: 0.41 +/- 0.06 (26/64); of those, docked: 0.46 +/- 0.10 (12/26)
- Closest approach: median 33 m (10th to 90th percentile 6 to 184 m)
- Time from the order to the dock: median 28.4 s (10th to 90th percentile 6.3 to 36.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.1 +/- 0.0 (n=64); drills with one: 0.11 +/- 0.04 (7/64)
- Hull at the dock (fraction of its maximum): 0.29 +/- 0.03 (n=12)
- Damage dealt per drill: 31.5 +/- 10.0 (n=64)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (2/64)
- Lift from seeing the order: +0.16

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.21 (7/33) | 0.42 |
| station | 0.07 (1/14) | 0.07 |
| citadel | 0.24 (4/17) | 0.41 |
| fighter | 0.07 (1/14) | 0.57 |
| strafer | 0.12 (1/8) | 0.62 |
| gunship | 0.35 (9/26) | 0.04 |
| bomber | 0.06 (1/16) | 0.50 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.839 | met |
| goto_lift | 0.719 | met |
| attack_target_hit | 0.977 | met |
| attack_side | 0.984 | met |
| attack_flip | 0.969 | met |
| defend_more_on_named | 0.891 | met |
| defend_side | 0.938 | met |
| defend_flip | 0.875 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.469 | unset |
| dock_calm_lift | 0.453 | unset |
| dock_threat_docked | 0.188 | unset |
| dock_threat_docked_of_survivors | 0.286 | unset |
