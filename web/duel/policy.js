// In-browser inference for the spike policy (spacefight/rl/spike_policy.py SpikeActor):
// a 385 → 256 tanh → 256 tanh → 61 MLP whose logits split into 21 categorical heads.
// Weights come from tools/export_policy.py (manifest.json + weights.bin). No DOM here,
// so the Node parity and smoke tests run exactly this file.

export const MANIFEST_FORMAT = "rlf.web_policy/1";

/** Seeded uniform [0, 1) generator (mulberry32). */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Build a policy from the export's manifest and the bytes of weights.bin.
 * Throws if the files disagree with each other or with `expect` ({ simVersion, obsDim,
 * actionWidth }) — the WASM build the policy will run against.
 */
export function createPolicy(manifest, weightsBuffer, expect) {
  if (manifest.format !== MANIFEST_FORMAT) throw new Error(`policy manifest format ${manifest.format}, expected ${MANIFEST_FORMAT}`);
  if (expect.simVersion !== manifest.sim_version) throw new Error(`policy is for sim_version ${manifest.sim_version}, this build is ${expect.simVersion}`);
  if (expect.obsDim !== manifest.obs_dim) throw new Error(`policy obs_dim ${manifest.obs_dim} != sim OBS_DIM ${expect.obsDim}`);
  if (expect.actionWidth !== manifest.action_width) throw new Error(`policy action_width ${manifest.action_width} != sim ACTION_WIDTH ${expect.actionWidth}`);
  if (weightsBuffer.byteLength !== manifest.weights_floats * 4) throw new Error(`weights.bin has ${weightsBuffer.byteLength} bytes, manifest says ${manifest.weights_floats * 4}`);
  // The manifest promises little-endian f32; a Float32Array uses the platform order,
  // which is little-endian on every browser target, so check rather than convert.
  if (new Uint8Array(new Uint16Array([1]).buffer)[0] !== 1) throw new Error("big-endian platform: weights.bin is little-endian");
  const all = new Float32Array(weightsBuffer);
  const layers = manifest.layers.map((l) => ({
    in: l.in,
    out: l.out,
    tanh: l.activation === "tanh",
    w: all.subarray(l.weight_offset, l.weight_offset + l.in * l.out),
    b: all.subarray(l.bias_offset, l.bias_offset + l.out),
    y: new Float32Array(l.out),
  }));
  if (layers[0].in !== manifest.obs_dim || layers.at(-1).out !== manifest.n_logits) throw new Error("policy layer shapes do not match obs_dim / n_logits");
  const heads = manifest.heads;
  const maxChoices = Math.max(...heads.map((h) => h.choices));
  const probs = new Float64Array(maxChoices);

  /** Raw logits for one observation (a view, overwritten by the next call). */
  function forward(obs) {
    let x = obs;
    for (const l of layers) {
      const { w, b, y } = l;
      const n = l.in;
      for (let o = 0; o < l.out; o++) {
        let acc = b[o];
        const row = o * n;
        for (let i = 0; i < n; i++) acc += w[row + i] * x[i];
        y[o] = l.tanh ? Math.tanh(acc) : acc;
      }
      x = y;
    }
    return x;
  }

  /**
   * One action row from logits, as SpikeActor.sample does: every head valid in
   * `headValid` (Uint8Array, 21) samples its own softmax (or takes the first argmax when
   * `rng` is null); masked heads take the head's masked value (HOLD / no fire).
   */
  function actFromLogits(logits, headValid, rng, row) {
    for (const h of heads) {
      for (let k = 0; k < h.count; k++) {
        const col = h.action_start + k;
        if (!headValid[col]) {
          row[col] = h.masked_value;
          continue;
        }
        const base = h.logit_start + k * h.choices;
        let best = 0;
        let max = -Infinity;
        for (let c = 0; c < h.choices; c++) {
          if (logits[base + c] > max) {
            max = logits[base + c];
            best = c;
          }
        }
        if (!rng) {
          row[col] = best;
          continue;
        }
        let total = 0;
        for (let c = 0; c < h.choices; c++) total += probs[c] = Math.exp(logits[base + c] - max);
        let u = rng() * total;
        let pick = h.choices - 1;
        for (let c = 0; c < h.choices; c++) {
          u -= probs[c];
          if (u < 0) {
            pick = c;
            break;
          }
        }
        row[col] = pick;
      }
    }
    return row;
  }

  return {
    manifest,
    forward,
    actFromLogits,
    /** Sample (rng) or argmax (rng null) an Int8Array action row for one observation. */
    act(obs, headValid, rng, row = new Int8Array(manifest.action_width)) {
      return actFromLogits(forward(obs), headValid, rng, row);
    },
  };
}
