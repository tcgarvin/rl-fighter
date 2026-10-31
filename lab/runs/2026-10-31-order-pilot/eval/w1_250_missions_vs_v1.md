**policy:ppo_bc_250.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.740

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.762 | 0.744 | 0.779 | 0.000 | 0.006 | 0.000 | 108 | 134 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.719 | 0.488 | 0.950 | 0.000 | 0.000 | 0.000 | 57 | 72 | eliminated 0.02, convoy_through 0.25, convoy_destroyed 0.73 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 71.0 | 44.2 | 0.05 | 0.296 | 0.81 | 0.0040 | 0.17 | 1.85 | 0.503 |
| carrier_battle | a | gunship | 860 | 490.1 | 173.9 | 0.53 | 0.277 | 0.82 | 0.0009 | 0.49 | 2.92 | 0.635 |
| carrier_battle | a | strafer | 1032 | 115.1 | 96.9 | 0.05 | 0.205 | 0.72 | 0.0074 | 0.23 | 2.33 | 0.589 |
| carrier_battle | a | all | 3956 | 173.6 | 86.1 | 0.15 | 0.254 | 0.79 | 0.0036 | 0.30 | 2.21 | 0.571 |
| carrier_battle | b | fighter | 2064 | 45.5 | 38.8 | 0.02 | 0.282 | 0.80 | 0.0080 | 0.16 | 1.68 | 0.371 |
| carrier_battle | b | gunship | 860 | 280.9 | 152.3 | 0.25 | 0.255 | 0.85 | 0.0010 | 0.49 | 2.59 | 0.513 |
| carrier_battle | b | strafer | 1032 | 83.1 | 87.6 | 0.03 | 0.205 | 0.71 | 0.0190 | 0.26 | 2.26 | 0.481 |
| carrier_battle | b | all | 3956 | 106.5 | 76.2 | 0.07 | 0.240 | 0.80 | 0.0082 | 0.30 | 2.03 | 0.448 |
| convoy_escort | a | fighter | 1462 | 183.5 | 59.5 | 0.39 | 0.398 | 0.91 | 0.0025 | 0.19 | 1.56 | 0.561 |
| convoy_escort | a | gunship | 430 | 372.8 | 144.9 | 0.73 | 0.234 | 0.90 | 0.0009 | 0.45 | 1.93 | 0.689 |
| convoy_escort | a | strafer | 688 | 143.0 | 41.3 | 0.61 | 0.150 | 0.72 | 0.0067 | 0.26 | 2.59 | 0.454 |
| convoy_escort | a | all | 2580 | 204.3 | 68.9 | 0.51 | 0.242 | 0.86 | 0.0032 | 0.26 | 1.90 | 0.561 |
| convoy_escort | b | fighter | 1462 | 133.7 | 60.7 | 0.30 | 0.347 | 0.86 | 0.0098 | 0.18 | 1.74 | 0.397 |
| convoy_escort | b | gunship | 430 | 436.9 | 196.1 | 0.66 | 0.286 | 0.90 | 0.0014 | 0.44 | 1.75 | 0.614 |
| convoy_escort | b | strafer | 688 | 82.3 | 43.1 | 0.60 | 0.123 | 0.54 | 0.0374 | 0.32 | 2.58 | 0.291 |
| convoy_escort | b | all | 2580 | 170.5 | 78.6 | 0.44 | 0.241 | 0.78 | 0.0160 | 0.27 | 1.97 | 0.412 |
