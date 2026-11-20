# Order drills: script

**Gate: report_only.** Report only, not a pass: 8 of 8 bars are unset or have nothing to measure (goto_arrival, goto_lift, attack_target_hit, attack_side, attack_flip, defend_more_on_named, defend_side, defend_flip).

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `script`, seed 500000, sim version 11, kinds dock_calm, dock_threat. Overall: n/a (go-to arrivals (shown) and attack and defend swap-test flips (not every order kind was played)).

## Dock, alone (128 drills)

- Docked: 0.95 +/- 0.02 (122/128)
- Shot down first: 0.02 +/- 0.01 (2/128)
- Out of time: 0.03 +/- 0.02 (4/128)
- Docked, of those not shot down: 0.97 +/- 0.02 (122/126)
- Came within 30 m of the dock point: 1.00 +/- 0.00 (128/128); of those, docked: 0.95 +/- 0.02 (122/128)
- Closest approach: median 9 m (10th to 90th percentile 3 to 10 m)
- Time from the order to the dock: median 12.8 s (10th to 90th percentile 8.1 to 21.7 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.4 +/- 0.1 (n=128); drills with one: 0.14 +/- 0.03 (18/128)
- Hull at the dock (fraction of its maximum): 0.33 +/- 0.01 (n=122)
- Damage dealt per drill: 0.0 +/- 0.0 (n=128)
- Hidden pass not run (the script flies orders it cannot see).

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.97 (58/60) | 0.00 |
| station | 0.97 (30/31) | 0.00 |
| citadel | 0.92 (34/37) | 0.05 |
| fighter | 0.97 (30/31) | 0.00 |
| strafer | 1.00 (34/34) | 0.00 |
| gunship | 0.88 (28/32) | 0.03 |
| bomber | 0.97 (30/31) | 0.03 |

## Dock, enemies on the pilot (128 drills)

- Docked: 0.58 +/- 0.04 (74/128)
- Shot down first: 0.41 +/- 0.04 (53/128)
- Out of time: 0.01 +/- 0.01 (1/128)
- Docked, of those not shot down: 0.99 +/- 0.01 (74/75)
- Came within 30 m of the dock point: 0.70 +/- 0.04 (90/128); of those, docked: 0.82 +/- 0.04 (74/90)
- Closest approach: median 10 m (10th to 90th percentile 3 to 170 m)
- Time from the order to the dock: median 13.7 s (10th to 90th percentile 7.7 to 21.0 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=128); drills with one: 0.12 +/- 0.03 (15/128)
- Hull at the dock (fraction of its maximum): 0.25 +/- 0.01 (n=74)
- Damage dealt per drill: 27.6 +/- 4.8 (n=128)
- Hidden pass not run (the script flies orders it cannot see).

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.59 (38/64) | 0.41 |
| station | 0.62 (21/34) | 0.35 |
| citadel | 0.50 (15/30) | 0.50 |
| fighter | 0.30 (8/27) | 0.70 |
| strafer | 0.46 (12/26) | 0.54 |
| gunship | 0.77 (30/39) | 0.21 |
| bomber | 0.67 (24/36) | 0.33 |

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
| dock_calm_docked | 0.953 | unset |
| dock_calm_lift | n/a | unset |
| dock_threat_docked | 0.578 | unset |
| dock_threat_docked_of_survivors | 0.987 | unset |
