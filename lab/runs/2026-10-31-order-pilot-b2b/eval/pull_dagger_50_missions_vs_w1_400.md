**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.116

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 78 | 93 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.233 | 0.000 | 0.465 | 0.000 | 0.000 | 0.000 | 39 | 67 | eliminated 0.20, convoy_through 0.07, convoy_destroyed 0.73 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.1 | 8.9 | 0.00 | 0.109 | 0.89 | 0.0002 | 0.27 | 1.33 | 0.184 |
| carrier_battle | a | gunship | 860 | 51.7 | 58.7 | 0.13 | 0.152 | 0.95 | 0.0005 | 0.46 | 1.63 | 0.393 |
| carrier_battle | a | strafer | 1032 | 6.3 | 11.8 | 0.00 | 0.067 | 0.83 | 0.0003 | 0.31 | 1.37 | 0.261 |
| carrier_battle | a | all | 3956 | 17.1 | 20.5 | 0.03 | 0.117 | 0.90 | 0.0004 | 0.35 | 1.40 | 0.275 |
| carrier_battle | b | fighter | 2064 | 123.2 | 58.9 | 0.35 | 0.289 | 0.79 | 0.0002 | 0.20 | 2.26 | 0.580 |
| carrier_battle | b | gunship | 860 | 442.6 | 118.1 | 0.95 | 0.312 | 0.82 | 0.0003 | 0.48 | 1.78 | 0.741 |
| carrier_battle | b | strafer | 1032 | 216.4 | 110.0 | 0.36 | 0.203 | 0.75 | 0.0041 | 0.19 | 2.64 | 0.679 |
| carrier_battle | b | all | 3956 | 216.9 | 85.1 | 0.48 | 0.256 | 0.78 | 0.0012 | 0.26 | 2.25 | 0.641 |
| convoy_escort | a | fighter | 1462 | 53.4 | 39.4 | 0.04 | 0.362 | 0.92 | 0.0000 | 0.34 | 1.01 | 0.312 |
| convoy_escort | a | gunship | 430 | 439.8 | 134.4 | 0.51 | 0.349 | 0.95 | 0.0000 | 0.47 | 1.02 | 0.620 |
| convoy_escort | a | strafer | 688 | 98.8 | 34.3 | 0.14 | 0.205 | 0.92 | 0.0000 | 0.27 | 1.08 | 0.445 |
| convoy_escort | a | all | 2580 | 129.9 | 53.9 | 0.14 | 0.297 | 0.93 | 0.0000 | 0.36 | 1.03 | 0.438 |
| convoy_escort | b | fighter | 1462 | 196.6 | 48.9 | 0.67 | 0.401 | 0.92 | 0.0000 | 0.22 | 1.35 | 0.636 |
| convoy_escort | b | gunship | 430 | 352.5 | 188.8 | 1.00 | 0.252 | 0.89 | 0.0000 | 0.50 | 1.74 | 0.729 |
| convoy_escort | b | strafer | 688 | 186.1 | 60.7 | 0.79 | 0.166 | 0.84 | 0.0004 | 0.19 | 2.54 | 0.629 |
| convoy_escort | b | all | 2580 | 219.8 | 75.4 | 0.76 | 0.249 | 0.90 | 0.0001 | 0.27 | 1.73 | 0.654 |
