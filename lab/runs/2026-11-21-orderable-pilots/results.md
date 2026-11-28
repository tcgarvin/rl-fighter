# Orderable pilots: neither arm ends with both skills

A commander can only help its side if its pilots both take orders without losing their
fights and come home when recalled for repair. At the start of this night each skill
lived in a different pilot. `kite_2205` loses little of its fighting strength when given
an attack order, and `dock600` 2624 (the `dock600` arm of the previous night's run,
saved at update 2624) answers a recall. Each was taught the other's skill: two arms (two
versions of the experiment, one per starting pilot) trained on Beast, the lab's desktop
with two graphics cards, for seven hours (04:22 to 11:30, about 2,290 updates, or rounds
of training, each). Both learned some of the new skill and lost some of the one they
had. In real matches, recalls still almost never end in a dock (1 to 5 in 100). Both
arms joined the pilot season (every pilot trained under the current rules) as new
members, and wins above replacement, a rating of how many more matches a side wins with
a pilot than with our hand-written one, decides whether they fly on the website's front
page. No rule of the game changed (`SIM_VERSION` 11).

<!-- summary: A commander is only worth something if its pilots both take orders and come home when recalled. Today those skills live in two different pilots, so each was taught the other's skill for a night. The orderable pilot learned to dock (18 calm dock drills in 100, from 4) but got weaker in fleet fights. The docking pilot learned to take an attack order (against one opponent its ordered side now beats its unordered side) but docks less (44 in 100, from 57). In real matches recalls still rarely end in a dock. Both joined the pilot season; wins above replacement, running now, decides whether they fly live. -->

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a neural network,
a pilot, that learned to fly by trial and error. Each side can also have a commander
that gives its ships orders. Two problems stood between a commander and any use. First,
an order cost a pilot its fight: ordered to attack, a pilot charged its target and lost
the duel ([the order-cost night](../2026-11-17-order-cost/results.md)).
[Kite drills](../2026-11-18-kite-drills/results.md), practice attacks on a target that
backs away and fights back, made the order much cheaper for one pilot, `kite_2205`.
Second, since [dock and repair](../2026-11-20-dock-repair/results.md) a commander can
recall a damaged craft, but no trained pilot came home until
[the dock pilot run](../2026-11-20-dock-pilot/results.md) taught `dock600` 2624 to land.
A commander that orders its pilots onto targets and recalls them needs both skills in one
pilot. On the laptop the same night, [commander 4](../2026-11-21-commander-4/results.md)
trained commanders over the pilots that exist.

Pilot names are a training line followed by the update they were saved at. Both parents
come from the followers family, bred to fight and follow orders. The arms are called by
their run names in the tables below. Each pilot's names:

| In this entry | Name in the season | Started from | Skill at the start |
|---|---|---|---|
| `kite_2205` (parent) | `kite_2205` | `followers_school_1052`, a follower after [two nights of go-to school](../2026-11-14-goto-school-2/results.md) | takes an attack order cheaply |
| `dock600` 2624 (parent) | `followers_dock_2624` | `followers_school_600` | docks when recalled |
| `kitedock` 2293 (arm) | `kite_dock_2293` | `kite_2205` | learning to dock |
| `dockkite` 2286 (arm) | `followers_dockkite_2286` | `dock600` 2624 | learning kite drills |

<div data-figure="diagram" data-name="training-night" data-caption="Here the night had two parents, each with one skill, and one arm from each that learned the other's skill: kitedock learned to dock and dockkite took kite drills. Their WAR round was still running when this entry was written."></div>

The [plan](plan.md) has the arms and the training mix. [report.md](report.md) has every
measure, each arm beside its parent and at every 500 updates. The final evals (batches of
matches played only to measure): 128 drills a kind, 256 recall matches a mission, 192
matches a mission against the script (our hand-written rule-based pilot), and order cost
at 1,152 matches a row. ± is the margin of error (95%): the true value very likely lies
within that range.

**How to read the order cost.** In a 3 v 3 fight (three ships a side), the pilot's side
is either ordered onto its nearest enemies (each ship given an attack order on the enemy
nearest it) or unordered. The other side is flown by a "free" pilot: it flies with its
orders hidden and fights on its own judgment. Two free opponents are used,
`followers_school_1052` and `f995_701` (a strong fighter that ignores orders, from
[fighters v2](../2026-11-01-fighters-v2/results.md), and the founder of the fighters
family). The order cost is the ordered win rate minus the unordered one, compared match
by match on the same matches. It is a change in the share of matches won, out of 1. A
negative cost means the order loses fights.

<div data-figure="diagram" data-name="order-cost" data-caption="Here the tested side is an arm or its parent, and the free side is followers_school_1052 or f995_701. Run 2 is what the tables call unordered."></div>

## `kitedock`: the orderable pilot learning to dock

Each row is one measure, for the parent and for the arm at its last update. Dock drills
are short practice scenarios in which a damaged craft is ordered home, alone (calm) or
chased (under fire). "Recalls that end in a dock" is from real matches under the scripted
commander, in carrier battles (each side has a carrier, and a side wins by destroying the
other's) and station assaults (one side defends a station, the other attacks it with a
carrier and bombers). The last row is the win rate against script-flown sides in a
carrier battle, a station assault and a four-a-side fleet fight (small ships only, last
side standing).

