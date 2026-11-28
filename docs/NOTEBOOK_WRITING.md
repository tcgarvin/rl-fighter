# Writing a notebook entry

The notebook (`/notebook/` on the site) is built by `tools/build_notebook.py` from
`lab/runs/<id>/results.md`, or from `plan.md` where an entry has no results yet. Each
entry should read like a short blog post that a college-educated professional, who
knows nothing about this project or about machine learning, can open cold and
understand: what was asked, what was done, what was found and why it matters. A reader
may land on any entry first, so every entry stands on its own.

## Shape of an entry

1. **Title** (the H1): a plain statement of the finding, short. Not a code name.
2. **Summary comment**: `<!-- summary: ... -->`, 2 to 4 plain sentences, before the
   first `##`. It is the card on the notebook index.
3. **Verdict line**, also before the first `##`: `Verdict: **PASS**` (or `PARTIAL`,
   `FAIL`), or the word "shipped", plus one plain sentence. Keep the number-heavy
   version for a `## Verdict in detail` section after the setup. The first screen of an
   entry should never be a wall of numbers.
4. **`## Where this fits`** (80 to 200 words): what RL Fighter is in a sentence, what
   happened before this night (linked), and why the question mattered then.
5. The setup, the results, the verdict in detail, and what comes next.

## Rules

- **Reading order.** Explain every term at or before its first use, reading top to
  bottom, including in the verdict line and table headers. A clause or a parenthesis is
  usually enough. Don't explain the same term twice in one entry. The glossary below
  gives the agreed wording.
- **Link earlier work.** Every mention of an earlier night, run, pilot or decision
  links to its entry with a relative link, `[the order-cost night](../2026-11-17-order-cost/results.md)`
  (or `../<id>/plan.md`), plus enough of a phrase that the reader need not follow it.
  The build rewrites these to notebook anchors and fails on a link to a missing file.
  Site pages: `/pilot/`, `/commander/`, `/hulls/`, `/`.
- **Tables.** Say in a sentence what the rows and columns measure and how to read them
  ("each number is the share of matches won against the script; 0.5 is an even fight").
  Explain ± once per entry.
- **Units.** "Costs 0.37 of a 3 v 3" is shorthand. Say "costs a side 0.37 in win rate,
  out of 1, in 3 v 3 fights" at first use. Write ranges as "0.27 to 0.33 (for 1052)",
  never chains.
- **Pilots.** Keep a pilot's real name in code font (`kite_2205`), but say what it is
  the first time it appears. Check its record in
  `lab/population/<season>/members/<id>.json` first.
- **Missions and hulls.** Where one matters to the story, describe it in a clause at
  first use. Readers could not picture them otherwise.
- **People.** "The owner" for the user. Design reviews involve the owner and the lab's
  AI assistants; say that rather than naming roles.
- **Dense records** (parameter lists, deviations): keep them, with a sentence saying a
  reader can skip them, or move them under `## Details` near the end.
- **Figures.** Shared explainer diagrams live in `web/notebook/diagrams/<name>.svg`
  and go in with `<div data-figure="diagram" data-name="<name>" data-caption="..."></div>`
  (optional `data-title`). Check the ones there before drawing a new one. Films go in
  with `<div data-figure="compare" ...>` (see `CLAUDE.md`). Where a picture would help
  but none exists, leave `<!-- figure-idea: ... -->` (dropped on render; start it with
  `shared:` if many entries could use it).
- **Voice.** Short, plain, declarative sentences, "we", numbers stated exactly. Say how
  sure we are ("within the noise", "we have not tested whether"). No hype or filler, no
  dashes or semicolons in prose.
- **Facts.** Never round, strengthen or soften a result to make it read better. If a
  later fact overrides an earlier one in the same entry, add a note rather than delete
  the record.

## Parts the build reads

