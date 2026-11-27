# Order drills: nobomb_3500

**Gate: pass.** nobomb_3500 passed the drill gate: every bar met.

**Dock gate: report_only.** Report only, not a pass: 4 of 4 bars are unset or have nothing to measure (dock_calm_docked, dock_calm_lift, dock_threat_docked, dock_threat_docked_of_survivors).

Pilot `policy:ppo_bc_3500.pt`, seed 500000, sim version 11, kinds goto, attack, defend, dock_calm, dock_threat. Overall: 0.92 +/- 0.02 (252/274) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (64 drills, ship by ship)

- Arrival by the deadline, order shown: 0.92 +/- 0.02 (135/146; 7 killed first, not counted)
- Same seeds, order hidden: 0.13 +/- 0.03 (18/134; 19 killed first, not counted)
- Lift from seeing the order: +0.79
- Near: 0.90 +/- 0.03 (69/77; 2 killed first, not counted)
- Far: 0.96 +/- 0.02 (66/69; 5 killed first, not counted)
- Enemies around the route: 0.90 +/- 0.03 (72/80; 5 killed first, not counted)
- Deadline in the order: 0.92 (90/98)
- No deadline (judged by 2x + 10 s): 0.94 (45/48)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.85 (23/27) |
| medium (2.5 to 4.5) | 0.93 (37/40) |
| loose (over 4.5) | 0.97 (30/31) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 146 | 98 | 48 | 12 |
| In time | 0.92 | 0.92 | 0.94 | 0.92 |
| Near miss (within 60 m) | 0.08 | 0.08 | 0.06 | 0.08 |
| At the enemy instead | 0.00 | 0.00 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (64 swap pairs)

- Any damage on the named target: 0.96 +/- 0.02 (123/128)
- Swap test, flipped, groups busy with a freighter: 0.93 +/- 0.04 (42/45)
- Swap test, flipped, groups flying at the pilots: 0.95 +/- 0.05 (18/19)
- Damage on the named target per pilot: 56.6 +/- 5.7 (n=128)
- On other enemies per pilot (not judged): 43.8 +/- 4.8 (n=128)
- Chose the named side: 0.97 +/- 0.02 (124/128)
- Chose the other side: 0.02 +/- 0.01 (2/128)
- Chose neither: 0.02 +/- 0.01 (2/128)
- Swap test, flipped with the order: 0.94 +/- 0.03 (60/64)
- Swap test, one side whatever was named: 0.03 +/- 0.02 (2/64)

## Defend (64 swap pairs)

- Named ward's attackers took more than the other's: 0.93 +/- 0.02 (119/128)
- On the named ward's attackers per pilot: 81.9 +/- 7.2 (n=128)
- On the other's per pilot: 5.6 +/- 1.4 (n=128)
- Chose the named side: 0.95 +/- 0.02 (121/128)
- Chose the other side: 0.00 +/- 0.00 (0/128)
- Chose neither: 0.05 +/- 0.02 (7/128)
- Swap test, flipped with the order: 0.89 +/- 0.04 (57/64)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (0/64)

## Dock, alone (64 drills)

- Docked: 0.67 +/- 0.06 (43/64)
- Shot down first: 0.09 +/- 0.04 (6/64)
- Out of time: 0.23 +/- 0.05 (15/64)
- Docked, of those not shot down: 0.74 +/- 0.06 (43/58)
- Came within 30 m of the dock point: 0.78 +/- 0.05 (50/64); of those, docked: 0.86 +/- 0.05 (43/50)
- Closest approach: median 10 m (10th to 90th percentile 2 to 52 m)
- Time from the order to the dock: median 10.2 s (10th to 90th percentile 6.1 to 30.9 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.14 +/- 0.04 (9/64)
- Hull at the dock (fraction of its maximum): 0.31 +/- 0.02 (n=43)
- Damage dealt per drill: 1.7 +/- 1.7 (n=64)
- Same drills, order hidden, docked: 0.08 +/- 0.03 (5/64)
- Lift from seeing the order: +0.59

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.75 (24/32) | 0.03 |
| station | 0.47 (7/15) | 0.20 |
| citadel | 0.71 (12/17) | 0.12 |
| fighter | 0.64 (9/14) | 0.36 |
| strafer | 1.00 (19/19) | 0.00 |
| gunship | 0.73 (11/15) | 0.00 |
| bomber | 0.25 (4/16) | 0.06 |

## Dock, enemies on the pilot (64 drills)

- Docked: 0.22 +/- 0.05 (14/64)
- Shot down first: 0.39 +/- 0.06 (25/64)
- Out of time: 0.39 +/- 0.06 (25/64)
- Docked, of those not shot down: 0.36 +/- 0.08 (14/39)
- Came within 30 m of the dock point: 0.47 +/- 0.06 (30/64); of those, docked: 0.47 +/- 0.09 (14/30)
- Closest approach: median 32 m (10th to 90th percentile 3 to 192 m)
- Time from the order to the dock: median 25.6 s (10th to 90th percentile 6.7 to 33.6 s)
- Fly-throughs (left the bay's capture circle undocked) per drill: 0.2 +/- 0.1 (n=64); drills with one: 0.12 +/- 0.04 (8/64)
- Hull at the dock (fraction of its maximum): 0.32 +/- 0.03 (n=14)
- Damage dealt per drill: 43.0 +/- 11.4 (n=64)
- Same drills, order hidden, docked: 0.05 +/- 0.03 (3/64)
- Lift from seeing the order: +0.17

| By | Docked | Shot down |
|---|---|---|
| carrier | 0.27 (9/33) | 0.42 |
| station | 0.00 (0/14) | 0.36 |
| citadel | 0.29 (5/17) | 0.35 |
| fighter | 0.14 (2/14) | 0.64 |
| strafer | 0.00 (0/8) | 1.00 |
| gunship | 0.38 (10/26) | 0.08 |
| bomber | 0.12 (2/16) | 0.38 |

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.925 | met |
| goto_lift | 0.790 | met |
| attack_target_hit | 0.961 | met |
| attack_side | 0.969 | met |
| attack_flip | 0.938 | met |
| defend_more_on_named | 0.930 | met |
| defend_side | 0.945 | met |
| defend_flip | 0.891 | met |

## Dock bars

| Bar | Measured | Bar value |
|---|---|---|
| dock_calm_docked | 0.672 | unset |
| dock_calm_lift | 0.594 | unset |
| dock_threat_docked | 0.219 | unset |
| dock_threat_docked_of_survivors | 0.359 | unset |
