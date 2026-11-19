# What go-to and defend orders cost a fleet fight

A go-to costs a 3 v 3 about a fifth of what an attack order costs, and a defend order
about 60%. With `followers_school_1052` on both sides, a side sent once to the middle of
the field, then free, scores 0.42 against a side with no orders. Without orders it scores
0.50; ordered onto its nearest enemies, 0.14. So the go-to costs 0.08 ± 0.04 and attack
costs 0.37. Defending each other costs 0.21 ± 0.04. A go-to back to a rally point costs
0.14. Those averages hide a split by hull. In fighter and strafer fights, a defend or a
rally costs 0.34 to 0.47, as much as an attack order. In gunship fights the same orders
*win* 0.17 to 0.29 over no orders. The deadline on a go-to changes nothing. No rule of
the game changed (`SIM_VERSION` 8), and no Rust change was needed.

<!-- summary: We measured what the other order kinds cost a pilot in a fleet fight, after two days showed that an attack order loses most of them. A go-to that ends on arrival costs about a fifth of what an attack order does, and a defend order about 60%. But the cost depends on the hull: holding back or defending loses fighter and strafer fights badly and wins gunship fights, so a commander has a real choice to make. -->

The setup is the same-pilot measure of [2026-11-17](../2026-11-17-order-cost/results.md),
as rerun in [2026-11-18](../2026-11-18-mixed-orders/results.md)'s `eval_before`. One
pilot flies every ship on both sides. The **ordered** side gets orders its pilots see,
from one rule. The **unseen** side gets the scripted commander's orders, hidden from its
own pilots. Rosters are even 3 v 3 of one hull (fighter, strafer, gunship, 8 rosters
each), each played with the ordered side on either team. There are **1,152 matches a
row**, on the 2026-11-17 seeds, so every row pairs match by match with `none`. The ± is
1.96 standard errors, paired for the cost.

`none` and `nearest` were run again with the new script, at 3 threads instead of 4.
`nearest` repeats 0.136 exactly. `none` gives 0.502 against 0.503 before: torch's thread
count changes a few matches. Every cost below is paired against this run's `none`. On a
48-match block at the same thread count, the new script reproduces the old one's output
on `nearest` and `none` field for field.

## The rules

The new rules are in `../2026-11-17-order-cost/order_rules.py`. The old rules are
unchanged. A go-to is sent once, at the first slow tick (t = 2 s), to the whole side as
one squad, and never sent again. Its radius is 60 m, the learned commander's
`GOTO_RADIUS`.

| Rule | Orders |
|---|---|
| `goto_front` | Go to the midpoint between the two fleets' centroids. At t = 2 s that is about 225 m ahead and 225 m short of the enemy, at the edge of its gun range. It is where two fleets of one hull meet, and the go-to a commander would give to "take the middle". No deadline. |
| `goto_front_deadline` | The same point, with a v8 deadline: 2 times the slowest ship's straight-line time to the circle at its speed cap, plus 3 s. That is the tight end of the drills' 2 to 8. |
| `goto_rally` | Go to a point 120 m behind the side's own centroid, away from the enemy: regroup, then fight. The fleets start in a 30 m cluster, so a rally *at* the centroid would be complete on the spot. |
| `defend_ward` | One ship is the ward and gets no order. The other two are one squad defending it. The ward is the ship nearest the side's centroid, kept until it dies. Then the survivor nearest the survivors' centroid takes over, while two are left. |
| `defend_ring` | Each ship is its own squad, defending the next live ship in slot order. With two left they defend each other; with one, it has no order. Every ship is ordered, as under `nearest`, so this is the defend row to compare with attack. Each ship is also a ward: escorts covering each other. |
| `nearest`, `none` | From 2026-11-17: every ship ordered to attack the enemy nearest it, chosen again every 2 s; no orders at all. |

The sim's scripted commander uses go-to the same way, with a radius of 60 to 80 m, no
deadline, and a point re-sent only if it moves more than 120 m (`sticky_goto`). It sends
defend only for a carrier or a transport. No deathmatch convention exists for defend, so
the two arrangements above bracket it.

**A completed go-to is "no order" to the pilot.** Once the ship is inside the circle, or
has missed the deadline, its effective order is none (SIM_SPEC §0.4 row 2, §0.6 row 3).
Everything the pilot reads comes from the effective order through `seen_order`: the order
block, `order_ships`, the order-dependent extras and `order_time`. All of it is zero, as
for a ship never ordered. What differs is outside the pilot's view. The squad's
*standing* order stays a go-to: `order_tracks()` reports `standing_kind` 3 with
`arrived` set, and the learned commander's squad record still shows a go-to. A go-to
re-sent within 40 m of the first point, with the same deadline, is the same instance and
stays complete (`GOTO_SAME_POINT`). One to a new point, or with a new deadline, starts
over. That is why the rules send the go-to once: a midpoint re-sent every 2 s would
drift and restart it.

## The cost

`followers_school_1052`, 3 v 3, 1,152 matches a row (by hull, 384 each):

