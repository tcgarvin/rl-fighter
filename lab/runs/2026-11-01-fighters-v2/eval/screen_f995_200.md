**policy:ppo_bc_200.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.698

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.721 | 0.721 | 0.721 | 0.000 | 0.004 | 0.000 | 93 | 119 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.674 | 0.829 | 0.519 | 0.000 | 0.000 | 0.000 | 50 | 74 | eliminated 0.56, convoy_through 0.09, convoy_destroyed 0.34 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 62.5 | 44.6 | 0.04 | 0.318 | 0.86 | 0.0042 | 0.24 | 1.64 | 0.634 |
| carrier_battle | a | gunship | 430 | 528.9 | 187.4 | 0.57 | 0.334 | 0.80 | 0.0013 | 0.55 | 2.18 | 0.807 |
| carrier_battle | a | strafer | 516 | 113.9 | 70.9 | 0.04 | 0.205 | 0.72 | 0.0117 | 0.26 | 1.84 | 0.626 |
| carrier_battle | a | all | 1978 | 177.3 | 82.5 | 0.16 | 0.286 | 0.81 | 0.0049 | 0.35 | 1.81 | 0.691 |
| carrier_battle | b | fighter | 1032 | 47.2 | 33.7 | 0.03 | 0.196 | 0.84 | 0.0027 | 0.25 | 1.97 | 0.654 |
| carrier_battle | b | gunship | 430 | 316.6 | 132.6 | 0.58 | 0.185 | 0.82 | 0.0020 | 0.45 | 3.00 | 0.741 |
| carrier_battle | b | strafer | 516 | 61.2 | 66.6 | 0.01 | 0.152 | 0.71 | 0.0012 | 0.19 | 2.06 | 0.642 |
| carrier_battle | b | all | 1978 | 109.4 | 63.8 | 0.14 | 0.177 | 0.81 | 0.0022 | 0.31 | 2.22 | 0.684 |
| convoy_escort | a | fighter | 774 | 119.9 | 77.7 | 0.16 | 0.393 | 0.87 | 0.0005 | 0.27 | 1.17 | 0.767 |
| convoy_escort | a | gunship | 258 | 470.4 | 168.1 | 0.62 | 0.269 | 0.84 | 0.0003 | 0.40 | 1.42 | 0.935 |
| convoy_escort | a | strafer | 516 | 225.3 | 65.4 | 0.43 | 0.170 | 0.84 | 0.0006 | 0.24 | 2.20 | 0.735 |
| convoy_escort | a | all | 1548 | 213.4 | 88.6 | 0.33 | 0.232 | 0.85 | 0.0005 | 0.29 | 1.55 | 0.791 |
| convoy_escort | b | fighter | 774 | 120.0 | 85.6 | 0.09 | 0.376 | 0.85 | 0.0003 | 0.25 | 1.19 | 0.763 |
| convoy_escort | b | gunship | 258 | 261.7 | 84.9 | 0.31 | 0.198 | 0.84 | 0.0006 | 0.39 | 1.20 | 0.837 |
| convoy_escort | b | strafer | 516 | 189.5 | 85.5 | 0.16 | 0.192 | 0.85 | 0.0002 | 0.16 | 1.59 | 0.785 |
| convoy_escort | b | all | 1548 | 166.8 | 85.5 | 0.15 | 0.229 | 0.85 | 0.0003 | 0.25 | 1.32 | 0.785 |
