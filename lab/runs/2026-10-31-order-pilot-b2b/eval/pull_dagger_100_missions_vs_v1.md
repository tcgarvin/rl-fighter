**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.186

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 | 0.000 | 84 | 102 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.372 | 0.167 | 0.578 | 0.000 | 0.000 | 0.000 | 54 | 71 | eliminated 0.15, convoy_through 0.14, convoy_destroyed 0.71 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 6.0 | 12.9 | 0.00 | 0.115 | 0.88 | 0.0011 | 0.27 | 1.52 | 0.159 |
| carrier_battle | a | gunship | 860 | 50.7 | 82.4 | 0.14 | 0.159 | 0.95 | 0.0009 | 0.49 | 1.87 | 0.404 |
| carrier_battle | a | strafer | 1032 | 5.9 | 15.6 | 0.00 | 0.075 | 0.84 | 0.0015 | 0.32 | 1.51 | 0.259 |
| carrier_battle | a | all | 3956 | 15.7 | 28.7 | 0.03 | 0.125 | 0.90 | 0.0011 | 0.36 | 1.60 | 0.268 |
| carrier_battle | b | fighter | 2064 | 113.8 | 63.6 | 0.31 | 0.321 | 0.73 | 0.0071 | 0.19 | 2.41 | 0.349 |
| carrier_battle | b | gunship | 860 | 494.4 | 122.8 | 0.93 | 0.323 | 0.83 | 0.0005 | 0.49 | 2.09 | 0.569 |
| carrier_battle | b | strafer | 1032 | 155.9 | 112.2 | 0.48 | 0.225 | 0.62 | 0.0282 | 0.28 | 3.04 | 0.383 |
| carrier_battle | b | all | 3956 | 207.5 | 89.1 | 0.49 | 0.284 | 0.72 | 0.0112 | 0.29 | 2.51 | 0.411 |
| convoy_escort | a | fighter | 1462 | 58.3 | 40.5 | 0.07 | 0.329 | 0.92 | 0.0000 | 0.35 | 1.09 | 0.313 |
| convoy_escort | a | gunship | 430 | 430.6 | 117.7 | 0.47 | 0.312 | 0.95 | 0.0003 | 0.49 | 1.07 | 0.610 |
| convoy_escort | a | strafer | 688 | 128.8 | 36.6 | 0.28 | 0.169 | 0.92 | 0.0000 | 0.27 | 1.36 | 0.474 |
| convoy_escort | a | all | 2580 | 139.2 | 52.3 | 0.19 | 0.250 | 0.93 | 0.0001 | 0.37 | 1.16 | 0.441 |
| convoy_escort | b | fighter | 1462 | 212.2 | 68.4 | 0.62 | 0.393 | 0.89 | 0.0050 | 0.20 | 1.74 | 0.421 |
| convoy_escort | b | gunship | 430 | 393.0 | 222.2 | 1.00 | 0.252 | 0.88 | 0.0004 | 0.48 | 2.17 | 0.585 |
| convoy_escort | b | strafer | 688 | 91.8 | 44.9 | 0.89 | 0.121 | 0.52 | 0.0315 | 0.31 | 2.73 | 0.277 |
| convoy_escort | b | all | 2580 | 210.2 | 87.7 | 0.76 | 0.247 | 0.79 | 0.0115 | 0.29 | 2.08 | 0.413 |
