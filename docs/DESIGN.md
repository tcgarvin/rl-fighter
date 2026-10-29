# RL Fighter — Design (v2)

Status: living document, started 2026-10-27. This replaces `SPEC.md`, `SIMULATION.md`
and `RL.md` as the source of truth; those describe the v1 NumPy prototype and are kept
for history.

The nightly lab agent reads this file at the start of every run. Keep it current: when
a decision changes, change it here, and record the reason in the lab journal.

---

## 1. Vision

A live, always-on space battle on the web at **rl-fighter.tcgarvin.com**. Fleets of
very different ships fight, controlled by policies that learn every night. Anyone can
open the page and watch the latest state of the experiment, and leave it running on a
screen for hours.

Three threads run through the project:

1. **Heterogeneous ships.** Hulls differ in *how they are controlled*, not only in
   stats. Thruster layouts, turrets, launch bays and stranger mechanisms all come from
   data.
2. **Hierarchy.** Pilots fly ships at the actuator level. A commander decides what to
   launch, and when, and issues orders. A fleet-drafting layer comes later.
3. **A public, autonomous lab.** An agent wakes every night, picks an experiment, runs
   it, writes it up in a public journal, and deploys the result live.

## 2. Principles

- **One simulation, one source of truth.** The sim is written once in Rust. It is
  compiled to WebAssembly for the browser and to a Python extension for training.
  There is no second implementation to keep in sync.
- **Strictly 2D physics, rendered in 3D.** Ships live on a plane. three.js provides
  depth, light and effects. A 3D sim would be a separate project and is out of scope.
- **No autopilot actions.** A pilot policy controls each thruster and turret
  directly; the commander controls the launch bays. Following, formations and
  strafing runs must *emerge*, from learning, reward shaping, or orders passed in as
  goals. An action never executes a behaviour on the ship's behalf.
- **One pilot per ship.** Every ship is flown by its own pilot decision from its
  own observation. A squad is only a grouping the commander addresses orders to; it
  never shares controls, and three ships never act as one mechanically.
- **Hulls are data.** A new hull is a model plus a YAML file, and needs no code. The
  physics properties are derived from those files, and validated against them.
- **Deterministic.** The same seed, bundle and policies give the same match on the
  training machine and in any browser.
- **Develop in public.** Every promoted change goes straight to the live site.
  There are no preview branches.

## 3. Architecture

```
crates/
  sim/          # Rust core: state, physics, weapons, damage, match flow. No I/O.
  sim-py/       # PyO3 bindings: batched VecEnv over N matches, zero-copy numpy views
  sim-wasm/     # wasm-bindgen bindings: one live match + policy inference
spacefight/     # Python: env wrapper, policies, PPO, eval, scripted controllers
assets/hulls/<name>/
  hull.yaml     # gameplay definition (references mount nodes in the model)
  model.glb     # visual model with named mount empties
web/            # three.js client (Vite + TypeScript)
lab/
  backlog.md    # experiment ideas, added by the user or the agent
  runs/<date>-<slug>/   # one directory per nightly run: plan, config, results, verdict
  champions/    # promoted bundles (weights + manifest), the league history
tools/          # hull validator, bundle builder, deploy script
docs/DESIGN.md  # this file
docs/SIM_SPEC.md # M1 implementation spec for the sim and bindings
```

**Bundle.** The unit of deployment: sim WASM, the hull catalogue (YAML + GLB),
policy weights, and a `manifest.json` carrying `sim_version`, the bundle id, the
champion ids and the journal entry. The browser loads a bundle as one piece. A new
bundle is swapped in only between matches. If it fails to load, the page falls back
to the last known-good bundle.

**`sim_version`** is bumped whenever a change alters physics or observations in a way
that invalidates trained policies. A bump starts a new **season**: old champions
retire from the active league, though they stay in history.

## 4. Simulation

- **Time step:** fixed, 30 Hz. All arithmetic is `f32`, using the `libm` crate for
  transcendental functions, so native and WASM builds produce identical results. The
  RNG is a seeded PCG, one stream per match.
- **Ships:** 2D rigid bodies, each with position, velocity, heading, angular velocity,
  mass and moment of inertia. There is mild linear and angular drag, so ships settle
  rather than drifting forever, and a soft speed cap per hull.
