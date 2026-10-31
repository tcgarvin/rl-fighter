**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.158

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 78 | 95 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.316 | 0.000 | 0.632 | 0.000 | 0.000 | 0.000 | 38 | 53 | eliminated 0.18, convoy_destroyed 0.82 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.4 | 16.1 | 0.00 | 0.110 | 0.87 | 0.0005 | 0.28 | 1.39 | 0.339 |
| carrier_battle | a | gunship | 860 | 70.6 | 73.1 | 0.17 | 0.153 | 0.95 | 0.0004 | 0.45 | 1.67 | 0.624 |
| carrier_battle | a | strafer | 1032 | 7.9 | 16.1 | 0.00 | 0.068 | 0.83 | 0.0002 | 0.32 | 1.33 | 0.425 |
| carrier_battle | a | all | 3956 | 21.3 | 28.5 | 0.04 | 0.118 | 0.89 | 0.0004 | 0.35 | 1.44 | 0.455 |
| carrier_battle | b | fighter | 2064 | 118.1 | 57.7 | 0.32 | 0.261 | 0.75 | 0.0005 | 0.20 | 2.45 | 0.559 |
| carrier_battle | b | gunship | 860 | 470.0 | 127.0 | 0.94 | 0.315 | 0.80 | 0.0003 | 0.48 | 1.84 | 0.751 |
| carrier_battle | b | strafer | 1032 | 195.8 | 98.7 | 0.33 | 0.194 | 0.73 | 0.0033 | 0.20 | 2.66 | 0.657 |
| carrier_battle | b | all | 3956 | 214.9 | 83.5 | 0.46 | 0.249 | 0.76 | 0.0011 | 0.26 | 2.37 | 0.625 |
| convoy_escort | a | fighter | 1462 | 57.6 | 39.3 | 0.05 | 0.340 | 0.92 | 0.0000 | 0.34 | 1.01 | 0.534 |
| convoy_escort | a | gunship | 430 | 546.7 | 137.6 | 0.51 | 0.384 | 0.94 | 0.0000 | 0.44 | 1.03 | 0.824 |
| convoy_escort | a | strafer | 688 | 86.6 | 31.8 | 0.18 | 0.165 | 0.92 | 0.0000 | 0.26 | 1.12 | 0.627 |
| convoy_escort | a | all | 2580 | 146.8 | 53.7 | 0.16 | 0.291 | 0.92 | 0.0000 | 0.35 | 1.04 | 0.640 |
| convoy_escort | b | fighter | 1462 | 184.9 | 48.4 | 0.61 | 0.408 | 0.93 | 0.0000 | 0.21 | 1.28 | 0.645 |
| convoy_escort | b | gunship | 430 | 363.7 | 181.8 | 0.99 | 0.269 | 0.91 | 0.0000 | 0.49 | 1.59 | 0.745 |
| convoy_escort | b | strafer | 688 | 190.3 | 60.2 | 0.85 | 0.162 | 0.84 | 0.0002 | 0.19 | 2.72 | 0.637 |
| convoy_escort | b | all | 2580 | 216.1 | 73.8 | 0.74 | 0.250 | 0.90 | 0.0001 | 0.26 | 1.71 | 0.663 |
