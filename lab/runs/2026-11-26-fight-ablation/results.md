# Fight ablation: bombers cost the fleet fights, teammates don't

In the [horizon and bombers night](../2026-11-24-horizon-bombers/results.md) our pilots
learned to fly the bomber, a slow ship with a torpedo fixed to its nose, but fought worse
in ordinary fleet fights (team deathmatches: small ships only, 1 to 4 a side, last side
standing wins). Three changes came together there. Bombers flew a fifth of the small
ships' places in the other missions and in drills. The station assault (a static station
defends with its own ships, and the attacker brings a carrier, bombers and a dreadnought,
a heavy warship) joined the mix of missions trained on. And live pilots flew some of the
learner's own ships as teammates. This night trained the same parent pilot,
`followers_dock_v8_2676`, twice more, each time without one of the first two changes (an
ablation: take out one ingredient at a time to see which one caused the effect). `solo`
had no teammates, and `nobomb` no bombers outside the station assault. The station
assault stayed in both, since it is now part of the default training mix. It always puts
three bombers on the attacking side, so `nobomb` still flew bombers there, and only
there.

The first suspect was the teammates, and they are not the main cause. The pilot trained
without them, `solo`, lost the most fleet fights against the script, our hand-written
pilot, and lost them within its first 500 updates (an update is one round of playing
matches and then adjusting the network). The pilot trained without the extra bombers,
`nobomb`, held on far better there. Against another learned pilot, both fell, so
something common to both also costs, and the two changes together cost the most. Wins
above replacement (WAR, our estimate of how many more matches in 100 a side wins with a
pilot than with the script) rates the bomber pilot level with its parent. It edges onto
the live ten, the ten pilots the live page draws from, by a hair, in place of
`kite_2205`. No rule of the game changed (`SIM_VERSION` 11, the eleventh version of the
game's rules).

<!-- summary: Last time our pilots learned to fly the torpedo bomber but got worse at ordinary dogfights, and we didn't know why. This time we trained the same pilot twice more, leaving out one change each time. The answer is mostly the bombers: the copy that practised in bombers lost more fleet fights within hours, while the copy that practised beside other pilots, our first suspect, held on. Both copies still got worse against another of our pilots, so there is more to find. The bomber pilot rates level with its parent and joins the live page. -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error (the [pilot page](/pilot/) explains how
one works). The parent here, `followers_dock_v8_2676`, is a live pilot from the followers
family, pilots bred to fight and follow orders, and was taught to
[dock for repair](../2026-11-20-dock-pilot/results.md) (`_v8_` means it reads go-to
deadlines). A pilot's name is its training line followed by the update it was saved at,
and the `dock_` pilots here are its children.

Last round, two copies of it trained with bombers, the station assault and live teammates
all at once. They learned the bomber and got much better at the station assault, but
against the script their fleet suite score fell from 0.88 to 0.73 and 0.74. (The fleet
suite is a fixed set of sixteen team deathmatch line-ups, from one ship a side to four a
side, some of them uneven and none with a bomber, flown by the pilot under test against
the script.) In 3 v 3 (three ships a side) against another learned pilot their wins fell
from 0.59 to between 0.11 and 0.23. Those copies differed only in how far ahead they
planned, and fell alike, so that was ruled out. Before keeping any of the three changes
we needed to know which one cost the fighting. Meanwhile the [long commander
run](../2026-11-21-commander-long/results.md) is paused until there are pilots worth
giving orders to.

## The run

The plan is in [plan.md](plan.md). Both arms (copies of the parent, identical except for
what is left out) started from the same weights and trained on Beast, the lab's desktop
with two graphics cards, from 13:22 on 2026-11-26 to 03:00 the next morning, at about
11 s an update. Both used the parent's `gamma` 0.995 (the discount, which sets how far
ahead a pilot weighs reward). Last round's `h995` arm is the reference with all three
changes.

<div data-figure="diagram" data-name="training-night" data-caption="Here one parent, followers_dock_v8_2676, was copied into two arms, solo and nobomb, each leaving out one of last round's changes. They trained from 13:22 to 03:00. In the WAR round one of them, dock_solo_4359, joined the live ten."></div>

| Arm | Bombers outside the station assault | Teammates | Updates |
|---|---|---|---|
| `solo` | yes | no | 4,359 |
| `nobomb` | no | yes | 4,198 |
| `h995` | yes | yes | 5,374 |

