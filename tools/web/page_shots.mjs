// Full-page screenshots of the notebook and hull catalogue in headless Chromium, at the
// iPhone portrait size (390×844) and a desktop (1440×900), for review. Fails on page
// errors, on the pages' own error states (missing data), and on horizontal page scroll
// (the phone-first rule). Serve web/dist first, e.g. `cd web && npx vite preview --port 4173`.
//
// Usage: node tools/web/page_shots.mjs [base=http://localhost:4173] [out=web/shots/pages]
//   RLF_SHOTS_RUN=<run-id> picks the run page shown (default: the newest run).

import fs from "node:fs";
import path from "node:path";
import { REPO } from "./load.mjs";
import { launch, watchErrors } from "./browser.mjs";

const [base = "http://localhost:4173", outArg = path.join(REPO, "web/shots/pages")] = process.argv.slice(2);
const out = path.resolve(outArg);
fs.mkdirSync(out, { recursive: true });

const VIEWPORTS = [
  { name: "phone", width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  { name: "desktop", width: 1440, height: 900, deviceScaleFactor: 1 },
];

const index = await (await fetch(`${base}/notebook/data/index.json`)).json();
const run = process.env.RLF_SHOTS_RUN ?? index.runs[0]?.id;
if (!run) throw new Error("page shots: the notebook index has no runs");

// `ready` is a selector the page renders once its data is in; `settle` gives the hull
// turntables (WebGL) time to draw a frame.
const MAX_FULL_PAGE_PX = 6000;

const SCENES = [
  { name: "notebook", url: "/notebook/", ready: ".nb-index", settle: 0.3 },
  { name: "notebook-run", url: `/notebook/#${run}`, ready: ".nb-entry-head", settle: 0.5 },
  { name: "notebook-plan", url: `/notebook/#${run}/plan`, ready: ".nb-entry-head", settle: 0.5 },
  { name: "hulls", url: "/hulls/", ready: ".hull-list", settle: 2.0 },
];

const browser = await launch();
const errors = [];
for (const vp of VIEWPORTS) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: vp.deviceScaleFactor, isMobile: vp.isMobile ?? false, hasTouch: vp.hasTouch ?? false });
  for (const scene of SCENES) {
    const label = `${vp.name}/${scene.name}`;
    const page = await context.newPage();
    const pageErrors = watchErrors(page, label);
    await page.goto(`${base}${scene.url}`, { waitUntil: "load" });
    try {
      await page.waitForSelector(`${scene.ready}, .nb-message`, { timeout: 30000 });
    } catch {
      errors.push(`${label}: ${scene.ready} never rendered`);
      await page.close();
      continue;
    }
    if (await page.$(".nb-message")) {
      errors.push(`${label}: error state: ${await page.textContent(".nb-message")}`);
    }
    await page.waitForTimeout(scene.settle * 1000);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (overflow > 0) errors.push(`${label}: page scrolls sideways by ${overflow}px`);
    const stem = path.join(out, `${scene.name}-${vp.name}-${vp.width}x${vp.height}`);
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    if (height * vp.deviceScaleFactor <= MAX_FULL_PAGE_PX) {
      await page.screenshot({ path: `${stem}.png`, fullPage: true, timeout: 120000 });
      console.log(`page shots: ${stem}.png`);
    } else {
      // Past several thousand device pixels Chromium's full-page capture repeats the
      // top of the page; shoot the page's sections one by one instead.
      const parts = await page.$$("body > nav, main > header, main > div > *, main > footer");
      for (const [i, part] of parts.entries()) {
        const file = `${stem}-${String(i).padStart(2, "0")}.png`;
        // The hull turntables draw only cards on screen: scroll in, let a frame land.
        await part.scrollIntoViewIfNeeded();
        await page.waitForTimeout(scene.settle * 1000);
        await part.screenshot({ path: file, timeout: 120000 });
        console.log(`page shots: ${file}`);
      }
    }
    await page.close();
    errors.push(...pageErrors);
  }
  await context.close();
}
await browser.close();
if (errors.length) {
  console.error(`page shots: ${errors.length} problem(s):\n  ${errors.join("\n  ")}`);
  process.exit(1);
}
