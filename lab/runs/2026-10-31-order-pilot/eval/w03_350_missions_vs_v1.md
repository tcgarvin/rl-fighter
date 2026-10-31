**policy:ppo_bc_350.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.742

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.771 | 0.802 | 0.740 | 0.000 | 0.010 | 0.000 | 105 | 131 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.713 | 0.446 | 0.981 | 0.000 | 0.000 | 0.000 | 50 | 71 | eliminated 0.00, convoy_through 0.23, convoy_destroyed 0.77 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 70.9 | 48.2 | 0.06 | 0.288 | 0.80 | 0.0038 | 0.17 | 1.89 | 0.564 |
| carrier_battle | a | gunship | 860 | 492.8 | 167.2 | 0.54 | 0.283 | 0.82 | 0.0005 | 0.47 | 2.68 | 0.664 |
| carrier_battle | a | strafer | 1032 | 130.3 | 89.1 | 0.06 | 0.206 | 0.73 | 0.0051 | 0.20 | 2.26 | 0.625 |
| carrier_battle | a | all | 3956 | 178.1 | 84.8 | 0.16 | 0.255 | 0.79 | 0.0029 | 0.28 | 2.16 | 0.613 |
| carrier_battle | b | fighter | 2064 | 45.7 | 36.2 | 0.02 | 0.274 | 0.80 | 0.0066 | 0.16 | 1.67 | 0.375 |
| carrier_battle | b | gunship | 860 | 273.7 | 143.6 | 0.24 | 0.253 | 0.85 | 0.0014 | 0.49 | 2.47 | 0.516 |
| carrier_battle | b | strafer | 1032 | 74.7 | 90.4 | 0.04 | 0.204 | 0.69 | 0.0192 | 0.26 | 2.29 | 0.466 |
| carrier_battle | b | all | 3956 | 102.9 | 73.7 | 0.07 | 0.238 | 0.79 | 0.0079 | 0.30 | 2.01 | 0.446 |
| convoy_escort | a | fighter | 1462 | 169.5 | 48.6 | 0.47 | 0.380 | 0.92 | 0.0014 | 0.18 | 1.44 | 0.608 |
| convoy_escort | a | gunship | 430 | 380.6 | 149.0 | 0.79 | 0.237 | 0.90 | 0.0006 | 0.43 | 1.79 | 0.742 |
| convoy_escort | a | strafer | 688 | 154.4 | 39.6 | 0.55 | 0.158 | 0.81 | 0.0019 | 0.18 | 2.15 | 0.582 |
| convoy_escort | a | all | 2580 | 200.6 | 62.9 | 0.54 | 0.240 | 0.89 | 0.0013 | 0.24 | 1.68 | 0.632 |
| convoy_escort | b | fighter | 1462 | 126.1 | 56.1 | 0.27 | 0.353 | 0.86 | 0.0101 | 0.17 | 1.62 | 0.398 |
| convoy_escort | b | gunship | 430 | 489.4 | 215.9 | 0.72 | 0.315 | 0.92 | 0.0009 | 0.45 | 1.62 | 0.634 |
| convoy_escort | b | strafer | 688 | 79.6 | 37.5 | 0.60 | 0.123 | 0.52 | 0.0469 | 0.32 | 2.38 | 0.278 |
| convoy_escort | b | all | 2580 | 174.2 | 77.8 | 0.43 | 0.254 | 0.77 | 0.0189 | 0.28 | 1.82 | 0.413 |
