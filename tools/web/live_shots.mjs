// Screenshots of the live page in headless Chromium with real WebGL, at the iPhone
// portrait size (390×844) and a desktop (1440×900): for team deathmatch the muster,
// mid-battle (plain and with technical details) and the result banner; for the carrier
// battle, the convoy escort and the station assault the muster, the opening, mid-battle
// with the commander layer on (lines, markers and the command log) and the result, and
// the station assault's heavy guns (rail and lance), its torpedo run, the citadel with
// turrets and bays shot off, and an inspected citadel, dreadnought and bomber; and (v11) a
// craft called home to its carrier, its dock flash, the inspector on it repairing in the
// hangar and its relaunch. Serve web/dist (with the bundle) first, e.g. `cd web && npx vite
// preview --port 4173`.
//
// Usage: node tools/web/live_shots.mjs [base=http://localhost:4173] [out=web/shots/live]
// Env: RLF_SHOTS_ONLY=<substring> takes only the scenes whose name contains it;
// RLF_SHOTS_COMMANDER=<id> adds scenes with that learned commander from the bundle's
// stable forced on (?commander=): a carrier battle and a convoy with the commander
// layer on, and the inspector's details on one of its strike craft.

import fs from "node:fs";
import path from "node:path";
import { REPO } from "./load.mjs";
import { launch, watchErrors } from "./browser.mjs";

const [base = "http://localhost:4173", outArg = path.join(REPO, "web/shots/live")] = process.argv.slice(2);
const out = path.resolve(outArg);
fs.mkdirSync(out, { recursive: true });

