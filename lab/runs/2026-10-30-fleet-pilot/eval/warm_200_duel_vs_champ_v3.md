| a | b | n | win | draw | loss | length med (p10–p90) | kill | passes | shots | hits | hit rate | dmg | engage | outside | engine | fire | speed | nan/stuck |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| policy:ppo_bc_200.pt | policy:ppo_bc_600.pt | 512 | 0.010 | 0.020 | 0.980 | 322 (260–364) | 1.000 | 1.00 | 14.6 | 3.9 | 0.264 | 11.4 | 0.801 | 0.0000 | 0.245 | 0.115 | 44.3 | 0 |
| policy:ppo_bc_600.pt | policy:ppo_bc_200.pt | 512 | 0.990 | 0.020 | 0.000 | 322 (260–364) | 1.000 | 1.00 | 33.4 | 24.6 | 0.736 | 72.0 | 0.800 | 0.0000 | 0.770 | 0.662 | 43.6 | 0 |
team-0 a win rate 0.012, team-1 0.008; draws 0.020, time limit 0.000; crashes/match 0.74, crash hp share 0.260
