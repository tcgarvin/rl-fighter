// Screenshots of the M3 art preview (web/dev/m3-art.html: carrier, transport, bay
// launch, jump charge and jump-out, quick jump-out, the order overlay) at the iPhone
// portrait size (390×844) and a desktop (1440×900). The page is dev-only, so serve it
// with the Vite dev server: `cd web && npx vite --port 5179 --strictPort`.
// Fails on page errors.
//
// Usage: node tools/web/art_shots.mjs [base=http://localhost:5179] [out=web/shots/m3-art]
//   RLF_ART_SCENES=launch,jump limits the scenes.

import fs from "node:fs";
import path from "node:path";
import { REPO } from "./load.mjs";
import { launch, watchErrors } from "./browser.mjs";

const [base = "http://localhost:5179", outArg = path.join(REPO, "web/shots/m3-art")] = process.argv.slice(2);
const out = path.resolve(outArg);
fs.mkdirSync(out, { recursive: true });

const VIEWPORTS = [
  { name: "phone", width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  { name: "desktop", width: 1440, height: 900, deviceScaleFactor: 1 },
];

// Times (s) chosen to catch each effect's beats; see the scenes in web/src/dev/m3art.ts.
// A key may carry extra query parameters after the scene name.
const SHOTS = {
  lineup: [0.5],
  "detail&close=80": [0.3],
  convoy: [1.5],
  // Launch at 0.9 (port, 2nd craft, starboard) / 1.5 (bomber): flash, trail, coast.
  launch: [0.97, 1.1, 1.58, 3.6],
  // Transport 0 charges 0.3-2.3 then leaves; transport 1 charges 1.2-3.2.
  jump: [0.9, 2.0, 2.33, 2.45, 2.7],
  quick: [0.55, 0.72, 0.95],
  orders: [1.0],
};
const only = process.env.RLF_ART_SCENES?.split(",").filter(Boolean);

const browser = await launch();
const errors = [];
for (const vp of VIEWPORTS) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: vp.deviceScaleFactor, isMobile: vp.isMobile ?? false, hasTouch: vp.hasTouch ?? false });
  for (const [scene, times] of Object.entries(SHOTS)) {
    const name = scene.split("&")[0];
    if (only && !only.includes(name)) continue;
    for (const t of times) {
      const label = `${vp.name}/${scene}@${t}`;
      const page = await context.newPage();
      const pageErrors = watchErrors(page, label);
      await page.goto(`${base}/dev/m3-art.html?scene=${scene}&t=${t}`, { waitUntil: "load" });
      try {
        await page.waitForFunction(() => window.artReady === true, null, { timeout: 120000 });
      } catch {
        errors.push(`${label}: never became ready`);
      }
      const file = path.join(out, `${name}-${String(t).replace(".", "_")}-${vp.name}-${vp.width}x${vp.height}.png`);
      await page.screenshot({ path: file, timeout: 120000 });
      console.log(`art shots: ${file}`);
      errors.push(...pageErrors);
      await page.close();
    }
  }
  await context.close();
}
await browser.close();
if (errors.length) {
  console.error(`art shots: ${errors.length} error(s)\n${errors.join("\n")}`);
  process.exit(1);
}
