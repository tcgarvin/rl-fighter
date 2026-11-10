// Film the live page frame by frame on a virtual clock, for before/after comparisons of
// renderer work (the notebook's "compare" figures). The page's clock and its animation
// frames are replaced before it loads, so every frame is exactly 1/fps long whatever
// the machine's speed, and two builds given the same query show the same instants of
// the same match. It needs no hook in the page, so it films old builds too.
//
// One build:   node tools/web/film.mjs <out.mp4> <base-url> "<query>" [options]
// Two, joined: node tools/web/film.mjs <out.mp4> <before-url> <after-url> "<query>" [options]
//   (before on the left half of the frame, after on the right: what the notebook's
//   compare figure expects. A poster, <out>.jpg, is written beside it: the first frame
//   as the figure shows it before the film has loaded, before | after down the middle.)
// Options: --view wide|phone (960x600 or 390x844 CSS px; default wide), --seconds 8,
//   --fps 30, --lead 0 (seconds run before filming starts, unrecorded), --crf 24,
//   --hud (keep the page's HUD; by default only the canvas shows),
//   --follow <slot> --zoom 2 (film only the 1/zoom of the view around that ship, easing
//   after it; when it dies the frame holds where it was).
// Needs ffmpeg on the PATH. Uses the host GPU unless RLF_GPU=0.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { launch } from "./browser.mjs";

process.env.RLF_GPU ??= "1";
const args = process.argv.slice(2);
const options = { view: "wide", seconds: "8", fps: "30", lead: "0", crf: "24", follow: "-1", zoom: "2", hud: false };
const positional = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--hud") options.hud = true;
  else if (a.startsWith("--")) {
    if (!(a.slice(2) in options) || args[i + 1] === undefined) throw new Error(`film: unknown or incomplete option ${a}`);
    options[a.slice(2)] = args[++i];
  } else positional.push(a);
}
if (positional.length < 3 || positional.length > 4) throw new Error('usage: film.mjs <out.mp4> <base-url> [<after-url>] "<query>" [options]');
const out = path.resolve(positional[0]);
const query = positional[positional.length - 1];
const bases = positional.slice(1, -1);
const VIEWS = {
  // Drawn at 1.5x and 2x and scaled down in the encode, so edges are supersampled.
  wide: { width: 960, height: 600, deviceScaleFactor: 1.5, outWidth: 960 },
  phone: { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true, outWidth: 586 },
};
const view = VIEWS[options.view];
if (!view) throw new Error(`film: unknown view ${options.view}`);
const follow = Number(options.follow);
const zoom = follow >= 0 ? Math.max(1, Number(options.zoom)) : 1;
// A followed frame is cut out of the page: draw the page at up to 2x (the page's own
// limit) so the cut still has a pixel for every pixel of the film.
const pixelRatio = Math.max(view.deviceScaleFactor, Math.min(2, zoom));
// How fast the followed frame closes on its ship, per frame.
const FOLLOW_EASE = 0.12;
const fps = Number(options.fps);
const frames = Math.round(Number(options.seconds) * fps);
const leadFrames = Math.round(Number(options.lead) * fps);

// Runs in the page before any of its scripts: time only moves when __filmStep is called.
function virtualClock() {
  let now = 1000;
  let queue = [];
  performance.now = () => now;
  window.requestAnimationFrame = (cb) => queue.push(cb);
  window.cancelAnimationFrame = () => {};
  // The page has booted once its frame loop has asked for its first frame.
  window.__filmReady = () => queue.length > 0;
  window.__filmStep = (ms) => {
    now += ms;
    const due = queue;
    queue = [];
    for (const cb of due) cb(now);
  };
}

