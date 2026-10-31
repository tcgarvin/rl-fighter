**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.731

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.766 | 0.762 | 0.771 | 0.002 | 0.006 | 0.000 | 104 | 131 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.696 | 0.407 | 0.984 | 0.000 | 0.000 | 0.000 | 52 | 72 | eliminated 0.00, convoy_through 0.21, convoy_destroyed 0.79 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 75.0 | 48.4 | 0.06 | 0.306 | 0.81 | 0.0030 | 0.17 | 1.92 | 0.530 |
| carrier_battle | a | gunship | 860 | 490.4 | 172.0 | 0.52 | 0.292 | 0.83 | 0.0006 | 0.47 | 2.76 | 0.626 |
| carrier_battle | a | strafer | 1032 | 120.2 | 90.7 | 0.05 | 0.212 | 0.73 | 0.0046 | 0.21 | 2.26 | 0.602 |
| carrier_battle | a | all | 3956 | 177.1 | 86.3 | 0.16 | 0.266 | 0.80 | 0.0025 | 0.28 | 2.19 | 0.580 |
| carrier_battle | b | fighter | 2064 | 44.1 | 37.4 | 0.02 | 0.274 | 0.80 | 0.0076 | 0.16 | 1.66 | 0.372 |
| carrier_battle | b | gunship | 860 | 267.3 | 142.5 | 0.25 | 0.246 | 0.85 | 0.0016 | 0.49 | 2.50 | 0.515 |
| carrier_battle | b | strafer | 1032 | 81.0 | 87.8 | 0.04 | 0.203 | 0.69 | 0.0173 | 0.26 | 2.31 | 0.470 |
| carrier_battle | b | all | 3956 | 102.2 | 73.4 | 0.08 | 0.234 | 0.79 | 0.0079 | 0.30 | 2.01 | 0.447 |
| convoy_escort | a | fighter | 1462 | 176.0 | 52.2 | 0.46 | 0.384 | 0.92 | 0.0018 | 0.17 | 1.53 | 0.570 |
| convoy_escort | a | gunship | 430 | 372.5 | 153.7 | 0.80 | 0.240 | 0.89 | 0.0011 | 0.42 | 1.71 | 0.707 |
| convoy_escort | a | strafer | 688 | 145.4 | 38.8 | 0.57 | 0.153 | 0.77 | 0.0025 | 0.20 | 2.39 | 0.504 |
| convoy_escort | a | all | 2580 | 200.6 | 65.5 | 0.55 | 0.242 | 0.88 | 0.0018 | 0.23 | 1.79 | 0.584 |
| convoy_escort | b | fighter | 1462 | 128.1 | 57.1 | 0.27 | 0.348 | 0.86 | 0.0097 | 0.17 | 1.70 | 0.396 |
| convoy_escort | b | gunship | 430 | 468.1 | 206.6 | 0.66 | 0.308 | 0.92 | 0.0011 | 0.45 | 1.59 | 0.628 |
| convoy_escort | b | strafer | 688 | 81.2 | 38.6 | 0.57 | 0.124 | 0.53 | 0.0403 | 0.32 | 2.38 | 0.288 |
| convoy_escort | b | all | 2580 | 172.3 | 77.1 | 0.42 | 0.251 | 0.78 | 0.0166 | 0.27 | 1.86 | 0.414 |
