// Run web/src/live/policy.js over a batch of observations for tests/test_web_policy.py.
//
// Usage: node tools/web/policy_parity.mjs <policy-dir> <obs.f32> <head_valid.u8> <out.json>
// obs.f32: B × obs_dim little-endian float32; head_valid.u8: B × action_width bytes.
// Writes { logits: [[61]...], argmax: [[21]...], sampled: [[21]...] } (sampled with a
// fixed seed, for mask checks only: torch's RNG is not reproduced).

import fs from "node:fs";
import { importRepo, readPolicyFiles } from "./load.mjs";

const [policyDir, obsPath, validPath, outPath] = process.argv.slice(2);
if (!outPath) {
  console.error("usage: node tools/web/policy_parity.mjs <policy-dir> <obs.f32> <head_valid.u8> <out.json>");
  process.exit(2);
}
const { createPolicy, mulberry32 } = await importRepo("web/src/live/policy.js");
const { manifest, weights } = readPolicyFiles(policyDir);
const policy = createPolicy(manifest, weights, {
  simVersion: manifest.sim_version,
  obsDim: manifest.obs_dim,
  actionWidth: manifest.action_width,
});
const obsBytes = fs.readFileSync(obsPath);
const obsAll = new Float32Array(obsBytes.buffer.slice(obsBytes.byteOffset, obsBytes.byteOffset + obsBytes.byteLength));
const valid = new Uint8Array(fs.readFileSync(validPath));
const D = manifest.obs_dim;
const A = manifest.action_width;
const B = obsAll.length / D;
if (!Number.isInteger(B) || valid.length !== B * A) throw new Error(`obs/head_valid sizes disagree: ${obsAll.length} floats, ${valid.length} mask bytes`);
const rng = mulberry32(12345);
const out = { logits: [], argmax: [], sampled: [] };
for (let r = 0; r < B; r++) {
  const obs = obsAll.subarray(r * D, (r + 1) * D);
  const hv = valid.subarray(r * A, (r + 1) * A);
  const logits = policy.forward(obs);
  out.logits.push(Array.from(logits));
  out.argmax.push(Array.from(policy.actFromLogits(logits, hv, null, new Int8Array(A))));
  out.sampled.push(Array.from(policy.actFromLogits(logits, hv, rng, new Int8Array(A))));
}
fs.writeFileSync(outPath, JSON.stringify(out));