- The H1 is the title. Keep any `<!-- hand:NAME -->` markers exactly.
- The verdict is parsed only from text before the first `##`: `verdict: **PASS**`, a
  `| Verdict |` row, or the word "shipped". Don't put those words there by accident.
- The first `SIM_VERSION n` or `sim vN` in the file sets the entry's season. Don't
  mention an earlier version before it.
- `<div data-figure="matchups|compare">` lines are figures. Keep them as they are.

## Glossary: agreed plain explanations

Check the entry's date: some things changed over time (the live page had one pilot
until 2026-11-02 and ten after, WAR began 2026-11-09).

**The game**
- **RL Fighter**: a space-combat game where every ship is flown by a small neural
  network that learned to fly by trial and error (reinforcement learning, "RL").
- **The sim**: the program that runs the game's physics and rules, thousands of
  matches at once and far faster than real time, for training.
- **`SIM_VERSION` n**: the version of the game's rules. It goes up when a rule changes.
  Pilots are compared only within one version (a **season**).
- **The live page**: the site's front page, which plays matches forever with the
  current pilots and commanders.
- **Strike craft**: the small piloted ships. The **fighter** and **strafer** have guns
  fixed to the nose, so they must point at a target to shoot. The **gunship** is slower,
  with turrets that aim on their own. The **bomber** (v9 on) is slow, with a torpedo
  fixed to its nose for hitting big ships.
