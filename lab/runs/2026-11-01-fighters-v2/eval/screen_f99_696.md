**policy:ppo_bc_696.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.657

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.663 | 0.682 | 0.643 | 0.000 | 0.000 | 0.000 | 86 | 111 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.651 | 0.822 | 0.481 | 0.000 | 0.000 | 0.000 | 46 | 68 | eliminated 0.64, convoy_through 0.03, convoy_destroyed 0.33 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 71.8 | 54.9 | 0.05 | 0.383 | 0.84 | 0.0061 | 0.14 | 1.79 | 0.630 |
| carrier_battle | a | gunship | 430 | 471.8 | 141.4 | 0.59 | 0.403 | 0.76 | 0.0062 | 0.44 | 2.01 | 0.611 |
| carrier_battle | a | strafer | 516 | 117.0 | 91.8 | 0.05 | 0.268 | 0.70 | 0.0119 | 0.39 | 1.84 | 0.549 |
| carrier_battle | a | all | 1978 | 170.6 | 83.4 | 0.17 | 0.347 | 0.78 | 0.0075 | 0.29 | 1.85 | 0.605 |
| carrier_battle | b | fighter | 1032 | 50.1 | 34.4 | 0.04 | 0.210 | 0.85 | 0.0035 | 0.25 | 1.91 | 0.669 |
| carrier_battle | b | gunship | 430 | 324.1 | 117.2 | 0.61 | 0.178 | 0.83 | 0.0037 | 0.44 | 2.93 | 0.758 |
| carrier_battle | b | strafer | 516 | 56.2 | 76.2 | 0.02 | 0.158 | 0.70 | 0.0026 | 0.20 | 1.96 | 0.643 |
| carrier_battle | b | all | 1978 | 111.2 | 63.3 | 0.16 | 0.178 | 0.82 | 0.0034 | 0.31 | 2.14 | 0.698 |
| convoy_escort | a | fighter | 774 | 119.6 | 66.7 | 0.19 | 0.368 | 0.81 | 0.0004 | 0.13 | 1.12 | 0.851 |
| convoy_escort | a | gunship | 258 | 468.9 | 181.2 | 0.65 | 0.285 | 0.79 | 0.0000 | 0.49 | 1.33 | 0.826 |
| convoy_escort | a | strafer | 516 | 219.8 | 63.9 | 0.35 | 0.198 | 0.83 | 0.0005 | 0.26 | 1.76 | 0.787 |
| convoy_escort | a | all | 1548 | 211.2 | 84.9 | 0.32 | 0.253 | 0.81 | 0.0003 | 0.26 | 1.37 | 0.824 |
| convoy_escort | b | fighter | 774 | 132.1 | 75.6 | 0.08 | 0.423 | 0.88 | 0.0001 | 0.24 | 1.14 | 0.767 |
| convoy_escort | b | gunship | 258 | 230.7 | 77.6 | 0.32 | 0.202 | 0.84 | 0.0004 | 0.38 | 1.23 | 0.829 |
| convoy_escort | b | strafer | 516 | 193.4 | 91.6 | 0.20 | 0.205 | 0.84 | 0.0001 | 0.15 | 1.63 | 0.780 |
| convoy_escort | b | all | 1548 | 169.0 | 81.2 | 0.16 | 0.244 | 0.86 | 0.0002 | 0.24 | 1.32 | 0.783 |
