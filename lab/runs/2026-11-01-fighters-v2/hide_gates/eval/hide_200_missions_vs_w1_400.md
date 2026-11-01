**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.382

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.291 | 0.318 | 0.264 | 0.000 | 0.004 | 0.000 | 104 | 126 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.473 | 0.767 | 0.178 | 0.000 | 0.000 | 0.000 | 63 | 75 | eliminated 0.43, convoy_through 0.36, convoy_destroyed 0.21 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 51.4 | 47.5 | 0.02 | 0.317 | 0.83 | 0.0044 | 0.12 | 1.60 | 0.620 |
| carrier_battle | a | gunship | 430 | 300.3 | 140.1 | 0.26 | 0.267 | 0.85 | 0.0004 | 0.41 | 2.18 | 0.663 |
| carrier_battle | a | strafer | 516 | 104.8 | 69.0 | 0.03 | 0.193 | 0.70 | 0.0076 | 0.23 | 1.95 | 0.624 |
| carrier_battle | a | all | 1978 | 119.4 | 73.2 | 0.07 | 0.246 | 0.80 | 0.0039 | 0.24 | 1.82 | 0.636 |
| carrier_battle | b | fighter | 1032 | 70.5 | 36.7 | 0.04 | 0.251 | 0.81 | 0.0020 | 0.19 | 1.97 | 0.570 |
| carrier_battle | b | gunship | 430 | 488.1 | 184.0 | 0.53 | 0.267 | 0.84 | 0.0016 | 0.48 | 2.80 | 0.723 |
| carrier_battle | b | strafer | 516 | 106.9 | 100.8 | 0.03 | 0.197 | 0.73 | 0.0022 | 0.20 | 2.39 | 0.645 |
| carrier_battle | b | all | 1978 | 170.8 | 85.5 | 0.15 | 0.240 | 0.80 | 0.0019 | 0.30 | 2.26 | 0.641 |
| convoy_escort | a | fighter | 774 | 78.4 | 48.1 | 0.04 | 0.245 | 0.78 | 0.0018 | 0.17 | 1.41 | 0.693 |
| convoy_escort | a | gunship | 258 | 291.8 | 161.1 | 0.33 | 0.217 | 0.78 | 0.0001 | 0.39 | 1.47 | 0.761 |
| convoy_escort | a | strafer | 516 | 170.3 | 88.5 | 0.13 | 0.221 | 0.74 | 0.0027 | 0.23 | 2.05 | 0.589 |
| convoy_escort | a | all | 1548 | 144.6 | 80.4 | 0.12 | 0.225 | 0.77 | 0.0017 | 0.24 | 1.64 | 0.675 |
| convoy_escort | b | fighter | 774 | 77.2 | 47.6 | 0.16 | 0.264 | 0.76 | 0.0009 | 0.20 | 1.20 | 0.610 |
| convoy_escort | b | gunship | 258 | 359.6 | 159.0 | 0.63 | 0.231 | 0.77 | 0.0006 | 0.45 | 1.55 | 0.740 |
| convoy_escort | b | strafer | 516 | 246.2 | 143.5 | 0.55 | 0.193 | 0.83 | 0.0015 | 0.23 | 3.15 | 0.627 |
| convoy_escort | b | all | 1548 | 180.6 | 98.1 | 0.37 | 0.212 | 0.79 | 0.0011 | 0.26 | 1.91 | 0.644 |
