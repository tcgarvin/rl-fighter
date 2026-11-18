# An order costs a fleet fight whichever enemy it names

Verdict: **it is following an order, not the script's choice of target.** An attack
order on each ship's own nearest enemy costs a 3 v 3 as much as the scripted commander's
orders (0.22 and 0.24 against the side with no orders, which a no-order control puts at
0.52). An ordered pilot does two things a free one does not. It keeps closing while free
pilots fall back. Once they meet, it shoots only its target and loses the duel with it.
No rule of the game changed (`SIM_VERSION` 8), and no Rust change was needed.

<!-- summary: The pilots lose fleet fights when they are given orders, and the question was why. We tried four ways of ordering one side against the same pilots with their orders hidden. Ordering each ship onto the enemy nearest it costs as much as the script's orders do. In the first 30 seconds the ordered pilots keep flying at the enemy while free pilots fall back, and once they meet, an ordered pilot shoots only its target and loses that duel: it is hit 80% harder by its target and lands almost nothing on the ships around it. -->

The background is in [commander 3](../2026-11-15-commander-3/results.md) ("Next") and its
plan's "Where the cost is". The same pilots fly both sides, the four followers
(`pilots_followers.json`) unless stated. The **ordered** side gets orders its pilots see,
from one of the rules below. The **unseen** side is the eval's `unseen`: the scripted
commander, its orders hidden from its own pilots. Rosters are even k v k of one hull
(fighter, strafer, gunship, 8 rosters each), each played with the ordered side on either
team. **1,152 matches a row**, the same seeds, rosters and pilot draws in every row, so rows
pair match by match. The ± is 1.96 standard errors.

The rules for the ordered side all give attack orders, on the sim's slow tick (every 2 s,
from t = 2 s):

| Rule | Orders |
|---|---|
| `scripted` | The sim's scripted commander: half the fleet on the enemy nearest the squad, half on the most damaged one within 300 m, both sticky |
| `nearest` | Every ship its own squad, on the enemy nearest *it*, chosen again every 2 s |
| `focus` | The whole side one squad, on the enemy nearest its centroid, kept until it dies |
| `near250` | As `nearest`, but no order while that enemy is farther than 250 m |
| `none` | An external commander that gives no orders: the control |

## Is it the target choice?

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
  does (0.07 ± 0.03 better, paired), and focus fire costs more. Still, ordering a ship
  onto the enemy nearest it costs 0.09.
- **The control holds:** an ordered side with no orders scores 0.50 and 0.52.
- **The ignorers pay the same way.** Ordering them onto their nearest enemy costs about
  what the script's orders do.
- **Holding the order back until the fight arrives** (`near250`) saves about a third of
  the 3 v 3 cost, and nothing in the 2 v 2. The ships were under an order only 17% to
  25% of the time and still lost 0.19.

## The first 30 seconds

Per side, 3 v 3. A ship's "target" is its standing order's target. On the unseen side
that is the order the script chose and hid, which its pilot never saw. Damage is per
match, hull and shield together. "In arc": the fighter's and strafer's fixed nose gun
points within 10° of the enemy, which is inside the gun's range. For the gunship, whose
turrets reach nearly all round, the enemy only has to be inside 230 m.

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

