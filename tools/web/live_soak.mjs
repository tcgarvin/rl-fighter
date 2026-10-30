// Soak test of the live page in headless Chromium: runs the real page (sped up with
// ?speed=) for a while and samples, at every new match, the JS heap after a forced GC,
// the three.js GPU resource counts and the DOM size. Fails if the heap grows more than
// 10 % past the warm-up or any GPU count grows after it. It also reports, per match and
// per mission, the most ships on the field and the frame and tick times (informational:
// headless SwiftShader frame times say little about a real GPU).
//
// It serves a private copy of web/dist, so halfway through it can also check the
// bundle swap: it publishes a broken manifest (the page must keep its bundle), then a
// valid one with a new bundle_id (the page must take it over between matches).
//
// Usage: node tools/web/live_soak.mjs [minutes=10] [speed=8] [warmup-minutes=2]
// Env: RLF_GPU=1 to use the host GPU (tools/web/browser.mjs).

import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { REPO } from "./load.mjs";
import { launch, watchErrors } from "./browser.mjs";

const [minutesArg = "10", speedArg = "8", warmupArg = "2"] = process.argv.slice(2);
const MINUTES = Number(minutesArg);
const WARMUP_MS = Number(warmupArg) * 60_000;
const HEAP_GROWTH_LIMIT = 0.1;
const SAMPLE_POLL_MS = 1000;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".wasm": "application/wasm", ".bin": "application/octet-stream", ".png": "image/png" };

const dist = path.join(REPO, "web/dist");
if (!fs.existsSync(path.join(dist, "bundle/manifest.json"))) {
  console.error("live soak: web/dist/bundle/manifest.json missing; run scripts/build_bundle.sh and npm run build first");
  process.exit(2);
}
const root = fs.mkdtempSync(path.join(os.tmpdir(), "rlf-soak-"));
fs.cpSync(dist, root, { recursive: true });
const manifestPath = path.join(root, "bundle/manifest.json");
const original = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  let file = path.join(root, decodeURIComponent(url.pathname));
  if (!file.startsWith(root)) return void res.writeHead(403).end();
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
  if (!fs.existsSync(file)) return void res.writeHead(404).end();
  res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] ?? "application/octet-stream", "Cache-Control": "no-cache" });
  fs.createReadStream(file).pipe(res);
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = watchErrors(page, "soak");
const warnings = [];
page.on("console", (m) => {
  if (m.type() === "warning" && m.text().startsWith("live:")) warnings.push(m.text());
});
const cdp = await page.context().newCDPSession(page);
await page.goto(`${base}/?debug&speed=${speedArg}`);
await page.waitForFunction(() => window.rlfLive?.stats().matches >= 1, null, { timeout: 120_000 });

async function sample() {
  await cdp.send("HeapProfiler.collectGarbage");
  const heap = await cdp.send("Runtime.getHeapUsage");
  const s = await page.evaluate(() => ({ ...window.rlfLive.stats(), dom: document.getElementsByTagName("*").length - document.querySelectorAll("#tags *, #cmdlog *, #mission *").length }));
  return { t: Date.now() - start, heap: heap.usedSize, ...s };
}

const start = Date.now();
const samples = [];
let lastMatch = 0;
const swap = { brokenAt: null, validAt: null, keptOld: null, tookNew: null };
const newId = `${original.bundle_id}-soak`;
// Per match (between samples): the most ships on the field, the mean and worst frame
// and the worst smoothed sim + inference tick, polled once a second.
let load = { mission: "", ships: 0, frame: [], worstFrame: 0, tick: 0 };
const loads = [];
while (Date.now() - start < MINUTES * 60_000) {
  await page.waitForTimeout(SAMPLE_POLL_MS);
  const st = await page.evaluate(() => window.rlfLive.stats());
  if (st.phase === "battle") {
    load.mission = st.mission ?? "";
    load.ships = Math.max(load.ships, st.ships ?? 0);
    if (st.frameMs) load.frame.push(st.frameMs);
    load.worstFrame = Math.max(load.worstFrame, st.worstFrameMs ?? 0);
    load.tick = Math.max(load.tick, st.tickMs ?? 0);
  }
  const matches = st.matches;
  if (matches === lastMatch) continue;
  lastMatch = matches;
  const s = await sample();
  samples.push(s);
  const meanFrame = load.frame.length ? load.frame.reduce((a, b) => a + b, 0) / load.frame.length : 0;
  if (load.mission) loads.push({ ...load, meanFrame });
  const perf = load.mission
    ? ` · last match ${load.mission}: peak ${load.ships} ships, frame ${meanFrame.toFixed(1)} ms mean / ${load.worstFrame.toFixed(0)} worst, tick ≤ ${load.tick.toFixed(2)} ms`
    : "";
  load = { mission: "", ships: 0, frame: [], worstFrame: 0, tick: 0 };
  console.log(`live soak: ${(s.t / 1000).toFixed(0)} s match ${s.matches} heap ${(s.heap / 1048576).toFixed(2)} MiB gpu ${JSON.stringify(s.gpu)} dom ${s.dom} bundle ${s.bundle} tally ${s.tally.wins.join("-")}/${s.tally.draws}${perf}`);
  const half = (MINUTES * 60_000) / 2;
  if (swap.brokenAt === null && s.t > half) {
    // A manifest for a bundle whose wasm cannot match: the load must fail.
    fs.writeFileSync(manifestPath, JSON.stringify({ ...original, bundle_id: "broken-soak", sim_version: 999 }));
    swap.brokenAt = s.matches;
  } else if (swap.brokenAt !== null && swap.validAt === null && s.matches >= swap.brokenAt + 2) {
    swap.keptOld = s.bundle === original.bundle_id;
    fs.writeFileSync(manifestPath, JSON.stringify({ ...original, bundle_id: newId }));
    swap.validAt = s.matches;
  } else if (swap.validAt !== null && swap.tookNew === null && s.matches >= swap.validAt + 2) {
    swap.tookNew = s.bundle === newId;
  }
}
await browser.close();
server.close();
fs.rmSync(root, { recursive: true, force: true });