<div data-figure="diagram" data-name="dock-loop" data-caption="The recalls in the tables below go round this loop, with the scripted commander recalling. A dock drill practises only the trip home and the landing."></div>

| Measure | `kite_2205` (parent) | `kitedock` 2293 |
|---|---|---|
| Calm dock drills: docked | 0.04 ± 0.03 | **0.18** ± 0.07 |
| Dock drills under fire: docked | 0.02 ± 0.03 | 0.09 ± 0.05 |
| Recalls that end in a dock: carrier battle / station | 0.03 / 0.02 | 0.01 / 0.03 |
| Ordered onto nearest, 3 v 3 against a free `followers_school_1052`: wins | 0.42 | 0.14 |
| The same, unordered | 0.57 | 0.34 |
| Order cost against it (paired) | −0.15 ± 0.04 | −0.20 ± 0.03 |
| Unordered, 3 v 3 against a free `f995_701` | 0.63 | **0.14** |
| Order cost against `f995_701` (paired) | −0.17 ± 0.04 | +0.03 ± 0.03 |
| Against the script: carrier battle / station / fleet 4 v 4 | 0.92 / 0.59 / 0.89 | 0.82 / 0.54 / 0.72 |

It learned to dock slowly but steadily. In training, calm docks rose from 0.05 to 0.23
over the night and were still climbing. The order drills (practice scenarios for the
attack, defend and go-to orders) held within a few points: go-to arrivals 0.89 to 0.86,
attack orders followed when the target is switched 0.96 to 0.94, defend orders followed
when switched 0.95 to 0.92. But it got much weaker in 3 v 3 fleet fights,
ordered or not, and somewhat weaker against the script. Its order cost against `f995_701`
looks like zero (+0.03) only because it now loses those fights either way.

## `dockkite`: the docking pilot learning kite drills

Read as the table above. "Ships lost" counts the ordered side's ships lost per match (out
of three) in the same fights against `followers_school_1052`. The last two rows are
order-drill measures. `defend_flip` is the share of paired defend drills in which the
pilot switched to the other friendly ship when the order named that one instead.
`defend_more_on_named` is the share of defend drills in which the enemies attacking the
ship it was told to defend took more damage than the other enemies.

| Measure | `dock600` 2624 (parent) | `dockkite` 2286 |
|---|---|---|
| Calm dock drills: docked | **0.57** ± 0.09 | 0.44 ± 0.09 |
| Dock drills under fire: docked | 0.27 ± 0.08 | 0.17 ± 0.07 |
| Recalls that end in a dock: carrier battle / station | 0.05 / 0.08 | 0.02 / 0.05 |
| Order cost, 3 v 3 against a free `followers_school_1052` (paired) | −0.10 ± 0.04 | **+0.06** ± 0.03 |
| Ordered side's ships lost in a match, the same fights | 0.98 | 0.54 |
| Order cost, 3 v 3 against a free `f995_701` (paired) | +0.11 ± 0.04 | −0.12 ± 0.04 |
| Against the script: carrier battle / station / fleet 4 v 4 | 0.82 / 0.66 / 0.75 | 0.90 / 0.64 / 0.66 |
| Order drills: defend_flip | 0.86 | 0.78 |
| Order drills: defend_more_on_named (pass mark 0.85) | 0.84 | 0.83 |

Ordered onto its nearest enemy against `followers_school_1052`, it now wins more than
unordered, and loses half as many ships doing it. Against `f995_701` the order went from
helping to costing, so the gain depends on the opponent. It docks less than its parent,
and its defend drills slipped. It is the one new member below the drill bars, the pass
marks set for the order drills: its `defend_more_on_named` is 0.83 against a mark of 0.85
(its parent, already a member, was at 0.84). The bars are a report, not a gate (a pass
mark a pilot must meet to be admitted), so it plays WAR like the rest.

## What it means for the commander

A commander still has no pilot that takes an attack order cheaply against every opponent
and also comes home. And no pilot yet completes more than about 1 recall in 12 in a real
match (the best, `dock600` 2624, 5 in 100 in carrier battles and 8 in station assaults),
which is where a recall would matter. The dock drills teach landing from a
standing start. The matches need a pilot that breaks off a fight and gets home alive.

## Into the season

Wins above replacement (WAR) is borrowed from baseball. Pilots are dropped at random into
matches like the live page's, and a statistical fit estimates how many more matches out
of 100 a side wins with that pilot flying its ships instead of the script.

`war.sh` (on Beast, started 13:43) entered four members as children of their parents in
the season's records, `lab/population/2026-11-sim6`: `kite_2205` and its sister `kite_pay025_2211`, from the other arm of the
[kite drills](../2026-11-18-kite-drills/results.md), which was also paid a quarter as much
for following orders in matches (both trained there but were not yet in the season),
`kite_dock_2293` and `followers_dockkite_2286`. It is now playing wins above replacement
for them, the live ten (the pilots the live page draws from) and the dock pilots, in the
four live missions with the live commander stable (the commanders the live page draws
from). Then `tools.live_pilots publish --war` picks the live ten.