<!-- figure-idea: shared: an ablation at a glance. The three changes drawn as switches (bombers, station assault in the mix, live teammates) and which were on in the parent, h995, solo and nobomb, with each arm's fleet score beside it. Many entries compare arms this way, and the picture shows what each arm isolates. -->

"Teammates" means live pilots flying about a quarter of the learner's side. All three
also had the station assault in their mission mix. The new members of the season (the
record of every pilot trained under these rules) are `dock_solo_4359` and
`dock_nobomb_4198`. The full tables are in [report.md](report.md), with quick evals (the
smaller evals run during training) every 500 updates. An eval is a batch of matches
played only to measure, with no training. ± is the margin of error (1.96 standard
errors): the true value very likely lies within that range. The parent column is the
same evals on `followers_dock_v8_2676`.

## The fights

Each number is the share of matches won (0.5 is even). "Fleet 3 v 3" and "Fleet 4 v 4"
are the fleet suite's three-a-side and four-a-side parts. In the carrier battle (each
side has a carrier, and a side wins by destroying the enemy's) and the station assault,
the pilot under test plays each side equally often, so the station figure averages
attacking and defending.

| Win rate | Parent | `solo` | `nobomb` | `h995` |
|---|---|---|---|---|
| Fleet suite | 0.88 | **0.68** | 0.77 | 0.74 |
| Fleet 3 v 3 | 0.92 | **0.69** | 0.88 | 0.77 |
| Fleet 4 v 4 | 0.78 | 0.50 | 0.59 | 0.53 |
| Carrier battle | 0.89 | 0.70 | 0.75 | 0.66 |
| Station assault | 0.61 | **0.91** | 0.62 | **0.93** |
| 3 v 3, other pilot | 0.59 | 0.38 | 0.22 | **0.11** |

<!-- figure-idea: shared: the fleet suite. The sixteen line-ups drawn as rows of ship icons (fighter, strafer, gunship), 1 v 1 up to 4 v 4, uneven fights included. "Fleet suite" is a headline number in many pilot entries, and the picture shows what it covers. -->

The first five are against the script, about ± 0.05 (± 0.1 to 0.17 for the rows of one
fleet size, 3 v 3 and 4 v 4). Convoy escort stayed at 0.97 to 1.00 for all. The last row
is 3 v 3, unordered (no orders on the pilot's side), against a free
`followers_school_1052` (a followers pilot that went through
[go-to school](../2026-11-14-goto-school-2/results.md), drill-heavy training on go-to
orders, and our standard learned opponent, also flying with no orders), ± 0.03.

**Against the script, the bombers did it.** `solo` has bombers and no teammates. Its
fleet score is the lowest of the three, and in fleet 3 v 3 it fell from 0.92 to 0.69.
`nobomb` has the teammates and no bombers, and stayed level with its parent in 3 v 3
(0.88). The fleet suite has no bombers in it at all. Practice in the bomber has cost skill
in the hulls the pilot already flew, and fast. The quick evals show when: each number is
the fleet suite win rate against the script at that update.

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

The bomber practice in the other missions also bought all of the station assault gain: it
is what taught the pilots to attack the station. `nobomb` trained on the station assault
as often as the others, and flew the three bombers that mission always puts on the
attacking side, yet it won no more often than its parent.

**Against another pilot, both fell.** In 3 v 3 against `followers_school_1052`, `solo`
won 0.38, `nobomb` 0.22, and `h995`, with both changes, 0.11. `solo` fell within the
first 500 updates (0.27), like its fleet score. `nobomb` stayed between 0.33 and 0.59
through update 3,500, then dropped to 0.22 by 4,000 (quick evals ± 0.05). So neither
change alone explains this loss, and the two together are worse than either. What's
common to both is the station assault in the mix and simply more training on these
settings. The [plan](plan.md) had said in advance that if both arms fell, the cause would
most likely be one of those two, and this run can't separate them.

One more thing changed in `nobomb`: given orders (each ship sent at its nearest enemy),
it now wins the 3 v 3 more often than unordered (0.31 against 0.22). The parent and the
other arms win less, or no more, when ordered (the parent 0.23 against 0.59). Its
unordered fight got worse while its ordered one got better.

## The bomber and docking

The first two rows are the swap cost: the same matches played twice, once with a side's
first gunship and once with a bomber in its place, and the change in the side's result (0
means the swap costs nothing, a minus means the side wins less with the bomber). The next
two are dock drills, short practice scenarios in which a damaged ship is ordered home,
with a clear run (calm) or with enemies chasing it (under fire). The last two are real
matches, where the scripted commander recalls a damaged ship home. Every number from the
third row down is the share of attempts that ended with the ship docked.

