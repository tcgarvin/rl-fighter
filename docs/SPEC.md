Below is a build plan you can start coding immediately. It’s biased toward: **fast headless sim**, **data-driven Naev-ish content**, **team tactics**, and **league self-play** for variety.

---

## 1) Repo layout (Python-first, sim stays headless)

```
spacefight/
  sim/
    core.py          # step() on pure arrays; deterministic PRNG
    weapons.py       # beam, projectile, missile, torpedo, emp
    damage.py        # shields/hull/resists/recharge delays
    sensors.py       # structured obs + rays + noise model
    loadout.py       # point-buy + randomization
    rules.py         # win conditions, time limit, reward shaping
  env/
    pz_parallel.py   # PettingZoo ParallelEnv wrapper
    vec_env.py       # N-parallel matches (batch sim)
  rl/
    nets.py          # policy + centralized critic
    ppo_mappo.py     # MAPPO-style PPO loop
    league.py        # snapshot pool, opponent sampling, Elo
    buffers.py       # rollout storage, GAE
  tools/
    viewer.py        # optional pygame viewer (reads sim state)
    replays.py       # record/serialize seeds + actions + states
  data/
    hulls.yaml
    weapons.yaml
    outfits.yaml
  scripts/
    train.py
    eval.py
    play_league.py
```

Key principle: **`sim/` must not import torch**. Keep it pure + fast.

---

## 2) Simulation core (deterministic, fixed dt, EV-ish arcade)

### State as batched arrays

For speed and easy vectorization, store match state as NumPy arrays:

* `pos[N, S, 2]`, `vel[N, S, 2]`
* `theta[N, S]`, `omega[N, S]`
* `shield[N, S]`, `hull[N, S]`, `energy[N, S]`
* `cooldowns[N, S, W]`, `ammo[N, S, W]`
* `alive[N, S]` boolean
* projectiles/missiles in separate fixed-size pools:

  * `proj_pos[N, P, 2]`, `proj_vel[N, P, 2]`, `proj_alive[N, P]`, `proj_owner[N, P]`, `proj_damage[N,P,3]`, `proj_ttl[N,P]`
  * similar for missiles/torps: include `target_id`, `lock_mode`, `turn_rate`, `thrust`

Where:

* `N` = number of parallel matches
* `S` = max ships per match (8 for 4v4)
* `W` = max weapon mounts per ship (pad)
* `P` = projectile pool size (pad)

### Arcade physics update (no strafing)

Per ship, per tick:

1. **Turn**

* `omega = turn_cmd * turn_rate`
* `theta += omega * dt`

2. **Thrust / brake**

* `heading = [cos(theta), sin(theta)]`
* `acc = thrust_cmd * thrust * heading`
* `acc += brake_cmd * (-brake * vel)`  (brake is viscous)

3. **Soft speed cap (EV feel)**
   Instead of hard clamp, apply extra drag when above `v_max`:

* `speed = ||vel||`
* `over = max(0, speed - v_max)`
* `vel += dt * (-cap_drag * over * vel_unit)`  (vel_unit = vel / (speed+eps))

4. **Integrate**

* `vel += acc * dt`
* `pos += vel * dt`

This is stable, feels “arcade”, and avoids brittle clamping.

### Collision model

* Ships: circles (radius from hull data)
* Bullets: point or tiny circle
* Hit test: distance < (ship_r + proj_r)
* Beam hitscan: ray-circle intersection on heading, within range

---

## 3) Weapons & systems (variety from data, not code)

Define each weapon in `weapons.yaml`:

* type: `beam | bullet | missile | torpedo | emp_beam | emp_proj`
* damage: `{thermal, kinetic, emp}`
* range, projectile_speed, ttl
* fire_rate / cooldown
* energy_cost, heat (optional), ammo_max
* guidance (for missiles/torps): turn_rate, thrust, top_speed
* lock: required? lock_time? lock_break_distance?

**Dumbfire + lock**: implement missiles with `mode`:

* if lock acquired: steer toward target (limited turn rate)
* if no lock: coast on initial heading

