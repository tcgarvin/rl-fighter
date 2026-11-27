# Fight ablation: bombers cost the fleet fights, teammates don't

Last round's pilots learned the bomber but fought worse
([horizon and bombers](../2026-11-24-horizon-bombers/results.md)). Three changes came
together there: bombers in training, the station assault in the mission mix, and live
pilots as teammates. This night trained the same parent, `followers_dock_v8_2676`, twice
more, each time without one of the changes. The first suspect was the teammates, and
they are not the main cause. The pilot trained without them lost the most fleet fights
against the script, and lost them within its first 500 updates. The pilot trained without
bombers held on far better there. Against another learned pilot, both fell, so something
common to both also costs, and the two changes together cost the most. Wins above
replacement rates the bomber pilot level with its parent. It edges onto the live ten by a
hair, in place of `kite_2205`. No rule of the game changed (`SIM_VERSION` 11).

<!-- summary: Last time our pilots learned to fly the torpedo bomber but got worse at ordinary dogfights, and we didn't know why. This time we trained the same pilot twice more, leaving out one change each time. The answer is mostly the bombers: the copy that practised in bombers lost more fleet fights within hours, while the copy that practised beside other pilots, our first suspect, held on. Both copies still got worse against another of our pilots, so there is more to find. The bomber pilot rates level with its parent and joins the live page. -->

The plan is in [plan.md](plan.md). Both arms started from the same weights and trained on
Beast from 13:22 on 2026-11-26 to 03:00 the next morning, at about 11 s an update. Both
used the parent's `gamma` 0.995. Last round's `h995` arm is the reference with all three
changes.

| Arm | Bombers | Teammates | Updates |
|---|---|---|---|
| `solo` | yes | no | 4,359 |
| `nobomb` | no | yes | 4,198 |
| `h995` | yes | yes | 5,374 |

"Teammates" means live pilots flying about a quarter of the learner's side. All three also had the station assault in their mission mix. The new members are `dock_solo_4359` and `dock_nobomb_4198`. The full tables are in
[report.md](report.md), with quick evals every 500 updates. The ± are 1.96 standard
errors. The parent column is the same evals on `followers_dock_v8_2676`.

## The fights

| Win rate | Parent | `solo` | `nobomb` | `h995` |
|---|---|---|---|---|
| Fleet suite | 0.88 | **0.68** | 0.77 | 0.74 |
| Fleet 3 v 3 | 0.92 | **0.69** | 0.88 | 0.77 |
| Fleet 4 v 4 | 0.78 | 0.50 | 0.59 | 0.53 |
| Carrier battle | 0.89 | 0.70 | 0.75 | 0.66 |
| Station assault | 0.61 | **0.91** | 0.62 | **0.93** |
| 3 v 3, other pilot | 0.59 | 0.38 | 0.22 | **0.11** |

The first five are against the script, about ± 0.05 (± 0.1 to 0.17 for one fleet size). Convoy escort stayed at 0.97 to 1.00 for all. The last row is
3 v 3, unordered, against a free `followers_school_1052`, ± 0.03.

**Against the script, the bombers did it.** `solo` has bombers and no teammates. Its
fleet score is the lowest of the three, and in fleet 3 v 3 it fell from 0.92 to 0.69. `nobomb` has
the teammates and no bombers, and stayed level with its parent in 3 v 3 (0.88). The fleet
suite has no bombers in it at all. Practice in the bomber has cost skill in the hulls the
pilot already flew, and fast:

| Fleet suite | `solo` | `nobomb` |
|---|---|---|
| Update 500 | 0.73 | 0.88 |
| 1,000 | 0.73 | 0.80 |
| 2,000 | 0.67 | 0.81 |
| 3,000 | 0.68 | 0.84 |
| 4,000 | 0.71 | 0.83 |
| Final | 0.68 | 0.77 |

Quick evals are ± 0.08, the final ± 0.06. `nobomb` ends about 0.1 below its parent, so the
teammates or the station mix may cost a little here too, but most of the fall is the
bombers'.

The bombers also bought all the station assault gain. `nobomb` trained on the station
assault as often as the others, with its fixed bombers on the attacking side, yet it won no more often than its parent.
The bomber practice in the other missions is what taught the pilots to attack the station.

