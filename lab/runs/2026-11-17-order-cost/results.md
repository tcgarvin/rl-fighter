# An order costs a fleet fight whichever enemy it names

Verdict: **it is following an order, not the script's choice of target.** No rule of the
game changed (`SIM_VERSION` 8, the eighth version of the game's rules), and the game's
code needed no change.

<!-- summary: Our pilots lose fleet fights when they are given orders, and the question was why. We tried four ways of ordering one side against the same pilots with their orders hidden. Ordering each ship onto the enemy nearest it costs as much as the script's orders do. In the first 30 seconds the ordered pilots keep flying at the enemy while free pilots fall back, and once they meet, an ordered pilot shoots only its target and loses that duel: it is hit 80% harder by its target and lands almost nothing on the ships around it. -->

In a fleet fight (a team deathmatch: small ships only, and a side wins by destroying every
enemy, or by having more hull and shields left at the 90-second time limit), a side whose
pilots are given attack orders loses to the same pilots fighting on their own judgment,
and loses more the bigger the fleets. We wanted to know why: is the scripted commander naming bad targets, or does being ordered change how a
pilot flies? It is the order itself. Ordering each ship onto the enemy nearest it, the
one it would face anyway, costs as much as the script's choices. An ordered pilot flies
straight at its target while free pilots fall back, then shoots only that target and
loses the duel with it.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error (reinforcement learning). A commander, a
second network or a hand-written script, gives a side's ships orders. An attack order
names one enemy for a ship to go after. The [commander page](/commander/) explains how
it works.

<div data-figure="diagram" data-name="orders" data-caption="Every rule tested in this entry gives attack orders, except the control, which gives none. The ordered pilot sees which enemy to go after and still chooses how to fly at it."></div>

Two days earlier, [the third commander night](../2026-11-15-commander-3/results.md) found
that a side whose pilots get no orders beat every commander we had, and that new
commanders came level with it only by learning to give almost no orders. The measurements
in [that night's plan](../2026-11-15-commander-3/plan.md) ("Where the cost is") showed the
cost grows with the size of the fleet, shows up as ships lost in the first 30 seconds, and
is paid even by pilots that mostly ignore orders. Until an order is cheap to follow, no
commander can be worth having. The scripted commander also gives the orders in much of
pilot training. So this entry looks at what ordered pilots do in those first seconds.

## How we tested it

The same pilots fly both sides: the four that follow orders best
(`pilots_followers.json`), unless stated. The **ordered** side gets orders its pilots see,
from one of the rules below. The **unseen** side is the scripted commander with its orders
hidden from its own pilots, so they fight on their own judgment. Below we also call them
free pilots. The `none` rule below is an external commander, a test program outside the
game's own code that sends orders in, here sending none. The "ignorers" are a second list
(`pilots_ignorers.json`): three pilots of the `fighters_pay1` line (fighters bred mainly
to win fights, paid less for following orders), which follow an attack or defend order in
practice drills only two or three times in ten.

Each match is an even fight of k ships a side (2 v 2 or 3 v 3), all of one hull, or ship
type: fighter, strafer or gunship (the [hulls page](/hulls/) has them), 8 rosters
(line-ups) of each, each played with the ordered side on either team. **1,152 matches a row**, the same random
starts, rosters and pilot draws in every row, so two rows can be compared match by match
("paired"), which measures the difference between them more precisely than either score
alone. The ± is the margin of error, 1.96 standard errors: the true value is very likely
within that range.

The rules for the ordered side all give attack orders, at the moments the game lets a
commander act (every 2 s, from 2 s in). A squad is a group of ships that share one order,
and a centroid is a group's centre, the average of its ships' positions:

| Rule | Orders |
|---|---|
| `scripted` | The game's scripted commander: half the fleet on the enemy nearest the squad, half on the most damaged one within 300 m, both kept rather than chosen again |
| `nearest` | Every ship its own squad, on the enemy nearest *it*, chosen again every 2 s |
| `focus` | The whole side one squad, on the enemy nearest its centroid, kept until it dies |
| `near250` | As `nearest`, but no order while that enemy is farther than 250 m |
| `none` | An external commander that gives no orders: the control |

<div data-figure="diagram" data-name="order-cost" data-caption="This entry built the test. The same four order-following pilots fly both sides, and the fights are 2 v 2 as well as 3 v 3. Each rule in the table above takes the place of run 1, and the control that gives no orders is run 2."></div>

## Verdict in detail

An attack order on each ship's own nearest enemy (`nearest`) costs a 3 v 3 as much as the
scripted commander's orders. The ordered side wins 0.22 of its matches against the unseen side under `nearest` and 0.24
under the script's orders, where the `none` control, given no orders at all, wins 0.52. Here and
below, an order's "cost" is that drop in the share of matches won, out of 1. An ordered
pilot does two things a free one does not. It keeps closing while free pilots fall back.
Once they meet, it shoots only its target and loses the duel with it.

## Is it the target choice?

Each score is the share of matches the ordered side won against the unseen side, so 0.50
is an even fight. The last column is that score minus the `none` row's, on the same
matches: what ordering that way costs in share of matches won.

| k v k | Rule | Ordered side's score | Minus no orders (paired) |
|---|---|---|---|
| 2 v 2 | `scripted` | 0.333 ± 0.026 | −0.165 ± 0.036 |
| 2 v 2 | `nearest` | 0.404 ± 0.026 | −0.094 ± 0.037 |
| 2 v 2 | `near250` | 0.411 ± 0.026 | −0.087 ± 0.032 |
| 2 v 2 | `focus` | 0.292 ± 0.024 | −0.206 ± 0.034 |
| 2 v 2 | `none` | 0.498 ± 0.026 | |
| 3 v 3 | `scripted` | 0.242 ± 0.025 | −0.279 ± 0.038 |
| 3 v 3 | `nearest` | **0.220 ± 0.024** | −0.300 ± 0.036 |
| 3 v 3 | `near250` | 0.330 ± 0.027 | −0.191 ± 0.032 |
| 3 v 3 | `focus` | 0.219 ± 0.024 | −0.302 ± 0.037 |
| 3 v 3 | `none` | 0.521 ± 0.029 | |
| *The ignorers (`pilots_ignorers.json`), 3 v 3:* | | | |
| 3 v 3 | `scripted` | 0.235 ± 0.024 | −0.227 ± 0.037 |
| 3 v 3 | `nearest` | 0.250 ± 0.025 | −0.211 ± 0.037 |
| 3 v 3 | `none` | 0.461 ± 0.028 | |

- **In a 3 v 3 the target does not matter.** Each ship on its own nearest enemy, the whole
  side on one, and the script's split all cost the same, about 0.28 to 0.30.
- **In a 2 v 2 the choice is a part of it.** `nearest` costs about half what the script
  does (0.07 ± 0.03 better, paired), and focus fire (`focus`) costs more. Still, ordering a ship
  onto the enemy nearest it costs 0.09.
- **The control holds:** an "ordered" side given no orders (`none`) scores 0.50 and 0.52.
- **The ignorers pay the same way.** Ordering them onto their nearest enemy costs about
  what the script's orders do.
- **Holding the order back until the fight arrives** (`near250`) saves about a third of
  the 3 v 3 cost, and nothing in the 2 v 2. The ships were under an order only 17% to
  25% of the time and still lost 0.19.

## The first 30 seconds

Next we recorded what every ship did in the first 30 seconds of the 3 v 3s. Each column
is one side: under `nearest` and under `scripted`, the ordered side and the unseen side
it fought, and under `none` either side. A ship's "target" is its standing order's
target. On the unseen side that is the order the script chose and hid, which its pilot
never saw, so those numbers show what a pilot does about that enemy when not told to.
"Ships lost" is per side per match. Rows about time ("in arc", "retreating") are shares
of each ship's time. Damage is per match, hull and shield together. "In arc":
for the fighter and strafer, whose gun is fixed to the nose, the nose points within 10°
of the enemy and the enemy is inside the gun's range. For the gunship, whose turrets reach nearly all round, the enemy
only has to be inside 230 m. "Retreating" is moving away from the enemy fleet faster than
5 m/s. "Behind its beam" means from the rear half of the ship, more than 90° off its nose:

<!-- figure-idea: shared: gun arc and beam. Top view of a fighter with its narrow 10° nose arc out to gun range, a gunship with its all-round 230 m circle, and the line across each ship's beam separating front from rear. Makes "in arc" and "behind its beam" readable at a glance in this table and later order entries. -->

| | `nearest` ordered | `nearest` unseen | `scripted` ordered | `scripted` unseen | `none`, either side |
|---|---|---|---|---|---|
| Ships lost | **0.93** | 0.47 | **0.95** | 0.53 | 0.56 |
| Speed toward the enemy fleet (m/s) | **+12.6** | −4.5 | +12.7 | −3.9 | +0.9 |
| Speed toward its own target (m/s) | +16.2 | −6.7 | | | |
| Time spent retreating | 0.17 | 0.52 | | | 0.39 |
| Target in arc | 0.123 | 0.098 | 0.096 | 0.100 | |
| Another enemy in arc | **0.009** | 0.044 | 0.039 | 0.045 | |
| Any enemy in arc | 0.126 | 0.132 | 0.131 | 0.136 | 0.078 |
| Damage taken from its target | **127** | 71 | 99 | 71 | |
| Damage taken from other enemies | 24 | 32 | 59 | 34 | |
| Damage taken from behind its beam | 27 | 13 | 29 | 13 | 8 |
| Damage dealt to its target | 101 | 112 | 79 | 114 | |
| Damage dealt to other enemies | **2** | 40 | 27 | 44 | |
| Hits per second with an enemy in arc | 3.1 | 4.0 | 3.1 | 4.1 | 4.4 |
| Share of trigger time with an enemy in arc | 0.46 | 0.54 | 0.49 | 0.54 | 0.47 |
| Landed the match's first hit | 0.38 | 0.59 | 0.34 | 0.64 | 0.45 |

Over time, 3 v 3, in 2-second steps. "Gap" is the distance between the two fleets'
centres. "Toward" is the side's average speed toward the other fleet, negative when it is
falling back:

| t (s) | 0 | 4 | 6 | 8 | 12 | 16 | 20 | 24 | 28 |
|---|---|---|---|---|---|---|---|---|---|
| `none`: gap (m) | 482 | 399 | 476 | 500 | 486 | 476 | 455 | 443 | 430 |
| `none`: either side toward the other (m/s) | 15 | −22 | −16 | −3 | −1 | 0 | 3 | 5 | 6 |
| `nearest`: gap (m) | 482 | 365 | 396 | 395 | 358 | 333 | 302 | 278 | 261 |
| `nearest`: ordered toward (m/s) | 15 | 7 | 15 | 17 | 11 | 12 | 11 | 9 | 7 |
| `nearest`: unseen toward (m/s) | 15 | −29 | −27 | −16 | −9 | −5 | −0 | 3 | 4 |
| `nearest`: ordered ships lost so far | 0 | 0 | 0 | 0 | 0.02 | 0.19 | 0.47 | 0.74 | 0.93 |
| `nearest`: unseen ships lost so far | 0 | 0 | 0 | 0 | 0.01 | 0.05 | 0.16 | 0.33 | 0.47 |

<div data-figure="diagram" data-name="charge-and-duel" data-caption="The 3 v 3 rows of the two tables above, drawn for the rule that sends each ship at the enemy nearest it. The comparison box is the control, with no orders on either side."></div>

The first ship lost in each match, 3 v 3. The first two rows are shares of matches, the
next two shares of those first losses, and the last a count:

| | `nearest` | `scripted` | `none` |
|---|---|---|---|
| The ordered side lost it | **0.68** | 0.67 | 0.42 |
| The unseen side lost it | 0.18 | 0.18 | 0.42 |
| An ordered victim was killed by its own target | 0.73 | 0.57 | |
| The killer was behind the victim's beam: ordered / unseen victim | 0.31 / 0.40 | 0.30 / 0.34 | 0.26 / 0.31 |
| Enemies that hit it in its last 3 s | 1.6 | 1.6 | 1.6 |

What this says, in order:

1. **Free pilots open by falling back.** With no orders on either side, both fleets close
   to about 370 m, then both turn away at about 20 m/s, sit near 500 m by 8 s and only
   slowly come back. Almost no ship is lost before 14 s.
2. **An ordered pilot does not fall back.** From the first order at 2 s it keeps flying at
   its target, at 12 to 16 m/s on average. The free side keeps falling back, faster than
   it does against free pilots (−29 m/s). It mostly turns and runs: of its time
   retreating, a third has its nose on the nearest enemy. So the fight happens earlier,
   and on the free side's terms. The free side lands the first hit in 0.59 to 0.64 of
   matches.
3. **Once they meet, the ordered pilot shoots only its target and loses that duel.** It
   has a non-target enemy in its gun arc a fifth as often as the free pilot (0.009 and
   0.044) and lands 2 damage a match on other enemies, against 40. Its total time with
   some enemy in arc is the same (0.126 and 0.132). It is hit by its own target 80% harder
   than the free pilot is (127 and 71) and lands less on it (101 and 112). Its shooting is
   worse too: 3.1 hits per second in arc against 4.0, and less of its trigger time has
   an enemy in arc (0.46 and 0.54). The free pilot takes whatever shot comes, chases
   nothing, and wins.
4. **Being shot in the back by the other enemies is only a small part of it.** That was
   our guess, and it was only partly right. Ordered pilots take twice the damage from behind (27 and 13), and
   under the script's split they take more from non-targets (59 and 34). But with
   `nearest` they take *less* from other enemies than free pilots do (24 and 32). The
   first ship lost was usually killed by the very enemy it was sent at (0.73). It was hit
   by as many enemies in its last 3 s as a free victim was (1.6), and its killer was in
   front of its beam as often.
5. **`near250` takes away the charge but not the duel.** Ordered only once the nearest
   enemy is inside 250 m, the side opens like a free one (+1.3 m/s toward the enemy, the
   control's +0.9). Then it still loses ships faster (0.68 against 0.43), still lands 3
   damage a match on other enemies against 28, and is hit harder by its target (90 and
   57). The charge explains about a third of the 3 v 3 cost; the fixed target, the rest.

The 2 v 2 is the same story, milder. With `nearest` the ordered side advances at +11.9 m/s
against −2.1, loses 0.53 ships to 0.44, and lands 1 damage on other enemies against 14.
Per-pilot sums are in the JSON output (`sides.<side>.by_pilot`). All seven pilots,
followers and ignorers, advance more, take more and deal less when ordered. The follower that advances
least under orders (`followers_pay3_810`, +6 m/s against +13 to +19 for the others) gives
up the fewest extra ships.

The ignorers do it too (`tables_ignorers.md`). Ordered onto their nearest enemy, they
close at +7.5 m/s against +2.5, take 201 from their target against 131, and land 6 on
other enemies against 68. They also hold the trigger far more with nothing in arc: the
share of trigger time with an enemy in arc is 0.46 for them ordered and 0.67 free.

## What we learned

- **The order itself costs, not the script's targets.** A commander cannot pick its way
  out of it. Giving each ship the enemy it would face anyway costs a 3 v 3 as much as the
  script's choices.
- **To these pilots, an attack order means "go straight at it and shoot only it".** That
  is what the drills ask: a drill counts as a success when damage lands on the named
  target and the pilot goes to its side. Hits on others are paid but never needed. Against free pilots it loses
  twice: they give ground while the ordered ship closes, and they take shots of
  opportunity while it holds out for its one target.
- **No pilot has trained against this.** Every training match puts both sides under the
  same condition (`docs/PILOT_TRAINING.md` §3): both ordered, or both with orders
  hidden. So an ordered pilot has only met ordered pilots, who also close, and free pilots have only
  met free ones. Pressing into a side that falls back and waits is never punished in
  training. Most of a pilot's training under orders comes from drills, the short practice
  scenarios: 78% of its ordered training episodes for three of the four followers, and
  about half for the fourth and for the ignorers. Drills pay no match result, and their enemies are scripts.
- **Not tested:** whether it is the drills' share of training that makes ordered pilots
  reckless. The ignorers trained with a far smaller drill share and pay the same cost, which argues
  against it.

## Next

For the pilot phase, the next nights of training pilots rather than commanders, aimed at
making an order cheap to follow:

- **Mixed-condition matches.** One side ordered, the other with its orders hidden, the
  pilot being trained on either side, paid for the match result. This is the matchup the
  cost shows up in, and the one no pilot has trained in. A free side that falls back and picks its shots
  is the opponent an ordered pilot has to learn to beat.
- **An attack order should not stop the pilot shooting others.** Order pay, the reward
  for following an order, is damage on the target. Check that it does not make a hit on another enemy worth less
  than taking no shot. Paying the order as a bonus on top of normal hit pay is the intent
  (`docs/PILOT_TRAINING.md` §2), so measure what the training code actually pays.
- **An attack drill where the target falls back** and other enemies cross the pilot's nose.
  Success stays the same (damage on the named target), with being destroyed costing
  reward, so
  the drill rewards taking the target without being taken by it.
- **The test to keep:** `order_rules.py --rule nearest --k 3` against `--rule none` on the
  same random starts (1,152 matches each, about 3.5 minutes each on Beast, the lab's
  training desktop, at 4 threads). A pilot for whom orders are cheap scores near 0.50 there. These pilots score 0.22.

## Files

The scripts and outputs, for anyone repeating the work.

- `order_rules.py`: plays one rule's 1,152 matches with the telemetry and writes
  `out/k<k>_<rule>[_ign].json` (scores per match, per-side sums, per-pilot sums, the
  first loss in each match, a 2-s timeline).
- `analyze.py [tag]`: the tables. `tables.md` is the followers', `tables_ignorers.md`
  (`_ign`) the ignorers'.
- `run.sh` (four rules, 2 v 2 and 3 v 3), `run2.sh` (`near250`, ignorers) and `run3.sh`
  (3 v 3 `nearest` and `none` again with the retreat measures; same seeds, same scores).
  Their logs are the `.out` files.
- The game's existing Python interface (its bindings) gave everything needed.
  `render_state` has positions, velocities and headings. The `hits` buffer has shooter, target and damage for each hit.
  `order_tracks` has every ship's standing order, the hidden ones included. External
  commands go through `submit_command` on the slow tick, the commander's 2-second turn.
