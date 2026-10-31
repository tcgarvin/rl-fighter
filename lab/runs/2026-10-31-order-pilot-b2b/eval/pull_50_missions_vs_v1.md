**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.233

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.004 | 0.008 | 0.000 | 0.000 | 0.002 | 0.000 | 89 | 109 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.461 | 0.217 | 0.705 | 0.000 | 0.000 | 0.000 | 54 | 71 | eliminated 0.13, convoy_through 0.12, convoy_destroyed 0.74 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 12.4 | 13.4 | 0.00 | 0.107 | 0.89 | 0.0011 | 0.26 | 1.56 | 0.337 |
| carrier_battle | a | gunship | 860 | 87.9 | 125.1 | 0.11 | 0.188 | 0.95 | 0.0007 | 0.44 | 1.90 | 0.602 |
| carrier_battle | a | strafer | 1032 | 9.4 | 15.4 | 0.00 | 0.062 | 0.83 | 0.0003 | 0.28 | 1.53 | 0.436 |
| carrier_battle | a | all | 3956 | 28.0 | 38.2 | 0.02 | 0.133 | 0.90 | 0.0008 | 0.33 | 1.63 | 0.450 |
| carrier_battle | b | fighter | 2064 | 118.6 | 58.6 | 0.25 | 0.345 | 0.78 | 0.0056 | 0.18 | 2.25 | 0.382 |
| carrier_battle | b | gunship | 860 | 487.7 | 134.1 | 0.82 | 0.330 | 0.85 | 0.0003 | 0.50 | 2.04 | 0.574 |
| carrier_battle | b | strafer | 1032 | 156.2 | 115.1 | 0.37 | 0.229 | 0.65 | 0.0244 | 0.28 | 3.01 | 0.409 |
| carrier_battle | b | all | 3956 | 208.6 | 89.7 | 0.40 | 0.292 | 0.76 | 0.0094 | 0.29 | 2.40 | 0.438 |
| convoy_escort | a | fighter | 1462 | 69.7 | 43.8 | 0.10 | 0.330 | 0.92 | 0.0000 | 0.34 | 1.09 | 0.482 |
| convoy_escort | a | gunship | 430 | 477.1 | 115.1 | 0.54 | 0.300 | 0.93 | 0.0002 | 0.44 | 1.16 | 0.762 |
| convoy_escort | a | strafer | 688 | 146.6 | 35.6 | 0.33 | 0.165 | 0.91 | 0.0000 | 0.25 | 1.36 | 0.604 |
| convoy_escort | a | all | 2580 | 158.1 | 53.5 | 0.23 | 0.244 | 0.92 | 0.0001 | 0.34 | 1.17 | 0.592 |
| convoy_escort | b | fighter | 1462 | 197.6 | 68.4 | 0.53 | 0.396 | 0.88 | 0.0055 | 0.20 | 1.76 | 0.412 |
| convoy_escort | b | gunship | 430 | 404.4 | 216.0 | 1.00 | 0.259 | 0.89 | 0.0010 | 0.48 | 2.06 | 0.596 |
| convoy_escort | b | strafer | 688 | 92.0 | 39.3 | 0.86 | 0.122 | 0.50 | 0.0372 | 0.32 | 2.57 | 0.270 |
| convoy_escort | b | all | 2580 | 203.9 | 85.3 | 0.70 | 0.250 | 0.77 | 0.0136 | 0.28 | 2.03 | 0.408 |
