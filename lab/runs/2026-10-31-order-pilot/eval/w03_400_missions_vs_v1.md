**policy:ppo_bc_400.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.731

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.750 | 0.767 | 0.733 | 0.000 | 0.014 | 0.000 | 107 | 132 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.711 | 0.438 | 0.984 | 0.000 | 0.000 | 0.000 | 49 | 72 | eliminated 0.01, convoy_through 0.22, convoy_destroyed 0.77 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 67.8 | 46.6 | 0.04 | 0.290 | 0.81 | 0.0029 | 0.17 | 1.86 | 0.566 |
| carrier_battle | a | gunship | 860 | 494.9 | 174.0 | 0.48 | 0.286 | 0.83 | 0.0005 | 0.47 | 2.67 | 0.676 |
| carrier_battle | a | strafer | 1032 | 124.6 | 89.5 | 0.05 | 0.204 | 0.73 | 0.0043 | 0.20 | 2.30 | 0.619 |
| carrier_battle | a | all | 3956 | 175.5 | 85.5 | 0.14 | 0.257 | 0.80 | 0.0024 | 0.28 | 2.15 | 0.617 |
| carrier_battle | b | fighter | 2064 | 46.8 | 37.0 | 0.02 | 0.282 | 0.80 | 0.0063 | 0.16 | 1.67 | 0.377 |
| carrier_battle | b | gunship | 860 | 279.0 | 150.2 | 0.23 | 0.263 | 0.85 | 0.0011 | 0.49 | 2.47 | 0.516 |
| carrier_battle | b | strafer | 1032 | 81.4 | 87.8 | 0.03 | 0.204 | 0.69 | 0.0168 | 0.26 | 2.30 | 0.473 |
| carrier_battle | b | all | 3956 | 106.3 | 74.9 | 0.07 | 0.243 | 0.79 | 0.0071 | 0.30 | 2.01 | 0.449 |
| convoy_escort | a | fighter | 1462 | 177.0 | 51.7 | 0.46 | 0.397 | 0.92 | 0.0014 | 0.18 | 1.44 | 0.613 |
| convoy_escort | a | gunship | 430 | 374.3 | 140.7 | 0.79 | 0.235 | 0.90 | 0.0005 | 0.42 | 1.79 | 0.742 |
| convoy_escort | a | strafer | 688 | 153.1 | 40.2 | 0.55 | 0.161 | 0.81 | 0.0015 | 0.18 | 2.16 | 0.568 |
| convoy_escort | a | all | 2580 | 203.5 | 63.5 | 0.54 | 0.245 | 0.89 | 0.0012 | 0.23 | 1.69 | 0.631 |
| convoy_escort | b | fighter | 1462 | 123.8 | 57.6 | 0.26 | 0.356 | 0.87 | 0.0090 | 0.17 | 1.57 | 0.404 |
| convoy_escort | b | gunship | 430 | 480.5 | 209.7 | 0.70 | 0.316 | 0.92 | 0.0007 | 0.44 | 1.61 | 0.628 |
| convoy_escort | b | strafer | 688 | 77.3 | 37.8 | 0.60 | 0.121 | 0.52 | 0.0402 | 0.32 | 2.43 | 0.278 |
| convoy_escort | b | all | 2580 | 170.9 | 77.6 | 0.43 | 0.254 | 0.78 | 0.0165 | 0.27 | 1.81 | 0.414 |