<div data-figure="diagram" data-name="swap-test" data-caption="The parent and each arm flew every strike craft on both sides, in both runs."></div>

| Measure | Parent | `solo` | `nobomb` | `h995` |
|---|---|---|---|---|
| Swap cost, deathmatch | −0.16 | **+0.06** | −0.10 | −0.03 |
| Swap cost, carrier | −0.18 | −0.07 | −0.05 | −0.08 |
| Calm dock drills | 0.38 | 0.48 | 0.65 | **0.73** |
| Dock drills under fire | 0.14 | 0.24 | 0.24 | **0.34** |
| Recalls, carrier | 0.03 | 0.05 | 0.07 | 0.05 |
| Recalls, station | 0.07 | 0.06 | **0.13** | 0.08 |

The swap cost is ± 0.04 in deathmatches and ± 0.09 in carrier battles. Dock drills, calm
or under fire, are ± 0.08, match recalls ± 0.01 to 0.02 ("recalls" is the share of
recalls in matches that end in a dock).

`solo` learned the bomber as well as `h995` did: swapping a gunship for a bomber no longer
costs its side anything in a deathmatch. `nobomb` docks better than `solo`. Its station
recalls, 0.13, are the best of any learned pilot so far, though still far below the
script's 0.54. That may be partly a side effect. The network learns from rows, each one
ship's moment of play. Teammates fly a quarter of the learner's match slots and their
rows train nothing, so `nobomb` spent 18 in 100 of its training rows in drills, against
12 for `solo`.

## Wins above replacement: one new live pilot

WAR is played in matches like the live page's, with pilots dropped at random into the
ships, and a statistical fit gives each pilot its rating (0 is script level). This one
covered the live ten and the two new members: 5,760 matches, 1,440 in each live mission,
with commanders drawn from the live commander stable, the commanders the live page uses
([war.md](../../population/2026-11-sim6/war/fight-ablation/war.md)). The 95% interval is
the range the true WAR very likely lies in.

<div data-figure="diagram" data-name="war" data-caption="As in the horizon-bombers round, the live ten and the two new members over 5,760 matches. Compare these ratings with each other, not with that round's."></div>

| Pilot | WAR | 95% interval |
|---|--:|---|
| `kite_pay025_2211` | +11.6 | +8.9 to +14.3 |
| `dock_solo_4359` | +7.2 | +4.3 to +10.0 |
| `followers_dock_v8_2676` | +7.2 | +4.3 to +9.9 |
| `dock_nobomb_4198` | +6.0 | +3.3 to +8.8 |
| `kite_2205` | +5.5 | +2.6 to +8.5 |

The first is the top pilot this time, then `solo`, its parent, `nobomb`, and the last of
the twelve. `kite_pay025_2211` and `kite_2205` are followers trained in the
[kite drills](../2026-11-18-kite-drills/results.md), attack drills against an opponent
that backs away and fights back. Last round the bomber pilots rated 2.4 and 3.0 below this
parent. `solo` now rates level with it, and `nobomb` a little below. Under the no-gates
rule (a new pilot has no pass mark to meet: it joins the season and WAR alone decides who
flies live), WAR picks the live page: `dock_solo_4359` is ninth of twelve, a thousandth of
a win ahead of its parent, and joins the live ten. `kite_2205` drops to twelfth and leaves
it. That margin is far inside the noise, so this is a coin flip the rule settled, not a
better pilot. It does put a pilot that flies the bomber well on the live page, which has
flown bombers in every station assault. `dock_nobomb_4198` stays in the season as another
child of the parent. Each WAR is its own fit, so compare ratings within one table, not
across rounds.

## Next

- **A control arm:** the same parent and night with neither bombers nor teammates, only
  the station mix. If it also falls against `followers_school_1052`, the cause is the mix
  or more training on these settings, not the bombers.
- **Bombers at a lower share.** They pay in the station assault and cost in plain fights.
  Try 0.05 to 0.1 of strike slots (a match's places for small piloted ships) in place of
  0.2, or bombers only in drills.
- **Keep the drill share** (the fraction of training spent in drills) **matched** when
  comparing arms with and without teammates, so the docking comparison is fair.
- The [commander run](../2026-11-21-commander-long/results.md) paused at update 7,149 still
  waits for a stronger pilot list.
