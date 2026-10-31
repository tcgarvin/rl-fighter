**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.261

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.050 | 0.047 | 0.054 | 0.000 | 0.002 | 0.000 | 100 | 123 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.471 | 0.275 | 0.667 | 0.000 | 0.000 | 0.000 | 55 | 71 | eliminated 0.14, convoy_through 0.16, convoy_destroyed 0.70 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 12.2 | 15.5 | 0.01 | 0.082 | 0.83 | 0.0020 | 0.14 | 1.99 | 0.334 |
| carrier_battle | a | gunship | 860 | 147.8 | 133.7 | 0.19 | 0.141 | 0.92 | 0.0008 | 0.42 | 2.48 | 0.674 |
| carrier_battle | a | strafer | 1032 | 18.3 | 23.0 | 0.01 | 0.057 | 0.76 | 0.0021 | 0.32 | 1.86 | 0.490 |
| carrier_battle | a | all | 3956 | 43.2 | 43.2 | 0.05 | 0.103 | 0.85 | 0.0016 | 0.27 | 2.07 | 0.478 |
| carrier_battle | b | fighter | 2064 | 103.2 | 59.2 | 0.17 | 0.357 | 0.79 | 0.0070 | 0.18 | 1.99 | 0.384 |
| carrier_battle | b | gunship | 860 | 540.4 | 158.9 | 0.73 | 0.361 | 0.85 | 0.0011 | 0.50 | 2.13 | 0.559 |
| carrier_battle | b | strafer | 1032 | 153.5 | 103.9 | 0.33 | 0.212 | 0.64 | 0.0433 | 0.28 | 2.96 | 0.406 |
| carrier_battle | b | all | 3956 | 211.4 | 92.6 | 0.33 | 0.298 | 0.76 | 0.0158 | 0.30 | 2.27 | 0.438 |
| convoy_escort | a | fighter | 1462 | 101.0 | 40.0 | 0.21 | 0.281 | 0.92 | 0.0000 | 0.19 | 1.17 | 0.531 |
| convoy_escort | a | gunship | 430 | 393.5 | 112.5 | 0.52 | 0.217 | 0.93 | 0.0000 | 0.44 | 1.19 | 0.781 |
| convoy_escort | a | strafer | 688 | 139.7 | 48.9 | 0.33 | 0.151 | 0.91 | 0.0001 | 0.28 | 1.47 | 0.637 |
| convoy_escort | a | all | 2580 | 160.0 | 54.4 | 0.29 | 0.203 | 0.92 | 0.0000 | 0.27 | 1.25 | 0.616 |
| convoy_escort | b | fighter | 1462 | 201.0 | 62.2 | 0.50 | 0.402 | 0.86 | 0.0108 | 0.19 | 1.64 | 0.409 |
| convoy_escort | b | gunship | 430 | 458.6 | 224.8 | 0.98 | 0.276 | 0.90 | 0.0002 | 0.47 | 2.30 | 0.599 |
| convoy_escort | b | strafer | 688 | 78.1 | 28.2 | 0.88 | 0.105 | 0.42 | 0.0540 | 0.33 | 2.27 | 0.244 |
| convoy_escort | b | all | 2580 | 211.2 | 80.3 | 0.68 | 0.253 | 0.74 | 0.0212 | 0.28 | 1.92 | 0.399 |
