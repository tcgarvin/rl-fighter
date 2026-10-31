**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.258

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.002 | 0.004 | 0.000 | 0.000 | 0.000 | 0.000 | 93 | 114 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.514 | 0.271 | 0.756 | 0.000 | 0.000 | 0.000 | 50 | 71 | eliminated 0.11, convoy_through 0.14, convoy_destroyed 0.74 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 6.8 | 15.0 | 0.00 | 0.068 | 0.82 | 0.0004 | 0.13 | 1.89 | 0.330 |
| carrier_battle | a | gunship | 860 | 74.5 | 106.1 | 0.12 | 0.115 | 0.94 | 0.0001 | 0.43 | 2.01 | 0.677 |
| carrier_battle | a | strafer | 1032 | 10.5 | 20.8 | 0.01 | 0.048 | 0.78 | 0.0006 | 0.37 | 1.70 | 0.477 |
| carrier_battle | a | all | 3956 | 22.5 | 36.3 | 0.03 | 0.083 | 0.85 | 0.0003 | 0.27 | 1.87 | 0.466 |
| carrier_battle | b | fighter | 2064 | 118.0 | 65.8 | 0.26 | 0.338 | 0.73 | 0.0088 | 0.20 | 2.33 | 0.350 |
| carrier_battle | b | gunship | 860 | 538.5 | 135.4 | 0.90 | 0.342 | 0.84 | 0.0010 | 0.50 | 2.01 | 0.568 |
| carrier_battle | b | strafer | 1032 | 151.4 | 92.6 | 0.46 | 0.206 | 0.58 | 0.0441 | 0.30 | 3.03 | 0.354 |
| carrier_battle | b | all | 3956 | 218.1 | 87.9 | 0.45 | 0.287 | 0.71 | 0.0167 | 0.30 | 2.44 | 0.404 |
| convoy_escort | a | fighter | 1462 | 114.7 | 46.6 | 0.27 | 0.321 | 0.93 | 0.0000 | 0.20 | 1.17 | 0.652 |
| convoy_escort | a | gunship | 430 | 361.4 | 84.4 | 0.57 | 0.192 | 0.93 | 0.0000 | 0.43 | 1.16 | 0.804 |
| convoy_escort | a | strafer | 688 | 121.6 | 39.4 | 0.31 | 0.144 | 0.91 | 0.0000 | 0.33 | 1.38 | 0.621 |
| convoy_escort | a | all | 2580 | 157.7 | 51.0 | 0.33 | 0.203 | 0.92 | 0.0000 | 0.28 | 1.23 | 0.682 |
| convoy_escort | b | fighter | 1462 | 214.1 | 64.3 | 0.59 | 0.407 | 0.88 | 0.0071 | 0.19 | 1.65 | 0.421 |
| convoy_escort | b | gunship | 430 | 400.4 | 212.0 | 0.99 | 0.264 | 0.90 | 0.0006 | 0.47 | 2.29 | 0.594 |
| convoy_escort | b | strafer | 688 | 70.8 | 29.7 | 0.89 | 0.104 | 0.44 | 0.0449 | 0.33 | 2.18 | 0.243 |
| convoy_escort | b | all | 2580 | 206.9 | 79.7 | 0.73 | 0.253 | 0.76 | 0.0166 | 0.28 | 1.90 | 0.403 |
