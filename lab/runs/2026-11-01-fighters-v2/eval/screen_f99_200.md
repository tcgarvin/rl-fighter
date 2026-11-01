**policy:ppo_bc_200.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.595

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.616 | 0.612 | 0.620 | 0.000 | 0.000 | 0.000 | 94 | 117 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.574 | 0.605 | 0.543 | 0.000 | 0.000 | 0.000 | 53 | 75 | eliminated 0.41, convoy_through 0.12, convoy_destroyed 0.47 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 59.4 | 40.0 | 0.05 | 0.337 | 0.85 | 0.0025 | 0.16 | 1.46 | 0.680 |
| carrier_battle | a | gunship | 430 | 472.3 | 180.7 | 0.58 | 0.329 | 0.79 | 0.0011 | 0.43 | 2.30 | 0.719 |
| carrier_battle | a | strafer | 516 | 126.6 | 87.9 | 0.05 | 0.222 | 0.70 | 0.0087 | 0.25 | 2.09 | 0.638 |
| carrier_battle | a | all | 1978 | 166.7 | 83.1 | 0.17 | 0.289 | 0.79 | 0.0036 | 0.28 | 1.81 | 0.683 |
| carrier_battle | b | fighter | 1032 | 50.3 | 32.7 | 0.05 | 0.226 | 0.82 | 0.0022 | 0.23 | 1.84 | 0.657 |
| carrier_battle | b | gunship | 430 | 364.8 | 143.3 | 0.55 | 0.218 | 0.82 | 0.0015 | 0.46 | 2.77 | 0.729 |
| carrier_battle | b | strafer | 516 | 87.4 | 77.9 | 0.02 | 0.173 | 0.72 | 0.0008 | 0.19 | 2.20 | 0.666 |
| carrier_battle | b | all | 1978 | 128.3 | 68.5 | 0.15 | 0.204 | 0.80 | 0.0016 | 0.31 | 2.14 | 0.686 |
| convoy_escort | a | fighter | 774 | 126.4 | 65.3 | 0.19 | 0.339 | 0.84 | 0.0003 | 0.17 | 1.21 | 0.838 |
| convoy_escort | a | gunship | 258 | 396.0 | 182.8 | 0.64 | 0.242 | 0.84 | 0.0004 | 0.38 | 1.72 | 0.870 |
| convoy_escort | a | strafer | 516 | 239.5 | 78.0 | 0.36 | 0.193 | 0.83 | 0.0003 | 0.21 | 2.09 | 0.785 |
| convoy_escort | a | all | 1548 | 209.0 | 89.1 | 0.32 | 0.232 | 0.84 | 0.0003 | 0.23 | 1.59 | 0.827 |
| convoy_escort | b | fighter | 774 | 132.5 | 79.6 | 0.07 | 0.422 | 0.86 | 0.0002 | 0.24 | 1.15 | 0.763 |
| convoy_escort | b | gunship | 258 | 296.0 | 88.0 | 0.38 | 0.208 | 0.83 | 0.0004 | 0.40 | 1.45 | 0.828 |
| convoy_escort | b | strafer | 516 | 244.8 | 90.6 | 0.21 | 0.219 | 0.83 | 0.0001 | 0.15 | 1.64 | 0.785 |
| convoy_escort | b | all | 1548 | 197.2 | 84.7 | 0.17 | 0.250 | 0.84 | 0.0002 | 0.24 | 1.36 | 0.784 |
