**policy:ppo_bc_701.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.914

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.863 | 0.878 | 0.849 | 0.002 | 0.002 | 0.000 | 81 | 113 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.965 | 0.988 | 0.942 | 0.000 | 0.000 | 0.000 | 61 | 75 | eliminated 0.07, convoy_through 0.46, convoy_destroyed 0.48 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 86.0 | 71.7 | 0.07 | 0.440 | 0.86 | 0.0090 | 0.19 | 1.77 | 0.692 |
| carrier_battle | a | gunship | 860 | 512.0 | 126.9 | 0.67 | 0.320 | 0.84 | 0.0020 | 0.56 | 2.43 | 0.740 |
| carrier_battle | a | strafer | 1032 | 162.0 | 85.5 | 0.08 | 0.247 | 0.73 | 0.0160 | 0.28 | 2.10 | 0.628 |
| carrier_battle | a | all | 3956 | 198.4 | 87.3 | 0.21 | 0.312 | 0.82 | 0.0085 | 0.33 | 2.00 | 0.691 |
| carrier_battle | b | fighter | 2064 | 38.6 | 42.2 | 0.02 | 0.240 | 0.83 | 0.0195 | 0.17 | 1.88 | 0.355 |
| carrier_battle | b | gunship | 860 | 201.8 | 91.5 | 0.39 | 0.162 | 0.88 | 0.0050 | 0.48 | 2.77 | 0.516 |
| carrier_battle | b | strafer | 1032 | 58.5 | 111.7 | 0.07 | 0.231 | 0.63 | 0.0364 | 0.29 | 2.18 | 0.367 |
| carrier_battle | b | all | 3956 | 79.3 | 71.1 | 0.11 | 0.199 | 0.80 | 0.0185 | 0.31 | 2.15 | 0.414 |
| convoy_escort | a | fighter | 1290 | 185.8 | 98.2 | 0.28 | 0.499 | 0.88 | 0.0025 | 0.23 | 1.18 | 0.896 |
| convoy_escort | a | gunship | 516 | 493.0 | 138.9 | 0.86 | 0.219 | 0.77 | 0.0010 | 0.53 | 1.92 | 0.836 |
| convoy_escort | a | strafer | 774 | 297.0 | 54.5 | 0.50 | 0.215 | 0.85 | 0.0038 | 0.18 | 1.72 | 0.832 |
| convoy_escort | a | all | 2580 | 280.6 | 93.2 | 0.46 | 0.262 | 0.84 | 0.0024 | 0.30 | 1.49 | 0.860 |
| convoy_escort | b | fighter | 1290 | 89.1 | 97.5 | 0.15 | 0.365 | 0.84 | 0.0147 | 0.16 | 1.77 | 0.378 |
| convoy_escort | b | gunship | 516 | 267.6 | 140.1 | 0.49 | 0.247 | 0.88 | 0.0031 | 0.43 | 1.50 | 0.590 |
| convoy_escort | b | strafer | 774 | 56.5 | 58.3 | 0.65 | 0.124 | 0.43 | 0.0583 | 0.38 | 2.56 | 0.214 |
| convoy_escort | b | all | 2580 | 115.0 | 94.3 | 0.37 | 0.224 | 0.69 | 0.0290 | 0.30 | 1.95 | 0.358 |
