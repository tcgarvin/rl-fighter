// Screenshots of the live page in headless Chromium with real WebGL, at the iPhone
// portrait size (390×844) and a desktop (1440×900): the muster, mid-battle (plain and
// with technical details) and the result banner. Serve web/dist (with the bundle) first,
// e.g. `cd web && npx vite preview --port 4173`.
//
// Usage: node tools/web/live_shots.mjs [base=http://localhost:4173] [out=web/shots/live]

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
const SCENES = [
  { name: "muster", query: "seed=11", phase: "muster", after: 1.6 },
  { name: "battle", query: "seed=11&fleets=3v3&warmup=24", phase: "battle", after: 1.5 },
  { name: "battle-4v4-details", query: "seed=4&fleets=4v4&warmup=20&details", phase: "battle", after: 1.5 },
  { name: "result", query: "seed=1&fleets=duel&warmup=8.2", phase: "result", after: 0.9 },
  ...(process.env.RLF_SHOTS_EXTRA ?? "").split(";").filter(Boolean).map((s) => {
    const [name, query, phase, after] = s.split("|");
    return { name, query, phase, after: Number(after ?? 1.5) };
  }),
];

const browser = await launch();
const errors = [];
for (const vp of VIEWPORTS) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: vp.deviceScaleFactor, isMobile: vp.isMobile ?? false, hasTouch: vp.hasTouch ?? false });
  for (const scene of SCENES) {
    const page = await context.newPage();
    const pageErrors = watchErrors(page, `${vp.name}/${scene.name}`);
    await page.goto(`${base}/?${scene.query}&debug`, { waitUntil: "load" });
    await page.waitForFunction(
      ({ phase, after }) => {
        const s = window.rlfLive?.stats();
        return s && s.phase === phase && s.phaseTime >= after;
      },
      scene,
      { timeout: 90000, polling: 100 },
    );
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
