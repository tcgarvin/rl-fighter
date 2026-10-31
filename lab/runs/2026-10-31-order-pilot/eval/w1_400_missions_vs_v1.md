**policy:ppo_bc_400.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.763

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.787 | 0.767 | 0.806 | 0.000 | 0.008 | 0.000 | 103 | 131 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.738 | 0.488 | 0.988 | 0.000 | 0.000 | 0.000 | 50 | 72 | eliminated 0.01, convoy_through 0.24, convoy_destroyed 0.75 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 71.7 | 41.3 | 0.06 | 0.269 | 0.79 | 0.0034 | 0.19 | 1.93 | 0.558 |
| carrier_battle | a | gunship | 860 | 519.1 | 175.3 | 0.57 | 0.281 | 0.83 | 0.0011 | 0.48 | 2.75 | 0.710 |
| carrier_battle | a | strafer | 1032 | 116.3 | 90.7 | 0.04 | 0.194 | 0.73 | 0.0040 | 0.21 | 2.28 | 0.651 |
| carrier_battle | a | all | 3956 | 180.6 | 83.3 | 0.17 | 0.248 | 0.79 | 0.0027 | 0.29 | 2.20 | 0.632 |
| carrier_battle | b | fighter | 2064 | 41.9 | 35.0 | 0.01 | 0.279 | 0.80 | 0.0073 | 0.15 | 1.59 | 0.373 |
| carrier_battle | b | gunship | 860 | 259.3 | 146.7 | 0.22 | 0.260 | 0.86 | 0.0009 | 0.49 | 2.41 | 0.515 |
| carrier_battle | b | strafer | 1032 | 80.5 | 83.6 | 0.04 | 0.203 | 0.70 | 0.0196 | 0.26 | 2.19 | 0.482 |
| carrier_battle | b | all | 3956 | 99.3 | 72.0 | 0.06 | 0.240 | 0.79 | 0.0082 | 0.30 | 1.93 | 0.450 |
| convoy_escort | a | fighter | 1462 | 169.7 | 46.6 | 0.44 | 0.370 | 0.92 | 0.0015 | 0.21 | 1.43 | 0.631 |
| convoy_escort | a | gunship | 430 | 388.2 | 145.6 | 0.82 | 0.235 | 0.91 | 0.0003 | 0.44 | 1.78 | 0.757 |
| convoy_escort | a | strafer | 688 | 154.1 | 47.8 | 0.55 | 0.161 | 0.82 | 0.0016 | 0.21 | 2.32 | 0.595 |
| convoy_escort | a | all | 2580 | 202.0 | 63.4 | 0.53 | 0.239 | 0.89 | 0.0013 | 0.26 | 1.73 | 0.651 |
| convoy_escort | b | fighter | 1462 | 113.9 | 56.1 | 0.24 | 0.341 | 0.86 | 0.0108 | 0.17 | 1.59 | 0.387 |
| convoy_escort | b | gunship | 430 | 490.6 | 214.2 | 0.73 | 0.311 | 0.92 | 0.0006 | 0.44 | 1.69 | 0.627 |
| convoy_escort | b | strafer | 688 | 79.1 | 35.2 | 0.58 | 0.119 | 0.51 | 0.0483 | 0.32 | 2.33 | 0.280 |
| convoy_escort | b | all | 2580 | 167.4 | 76.9 | 0.42 | 0.248 | 0.77 | 0.0196 | 0.28 | 1.80 | 0.409 |
