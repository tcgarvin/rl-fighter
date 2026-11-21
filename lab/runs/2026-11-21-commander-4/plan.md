# Commander 4: three ways a commander might help its side

Started 2026-11-21 at 03:23 (`hold` at 03:40) on the laptop; the trainers stop at 10:30. `SIM_VERSION` 11.

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

## In the morning

- **`hold`, `hold_quiet`**: the station-commander eval (`../2026-11-19-station-commander/eval.sh`, defender
  cells) for the final checkpoint, update 0 and `hold_late`, with first-launch time and the
  hull at first launch; `eval.sh` here plays them on the preflight's seeds.
- **`kite`, `noattack`**: `spacefight.commander.eval` against `unseen`, 384 a mission, over
  their own pilots and the live ten, with the order kinds by hull.
- The measures go into results.md. A commander that beats unseen goes into the live stable
  beside the others (`tools.live_commanders publish --keep`), as a pilot joins the season:
  measured, not gated.
