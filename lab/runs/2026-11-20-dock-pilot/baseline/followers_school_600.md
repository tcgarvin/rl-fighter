# Order drills: followers_school_600

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_600.pt`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.02 +/- 0.01 (2/128)
- Shot down first: 0.08 +/- 0.02 (10/128)
- Out of time: 0.91 +/- 0.03 (116/128)
- Docked, of those not shot down: 0.02 +/- 0.01 (2/118)
- Came within 30 m of the dock point: 0.08 +/- 0.02 (10/128); of those, docked: 0.20 +/- 0.13 (2/10)
- Closest approach: median 88 m (10th to 90th percentile 35 to 153 m)
- Time from the order to the dock: median 8.6 s (10th to 90th percentile 5.9 to 11.3 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.01 +/- 0.01 (1/128)
- Hull at the dock (fraction of its maximum): 0.16 +/- 0.03 (n=2)
- Damage dealt per drill: 20.5 +/- 7.6 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (3/128)
- Lift from seeing the order: -0.01

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.02 (1/60) | 0.05 |
| station | 0.00 (0/31) | 0.13 |
| citadel | 0.03 (1/37) | 0.08 |
| fighter | 0.00 (0/31) | 0.13 |
| strafer | 0.00 (0/34) | 0.15 |
| gunship | 0.06 (2/32) | 0.03 |
| bomber | 0.00 (0/31) | 0.00 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.02 +/- 0.01 (3/128)
- Shot down first: 0.49 +/- 0.04 (63/128)
- Out of time: 0.48 +/- 0.04 (62/128)
- Docked, of those not shot down: 0.05 +/- 0.03 (3/65)
- Came within 30 m of the dock point: 0.12 +/- 0.03 (16/128); of those, docked: 0.19 +/- 0.10 (3/16)
- Closest approach: median 103 m (10th to 90th percentile 26 to 224 m)
- Time from the order to the dock: median 20.7 s (10th to 90th percentile 8.9 to 26.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.05 +/- 0.02 (6/128)
- Hull at the dock (fraction of its maximum): 0.21 +/- 0.05 (n=3)
- Damage dealt per drill: 70.8 +/- 9.0 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (2/128)
- Lift from seeing the order: +0.01

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.03 (2/64) | 0.50 |
| station | 0.00 (0/34) | 0.44 |
| citadel | 0.03 (1/30) | 0.53 |
| fighter | 0.00 (0/27) | 0.70 |
| strafer | 0.00 (0/26) | 0.50 |
| gunship | 0.03 (1/39) | 0.18 |
| bomber | 0.06 (2/36) | 0.67 |

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
| dock_calm_docked | 0.016 | unset |
| dock_calm_lift | -0.008 | unset |
| dock_threat_docked | 0.023 | unset |
| dock_threat_docked_of_survivors | 0.046 | unset |
