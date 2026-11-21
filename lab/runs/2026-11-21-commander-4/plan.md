# Commander 4: three ways a commander might help its side

Started 2026-11-21 at 03:23 (`hold` at 03:40) on the laptop; the trainers stop at 10:30. `SIM_VERSION` 11. The hold arms changed in the night: see "A change at 05:11", "07:55" and "08:25" below.

## Why

The goal is a commander that makes its side win more than the same pilots with no orders.
Three phases have not found one:

- [Commander 3](../2026-11-15-commander-3/results.md): given the choice, commanders learned to
  stop giving orders and scored level with a side that gets none.
- [Order cost](../2026-11-17-order-cost/results.md) and
  [order kinds](../2026-11-19-order-kinds/results.md) found why: an attack order costs a 3 v 3
  about 0.37, because an ordered pilot charges its target and shoots nothing else. A go-to
  costs about 0.08. A defend order costs fighters and strafers a lot and *helps* gunships.
- [Station rules](../2026-11-19-station-rules/results.md) found the only commander decisions
  measured to win: hold the station's reserve in its hangar instead of launching it at
  once. The [station commander](../2026-11-19-station-commander/results.md) did not find it.
  It launched everything at 2 s, as the script does.
- [Kite drills](../2026-11-18-kite-drills/results.md) made an attack order much cheaper for
  one pilot: `kite` 2205 loses 0.09 to 0.15 when ordered, where its parent lost 0.37.

A design review of these results (with Fable, a second model) suggested two of tonight's
arms; the third pairs the commander with the pilots the kite drills made. On Beast,
[orderable pilots](../2026-11-21-orderable-pilots/plan.md) trains the pilot half of the
loop the same night: one pilot that both takes an attack order cheaply and answers a
recall. The owner also suggested training a commander and its pilots together; the
review argued against it for now (the [pairing grid](../2026-11-19-pairing/results.md)
found no commander-pilot interaction beyond orders hurting followers, and the pilot
trainer only plays frozen commanders), until some order is worth giving.

## Three arms, one learner each

| Arm | What changes | Pilots | Enemies |
|---|---|---|---|
| `hold` | Station assault only, always the defender, the citadel. Starts from commander 3's `live` 197 (already quiet), its launch head reset to launch each hull on 3% of decisions, so holding the reserve is what it tries first. Longer credit (γ 0.997, λ 0.98), no shaping. | the live ten | 3/4 unseen, 1/4 scripted |
| `kite` | A fresh commander over the two kite pilots, all four missions. | `kite_2205`, `kite_pay025_2211` | 1/2 unseen, the rest itself and its snapshots |
| `noattack` | A fresh commander that cannot give an attack order (a fixed −30 on that choice), all four missions. What is left is go-to, defend and dock, and which hull gets which. | commander 3's four followers | 1/2 unseen, the rest itself and its snapshots |

"Unseen" is the scripted commander with its orders hidden from its own pilots: the side
with no orders. A commander that gives no orders scores about 0.50 against it.

**Why `hold` starts so cautious.** A fresh launch head launches each hull half the time,
so the hangar is empty in about 4 s and the learner never tries holding. Credit was the
other problem: the payoff of a held reserve comes 30 to 60 s later, past what γ 0.99
reaches. And the old shaping paid for the station's hull, which falls while the reserve
waits. A 3% launch rate holds each hull class about 33 s on average. That is itself close
to the `hold_late` rule, so the morning compares the final checkpoint with update 0 too:
if both beat no orders by the same amount, the prior helped and nothing was learned.

## Checking the hand rules still win at v11

Before the night, `preflight.sh` here played the
defender's hand rules at v11, which recalls and relaunches. 512 matches a cell; the
attacker's win rate (lower is better for the defender):

| Station | No orders (unseen) | `hold_late` | `hold_reserve` |
|---|---|---|---|
| v9 station ("strike of 8") | 0.467 ± 0.043 | **0.246** ± 0.037 | 0.322 ± 0.040 |
| Citadel | 0.322 ± 0.041 | **0.133** ± 0.029 | 0.275 ± 0.039 |

