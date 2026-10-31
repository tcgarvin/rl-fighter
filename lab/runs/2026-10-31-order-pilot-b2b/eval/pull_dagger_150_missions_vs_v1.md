**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.193

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 85 | 101 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.386 | 0.124 | 0.647 | 0.000 | 0.000 | 0.000 | 53 | 70 | eliminated 0.14, convoy_through 0.10, convoy_destroyed 0.76 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 6.1 | 16.2 | 0.00 | 0.124 | 0.88 | 0.0005 | 0.28 | 1.49 | 0.188 |
| carrier_battle | a | gunship | 860 | 52.1 | 80.2 | 0.14 | 0.151 | 0.95 | 0.0011 | 0.47 | 1.84 | 0.429 |
| carrier_battle | a | strafer | 1032 | 6.1 | 15.7 | 0.00 | 0.070 | 0.84 | 0.0005 | 0.31 | 1.48 | 0.285 |
| carrier_battle | a | all | 3956 | 16.1 | 30.0 | 0.03 | 0.121 | 0.90 | 0.0007 | 0.36 | 1.56 | 0.296 |
| carrier_battle | b | fighter | 2064 | 122.8 | 63.0 | 0.31 | 0.331 | 0.73 | 0.0076 | 0.19 | 2.41 | 0.354 |
| carrier_battle | b | gunship | 860 | 482.1 | 122.8 | 0.90 | 0.323 | 0.84 | 0.0005 | 0.50 | 2.03 | 0.571 |
| carrier_battle | b | strafer | 1032 | 155.7 | 106.9 | 0.46 | 0.227 | 0.63 | 0.0267 | 0.28 | 3.04 | 0.385 |
| carrier_battle | b | all | 3956 | 209.4 | 87.5 | 0.48 | 0.287 | 0.73 | 0.0110 | 0.29 | 2.49 | 0.413 |
| convoy_escort | a | fighter | 1462 | 58.9 | 39.1 | 0.06 | 0.324 | 0.92 | 0.0000 | 0.36 | 1.05 | 0.359 |
| convoy_escort | a | gunship | 430 | 451.7 | 117.9 | 0.55 | 0.308 | 0.94 | 0.0003 | 0.46 | 1.09 | 0.650 |
| convoy_escort | a | strafer | 688 | 130.7 | 36.3 | 0.28 | 0.165 | 0.92 | 0.0000 | 0.25 | 1.30 | 0.522 |
| convoy_escort | a | all | 2580 | 143.5 | 51.5 | 0.20 | 0.246 | 0.93 | 0.0001 | 0.36 | 1.12 | 0.488 |
| convoy_escort | b | fighter | 1462 | 207.7 | 67.1 | 0.62 | 0.398 | 0.89 | 0.0048 | 0.20 | 1.72 | 0.420 |
| convoy_escort | b | gunship | 430 | 415.7 | 226.9 | 1.00 | 0.267 | 0.89 | 0.0003 | 0.48 | 2.05 | 0.591 |
| convoy_escort | b | strafer | 688 | 81.7 | 43.7 | 0.89 | 0.117 | 0.51 | 0.0302 | 0.31 | 2.66 | 0.266 |
| convoy_escort | b | all | 2580 | 208.8 | 87.5 | 0.75 | 0.252 | 0.78 | 0.0111 | 0.29 | 2.02 | 0.410 |
