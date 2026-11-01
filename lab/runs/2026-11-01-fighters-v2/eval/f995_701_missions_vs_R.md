**policy:ppo_bc_701.pt** vs **policy:ppo_bc_300.pt** (scripted commanders): mean win 0.714

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 1032 | 0.771 | 0.761 | 0.781 | 0.001 | 0.001 | 0.000 | 82 | 110 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 1032 | 0.658 | 0.787 | 0.529 | 0.000 | 0.000 | 0.000 | 48 | 71 | eliminated 0.56, convoy_through 0.07, convoy_destroyed 0.37 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 4128 | 65.2 | 58.1 | 0.06 | 0.392 | 0.87 | 0.0057 | 0.19 | 1.56 | 0.696 |
| carrier_battle | a | gunship | 1720 | 536.3 | 152.7 | 0.66 | 0.390 | 0.82 | 0.0010 | 0.57 | 1.90 | 0.755 |
| carrier_battle | a | strafer | 2064 | 125.3 | 76.5 | 0.04 | 0.238 | 0.74 | 0.0104 | 0.27 | 1.84 | 0.652 |
| carrier_battle | a | all | 7912 | 183.3 | 83.5 | 0.19 | 0.333 | 0.82 | 0.0053 | 0.33 | 1.71 | 0.704 |
| carrier_battle | b | fighter | 4128 | 44.2 | 32.8 | 0.02 | 0.186 | 0.83 | 0.0035 | 0.26 | 1.96 | 0.659 |
| carrier_battle | b | gunship | 1720 | 275.6 | 108.0 | 0.61 | 0.154 | 0.82 | 0.0037 | 0.45 | 3.04 | 0.758 |
| carrier_battle | b | strafer | 2064 | 55.7 | 78.1 | 0.02 | 0.147 | 0.71 | 0.0019 | 0.20 | 2.21 | 0.638 |
| carrier_battle | b | all | 7912 | 97.5 | 61.0 | 0.15 | 0.158 | 0.80 | 0.0032 | 0.31 | 2.26 | 0.692 |
| convoy_escort | a | fighter | 3096 | 108.1 | 67.9 | 0.13 | 0.383 | 0.84 | 0.0009 | 0.26 | 1.23 | 0.876 |
| convoy_escort | a | gunship | 1032 | 506.7 | 197.2 | 0.60 | 0.287 | 0.84 | 0.0001 | 0.48 | 1.29 | 0.909 |
| convoy_escort | a | strafer | 2064 | 222.8 | 52.7 | 0.35 | 0.173 | 0.83 | 0.0007 | 0.20 | 1.86 | 0.819 |
| convoy_escort | a | all | 6192 | 212.8 | 84.4 | 0.28 | 0.237 | 0.84 | 0.0006 | 0.29 | 1.45 | 0.863 |
| convoy_escort | b | fighter | 3096 | 120.4 | 80.0 | 0.07 | 0.418 | 0.87 | 0.0004 | 0.24 | 1.11 | 0.762 |
| convoy_escort | b | gunship | 1032 | 224.8 | 72.2 | 0.35 | 0.188 | 0.85 | 0.0005 | 0.39 | 1.25 | 0.828 |
| convoy_escort | b | strafer | 2064 | 231.2 | 98.6 | 0.22 | 0.225 | 0.86 | 0.0002 | 0.15 | 1.65 | 0.792 |
| convoy_escort | b | all | 6192 | 174.7 | 84.9 | 0.17 | 0.250 | 0.86 | 0.0003 | 0.24 | 1.31 | 0.786 |
