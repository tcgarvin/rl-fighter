# New directions: a station to assault, a bomber, and whole-side pairings

Verdict: **PARTIAL**. Of the directions tried overnight, the new mission and the new
ships work: a station assault and a bomber are in the game (`SIM_VERSION` 9), balanced for
the scripts, and a pilot trained with them in the mix learns to fly the bomber and win the
assault, though it slips on the old missions the longer it trains. The kite drills, the
order-cost run carried over from the night before, passed: ordered pilots now hold their
own against a free one. Pairing each side with one commander and one pilot changed
nothing measurable. The hand rules show the station gives a commander decisions worth
0.13 to 0.19 of a match, but a learned commander did not find them: trained half a day,
it scores the same as giving no orders. Piracy is designed, not built.

<!-- summary: Overnight we tried several new directions for the game. We added a station for one side to assault and the other to defend, plus a new bomber ship, and pilots trained with them learned to fly the bomber and win the assault, though they got worse at the old missions the longer they trained. Giving each side one fixed commander and pilot instead of random pilots made no measurable difference, and a design for a piracy mission is written but not built. -->

The owner asked, on the night of 2026-11-18, for a new direction: a new scenario such as a
base assault or piracy, something more complex for the commanders to do; each side a
consistent commander and pilot pairing instead of random pilots ship by ship; and one to
three new ship types. This entry links the night's entries and says how each went. The
work ran on the laptop and on Beast (two GTX 1080 Ti) from 22:00 to 16:00.

| Direction | Entry | Outcome |
|---|---|---|
| What each order kind costs (the groundwork for any new commander task) | [order-kinds](../2026-11-19-order-kinds/results.md) | Go-to costs a fifth of an attack order; defend and rally depend on the hull |
| Kite drills (the order-cost run carried over from the night before) | [kite-drills](../2026-11-18-kite-drills/results.md) | **PASS**: ordered 0.42 to 0.47 against a free 1052, against 0.14 for the parent |
| Base assault: the station mission, the station and bomber hulls | [station-bomber](../2026-11-19-station-bomber/results.md) | Scripts balanced at 0.55 for the attacker; learned pilots 0.36 to 0.39 and barely fire torpedoes |
| Consistent commander and pilot a side | [pairing](../2026-11-19-pairing/results.md) | No interaction beyond what we knew; `?pairing=side` on the live page |
| What a commander can do in the station assault, by hand | [station-rules](../2026-11-19-station-rules/results.md) | Launch timing and the carrier's position beat no orders by 0.13 to 0.19; orders to fighters do not |
| A learned station commander | [station-commander](../2026-11-19-station-commander/results.md) | **FAIL**: both arms level with no orders (−0.06 to +0.04); both launch the reserve at 2 s |
| Pilots trained with the station and bomber in the mix | [station-mix](../2026-11-19-station-mix/results.md) | **PARTIAL**: station attack 0.50 → 0.87 against the parent, bomber as good as the gunship; old missions slip with training |
| Piracy, stealing cargo | [piracy-design](../2026-11-19-piracy-design/plan.md) | A design: disable, board by presence, carry out; reads as a convoy escort |

## The base assault

Team 0 defends a static `station` (1,600 hull, three flak and three gauss turrets, two
bays) with a picket and a reserve it launches. Team 1 jumps in with a carrier and eight
strike craft, three of them `bomber`s: slow, heavy, with a torpedo rack fixed to the nose
(90 m/s, 240 m, 150 damage), so the pilot aims the ship to aim the torpedo. There is no
autopilot; the bomber is flown through the same four actuators as every other hull.
The mission reads to the pilot and commander nets as a carrier battle or a convoy escort,
so the observation (587 inputs) did not change and every old mission replays bit for bit.

With scripts on both sides the attacker wins 0.55. The live pilots, untrained on it,
win 0.36 to 0.39 attacking, because they barely fire the torpedo: `followers_school_1052`
in a bomber hits its drill target 0.16 of the time, against 0.96 in the hull it drew.

Pilots trained with a quarter of their matches in the station assault and a fifth of
their strike slots in bombers (two seeds, from 1052):

