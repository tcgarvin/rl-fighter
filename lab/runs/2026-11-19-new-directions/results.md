# New directions: a station to assault, a bomber, and whole-side pairings

This is the overview of one night, 2026-11-18 to 19, when the owner asked for new
directions: a new kind of mission, more for the commanders to decide, each side flown by
one fixed commander and pilot, and new ships. In short, the new mission and the new
ships work. We added a station assault (one side defends a static station, the other
attacks it) and a bomber, a slow ship with a torpedo fixed to its nose. Pilots trained
with them in the mix learned to fly the bomber and win the assault, but got worse at the
old missions the longer they trained. The station gives a commander decisions worth
winning matches with, but a learned commander did not find them. Pairing each side with
one commander and one pilot made no measurable difference. Each part has its own entry, linked below.

Verdict: **PARTIAL**. The new mission and ship work and can be learned, but not yet
without cost to the old missions, and the learned commander found nothing. The game's
rules moved to `SIM_VERSION` 9 (the ninth version) for the new mission and ship.

<!-- summary: Overnight we tried several new directions for the game. We added a station for one side to assault and the other to defend, plus a new bomber ship, and pilots trained with them learned to fly the bomber and win the assault, though they got worse at the old missions the longer they trained. Giving each side one fixed commander and pilot instead of random pilots made no measurable difference, and a design for a piracy mission is written but not built. -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a **pilot**, that learned to fly by trial and error ([/pilot/](/pilot/)). Each side can
also have a **commander**, a second network or a script that sees the whole side and
gives its ships orders ([/commander/](/commander/)). Until this night there were three
missions. In team deathmatch (a "fleet fight"), 1 to 4 small ships a side fight until one
side is destroyed. In a carrier battle, each side has a carrier that launches its strike
craft (the small piloted ships), and a side wins by destroying the enemy carrier. In a
convoy escort, one side's escorts guard freighters flying to a jump point and the other
side attacks them.

The week before had kept finding the same thing. Pilots fight worse when given orders:
told to attack an enemy, a pilot charges it and loses the duel
([the order-cost night](../2026-11-17-order-cost/results.md)). Training the pilots in
matches where only one side sees its orders did not change that
([mixed orders](../2026-11-18-mixed-orders/results.md)). The best learned commanders had
learned to give almost no orders ([commander 3](../2026-11-15-commander-3/results.md)).
So in a fleet fight a commander had nothing useful to do. The owner asked, on the night
of 2026-11-18, for a new direction: a new scenario such as a base assault or piracy,
something more complex for the commanders to do, each side a consistent commander and
pilot pairing instead of random pilots ship by ship, and one to three new ship types. The
work ran on the laptop and on Beast (the lab's desktop with two GTX 1080 Ti graphics
cards) from 22:00 to 16:00.

## The night's entries

Each row is one entry from the night, with its outcome in a line. "1052" is
`followers_school_1052`, the best order-following pilot we had (from the followers
family, bred to fight and follow orders, after go-to school), used as the reference
pilot in several of these. A pilot's name ends with the training update (round of
training) it was saved at.

| Direction | Outcome |
|---|---|
| [Order kinds](../2026-11-19-order-kinds/results.md) | An order to fly to a point (go-to) costs about a fifth of what an attack order does; defend orders and go-tos back to a rally point cost much in some hulls and help in others |
| [Kite drills](../2026-11-18-kite-drills/results.md) | **PASS**: ordered 0.42 to 0.47 against a free 1052, against 0.14 for the parent |
| [Base assault](../2026-11-19-station-bomber/results.md) | Scripts balanced at 0.55 for the attacker; learned pilots 0.36 to 0.39 and barely fire torpedoes |
| [Pairing by side](../2026-11-19-pairing/results.md) | Flying a whole side with one pilot under one commander is worth no more than its parts; the page's option to do so was then removed |
| [Station hand rules](../2026-11-19-station-rules/results.md) | Launch timing and the carrier's position beat no orders by 0.13 to 0.19; orders to fighters do not |
| [Learned commander](../2026-11-19-station-commander/results.md) | **FAIL**: both versions trained score level with no orders (−0.06 to +0.04); both launch the station's reserve ships at once (2 s) |
| [Station-mix pilots](../2026-11-19-station-mix/results.md) | **PARTIAL**: station attack 0.50 → 0.87 against the parent, bomber as good as the gunship; old missions slip with training |
| [Piracy](../2026-11-19-piracy-design/plan.md) | A design, not built: pirates disable a freighter, take its cargo by staying beside it, and fly it out |

