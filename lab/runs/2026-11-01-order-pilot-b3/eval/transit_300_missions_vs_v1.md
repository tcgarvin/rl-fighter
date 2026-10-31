**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.305

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.017 | 0.019 | 0.016 | 0.000 | 0.000 | 0.000 | 96 | 116 | carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.593 | 0.345 | 0.841 | 0.000 | 0.000 | 0.000 | 50 | 71 | eliminated 0.07, convoy_through 0.18, convoy_destroyed 0.75 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 9.1 | 20.0 | 0.01 | 0.080 | 0.82 | 0.0005 | 0.13 | 1.99 | 0.379 |
| carrier_battle | a | gunship | 860 | 117.1 | 137.7 | 0.11 | 0.147 | 0.94 | 0.0004 | 0.44 | 1.99 | 0.708 |
| carrier_battle | a | strafer | 1032 | 13.4 | 23.6 | 0.01 | 0.052 | 0.76 | 0.0004 | 0.35 | 1.68 | 0.509 |
| carrier_battle | a | all | 3956 | 33.7 | 46.5 | 0.03 | 0.102 | 0.84 | 0.0005 | 0.26 | 1.91 | 0.502 |
| carrier_battle | b | fighter | 2064 | 113.6 | 64.1 | 0.22 | 0.340 | 0.73 | 0.0074 | 0.19 | 2.29 | 0.353 |
| carrier_battle | b | gunship | 860 | 535.8 | 135.0 | 0.84 | 0.334 | 0.84 | 0.0012 | 0.50 | 2.11 | 0.561 |
| carrier_battle | b | strafer | 1032 | 151.6 | 92.6 | 0.41 | 0.205 | 0.59 | 0.0423 | 0.29 | 3.00 | 0.367 |
| carrier_battle | b | all | 3956 | 215.3 | 86.9 | 0.40 | 0.284 | 0.72 | 0.0154 | 0.30 | 2.44 | 0.410 |
| convoy_escort | a | fighter | 1462 | 117.0 | 45.7 | 0.31 | 0.315 | 0.91 | 0.0000 | 0.16 | 1.18 | 0.717 |
| convoy_escort | a | gunship | 430 | 365.8 | 87.7 | 0.58 | 0.202 | 0.92 | 0.0000 | 0.45 | 1.20 | 0.825 |
| convoy_escort | a | strafer | 688 | 133.1 | 41.4 | 0.37 | 0.141 | 0.89 | 0.0000 | 0.30 | 1.44 | 0.670 |
| convoy_escort | a | all | 2580 | 162.8 | 51.5 | 0.37 | 0.202 | 0.91 | 0.0000 | 0.26 | 1.25 | 0.730 |
| convoy_escort | b | fighter | 1462 | 197.7 | 66.6 | 0.56 | 0.395 | 0.87 | 0.0084 | 0.18 | 1.70 | 0.413 |
| convoy_escort | b | gunship | 430 | 421.6 | 219.1 | 0.96 | 0.280 | 0.89 | 0.0006 | 0.47 | 2.24 | 0.593 |
| convoy_escort | b | strafer | 688 | 73.3 | 29.2 | 0.87 | 0.105 | 0.42 | 0.0559 | 0.33 | 2.06 | 0.242 |
| convoy_escort | b | all | 2580 | 201.8 | 82.0 | 0.71 | 0.254 | 0.75 | 0.0205 | 0.28 | 1.88 | 0.399 |
