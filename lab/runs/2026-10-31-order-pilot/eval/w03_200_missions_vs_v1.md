**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.703

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.713 | 0.733 | 0.694 | 0.000 | 0.016 | 0.000 | 110 | 136 | time_limit 0.02, carrier_destroyed 0.98 |
| convoy_escort | 516 | 0.692 | 0.492 | 0.891 | 0.000 | 0.000 | 0.000 | 58 | 72 | eliminated 0.01, convoy_through 0.29, convoy_destroyed 0.70 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 68.1 | 50.6 | 0.04 | 0.322 | 0.82 | 0.0066 | 0.17 | 1.87 | 0.444 |
| carrier_battle | a | gunship | 860 | 471.3 | 169.4 | 0.43 | 0.306 | 0.84 | 0.0005 | 0.47 | 2.64 | 0.569 |
| carrier_battle | a | strafer | 1032 | 119.0 | 94.2 | 0.05 | 0.224 | 0.72 | 0.0108 | 0.23 | 2.36 | 0.530 |
| carrier_battle | a | all | 3956 | 169.0 | 87.8 | 0.13 | 0.278 | 0.81 | 0.0054 | 0.29 | 2.16 | 0.508 |
| carrier_battle | b | fighter | 2064 | 48.7 | 41.9 | 0.02 | 0.282 | 0.80 | 0.0082 | 0.16 | 1.75 | 0.371 |
| carrier_battle | b | gunship | 860 | 284.3 | 151.7 | 0.23 | 0.247 | 0.84 | 0.0020 | 0.49 | 2.62 | 0.509 |
| carrier_battle | b | strafer | 1032 | 83.1 | 93.0 | 0.03 | 0.203 | 0.69 | 0.0200 | 0.27 | 2.43 | 0.454 |
| carrier_battle | b | all | 3956 | 108.9 | 79.1 | 0.07 | 0.236 | 0.79 | 0.0090 | 0.30 | 2.12 | 0.440 |
| convoy_escort | a | fighter | 1462 | 181.4 | 59.5 | 0.42 | 0.383 | 0.89 | 0.0037 | 0.17 | 1.65 | 0.484 |
| convoy_escort | a | gunship | 430 | 403.9 | 159.0 | 0.75 | 0.253 | 0.90 | 0.0012 | 0.41 | 1.87 | 0.649 |
| convoy_escort | a | strafer | 688 | 121.0 | 40.5 | 0.61 | 0.151 | 0.64 | 0.0107 | 0.25 | 2.62 | 0.362 |
| convoy_escort | a | all | 2580 | 202.4 | 71.0 | 0.53 | 0.252 | 0.83 | 0.0050 | 0.24 | 1.95 | 0.487 |
| convoy_escort | b | fighter | 1462 | 132.7 | 67.7 | 0.30 | 0.351 | 0.84 | 0.0122 | 0.17 | 1.81 | 0.388 |
| convoy_escort | b | gunship | 430 | 417.6 | 171.3 | 0.61 | 0.278 | 0.90 | 0.0017 | 0.44 | 1.69 | 0.613 |
| convoy_escort | b | strafer | 688 | 76.8 | 38.8 | 0.60 | 0.120 | 0.49 | 0.0474 | 0.33 | 2.37 | 0.269 |
| convoy_escort | b | all | 2580 | 165.3 | 77.3 | 0.43 | 0.240 | 0.75 | 0.0202 | 0.27 | 1.94 | 0.398 |