| Rule | Ordered score | Cost vs `none` (paired) | Fighter cost | Strafer cost | Gunship cost |
|---|---|---|---|---|---|
| `none` | 0.502 ± 0.029 | | (0.49) | (0.48) | (0.54) |
| `nearest` (attack) | 0.136 ± 0.020 | **−0.366 ± 0.035** | −0.37 ± 0.06 | −0.44 ± 0.05 | −0.29 ± 0.07 |
| `goto_front` | 0.422 ± 0.028 | **−0.080 ± 0.041** | −0.12 ± 0.07 | −0.13 ± 0.07 | +0.01 ± 0.07 |
| `goto_front_deadline` | 0.418 ± 0.028 | −0.084 ± 0.041 | −0.14 ± 0.07 | −0.12 ± 0.07 | +0.01 ± 0.07 |
| `goto_rally` | 0.361 ± 0.028 | −0.141 ± 0.038 | −0.34 ± 0.06 | −0.36 ± 0.06 | **+0.28 ± 0.06** |
| `defend_ward` | 0.287 ± 0.026 | −0.215 ± 0.038 | −0.42 ± 0.06 | −0.40 ± 0.05 | +0.17 ± 0.07 |
| `defend_ring` | 0.288 ± 0.026 | **−0.214 ± 0.038** | −0.46 ± 0.05 | −0.47 ± 0.05 | **+0.29 ± 0.06** |

`f995_701` (the live list's top pilot, which "fights hard and ignores orders"; a v6 pilot
with 583 inputs, so it cannot see a deadline), 576 matches a row:

| Rule | Ordered score | Cost vs `none` (paired) | Go-to ships that arrived |
|---|---|---|---|
| `none` | 0.458 ± 0.038 | | |
| `nearest` | 0.554 ± 0.038 | +0.095 ± 0.052 | |
| `goto_front` | 0.380 ± 0.038 | −0.078 ± 0.053 | 0.38 |
| `goto_front_deadline` | 0.438 ± 0.038 | −0.021 ± 0.053 | 0.09 (0.91 missed) |
| `goto_rally` | 0.362 ± 0.037 | −0.096 ± 0.051 | 0.09 |
| `defend_ward` | 0.484 ± 0.040 | +0.025 ± 0.054 | |
| `defend_ring` | 0.571 ± 0.039 | +0.113 ± 0.053 | |

For `f995_701` no order costs much. Every row is within 0.11 of `none`, and the signs
are mixed. It barely follows a go-to (it arrives at the middle 38% of the time and at
the rally point 9%). Its attack and defend rows come out slightly *ahead*, by about two
standard errors. Hull by hull, the costs are in `tables.md`. They swing by up to ±0.3 at
192 matches a hull, which is close to noise.

## What the ordered side does (`followers_school_1052`, first 30 s)

Per match, ordered side, with the free side under `none` as the reference. "Advance" is
speed toward the enemy fleet's centroid. "Under an order" is the share of time alive with
an effective order. Damage is hull and shield. For defend, "on threats" is the share of a
defender's damage that lands on its ward's threat set. That set is approximated as an
enemy within its gun range plus 40 m of the ward, or one that hit the ward in the last
5 s.

| Side | Lost | Advance (m/s) | Under an order | Enemy in arc | Dealt | Taken | Other |
|---|---|---|---|---|---|---|---|
| `none`, free | 0.72 | +1.2 | | 0.079 | 112 | 112 | |
| `nearest` | **1.00** | **+13.5** | 0.92 | 0.111 | 90 | 150 | 0.98 of damage on the target |
| `goto_front` | 0.84 | +8.8 | 0.32 | 0.109 | 115 | 142 | arrived 0.95, median 4.5 s after the order |
| `goto_front_deadline` | 0.85 | +5.0 | 0.17 | 0.094 | 114 | 128 | arrived 1.00, median 3.4 s; none missed |
| `goto_rally` | 0.90 | −2.5 | 0.58 | 0.071 | 77 | 120 | arrived 0.89, median 14.0 s; 0.09 died first |
| `defend_ward` | 0.49 | −2.8 | 0.61 | 0.054 | 61 | 94 | 0.40 on threats; 181 m from the ward; wards lost 0.35 |
| `defend_ring` | 0.42 | −7.1 | 0.93 | **0.027** | **25** | 70 | 0.33 on threats; 131 m from the ward; wards lost 0.42 |

Over time (2-s bins starting at t; "lost" is ships lost by the end of the bin):

| t (s) | 2 | 4 | 6 | 8 | 12 | 16 | 20 | 28 |
|---|---|---|---|---|---|---|---|---|
| `none`: either side toward (m/s) | +18 | −22 | −22 | −3 | +7 | −1 | 0 | +9 |
| `goto_front`: ordered toward | +36 | +30 | +10 | −4 | +2 | +3 | +4 | +8 |
| `goto_front`: unseen toward | +18 | −30 | −34 | −15 | −1 | +3 | +3 | +4 |
| `goto_front`: ordered / unseen lost | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0.13 / 0.02 | 0.39 / 0.27 | 0.84 / 0.68 |
| `goto_rally`: ordered toward | +18 | −34 | −26 | −8 | +5 | −1 | −3 | 0 |
| `goto_rally`: unseen toward | +19 | −16 | −8 | +9 | +10 | +10 | +9 | +10 |
| `defend_ring`: ordered toward | +22 | −24 | −21 | −16 | −11 | −6 | −6 | −9 |
| `defend_ring`: unseen toward | +19 | −20 | −17 | 0 | +11 | +16 | +18 | +20 |
| `defend_ring`: ordered / unseen lost | | | | | | 0.01 / 0 | 0.04 / 0 | 0.42 / 0.04 |

