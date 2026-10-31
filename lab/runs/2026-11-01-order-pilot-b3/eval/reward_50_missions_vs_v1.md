**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.715

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.709 | 0.702 | 0.717 | 0.000 | 0.012 | 0.000 | 108 | 134 | time_limit 0.01, carrier_destroyed 0.99 |
| convoy_escort | 516 | 0.721 | 0.469 | 0.973 | 0.000 | 0.000 | 0.000 | 51 | 72 | eliminated 0.01, convoy_through 0.24, convoy_destroyed 0.75 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 62.0 | 37.8 | 0.03 | 0.245 | 0.80 | 0.0025 | 0.20 | 1.91 | 0.555 |
| carrier_battle | a | gunship | 860 | 494.1 | 186.2 | 0.53 | 0.264 | 0.83 | 0.0016 | 0.48 | 2.91 | 0.706 |
| carrier_battle | a | strafer | 1032 | 103.6 | 72.0 | 0.03 | 0.161 | 0.72 | 0.0027 | 0.18 | 2.17 | 0.668 |
| carrier_battle | a | all | 3956 | 166.8 | 79.0 | 0.14 | 0.223 | 0.79 | 0.0022 | 0.30 | 2.19 | 0.635 |
| carrier_battle | b | fighter | 2064 | 49.9 | 39.3 | 0.02 | 0.297 | 0.80 | 0.0071 | 0.15 | 1.69 | 0.379 |
| carrier_battle | b | gunship | 860 | 329.3 | 161.6 | 0.30 | 0.280 | 0.86 | 0.0007 | 0.50 | 2.48 | 0.523 |
| carrier_battle | b | strafer | 1032 | 85.3 | 86.0 | 0.03 | 0.212 | 0.71 | 0.0172 | 0.26 | 2.09 | 0.495 |
| carrier_battle | b | all | 3956 | 119.9 | 78.1 | 0.09 | 0.258 | 0.80 | 0.0071 | 0.30 | 1.96 | 0.458 |
| convoy_escort | a | fighter | 1462 | 172.9 | 54.0 | 0.43 | 0.390 | 0.92 | 0.0010 | 0.22 | 1.37 | 0.627 |
| convoy_escort | a | gunship | 430 | 358.6 | 124.6 | 0.78 | 0.220 | 0.90 | 0.0010 | 0.42 | 1.83 | 0.740 |
| convoy_escort | a | strafer | 688 | 161.5 | 43.3 | 0.56 | 0.154 | 0.83 | 0.0012 | 0.18 | 2.22 | 0.625 |
| convoy_escort | a | all | 2580 | 200.8 | 62.9 | 0.52 | 0.233 | 0.89 | 0.0011 | 0.26 | 1.67 | 0.652 |
| convoy_escort | b | fighter | 1462 | 130.4 | 58.0 | 0.29 | 0.358 | 0.86 | 0.0103 | 0.17 | 1.65 | 0.397 |
| convoy_escort | b | gunship | 430 | 457.4 | 207.2 | 0.70 | 0.304 | 0.92 | 0.0011 | 0.45 | 1.62 | 0.623 |
| convoy_escort | b | strafer | 688 | 75.2 | 37.1 | 0.61 | 0.120 | 0.49 | 0.0489 | 0.33 | 2.39 | 0.269 |
| convoy_escort | b | all | 2580 | 170.2 | 77.3 | 0.44 | 0.252 | 0.76 | 0.0197 | 0.27 | 1.84 | 0.407 |
