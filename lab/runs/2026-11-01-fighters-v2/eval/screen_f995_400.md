**policy:ppo_bc_400.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.702

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.736 | 0.736 | 0.736 | 0.000 | 0.000 | 0.000 | 87 | 113 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.667 | 0.798 | 0.535 | 0.000 | 0.000 | 0.000 | 46 | 71 | eliminated 0.57, convoy_through 0.07, convoy_destroyed 0.37 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 60.6 | 45.5 | 0.05 | 0.327 | 0.85 | 0.0048 | 0.19 | 1.62 | 0.625 |
| carrier_battle | a | gunship | 430 | 547.6 | 169.7 | 0.62 | 0.377 | 0.81 | 0.0013 | 0.53 | 1.97 | 0.744 |
| carrier_battle | a | strafer | 516 | 121.4 | 74.3 | 0.05 | 0.216 | 0.69 | 0.0095 | 0.26 | 1.89 | 0.630 |
| carrier_battle | a | all | 1978 | 182.3 | 80.0 | 0.17 | 0.307 | 0.80 | 0.0048 | 0.32 | 1.76 | 0.665 |
| carrier_battle | b | fighter | 1032 | 50.2 | 32.5 | 0.03 | 0.203 | 0.84 | 0.0052 | 0.25 | 1.89 | 0.666 |
| carrier_battle | b | gunship | 430 | 311.4 | 124.0 | 0.63 | 0.179 | 0.82 | 0.0034 | 0.46 | 2.94 | 0.743 |
| carrier_battle | b | strafer | 516 | 56.8 | 70.4 | 0.03 | 0.156 | 0.72 | 0.0017 | 0.19 | 2.01 | 0.652 |
| carrier_battle | b | all | 1978 | 108.7 | 62.3 | 0.16 | 0.177 | 0.81 | 0.0039 | 0.32 | 2.15 | 0.692 |
| convoy_escort | a | fighter | 774 | 116.6 | 75.6 | 0.12 | 0.431 | 0.86 | 0.0003 | 0.24 | 1.12 | 0.788 |
| convoy_escort | a | gunship | 258 | 460.9 | 167.0 | 0.63 | 0.265 | 0.83 | 0.0000 | 0.43 | 1.31 | 0.893 |
| convoy_escort | a | strafer | 516 | 234.0 | 54.2 | 0.40 | 0.175 | 0.84 | 0.0002 | 0.19 | 2.01 | 0.744 |
| convoy_escort | a | all | 1548 | 213.1 | 83.7 | 0.30 | 0.237 | 0.84 | 0.0002 | 0.27 | 1.45 | 0.795 |
| convoy_escort | b | fighter | 774 | 110.4 | 76.1 | 0.10 | 0.393 | 0.87 | 0.0001 | 0.24 | 1.12 | 0.759 |
| convoy_escort | b | gunship | 258 | 306.3 | 105.5 | 0.42 | 0.223 | 0.87 | 0.0002 | 0.40 | 1.23 | 0.837 |
| convoy_escort | b | strafer | 516 | 192.5 | 83.8 | 0.20 | 0.200 | 0.86 | 0.0000 | 0.15 | 1.53 | 0.790 |
| convoy_escort | b | all | 1548 | 170.4 | 83.5 | 0.19 | 0.240 | 0.87 | 0.0001 | 0.25 | 1.27 | 0.786 |
