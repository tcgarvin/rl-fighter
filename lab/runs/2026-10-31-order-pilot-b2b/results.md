# Order pilot, second run (B2b): pilots follow orders, and stop winning

Run 2026-10-31, `SIM_VERSION` 5 (the version of the game's rules that first shows pilots
their orders), plan: `plan.md`. "B2b" is the project's name for this second order-pilot
run. **Nothing promoted**: fleet pilot v1 stays the pilot that flies the project's
website.

<!-- summary: In our second try at teaching the learned pilot to follow orders, we pulled its choices toward those of a hand-written pilot that follows orders. It learned to follow them about as well as the hand-written one, but the pull also overwrote how it fights: it won 0 to 4 % of carrier battles against the old pilot, where the first try had won 79 %. -->

The [first order-pilot run](../2026-10-31-order-pilot/results.md) made a much stronger
mission pilot that barely followed its orders. This run showed it how: during training
it was pulled toward the choices of the hand-written pilot that follows orders. That
worked for following, which rose to the hand-written pilot's level. It ruined fighting.
The pilot lost nearly every carrier battle, because most moments with an order are
moments in a fight, and there the hand-written pilot flies much worse than the learned
one.

Verdict: **FAIL.** The pilot learned to follow orders but lost its fighting strength.

## Where this fits

RL Fighter is a space-combat game where every small ship is flown by a neural network,
the **pilot**, that learned to fly by trial and error. The project's website plays
matches forever on its front page, the **live page**. Besides team deathmatch (small
ships only, 1 to 4 a side, until one side is destroyed) there are two missions. In a
**carrier battle** each side has a carrier that launches its strike craft, and a side
wins by destroying the enemy carrier. In a **convoy escort** one side's escorts guard
freighters flying to a jump point and the other side attacks, winning if it destroys at
least half of them. Each side also has a **commander** that gives its squads orders:
attack a named enemy, guard a friendly ship (the "ward", the ship to protect), or hold a
point. The live pilot, [fleet pilot v1](../2026-10-30-fleet-pilot/results.md), cannot
see orders, so the orders drawn on the page did not change how ships flew.

Run 1, the [first order-pilot run](../2026-10-31-order-pilot/results.md), showed pilots
their orders and paid them a little for following, and got almost no following. Its
best checkpoint, `w1_400` (the arm with order reward weight 1, saved at training update
400), won 0.79 of carrier battles against v1. Among the likely causes run 1 named:
nothing showed the pilot *how* to follow, and following paid far less than fighting.
This run attacks both. It starts from `w1_400`, pulls the pilot toward the **teacher**
(the hand-written, "scripted", pilot that flies every order), and makes holding a point
pay more, with random hold points drawn near the fight.

<!-- figure-idea: shared: the script pull. One moment of training: the pilot's own choice, the script's choice for the same moment, and the pull that drags the first toward the second, applied only on some moments (here: every moment with an order). Helps here and in the next order-pilot run, where the same mechanism is applied to fewer moments. -->

## What ran

- Two **arms** (versions of the experiment trained side by side, identical but for one
  setting), both from run 1's `w1_400`, 300 updates each (an update is a batch of
  matches played, then one adjustment of the network), run concurrently 04:59–06:47.
  - `pull`: a **script pull**, an extra training term that pulls the pilot's choices
    toward the script's, on ordered rows (a row is one ship's view and choice at one
    moment of training). It covers the movement controls only (thrusters and power, not
    turret aim or trigger), with strength β 0.1 falling to 0 over updates 30–300.
  - `pull_dagger`: the same, after one ordered-rows **DAgger** round (the pilot flies,
    the script labels what it would have done at each ordered moment, and the pilot is
    trained to copy those labels).
- In both: random hold points now drawn near the action, and pay for time inside a hold
  raised to 0.0009 per tick (a tick is 1/30 s). A "KL anchor", a training term that
  penalises the pilot for moving its choices far from v1's, held it close to v1 on rows without an order.
- Gate evals 06:47–08:23 (with the anchor's values cached during play: about 21 s per
  update, 4.3 k samples a second).

## Verdict in detail

The plan fixed its pass marks ("gates") and its rule for picking a winner in its §5
before any candidate was measured. They are run 1's: O (following orders under the
random and the scripted commander, for example a hold order's ship spending at least
0.40 of its time inside its circle), M (mission win against v1 of at least 0.47 in each
mission and 0.52 on average), D (deathmatch win of at least 0.85 against the script and
0.45 against v1) and H (health: matches end normally). Two of O's bars were then reset,
at 04:55 and also before any candidate was measured, because the teacher itself could
not reach them: a guard must now spend at least 0.35 of its time near its ward (was
0.50), and an attacker's share of damage on its target must beat v1's by 0.05 (was
0.10).

