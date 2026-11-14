# Order drills: script

**Gate: report_only.** Report only, not a pass: 1 of 8 bars are unset or have nothing to measure (goto_lift).

Pilot `script`, seed 500000, sim version 8. Overall: 0.98 +/- 0.00 (1110/1129) (go-to arrivals (shown) and attack and defend swap-test flips).

## Go-to (256 drills, ship by ship)

- Arrival by the deadline, order shown: 0.99 +/- 0.00 (610/617; 43 killed first, not counted)
- Hidden pass not run (the script flies orders it cannot see).
- Near: 0.98 +/- 0.01 (340/347; 8 killed first, not counted)
- Far: 1.00 +/- 0.00 (270/270; 35 killed first, not counted)
- Enemies around the route: 1.00 +/- 0.00 (318/319; 27 killed first, not counted)
- Deadline in the order: 0.99 (440/446)
- No deadline (judged by 2x + 10 s): 0.99 (170/171)

The go-to drill changed with SIM_VERSION 8: three orders in four carry a deadline (slack 2 to 8) that the sim pays and charges by, and the match clock no longer gives the deadline away. Go-to numbers from before are not comparable, and the go-to bars were set on the old drills.

| Slack | In time |
|---|---|
| tight (under 2.5) | 0.96 (94/98) |
| medium (2.5 to 4.5) | 0.99 (196/198) |
| loose (over 4.5) | 1.00 (150/150) |

Ships not killed before their deadline, order shown:

| | All | Deadline | None | Solo |
|---|---|---|---|---|
| Ships | 617 | 446 | 171 | 46 |
| In time | 0.99 | 0.99 | 0.99 | 0.98 |
| Near miss (within 60 m) | 0.01 | 0.01 | 0.01 | 0.02 |
| At the enemy instead | 0.00 | 0.00 | 0.00 | 0.00 |
| Neither | 0.00 | 0.00 | 0.00 | 0.00 |

## Attack (256 swap pairs)

- Any damage on the named target: 0.99 +/- 0.01 (505/512)
- Swap test, flipped, groups busy with a freighter: 0.98 +/- 0.01 (195/198)
- Swap test, flipped, groups flying at the pilots: 0.84 +/- 0.05 (49/58)
- Damage on the named target per pilot: 61.8 +/- 2.2 (n=512)
- On other enemies per pilot (not judged): 42.8 +/- 2.0 (n=512)
- Chose the named side: 0.98 +/- 0.01 (500/512)
- Chose the other side: 0.01 +/- 0.00 (6/512)
- Chose neither: 0.01 +/- 0.00 (6/512)
- Swap test, flipped with the order: 0.95 +/- 0.01 (244/256)
- Swap test, one side whatever was named: 0.02 +/- 0.01 (6/256)

## Defend (256 swap pairs)

- Named ward's attackers took more than the other's: 0.99 +/- 0.01 (505/512)
- On the named ward's attackers per pilot: 87.6 +/- 2.3 (n=512)
- On the other's per pilot: 1.7 +/- 0.4 (n=512)
- Chose the named side: 1.00 +/- 0.00 (512/512)
- Chose the other side: 0.00 +/- 0.00 (0/512)
- Chose neither: 0.00 +/- 0.00 (0/512)
- Swap test, flipped with the order: 1.00 +/- 0.00 (256/256)
- Swap test, one side whatever was named: 0.00 +/- 0.00 (0/256)

## Bars

| Bar | Measured | Bar value |
|---|---|---|
| goto_arrival | 0.989 | met |
| goto_lift | n/a | unset |
| attack_target_hit | 0.986 | met |
| attack_side | 0.977 | met |
| attack_flip | 0.953 | met |
| defend_more_on_named | 0.986 | met |
| defend_side | 1.000 | met |
| defend_flip | 1.000 | met |
