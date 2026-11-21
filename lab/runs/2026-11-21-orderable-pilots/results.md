# Orderable pilots: neither arm ends with both skills

Two followers trained on Beast for seven hours (04:22 to 11:30, about 2,290 updates
each). Each had one skill: `kite` 2205 takes an attack order cheaply, and `dock600` 2624
answers a recall. Each was taught the other. Both learned some of the new skill and lost
some of the one they had. In real matches, recalls still almost never end in a dock (1 to
5 in 100). Both arms joined the pilot season as new members, and wins above replacement
decides whether they fly on the live page. No rule of the game changed (`SIM_VERSION` 11).

<!-- summary: A commander is only worth something if its pilots both take orders and come home when recalled. Today those skills live in two different pilots, so each was taught the other's skill for a night. The orderable pilot learned to dock (18 calm dock drills in 100, from 4) but got weaker in fleet fights. The docking pilot learned to take an attack order (against one opponent its ordered side now beats its unordered side) but docks less (44 in 100, from 57). In real matches recalls still rarely end in a dock. Both joined the pilot season; wins above replacement, running now, decides whether they fly live. -->

The [plan](plan.md) has the arms and the training mix. [report.md](report.md) has every
measure, each arm beside its parent and at every 500 updates. The final evals:
128 drills a kind, 256 recall matches a mission, 192 matches a mission against the
script, and order cost at 1,152 matches a row (± is 95%).

## `kitedock`: the orderable pilot learning to dock

| Measure | `kite` 2205 (parent) | `kitedock` 2293 |
|---|---|---|
| Calm dock drills: docked | 0.04 ± 0.03 | **0.18** ± 0.07 |
| Dock drills under fire: docked | 0.02 ± 0.03 | 0.09 ± 0.05 |
| Recalls that end in a dock: carrier battle / station | 0.03 / 0.02 | 0.01 / 0.03 |
| Ordered onto nearest, 3 v 3 against a free `followers_school_1052`: wins | 0.42 | 0.14 |
| The same, unordered | 0.57 | 0.34 |
| Order cost against it (paired) | −0.15 ± 0.04 | −0.20 ± 0.03 |
| Unordered, 3 v 3 against a free `f995_701` | 0.63 | **0.14** |
| Against the script: carrier battle / station / fleet 4 v 4 | 0.92 / 0.59 / 0.89 | 0.82 / 0.54 / 0.72 |

It learned to dock slowly but steadily. In training, calm docks rose from 0.05 to 0.23
over the night and were still climbing. The order drills held. But it got much weaker in
3 v 3 fleet fights, ordered or not, and somewhat weaker against the script. Its order cost
against `f995_701` looks like zero (+0.03) only because it now loses those fights either
way.

## `dockkite`: the docking pilot learning kite drills

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

Ordered onto its nearest enemy against `followers_school_1052`, it now wins more than
unordered, and loses half as many ships doing it. Against `f995_701` the order went from
helping to costing, so the gain depends on the opponent. It docks less than its parent,
and its defend drills slipped. It is the one new member below the drill bars
(`defend_more_on_named`). The bars are a report, not a gate, so it plays WAR like the rest.

## What it means for the commander

A commander still has no pilot that takes an attack order cheaply against every opponent
and also comes home. And no pilot yet completes more than about 1 recall in 20 in a real
match, which is where a recall would matter. The dock drills teach landing from a
standing start. The matches need a pilot that breaks off a fight and gets home alive.

## Into the season

`war.sh` (on Beast, started 13:43) entered four members as children of their parents in
`lab/population/2026-11-sim6`: `kite_2205` and `kite_pay025_2211` (from the
[kite drills](../2026-11-18-kite-drills/results.md), not yet in the season), `kite_dock_2293`
and `followers_dockkite_2286`. It is now playing wins above replacement for them, the
live ten and the dock pilots, in the four live missions with the live commander stable.
Then `tools.live_pilots publish --war` picks the live ten.
