**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.214

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.004 | 0.004 | 0.004 | 0.000 | 0.002 | 0.000 | 86 | 104 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.424 | 0.194 | 0.655 | 0.000 | 0.000 | 0.000 | 52 | 70 | eliminated 0.15, convoy_through 0.12, convoy_destroyed 0.73 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.0 | 15.8 | 0.00 | 0.107 | 0.88 | 0.0011 | 0.27 | 1.55 | 0.302 |
| carrier_battle | a | gunship | 860 | 71.8 | 102.8 | 0.14 | 0.163 | 0.95 | 0.0008 | 0.48 | 1.93 | 0.584 |
| carrier_battle | a | strafer | 1032 | 6.8 | 15.4 | 0.00 | 0.061 | 0.83 | 0.0017 | 0.32 | 1.52 | 0.381 |
| carrier_battle | a | all | 3956 | 21.6 | 34.6 | 0.03 | 0.122 | 0.90 | 0.0011 | 0.36 | 1.62 | 0.420 |
| carrier_battle | b | fighter | 2064 | 113.7 | 63.8 | 0.27 | 0.335 | 0.74 | 0.0081 | 0.19 | 2.35 | 0.357 |
| carrier_battle | b | gunship | 860 | 499.7 | 127.9 | 0.87 | 0.329 | 0.84 | 0.0009 | 0.50 | 2.08 | 0.571 |
| carrier_battle | b | strafer | 1032 | 152.5 | 108.9 | 0.43 | 0.226 | 0.63 | 0.0274 | 0.28 | 3.05 | 0.385 |
| carrier_battle | b | all | 3956 | 207.7 | 89.5 | 0.44 | 0.289 | 0.73 | 0.0115 | 0.29 | 2.48 | 0.417 |
| convoy_escort | a | fighter | 1462 | 62.4 | 39.9 | 0.09 | 0.318 | 0.92 | 0.0000 | 0.34 | 1.08 | 0.473 |
| convoy_escort | a | gunship | 430 | 487.1 | 122.2 | 0.53 | 0.314 | 0.94 | 0.0000 | 0.47 | 1.12 | 0.767 |
| convoy_escort | a | strafer | 688 | 127.2 | 33.5 | 0.30 | 0.154 | 0.91 | 0.0000 | 0.27 | 1.39 | 0.593 |
| convoy_escort | a | all | 2580 | 150.5 | 51.9 | 0.22 | 0.243 | 0.92 | 0.0000 | 0.36 | 1.17 | 0.588 |
| convoy_escort | b | fighter | 1462 | 202.5 | 66.9 | 0.56 | 0.397 | 0.89 | 0.0046 | 0.20 | 1.71 | 0.419 |
| convoy_escort | b | gunship | 430 | 410.7 | 224.2 | 1.00 | 0.267 | 0.89 | 0.0004 | 0.48 | 2.10 | 0.596 |
| convoy_escort | b | strafer | 688 | 78.7 | 40.0 | 0.87 | 0.113 | 0.50 | 0.0296 | 0.31 | 2.65 | 0.261 |
| convoy_escort | b | all | 2580 | 204.2 | 85.9 | 0.71 | 0.251 | 0.78 | 0.0109 | 0.29 | 2.03 | 0.409 |
