**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.140

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 83 | 101 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.279 | 0.000 | 0.558 | 0.000 | 0.000 | 0.000 | 38 | 51 | eliminated 0.21, convoy_through 0.01, convoy_destroyed 0.78 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 6.9 | 12.2 | 0.00 | 0.073 | 0.81 | 0.0003 | 0.14 | 1.68 | 0.311 |
| carrier_battle | a | gunship | 430 | 63.8 | 61.8 | 0.15 | 0.094 | 0.92 | 0.0003 | 0.44 | 1.95 | 0.666 |
| carrier_battle | a | strafer | 516 | 9.5 | 14.0 | 0.01 | 0.045 | 0.76 | 0.0005 | 0.38 | 1.56 | 0.443 |
| carrier_battle | a | all | 1978 | 19.9 | 23.5 | 0.04 | 0.074 | 0.84 | 0.0003 | 0.28 | 1.71 | 0.451 |
| carrier_battle | b | fighter | 1032 | 135.7 | 63.0 | 0.30 | 0.317 | 0.75 | 0.0003 | 0.21 | 2.27 | 0.557 |
| carrier_battle | b | gunship | 430 | 473.7 | 127.2 | 0.96 | 0.324 | 0.78 | 0.0011 | 0.49 | 1.72 | 0.714 |
| carrier_battle | b | strafer | 516 | 223.5 | 109.2 | 0.37 | 0.227 | 0.74 | 0.0073 | 0.20 | 2.54 | 0.657 |
| carrier_battle | b | all | 1978 | 232.0 | 89.0 | 0.46 | 0.279 | 0.76 | 0.0022 | 0.27 | 2.22 | 0.617 |
| convoy_escort | a | fighter | 731 | 94.8 | 46.4 | 0.15 | 0.362 | 0.92 | 0.0000 | 0.21 | 1.06 | 0.623 |
| convoy_escort | a | gunship | 215 | 366.8 | 104.2 | 0.43 | 0.244 | 0.93 | 0.0000 | 0.45 | 1.03 | 0.804 |
| convoy_escort | a | strafer | 344 | 110.1 | 34.6 | 0.19 | 0.170 | 0.91 | 0.0001 | 0.31 | 1.11 | 0.636 |
| convoy_escort | a | all | 1290 | 144.2 | 52.9 | 0.21 | 0.242 | 0.92 | 0.0000 | 0.29 | 1.07 | 0.672 |
| convoy_escort | b | fighter | 731 | 209.2 | 51.5 | 0.62 | 0.448 | 0.93 | 0.0002 | 0.22 | 1.26 | 0.650 |
| convoy_escort | b | gunship | 215 | 374.1 | 168.5 | 0.99 | 0.273 | 0.91 | 0.0000 | 0.48 | 1.71 | 0.738 |
| convoy_escort | b | strafer | 344 | 173.4 | 41.1 | 0.87 | 0.148 | 0.82 | 0.0005 | 0.20 | 2.65 | 0.589 |
| convoy_escort | b | all | 1290 | 227.2 | 68.2 | 0.75 | 0.256 | 0.90 | 0.0002 | 0.27 | 1.71 | 0.651 |