- **Capital ships**, flown by scripts: **carrier** (launches strike craft and takes them
  back), **freighter** (the convoy's cargo ship), **station** (a static base),
  **citadel** (a much bigger station whose turrets and launch bays can each be shot
  off), **dreadnought** (a heavy warship that attacks the citadel).
- **Team deathmatch / fleet fight**: strike craft only, 1 to 4 a side ("3 v 3" is three
  a side). A side wins by destroying every enemy. At the time limit (90 s) the side
  with more hull and shields left wins.
- **Carrier battle**: each side has a carrier that launches its strike craft. A side
  wins by destroying the enemy carrier, or at the time limit by having more carrier
  hull left.
- **Convoy escort**: one side's escorts guard freighters flying to a jump point, where
  they charge and jump out. The attacker wins by destroying at least half the
  freighters.
- **Station assault** (v9 on): a static station defends with its own ships and
  reserve. The attacker brings a carrier, bombers and (v10) a dreadnought, and wins
  only by destroying the station. At the time limit (150 s) the defender wins. From v10
  the station on the live page is always the citadel.
- **Carrier reading / convoy reading**: networks trained before the station assault
  existed see it presented as a mission they know, the station as a carrier or as a
  convoy.
- **Roster**: the ships each side gets. A **roster class** is a group of similar ones.
- **Dock and repair** (v11): a damaged strike craft flies home to its carrier or
  station, lands, is repaired and launches again. A **recall** orders it home.

**Who flies**
- **Pilot**: the small network that flies one ship. Many times a second it looks at
  the battle from its own ship and sets every thruster, turret and trigger directly.
  There is no autopilot, so any behaviour has to be learned. One pilot flies every hull.
- **The script**: a pilot written by hand as rules. It is the yardstick learned pilots
  are measured against.
- **Commander**: a network (or the hand-written **scripted commander**) that sees the
  whole side and gives orders. An **external commander** is one outside the sim that
  sends it orders. "No orders", "the unseen side" or "a free pilot" mean pilots who get
  no orders and fight on their own judgment.
- **Orders**: **attack** (a named enemy), **defend** (stay near a friendly ship, the
  **ward**), **go-to** (fly to a point, from v8 optionally by a deadline), **dock**,
  **hold**. A **hidden** order is one the pilot is not shown, to measure what seeing it
  changes. **`nearest`** orders each ship onto the enemy nearest it.

**How pilots are trained**
- **Reward**: points the network gets during training for good outcomes, so it learns
  to do more of what earned them.
- **PPO**: the trial-and-error training method we use. Usually just say "training".
- **Update**: one round of training (play a batch of matches, adjust the network once).
  A night is a few thousand. A pilot's name ends with the update it was saved at.
- **Checkpoint**: a saved copy of a network at some update.
- **BC (behaviour cloning)**: training a network to copy the script, as a head start.
  **DAgger**: the copy flies and the script says what it would have done there.
  **Script pull** or **teacher**: a term that pulls the pilot back toward the script.
- **KL anchor**: a term that penalises a network for drifting too far from another
  network's choices.
- **Discount / horizon** (0.99, 0.995, 0.998): how far ahead the pilot weighs future
  reward. 0.995 looks roughly twice as far ahead as 0.99.
- **Entropy bonus**: keeps some randomness in the network's choices so it explores.
- **Critic**: a second network used only in training, which predicts how well things
  will go.
- **Inputs**: the numbers a pilot sees each moment. Going from 583 to 587 inputs means
  giving it new information.
- **Arm**: one version of an experiment. A night often trains two or three arms that
  differ in one setting. **Seed**: the random number that sets up a run, so two seeds
  show how much is luck (a "pool seed" is a different thing, a fixed opponent placed in
  training).
- **Line / family**: a pilot and its descendants. Training usually starts from an
  existing pilot (the **parent**), giving a **child**.
- **Drills**: short practice scenarios for one skill. **Drill share**: the fraction of
  training spent in them. **School**: a run that was mostly drills.
- **Teammates**: frozen pilots flying some of the learner's own side's ships.
- **Ablation**: removing one ingredient at a time to see which caused an effect.
- **Beast**: the lab's desktop with two graphics cards. The laptop and a Mac Mini also
  run jobs.

**How pilots are measured**
- **Eval**: matches played only to measure. **Win rate**: share won, from 0 to 1, a
  draw counting half.
- **±**: the margin of error (95%). Ranges that overlap may not really differ.
- **Fleet suite**: 16 fixed deathmatch line-ups against the script, 1 v 1 to 4 v 4.
- **The order-cost test**: 3 v 3, one side's pilots ordered, the other flown by
  `followers_school_1052` with no orders, from
  [the order-cost night](../lab/runs/2026-11-17-order-cost/results.md). **Paired cost**:
  the same matches with orders shown and hidden.
- **Season / population / members**: all pilots trained under one rules version. A
  **founder** comes from outside the family tree. **Archived** is a status in the
  records whose meaning changed over November: check the member record and the entry
  for what it did at that date.
- **Round robin / combat rating**: every pilot plays every other with no commanders.
  The rating works like a chess rating (a gap of 100 is about 64 wins to 36).
- **WAR (wins above replacement)**, from 2026-11-09: borrowed from baseball. Pilots are
  dropped at random into matches like the live page's, and a fit estimates how many
  more matches in 100 a side wins with that pilot instead of the script. Compare pilots
  within one WAR table, not across nights.
- **The live ten**: the ten pilots the live page draws from, picked by WAR from
  2026-11-09.
- **Gate / bar**: a pass mark set in advance. From 2026-11-20 new pilots face no gates:
  they join the population and WAR decides who flies live.
- **Swap cost**: how a side's result changes when one ship becomes another hull flown
  by the same pilot.

## Pilot lines

- **`f995` / `f99`**: from the Fighters v2 night, named for their discount. Strong
  fighters that ignore orders. `f995_701` founded the fighters family.
- **`fighters_...`**: descended from `f995_701`, bred to win fights.
  `fighters_pay1_...` was paid less for following orders.
- **`followers_...`**: descended from `transit_300` (followed orders well, fought
  weakly), bred to fight and follow. `followers_school_...` went through go-to school,
  `followers_dock_...` learned to dock.
- **`kite_...`**: followers drilled against a target that backs away and fights back.
- **`dock_...`**: children of `followers_dock_v8_2676`, from the horizon-bombers and
  fight-ablation nights.
- **`_v8_`**: widened to read go-to deadlines (rules v8).