const VIEWPORTS = [
  { name: "phone", width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  { name: "desktop", width: 1440, height: 900, deviceScaleFactor: 1 },
];
// Each scene waits for a phase of the page (window.rlfLive under ?debug) and a time
// into it, so slow software WebGL start-up does not shift what is captured. Seed 1's
// duel ends at 8.5 s (tools/web/live_smoke.mjs), so warmup=8.2 lands on its result.
// commands=0 pins the commander layer off, so no scene depends on another's choice.
const MISSION_SCENES = (mission, seed, mid) => [
  { name: `${mission}-muster`, query: `seed=${seed}&mission=${mission}&commands=0`, phase: "muster", after: 1.6 },
  // Fast-forwarded past the muster (a real-time muster on a loaded machine takes minutes),
  // then a second live so launch and jump-in effects are in the shot.
  { name: `${mission}-opening`, query: `seed=${seed}&mission=${mission}&warmup=1.5&commands=0`, phase: "battle", after: 1.0 },
  { name: `${mission}-mid-commands`, query: `seed=${seed}&mission=${mission}&warmup=${mid}&commands=1`, phase: "battle", after: 1.5 },
  { name: `${mission}-result`, query: `seed=${seed}&mission=${mission}&warmup=999&commands=0`, phase: "result", after: 1.0 },
];
// v11 dock and repair, seed 108's carrier battle under the scripted commander (the only
// one that recalls; the live pilots rarely make it home, tools/web/live_smoke.mjs): Ember's
// fighter 2 (slot 13) is called home at 8.0 s, docks at tick ~417 (13.9 s) with 4% of its
// hull and relaunches at tick ~720 (24.0 s). A scene with `tick` plays from its warm-up and
// is frozen on the first frame at or past that tick (bundle-dependent: re-find the seed
// with a new pilot list).
const DOCK = "seed=108&mission=carrier&commander=scripted";
const DOCK_SCENES = [
  { name: "dock-recall", query: `${DOCK}&warmup=10.5&commands=0&inspect=13&outputs=0`, phase: "battle", tick: 362 },
  { name: "dock-recall-commands", query: `${DOCK}&warmup=11&commands=1`, phase: "battle", tick: 375 },
  { name: "dock-flash", query: `${DOCK}&warmup=13&commands=0&inspect=13&outputs=0`, phase: "battle", tick: 431 },
  { name: "dock-flash-wide", query: `${DOCK}&warmup=13&commands=0`, phase: "battle", tick: 431 },
  { name: "dock-repairing", query: `${DOCK}&warmup=15&commands=0&inspect=13&outputs=0`, phase: "battle", tick: 500 },
  { name: "dock-relaunch", query: `${DOCK}&warmup=23&commands=0&inspect=13&outputs=0`, phase: "battle", tick: 724 },
];
const learnedScenes = (id) =>
  id
    ? [
        { name: `learned-${id}-carrier-mid-commands`, query: `seed=5&mission=carrier&commander=${id}&warmup=40&commands=1`, phase: "battle", after: 1.5 },
        { name: `learned-${id}-convoy-mid-commands`, query: `seed=3&mission=convoy&commander=scripted,${id}&warmup=30&commands=1`, phase: "battle", after: 1.5 },
        { name: `learned-${id}-deathmatch-commands`, query: `seed=11&fleets=3v3&commander=${id}&warmup=12&commands=1`, phase: "battle", after: 1.5 },
        { name: `learned-${id}-inspect`, query: `seed=11&fleets=3v3&commander=${id},scripted&warmup=6&commands=0&inspect=0&outputs=1`, phase: "battle", after: 3 },
      ]
    : [];
const SCENES = [
  { name: "muster", query: "seed=11&mission=deathmatch&commands=0", phase: "muster", after: 1.6 },
  { name: "battle", query: "seed=11&fleets=3v3&warmup=24&commands=0", phase: "battle", after: 1.5 },
  { name: "battle-4v4-details", query: "seed=4&fleets=4v4&warmup=20&details&commands=0", phase: "battle", after: 1.5 },
  { name: "result", query: "seed=1&fleets=duel&warmup=8.2&commands=0", phase: "result", after: 0.9 },
  // The camera eases in over a couple of seconds, so these hold a little longer.
  { name: "inspect-ship", query: "seed=11&fleets=3v3&warmup=6&commands=0&inspect=0&outputs=0", phase: "battle", after: 3 },
  { name: "inspect-outputs", query: "seed=11&fleets=3v3&warmup=6&commands=0&inspect=1&outputs=1", phase: "battle", after: 3 },
  { name: "inspect-carrier", query: "seed=5&mission=carrier&warmup=50&commands=0&inspect=0&outputs=1", phase: "battle", after: 3 },
  ...MISSION_SCENES("carrier", 5, 50),
  ...MISSION_SCENES("convoy", 3, 30),
  // The station assault (v10: the citadel against a carrier and a dreadnought). Seed 2
  // (c1_outcome on both sides): rail fire from 2 s and lance from 17 s, the
  // dreadnought's flak turret 3 shot off at 53 s, the citadel's bays 3 and 2 and turret
  // 10 at 67 to 70 s, and the citadel destroyed at 100.4 s. Slot 0 is the citadel, 9 the
  // dreadnought, 11 the attackers' first bomber.
  ...MISSION_SCENES("station", 2, 40),
  { name: "station-heavy-fire", query: "seed=2&mission=station&warmup=21&commands=0", phase: "battle", after: 1.0 },
  { name: "station-torpedoes", query: "seed=2&mission=station&warmup=55&commands=0", phase: "battle", after: 1.0 },
  { name: "station-hardpoints", query: "seed=2&mission=station&warmup=72&commands=0", phase: "battle", after: 1.0 },
  { name: "station-inspect-citadel", query: "seed=2&mission=station&warmup=72&commands=0&inspect=0&outputs=0", phase: "battle", after: 3 },
  { name: "station-inspect-dreadnought", query: "seed=2&mission=station&warmup=54&commands=0&inspect=9&outputs=1", phase: "battle", after: 3 },
  { name: "station-inspect-bomber", query: "seed=2&mission=station&warmup=14&commands=0&inspect=11&outputs=0", phase: "battle", after: 3 },
  // Played, not fast-forwarded, through the citadel's death, so its blast is in the shot.
  { name: "station-falls", query: "seed=2&mission=station&warmup=99.6&commands=0", phase: "result", after: 0.8 },
  ...DOCK_SCENES,
  ...learnedScenes(process.env.RLF_SHOTS_COMMANDER ?? ""),
  ...(process.env.RLF_SHOTS_EXTRA ?? "").split(";").filter(Boolean).map((s) => {
    const [name, query, phase, after] = s.split("|");
    return { name, query, phase, after: Number(after ?? 1.5) };
  }),
];

const only = process.env.RLF_SHOTS_ONLY ?? "";
const scenes = SCENES.filter((sc) => sc.name.includes(only));
const browser = await launch();
const errors = [];
for (const vp of VIEWPORTS) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: vp.deviceScaleFactor, isMobile: vp.isMobile ?? false, hasTouch: vp.hasTouch ?? false });
  for (const scene of scenes) {
    const page = await context.newPage();
    const pageErrors = watchErrors(page, `${vp.name}/${scene.name}`);
    // scale=1: full resolution, whatever a software renderer's frame rate would ask for.
    await page.goto(`${base}/?${scene.query}&scale=1&debug`, { waitUntil: "load" });
    if (scene.tick !== undefined) {
      // Checked every frame, and frozen in the same frame, so a brief effect is caught.
      await page.waitForFunction(
        ({ phase, tick }) => {
          const s = window.rlfLive?.stats();
          const due = s && s.phase === phase && s.tick >= tick;
          if (due) window.rlfLive.pause();
          return due;
        },
        scene,
        { timeout: 300000, polling: "raf" },
      );
    } else {
      await page.waitForFunction(
        ({ phase, after }) => {
          const s = window.rlfLive?.stats();
          return s && s.phase === phase && s.phaseTime >= after;
        },
        scene,
        { timeout: 240000, polling: 100 },
      );
    }
    // Freeze sim and effects time: a loaded machine can take seconds per frame.
    await page.evaluate(() => window.rlfLive.pause());
    const file = path.join(out, `${scene.name}-${vp.name}-${vp.width}x${vp.height}.png`);
    await page.screenshot({ path: file, timeout: 180000 });
    console.log(`live shots: ${file}`);
    await page.close();
    errors.push(...pageErrors);
  }
  await context.close();
}
await browser.close();
if (errors.length) {
  console.error(`live shots: ${errors.length} page error(s):\n  ${errors.join("\n  ")}`);
  process.exit(1);
}
