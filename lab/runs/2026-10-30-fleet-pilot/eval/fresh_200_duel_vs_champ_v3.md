| a | b | n | win | draw | loss | length med (p10–p90) | kill | passes | shots | hits | hit rate | dmg | engage | outside | engine | fire | speed | nan/stuck |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| policy:ppo_bc_200.pt | policy:ppo_bc_600.pt | 512 | 0.025 | 0.051 | 0.949 | 310 (254–380) | 1.000 | 1.00 | 15.5 | 3.2 | 0.208 | 9.7 | 0.798 | 0.0000 | 0.300 | 0.115 | 47.0 | 0 |
| policy:ppo_bc_600.pt | policy:ppo_bc_200.pt | 512 | 0.975 | 0.051 | 0.000 | 310 (254–380) | 1.000 | 1.00 | 33.0 | 23.4 | 0.709 | 68.2 | 0.797 | 0.0000 | 0.786 | 0.659 | 44.6 | 0 |
team-0 a win rate 0.023, team-1 0.027; draws 0.051, time limit 0.000; crashes/match 0.79, crash hp share 0.376