**Against another pilot, both fell.** In 3 v 3 against `followers_school_1052`, `solo` won
0.38, `nobomb` 0.22, and `h995`, with both changes, 0.11. `solo` fell within the first 500
updates (0.27), like its fleet score. `nobomb` stayed between 0.33 and 0.59 through update
3,500, then dropped to 0.22 by 4,000 (quick evals ± 0.05). So neither change alone explains this
loss, and the two together are worse than either. What's common to both is the station
assault in the mix and simply more training on this config. That is the plan's "both
fall" row, and this run can't separate those two.

One more thing changed in `nobomb`: given orders, it now wins the 3 v 3 more often than
unordered (0.31 against 0.22). The parent and the other arms win less, or no more, when
ordered (the parent 0.23 against 0.59). Its unordered fight got worse while its ordered one got better.

## The bomber and docking

| Measure | Parent | `solo` | `nobomb` | `h995` |
|---|---|---|---|---|
| Swap cost, DM | −0.16 | **+0.06** | −0.10 | −0.03 |
| Swap cost, carrier | −0.18 | −0.07 | −0.05 | −0.08 |
| Calm drills | 0.38 | 0.48 | 0.65 | **0.73** |
| Under fire | 0.14 | 0.24 | 0.24 | **0.34** |
| Recalls, carrier | 0.03 | 0.05 | 0.07 | 0.05 |
| Recalls, station | 0.07 | 0.06 | **0.13** | 0.08 |

Swap cost is the change in a side's result when its first gunship becomes a bomber (± 0.04
in deathmatches (DM), ± 0.09 in carrier battles). Dock drills, calm or under fire, are ± 0.08, match recalls ± 0.01 to
0.02 ("recalls" is the share of recalls in matches that end in a dock).

`solo` learned the bomber as well as `h995` did: swapping a gunship for a bomber no longer
costs its side anything in a deathmatch. `nobomb` docks better than `solo`. Its station
recalls, 0.13, are the best of any learned pilot so far, though still far below the
script's 0.54. That may be partly a side effect. Teammates fly a quarter of the learner's
match slots and their rows train nothing, so `nobomb` spent 18 in 100 of its training rows
in drills, against 12 for `solo`.

## Wins above replacement: one new live pilot

WAR over the live ten and the two new members: 5,760 matches, 1,440 in each live mission,
the live commander stable ([war.md](../../population/2026-11-sim6/war/fight-ablation/war.md)).

| Pilot | WAR | 95% interval |
|---|--:|---|
| `kite_pay025_2211` | +11.6 | +8.9 to +14.3 |
| `dock_solo_4359` | +7.2 | +4.3 to +10.0 |
| `followers_dock_v8_2676` | +7.2 | +4.3 to +9.9 |
| `dock_nobomb_4198` | +6.0 | +3.3 to +8.8 |
| `kite_2205` | +5.5 | +2.6 to +8.5 |

The first is the top pilot this time, then `solo`, its parent, `nobomb`, and the last of
the twelve. Last round the bomber pilots rated 2.4 and 3.0 below this parent. `solo` now rates level
with it, and `nobomb` a little below. Under the no-gates rule WAR picks the live page:
`dock_solo_4359` is ninth of twelve, a thousandth of a win ahead of its parent, and joins
the live ten. `kite_2205` drops to twelfth and leaves it. That margin is far inside the
noise, so this is a coin flip the rule settled, not a better pilot. It does put a pilot
that flies the bomber well on the live page, which has flown bombers in every station
assault. `dock_nobomb_4198` stays in the season as another child of the parent. Each WAR
is its own fit, so compare ratings within one table, not across rounds.

## Next

- **A control arm:** the same parent and night with neither bombers nor teammates, only
  the station mix. If it also falls against `followers_school_1052`, the cause is the mix or more
  training on this config, not the bombers.
- **Bombers at a lower share.** They pay in the station assault and cost in plain fights.
  Try 0.05 to 0.1 of strike slots in place of 0.2, or bombers only in drills.
- **Keep the drill share matched** when comparing arms with and without teammates, so the
  docking comparison is fair.
- The commander run paused at update 7,149 still waits for a stronger pilot list.