**Fast missiles vs slow torps**

* fast missile: high turn_rate, moderate damage, short ttl
* torpedo: low turn_rate, huge damage, longer ttl, easy to dodge unless used with teamwork

### Shields + hull

* Shields recharge after `recharge_delay` since last shield damage
* Recharge rate `shield_regen`
* Resist tables per ship: `shield_resist[type]`, `hull_resist[type]`
* EMP can:

  * extend shield recharge delay
  * reduce turn_rate/thrust temporarily
  * disrupt lock (optional later)

---

## 4) Loadouts: point-buy + random outfitting (v1)

At reset, generate each ship’s loadout by:

1. pick hull class (interceptor/gunboat/missile boat/brawler)
2. budget = hull_budget + random jitter
3. choose outfits/weapons until budget spent, respecting mount constraints
4. optionally enforce “role kits” distribution per team (1 missile boat max, etc.) to avoid degenerate all-X comps early

This produces asymmetry and forces the policy to generalize.

Later: add a **meta-step** where the agent picks loadout, but don’t start there.

---

## 5) Observations: structured + rays + noise

### Structured (fixed-size, sorted)

For each agent ship:

* self: normalized (speed, heading, omega, shield%, hull%, energy%, ammo bins, cooldown bins)
* allies: up to 3 nearest allies (relative pos/vel, ally shield/hull bins)
* enemies: up to 4 nearest enemies (relative pos/vel, *noisy/binned* shield/hull, maybe “class id”)
* threats: up to M nearest missiles/torps (relative pos/vel, time-to-impact approx)

Sort entities by distance, pad with zeros.

### Rays (32 directions)

Each ray returns:

* nearest distance to (enemy ship, ally ship, missile/torp) in that direction (3 channels), normalized to [0,1]
  Approximate quickly by checking angle between ray and relative vector; treat as “hit” if within small angular tolerance.

### Noise model (v1)

* Add Gaussian noise to sensed distances
* Quantize shield/hull estimates into bins (e.g., 0–10)
* Random dropout on some rays (simulating imperfect sensors)
  (“Damaged sensors” later: tie noise/dropout to a `sensor_health` subsystem.)

---

## 6) Actions: MultiDiscrete + masking

Represent action as tuple:

* `turn ∈ {L,0,R}`
* `thrust ∈ {0,1}`
* `brake ∈ {0,1}`
* `fire_primary ∈ {0,1}`
* `fire_secondary ∈ {0,1}`
* `fire_missile ∈ {0,1}` (fires selected missile mount if any)
* `toggle_lock ∈ {0,1}` (optional; or implicit auto-lock if within cone)

Mask invalid firing (no ammo, cooldown>0, energy insufficient). In PPO you can apply masking by setting logits of invalid options to a large negative value before sampling.

---

## 7) Reward: team win dominates; shaping kills boring behaviors

Per agent reward each step:

* Terminal:

  * +1 for team win, -1 for team loss (all surviving/dead agents get it)
* Shaping (small):

  * `+a * damage_dealt` (weighted hull > shield)
  * `-b * damage_taken`
  * `-c * disengage_penalty` if far from nearest enemy for too long **and** team hasn’t dealt damage recently
  * optional `-d * spin_penalty` if near-zero velocity + high turning for extended time (stops “sit and pivot” meta)
* Time limit:

  * if draw: reward based on team damage delta, not “who ran away better”

This setup tends to produce **closing distance + coordinated pressure** without forcing suicidal brawling.

---

## 8) Multi-agent RL algorithm (Python, MAPPO-style PPO)

You want wingman behavior ⇒ **decentralized actors + centralized critic**.

### Why MAPPO here

* Each ship acts on its own observation (decentralized execution).
* Critic sees more context, stabilizing learning in multi-agent nonstationarity.
* Works well with discrete actions and team rewards.

### Data collection

Run `N` parallel matches, each with `S=8` agents:

* For `T` steps:

  * get obs for all agents
  * sample actions from policy
  * step sim
  * store: obs, action, logprob, reward, done, value estimate

