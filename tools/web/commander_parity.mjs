// Run web/src/live/commander.js over a batch of commander features for
// tests/test_web_commander.py.
//
// Usage: node tools/web/commander_parity.mjs <export-dir> <features.f32> <out.json> [samples=40] [many_row=0] [many=4000]
// features.f32: B x features_len little-endian float32 (WasmMatch.commander_features
// rows). Writes { logits: [[432]...], argmax: [[40]...], sampled: [[40]...] (samples
// per row, row-major), many: [[40]...] (`many` samples of row many_row) }. Samples use a
// fixed seed: torch's RNG is not reproduced, so they are for mask and frequency checks.

import fs from "node:fs";
import path from "node:path";
import { importRepo } from "./load.mjs";

const [dir, featuresPath, outPath, samplesArg = "40", manyRowArg = "0", manyArg = "4000"] = process.argv.slice(2);
if (!outPath) {
  console.error("usage: node tools/web/commander_parity.mjs <export-dir> <features.f32> <out.json> [samples] [many_row] [many]");
  process.exit(2);
}
const { createCommander } = await importRepo("web/src/live/commander.js");
const { mulberry32 } = await importRepo("web/src/live/policy.js");
const manifest = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
const bytes = fs.readFileSync(path.join(dir, manifest.weights_file));
const weights = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
const net = createCommander(manifest, weights, {
  ioVersion: manifest.io_version,
  featuresLen: manifest.features_len,
  actionDim: manifest.dims.action_dim,
  flatLayout: manifest.flat_layout,
});
const fb = fs.readFileSync(featuresPath);
const all = new Float32Array(fb.buffer.slice(fb.byteOffset, fb.byteOffset + fb.byteLength));
const F = manifest.features_len;
const B = all.length / F;
if (!Number.isInteger(B)) throw new Error(`${all.length} floats is not a whole number of ${F}-float rows`);
const A = manifest.dims.action_dim;
const rng = mulberry32(2026);
const out = { logits: [], argmax: [], sampled: [], many: [] };
for (let r = 0; r < B; r++) {
  const f = all.subarray(r * F, (r + 1) * F);
  out.logits.push(Array.from(net.forward(f)));
  out.argmax.push(Array.from(net.decide(null, new Int32Array(A))));
  for (let k = 0; k < Number(samplesArg); k++) out.sampled.push(Array.from(net.decide(rng, new Int32Array(A))));
}
const manyRow = Number(manyRowArg);
net.forward(all.subarray(manyRow * F, (manyRow + 1) * F));
for (let k = 0; k < Number(manyArg); k++) out.many.push(Array.from(net.decide(rng, new Int32Array(A))));
fs.writeFileSync(outPath, JSON.stringify(out));
