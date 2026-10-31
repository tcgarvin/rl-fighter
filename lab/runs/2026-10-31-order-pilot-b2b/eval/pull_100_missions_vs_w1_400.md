**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.150

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 77 | 96 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.300 | 0.000 | 0.601 | 0.000 | 0.000 | 0.000 | 38 | 58 | eliminated 0.18, convoy_through 0.02, convoy_destroyed 0.80 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 7.9 | 11.6 | 0.00 | 0.099 | 0.88 | 0.0009 | 0.27 | 1.38 | 0.310 |
| carrier_battle | a | gunship | 860 | 67.2 | 73.3 | 0.17 | 0.156 | 0.95 | 0.0007 | 0.48 | 1.65 | 0.593 |
| carrier_battle | a | strafer | 1032 | 7.3 | 13.6 | 0.00 | 0.065 | 0.83 | 0.0005 | 0.32 | 1.35 | 0.384 |
| carrier_battle | a | all | 3956 | 20.6 | 25.5 | 0.04 | 0.117 | 0.89 | 0.0007 | 0.35 | 1.43 | 0.426 |
| carrier_battle | b | fighter | 2064 | 118.0 | 58.0 | 0.32 | 0.270 | 0.75 | 0.0005 | 0.20 | 2.37 | 0.566 |
| carrier_battle | b | gunship | 860 | 465.5 | 126.4 | 0.94 | 0.318 | 0.79 | 0.0005 | 0.48 | 1.80 | 0.749 |
| carrier_battle | b | strafer | 1032 | 201.5 | 98.3 | 0.34 | 0.195 | 0.74 | 0.0035 | 0.20 | 2.64 | 0.667 |
| carrier_battle | b | all | 3956 | 215.3 | 83.4 | 0.46 | 0.252 | 0.76 | 0.0012 | 0.26 | 2.32 | 0.631 |
| convoy_escort | a | fighter | 1462 | 51.4 | 39.8 | 0.05 | 0.338 | 0.92 | 0.0000 | 0.33 | 1.02 | 0.481 |
| convoy_escort | a | gunship | 430 | 503.9 | 138.8 | 0.53 | 0.369 | 0.94 | 0.0000 | 0.47 | 1.05 | 0.781 |
| convoy_escort | a | strafer | 688 | 99.8 | 30.2 | 0.19 | 0.176 | 0.91 | 0.0000 | 0.27 | 1.12 | 0.601 |
| convoy_escort | a | all | 2580 | 139.7 | 53.7 | 0.17 | 0.286 | 0.92 | 0.0000 | 0.36 | 1.05 | 0.599 |
| convoy_escort | b | fighter | 1462 | 188.6 | 48.8 | 0.61 | 0.414 | 0.92 | 0.0000 | 0.21 | 1.29 | 0.644 |
| convoy_escort | b | gunship | 430 | 359.4 | 180.4 | 1.00 | 0.261 | 0.90 | 0.0002 | 0.49 | 1.73 | 0.736 |
| convoy_escort | b | strafer | 688 | 173.4 | 59.5 | 0.80 | 0.156 | 0.83 | 0.0003 | 0.20 | 2.68 | 0.620 |
| convoy_escort | b | all | 2580 | 213.1 | 73.6 | 0.72 | 0.248 | 0.89 | 0.0001 | 0.27 | 1.74 | 0.657 |
