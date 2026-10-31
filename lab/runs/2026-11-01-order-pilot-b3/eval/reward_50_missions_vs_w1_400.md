**policy:ppo_bc_50.pt** vs **policy:ppo_bc_400.pt** (scripted commanders): mean win 0.430

| mission | n | win | as team 0 | as team 1 | draw | time limit | stalemate | median s | p90 s | end reasons |
|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | 258 | 0.380 | 0.457 | 0.302 | 0.000 | 0.000 | 0.000 | 98 | 123 | carrier_destroyed 1.00 |
| convoy_escort | 258 | 0.481 | 0.016 | 0.946 | 0.000 | 0.000 | 0.000 | 40 | 53 | eliminated 0.02, convoy_through 0.02, convoy_destroyed 0.97 |

| mission | side | hull | ships | dmg | shield dmg | survival | hit rate | engage | outside | engine | passes | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| carrier_battle | a | fighter | 1032 | 46.6 | 28.4 | 0.03 | 0.238 | 0.80 | 0.0009 | 0.18 | 1.62 | 0.567 |
| carrier_battle | a | gunship | 430 | 417.3 | 182.8 | 0.41 | 0.274 | 0.84 | 0.0007 | 0.47 | 2.58 | 0.710 |
| carrier_battle | a | strafer | 516 | 89.4 | 55.2 | 0.01 | 0.159 | 0.73 | 0.0009 | 0.18 | 2.01 | 0.667 |
| carrier_battle | a | all | 1978 | 138.3 | 69.0 | 0.11 | 0.227 | 0.80 | 0.0008 | 0.29 | 1.93 | 0.644 |
| carrier_battle | b | fighter | 1032 | 63.5 | 35.8 | 0.05 | 0.285 | 0.79 | 0.0011 | 0.17 | 1.71 | 0.573 |
| carrier_battle | b | gunship | 430 | 492.6 | 190.1 | 0.53 | 0.314 | 0.83 | 0.0004 | 0.49 | 2.39 | 0.707 |
| carrier_battle | b | strafer | 516 | 103.4 | 69.5 | 0.02 | 0.202 | 0.74 | 0.0020 | 0.20 | 1.90 | 0.671 |
| carrier_battle | b | all | 1978 | 167.2 | 78.1 | 0.15 | 0.270 | 0.80 | 0.0010 | 0.29 | 1.91 | 0.643 |
| convoy_escort | a | fighter | 731 | 147.1 | 47.8 | 0.34 | 0.409 | 0.93 | 0.0004 | 0.20 | 1.15 | 0.648 |
| convoy_escort | a | gunship | 215 | 421.8 | 143.0 | 0.75 | 0.287 | 0.92 | 0.0006 | 0.43 | 1.40 | 0.760 |
| convoy_escort | a | strafer | 344 | 153.0 | 42.1 | 0.52 | 0.160 | 0.85 | 0.0011 | 0.18 | 2.10 | 0.642 |
| convoy_escort | a | all | 1290 | 194.4 | 62.1 | 0.45 | 0.258 | 0.91 | 0.0007 | 0.25 | 1.44 | 0.672 |
| convoy_escort | b | fighter | 731 | 164.8 | 47.5 | 0.39 | 0.417 | 0.93 | 0.0006 | 0.19 | 1.28 | 0.652 |
| convoy_escort | b | gunship | 215 | 389.9 | 146.4 | 0.77 | 0.272 | 0.92 | 0.0006 | 0.44 | 1.45 | 0.767 |
| convoy_escort | b | strafer | 344 | 153.7 | 42.4 | 0.53 | 0.168 | 0.82 | 0.0007 | 0.21 | 2.18 | 0.600 |
| convoy_escort | b | all | 1290 | 199.4 | 62.6 | 0.49 | 0.263 | 0.90 | 0.0006 | 0.25 | 1.55 | 0.665 |