- **Thrusters:** each has a mount point (in the body frame), a thrust direction, a
  maximum force, and discrete throttle levels `{0, ½, 1}`. Force is applied at the
  mount, so an off-centre thruster produces torque. Turning, strafing and pivoting all
  come from the thruster layout.
- **Turrets:** each has a mount point, a rest angle, a firing arc and a slew rate.
  Its action is `{slew left, hold, slew right} × {hold fire, fire}`. Fixed guns are
  turrets with an arc of zero.
- **Weapons** (data-driven, as in v1): bullets, hitscan beams and guided missiles,
  each with magazine, reload, energy and damage-type properties.
- **Power split:** every ship divides its reactor output between shields, engines and
  weapons (engines and weapons only, on shieldless hulls). Shares sum to 1, none may
  exceed a cap (0.6 three-way, 0.8 two-way), and the split slews toward its target at
  0.45 per second, so a commitment takes time to undo. An even split runs each system
  at 1×; starved, 0.2×; at the cap, about 1.5–1.6×. The policy sets the target split
  directly; it is an actuator, not a mode. Prototyped in `prototypes/story/power.js`.
- **Bays:** launch a hull from the fleet's queue at the bay's mount point. Strike craft
  below a hull threshold may fly back, dock, repair and relaunch (prototyped in the
  story demo's flagship mission); docking is flown by the pilot, not automated.
- **Collision:** each hull is a compound of circles derived from the model's
  footprint. Projectiles are tested against those circles, using swept segments for
  fast bullets. Ships can collide with each other; the impulse depends on mass.
- **Damage:** hull HP. Some hulls (not all) also carry a **shield**: a pool of shield
  HP that absorbs incoming damage first, then regenerates after a delay with no hits.
  The sim emits a shield-hit event with the impact point and normal. Shields are
  invisible until they deflect fire. Armour and damage-type resistances are data fields
  for later.
- **Arrival (jump-in):** a match starts with an empty field. Each squad has an entry
  point and heading. Its ships appear with staggered delays of tens to hundreds of
  milliseconds, already moving at a residual forward velocity. They coast briefly with
  their controls locked, then their policy takes over. The sim decides arrival times
  and velocities; the renderer draws the jump: a very fast (~55 ms) streak in from
  off-screen and a brief soft flash on landing, with no shockwave ring or afterglow.
  Squads arrive about 300 ms apart.
- **Arena:** a bounded disc. Outside it a soft force pushes ships back and HP
  drains slowly. Match setup chooses the arena size.
- **Projectile pool:** fixed size per match, recycling the oldest entry first, as in
  v1.

Ships that are mounted to or tethered to other ships (sub-agents, bolas) are expected
later. Hit detection and friendly-fire filtering must treat "attached" as a first-class
relation before the first such hull lands.

## 5. Hulls: model and YAML designed together

A hull is designed collaboratively. The art agent (Codex, `gpt-6.1-sol`) drafts the
model. The art agent and Claude then agree where the thrusters, turrets and bays are
mounted, and the gameplay numbers are tuned against the result.

**The model is the source of geometry.** `model.glb` contains named empty nodes, one
per mount:

```
thruster.main.0, thruster.rcs.fl, thruster.rcs.fr, ...
turret.dorsal, turret.ventral
bay.port
```

Each empty's local +X axis is its thrust or rest direction. The model's footprint,
projected onto the plane, provides the collision circles.

**The YAML is the source of behaviour:**

```yaml
name: lancer
role: fighter
hp: 120
mass: 10.0                 # moment of inertia is derived from the footprint
speed_cap: 260
thrusters:
  - mount: thruster.main.0
    max_force: 2400
  - mount: thruster.rcs.fl
    max_force: 300
  # ...
turrets:
  - mount: turret.nose
    weapon: gauss_gun
    arc_deg: 0             # fixed forward gun
    slew_deg_s: 0
bays: []
cost: 40                   # supply cost to launch
```

`tools/validate_hull` checks that every mount the YAML names exists in the model, that
every mount in the model is used, that thrusters can produce both rotation directions
(a warning, not an error, because weird hulls are allowed), and that derived mass
properties are sane. It also writes `derived.json` with the collision circles and
inertia, and the sim reads that file. The validator runs in CI and in the nightly lab.

**Starting catalogue:** three hulls that cover distinct control schemes.

| Hull | Control scheme | Role |
|---|---|---|
| Fighter | main engine + 4 RCS thrusters, fixed nose gun | dogfighter |
| Strafer | lateral thruster pairs plus a weak main engine | skirmisher, circle-strafes |
| Gunship | slow hull, 2–3 independent turrets | anchor, anti-fighter |

The flagship (turrets plus bays) follows when the match structure lands.

Backlog of later hulls: comet (impulse-only rammer), bolas (tether pair), minelayer,
gravity tug, reflector, drone swarm, carrier.

## 6. Match structure

The match has three phases, designed for a spectator to follow without explanation:

1. **Muster** (shown for about 10 seconds). Each side's fleet roster is displayed. To
   begin with, the rosters come from a scripted or random draft against a budget.
2. **Arrival.** The field starts empty. The fleets jump in squad by squad at opposite
   ends of the arena: an extremely fast streak from off-screen, staggered by
   milliseconds, ending with the ships already moving forward. Each side has a
   **flagship**: if it dies, that side loses.
3. **Battle.** Supply accrues over time. Flagships launch ships from their bays,
   spending supply. The matchups are rock-paper-scissors: bombers beat capital ships,
   fighters beat bombers, and flak turrets beat fighters. Control rings, added later,
   boost supply. The match ends when a flagship dies, or at a time limit, after which
   the side with the most remaining value wins.

Between matches, the page shows the result and starts the next match. It loops
forever.

The scripted story demo (`prototypes/story/`, live on the site until M2) explored
this further, and its choices are the working plan: drafting deals 5-card hands and
fighter/bomber cards are whole flights (×3 and ×2); a carrier brings an air wing; and
there are four mission types: team deathmatch, flagship duel, hold the beacon, and
station assault (attackers against a pre-placed, turreted, immobile station).

**Staging:** the first build is a plain skirmish (fixed fleets, no economy). Then
flagships and supply, with a scripted commander. Then a learned commander. Then
learned drafting.

## 7. Learning

### Pilots

- **Observations** are a set of entities expressed in the ship's own body frame:
  self, other ships (team, hull id, relative position and velocity, heading, HP), the
  nearest projectiles, objectives, and the current order. A hull-specific block
  describes the ship's own actuators (mount positions, directions, turret angles,
  ammunition).
