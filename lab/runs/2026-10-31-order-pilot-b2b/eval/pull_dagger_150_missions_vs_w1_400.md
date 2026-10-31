**policy:ppo_bc_150.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.126

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 76 | 93 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.252 | 0.000 | 0.504 | 0.000 | 0.000 | 0.000 | 38 | 59 | eliminated 0.21, convoy_through 0.03, convoy_destroyed 0.75 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 6.3 | 12.0 | 0.00 | 0.110 | 0.88 | 0.0004 | 0.28 | 1.39 | 0.192 |
| carrier_battle | a | gunship | 860 | 50.6 | 56.7 | 0.18 | 0.152 | 0.95 | 0.0008 | 0.47 | 1.58 | 0.435 |
| carrier_battle | a | strafer | 1032 | 6.5 | 14.8 | 0.00 | 0.077 | 0.83 | 0.0000 | 0.31 | 1.29 | 0.298 |
| carrier_battle | a | all | 3956 | 16.0 | 22.4 | 0.04 | 0.120 | 0.89 | 0.0005 | 0.35 | 1.41 | 0.296 |
| carrier_battle | b | fighter | 2064 | 121.7 | 56.6 | 0.36 | 0.262 | 0.75 | 0.0004 | 0.21 | 2.42 | 0.563 |
| carrier_battle | b | gunship | 860 | 447.0 | 116.9 | 0.96 | 0.306 | 0.80 | 0.0005 | 0.48 | 1.78 | 0.751 |
| carrier_battle | b | strafer | 1032 | 206.9 | 103.3 | 0.41 | 0.195 | 0.73 | 0.0035 | 0.20 | 2.68 | 0.656 |
| carrier_battle | b | all | 3956 | 214.7 | 81.9 | 0.50 | 0.245 | 0.76 | 0.0012 | 0.26 | 2.35 | 0.626 |
| convoy_escort | a | fighter | 1462 | 47.6 | 38.1 | 0.03 | 0.340 | 0.92 | 0.0000 | 0.35 | 1.01 | 0.367 |
| convoy_escort | a | gunship | 430 | 472.3 | 143.2 | 0.51 | 0.368 | 0.95 | 0.0002 | 0.46 | 1.02 | 0.673 |
| convoy_escort | a | strafer | 688 | 95.3 | 32.2 | 0.15 | 0.179 | 0.92 | 0.0000 | 0.25 | 1.07 | 0.529 |
| convoy_escort | a | all | 2580 | 131.1 | 54.1 | 0.14 | 0.287 | 0.93 | 0.0001 | 0.36 | 1.02 | 0.500 |
| convoy_escort | b | fighter | 1462 | 194.4 | 48.3 | 0.66 | 0.408 | 0.92 | 0.0000 | 0.22 | 1.31 | 0.646 |
| convoy_escort | b | gunship | 430 | 353.2 | 182.3 | 1.00 | 0.257 | 0.88 | 0.0000 | 0.50 | 1.67 | 0.730 |
| convoy_escort | b | strafer | 688 | 185.6 | 62.7 | 0.81 | 0.162 | 0.84 | 0.0002 | 0.19 | 2.63 | 0.633 |
| convoy_escort | b | all | 2580 | 218.5 | 74.5 | 0.76 | 0.248 | 0.89 | 0.0001 | 0.27 | 1.72 | 0.660 |