Holding is still worth about 0.2 to the defender on both stations, so there is something
to find on the citadel, the one the live page plays. The `hold` arm trains there; it
started at 03:40, the other two at 03:23.

## A change at 05:11: `hold_quiet`

The `hold` arm started well and then slid. Its defender's win rate against the attacker
with no orders, averaged over 15-update windows (about 500 matches each, ± 0.04):

| Updates | 1–15 | 16–30 | 31–45 | 46–67 |
|---|---|---|---|---|
| Defender wins | 0.79 | 0.73 | 0.64 | 0.59 |
| Ship time under an order | 3% | 8% | 9% | 13% |

At the start, the launch prior alone put it well above the no-orders defender (0.68 in the
preflight's matches) and close to `hold_late` (0.87). It then drifted into giving orders,
which cost these pilots fights, as everywhere before, and lost ground. Its launches stayed
at about 4% of decisions. The question for this arm is launch timing, so it was stopped
at update 68 and replaced by **`hold_quiet`**: the same start and settings, with attack,
defend and go-to forbidden, so it chooses only when each hull class launches. `hold`'s
checkpoints stay for the morning eval.

## Midway, at 06:10

The trainers' own win rates against the side with no orders, in 10-update windows
(about 250 to 500 matches each, so ± 0.04 to 0.06). `hold_quiet` is the defender's.

| Updates | 1–10 | 11–20 | 21–30 | 31–40 | 41–50 | 51–60 | 61–70 |
|---|---|---|---|---|---|---|---|
| `hold_quiet` | 0.88 | 0.76 | | | | | |
| `kite` | 0.32 | 0.34 | 0.38 | 0.40 | 0.41 | 0.44 | 0.44 |
| `kite`: ship time under an order | 49% | 49% | 47% | 42% | 40% | 38% | 35% |
| `noattack` | 0.33 | 0.34 | 0.35 | 0.37 | 0.44 | 0.38 | 0.39 |
| `noattack`: ship time under an order | 41% | 38% | 31% | 26% | 17% | 13% | 10% |

`kite` and `noattack` climb as they give fewer orders, the path commander 3 took. Neither
is yet level with no orders. `hold_quiet` is at 21 updates (station matches are long); its
first windows sit near `hold_late`'s 0.87, which the launch prior alone may explain. The
morning's update-0 cell tells the two apart.

## 07:55: all three hold runs slid the same way, so both arms stopped

`hold_quiet` slid like `hold` even though it can give no orders. So orders were not what
cost `hold` its ground, as the 05:11 note above guessed. What PPO did to launch timing was.

There were in fact three runs, not two. Editing `run.sh` at 05:10, while the copy that
started `hold` was still running, made bash read the edited file part-way through and start
`hold` again from update 1 with the same settings. That second run overwrote the first
run's checkpoints 10 to 50 (60 and 68 remain) and appended to its log. It trained beside
`hold_quiet` until 07:55, a fourth trainer on the laptop the whole time. It is a replicate
nobody planned, and the three agree:

| Updates | 1–10 | 11–20 | 21–30 | 31–40 | 41–50 | 51–end |
|---|---|---|---|---|---|---|
| `hold`, first run | 0.85 | 0.80 | 0.72 | 0.67 | 0.57 | 0.61 (to 68) |
| `hold`, second run | 0.84 | 0.76 | 0.65 | 0.60 | 0.62 | 0.64 (to 56) |
| `hold_quiet` | 0.88 | 0.76 | 0.76 | 0.69 | 0.65 | 0.62 (to 57) |
| Launch-head entropy, `hold_quiet` | 0.20 | 0.15 | 0.11 | 0.09 | 0.08 | 0.05 |

These are defender wins against the attacker with no orders, from the trainers' logs. The
launch rate stayed at about 4.4% of decisions throughout. The launch head instead grew
nearly certain about *when* to launch, and its choice loses. One guess, not tested: an
update sees only about 25 station matches, each won or lost 30 to 120 s after the launches
that decided it. That is too little signal for a policy that starts near the best hand rule,
so its steps are mostly noise, and from near the top noise leads down.

The `hold` and `hold_quiet` trainers were stopped at 07:55. More of the same would only
lose ground and slow `kite` and `noattack`. `eval_hold_curve.sh` plays checkpoints along
all three curves on the preflight's seeds (512 matches a cell, paired with the no-orders
and `hold_late` cells), to measure the slide outside training and the launch times behind it.

