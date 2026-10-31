**policy:ppo_bc_400.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.499

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.496 | 0.504 | 0.488 | 0.000 | 0.019 | 0.000 | 115 | 139 | time_limit 0.02, carrier_destroyed 0.98 |
| convoy_escort | 516 | 0.502 | 0.450 | 0.554 | 0.000 | 0.000 | 0.000 | 68 | 72 | eliminated 0.01, convoy_through 0.44, convoy_destroyed 0.55 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 55.1 | 45.5 | 0.03 | 0.286 | 0.81 | 0.0129 | 0.17 | 1.87 | 0.369 |
| carrier_battle | a | gunship | 860 | 367.0 | 160.5 | 0.30 | 0.265 | 0.86 | 0.0020 | 0.50 | 2.82 | 0.518 |
| carrier_battle | a | strafer | 1032 | 94.4 | 99.5 | 0.05 | 0.210 | 0.68 | 0.0288 | 0.27 | 2.50 | 0.446 |
| carrier_battle | a | all | 3956 | 133.1 | 84.6 | 0.09 | 0.248 | 0.80 | 0.0129 | 0.31 | 2.24 | 0.440 |
| carrier_battle | b | fighter | 2064 | 54.7 | 45.4 | 0.03 | 0.281 | 0.81 | 0.0110 | 0.17 | 1.87 | 0.368 |
| carrier_battle | b | gunship | 860 | 377.9 | 165.4 | 0.32 | 0.267 | 0.85 | 0.0016 | 0.50 | 2.88 | 0.515 |
| carrier_battle | b | strafer | 1032 | 93.0 | 95.2 | 0.05 | 0.205 | 0.69 | 0.0224 | 0.27 | 2.50 | 0.462 |
| carrier_battle | b | all | 3956 | 135.0 | 84.5 | 0.10 | 0.247 | 0.80 | 0.0103 | 0.31 | 2.26 | 0.443 |
| convoy_escort | a | fighter | 1462 | 152.9 | 69.0 | 0.33 | 0.354 | 0.86 | 0.0114 | 0.18 | 1.84 | 0.399 |
| convoy_escort | a | gunship | 430 | 415.7 | 170.2 | 0.70 | 0.251 | 0.90 | 0.0013 | 0.44 | 2.00 | 0.599 |
| convoy_escort | a | strafer | 688 | 84.0 | 43.4 | 0.62 | 0.125 | 0.50 | 0.0461 | 0.33 | 2.49 | 0.276 |
| convoy_escort | a | all | 2580 | 178.4 | 79.0 | 0.47 | 0.235 | 0.77 | 0.0189 | 0.27 | 2.04 | 0.406 |
| convoy_escort | b | fighter | 1462 | 157.7 | 65.7 | 0.33 | 0.353 | 0.86 | 0.0117 | 0.18 | 1.89 | 0.403 |
| convoy_escort | b | gunship | 430 | 408.9 | 186.1 | 0.72 | 0.249 | 0.90 | 0.0011 | 0.44 | 2.05 | 0.599 |
| convoy_escort | b | strafer | 688 | 77.8 | 38.5 | 0.63 | 0.117 | 0.49 | 0.0419 | 0.32 | 2.50 | 0.266 |
| convoy_escort | b | all | 2580 | 178.3 | 78.5 | 0.48 | 0.233 | 0.76 | 0.0178 | 0.27 | 2.07 | 0.406 |
