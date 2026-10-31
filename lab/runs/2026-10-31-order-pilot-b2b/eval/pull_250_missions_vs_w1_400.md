**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.182

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.002 | 0.004 | 0.000 | 0.000 | 0.000 | 0.000 | 79 | 98 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.362 | 0.000 | 0.725 | 0.000 | 0.000 | 0.000 | 38 | 51 | eliminated 0.13, convoy_through 0.01, convoy_destroyed 0.86 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.3 | 17.1 | 0.00 | 0.110 | 0.87 | 0.0004 | 0.27 | 1.44 | 0.348 |
| carrier_battle | a | gunship | 860 | 93.3 | 81.5 | 0.18 | 0.174 | 0.95 | 0.0007 | 0.45 | 1.68 | 0.640 |
| carrier_battle | a | strafer | 1032 | 8.7 | 16.7 | 0.00 | 0.071 | 0.82 | 0.0002 | 0.32 | 1.37 | 0.434 |
| carrier_battle | a | all | 3956 | 26.9 | 31.0 | 0.04 | 0.130 | 0.89 | 0.0005 | 0.34 | 1.47 | 0.465 |
| carrier_battle | b | fighter | 2064 | 117.8 | 56.0 | 0.30 | 0.259 | 0.75 | 0.0007 | 0.21 | 2.46 | 0.560 |
| carrier_battle | b | gunship | 860 | 469.5 | 124.7 | 0.92 | 0.307 | 0.81 | 0.0004 | 0.48 | 1.94 | 0.753 |
| carrier_battle | b | strafer | 1032 | 198.5 | 99.4 | 0.30 | 0.196 | 0.73 | 0.0029 | 0.20 | 2.64 | 0.660 |
| carrier_battle | b | all | 3956 | 215.3 | 82.3 | 0.44 | 0.247 | 0.76 | 0.0012 | 0.27 | 2.40 | 0.627 |
| convoy_escort | a | fighter | 1462 | 66.0 | 38.4 | 0.09 | 0.343 | 0.92 | 0.0000 | 0.34 | 1.01 | 0.580 |
| convoy_escort | a | gunship | 430 | 574.6 | 136.7 | 0.61 | 0.384 | 0.94 | 0.0001 | 0.45 | 1.03 | 0.835 |
| convoy_escort | a | strafer | 688 | 93.9 | 33.7 | 0.22 | 0.171 | 0.91 | 0.0000 | 0.26 | 1.14 | 0.648 |
| convoy_escort | a | all | 2580 | 158.2 | 53.5 | 0.21 | 0.295 | 0.92 | 0.0000 | 0.35 | 1.05 | 0.668 |
| convoy_escort | b | fighter | 1462 | 179.7 | 47.4 | 0.57 | 0.414 | 0.93 | 0.0000 | 0.21 | 1.26 | 0.647 |
| convoy_escort | b | gunship | 430 | 386.9 | 176.1 | 1.00 | 0.276 | 0.91 | 0.0001 | 0.48 | 1.56 | 0.751 |
| convoy_escort | b | strafer | 688 | 170.8 | 53.2 | 0.80 | 0.156 | 0.84 | 0.0004 | 0.19 | 2.66 | 0.617 |
| convoy_escort | b | all | 2580 | 211.9 | 70.4 | 0.70 | 0.252 | 0.90 | 0.0001 | 0.26 | 1.68 | 0.661 |