The win rates and differences here and below are shares of matches won, from 0 to 1
(0.5 is an even fight). The kite drills were a run carried over from the night before,
one of several trying to make orders cheaper for pilots. Pilots practised attacks on a
target that backs away and shoots back. "Ordered 0.42 to 0.47" is the share of
three-a-side fights they won when ordered onto the nearest enemy, against 1052 flying
with no orders. The hand rules are a simple hand-written commander, tested on the new
station.

<!-- figure-idea: shared: the four missions side by side from above (deathmatch, carrier battle, convoy escort, and the new station assault), who wins and how in each; it would let a reader of this overview see what was added and why it reads to the networks as a carrier battle or a convoy. -->

## The base assault

The mission and its balance are in [the station and bomber entry](../2026-11-19-station-bomber/results.md).
Team 0 defends a static `station` (1,600 hull, three flak and three gauss turrets, two
bays) with a picket (strike craft already out) and a reserve it launches. Team 1 jumps in
with a carrier and eight strike craft, three of them `bomber`s: slow, heavy, with a
torpedo rack fixed to the nose (90 m/s, 240 m, 150 damage), so the pilot aims the ship to
aim the torpedo. There is no autopilot: the pilot flies the bomber with the same direct
controls as every other ship, so aiming the torpedo is a skill it has to learn. The mission reads to the pilot and commander nets as a
carrier battle or a convoy escort, so the observation (the 587 numbers a pilot sees each
moment) did not change and every old mission replays bit for bit.

With scripts on both sides the attacker wins 0.55. The live pilots (the ten the live page
draws from), untrained on it, win 0.36 to 0.39 attacking, because they barely fire the
torpedo. In an attack drill (a short practice scenario with a named target), 1052 in a
bomber damages the target 0.16 of the time, against 0.96 in the hulls it usually flies.

[The station-mix run](../2026-11-19-station-mix/results.md) then trained pilots with a
quarter of their matches in the station assault and a fifth of their strike-craft slots in
bombers, in two copies from 1052 that differ only in their random seed (`mix_s1`,
`mix_s2`). In the table, each row is a checkpoint (a saved copy of the network). "Station
attack vs 1052" is the share of assaults it wins attacking a 1052 defence (for the parent,
1052 on both sides). "Bomber swap" is how much a side's score changes when one of its
gunships becomes a bomber flown by the same pilot, in win rate. "Bomber dmg" is each
bomber's damage to capital ships a match. "Carrier / convoy / 3 v 3" is its share of
those matches won against 1052, where 0.5 is even. The drill gate is a fixed set of pass
marks on order-following practice scenarios. The plan's bars (pass marks) were: station
attack at least 0.45, bomber swap better than −0.15, at least 0.45 on each of carrier,
convoy and 3 v 3, and the drill gate passed.

| Checkpoint | Station attack vs 1052 | Bomber swap, 3 v 3 | Bomber dmg to capital ships | Carrier / convoy / 3 v 3 vs 1052 | Drill gate |
|---|---|---|---|---|---|
| `followers_school_1052` (parent) | 0.23 (both sides) | −0.28 | 38 | 0.50 / 0.50 / 0.50 | pass |
| `mix_s1` 725 | 0.50 | −0.11 | 139 | 0.48 / 0.47 / 0.42 | pass |
| `mix_s2` 725 | 0.54 | −0.14 | 122 | 0.46 / 0.45 / 0.50 | pass |
| `mix_s1` 2422 (final) | 0.87 | −0.09 | 262 | 0.42 / 0.46 / 0.48 | pass |
| `mix_s2` 2447 (final) | 0.86 | +0.12 | 343 | 0.46 / 0.41 / 0.31 | fail |

The script's bomber deals 305 to capital ships. The carrier and convoy cells are 192
matches, about ± 0.07 (the margin of error: the true value very likely lies within that
range). The 3 v 3 cells are only 48 matches, about ± 0.14.

Both seeds learned the new things: by the end they win 0.86 to 0.87 attacking the
station against their parent and fly the bomber as well as the gunship it replaces,
hitting capital ships as hard as the script. But the longer they trained, the more they
slipped on the old missions against their parent (0.31 to 0.48 at the finals, from 0.42
to 0.50 at update 725), and `mix_s2` fails the drill gate at the end. Only `mix_s2` 725
meets every bar: `mix_s1` 725 misses the 3 v 3 (0.42). Flown by these pilots on both sides, the station
falls 0.74 to 0.82 of the time, against 0.55 for the scripts, so the mission would need
rebalancing before it goes into the rotation with them.

