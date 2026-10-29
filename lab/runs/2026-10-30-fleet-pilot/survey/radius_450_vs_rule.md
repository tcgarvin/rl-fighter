> "rule" / radius 0 below is the growing radius that was proposed then (450 m + 25 m per ship beyond two, 600 m for 4v4), compared with a flat 450 m; the flat 450 m was adopted (plan.md §2). Command: `tools/fleet_survey.py --suite fleet_v1 --n-per-roster 64 --arena-radius 450 0`.


## radius 450 (0 = rule): rosters

| roster | cost | team-0 win | time limit | draws | median ticks |
|---|---|---|---|---|---|
| 1v1 F v F | 10 v 10 | 0.41 | 0.00 | 0.03 | 1442 |
| 1v1 S v S | 10 v 10 | 0.53 | 0.00 | 0.00 | 794 |
| 1v1 G v G | 30 v 30 | 0.42 | 0.41 | 0.03 | 2646 |
| 2v2 FS v FS | 20 v 20 | 0.48 | 0.00 | 0.00 | 1030 |
| 2v2 FG v SS | 40 v 20 | 1.00 | 0.00 | 0.00 | 620 |
| 2v2 SG v FF | 40 v 20 | 1.00 | 0.00 | 0.00 | 700 |
| 3v3 FSG v FSG | 50 v 50 | 0.62 | 0.52 | 0.00 | 2700 |
| 3v3 FFS v SSF | 30 v 30 | 0.56 | 0.00 | 0.00 | 862 |
| 3v3 FFG v SSG | 50 v 50 | 0.46 | 0.61 | 0.02 | 2700 |
| 2v3 FG v FFS | 40 v 30 | 0.84 | 0.00 | 0.02 | 1008 |
| 2v3 SS v FFF | 20 v 30 | 0.00 | 0.00 | 0.00 | 640 |
| draft G v FFF | 30 v 30 | 0.00 | 0.00 | 0.00 | 645 |
| draft G v SSS | 30 v 30 | 0.11 | 0.00 | 0.00 | 1158 |
| draft GF v FFSS | 40 v 40 | 0.41 | 0.00 | 0.00 | 1338 |
| 4v4 FFSS v FFSS | 40 v 40 | 0.62 | 0.00 | 0.00 | 910 |
| 4v4 FSGF v SSFG | 60 v 60 | 0.52 | 0.38 | 0.00 | 2226 |

## per hull, both sides pooled

| hull | ship-matches | dmg | shield dmg | dmg / cost | survival | hit rate | shots | engage | outside | engine | crash dmg |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fighter | 2112 | 59.9 | 30.8 | 9.07 | 0.36 | 0.590 | 34 | 0.89 | 0.0000 | 0.39 | 4.9 |
| gunship | 896 | 210.4 | 86.6 | 9.90 | 0.66 | 0.208 | 348 | 0.95 | 0.0000 | 0.53 | 0.9 |
| strafer | 1856 | 61.6 | 31.6 | 9.32 | 0.34 | 0.327 | 103 | 0.89 | 0.0000 | 0.43 | 0.6 |

## radius 0 (0 = rule): rosters

| roster | cost | team-0 win | time limit | draws | median ticks |
|---|---|---|---|---|---|
| 1v1 F v F | 10 v 10 | 0.41 | 0.00 | 0.03 | 1442 |
| 1v1 S v S | 10 v 10 | 0.53 | 0.00 | 0.00 | 794 |
| 1v1 G v G | 30 v 30 | 0.42 | 0.41 | 0.03 | 2646 |
| 2v2 FS v FS | 20 v 20 | 0.50 | 0.00 | 0.00 | 1109 |
| 2v2 FG v SS | 40 v 20 | 1.00 | 0.00 | 0.00 | 632 |
| 2v2 SG v FF | 40 v 20 | 1.00 | 0.00 | 0.00 | 692 |
| 3v3 FSG v FSG | 50 v 50 | 0.56 | 0.62 | 0.00 | 2700 |
| 3v3 FFS v SSF | 30 v 30 | 0.48 | 0.00 | 0.00 | 978 |
| 3v3 FFG v SSG | 50 v 50 | 0.67 | 0.42 | 0.00 | 2590 |
| 2v3 FG v FFS | 40 v 30 | 0.84 | 0.00 | 0.00 | 918 |
| 2v3 SS v FFF | 20 v 30 | 0.00 | 0.00 | 0.00 | 703 |
| draft G v FFF | 30 v 30 | 0.00 | 0.00 | 0.00 | 666 |
| draft G v SSS | 30 v 30 | 0.20 | 0.00 | 0.00 | 1202 |
| draft GF v FFSS | 40 v 40 | 0.28 | 0.00 | 0.00 | 1250 |
| 4v4 FFSS v FFSS | 40 v 40 | 0.61 | 0.00 | 0.00 | 1030 |
| 4v4 FSGF v SSFG | 60 v 60 | 0.56 | 0.56 | 0.00 | 2700 |

## per hull, both sides pooled

| hull | ship-matches | dmg | shield dmg | dmg / cost | survival | hit rate | shots | engage | outside | engine | crash dmg |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fighter | 2112 | 62.0 | 30.6 | 9.27 | 0.37 | 0.573 | 36 | 0.86 | 0.0000 | 0.40 | 4.7 |
| gunship | 896 | 212.6 | 86.4 | 9.97 | 0.67 | 0.206 | 352 | 0.93 | 0.0000 | 0.54 | 0.7 |
| strafer | 1856 | 58.2 | 31.8 | 9.01 | 0.32 | 0.324 | 100 | 0.86 | 0.0000 | 0.43 | 0.6 |

## arena radius

| radius | class | time limit | median ticks | engage (all) | crash dmg / ship |
|---|---|---|---|---|---|
| 450 | 1v1 | 0.14 | 1442 | 0.91 | 2.5 |
| 450 | 2v2 | 0.00 | 730 | 0.91 | 2.5 |
| 450 | 3v3 | 0.38 | 2276 | 0.91 | 2.5 |
| 450 | 2v3 | 0.00 | 736 | 0.91 | 2.5 |
| 450 | draft | 0.00 | 1095 | 0.91 | 2.5 |
| 450 | 4v4 | 0.19 | 1236 | 0.91 | 2.5 |
| rule | 1v1 | 0.14 | 1442 | 0.89 | 2.4 |
| rule | 2v2 | 0.00 | 708 | 0.89 | 2.4 |
| rule | 3v3 | 0.35 | 2222 | 0.89 | 2.4 |
| rule | 2v3 | 0.00 | 752 | 0.89 | 2.4 |
| rule | draft | 0.00 | 1076 | 0.89 | 2.4 |
| rule | 4v4 | 0.28 | 1476 | 0.89 | 2.4 |
