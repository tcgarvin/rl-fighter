**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.149

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.002 | 0.000 | 0.004 | 0.000 | 0.000 | 0.000 | 79 | 96 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.297 | 0.000 | 0.593 | 0.000 | 0.000 | 0.000 | 38 | 60 | eliminated 0.17, convoy_through 0.03, convoy_destroyed 0.80 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 6.8 | 13.1 | 0.00 | 0.112 | 0.87 | 0.0003 | 0.27 | 1.41 | 0.205 |
| carrier_battle | a | gunship | 860 | 58.7 | 62.5 | 0.20 | 0.160 | 0.95 | 0.0005 | 0.47 | 1.62 | 0.448 |
| carrier_battle | a | strafer | 1032 | 7.1 | 15.6 | 0.00 | 0.077 | 0.83 | 0.0003 | 0.32 | 1.31 | 0.309 |
| carrier_battle | a | all | 3956 | 18.2 | 24.5 | 0.04 | 0.124 | 0.89 | 0.0004 | 0.35 | 1.43 | 0.310 |
| carrier_battle | b | fighter | 2064 | 121.1 | 58.8 | 0.36 | 0.261 | 0.74 | 0.0003 | 0.21 | 2.46 | 0.559 |
| carrier_battle | b | gunship | 860 | 455.1 | 118.8 | 0.95 | 0.308 | 0.80 | 0.0002 | 0.48 | 1.79 | 0.747 |
| carrier_battle | b | strafer | 1032 | 200.3 | 103.5 | 0.38 | 0.194 | 0.72 | 0.0031 | 0.20 | 2.65 | 0.661 |
| carrier_battle | b | all | 3956 | 214.4 | 83.5 | 0.49 | 0.245 | 0.75 | 0.0010 | 0.26 | 2.36 | 0.624 |
| convoy_escort | a | fighter | 1462 | 54.0 | 39.7 | 0.05 | 0.341 | 0.92 | 0.0000 | 0.34 | 1.00 | 0.404 |
| convoy_escort | a | gunship | 430 | 519.5 | 139.3 | 0.59 | 0.376 | 0.94 | 0.0001 | 0.43 | 1.02 | 0.694 |
| convoy_escort | a | strafer | 688 | 93.6 | 31.3 | 0.18 | 0.175 | 0.92 | 0.0000 | 0.26 | 1.12 | 0.529 |
| convoy_escort | a | all | 2580 | 142.2 | 54.1 | 0.17 | 0.291 | 0.93 | 0.0000 | 0.35 | 1.04 | 0.521 |
| convoy_escort | b | fighter | 1462 | 187.5 | 49.8 | 0.65 | 0.409 | 0.93 | 0.0000 | 0.21 | 1.31 | 0.642 |
| convoy_escort | b | gunship | 430 | 355.2 | 178.9 | 1.00 | 0.254 | 0.89 | 0.0000 | 0.49 | 1.68 | 0.734 |
| convoy_escort | b | strafer | 688 | 186.0 | 60.6 | 0.83 | 0.160 | 0.84 | 0.0003 | 0.19 | 2.64 | 0.629 |
| convoy_escort | b | all | 2580 | 215.1 | 74.2 | 0.75 | 0.246 | 0.89 | 0.0001 | 0.26 | 1.73 | 0.657 |
