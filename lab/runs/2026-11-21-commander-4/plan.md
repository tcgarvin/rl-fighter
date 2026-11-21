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
arms; the third pairs the commander with the pilots the kite drills made.

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

## In the morning

- **`hold`**: the station-commander eval (`../2026-11-19-station-commander/eval.sh`, defender
  cells) for the final checkpoint, update 0 and `hold_late`, with first-launch time and the
  hull at first launch.
- **`kite`, `noattack`**: `spacefight.commander.eval` against `unseen`, 384 a mission, over
  their own pilots and the live ten, with the order kinds by hull.
- The measures go into results.md. A commander that beats unseen goes into the live stable
  beside the others (`tools.live_commanders publish --keep`), as a pilot joins the season:
  measured, not gated.
