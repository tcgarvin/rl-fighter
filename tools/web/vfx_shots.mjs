// Review shots and frame timings of the live page on the host GPU, for renderer work:
// a few fixed scenes at the phone size and at the Framework 13's full-screen size, plus
// (with RLF_BENCH=1) the cost of a frame measured by drawing the paused scene over and
// over with a pixel read-back after each, so vsync does not hide it (the best of
// several blocks: an integrated GPU's clock takes a while to come up).
//
// Usage: node tools/web/vfx_shots.mjs <out-dir> [base=http://localhost:5179]
// Env: RLF_SCALE=<0.5..1> pins the render scale (default 1), RLF_SHOTS_ONLY=<substring>, RLF_VIEW=<phone|laptop|desktop>, RLF_BENCH=1,
// RLF_CROP=<w>x<h>[+<dx>+<dy>] also saves that many CSS px about the screen centre
// (offset by dx, dy) at device resolution, RLF_GPU=0 for SwiftShader (default here is
// the host GPU).

import fs from "node:fs";
import path from "node:path";
import { launch, watchErrors } from "./browser.mjs";

process.env.RLF_GPU ??= "1";
const [outArg, base = "http://localhost:5179"] = process.argv.slice(2);
if (!outArg) throw new Error("usage: vfx_shots.mjs <out-dir> [base]");
const out = path.resolve(outArg);
fs.mkdirSync(out, { recursive: true });

const VIEWS = [
  { name: "phone", width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  // The Framework 13 panel (2256x1504) at 150% scaling, full screen.
  { name: "laptop", width: 1504, height: 1003, deviceScaleFactor: 1.5 },
  { name: "desktop", width: 1440, height: 900, deviceScaleFactor: 1 },
].filter((v) => (process.env.RLF_VIEW ?? "phone,laptop").split(",").includes(v.name));

const SCENES = [
  { name: "battle", query: "seed=11&fleets=3v3&warmup=24&commands=0", phase: "battle", after: 1.5 },
  { name: "battle4", query: "seed=4&fleets=4v4&warmup=20&commands=0", phase: "battle", after: 1.5 },
  { name: "inspect", query: "seed=11&fleets=3v3&warmup=6&commands=0&inspect=0&outputs=0", phase: "battle", after: 3 },
  { name: "carrier", query: "seed=5&mission=carrier&warmup=50&commands=0", phase: "battle", after: 1.5 },
  { name: "carrier-inspect", query: "seed=5&mission=carrier&warmup=50&commands=0&inspect=0&outputs=0", phase: "battle", after: 3 },
  { name: "carrier-open", query: "seed=5&mission=carrier&warmup=1.5&commands=0", phase: "battle", after: 1.0 },
  { name: "convoy", query: "seed=3&mission=convoy&warmup=30&commands=1", phase: "battle", after: 1.5 },
  { name: "result", query: "seed=1&fleets=duel&warmup=8.2&commands=0", phase: "result", after: 0.9 },
  ...(process.env.RLF_SHOTS_EXTRA ?? "").split(";").filter(Boolean).map((s) => {
    const [name, query, phase, after] = s.split("|");
    return { name, query, phase, after: Number(after ?? 1.5) };
  }),
].filter((s) => s.name.includes(process.env.RLF_SHOTS_ONLY ?? ""));

const browser = await launch();
const errors = [];
const timings = [];
for (const vp of VIEWS) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: vp.deviceScaleFactor, isMobile: vp.isMobile ?? false, hasTouch: vp.hasTouch ?? false });
  for (const scene of SCENES) {
    const page = await context.newPage();
    const pageErrors = watchErrors(page, `${vp.name}/${scene.name}`);
    await page.goto(`${base}/?${scene.query}&scale=${process.env.RLF_SCALE ?? 1}&debug`, { waitUntil: "load" });
    await page.waitForFunction(({ phase, after }) => {
      const s = window.rlfLive?.stats();
      return s && s.phase === phase && s.phaseTime >= after;
    }, scene, { timeout: 120000, polling: 50 });
    const live = await page.evaluate(() => window.rlfLive.stats().frameMs);
    await page.evaluate(() => window.rlfLive.pause());
    const file = path.join(out, `${scene.name}-${vp.name}.png`);
    await page.screenshot({ path: file, timeout: 60000 });
    const crop = /^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$/.exec(process.env.RLF_CROP ?? "");
    if (crop) {
      const [w, h, dx, dy] = crop.slice(1).map((n) => Number(n ?? 0));
      const clip = { x: Math.max(0, vp.width / 2 + dx - w / 2), y: Math.max(0, vp.height / 2 + dy - h / 2), width: Math.min(w, vp.width), height: Math.min(h, vp.height) };
      await page.screenshot({ path: path.join(out, `${scene.name}-${vp.name}-crop.png`), clip, timeout: 60000 });
    }
    let line = `${vp.name}/${scene.name}: live ${live.toFixed(1)} ms`;
    if (process.env.RLF_BENCH === "1") {
      const ms = await page.evaluate(() => window.rlfLive.bench(40));
      line += ` · bench ${ms.toFixed(2)} ms/frame`;
      timings.push({ view: vp.name, scene: scene.name, ms });
    }
    console.log(line);
    await page.close();
    errors.push(...pageErrors);
  }
  await context.close();
}
const gpu = await (async () => {
  const page = await browser.newPage();
  const r = await page.evaluate(() => {
    const gl = document.createElement("canvas").getContext("webgl2");
    const ext = gl?.getExtension("WEBGL_debug_renderer_info");
    return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "unknown";
  });
  await page.close();
  return r;
})();
console.log(`gpu: ${gpu}`);
await browser.close();
if (timings.length) fs.writeFileSync(path.join(out, "bench.json"), JSON.stringify({ gpu, timings }, null, 1));
if (errors.length) {
  console.error(`${errors.length} page error(s):\n  ${errors.join("\n  ")}`);
  process.exit(1);
}
