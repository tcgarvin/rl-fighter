**policy:ppo_bc_200.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.465

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.426 | 0.426 | 0.426 | 0.000 | 0.004 | 0.000 | 100 | 123 | time_limit 0.00, carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.504 | 0.039 | 0.969 | 0.000 | 0.000 | 0.000 | 37 | 48 | eliminated 0.03, convoy_through 0.01, convoy_destroyed 0.97 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 48.3 | 29.1 | 0.03 | 0.242 | 0.81 | 0.0005 | 0.20 | 1.61 | 0.626 |
| carrier_battle | a | gunship | 430 | 416.4 | 177.8 | 0.46 | 0.269 | 0.83 | 0.0011 | 0.48 | 2.62 | 0.720 |
| carrier_battle | a | strafer | 516 | 84.5 | 46.1 | 0.01 | 0.160 | 0.74 | 0.0004 | 0.18 | 1.80 | 0.690 |
| carrier_battle | a | all | 1978 | 137.8 | 65.9 | 0.12 | 0.227 | 0.80 | 0.0007 | 0.30 | 1.88 | 0.676 |
| carrier_battle | b | fighter | 1032 | 60.8 | 33.2 | 0.06 | 0.265 | 0.80 | 0.0011 | 0.16 | 1.73 | 0.576 |
| carrier_battle | b | gunship | 430 | 461.6 | 184.8 | 0.50 | 0.321 | 0.83 | 0.0001 | 0.49 | 2.27 | 0.703 |
| carrier_battle | b | strafer | 516 | 116.6 | 74.5 | 0.03 | 0.207 | 0.75 | 0.0021 | 0.20 | 2.01 | 0.685 |
| carrier_battle | b | all | 1978 | 162.5 | 77.0 | 0.15 | 0.268 | 0.80 | 0.0010 | 0.28 | 1.92 | 0.644 |
| convoy_escort | a | fighter | 731 | 136.0 | 45.1 | 0.34 | 0.432 | 0.93 | 0.0000 | 0.22 | 1.10 | 0.700 |
| convoy_escort | a | gunship | 215 | 415.0 | 124.3 | 0.75 | 0.287 | 0.93 | 0.0000 | 0.40 | 1.30 | 0.812 |
| convoy_escort | a | strafer | 344 | 171.0 | 45.3 | 0.42 | 0.204 | 0.90 | 0.0000 | 0.15 | 1.33 | 0.755 |
| convoy_escort | a | all | 1290 | 191.8 | 58.4 | 0.43 | 0.284 | 0.92 | 0.0000 | 0.24 | 1.19 | 0.740 |
| convoy_escort | b | fighter | 731 | 156.5 | 41.5 | 0.40 | 0.418 | 0.93 | 0.0000 | 0.19 | 1.22 | 0.657 |
| convoy_escort | b | gunship | 215 | 416.2 | 168.7 | 0.88 | 0.299 | 0.93 | 0.0001 | 0.46 | 1.35 | 0.779 |
| convoy_escort | b | strafer | 344 | 156.4 | 42.0 | 0.55 | 0.168 | 0.85 | 0.0001 | 0.20 | 2.01 | 0.644 |
| convoy_escort | b | all | 1290 | 199.7 | 62.8 | 0.52 | 0.268 | 0.91 | 0.0001 | 0.25 | 1.45 | 0.681 |
