**policy:ppo_bc_701.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.698

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.756 | 0.767 | 0.744 | 0.000 | 0.004 | 0.000 | 83 | 109 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.640 | 0.744 | 0.535 | 0.000 | 0.000 | 0.000 | 46 | 71 | eliminated 0.53, convoy_through 0.07, convoy_destroyed 0.40 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 62.8 | 58.2 | 0.05 | 0.385 | 0.87 | 0.0068 | 0.19 | 1.56 | 0.690 |
| carrier_battle | a | gunship | 430 | 535.0 | 151.2 | 0.65 | 0.383 | 0.82 | 0.0008 | 0.57 | 1.96 | 0.757 |
| carrier_battle | a | strafer | 516 | 125.1 | 67.5 | 0.05 | 0.232 | 0.72 | 0.0098 | 0.28 | 1.82 | 0.641 |
| carrier_battle | a | all | 1978 | 181.7 | 80.9 | 0.18 | 0.327 | 0.82 | 0.0056 | 0.33 | 1.71 | 0.700 |
| carrier_battle | b | fighter | 1032 | 44.2 | 35.4 | 0.04 | 0.189 | 0.83 | 0.0039 | 0.26 | 1.99 | 0.654 |
| carrier_battle | b | gunship | 430 | 285.8 | 106.9 | 0.61 | 0.163 | 0.82 | 0.0040 | 0.45 | 2.99 | 0.751 |
| carrier_battle | b | strafer | 516 | 55.3 | 71.4 | 0.03 | 0.143 | 0.70 | 0.0012 | 0.20 | 2.12 | 0.631 |
| carrier_battle | b | all | 1978 | 99.6 | 60.3 | 0.16 | 0.162 | 0.80 | 0.0034 | 0.31 | 2.24 | 0.685 |
| convoy_escort | a | fighter | 774 | 111.3 | 72.0 | 0.16 | 0.397 | 0.85 | 0.0006 | 0.25 | 1.21 | 0.881 |
| convoy_escort | a | gunship | 258 | 532.3 | 193.3 | 0.64 | 0.290 | 0.84 | 0.0000 | 0.47 | 1.31 | 0.917 |
| convoy_escort | a | strafer | 516 | 199.9 | 47.9 | 0.35 | 0.163 | 0.82 | 0.0005 | 0.20 | 1.83 | 0.822 |
| convoy_escort | a | all | 1548 | 211.0 | 84.2 | 0.30 | 0.237 | 0.84 | 0.0004 | 0.29 | 1.43 | 0.869 |
| convoy_escort | b | fighter | 774 | 120.0 | 79.0 | 0.09 | 0.420 | 0.87 | 0.0006 | 0.24 | 1.11 | 0.764 |
| convoy_escort | b | gunship | 258 | 254.8 | 72.6 | 0.34 | 0.207 | 0.86 | 0.0005 | 0.39 | 1.23 | 0.833 |
| convoy_escort | b | strafer | 516 | 222.8 | 97.8 | 0.24 | 0.225 | 0.85 | 0.0001 | 0.15 | 1.62 | 0.789 |
| convoy_escort | b | all | 1548 | 176.7 | 84.2 | 0.18 | 0.255 | 0.86 | 0.0004 | 0.24 | 1.30 | 0.786 |