const afterWarmup = samples.filter((s) => s.t >= WARMUP_MS);
let failed = false;
if (afterWarmup.length < 2) {
  console.error(`live soak: FAIL only ${afterWarmup.length} samples after warm-up; run longer`);
  process.exit(1);
}
const first = afterWarmup[0];
const last = afterWarmup.at(-1);
const peak = Math.max(...afterWarmup.map((s) => s.heap));
const growth = (last.heap - first.heap) / first.heap;
const gpuGrew = ["geometries", "textures", "programs"].filter((k) => afterWarmup.some((s) => s.gpu[k] > first.gpu[k]));
// Per-ship markers (#tags), the mission panel and the command log (capped at 90 lines)
// vary with the mission and roster, so they are left out; the rest is compared by peaks.
const halfway = Math.floor(afterWarmup.length / 2);
const domPeak = (list) => Math.max(...list.map((s) => s.dom));
const domGrew = domPeak(afterWarmup.slice(halfway)) > domPeak(afterWarmup.slice(0, Math.max(1, halfway)));
console.log(
  `live soak: ${samples.length} matches in ${MINUTES} min at speed ${speedArg}; heap after warm-up ${(first.heap / 1048576).toFixed(2)} → ${(last.heap / 1048576).toFixed(2)} MiB ` +
    `(${(growth * 100).toFixed(1)} %, peak ${(peak / 1048576).toFixed(2)}); gpu ${JSON.stringify(first.gpu)} → ${JSON.stringify(last.gpu)}; dom ${first.dom} → ${last.dom}`,
);
console.log(`live soak: bundle swap: broken manifest kept the old bundle: ${swap.keptOld}; new bundle taken over: ${swap.tookNew}; page warnings: ${warnings.length}`);
for (const mission of [...new Set(loads.map((l) => l.mission))]) {
  const ls = loads.filter((l) => l.mission === mission);
  const mean = ls.reduce((a, l) => a + l.meanFrame, 0) / ls.length;
  console.log(
    `live soak: ${mission} × ${ls.length}: peak ${Math.max(...ls.map((l) => l.ships))} ships on the field, frame ${mean.toFixed(1)} ms mean / ` +
      `${Math.max(...ls.map((l) => l.worstFrame)).toFixed(0)} ms worst, tick ≤ ${Math.max(...ls.map((l) => l.tick)).toFixed(2)} ms`,
  );
}
if (growth > HEAP_GROWTH_LIMIT) (failed = true), console.error(`live soak: FAIL heap grew ${(growth * 100).toFixed(1)} % (limit ${HEAP_GROWTH_LIMIT * 100} %)`);
if (gpuGrew.length) (failed = true), console.error(`live soak: FAIL GPU resources grew after warm-up: ${gpuGrew.join(", ")}`);
if (domGrew) (failed = true), console.error("live soak: FAIL DOM grew after warm-up");
if (swap.keptOld === false || swap.tookNew === false) (failed = true), console.error("live soak: FAIL bundle swap did not behave");
if (errors.length) (failed = true), console.error(`live soak: FAIL page errors:\n  ${errors.join("\n  ")}`);
process.exit(failed ? 1 : 0);