That evening the owner asked for a bigger station and a second attacking capital ship,
which became [the citadel and the dreadnought](../2026-11-19-citadel-dreadnought/results.md).

## Something for the commanders to do

The station assault was meant to give a commander decisions that matter. By hand, it
does ([the hand-rule test](../2026-11-19-station-rules/results.md)): keeping the
station's reserve docked until its hull is below 60% wins +0.19 over no orders, and
parking the attacker's carrier 170 m from the station once its hangar is empty wins
+0.13. Every rule that ordered the strike craft about was level with no orders or worse,
as in the fleet fights: the pilots still pay for being told where to fly. The
[order-kinds measurements](../2026-11-19-order-kinds/results.md) say where a commander's
orders could still help: in 3 v 3 fights, a go-to (fly to a point) lowers a side's win
rate by 0.08 where an attack order lowers it by 0.37, and defending wins gunship fights by 0.17 to 0.29 while losing fighter fights.

A [learned commander](../2026-11-19-station-commander/results.md), trained on the station
assault for 11.5 hours in two arms (two versions trained side by side: a new net, and
a commander from [commander 3](../2026-11-15-commander-3/results.md)'s night that already
gave almost no orders), found neither
gain. Both score within noise of no orders in both roles (−0.06 to +0.04) and 0.11 to
0.27 below the hand rules. Both launch the station's reserve at 2 s, as the script does.
The new net did learn to order less, as commander 3 did, and that is all it learned. The
likely reason is the action space (the way its choices are set up): holding the reserve
means choosing "don't launch" at every decision for half a minute, which a learner that
explores by sampling almost never does, so it never sees the payoff. A launch stance
chosen once ("hold until the hull is below x") would make holding one decision instead
of a run of them.

## One commander and one pilot a side

[The pairing test](../2026-11-19-pairing/results.md): every ship on a side flown by the
same pilot, under the same commander, scores what the per-ship random draw does, within
±0.06. The one strong interaction is the one we knew: orders lower a side's win rate by up to 0.28 with
three of the four pilots tested and nothing with `f995_701`, a strong fighter (the founder of the fighters family) that
ignores them. The live page had a `?pairing=side` option for a day; it was removed after this
result, at the owner's call.

## Piracy

Designed, not built ([plan](../2026-11-19-piracy-design/plan.md)): pirates disable a
freighter, hold a ship beside it to take its cargo, and fly the cargo out through a jump
point. It is built from go-to orders, the cheap kind, and gives a commander facts its
pilots cannot see. It needs `SIM_VERSION` 10. (That number went to the citadel and the
dreadnought the same evening, so piracy would now come in a later version.)

## What we learned

- **A new mission is cheap when it reads as an old one.** The station reuses the carrier
  battle's and convoy's inputs, so every pilot and commander could play it on day one,
  and the old missions are untouched.
- **A new hull needs training, not just balance.** The bomber was fair for the script
  and a loss for every learned pilot until it was in their training mix.
- **Commanders matter through the decisions pilots cannot make.** Launches and the
  carrier's position pay; telling fighters where to fly still costs.
- **A decision worth making has to be one a learner can stumble on.** The station's
  reserve is worth +0.19 held back, but holding it is a long run of "don't launch", and
  the learned commanders never tried it.
- **Pairing is not where the value is.** A fixed commander and pilot a side are worth
  the sum of their parts.

## Decisions for the owner

1. Put the station assault into the live rotation, and with which pilots. Answered:
   yes, with all the live pilots and no special selection; it rotates since 2026-11-19. With today's
   live ten the attacker wins 0.36 to 0.39; with a station-mix pilot on both sides,
   0.74 to 0.82. Either way it wants rebalancing for the pilots that will fly it. A
   station-mix pilot (`mix_s1` 2422, or `mix_s2` 725, the one that meets every bar)
   could join the live list after a WAR round (WAR, wins above replacement, is how
   pilots are picked for the live page: how many more matches in 100 a side wins with
   that pilot flying instead of the script).
2. Make `?pairing=side` the default (it measured the same; it is a look, not a gain).
   Answered: no, and the option is removed.
3. Change the script's launch logistics to the hand rules' (`hold_late`, which holds the
   station's reserve until its hull is below 60%, and `carrier_push`, which brings the
   attacking carrier in to 170 m). The script is the yardstick WAR measures every pilot
   against, so changing it would mean starting the ratings over. Answered: no.
4. Build piracy, which bumps `SIM_VERSION` to 10. Answered: not yet.
