**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.681

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.709 | 0.678 | 0.740 | 0.000 | 0.012 | 0.000 | 109 | 131 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.653 | 0.500 | 0.806 | 0.000 | 0.000 | 0.000 | 63 | 72 | eliminated 0.01, convoy_through 0.34, convoy_destroyed 0.65 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 68.1 | 46.5 | 0.04 | 0.299 | 0.80 | 0.0063 | 0.15 | 1.85 | 0.475 |
| carrier_battle | a | gunship | 860 | 461.1 | 171.8 | 0.50 | 0.272 | 0.84 | 0.0016 | 0.48 | 2.95 | 0.604 |
| carrier_battle | a | strafer | 1032 | 116.0 | 110.6 | 0.05 | 0.217 | 0.71 | 0.0133 | 0.25 | 2.46 | 0.555 |
| carrier_battle | a | all | 3956 | 166.0 | 90.5 | 0.14 | 0.257 | 0.79 | 0.0062 | 0.29 | 2.25 | 0.540 |
| carrier_battle | b | fighter | 2064 | 47.2 | 42.0 | 0.02 | 0.285 | 0.81 | 0.0098 | 0.16 | 1.76 | 0.372 |
| carrier_battle | b | gunship | 860 | 300.0 | 148.3 | 0.29 | 0.250 | 0.85 | 0.0021 | 0.50 | 2.79 | 0.507 |
| carrier_battle | b | strafer | 1032 | 81.7 | 97.2 | 0.03 | 0.211 | 0.68 | 0.0189 | 0.27 | 2.38 | 0.456 |
| carrier_battle | b | all | 3956 | 111.2 | 79.5 | 0.08 | 0.241 | 0.79 | 0.0092 | 0.31 | 2.15 | 0.441 |
| convoy_escort | a | fighter | 1462 | 184.6 | 62.8 | 0.40 | 0.373 | 0.89 | 0.0047 | 0.17 | 1.75 | 0.518 |
| convoy_escort | a | gunship | 430 | 348.3 | 155.6 | 0.72 | 0.220 | 0.89 | 0.0024 | 0.44 | 2.22 | 0.645 |
| convoy_escort | a | strafer | 688 | 125.5 | 45.1 | 0.59 | 0.139 | 0.63 | 0.0156 | 0.29 | 2.62 | 0.391 |
| convoy_escort | a | all | 2580 | 196.1 | 73.5 | 0.50 | 0.230 | 0.82 | 0.0071 | 0.26 | 2.06 | 0.512 |
| convoy_escort | b | fighter | 1462 | 140.3 | 61.9 | 0.31 | 0.342 | 0.86 | 0.0117 | 0.17 | 1.82 | 0.399 |
| convoy_escort | b | gunship | 430 | 429.1 | 199.3 | 0.67 | 0.274 | 0.90 | 0.0020 | 0.44 | 1.99 | 0.605 |
| convoy_escort | b | strafer | 688 | 77.5 | 42.0 | 0.57 | 0.120 | 0.52 | 0.0440 | 0.32 | 2.52 | 0.278 |
| convoy_escort | b | all | 2580 | 171.7 | 79.5 | 0.44 | 0.237 | 0.77 | 0.0187 | 0.27 | 2.04 | 0.408 |
