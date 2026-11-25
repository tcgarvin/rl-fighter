# Horizon and bombers: better bombers and dockers, weaker fighters

A live follower that already docked, `followers_dock_v8_2676`, trained for a night in two
copies. Both copies flew bombers in a fifth of their strike slots and had live pilots as
about a quarter of their teammates. One copy also looked much further ahead (`gamma` 0.999);
the other kept its parent's 0.995. Both learned to fly the bomber: swapping a gunship for a
bomber no longer costs a side much, and bombers do two to three times the damage they did. Both dock
about twice as often in drills. In real matches recalls still mostly fail. The longer
horizon made no difference we could measure. Both also became weaker in fights the station
assault doesn't cover. Wins above replacement rates them below their parent, so the live
ten stays as it was. No rule of the game changed (`SIM_VERSION` 11).

<!-- summary: Our trained pilots had never learned to fly the slow torpedo bomber, and rarely made it home for repairs. We trained one of the live pilots for a night with bombers in its matches and other live pilots beside it, in two copies: one that plans much further ahead, one that doesn't. Both learned the bomber: it now earns its place instead of costing its side. Both dock about twice as often in practice. But planning further ahead didn't help them come home in real battles, and both got worse at plain dogfights. Overall they win less than the pilot they started from, so they don't make the live page this time. -->

The plan is in [plan.md](plan.md). Both arms started from the same weights and trained on
Beast from 08:15 on 2026-11-24 to 03:00 the next morning, with a pause from 14:00 to
22:54 while the machine was needed. At about 11 s an update:

| Arm | Gamma | Updates | Member id |
|---|---|---|---|
| `h999` | 0.999 (a reward 30 s away weighs 0.41) | 5,334 | `dock_h999_5334` |
| `h995` | 0.995, the parent's (0.011) | 5,374 | `dock_h995_5374` |

The full tables, with the evals every 1,000 updates, are in [report.md](report.md). The ±
are 1.96 standard errors. The parent column is the same evals on `followers_dock_v8_2676`.

## The bomber: learned

The same matches played twice, once with a side's first gunship and once with a bomber in
its place:

| Bomber for gunship | Parent | `h999` | `h995` |
|---|---|---|---|
| Score, deathmatch | −0.16 | −0.11 | **−0.03** |
| Score, carrier battle | −0.18 | **−0.05** | **−0.08** |
| Hits capital ships | 36 | 74 | **101** |
| Hits strike craft | 55 | 174 | **223** |
| (Gunship: capital ships) | 152 | 133 | 170 |

Score is the change in the side's result (± 0.04 in deathmatches, ± 0.09 in carrier
battles); damage is the bomber's (or the gunship's) in a carrier battle.

A pilot in a bomber used to barely fight. Now it does about as well as a gunship in that
slot. The swap cost was near zero by update 2,000, and the damage kept rising after. It is still not a specialist: most of its damage goes to strike craft,
and a gunship in the same slot still hits capital ships harder.

## Docking: better in drills, not yet in matches

| Docked | Parent | `h999` | `h995` | Script |
|---|---|---|---|---|
| Calm drills | 0.38 | **0.67** | **0.73** | 0.95 |
| Drills under fire | 0.14 | 0.23 | **0.34** | 0.58 |
| Recalls, carrier battle | 0.03 | 0.06 | 0.05 | 0.61 |
| Recalls, station assault | 0.07 | 0.09 | 0.08 | 0.54 |

Drills are ± 0.08, match recalls ± 0.01 to 0.02. "Recalls" is the share of recalls in
matches that end in a dock. The script's figures are from
[dock and repair](../2026-11-20-dock-repair/results.md) (its station assault figure is the
citadel's, the live layout).

In matches, recalls that end in a dock rose by only 2 or 3 in 100. The most common failure is still "never close":
the craft never gets near its bay. It is four in five of the failed recalls in a carrier
battle for `h999`, and 70 in 100 for `h995`.

**The longer horizon didn't help.** `h999` was a point or two ahead on match recalls in
some of the quick evals along the way (0.09 against 0.07 at update 4,000), but the full
final evals put the two arms level. `h995` docks more under fire and flies the bomber
better. So the gains came from the extra night of training with bombers and dock drills,
not from looking further ahead. A short horizon is not, by itself, what keeps
pilots in the fight when they are recalled. Two candidates remain, neither tested: the pay
for damage dealt outweighs the dock bonus, or the commander's recall reads as one more go-to order
among many.

## What got worse: plain fighting

| Win rate | Parent | `h999` | `h995` |
|---|---|---|---|
| Station assault | 0.61 | **0.88** | **0.93** |
| Convoy escort | 0.99 | 0.99 | 0.99 |
| Carrier battle | 0.89 | 0.73 | 0.66 |
| Fleet suite | 0.88 | 0.73 | 0.74 |
| Fleet 4 v 4 | 0.78 | 0.44 | 0.53 |
| 3 v 3, other pilot | 0.59 | 0.23 | 0.11 |

The first five are against the script, about ± 0.05 (± 0.15 for 4 v 4). The last is 3 v 3,
unordered, against a free `followers_school_1052`, ± 0.03.

The station assault was new to this line (a fifth of the matches, three bombers on the
attacking side), and both arms got much better at it. Everywhere else they fight worse,
and the bigger the fleet, the worse. The drop came early and then held: `h995`'s fleet
score was 0.83 at update 1,000, 0.72 at 3,000 and 0.74 at the end (extra fleet evals in
`probe/`). In training the numbers stayed flat (damage dealt and taken, and wins against the script and
against past versions of itself), so the loss is in matches unlike the ones it trained on.

We can't yet say which change did it. Both arms had all three changes, bombers, the
station assault and live teammates, so only another run can separate them. The guess
we would test first: with live pilots as a quarter of its teammates in training, it may
have learned to let them start the fight. In the fleet suite and the 3 v 3 tests it flies
every ship of its side, so no one starts it. That fits the drop growing with fleet
size, but we haven't tested it.

## Wins above replacement: the live ten stays

WAR over the live ten and the two new members: 5,760 matches, 1,440 in each live mission,
the live commander stable ([war.md](../../population/2026-11-sim6/war/horizon-bombers/war.md)).

| Pilot | WAR | 95% interval |
|---|--:|---|
| `fighters_pay1_1317` | +14.2 | +11.5 to +16.8 |
| `followers_dock_v8_2676` | +8.5 | +5.8 to +11.2 |
| `dock_h995_5374` | +6.1 | +3.5 to +9.1 |
| `dock_h999_5334` | +5.5 | +2.6 to +8.5 |

The first is the top live pilot, the second the parent (tenth on the live list).
Both new pilots beat the script, but rank 11th and 12th of 12, below their parent in every
mission, including the station assault. Under the no-gates rule WAR picks the live page,
so the live ten is unchanged. It is republished with this WAR's ratings. The two new pilots
stay in the season as children of `followers_dock_v8_2676`. They are the first pilots that fly
a bomber well, and the obvious parents for the next bomber run.

## Next

- Rerun with one change at a time (bombers alone, teammates alone) from the same parent,
  to find what cost the fighting. Then keep whichever change pays.
- Docking in matches needs more than drills. Next to try: a larger pay for docking when
  recalled, or recall drills that start in the middle of a fight.
- Drop the longer horizon from pilots for now: it bought nothing measurable here and costs
  a critic warm-up.
- The commander run paused at update 7,149 waits for a stronger pilot list; this round
  didn't produce one.
