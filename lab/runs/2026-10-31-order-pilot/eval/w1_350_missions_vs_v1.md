**policy:ppo_bc_350.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.764

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.789 | 0.814 | 0.764 | 0.000 | 0.012 | 0.000 | 106 | 132 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.738 | 0.500 | 0.977 | 0.000 | 0.000 | 0.000 | 52 | 72 | eliminated 0.01, convoy_through 0.26, convoy_destroyed 0.74 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 68.2 | 40.4 | 0.05 | 0.263 | 0.79 | 0.0031 | 0.19 | 1.92 | 0.542 |
| carrier_battle | a | gunship | 860 | 509.4 | 175.1 | 0.55 | 0.279 | 0.83 | 0.0008 | 0.49 | 2.77 | 0.695 |
| carrier_battle | a | strafer | 1032 | 116.7 | 90.8 | 0.05 | 0.195 | 0.72 | 0.0035 | 0.21 | 2.25 | 0.642 |
| carrier_battle | a | all | 3956 | 176.7 | 82.8 | 0.16 | 0.246 | 0.79 | 0.0024 | 0.30 | 2.19 | 0.618 |
| carrier_battle | b | fighter | 2064 | 43.6 | 36.2 | 0.02 | 0.281 | 0.80 | 0.0069 | 0.16 | 1.64 | 0.374 |
| carrier_battle | b | gunship | 860 | 281.4 | 154.8 | 0.23 | 0.269 | 0.86 | 0.0012 | 0.49 | 2.47 | 0.516 |
| carrier_battle | b | strafer | 1032 | 80.7 | 82.4 | 0.03 | 0.208 | 0.71 | 0.0176 | 0.26 | 2.12 | 0.493 |
| carrier_battle | b | all | 3956 | 105.0 | 74.0 | 0.07 | 0.247 | 0.80 | 0.0074 | 0.30 | 1.94 | 0.453 |
| convoy_escort | a | fighter | 1462 | 165.4 | 47.6 | 0.42 | 0.376 | 0.92 | 0.0013 | 0.22 | 1.42 | 0.617 |
| convoy_escort | a | gunship | 430 | 370.2 | 136.4 | 0.80 | 0.224 | 0.90 | 0.0008 | 0.45 | 1.85 | 0.739 |
| convoy_escort | a | strafer | 688 | 175.3 | 55.0 | 0.55 | 0.176 | 0.81 | 0.0032 | 0.22 | 2.36 | 0.588 |
| convoy_escort | a | all | 2580 | 202.2 | 64.4 | 0.52 | 0.240 | 0.89 | 0.0017 | 0.27 | 1.74 | 0.638 |
| convoy_escort | b | fighter | 1462 | 120.9 | 54.5 | 0.27 | 0.348 | 0.86 | 0.0107 | 0.17 | 1.62 | 0.393 |
| convoy_escort | b | gunship | 430 | 461.6 | 221.2 | 0.73 | 0.303 | 0.91 | 0.0007 | 0.45 | 1.73 | 0.622 |
| convoy_escort | b | strafer | 688 | 85.5 | 38.1 | 0.58 | 0.126 | 0.54 | 0.0418 | 0.32 | 2.43 | 0.288 |
| convoy_escort | b | all | 2580 | 168.2 | 77.9 | 0.43 | 0.248 | 0.77 | 0.0177 | 0.28 | 1.86 | 0.412 |