const work = fs.mkdtempSync(path.join(os.tmpdir(), "rlf-film-"));
const browser = await launch();
const sides = [];
for (const [index, base] of bases.entries()) {
  const dir = path.join(work, `side${index}`);
  fs.mkdirSync(dir);
  const context = await browser.newContext({ viewport: { width: view.width, height: view.height }, deviceScaleFactor: pixelRatio, isMobile: view.isMobile ?? false, hasTouch: view.hasTouch ?? false });
  await context.addInitScript(virtualClock);
  const page = await context.newPage();
  page.on("pageerror", (err) => console.error(`film: page error (${base}): ${err.message}`));
  await page.goto(`${base}/?${query}&scale=1&debug`, { waitUntil: "load" });
  // (Polled on a timer: the page's animation frames no longer fire by themselves.)
  await page.waitForFunction(() => window.__filmReady() && window.rlfLive !== undefined, null, { timeout: 120000, polling: 100 });
  if (!options.hud) await page.addStyleTag({ content: "body > :not(canvas) { visibility: hidden !important; }" });
  // Out of the muster (if the query didn't fast-forward past it) and through the lead-in.
  for (let i = 0; i < 600 && (await page.evaluate((ms) => (window.__filmStep(ms), window.rlfLive.stats().phase), 1000 / fps)) === "muster"; i++);
  for (let i = 0; i < leadFrames; i++) await page.evaluate((ms) => window.__filmStep(ms), 1000 / fps);
  sides.push({ page, dir, context });
}
// The builds advance together, so a slow frame on one never lets the other run ahead.
const cut = { width: view.width / zoom, height: view.height / zoom };
let centre = null;
for (let f = 0; f < frames; f++) {
  for (const s of sides) await s.page.evaluate((ms) => window.__filmStep(ms), 1000 / fps);
  let clip;
  if (follow >= 0) {
    // Both builds draw the ship in the same place, so one of them places the cut for both.
    const at = await sides[0].page.evaluate((i) => window.rlfLive.shipOnScreen(i), follow);
    if (at && !centre) centre = { x: at.x, y: at.y };
    else if (at) (centre.x += (at.x - centre.x) * FOLLOW_EASE), (centre.y += (at.y - centre.y) * FOLLOW_EASE);
    const c = centre ?? { x: view.width / 2, y: view.height / 2 };
    clip = { x: Math.min(view.width - cut.width, Math.max(0, c.x - cut.width / 2)), y: Math.min(view.height - cut.height, Math.max(0, c.y - cut.height / 2)), ...cut };
  }
  for (const s of sides) await s.page.screenshot({ path: path.join(s.dir, `f${String(f).padStart(5, "0")}.png`), clip });
  if (f % fps === 0) console.log(`film: ${f}/${frames} frames`);
}
await browser.close();

// yuv420p H.264 with the index up front plays everywhere, iOS included; even sizes only.
const height = Math.round((view.outWidth * view.height) / view.width / 2) * 2;
const inputs = sides.flatMap((s) => ["-framerate", String(fps), "-i", path.join(s.dir, "f%05d.png")]);
const scale = (i) => `[${i}:v]scale=${view.outWidth}:${height}:flags=lanczos[v${i}]`;
const filter = sides.length === 2 ? `${scale(0)};${scale(1)};[v0][v1]hstack=inputs=2[v]` : `${scale(0)};[v0]null[v]`;
fs.mkdirSync(path.dirname(out), { recursive: true });
const encode = spawnSync("ffmpeg", ["-y", "-loglevel", "error", ...inputs, "-filter_complex", filter, "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", options.crf, "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", out], { stdio: "inherit" });
fs.rmSync(work, { recursive: true, force: true });
if (encode.status !== 0) throw new Error(`film: ffmpeg failed (${encode.status})`);
if (sides.length === 2) {
  const poster = out.replace(/\.mp4$/, "") + ".jpg";
  const halves = "[0:v]split[a][b];[a]crop=iw/4:ih:0:0[l];[b]crop=iw/4:ih:iw*3/4:0[r];[l][r]hstack=inputs=2[v]";
  const still = spawnSync("ffmpeg", ["-y", "-loglevel", "error", "-i", out, "-filter_complex", halves, "-map", "[v]", "-frames:v", "1", "-q:v", "4", poster], { stdio: "inherit" });
  if (still.status !== 0) throw new Error(`film: ffmpeg failed to write the poster (${still.status})`);
}
console.log(`film: ${out} (${(fs.statSync(out).size / 1024).toFixed(0)} KiB, ${frames} frames at ${fps} fps, ${sides.length === 2 ? "before | after" : "one build"})`);