## 08:25: the hold runs learned to launch everything at once

`eval_hold_curve.sh` played the checkpoints on the preflight's 512 seeds. Attacker wins,
lower is better for the defender (± 1.96 standard errors):

| Defender | Attacker wins | First launch, median (quartiles) | Hangar empty, median |
|---|---|---|---|
| No orders (the script's launches) | 0.322 ± 0.041 | 3 s | 7 s |
| `hold_late` (hand rule) | **0.133** ± 0.029 | 57 s (49–67) | 59 s |
| `hold_reserve` (hand rule) | 0.275 ± 0.039 | 19 s (15–33) | 25 s |
| `hold_quiet` update 0 (the start) | **0.158** ± 0.032 | 9 s (5–17) | 76 s |
| `hold_quiet` 10 | 0.191 ± 0.034 | 5 s (3–8) | 36 s |
| `hold_quiet` 30 | 0.283 ± 0.039 | 2 s | 15 s |
| `hold_quiet` 57 | 0.404 ± 0.043 | 2 s | 5 s |
| `hold` update 0 | 0.162 ± 0.032 | 9 s (5–17) | 76 s |
| `hold`, second run, 10 | 0.191 ± 0.034 | 4 s (3–7) | 32 s |
| `hold`, second run, 56 | 0.422 ± 0.043 | 2 s | 7 s |
| `hold`, first run, 68 | 0.383 ± 0.042 | 2 s | 9 s |

The launch prior alone was nearly as good as `hold_late`. It holds part of the reserve
for over a minute, though its first launch comes at 9 s, not 57. Every run then trained it
away, toward launching the whole hangar at 2 s. By the end each was worse than no orders:
0.40 against 0.32, so the defender wins less than it would with the script's launches.
Three runs moving the same way is not noise but a steady push.

**The guess, and the test.** The launch head carries an entropy bonus (`ent_coef` 0.002)
at every decision where that hull class can launch. When no reserve can launch, the mask
closes the choice and the bonus does not count. Holding a reserve for a minute means
choosing "hold" at every one of the many decisions in that minute, and the bonus pushes
each of them toward even odds. Launching ends those decisions, because the mask closes. So
the bonus presses hardest on exactly the behaviour that wins. Against that, the only signal
is a win or a loss a minute later, shared by every decision in the match, with about 25
station matches an update. Launch-head entropy *fell* in the logs because the hangar
emptied sooner, which leaves more decisions with nothing to choose. **`hold_ent0`**
(`run_hold_ent0.sh`, its own launcher) started at 08:30: `hold_quiet` with `ent_coef` 0, the
only change, until 10:30. If it keeps its launch times where `hold_quiet` had lost them by
update 30, the bonus did it. If it slides too, the weak signal is the problem, and the
choice needs fewer, larger decisions (for instance, a hold time chosen once per hull class)
or many more matches an update.

## In the morning

- **`hold`, `hold_quiet`**: done at 08:25 (above, `eval_hold_curve.sh`). **`hold_ent0`**:
  the same cells for its checkpoints at 10, 30 and its last, on the same seeds.
- **`kite`, `noattack`**: `spacefight.commander.eval` against `unseen`, 384 a mission, over
  their own pilots and the live ten, with the order kinds by hull.
- The measures go into results.md. A commander that beats unseen goes into the live stable
  beside the others (`tools.live_commanders publish --keep`), as a pilot joins the season:
  measured, not gated.