| Checkpoint | Station attack vs 1052 | Bomber swap, 3 v 3 | Bomber dmg to capital ships | Carrier / convoy vs 1052 | Drill gate |
|---|---|---|---|---|---|
| `followers_school_1052` (parent) | 0.23 (both sides) | −0.28 | 38 | 0.50 / 0.50 | pass |
| `mix_s1` 725 | 0.50 | −0.11 | 139 | 0.48 / 0.47 | pass |
| `mix_s2` 725 | 0.54 | −0.14 | 122 | 0.46 / 0.45 | pass |
| `mix_s1` 2422 (final) | 0.87 | −0.09 | 262 | 0.42 / 0.46 | pass |
| `mix_s2` 2447 (final) | 0.86 | +0.12 | 343 | 0.46 / 0.41 | fail |

The script's bomber deals 305 to capital ships. The old-mission cells are 192 matches,
about ± 0.07.

Both seeds learned the new things: by the end they win 0.86 to 0.87 attacking the
station against their parent and fly the bomber as well as the gunship it replaces,
hitting capital ships as hard as the script. But the longer they trained, the more they
slipped on the old missions against their parent (0.31 to 0.48 at the finals, from 0.45
to 0.50 at update 725), and `mix_s2` fails the drill gate at the end. Only `mix_s2` 725
meets every bar. Flown by these pilots on both sides, the station falls 0.74 to 0.82 of
the time, against 0.55 for the scripts, so the mission would need rebalancing before it
goes into the rotation with them.

## Something for the commanders to do

The station assault was meant to give a commander decisions that matter. By hand, it
does: keeping the station's reserve docked until its hull is below 60% wins +0.19 over no
orders, and parking the attacker's carrier 170 m from the station once its hangar is
empty wins +0.13. Every rule that ordered the strike craft about was level with no orders
or worse, as in the fleet fights: the pilots still pay for being told where to fly.
The order-kinds measurements say where a commander's orders could still help: a go-to
costs 0.08 where an attack order costs 0.37, and defending wins gunship fights by 0.17 to
0.29 while losing fighter fights.

A learned commander, trained on the station assault for 11.5 hours in two arms (a new
net, and commander 3's quiet `live` line), found neither gain. Both score within noise
of no orders in both roles (−0.06 to +0.04) and 0.11 to 0.27 below the hand rules. Both
launch the station's reserve at 2 s, as the script does. The new net did learn to order
less, as commander 3 did, and that is all it learned. The likely reason is the action
space: holding the reserve means choosing "don't launch" at every decision for half a
minute, which a learner that explores by sampling almost never does, so it never sees
the payoff. A launch stance chosen once ("hold until the hull is below x") would make
holding one decision instead of a run of them.

## One commander and one pilot a side

Every ship on a side flown by the same pilot, under the same commander, scores what the
per-ship random draw does, within ±0.06. The one strong interaction is the one we knew:
orders cost a side up to 0.28 with three of the four pilots tested and nothing with
`f995_701`, which ignores them. The live page takes `?pairing=side`; it is not the default.

## Piracy

Designed, not built ([plan](../2026-11-19-piracy-design/plan.md)): pirates disable a
freighter, hold a ship beside it to take its cargo, and fly the cargo out through a jump
point. It is built from go-to orders, the cheap kind, and gives a commander facts its
pilots cannot see. It needs `SIM_VERSION` 10.

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

1. Put the station assault into the live rotation, and with which pilots. With today's
   live ten the attacker wins 0.36 to 0.39; with a station-mix pilot on both sides,
   0.74 to 0.82. Either way it wants rebalancing for the pilots that will fly it. A
   station-mix pilot (`mix_s1` 2422, or `mix_s2` 725, the one that meets every bar)
   could join the live list after a WAR round.
2. Make `?pairing=side` the default (it measured the same; it is a look, not a gain).
3. Change the script's launch logistics to the hand rules' (`hold_late`, `carrier_push`).
   This moves WAR's replacement level, so it wants a new season baseline.
4. Build piracy, which bumps `SIM_VERSION` to 10.
