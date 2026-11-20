# Dock and repair: the script docks, the live pilots do not yet

`SIM_VERSION` 11 lets a strike craft come home. The scripted commander sends a craft
below half its hull back to its carrier; the craft flies its own approach, docks through
a live bay, repairs in the hangar and relaunches as the same ship. When the scripts fly
both sides, three recalled craft in five make it home, and nearly every one that
survives the trip docks. A carrier battle sees about two docks and two relaunches a side,
and who wins barely moves: the station assault's attacker wins 0.53 (v10: 0.57), the
citadel's 0.59 (v10: 0.58). The live pilots, who have never been asked to dock, mostly
keep fighting: about 1 recall in 70 ends in a dock, and the few that reach the bay mostly
fly through it too fast. The obs now has its own "dock here" signal for training them.
Deathmatch and convoy matches play exactly as before.

<!-- summary: Damaged fighters can now fly home to their carrier, land, get repaired and launch again as the same ship. When our scripted pilots fly, about three damaged fighters in five make it back, and the other two are shot down on the way. Docking barely changes who wins: the station attack still succeeds about half the time. Our trained pilots have never been asked to land, and almost none of them do: they keep fighting until they are shot down, and the few that reach the bay fly past it too fast. The pilots can now see a separate signal that says "land here" and how the bay is moving, so they can be taught. -->

**Verdict: PARTIAL.** The sim rule, the scripted recall, the dock signal in the obs and
the bindings are done, and the missions stay balanced for the script. The live pilots
need a docking drill and training (stage 3 of `plan.md`) before docking means anything on
the live page with learned pilots.

The rules are in `docs/SIM_SPEC.md` §0.9 (what changed), §5.11 (the rules) and §7.2 (the
obs); the design and the numbers are in `plan.md`. In short: the bay takes a craft in
when it is within 10 m of the mouth of any live bay of its carrier and moving at no more
than 15 m/s relative to it. In the hangar its shield is full at once, its hull repairs at
5% a second, and it may launch again after 4 s. If the carrier dies, so does everything
in its hangar.

**Who recalls.** Only a commander. The scripted commander recalls every own craft below
half its hull, but not one finishing a kill or still under an enemy capital ship's guns,
and relaunches a returned craft at 90% of its hull (half, when it is short of craft). The
random commander keeps these recalls with the scripted launches. A learned commander has
no way to recall yet, so its craft never come home; the sim recalls nobody on its own. A
first version had a sim-side "recall doctrine" that recalled under every commander,
learned ones too. The owner removed it the same day: docking is to be taught, not stood
in for. For scripted commanders it played the same matches.

**What the pilot sees.** A dock order adds five numbers at the end of the obs (587 to
592): a "dock" flag, the bay's velocity relative to the ship, and which way the bay's
mouth faces. In the first 587 numbers, which is all a pilot of v8 to v10 reads, the
order looks like a go-to to the bay's mouth (10 m, no deadline). So the live pilots below
fly the dock order as a go-to, which is what they can understand today. Their matches are
the same with and without the new block, since they do not read it.

Capital ships are always flown by the sim's scripts, and both commanders are scripted.
Each Python row is 512 matches (seeds from 1,100,000); the ± is 1.96 standard errors.
"Off" is the same matches with the dock rules off, which is v10. Code: `dock_eval.py`,
`summary.py`, `run.sh`; the Rust harness is `crates/sim/tests/dock.rs`
(`diag_dock_stats`, 128 starts a roster, `out/diag_dock_stats.txt`).

## Tuning

The plan started the recall at 30% of hull. In the Rust harness, 86% of recalled craft
were shot down before they reached the bay: by the time a craft is that damaged it is
usually deep in the fight, 300 to 450 m from home and often inside an enemy carrier's or
station's guns. Three changes fixed most of that:

| Change | Why |
|---|---|
| Recall at 60% of hull, then 50% | Sent home earlier, a craft has the hull to survive the trip |
| No recall under an enemy capital ship's guns (its longest range plus 40 m) | Turning for home inside a station's flak was the commonest way to die; the craft finishes its run and is recalled once clear |
| The script flies home on engines power, leaves its own carrier out of crash avoidance, and matches the carrier's velocity harder (0.8 /s) | It used to slow down to avoid a collision with its own carrier and never came within 10 m of the mouth |