### Networks

**Actor (shared across all ships initially):**

* Input: flattened structured + rays
* MLP: e.g., [512, 512, 256] with LayerNorm
* Output: logits for each discrete head (turn/thrust/…)
* You can add an “agent embedding” (team id + hull class) concatenated to obs to allow specialization.

**Centralized critic:**
Two pragmatic options:

1. **Concatenate all agent observations (padded)** into a global vector and feed an MLP → V(s).
   Simple, works fine for 8 agents.

2. **Attention critic**: embed each agent obs then self-attention pooling.
   Better scaling, more code.

Start with (1).

### Optimization (PPO with GAE)

For each update:

* compute advantages with GAE(λ), returns
* PPO clipped objective per action head (sum logprobs of heads)
* value loss + entropy bonus (entropy helps keep variety)
* gradient steps: K epochs over minibatches

### Self-play league

To avoid converging to one boring meta:

* Maintain a league of opponent snapshots `π_1..π_k`
* For each episode, sample opponent policy using:

  * 50% near-skill
  * 25% older random
  * 25% “diversity bucket” (policies whose behavior metrics differ)

Train one side against frozen opponent. Periodically swap which side is “learning” so you don’t overfit to a single training role.

---

## 9) Vectorization strategy (how you get “millions of runs”)

* **Single process, batched NumPy sim** for `N` matches at once is the biggest speed win.
* Keep Python loops only over small fixed dims; ideally vectorize across `N` and `S`.
* If bullets/missiles pools become bottleneck, use Numba later.

---

## 10) “Interestingness” evaluation (not just win-rate)

Track per match:

* engagement: time within distance D of an enemy
* damage cadence: longest “no damage dealt” interval
* movement diversity: distribution of speed / turning
* coordination: ally proximity + “same-target focus” fraction
* weapon usage entropy: are they using the kit or spamming one thing?

Use these to:

* select league snapshots
* detect regressions (“we trained a champion that fights like a Roomba”)

---

## 11) Implementation milestones (in order)

1. **Sim skeleton**: 1v1, thrust/turn, bullets only, hull only
2. Add **shields + regen delay**
3. Add **beams (hitscan) + energy cost**
4. Add **missile + torpedo guidance + lock/dumbfire**
5. Add **2v2 then 4v4**, team termination, padding/masks
6. Implement **observations A+B + noise**
7. Implement **Gym/PettingZoo wrapper + vectorized env**
8. Implement **MAPPO PPO training loop** with one frozen opponent
9. Add **league snapshots + sampling + metrics**
10. Add **viewer + replay seeds** (debugging sanity saver)

---

## 12) Minimal algorithm pseudocode (training loop)

```python
for iter in range(num_iters):
    opp_policy = league.sample_opponent(current_policy)

    rollouts = []
    state = env.reset(random_loadouts=True, opponent=opp_policy)

    for t in range(T):
        obs = env.observe_all()  # [N, S, obs_dim]
        actions, logp = policy.sample(obs, masks=env.action_masks())
        values = critic.value(env.global_state())  # centralized

        next_state, rewards, dones, info = env.step(actions, opponent=opp_policy)

        rollouts.append((obs, actions, logp, rewards, dones, values))
        if dones.all(): break

    returns, adv = compute_gae(rollouts, last_value=0)
    ppo_update(policy, critic, rollouts, returns, adv)

    if iter % snapshot_every == 0:
        league.add_snapshot(policy, metrics=info["metrics"])
```

---

## First concrete coding task (do this next)

Implement `sim/core.py` with:

* `reset(seed, teams, loadouts)`
* `step(actions)` returning state + per-agent reward + done + metrics
* deterministic RNG via `np.random.Generator(np.random.PCG64(seed))`
* one weapon type (bullet) + circle collision

Then wrap in `env/vec_env.py` and confirm you can run **N=256** matches deterministically with identical seeds.

If you want, paste your first cut of `hulls.yaml` / `weapons.yaml` and I’ll help you shape the schema so it stays flexible without turning into a content-authoring nightmare.

