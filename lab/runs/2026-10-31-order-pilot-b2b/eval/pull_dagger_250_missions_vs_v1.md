**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.246

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.004 | 0.004 | 0.004 | 0.000 | 0.000 | 0.000 | 86 | 105 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.488 | 0.190 | 0.787 | 0.000 | 0.000 | 0.000 | 51 | 70 | eliminated 0.10, convoy_through 0.10, convoy_destroyed 0.80 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.7 | 21.4 | 0.00 | 0.124 | 0.87 | 0.0006 | 0.25 | 1.58 | 0.263 |
| carrier_battle | a | gunship | 860 | 75.1 | 98.9 | 0.12 | 0.173 | 0.95 | 0.0008 | 0.45 | 1.92 | 0.515 |
| carrier_battle | a | strafer | 1032 | 8.5 | 18.3 | 0.00 | 0.070 | 0.83 | 0.0010 | 0.31 | 1.48 | 0.377 |
| carrier_battle | a | all | 3956 | 22.6 | 37.4 | 0.03 | 0.131 | 0.89 | 0.0007 | 0.33 | 1.63 | 0.374 |
| carrier_battle | b | fighter | 2064 | 120.3 | 62.5 | 0.30 | 0.326 | 0.71 | 0.0093 | 0.19 | 2.45 | 0.346 |
| carrier_battle | b | gunship | 860 | 486.4 | 125.5 | 0.89 | 0.315 | 0.84 | 0.0006 | 0.50 | 2.13 | 0.572 |
| carrier_battle | b | strafer | 1032 | 151.3 | 103.9 | 0.45 | 0.223 | 0.61 | 0.0280 | 0.29 | 3.08 | 0.370 |
| carrier_battle | b | all | 3956 | 208.0 | 87.0 | 0.47 | 0.282 | 0.72 | 0.0122 | 0.29 | 2.54 | 0.406 |
| convoy_escort | a | fighter | 1462 | 84.3 | 43.7 | 0.19 | 0.319 | 0.93 | 0.0000 | 0.31 | 1.08 | 0.509 |
| convoy_escort | a | gunship | 430 | 456.7 | 105.5 | 0.59 | 0.296 | 0.94 | 0.0001 | 0.43 | 1.18 | 0.743 |
| convoy_escort | a | strafer | 688 | 126.3 | 37.0 | 0.34 | 0.148 | 0.92 | 0.0000 | 0.24 | 1.35 | 0.610 |
| convoy_escort | a | all | 2580 | 157.6 | 52.2 | 0.29 | 0.235 | 0.93 | 0.0000 | 0.32 | 1.17 | 0.595 |
| convoy_escort | b | fighter | 1462 | 198.1 | 64.7 | 0.56 | 0.396 | 0.89 | 0.0054 | 0.19 | 1.66 | 0.423 |
| convoy_escort | b | gunship | 430 | 430.6 | 220.9 | 1.00 | 0.277 | 0.90 | 0.0003 | 0.47 | 1.94 | 0.607 |
| convoy_escort | b | strafer | 688 | 80.1 | 37.6 | 0.89 | 0.109 | 0.51 | 0.0338 | 0.31 | 2.57 | 0.270 |
| convoy_escort | b | all | 2580 | 205.4 | 83.5 | 0.72 | 0.251 | 0.79 | 0.0125 | 0.28 | 1.95 | 0.415 |