60% gave the most docks (completion 0.69, 3.1 docks a carrier battle) but pulled so many
craft out of the fight that the citadel assault moved to 0.63 for the attacker (v10:
0.58). At 50% it is 0.59, with 0.54 to 0.64 of recalls completed. The capture radius
(10 m), the relative speed (15 m/s), the repair rate and the turnaround stayed at the
plan's starting values: a scripted pilot that survives the trip docks 97 to 100 times in
100 with them, so there was no reason to loosen them.

One rule came from the live pilots' first run: a commander short of craft relaunched a
returned craft at whatever hull it had, and recalled it again on its first slow tick
out. The scripted commander now relaunches a returned craft early only once it is past
the recall threshold.

## 1. Script against script

| Mission | Team 1 win, dock rules off (v10) | On (v11) | End reasons, on | Median s, off / on |
|---|---|---|---|---|
| Deathmatch | 0.708 ± 0.039 | 0.708 ± 0.039 | eliminated 0.61, clock 0.39 | 42 / 42 |
| Carrier battle | 0.517 ± 0.043 | 0.504 ± 0.043 | carrier 0.87, clock 0.13 | 131 / 132 |
| Convoy escort | 0.002 ± 0.004 | 0.002 ± 0.004 | through 0.75, eliminated 0.24 | 75 / 75 |
| Station assault (attacker) | 0.572 ± 0.043 | 0.527 ± 0.043 | station 0.53, repelled 0.43, clock 0.04 | 103 / 99 |
| Citadel (attacker) | 0.576 ± 0.043 | 0.592 ± 0.043 | station 0.59, repelled 0.31, clock 0.09 | 116 / 118 |

Deathmatch and convoy escort have no carrier, so the dock rules never run: the matches
are identical, state hash for state hash. In the three missions with a carrier the
winner moves by less than two standard errors of the difference (the largest, the
station assault's −0.045, is 1.5). A few more matches run to the clock (carrier battle
0.10 to 0.13, citadel 0.05 to 0.09): repaired craft come back, so a side takes longer to
run out of them. The station assault's attacker, at 0.53, stays inside the 0.45 to 0.6
we aimed for.

**Docking, scripted pilots.**

| Mission | Recalls a match | Docked a match | Completion | Of those not shot down | Seconds to dock, median | Relaunches a match | Hull restored a match |
|---|---|---|---|---|---|---|---|
| Carrier battle | 3.57 | 2.16 | 0.61 | 1.00 | 9.5 | 2.16 | 1.29 |
| Station assault | 2.60 | 1.66 | 0.64 | 0.97 | 10.2 | 1.60 | 0.84 |
| Citadel | 2.06 | 1.11 | 0.54 | 0.98 | 7.5 | 1.10 | 0.53 |

