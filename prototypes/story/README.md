# Story demo (scripted, no RL)

A looping exhibit of the whole match story, used to explore scope before the Rust sim:
a mission title card, a fleet draft between two scripted "commanders", jump-in, the
mission itself, a result, then the next mission.

Missions (`missions.js`): team deathmatch, flagship duel (carriers launch the drafted
wing from their bays), hold the beacon (an uncontested ring charges to 100%), and station
assault (attackers versus a pre-placed turreted station).

- `draft.js`: picks scored by mission fit, counters to the enemy's picks so far, variety
  and persona taste; the whole draft is computed up front.
- `draftview.js`: replays it as cards with preference bars, lock-in reasons and roster chips.
- `thumbs.js`: renders the real hull models for the cards.
- `sim.js`: the scripted battle (a fork of the art-direction one, plus missions, bays,
  torpedoes and the static station).
- `shared/`, `treatments/`: copied from `../art-direction/`. `hullgeo.js` adds the
  bomber, carrier and station (Codex). In portrait, the environment places scenery at the
  side edges because the camera turns 90°.

Serve this directory statically and open `index.html`. URL parameters:

- `mission=deathmatch|flagship|beacon|station`: pin one mission.
- `nodraft`: skip the draft animation.
- `warmup=<s>`: with `nodraft`, fast-forward the battle silently.
- `seed=<n>`, `focus=<shipId>`, `details`: as in the art-direction demo.

Keys: `N` next mission, `D` technical details.
