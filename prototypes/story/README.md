# Story demo (scripted, no RL)

A looping exhibit of the whole match story, used to explore scope before the Rust sim:
a mission title card, a fleet draft between two scripted "commanders", jump-in, the
mission itself, a result, then the next mission.

Missions (`missions.js`): team deathmatch, flagship duel (carriers launch the drafted
wing from their bays), hold the beacon (an uncontested ring charges to 100%), and station
assault (attackers versus a pre-placed turreted station).

- `draft.js`: each pick deals a 5-card hand; the commander takes the affordable card
  with the best mission fit, counters to the enemy's picks so far, variety and persona
  taste. The whole draft is computed up front.
- `draftview.js`: replays it in about five seconds: hands dealt from the picking side,
  the choice lights up with its reason and flies onto the roster, beats speeding up.
- `thumbs.js`: renders the real hull models for the cards.
- `power.js`: shows the power split. Every ship divides its reactor output between its
  systems: shields, engines and weapons, or only engines and weapons on hulls without a
  shield (fighters, bombers). Shares sum to 1 and none may exceed a cap (0.6 three-way,
  0.8 two-way), so nothing runs everything at full; an even split is 1×, the cap about
  1.5-1.6×, starved 0.2×. The split slews at 0.45 per second, so a commitment takes time
  to undo. Shown as a shield bubble that glows when fed, engine plume length, a panel for
  one featured ship (tap a ship to pick it), and callouts when the featured ship, a
  carrier or the station shifts power. The scripted pilots switch between preset modes;
  a learned policy would set the split directly.
- `sim.js`: the scripted battle (a fork of the art-direction one, plus missions, bays,
  torpedoes, the static station and power management).
- `shared/`, `treatments/`: copied from `../art-direction/`. `hullgeo.js` adds the
  bomber, carrier and station (Codex). In portrait, the environment places scenery at the
  side edges because the camera turns 90°.

Serve this directory statically and open `index.html`. URL parameters:

- `mission=deathmatch|flagship|beacon|station`: pin one mission.
- `nodraft`: skip the draft animation.
- `warmup=<s>`: with `nodraft`, fast-forward the battle silently.
- `seed=<n>`, `focus=<shipId>`, `details`: as in the art-direction demo.

Keys: `N` next mission, `D` technical details.