"Hull restored" is in whole hulls: a carrier battle gets back about one and a third
strike craft's worth of hull through its hangars. A recalled craft starts 160 to 180 m
from its bay (the citadel's garrison, which fights near home, 70 m). The ones that do not
make it are shot down soon after the order: half within 3 to 3.7 s, having closed 33 to
57 m of the distance (medians). They were already losing the fight they were in. Of the
few that neither docked nor died, the match ended first; a handful in 512 matches
circled the bay or came in too fast.

## 2. Live pilots, zero-shot

The strike craft are flown by the ten live pilots (`lab/live_pilots.json`), drawn per
slot per match, on both sides, under the scripted commanders, which recall them. None has
been trained on a dock order; all read 587 numbers or fewer, so they see a go-to with no
deadline whose point is next to their own carrier.

| Mission | Team 1 win, off | On | Recalls a match | Docked a match | Completion | Of those not shot down |
|---|---|---|---|---|---|---|
| Carrier battle | 0.539 ± 0.043 | 0.508 ± 0.043 | 4.81 | 0.08 | 0.02 | 0.14 |
| Station assault (attacker) | 0.371 ± 0.042 | 0.424 ± 0.043 | 5.00 | 0.07 | 0.01 | 0.20 |
| Citadel (attacker) | 0.268 ± 0.038 | 0.289 ± 0.039 | 3.12 | 0.04 | 0.01 | 0.24 |

**How they fail: two gaps.**

*They do not go home.* Nine recalls in ten end with the pilot shot down, and later than
the script's: half live 7 to 13 s past the order (the script: 3 s), but in that time
they close only 11 to 22 m of the 225 to 285 m to the bay (the script closes 33 to 57 m
in 3 s). They stay in the fight.

*The few that reach the bay fly through it.* From the moment a recalled craft first comes
within 30 m of its dock point:

| Run | Came within 30 m | Of them docked | Inside 10 m but never slow enough | Their slowest there, median |
|---|---|---|---|---|
| Script, carrier battle | 1,287 | 0.86 | 46 | 22 m/s |
| Script, station assault | 1,013 | 0.84 | 65 | 26 m/s |
| Script, citadel | 869 | 0.65 | 65 | 25 m/s |
| Pilots, carrier battle | 248 | 0.16 | 58 | 26 m/s |
| Pilots, station assault | 354 | 0.10 | 85 | 26 m/s |
| Pilots, citadel | 159 | 0.11 | 17 | 37 m/s |

For every pilot that docked, one or two more were inside the bay's 10 m and went through
it at 26 m/s or more (the bay takes 15). The script, which matches the carrier's
velocity, rarely does. A go-to is done once the ship is inside its radius at any speed,
and that is how these pilots fly it. About half the pilots' few docks in a carrier battle
came within a second of the order: craft already at the mouth, defending their carrier.

By pilot (carrier battles), the go-to trained `followers_v8_352` docks most (16 of 256
recalls; 0.40 of those not shot down), then `followers_pay3_810` (8) and `f99_696` (5);
the two `f995` pilots never docked there. Recalling them changes little else: no
mission's winner moves by two standard errors of the difference (the largest, the
station assault's +0.05, is 1.7), since a recalled pilot keeps fighting. It does take
the craft out of its squad, so it loses its squad's attack or defend order.

## Was reading the dock order as a go-to a crutch?

Partly, and that is why the obs now has its own dock signal.

- **The far part is a go-to.** Flying 200 m home under fire is what a go-to asks. The
  pilots' failure there (staying in the fight) is the weak obedience the drill bars
  already show for go-tos in a real fight; no input changes that, drills and pay do.
- **The near part is not.** A go-to ends inside its radius at any speed, and since v8 a
  deadline pays to get there fast. Docking needs the opposite: arrive slowly, at the
  carrier's velocity, from the bay's side. With only the go-to inputs a pilot taught to
  slow down at a dock point would also slow down at go-to points, or have to guess
  "dock" from its carrier being next to the point. And the go-to inputs give the point's
  position, not its velocity. The new block gives the flag, the bay's velocity relative
  to the ship and the bay's direction, and keeps the go-to reading for the older pilots.

## What we learned

- **The rule works for a pilot that flies it.** Nearly every scripted craft that
  survives the trip home docks, in 7 to 10 s; a carrier battle sees two docks and two
  relaunches a side.
- **The danger is the trip, not the bay.** Two recalls in five end with the craft shot
  down on the way. Recalling earlier and not under the enemy's guns is what made docking
  worth having; nothing about the bay needed loosening.
- **Docking does not change who wins.** Every mission stays within two standard errors
  of v10; the station assault stays balanced at 0.53 for the attacker.
- **The live pilots ignore the order, and overshoot when they do not.** 1 to 2 recalls
  in 100 end in a dock. They need a docking drill and training on the 592-number obs
  (stage 3) before the live page shows learned pilots docking.
- **Learned commanders never recall.** Until one is trained to (stage 4), a side run by
  a learned commander keeps its damaged craft in the fight.

## Not done here

The docking drill (stage 3) is not built: drills touch the sim's drill rules, the drill
generator, the ledger, the eval and the bars, more than fitted beside this change. No
training was run.