The script pull taught following: from update 100 on, every `pull` candidate (a saved
copy of the arm) and most `pull_dagger` candidates pass gate O, at the teacher's level. But no candidate passes M
(missions) or D (deathmatch): carrier battle win vs v1 is 0.000–0.039 at every
checkpoint, against run 1's 0.787.

## Gates (copied from `eval/gates.md`)

Each row is a **candidate**: one arm saved at one update (`pull_dagger_150` is the
`pull_dagger` arm at update 150). O (following orders), M (missions), D (deathmatch) and
H (health: matches end normally, without stalls or errors) are the gates, ✓ met and ✗
not. "Mission win vs v1" is the mean share of carrier battles and convoys won against v1, where 0.5 is
even. Under the random commander (one that hands out random orders, to test following
any order), "guard" is the share of a guard order's time spent close to the ward and
"hold" the share spent inside the hold circle. The last two columns are deathmatch win
rates against the hand-written pilot and against v1.

| candidate | O | M | D | H | mission win vs v1 | guard (random) | hold (random) | dm vs script | dm vs v1 |
|---|---|---|---|---|---|---|---|---|---|
| pull_50 | ✗ | ✗ | ✗ | ✓ | 0.233 | 0.348 | 0.454 | 0.697 | 0.203 |
| pull_100 | ✓ | ✗ | ✗ | ✓ | 0.214 | 0.407 | 0.488 | 0.678 | 0.210 |
| pull_200 | ✓ | ✗ | ✗ | ✓ | 0.243 | 0.409 | 0.521 | 0.743 | 0.236 |
| pull_300 | ✓ | ✗ | ✗ | ✓ | 0.302 | 0.410 | 0.510 | 0.811 | 0.354 |
| pull_dagger_50 | ✗ | ✗ | ✗ | ✓ | 0.171 | 0.364 | 0.454 | 0.521 | 0.080 |
| pull_dagger_150 | ✓ | ✗ | ✗ | ✓ | 0.193 | 0.446 | 0.513 | 0.632 | 0.128 |
| pull_dagger_300 | ✓ | ✗ | ✗ | ✓ | 0.271 | 0.440 | 0.486 | 0.805 | 0.296 |

(Every candidate is in `eval/gates.md`.) For comparison, run 1's w1_400: mission win vs
v1 0.763, guard 0.227, hold 0.116 (0.31 when measured with this
run's hold points, drawn near the fight), deathmatch 0.892 / 0.613.
Against w1_400 itself, the best B2b candidate wins 0.008 of carrier battles.

## Why

- **The pull overwrote combat flying, not just transit** (flying to the ordered spot). It applied to every ordered,
  non-advisory row (advisory orders are the scripted commander's deathmatch orders,
  which are shown but not meant to be followed): about 0.67–0.70 of all rows
  (`beta_rows_share` in `log.jsonl`). Most of those rows are a ship in a fight, where
  the script's movement is much worse than v1's evasive flying. The pulled pilot's
  fighters (side a in the eval) in carrier battles dealt about 10 damage against v1's
  112, hit 0.13 of shots against 0.31, and almost none survived.
- **It happened by update 50, while β was still 0.09.** Decaying β to zero did not undo
  it: missions and deathmatch recover only slowly (dm vs script 0.70 → 0.81 over updates
  50–300) once the pull is gone. The plan's risk table (§7) named this failure but
  expected the schedule to contain it. It needs a row filter (limiting which moments
  get pulled), not a schedule.
- DAgger first made it worse (dm vs v1 0.080 at update 50).

## Next

A design review that followed (the owner and the lab's AI assistants, 2026-10-31)
changes the orders themselves, not only the training recipe. To be written into
`docs/M3_PLAN.md`:

- **Orders:** attack (as now). Defend replaces guard and has no pay for staying close:
  it pays for damage to enemies that threaten the ward (those within their own weapon
  range of it, or that hit it in the last 150 ticks), and every defender is charged
  when the ward loses hull or dies. Go-to replaces hold: fly to a point, done for that
  ship on arrival, with an arrival bonus of about 0.2. And none. An order to return to
  the carrier waits until the game has docking.
- **What the pilot sees:** a pilot sees the 7 ships nearest it. When defending, those
  should be the 7 nearest the ward instead. And for each ship it sees, a few new numbers
  at the end of its inputs: distance to my order point, hull type and longest weapon
  range, and whether it hit my ward recently.
- **Teacher:** the scripted defender goes after the same threatening enemies.
- **Pull:** only on transit rows (moments with an order where the script has no target
  to fight, such as flying to a go-to point), never on combat rows.
- **Gates:** per order, measured the same way the reward pays; missions against v1 and
  against `w1_400`.
