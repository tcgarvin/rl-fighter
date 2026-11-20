# Order drills: fighters_pay1_1317

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_1317.pt`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.00 +/- 0.00 (0/128)
- Shot down first: 0.67 +/- 0.04 (86/128)
- Out of time: 0.33 +/- 0.04 (42/128)
- Docked, of those not shot down: 0.00 +/- 0.00 (0/42)
- Came within 30 m of the dock point: 0.05 +/- 0.02 (7/128); of those, docked: 0.00 +/- 0.00 (0/7)
- Closest approach: median 137 m (10th to 90th percentile 47 to 230 m)
- Time from the order to the dock: none docked
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.01 +/- 0.01 (1/128)
- Hull at the dock (fraction of its maximum): 0.00 +/- 0.00 (n=0)
- Damage dealt per drill: 225.0 +/- 25.2 (n=128)
- Same drills, order hidden, docked: 0.00 +/- 0.00 (0/128)
- Lift from seeing the order: +0.00

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/60) | 0.65 |
| station | 0.00 (0/31) | 0.55 |
| citadel | 0.00 (0/37) | 0.81 |
| fighter | 0.00 (0/31) | 0.45 |
| strafer | 0.00 (0/34) | 0.68 |
| gunship | 0.00 (0/32) | 0.69 |
| bomber | 0.00 (0/31) | 0.87 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.01 +/- 0.01 (1/128)
- Shot down first: 0.70 +/- 0.04 (89/128)
- Out of time: 0.30 +/- 0.04 (38/128)
- Docked, of those not shot down: 0.03 +/- 0.03 (1/39)
- Came within 30 m of the dock point: 0.05 +/- 0.02 (7/128); of those, docked: 0.14 +/- 0.13 (1/7)
- Closest approach: median 158 m (10th to 90th percentile 48 to 277 m)
- Time from the order to the dock: median 5.4 s (10th to 90th percentile 5.4 to 5.4 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.0 +/- 0.0 (n=128); drills with one: 0.02 +/- 0.01 (2/128)
- Hull at the dock (fraction of its maximum): 0.28 +/- 0.00 (n=1)
- Damage dealt per drill: 221.3 +/- 29.2 (n=128)
- Same drills, order hidden, docked: 0.02 +/- 0.01 (2/128)
- Lift from seeing the order: -0.01

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.00 (0/64) | 0.67 |
| station | 0.00 (0/34) | 0.76 |
| citadel | 0.03 (1/30) | 0.67 |
| fighter | 0.00 (0/27) | 0.89 |
| strafer | 0.00 (0/26) | 0.85 |
| gunship | 0.00 (0/39) | 0.49 |
| bomber | 0.03 (1/36) | 0.67 |

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
| dock_calm_docked | 0.000 | unset |
| dock_calm_lift | 0.000 | unset |
| dock_threat_docked | 0.008 | unset |
| dock_threat_docked_of_survivors | 0.026 | unset |
