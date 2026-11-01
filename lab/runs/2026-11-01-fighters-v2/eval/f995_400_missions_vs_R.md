**policy:ppo_bc_400.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.698

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 1032 | 0.752 | 0.760 | 0.744 | 0.000 | 0.001 | 0.000 | 85 | 114 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 1032 | 0.644 | 0.767 | 0.521 | 0.000 | 0.000 | 0.000 | 47 | 70 | eliminated 0.56, convoy_through 0.06, convoy_destroyed 0.38 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 4128 | 61.0 | 46.6 | 0.06 | 0.326 | 0.85 | 0.0054 | 0.19 | 1.64 | 0.622 |
| carrier_battle | a | gunship | 1720 | 541.5 | 165.1 | 0.62 | 0.381 | 0.80 | 0.0012 | 0.53 | 1.92 | 0.742 |
| carrier_battle | a | strafer | 2064 | 120.0 | 80.1 | 0.04 | 0.225 | 0.68 | 0.0091 | 0.26 | 1.85 | 0.618 |
| carrier_battle | a | all | 7912 | 180.9 | 81.1 | 0.17 | 0.312 | 0.80 | 0.0050 | 0.32 | 1.76 | 0.659 |
| carrier_battle | b | fighter | 4128 | 48.1 | 31.2 | 0.04 | 0.203 | 0.84 | 0.0032 | 0.25 | 1.84 | 0.666 |
| carrier_battle | b | gunship | 1720 | 308.5 | 125.2 | 0.62 | 0.184 | 0.83 | 0.0034 | 0.45 | 2.92 | 0.743 |
| carrier_battle | b | strafer | 2064 | 56.4 | 73.4 | 0.02 | 0.166 | 0.73 | 0.0017 | 0.19 | 1.96 | 0.656 |
| carrier_battle | b | all | 7912 | 106.9 | 62.7 | 0.16 | 0.182 | 0.82 | 0.0030 | 0.32 | 2.10 | 0.693 |
| convoy_escort | a | fighter | 3096 | 115.8 | 77.3 | 0.11 | 0.425 | 0.86 | 0.0002 | 0.25 | 1.12 | 0.785 |
| convoy_escort | a | gunship | 1032 | 478.0 | 164.9 | 0.64 | 0.264 | 0.84 | 0.0000 | 0.43 | 1.34 | 0.896 |
| convoy_escort | a | strafer | 2064 | 233.7 | 54.7 | 0.39 | 0.176 | 0.84 | 0.0002 | 0.19 | 2.01 | 0.743 |
| convoy_escort | a | all | 6192 | 215.5 | 84.4 | 0.29 | 0.237 | 0.85 | 0.0002 | 0.27 | 1.46 | 0.794 |
| convoy_escort | b | fighter | 3096 | 114.8 | 77.4 | 0.09 | 0.393 | 0.87 | 0.0003 | 0.24 | 1.11 | 0.758 |
| convoy_escort | b | gunship | 1032 | 281.8 | 92.3 | 0.41 | 0.209 | 0.85 | 0.0002 | 0.39 | 1.26 | 0.835 |
| convoy_escort | b | strafer | 2064 | 199.8 | 86.3 | 0.21 | 0.201 | 0.85 | 0.0001 | 0.15 | 1.59 | 0.783 |
| convoy_escort | b | all | 6192 | 171.0 | 82.8 | 0.18 | 0.237 | 0.86 | 0.0002 | 0.24 | 1.29 | 0.783 |