- **Policy:** an attention encoder over entity tokens. Each actuator is a query token,
  and each actuator token outputs its own categorical action. One network serves every
  hull, including hulls added after it was trained. This is the default bet, not a
  law: the bundle manifest maps each hull to a pilot net, so a hull class can split
  off if a shared net measurably underserves it (M3 runs a shared-vs-specialist
  comparison at equal samples).
- **Critic:** centralised per team (MAPPO), attending over all of that team's
  entities.
- **Algorithm:** PPO with GAE, carried over from v1, plus the v1 retroactive
  projectile credit assignment.
- **Self-play league:** the current policy plus a pool of past champions, sampled so
  the policy can't overfit to its latest self.

### Hierarchy

The commander runs on a slow tick (about every 2 seconds). Its observation is coarse:
supply, roster and alive counts per hull, flagship HP, enemy composition, and
objective state. Its actions are launch decisions (it owns the flagship's bays) and
**orders** for each squad (role plus a target point or entity). A squad is a set of
ships the commander groups for one order; each ship still has its own pilot.

Orders reach pilots as observation tokens. Pilots receive a small shaped reward for
progress on their order, alongside the team reward. This is goal-conditioned
("feudal") RL. The commander is first scripted, then learned with its own PPO
learner at the slow tick. Pilots train on randomly sampled orders as well as the
commander's, so they follow any order rather than only the ones a script issues, and
eval measures order-following.

**Retreat** is an order. When defeat is certain, a commander may salvage remaining
fleet value by pulling ships back. Reward it only enough to be worth doing in a
lost position: a retreat must never beat fighting a winnable or even battle, and
eval watches the retreat rate the way it watches kiting.

### Scripted controllers and handwired experiments

Flying by individual actuators is hard to learn from scratch. So each new hull gets
a scripted controller: a thruster allocator plus pursue, aim and fire logic. It is
used in several ways:

- as a baseline opponent in evals;
- for **behaviour cloning**, then PPO with a decaying KL penalty toward the script;
- as a **residual policy**: logits = script + learned correction, with the
  correction initialised to zero;
- as an experiment backlog item, compiling a script into a network in the style of
  [handwired](https://github.com/chenglou/handwired), with softened comparisons, and
  comparing the learning curves against the approaches above.

Scripts are training aids, mostly for the early days. A scripted controller (or a
residual policy built on one) never flies a ship on the live site; only learned
champions do.

### Compute

There is no GPU for now: training runs on a 16-core CPU laptop, roughly 4 hours a
night. Keep the networks small (a model dimension of about 64–128, 2 attention
layers), and lean on the speed of the Rust sim. The GPU host (`192.168.50.202`) will
become an optional training target once it is back.

## 8. Evaluation and promotion

`spacefight/eval/` is the fixed yardstick. It is the only thing allowed to decide a
promotion.

- **Strength:** an Elo rating against the league of current-season champions, plus
  win rate against the scripted baseline.
- **Watchability:** engagement rate (ship pairs within weapon range), the spread of
  time-to-kill, lead changes, the share of time spent firing versus drifting, how many
  hulls are used and how they survive, and how long matches last. Strong-but-boring
  policies (kiting at maximum range, for example) must lose promotion.
- **Health:** no NaNs, no stuck ships, and no regression on a fixed set of seeded
  scenarios.

A champion is promoted when it beats the current champion's Elo by a margin and does
not regress on watchability or health. Thresholds live in `spacefight/eval/gates.yaml`.

**Rule:** a nightly run may change the eval harness, but a run that changes the
harness cannot promote a champion in the same night. The new yardstick applies from
the next run.

## 9. Web client

- **Stack:** Vite + TypeScript + three.js, with the sim and policy inference in WASM.
  The sim and inference run in a Web Worker. The main thread renders by interpolating
  between sim ticks.
- **Camera (v1):** a fixed top-down/oblique view that frames all the live ships, with
  smoothed zoom and pan. A director camera is future work.
- **Visuals:** per-thruster exhaust driven by the throttle actions; turret meshes
  follow the sim's turret angles; projectiles, hits and explosions. Optionally, the
  commander's orders as lines and markers.
- **No health bars.** Damage shows on the ship itself: smoke, then flame, then
  electrical arcing as HP falls. Smoke stays thin over the hull and thickens as it
  trails, so it never hides a slow-moving ship. A "technical details" toggle shows HP, shields,
  throttles and other numbers for anyone who wants them.
- **Perf readout:** a small debug figure in the upper right shows the tick budget's
  headroom (sim + inference time per tick against the 33 ms of a 30 Hz tick), so
  phone performance stays visible as the pilot net grows.
- **Shields** are invisible until they deflect a hit; then a brief, local ripple shows
  at the impact point.
- **Scenery** has two layers. (1) A rigid **backdrop**: the starfield, nebulae and
  large painted bodies (planets, rings, moons). Its parts never move relative to each
  other. The layer is anchored to the screen, and the whole of it shifts slightly as
  the camera moves; per-object parallax between planets and stars looked wrong.
  Bodies sit at the screen edges or corners, preferring the viewport's long axis,
  rarely behind the battle. (2) World-space **foreground dust** that the ships and
  camera visibly move against. Scenery is generated procedurally from the match
  seed, with enough variety that it never feels like a rotation.
- **Pages:**
  - `/` is the live match.
  - `/journal` is the lab journal, generated from `lab/runs/`.
  - `/hulls` is the hull catalogue.
- **Performance target:** 60 fps on Intel Iris Xe-class integrated graphics, with
  hours of uptime and no memory growth. A soak test is part of CI.
- **Hosting:** a separate Netlify site (`rl-fighter`, id
  `fc4f1b89-61db-4eab-89b8-f3c4bfdf6080`) on `rl-fighter.tcgarvin.com`; DNS is a
  Cloudflare CNAME to `rl-fighter.netlify.app`. Deploys run from this machine with
  `scripts/deploy.sh` (Netlify CLI, no Netlify-side build) using `NETLIFY_AUTH_TOKEN`
  from the gitignored `.env`. Netlify personal tokens are account-wide, so the
  "only this site" rule in §10 is policy, not enforced by the token. The vibe
  gallery on `tcgarvin.com` links to it.

## 10. Nightly lab

- **When:** about 03:00–07:00 local time, on the laptop. If the laptop is off or
  asleep, the night is skipped; we don't engineer around it. A systemd user timer
  starts a headless Claude Code session. A hard stop at 07:00 kills training and
  leaves the repo in a committed state.
- **The flow:**
  1. Read this file, `lab/backlog.md`, and the last few runs.
  2. Choose one experiment and write `plan.md` *before* running anything.
  3. Implement and run it on a branch.
  4. Evaluate it with the fixed harness.
  5. Write the results and a verdict, in a format suited to the public journal.
  6. If the gates pass, merge to `main`, build a bundle, and deploy live. If they
     don't, keep the branch and record the negative result. Negative results get
     published too.
- **Experiment menu** (not exhaustive):
  - fine-tune the current champion;
  - add or retune a hull, with the art agent;
  - change rewards or curriculum;
  - try new architectures or algorithms;
  - add match-structure features;
  - try handwired or scripted initialisations;
  - work on the web client.
- **Powers:** the agent may change any code, add hulls, push to `main` and deploy.
  It may not edit the gates in the same run that it promotes (see §8), rewrite git
  history, or touch anything outside this repo and its Netlify site.
- **Budget:** the time box is the main limit. Every run ends with a journal entry,
  even if it crashed.

## 11. Art direction

The art agent is Codex (`gpt-6.1-sol`). Its responsibilities:

- the style guide: palette, shape language, how factions are told apart, how
  silhouettes encode role;
- the shared material and part kit, and a model draft for each hull;
- review of each new hull from headless-browser screenshots.

Art-direction options were explored in `prototypes/art-direction/`, each as a
scripted (non-RL) demo match.

**Chosen (2026-10-28): Cinematic** (`prototypes/art-direction/treatments/cinematic.js`).
It is a linear HDR "photographed" look: clearcoated metal under an amber key light
and teal rim, quarter-resolution halation, a restrained anamorphic streak, a teal
shadow grade, a soft vignette and fine grain. Every HDR read in post is made finite,
because iOS half-float targets otherwise smear NaN/Inf into black blocks. The shared
hull models, the two-layer backdrop and the effects carry over to the real client
unchanged.

Feedback from round 1 (2026-10-27):

- Explore **rendering treatments** (materials, shaders, post-processing, e.g. a
  tilt-shift "miniature photograph"), not palette swaps. Hull geometry is shared
  across treatments, and each treatment fills the model's material slots.
- Keep the explosions from the round-1 "Abyssal Organisms" style.

## 12. Roadmap

1. **M0, Art direction. Done (2026-10-28).** Cinematic chosen (§11); the scripted
   demo is live on the subdomain as a placeholder.
2. **M1, Sim core** (specified in `docs/SIM_SPEC.md`). **M1a:** the Rust crate, three
   hulls, thruster physics, power split, weapons, shields, hits, a scripted fighter,
   and a determinism test comparing native and WASM builds. **M1b:** the PyO3 batched
   VecEnv and a throughput benchmark.
3. **Learnability spike. Done (2026-10-29), PASS:** BC → DAgger → PPO beat the script 512/512; PPO from scratch never learned to fire (`lab/runs/2026-10-28-learnability-spike/results.md`). A first live duel page is at `/duel/`. (Moved ahead of the web client, 2026-10-28.) Fighter vs.
   fighter with a small MLP: behaviour cloning from the scripted controller, then PPO,
   on the CPU. The question: can actuator-level control learn in a night? It is the
   project's biggest risk; the web client is not, and the story demo holds the site.
4. **M2, Live web.** The WASM client with a scripted match, the fit-all camera, and
   journal page scaffolding. Hosting and `scripts/deploy.sh` already exist (§9); M2
   moves the site from the scripted story demo (`prototypes/story/`) to `web/`.
5. **M3, Pilots learn.** The attention policy, eval harness v1, the self-play league,
   and the first champion deployed.
6. **M4, Nightly lab on.** Starting with conservative experiments (fine-tuning, hull
   tuning).
7. **M5, Fleet battles.** Flagships, supply, bays, a scripted commander and
   goal-conditioned orders.
8. **M6+.** A learned commander, drafting, strange hulls, and handwired experiments.

## 13. Open questions

- Throttle levels: discrete `{0, ½, 1}`, or continuous with a Beta distribution?
  Start discrete.
- Observing projectiles: the nearest K as tokens, or a coarse threat field?
- Victory under the time limit: score by remaining fleet value, or by objective
  control?
- How much the commander's plan is shown on screen. Too much clutters the view; too
  little loses the story.
