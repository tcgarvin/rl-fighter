# Dock and repair: plan (SIM_VERSION 11)

The owner noticed on 2026-11-20 that strike craft never come home: the sim only launches
from a hangar. The story demo's flagship mission had craft fly back, dock, repair and
relaunch; this brings that into the Rust sim. Retreats, withdrawals and surrender are
out of scope (the owner's call).

The rules as built are `docs/SIM_SPEC.md` §0.9 (changes table) and §5.11 (the rules).
This page is the design and the numbers.

## Stages

1. **The sim rule and the scripted recall (this entry).** A dock order, the docking
   rule, repair, relaunch, bindings, the scripted commander recalling and the scripted
   pilot flying it. Measure script against script and the live pilots zero-shot.
2. **The live page (a web agent, next).** Show recalls, the approach, the dock, the
   hangar repair and the relaunch from the new events and the dock view.
3. **A docking drill, if the zero-shot pilots need one.** Started here if time allows
   (results.md says whether), scored for the script and the live pilots; no training
   run.
4. **The learned commander decides recalls.** It gets the recall in its action space (a
   `COMMANDER_IO_VERSION` bump) and is trained to use it. Until then a learned commander
   never recalls.

## Design

**The order.** `Order::Dock { carrier, bay }` is a ship's own order, not a squad's,
stored per slot in `Match.dock`. It wins over the squad's order while it lasts, and the
ship leaves its squad when it gets it.

**What the pilot sees** (`docs/SIM_SPEC.md` §7.2). The first version read the order to
every net as a plain go-to to the bay's dock point (radius 10 m, no deadline), so the
obs stayed 587 floats. The zero-shot numbers (results.md) showed the cost: the few live
pilots that reached the mouth mostly went through it at 26 m/s, as a go-to allows, and
the obs could not tell them how the bay was moving. The owner then asked for a separate
"dock here" signal, so v11 appends a 5-float `dock` block (587 to 592):

- a dock flag (the order kind's own entry for a v11 pilot);
- the dock point's velocity relative to the ship (body frame): the bay catches a ship
  moving with it, and a go-to's point velocity reads zero;
- the bay's outward direction (body frame): the side to come in from.

Nothing else: distance, closeness and the radius are in the go-to reading already. In
the first 587 floats the dock order still reads as a go-to to the bay mouth, which is
what a v8 to v10 pilot sees (it reads its own 587-float prefix), so the zero-shot
measurement keeps its meaning and today's pilots can still try it. The commander's
inputs are unchanged (`COMMANDER_IO_VERSION` 1; its order one-hot reads go-to).

Unlike a go-to the dock order does not end when the ship is inside the radius: a pilot
trained on go-tos treats "inside" as done and flies its role again, which here would
mean circling the bay forever. It ends when the ship docks.

**The dock point** is the bay mouth plus 8 m along the bay direction: where a launched
light craft appears (bound radius plus 1 m, 6 m for a fighter), rounded out so a
gunship's centre there is clear of the carrier's circles.

**Docking is a rule, not an autopilot.** At the end of every step, a ship holding a dock
order docks if it is within 10 m of the dock point of *any* live bay of its carrier and
its velocity is within 15 m/s of that point's (carrier velocity plus its spin). Any live
bay rather than only the ordered one: the citadel has four mouths facing four gaps, and a
craft that lines up on the wrong one should not be sent round again. The ordered bay is
the one the obs shows; it is the live bay whose dock point was nearest when the order was
given, re-picked if it is destroyed. A destroyed bay never takes a craft in; with no
live bay left, or the carrier gone, the order is dropped.

**In the hangar.** The ship leaves the field as a reserve does and joins the back of the
hangar with its shield full. Its hull repairs at 5% of the maximum a second. It may
launch again 4 s after docking. The ordinary launch takes the first reserve that may
launch, so fresh reserves go first, and the relaunched craft is the same slot: same
pilot, same identity on the live page and in the inspector. If the carrier dies, the
hangar dies with it, returned ships included.

**Who recalls.** Only a commander. The first version of this entry had a sim-side
"recall doctrine" that recalled damaged craft under every commander, learned ones
included, as a stopgap; the owner removed it the same day: no shortcuts where the models
have not learned to dock, since we want to teach it. So:

- The **scripted commander** recalls, on its slow tick, every own strike craft on the
  field below half its hull while its carrier is up with a live bay. Two exceptions: a
  craft finishing a kill (its attack target within its reach and below a quarter of its
  hull), and a craft under an enemy capital ship's guns (within that ship's longest
  weapon range plus 40 m), which is recalled once it is clear.
- The **random commander** keeps the scripted commander's logistics, launches and now
  recalls, and draws only the squad orders, so it recalls the same way.
- An **external** commander may send the `dock` command.
- A **learned** commander has no recall output and never recalls, until stage 4.
- Hiding orders from the pilots (the commander eval's "unseen" side) changes only what
  the pilots see; the recalls are the same.

**The script.** A docking scripted pilot keeps station on a point on the bay axis that
slides into the dock point as it closes (half its distance out along the bay direction,
at most 80 m), so it comes in from the open side of the bay; it matches the carrier's
velocity with a pull of 0.8 /s, runs engines (and shields) power, and leaves its own
carrier out of crash avoidance (the dock point is inside the carrier's bounding circle,
which avoidance would otherwise refuse to enter at speed). The scripted commander keeps
recalled craft out of its squads and relaunches a returned craft once repaired to 90% of
its hull, or past half when it scrambles, in the last minute, or when its station is
alarmed, so that nothing it launches is recalled again on its way out of the bay.

**Gating.** All of it needs `MatchConfig.docking` (default true) and a carrier in the
match. With docking off every match is v10's bit for bit (`v10_compat_*` replays all
thirteen v10 traces); a deathmatch or a convoy, which have no carrier, are v10's either
way, state hash included. The obs is 592 wide either way; with no dock order its last
five floats are zero.

## Numbers

| Constant | Value | Tuned |
|---|---|---|
| Dock point offset | 8 m | no |
| Capture radius | 10 m | kept (the start value) |
| Max relative speed | 15 m/s | kept |
| Repair | 5% of max hull a second | kept |
| Turnaround | 4 s | kept |
| Recall threshold | 50% of hull | 30% → 60% → 50% |
| Finishing a kill | target below 25% of its hull, within reach | no |
| Under capital guns | within its longest range + 40 m | added after measuring |
| Script relaunch | at 90% hull, or 50% when urgent | the urgent floor added after the pilots' first run |
| Script approach pull | 0.8 /s | 0.5 → 0.8 |

How they were chosen is in `results.md` ("Tuning").

## Measurements

`run.sh` (nice 19, 8 threads): `dock_eval.py` for every mission with the dock rules off
and on, script against script, 512 matches each; the live pilots zero-shot on both sides
of the three missions with a carrier, docking on and off; the Rust harness by roster.
`summary.py` prints the tables.