Over time, 3 v 3 (2-second bins; "gap" is the distance between the fleets' centroids):

| t (s) | 0 | 4 | 6 | 8 | 12 | 16 | 20 | 24 | 28 |
|---|---|---|---|---|---|---|---|---|---|
| `none`: gap (m) | 482 | 399 | 476 | 500 | 486 | 476 | 455 | 443 | 430 |
| `none`: either side toward the other (m/s) | 15 | −22 | −16 | −3 | −1 | 0 | 3 | 5 | 6 |
| `nearest`: gap (m) | 482 | 365 | 396 | 395 | 358 | 333 | 302 | 278 | 261 |
| `nearest`: ordered toward (m/s) | 15 | 7 | 15 | 17 | 11 | 12 | 11 | 9 | 7 |
| `nearest`: unseen toward (m/s) | 15 | −29 | −27 | −16 | −9 | −5 | −0 | 3 | 4 |
| `nearest`: ordered ships lost so far | 0 | 0 | 0 | 0 | 0.02 | 0.19 | 0.47 | 0.74 | 0.93 |
| `nearest`: unseen ships lost so far | 0 | 0 | 0 | 0 | 0.01 | 0.05 | 0.16 | 0.33 | 0.47 |

The first ship lost in each match, 3 v 3:

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
   an enemy in arc (0.46 and 0.54). The free pilot takes whatever shot comes, chases nothing, and wins.
4. **It is mostly not about being shot in the back by the others.** That was the guess,
   and it was half right. Ordered pilots take twice the damage from behind (27 and 13), and
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
Per-pilot sums are in the JSON (`sides.<side>.by_pilot`). All seven pilots, followers and
ignorers, advance more, take more and deal less when ordered. The follower that advances
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
  is what the drills ask: the pass condition is damage on the named target and going to
  its side. Hits on others are paid but never needed. Against free pilots it loses
  twice: they give ground while the ordered ship closes, and they take shots of
  opportunity while it holds out for its one target.
- **No pilot has trained against this.** Every training match puts both sides under the
  same condition (`docs/PILOT_TRAINING.md` §3): both ordered, or both hidden. So an
  ordered pilot has only met ordered pilots, who also close, and free pilots have only
  met free ones. Pressing into a side that falls back and waits is never punished in
  training. Drills, where most ordered experience comes from (78% of the ordered episodes
  for three of the four followers, about half for the fourth and for the ignorers), pay no match result, and their enemies are
  scripts.
- **Not tested:** whether it is the drills' share that makes ordered pilots reckless. The
  ignorers trained with a far smaller drill share and pay the same cost, which argues
  against it.

## Next

For the pilot phase that makes an order cheap to follow:

- **Mixed-condition matches.** One side ordered, the other with its orders hidden, the
  learner on either side, match result paid. This is the matchup the cost shows up in,
  and the one no pilot has trained in. A free side that falls back and picks its shots
  is the opponent an ordered pilot has to learn to beat.
- **An attack order should not stop the pilot shooting others.** Order pay is damage on
  the target. Check that it does not make a hit on another enemy worth less than taking
  no shot. Paying the order as a bonus on top of normal hit pay is the intent (§2), so
  measure what the trainer actually pays.
- **An attack drill where the target falls back** and other enemies cross the pilot's nose.
  The pass condition stays the same (damage on the named target), with death charged, so
  the drill rewards taking the target without being taken by it.
- **The test to keep:** `order_rules.py --rule nearest --k 3` against `--rule none` on the
  same seeds (1,152 matches each, about 3.5 minutes each on Beast at 4 threads). A pilot
  for whom orders are cheap scores near 0.50 there. These pilots score 0.22.

## Files

- `order_rules.py`: plays one rule's 1,152 matches with the telemetry and writes
  `out/k<k>_<rule>[_ign].json` (scores per match, per-side sums, per-pilot sums, the
  first loss in each match, a 2-s timeline).
- `analyze.py [tag]`: the tables. `tables.md` is the followers', `tables_ignorers.md`
  (`_ign`) the ignorers'.
- `run.sh` (four rules, 2 v 2 and 3 v 3), `run2.sh` (`near250`, ignorers) and `run3.sh`
  (3 v 3 `nearest` and `none` again with the retreat measures; same seeds, same scores).
  Their logs are the `.out` files.
- What the bindings give is enough. `render_state` has positions, velocities and
  headings. The `hits` buffer has shooter, target and damage for each hit.
  `order_tracks` has every ship's standing order, the hidden ones included. External
  commands go through `submit_command` on the slow tick.
