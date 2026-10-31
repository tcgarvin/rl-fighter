**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.257

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.014 | 0.019 | 0.008 | 0.000 | 0.002 | 0.000 | 87 | 106 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.500 | 0.225 | 0.775 | 0.000 | 0.000 | 0.000 | 50 | 71 | eliminated 0.11, convoy_through 0.12, convoy_destroyed 0.78 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 8.2 | 24.0 | 0.00 | 0.127 | 0.87 | 0.0008 | 0.27 | 1.59 | 0.346 |
| carrier_battle | a | gunship | 860 | 109.2 | 115.2 | 0.13 | 0.182 | 0.95 | 0.0008 | 0.45 | 1.93 | 0.636 |
| carrier_battle | a | strafer | 1032 | 9.2 | 21.3 | 0.00 | 0.071 | 0.83 | 0.0013 | 0.32 | 1.54 | 0.435 |
| carrier_battle | a | all | 3956 | 30.4 | 43.1 | 0.03 | 0.138 | 0.89 | 0.0009 | 0.35 | 1.65 | 0.467 |
| carrier_battle | b | fighter | 2064 | 116.3 | 62.6 | 0.24 | 0.320 | 0.72 | 0.0110 | 0.19 | 2.50 | 0.345 |
| carrier_battle | b | gunship | 860 | 490.7 | 122.5 | 0.86 | 0.307 | 0.84 | 0.0008 | 0.50 | 2.20 | 0.566 |
| carrier_battle | b | strafer | 1032 | 144.5 | 101.1 | 0.39 | 0.220 | 0.61 | 0.0288 | 0.29 | 2.96 | 0.373 |
| carrier_battle | b | all | 3956 | 205.0 | 85.7 | 0.42 | 0.277 | 0.72 | 0.0130 | 0.29 | 2.55 | 0.406 |
| convoy_escort | a | fighter | 1462 | 75.9 | 40.4 | 0.16 | 0.315 | 0.92 | 0.0000 | 0.35 | 1.11 | 0.566 |
| convoy_escort | a | gunship | 430 | 502.0 | 117.7 | 0.59 | 0.304 | 0.94 | 0.0001 | 0.45 | 1.17 | 0.818 |
| convoy_escort | a | strafer | 688 | 125.8 | 38.9 | 0.35 | 0.150 | 0.90 | 0.0000 | 0.26 | 1.43 | 0.646 |
| convoy_escort | a | all | 2580 | 160.2 | 52.9 | 0.28 | 0.238 | 0.92 | 0.0000 | 0.35 | 1.21 | 0.654 |
| convoy_escort | b | fighter | 1462 | 188.6 | 64.6 | 0.52 | 0.392 | 0.89 | 0.0057 | 0.19 | 1.65 | 0.419 |
| convoy_escort | b | gunship | 430 | 423.5 | 230.9 | 1.00 | 0.279 | 0.90 | 0.0006 | 0.47 | 1.97 | 0.605 |
| convoy_escort | b | strafer | 688 | 79.5 | 35.7 | 0.88 | 0.109 | 0.51 | 0.0356 | 0.32 | 2.51 | 0.268 |
| convoy_escort | b | all | 2580 | 198.6 | 84.6 | 0.69 | 0.250 | 0.78 | 0.0133 | 0.28 | 1.93 | 0.412 |
