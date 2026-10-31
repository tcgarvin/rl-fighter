**policy:ppo_bc_300.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.726

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 516 | 0.759 | 0.762 | 0.756 | 0.002 | 0.004 | 0.000 | 106 | 128 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 516 | 0.694 | 0.419 | 0.969 | 0.000 | 0.000 | 0.000 | 46 | 72 | eliminated 0.02, convoy_through 0.20, convoy_destroyed 0.78 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 2064 | 61.2 | 41.0 | 0.04 | 0.264 | 0.81 | 0.0017 | 0.23 | 1.77 | 0.658 |
| carrier_battle | a | gunship | 860 | 537.0 | 190.8 | 0.55 | 0.299 | 0.82 | 0.0011 | 0.47 | 2.67 | 0.743 |
| carrier_battle | a | strafer | 1032 | 106.9 | 65.2 | 0.03 | 0.187 | 0.75 | 0.0013 | 0.18 | 2.02 | 0.716 |
| carrier_battle | a | all | 3956 | 176.5 | 79.9 | 0.15 | 0.254 | 0.81 | 0.0014 | 0.31 | 2.03 | 0.702 |
| carrier_battle | b | fighter | 2064 | 47.3 | 32.5 | 0.02 | 0.267 | 0.80 | 0.0055 | 0.16 | 1.73 | 0.373 |
| carrier_battle | b | gunship | 860 | 305.6 | 153.1 | 0.26 | 0.287 | 0.86 | 0.0005 | 0.49 | 2.40 | 0.531 |
| carrier_battle | b | strafer | 1032 | 83.9 | 86.3 | 0.03 | 0.211 | 0.70 | 0.0137 | 0.25 | 2.11 | 0.498 |
| carrier_battle | b | all | 3956 | 113.0 | 72.7 | 0.08 | 0.254 | 0.79 | 0.0058 | 0.29 | 1.97 | 0.456 |
| convoy_escort | a | fighter | 1462 | 147.0 | 53.5 | 0.41 | 0.424 | 0.92 | 0.0004 | 0.23 | 1.16 | 0.755 |
| convoy_escort | a | gunship | 430 | 396.9 | 109.8 | 0.77 | 0.239 | 0.91 | 0.0006 | 0.39 | 1.62 | 0.828 |
| convoy_escort | a | strafer | 688 | 190.8 | 49.4 | 0.49 | 0.199 | 0.88 | 0.0004 | 0.15 | 1.45 | 0.776 |
| convoy_escort | a | all | 2580 | 200.3 | 61.8 | 0.49 | 0.263 | 0.91 | 0.0004 | 0.25 | 1.31 | 0.778 |
| convoy_escort | b | fighter | 1462 | 128.8 | 53.3 | 0.29 | 0.369 | 0.87 | 0.0091 | 0.18 | 1.56 | 0.409 |
| convoy_escort | b | gunship | 430 | 487.5 | 207.5 | 0.82 | 0.326 | 0.92 | 0.0003 | 0.45 | 1.61 | 0.634 |
| convoy_escort | b | strafer | 688 | 75.5 | 35.9 | 0.63 | 0.120 | 0.53 | 0.0413 | 0.33 | 2.25 | 0.279 |
| convoy_escort | b | all | 2580 | 174.4 | 74.4 | 0.47 | 0.261 | 0.78 | 0.0168 | 0.28 | 1.75 | 0.419 |
