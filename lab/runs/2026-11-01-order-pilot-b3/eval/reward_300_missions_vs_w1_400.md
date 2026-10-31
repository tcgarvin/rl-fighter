**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.531

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.566 | 0.574 | 0.558 | 0.000 | 0.012 | 0.000 | 100 | 128 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 258 | 0.496 | 0.023 | 0.969 | 0.000 | 0.000 | 0.000 | 36 | 50 | eliminated 0.01, convoy_through 0.02, convoy_destroyed 0.97 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 52.6 | 32.4 | 0.03 | 0.273 | 0.82 | 0.0003 | 0.21 | 1.53 | 0.672 |
| carrier_battle | a | gunship | 430 | 489.1 | 197.7 | 0.47 | 0.304 | 0.84 | 0.0006 | 0.47 | 2.52 | 0.751 |
| carrier_battle | a | strafer | 516 | 92.2 | 48.2 | 0.02 | 0.183 | 0.75 | 0.0003 | 0.18 | 1.79 | 0.713 |
| carrier_battle | a | all | 1978 | 157.8 | 72.5 | 0.12 | 0.260 | 0.81 | 0.0004 | 0.31 | 1.81 | 0.712 |
| carrier_battle | b | fighter | 1032 | 60.4 | 33.0 | 0.05 | 0.266 | 0.80 | 0.0008 | 0.17 | 1.75 | 0.577 |
| carrier_battle | b | gunship | 430 | 397.5 | 175.5 | 0.40 | 0.302 | 0.84 | 0.0002 | 0.48 | 2.16 | 0.710 |
| carrier_battle | b | strafer | 516 | 102.3 | 63.7 | 0.02 | 0.189 | 0.73 | 0.0015 | 0.20 | 1.99 | 0.675 |
| carrier_battle | b | all | 1978 | 144.6 | 72.0 | 0.12 | 0.253 | 0.80 | 0.0007 | 0.28 | 1.90 | 0.643 |
| convoy_escort | a | fighter | 731 | 125.3 | 46.8 | 0.33 | 0.433 | 0.93 | 0.0000 | 0.22 | 1.07 | 0.759 |
| convoy_escort | a | gunship | 215 | 441.6 | 127.2 | 0.77 | 0.291 | 0.92 | 0.0000 | 0.39 | 1.36 | 0.858 |
| convoy_escort | a | strafer | 344 | 176.8 | 44.9 | 0.44 | 0.212 | 0.89 | 0.0001 | 0.15 | 1.32 | 0.785 |
| convoy_escort | a | all | 1290 | 191.8 | 59.7 | 0.43 | 0.288 | 0.91 | 0.0000 | 0.25 | 1.19 | 0.791 |
| convoy_escort | b | fighter | 731 | 143.9 | 41.4 | 0.37 | 0.398 | 0.92 | 0.0001 | 0.20 | 1.28 | 0.641 |
| convoy_escort | b | gunship | 215 | 448.0 | 164.6 | 0.89 | 0.307 | 0.93 | 0.0000 | 0.45 | 1.40 | 0.784 |
| convoy_escort | b | strafer | 344 | 152.3 | 43.9 | 0.53 | 0.166 | 0.85 | 0.0002 | 0.20 | 2.01 | 0.634 |
| convoy_escort | b | all | 1290 | 196.8 | 62.6 | 0.50 | 0.266 | 0.90 | 0.0001 | 0.26 | 1.50 | 0.672 |
