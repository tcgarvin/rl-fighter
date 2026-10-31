**policy:ppo_bc_100.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.701

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.703 | 0.729 | 0.678 | 0.000 | 0.004 | 0.000 | 109 | 133 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.698 | 0.422 | 0.973 | 0.000 | 0.000 | 0.000 | 49 | 72 | eliminated 0.01, convoy_through 0.21, convoy_destroyed 0.78 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 62.3 | 39.7 | 0.04 | 0.248 | 0.81 | 0.0022 | 0.19 | 1.89 | 0.584 |
| carrier_battle | a | gunship | 860 | 486.2 | 182.1 | 0.56 | 0.261 | 0.83 | 0.0014 | 0.48 | 2.90 | 0.707 |
| carrier_battle | a | strafer | 1032 | 101.9 | 67.5 | 0.03 | 0.166 | 0.72 | 0.0024 | 0.19 | 2.10 | 0.660 |
| carrier_battle | a | all | 3956 | 164.8 | 77.9 | 0.15 | 0.226 | 0.80 | 0.0019 | 0.30 | 2.16 | 0.646 |
| carrier_battle | b | fighter | 2064 | 50.5 | 35.1 | 0.02 | 0.288 | 0.80 | 0.0061 | 0.15 | 1.64 | 0.386 |
| carrier_battle | b | gunship | 860 | 319.7 | 162.2 | 0.30 | 0.289 | 0.86 | 0.0008 | 0.50 | 2.36 | 0.526 |
| carrier_battle | b | strafer | 1032 | 84.5 | 87.6 | 0.04 | 0.209 | 0.71 | 0.0177 | 0.26 | 2.15 | 0.500 |
| carrier_battle | b | all | 3956 | 117.9 | 76.4 | 0.09 | 0.258 | 0.80 | 0.0070 | 0.30 | 1.93 | 0.462 |
| convoy_escort | a | fighter | 1462 | 160.1 | 45.1 | 0.43 | 0.372 | 0.93 | 0.0009 | 0.20 | 1.33 | 0.650 |
| convoy_escort | a | gunship | 430 | 365.6 | 131.4 | 0.76 | 0.225 | 0.91 | 0.0010 | 0.43 | 1.77 | 0.757 |
| convoy_escort | a | strafer | 688 | 180.2 | 49.2 | 0.48 | 0.184 | 0.86 | 0.0011 | 0.17 | 1.76 | 0.688 |
| convoy_escort | a | all | 2580 | 199.7 | 60.6 | 0.50 | 0.244 | 0.91 | 0.0010 | 0.25 | 1.52 | 0.684 |
| convoy_escort | b | fighter | 1462 | 135.6 | 54.5 | 0.27 | 0.367 | 0.87 | 0.0090 | 0.17 | 1.57 | 0.413 |
| convoy_escort | b | gunship | 430 | 489.4 | 210.6 | 0.81 | 0.307 | 0.92 | 0.0005 | 0.45 | 1.74 | 0.626 |
| convoy_escort | b | strafer | 688 | 77.6 | 37.4 | 0.61 | 0.123 | 0.52 | 0.0498 | 0.32 | 2.38 | 0.276 |
| convoy_escort | b | all | 2580 | 179.1 | 76.0 | 0.45 | 0.256 | 0.78 | 0.0190 | 0.28 | 1.82 | 0.420 |
