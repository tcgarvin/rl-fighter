# Horizon and bombers: better bombers and dockers, weaker fighters

Our trained pilots had never learned to fly the bomber, a slow ship with a torpedo fixed
to its nose, and rarely made it home when called back for repair. So a live follower that
already docked, `followers_dock_v8_2676`, trained for a night in two copies. (It is one
of the live ten, the ten pilots the live page draws from. It belongs to the followers
family, pilots bred to fight and follow orders, and was taught to dock. `_v8_` means it
reads go-to deadlines, and 2676 is the update it was saved at. An update is one round of
playing matches and then adjusting the network.) Both copies flew bombers in a fifth of
their strike slots (a match's places for the small piloted ships) and had live pilots as
about a quarter of their teammates. One copy also looked much further ahead (`gamma`
0.999, its discount, the setting for how much future reward counts); the other kept its
parent's 0.995.

Both learned to fly the bomber: swapping a gunship for a bomber no longer costs a side
much, and bombers do two to four times the damage they did. Both dock about twice as
often in drills, the short practice scenarios. In real matches, when a commander calls a
damaged ship home (a recall), it still mostly fails to get there. The longer horizon made
no difference we could measure. Both also became weaker in every kind of match except the
station assault (a mission in which a static station defends with its own ships, and the
attacker brings a carrier, bombers and a dreadnought, a heavy warship). Wins above
replacement (WAR, our estimate of how many more matches in 100 a side wins with a pilot
than with the hand-written script) rates them below their parent, so the live ten stays
as it was. No rule of the game changed (`SIM_VERSION` 11, the eleventh version of the
game's rules).

<!-- summary: Our trained pilots had never learned to fly the slow torpedo bomber, and rarely made it home for repairs. We trained one of the live pilots for a night with bombers in its matches and other live pilots beside it, in two copies: one that plans much further ahead, one that doesn't. Both learned the bomber: it now earns its place instead of costing its side. Both dock about twice as often in practice. But planning further ahead didn't help them come home in real battles, and both got worse at plain dogfights. Overall they win less than the pilot they started from, so they don't make the live page this time. -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error. A pilot sets every thruster and trigger
itself, with no autopilot (the [pilot page](/pilot/) explains how one works). Two recent
additions to the game had left the pilots behind. The
[bomber](../2026-11-19-station-bomber/results.md) arrived with the station assault: a
learned pilot in one barely fought, and swapping a gunship for a bomber cost the live
pilots of that time 0.38 in win rate (out of 1) in a 3 v 3 deathmatch. [Dock and
repair](../2026-11-20-dock-repair/results.md) let damaged ships fly home to their
carrier, and the [dock pilots](../2026-11-20-dock-pilot/results.md) learned it in
practice, but in real matches only 5 to 8 recalls in 100 ended in a dock.

Meanwhile the [long commander run](../2026-11-21-commander-long/results.md) had found that
a commander does best by giving almost no orders, because today's pilots lose more than
they gain from one. A commander needs pilots that come home when recalled. One guess was
that pilots plan too short: at 0.995, a reward 30 seconds away counts for about 1% of one
now, so breaking off a fight to repair is worth almost nothing to them. This night tested
that guess, and tried to teach the bomber, in one run.

<!-- figure-idea: shared: a training night. A parent pilot's weights copied into two or three arms that differ in one setting, each trained overnight, measured by quick evals along the way and full evals at the end, then entered into the season and rated by WAR, which picks the live ten. Helps every pilot-training entry read its setup paragraph. -->

## The run

The plan is in [plan.md](plan.md). Both arms (the two copies, identical except for the
setting under test) started from the same weights and trained on Beast, the lab's desktop
with two graphics cards, from 08:15 on 2026-11-24 to 03:00 the next morning, with a pause
from 14:00 to 22:54 while the machine was needed. At about 11 s an update:

| Arm | Gamma | Updates | Member id |
|---|---|---|---|
| `h999` | 0.999 (a reward 30 s away weighs 0.41) | 5,334 | `dock_h999_5334` |
| `h995` | 0.995, the parent's (0.011) | 5,374 | `dock_h995_5374` |

The figure in brackets is how much a reward 30 seconds in the future counts, against 1
for a reward now. The member id is each copy's name in the season, the record of every
pilot trained under these rules: its line, its arm and the update it was saved at.

<!-- figure-idea: shared: what the discount does. A curve of how much a reward counts against how many seconds ahead it comes, at 0.99, 0.995 and 0.999, with the 30-second mark showing 0.011 against 0.41. Makes "horizon" and "gamma" concrete wherever they appear. -->

The full tables, with the evals every 1,000 updates, are in [report.md](report.md). An
eval is a batch of matches played only to measure, with no training. ± is the margin of
error (1.96 standard errors): the true value very likely lies within that range. The
parent column is the same evals on `followers_dock_v8_2676`.

## The bomber: learned

The same matches played twice, once with a side's first gunship and once with a bomber in
its place, the pilot under test flying every strike craft. The matches are 3 v 3 team
deathmatches (small ships only, three a side, last side standing wins) and carrier
battles (each side has a carrier that launches its strike craft, and a side wins by
destroying the enemy carrier). The first two rows are the
change in the side's result when the bomber goes in (0 means the swap costs nothing,
−0.16 means the side's share of matches won falls by 0.16). The other rows are damage dealt in a
carrier battle by the bomber, or, in the last row, by the gunship it replaced.

| Bomber for gunship | Parent | `h999` | `h995` |
|---|---|---|---|
| Score, deathmatch | −0.16 | −0.11 | **−0.03** |
| Score, carrier battle | −0.18 | **−0.05** | **−0.08** |
| Bomber's damage to capital ships | 36 | 74 | **101** |
| Bomber's damage to strike craft | 55 | 174 | **223** |
| (Gunship's damage to capital ships) | 152 | 133 | 170 |

The score changes are ± 0.04 in deathmatches and ± 0.09 in carrier battles. The parent's
−0.16 and the 0.38 above are different pilots: that figure was for the live pilots of
2026-11-19, before this parent was trained.

<!-- figure-idea: shared: the bomber swap. The same match run twice side by side, identical except that one side's first gunship is a bomber in the second run, with the difference in result read off as the swap cost. Used in this entry and the fight ablation. -->

A pilot in a bomber used to barely fight. Now it does about as well as a gunship in that
slot. The swap cost was near zero by update 2,000, and the damage kept rising after. It is
still not a specialist: most of its damage goes to strike craft (the small piloted
ships), and a gunship in the same slot still hits capital ships (carriers, stations and
the like) harder.

## Docking: better in drills, not yet in matches

Each number is the share of attempts that ended with the ship docked. The first two rows
are dock drills: a damaged ship ordered home, either with a clear run (calm) or with
enemies chasing it (under fire). The last two are real matches, where the scripted
commander recalls a ship when its hull is below half.

| Docked | Parent | `h999` | `h995` | Script |
|---|---|---|---|---|
| Calm drills | 0.38 | **0.67** | **0.73** | 0.95 |
| Drills under fire | 0.14 | 0.23 | **0.34** | 0.58 |
| Recalls, carrier battle | 0.03 | 0.06 | 0.05 | 0.61 |
| Recalls, station assault | 0.07 | 0.09 | 0.08 | 0.54 |

Drills are ± 0.08, match recalls ± 0.01 to 0.02. "Recalls" is the share of recalls in
matches that end in a dock. The script (our hand-written pilot) figures are from [dock
and repair](../2026-11-20-dock-repair/results.md) (its station assault figure is for the
citadel, the layout the live page uses: a much bigger station whose turrets and launch
bays can each be shot off).

In matches, recalls that end in a dock rose by only 2 or 3 in 100. The most common failure
is still "never close": the craft never gets near its bay. It is four in five of the
failed recalls in a carrier battle for `h999`, and 70 in 100 for `h995`.

**The longer horizon didn't help.** `h999` was a point or two ahead on match recalls in
some of the quick evals along the way (the smaller evals every 1,000 updates: 0.09
against 0.07 at update 4,000), but the full final evals put the two arms level. `h995`
docks more under fire and flies the bomber better. So the gains came from the extra night
of training with bombers and dock drills, not from looking further ahead. A short horizon
is not, by itself, what keeps pilots in the fight when they are recalled. Two candidates
remain, neither tested: the pay for damage dealt outweighs the dock bonus (the reward for
docking), or the commander's recall reads as one more go-to order among many (a dock
order shows the pilot a point to fly to, its bay, much as a go-to order does).

## What got worse: plain fighting

Each number is the share of matches won. In the missions the pilot under test plays each
side equally often (in the station assault, attacking and defending). The fleet suite is
a fixed set of sixteen team deathmatch line-ups, from one ship a side to four a side,
some of them uneven, flown by the pilot under test against the script. "Fleet 4 v 4" is
its four-a-side part.

| Win rate | Parent | `h999` | `h995` |
|---|---|---|---|
| Station assault | 0.61 | **0.88** | **0.93** |
| Convoy escort | 0.99 | 0.99 | 0.99 |
| Carrier battle | 0.89 | 0.73 | 0.66 |
| Fleet suite | 0.88 | 0.73 | 0.74 |
| Fleet 4 v 4 | 0.78 | 0.44 | 0.53 |
| 3 v 3, other pilot | 0.59 | 0.23 | 0.11 |

The first five are against the script, about ± 0.05 (± 0.15 for 4 v 4). The last is 3 v
3, unordered (no orders on the pilot's side), against a free `followers_school_1052` (a
followers pilot that went through [go-to school](../2026-11-14-goto-school-2/results.md),
drill-heavy training on go-to orders, and our standard learned opponent, also flying
with no orders), ± 0.03.

The station assault was new to this line (a fifth of the matches, three bombers on the
attacking side), and both arms got much better at it. Everywhere else they fight worse,
and the bigger the fleet, the worse. The drop came early and then held: `h995`'s fleet
score was 0.83 at update 1,000, 0.72 at 3,000 and 0.74 at the end (extra fleet evals in
`probe/`). In training the numbers stayed flat (damage dealt and taken, and wins against
the script and against past versions of itself), so the loss is in matches unlike the
ones it trained on.

We can't yet say which change did it. Both arms had all three changes, bombers, the
station assault and live teammates, so only another run can separate them. The guess
we would test first: with live pilots as a quarter of its teammates in training, it may
have learned to let them start the fight. In the fleet suite and the 3 v 3 tests it flies
every ship of its side, so no one starts it. That fits the drop growing with fleet
size, but we haven't tested it.

## Wins above replacement: the live ten stays

WAR is played in matches like the live page's, with pilots dropped at random into the
ships, and a statistical fit gives each pilot its rating (0 is script level). This one
covered the live ten and the two new members: 5,760 matches, 1,440 in each live mission, with commanders
drawn from the live commander stable, the commanders the live page uses
([war.md](../../population/2026-11-sim6/war/horizon-bombers/war.md)). The 95% interval is
the range the true WAR very likely lies in.

| Pilot | WAR | 95% interval |
|---|--:|---|
| `fighters_pay1_1317` | +14.2 | +11.5 to +16.8 |
| `followers_dock_v8_2676` | +8.5 | +5.8 to +11.2 |
| `dock_h995_5374` | +6.1 | +3.5 to +9.1 |
| `dock_h999_5334` | +5.5 | +2.6 to +8.5 |

The first is the top live pilot, from the fighters family (bred mainly to win fights), in
its branch paid less for following orders. The second is the parent (tenth on the live
list).
Both new pilots beat the script, but rank 11th and 12th of 12, below their parent in every
mission, including the station assault. Under the no-gates rule (a new pilot has no pass
mark to meet: it joins the season and WAR alone decides who flies live), WAR picks the
live page, so the live ten is unchanged. It is republished with this WAR's ratings. The
two new pilots stay in the season as children (pilots trained from it) of
`followers_dock_v8_2676`. They are the
first pilots that fly a bomber well, and the obvious parents for the next bomber run.

## Next

- Rerun with one change at a time (bombers alone, teammates alone) from the same parent,
  to find what cost the fighting. Then keep whichever change pays.
- Docking in matches needs more than drills. Next to try: a larger pay for docking when
  recalled, or recall drills that start in the middle of a fight.
- Drop the longer horizon from pilots for now: it bought nothing measurable here and costs
  a critic warm-up (the critic, a second network used in training to predict how a match
  will go, starts out wrong at a new discount, so it first trains alone, here for 50
  updates, before the pilot itself moves).
- The [commander run](../2026-11-21-commander-long/results.md) paused at update 7,149
  waits for a stronger pilot list; this round didn't produce one.
