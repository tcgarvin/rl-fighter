**policy:ppo_bc_200.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.388

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.306 | 0.326 | 0.287 | 0.000 | 0.004 | 0.000 | 100 | 124 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.469 | 0.566 | 0.372 | 0.000 | 0.000 | 0.000 | 54 | 73 | eliminated 0.50, convoy_through 0.10, convoy_destroyed 0.40 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 49.4 | 40.6 | 0.03 | 0.302 | 0.83 | 0.0044 | 0.12 | 1.58 | 0.621 |
| carrier_battle | a | gunship | 430 | 326.5 | 148.7 | 0.27 | 0.289 | 0.86 | 0.0005 | 0.40 | 2.11 | 0.680 |
| carrier_battle | a | strafer | 516 | 94.1 | 71.4 | 0.02 | 0.189 | 0.67 | 0.0081 | 0.24 | 1.86 | 0.613 |
| carrier_battle | a | all | 1978 | 121.3 | 72.1 | 0.08 | 0.251 | 0.80 | 0.0041 | 0.24 | 1.77 | 0.639 |
| carrier_battle | b | fighter | 1032 | 70.0 | 38.0 | 0.04 | 0.251 | 0.83 | 0.0021 | 0.24 | 1.97 | 0.669 |
| carrier_battle | b | gunship | 430 | 495.3 | 169.8 | 0.59 | 0.266 | 0.85 | 0.0023 | 0.46 | 2.69 | 0.765 |
| carrier_battle | b | strafer | 516 | 95.8 | 69.8 | 0.03 | 0.159 | 0.74 | 0.0008 | 0.19 | 2.35 | 0.681 |
| carrier_battle | b | all | 1978 | 169.2 | 74.9 | 0.16 | 0.226 | 0.82 | 0.0019 | 0.31 | 2.23 | 0.706 |
| convoy_escort | a | fighter | 774 | 81.5 | 39.3 | 0.11 | 0.265 | 0.83 | 0.0004 | 0.15 | 1.30 | 0.720 |
| convoy_escort | a | gunship | 258 | 459.0 | 205.3 | 0.47 | 0.312 | 0.87 | 0.0000 | 0.38 | 1.28 | 0.806 |
| convoy_escort | a | strafer | 516 | 195.6 | 92.0 | 0.22 | 0.240 | 0.84 | 0.0008 | 0.22 | 1.93 | 0.647 |
| convoy_escort | a | all | 1548 | 182.5 | 84.6 | 0.20 | 0.268 | 0.84 | 0.0005 | 0.23 | 1.50 | 0.716 |
| convoy_escort | b | fighter | 774 | 88.5 | 60.6 | 0.10 | 0.320 | 0.82 | 0.0001 | 0.24 | 1.14 | 0.748 |
| convoy_escort | b | gunship | 258 | 481.3 | 174.0 | 0.62 | 0.258 | 0.80 | 0.0002 | 0.40 | 1.59 | 0.825 |
| convoy_escort | b | strafer | 516 | 220.8 | 87.3 | 0.28 | 0.191 | 0.82 | 0.0003 | 0.16 | 1.58 | 0.784 |
| convoy_escort | b | all | 1548 | 198.1 | 88.4 | 0.24 | 0.231 | 0.82 | 0.0002 | 0.25 | 1.36 | 0.780 |