What this says:

1. **The go-to's cost is the charge, and it is a quarter of the attack's.** Sent to the
   middle, the side flies in at 30 to 41 m/s while the free side falls back, faster than
   it does against free pilots (−30 m/s). It arrives at about t = 6 s, with the fleets' centroids
   320 to 340 m apart. From then on it flies like a free side: −4 to +8 m/s, the control's −3 to
   +9. The charge leaves it a little behind (0.84 ships lost by 30 s against 0.68), and
   that is the 0.08. Under `nearest` the side keeps closing at +12 to +19 m/s until it
   dies.
2. **The deadline makes no difference.** With one, the pilots fly faster (median arrival
   3.4 s against 4.5) and all of them arrive in time. The score is the same (0.418 and
   0.422, paired difference 0.00 ± 0.04).
3. **Defending is passive, and that is the cost.** Defenders fall back and keep falling
   back (−7 m/s under `defend_ring`). They have an enemy in arc a third as often as free
   pilots, and deal 25 damage in the first 30 s against 112. They stay 130 to 180 m from
   their ward, well outside any escort ring. The free side walks in at +10 to +20 m/s and
   picks wards off: one is lost in 35% to 42% of matches by 30 s. Matches run longer
   (63 s against 58 without orders), and the ordered side loses them later.
4. **The same passivity wins with gunships.** A gunship's turrets cover almost all round
   and it flies at 24 m/s. A gunship side that holds back while the enemy comes to it wins
   rally and defend matches 0.71 to 0.83 of the time. A fighter or strafer side that holds
   back is closed on and loses 0.85 to 0.99 of them. Free gunships play the fighters'
   game: they fall back and come in again. Against a side that holds still, that loses.
5. **Rally is a falling-back go-to with the same split.** It takes 14 s to arrive, most
   of it flying away from the enemy (−34 m/s), and 9% of the ships die before they get
   there. Fighters and strafers lose 0.34 to 0.36 of a match; gunships gain 0.28.

## What we learned

- **A go-to is the cheap order.** To the middle of the field, then free, it costs 0.08 ±
  0.04 of a 3 v 3, against 0.37 for attack. The cost is the charge into a side that falls
  back. A completed go-to leaves the pilot exactly as free as one never ordered, and that
  is how it flies.
- **Defend is not cheap for fighters and strafers.** It costs them 0.40 to 0.47, more
  than attack (0.37 to 0.44). It does not keep defenders near the ward, and it does not
  protect the ward either.
- **What an order costs depends on the hull, and the sign can flip.** The same defend or
  rally that loses a fighter fight by 0.4 wins a gunship fight by 0.2 to 0.3. Even attack
  costs gunships less (0.29). For a scenario built around go-to, defend and launch
  decisions, this is the useful finding. A commander that sends fighters and strafers
  forward with a go-to, and holds gunships back on a defend or a rally, beats one that
  gives every hull the same order. Free pilots do not make that choice. The rules here
  only show that the choice is worth something in an even single-hull fight. Mixed hulls
  are untested.
- **An order the pilot ignores costs about nothing.** `f995_701` arrives at a go-to 9% to
  38% of the time, and no order costs it more than 0.1. Attack and defend come out
  slightly ahead (+0.10 and +0.11, about two standard errors). The cost of an order is
  the cost of *following* it. It goes up with how well the pilot follows, so a pilot that
  learns to follow better pays more.
- **Not measured:** the 2 v 2, mixed rosters, carrier and convoy missions (where defend
  has a natural ward), a go-to to a flank, and the gunship result with other pilots.

## Files

- `run.sh`: reproduces `out/` (`PILOT=followers_school_1052` by default, 1,152 matches a
  rule; `PILOT=f995_701 BLOCKS=12`). Two chains of 3 threads, `nice -n 19`. Each rule
  takes 520 to 820 s on the laptop. The logs are `run.out` and `run_f995.out`.
- `out/<pilot>_k3_<rule>.json|.out`: each rule's matches (`rlf.order_cost.rules/1`). New
  fields: `orders` (per side: go-to arrived, missed, died first, arrival-time quartiles,
  when the order was spent), `per_match.order_steps` (per ship: go-to start, arrival,
  miss, order start and spent, death step), `per_match.side`. New window sums in
  `sides`: `eff_ordered_s`, `goto_s`, `defend_s`, `ward_s`, `dist_ward_sum`, `ward_taken`,
  `ward_lost`, `dealt_threat`, `dealt_nonthreat`.
- `analyze.py [pilot]`: the tables. `tables.md` holds both pilots' full output, by hull
  and over time.
