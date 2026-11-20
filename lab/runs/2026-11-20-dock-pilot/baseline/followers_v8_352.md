# Order drills: followers_v8_352

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_352.pt`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.01 +/- 0.01 (1/128)
- Shot down first: 0.12 +/- 0.03 (15/128)
- Out of time: 0.88 +/- 0.03 (112/128)
- Docked, of those not shot down: 0.01 +/- 0.01 (1/113)
- Came within 30 m of the dock point: 0.09 +/- 0.02 (11/128); of those, docked: 0.09 +/- 0.09 (1/11)
- Closest approach: median 126 m (10th to 90th percentile 33 to 185 m)
- Time from the order to the dock: median 5.5 s (10th to 90th percentile 5.5 to 5.5 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.03 +/- 0.02 (4/128)
- Hull at the dock (fraction of its maximum): 0.19 +/- 0.00 (n=1)
- Damage dealt per drill: 14.0 +/- 3.5 (n=128)
- Same drills, order hidden, docked: 0.03 +/- 0.02 (4/128)
- Lift from seeing the order: -0.02

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/60) | 0.12 |
| station | 0.00 (0/31) | 0.16 |
| citadel | 0.03 (1/37) | 0.08 |
| fighter | 0.00 (0/31) | 0.19 |
| strafer | 0.00 (0/34) | 0.21 |
| gunship | 0.03 (1/32) | 0.03 |
| bomber | 0.00 (0/31) | 0.03 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.01 +/- 0.01 (1/128)
- Shot down first: 0.55 +/- 0.04 (70/128)
- Out of time: 0.45 +/- 0.04 (57/128)
- Docked, of those not shot down: 0.02 +/- 0.02 (1/58)
- Came within 30 m of the dock point: 0.09 +/- 0.03 (12/128); of those, docked: 0.08 +/- 0.08 (1/12)
- Closest approach: median 134 m (10th to 90th percentile 32 to 249 m)
- Time from the order to the dock: median 5.3 s (10th to 90th percentile 5.3 to 5.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.04 +/- 0.02 (5/128)
- Hull at the dock (fraction of its maximum): 0.23 +/- 0.00 (n=1)
- Damage dealt per drill: 67.5 +/- 9.7 (n=128)
- Same drills, order hidden, docked: 0.01 +/- 0.01 (1/128)
- Lift from seeing the order: +0.00

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/64) | 0.53 |
| station | 0.00 (0/34) | 0.62 |
| citadel | 0.03 (1/30) | 0.50 |
| fighter | 0.00 (0/27) | 0.78 |
| strafer | 0.00 (0/26) | 0.69 |
| gunship | 0.00 (0/39) | 0.23 |
| bomber | 0.03 (1/36) | 0.61 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | n/a | unset |
| goto_lift | n/a | unset |
| attack_target_hit | n/a | unset |
| attack_side | n/a | unset |
| attack_flip | n/a | unset |
| defend_more_on_named | n/a | unset |
| defend_side | n/a | unset |
| defend_flip | n/a | unset |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.008 | unset |
| dock_calm_lift | -0.023 | unset |
| dock_threat_docked | 0.008 | unset |
| dock_threat_docked_of_survivors | 0.017 | unset |
