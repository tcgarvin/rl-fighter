// In-browser inference for the learned commander (spacefight/commander/policy.py
// CommanderActor): an entity encoder, one hand-written self-attention layer, a pooled
// summary, and the decision heads of docs/COMMANDER.md "Outputs", masked as policy.py's
// _masked does (a row with nothing allowed allows choice 0). Weights come from
// tools/export_commander.py (manifest.json + weights.bin); the features are
// WasmMatch.commander_features(team). No DOM here, so the Node parity test
// (tests/test_web_commander.py) and the smoke test run exactly this file.

export const COMMANDER_FORMAT = "rlf.web_commander/1";

// Where each head's logits sit in forward()'s output, and each head's action columns.
// Rows are `count` softmaxes of `choices` each; `col` is the first action column.
export const COMMANDER_HEADS = [
  { name: "launch", col: 0, count: 3, choices: 2 },
  { name: "waypoint", col: 3, count: 1, choices: 26 },
  { name: "squad", col: 4, count: 20, choices: 6 },
  { name: "order", col: 24, count: 4, choices: 5 },
  { name: "target", col: 28, count: 4, choices: 20 },
  { name: "ward", col: 32, count: 4, choices: 20 },
  { name: "point", col: 36, count: 4, choices: 25 },
];
let start = 0;
for (const h of COMMANDER_HEADS) {
  h.logitStart = start;
  start += h.count * h.choices;
}
export const COMMANDER_N_LOGITS = start;

function same(a, b) {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

/**
 * Build a commander from the export's manifest and the bytes of weights.bin. Throws if
 * the files disagree with each other, with this forward pass's shape, or with `expect`
 * ({ ioVersion, featuresLen, actionDim, flatLayout: [[name, offset, width], ...] }):
 * the WASM build it will decide for (COMMANDER_IO_VERSION(), commanderIoJson()).
 */
export function createCommander(manifest, weightsBuffer, expect) {
  if (manifest.format !== COMMANDER_FORMAT) throw new Error(`commander manifest format ${manifest.format}, expected ${COMMANDER_FORMAT}`);
  if (manifest.io_version !== expect.ioVersion) throw new Error(`commander is for commander io ${manifest.io_version}, this build is ${expect.ioVersion}`);
  if (manifest.features_len !== expect.featuresLen) throw new Error(`commander reads ${manifest.features_len} features, the sim gives ${expect.featuresLen}`);
  if (manifest.dims.action_dim !== expect.actionDim) throw new Error(`commander action_dim ${manifest.dims.action_dim} != sim ${expect.actionDim}`);
  const flat = manifest.flat_layout;
  if (flat.length !== expect.flatLayout.length || !flat.every((e, i) => same(e, expect.flatLayout[i]))) {
    throw new Error(`commander flat layout ${JSON.stringify(flat)} differs from the sim's ${JSON.stringify(expect.flatLayout)}`);
  }
  if (weightsBuffer.byteLength !== manifest.weights_floats * 4) throw new Error(`commander weights.bin has ${weightsBuffer.byteLength} bytes, manifest says ${manifest.weights_floats * 4}`);
  if (new Uint8Array(new Uint16Array([1]).buffer)[0] !== 1) throw new Error("big-endian platform: weights.bin is little-endian");

  const d = manifest.dims;
  const E = d.n_entities;
  const D = d.entity_dim;
  const G = d.global_dim;
  const W = d.width;
  const S = d.summary;
  const H = d.attention_heads;
  const DH = W / H;
  const K = d.n_squads;
  const SE = d.squad_embed;
  const SG = d.squad_global_dim;
  const SG0 = d.squad_globals_offset;
  const want = { n_entities: 20, n_squads: 4, n_launch_hulls: 3, n_waypoint_choices: 26, n_squad_choices: 6, n_order_choices: 5, n_points: 25, action_dim: 40 };
  for (const [k, v] of Object.entries(want)) if (d[k] !== v) throw new Error(`commander ${k} ${d[k]}, this forward pass is written for ${v}`);
  if (!Number.isInteger(DH)) throw new Error(`commander width ${W} does not split into ${H} heads`);
  const MASKED = manifest.masked_logit;

  const all = new Float32Array(weightsBuffer);
  const byName = new Map(manifest.tensors.map((t) => [t.name, t]));
  const used = new Set();
  const tensor = (name, shape) => {
    const t = byName.get(name);
    used.add(name);
    if (!t) throw new Error(`commander weights lack ${name}`);
    if (!same(t.shape, shape)) throw new Error(`commander ${name} has shape [${t.shape}], expected [${shape}]`);
    const n = shape.reduce((a, b) => a * b, 1);
    if (t.offset + n > all.length) throw new Error(`commander ${name} runs past weights.bin`);
    return all.subarray(t.offset, t.offset + n);
  };
  const linear = (name, inDim, outDim, bias = true) => ({
    in: inDim,
    out: outDim,
    w: tensor(`${name}.weight`, [outDim, inDim]),
    b: bias ? tensor(`${name}.bias`, [outDim]) : null,
  });
  const L = {
    enc0: linear("trunk.encode.0", D, W),
    enc2: linear("trunk.encode.2", W, W),
    q: linear("trunk.q", W, W),
    k: linear("trunk.k", W, W),
    v: linear("trunk.v", W, W),
    o: linear("trunk.o", W, W),
    summary: linear("trunk.summary.0", W + G, S),
    launch: linear("launch", S, 2 * d.n_launch_hulls),
    waypoint: linear("waypoint", S, d.n_waypoint_choices),
    squad0: linear("squad.0", W + S, W),
    squad2: linear("squad.2", W, d.n_squad_choices),
    query: linear("query.0", SE + SG + S, W),
    order: linear("order", W, d.n_order_choices),
    point: linear("point", W, d.n_points),
    attackQ: linear("attack_q", W, W, false),
    attackK: linear("attack_k", W, W, false),
    defendQ: linear("defend_q", W, W, false),
    defendK: linear("defend_k", W, W, false),
  };
  const embed = tensor("squad_embed", [K, SE]);
  const unknown = manifest.tensors.filter((t) => !used.has(t.name)).map((t) => t.name);
  if (unknown.length) throw new Error(`commander weights have tensors this forward pass does not know: ${unknown.join(", ")}`);

  const off = Object.fromEntries(flat.map(([name, o]) => [name, o]));

  // y[yOff..yOff+out] = act(W x[xOff..xOff+in] + b); accumulates in double precision.
  function affine(l, x, xOff, y, yOff, tanh) {
    const { w, b } = l;
    const n = l.in;
    for (let o = 0; o < l.out; o++) {
      let acc = b ? b[o] : 0;
      const row = o * n;
      for (let i = 0; i < n; i++) acc += w[row + i] * x[xOff + i];
      y[yOff + o] = tanh ? Math.tanh(acc) : acc;
    }
  }

  // Scratch, reused by every decision. Every activation is a Float64Array (the features
  // are copied into one first), so affine() sees one array type and stays fast.
  const fx = new Float64Array(manifest.features_len);
  const valid = new Uint8Array(E);
  const h1 = new Float64Array(W);
  const h = new Float64Array(E * W);
  const qs = new Float64Array(E * W);
  const ks = new Float64Array(E * W);
  const vs = new Float64Array(E * W);
  const mixed = new Float64Array(E * W);
  const attn = new Float64Array(E);
  const hOut = new Float64Array(E * W);
  const summaryIn = new Float64Array(W + G);
  const s = new Float64Array(S);
  const squadBase = new Float64Array(W);
  const queryIn = new Float64Array(SE + SG + S);
  const queries = new Float64Array(K * W);
  const proj = new Float64Array(W);
  const keysA = new Float64Array(E * W);
  const keysD = new Float64Array(E * W);
  // One head row's raw logits (the widest row is the waypoint's 26; a pointer row is E).
  const raw = new Float64Array(Math.max(2 * d.n_launch_hulls, d.n_waypoint_choices, d.n_squad_choices, d.n_order_choices, d.n_points, E));
  const logits = new Float32Array(COMMANDER_N_LOGITS);
  const allowed = new Uint8Array(COMMANDER_N_LOGITS);
  const probs = new Float64Array(32);

  /** Write a head row's masked logits: a choice not allowed reads MASKED; none allowed allows 0. */
  function putRow(base, values, n, mask, maskOff) {
    let any = 0;
    for (let c = 0; c < n; c++) any |= allowed[base + c] = mask === null ? 1 : mask[maskOff + c] > 0.5 ? 1 : 0;
    if (!any) allowed[base] = 1;
    for (let c = 0; c < n; c++) logits[base + c] = allowed[base + c] ? values[c] : MASKED;
  }

  /**
   * Masked logits of every head for one decision's flat features (a view, overwritten
   * by the next call), in COMMANDER_HEADS order: launch [3 x 2], waypoint [26],
   * squad [20 x 6], order [4 x 5], target [4 x 20], ward [4 x 20], point [4 x 25].
   */
  function forward(features) {
    if (features.length !== manifest.features_len) throw new Error(`commander reads ${manifest.features_len} features, got ${features.length}`);
    fx.set(features);
    // Trunk: encode each slot, attend over the valid ones, pool, join the globals.
    let anyValid = 0;
    for (let j = 0; j < E; j++) anyValid |= valid[j] = fx[off.valid + j] > 0.5 ? 1 : 0;
    if (!anyValid) valid[0] = 1;
    for (let j = 0; j < E; j++) {
      affine(L.enc0, fx, off.entities + j * D, h1, 0, true);
      affine(L.enc2, h1, 0, h, j * W, true);
    }
    for (let j = 0; j < E; j++) {
      affine(L.q, h, j * W, qs, j * W, false);
      affine(L.k, h, j * W, ks, j * W, false);
      affine(L.v, h, j * W, vs, j * W, false);
    }
    const scale = 1 / Math.sqrt(DH);
    for (let hd = 0; hd < H; hd++) {
      const c0 = hd * DH;
      for (let i = 0; i < E; i++) {
        let max = -Infinity;
        for (let j = 0; j < E; j++) {
          if (!valid[j]) continue;
          let dot = 0;
          for (let c = 0; c < DH; c++) dot += qs[i * W + c0 + c] * ks[j * W + c0 + c];
          attn[j] = dot * scale;
          if (attn[j] > max) max = attn[j];
        }
        let total = 0;
        for (let j = 0; j < E; j++) if (valid[j]) total += attn[j] = Math.exp(attn[j] - max);
        for (let c = 0; c < DH; c++) {
          let acc = 0;
          for (let j = 0; j < E; j++) if (valid[j]) acc += attn[j] * vs[j * W + c0 + c];
          mixed[i * W + c0 + c] = acc / total;
        }
      }
    }
    for (let i = 0; i < E; i++) {
      affine(L.o, mixed, i * W, hOut, i * W, false);
      for (let c = 0; c < W; c++) hOut[i * W + c] += h[i * W + c];
    }
    let nValid = 0;
    summaryIn.fill(0);
    for (let j = 0; j < E; j++) {
      if (!valid[j]) continue;
      nValid += 1;
      for (let c = 0; c < W; c++) summaryIn[c] += hOut[j * W + c];
    }
    for (let c = 0; c < W; c++) summaryIn[c] /= Math.max(1, nValid);
    for (let g = 0; g < G; g++) summaryIn[W + g] = fx[off.globals + g];
    affine(L.summary, summaryIn, 0, s, 0, true);

    // Launch: hold is always allowed, launch hull i when launch_mask[i].
    affine(L.launch, s, 0, raw, 0, false);
    const lh = COMMANDER_HEADS[0];
    for (let i = 0; i < lh.count; i++) {
      const base = lh.logitStart + i * 2;
      allowed[base] = 1;
      allowed[base + 1] = fx[off.launch_mask + i] > 0.5 ? 1 : 0;
      logits[base] = raw[2 * i];
      logits[base + 1] = allowed[base + 1] ? raw[2 * i + 1] : MASKED;
    }
    affine(L.waypoint, s, 0, raw, 0, false);
    putRow(COMMANDER_HEADS[1].logitStart, raw, d.n_waypoint_choices, fx, off.waypoint_mask);
    // Squad of each slot: from its entity vector and the summary. The summary's half of
    // the first layer is the same for every slot, so it is computed once.
    const sq = L.squad0;
    const sqIn = W + S;
    for (let o = 0; o < W; o++) {
      let acc = sq.b[o];
      const row = o * sqIn + W;
      for (let i = 0; i < S; i++) acc += sq.w[row + i] * s[i];
      squadBase[o] = acc;
    }
    for (let j = 0; j < E; j++) {
      for (let o = 0; o < W; o++) {
        let acc = squadBase[o];
        const row = o * sqIn;
        const x0 = j * W;
        for (let i = 0; i < W; i++) acc += sq.w[row + i] * hOut[x0 + i];
        h1[o] = Math.tanh(acc);
      }
      affine(L.squad2, h1, 0, raw, 0, false);
      putRow(COMMANDER_HEADS[2].logitStart + j * d.n_squad_choices, raw, d.n_squad_choices, fx, off.squad_mask + j * d.n_squad_choices);
    }
    // Per squad: a query from its embedding, its globals and the summary.
    for (let c = 0; c < S; c++) queryIn[SE + SG + c] = s[c];
    for (let k = 0; k < K; k++) {
      for (let c = 0; c < SE; c++) queryIn[c] = embed[k * SE + c];
      for (let c = 0; c < SG; c++) queryIn[SE + c] = fx[off.globals + SG0 + k * SG + c];
      affine(L.query, queryIn, 0, queries, k * W, true);
      affine(L.order, queries, k * W, raw, 0, false);
      putRow(COMMANDER_HEADS[3].logitStart + k * d.n_order_choices, raw, d.n_order_choices, fx, off.order_mask + k * d.n_order_choices);
      affine(L.point, queries, k * W, raw, 0, false);
      putRow(COMMANDER_HEADS[6].logitStart + k * d.n_points, raw, d.n_points, null, 0);
    }
    // Pointers: a projected query against every slot's projected entity vector.
    const pscale = 1 / Math.sqrt(W);
    for (let j = 0; j < E; j++) {
      affine(L.attackK, hOut, j * W, keysA, j * W, false);
      affine(L.defendK, hOut, j * W, keysD, j * W, false);
    }
    const pointer = (lq, keys, head, maskOff) => {
      for (let k = 0; k < K; k++) {
        affine(lq, queries, k * W, proj, 0, false);
        for (let j = 0; j < E; j++) {
          let dot = 0;
          for (let c = 0; c < W; c++) dot += proj[c] * keys[j * W + c];
          raw[j] = dot * pscale;
        }
        putRow(head.logitStart + k * E, raw, E, features, maskOff);
      }
    };
    pointer(L.attackQ, keysA, COMMANDER_HEADS[4], off.target_mask);
    pointer(L.defendQ, keysD, COMMANDER_HEADS[5], off.ward_mask);
    return logits;
  }

  /** One choice from a head row: a sample of its softmax over the allowed choices, or the first argmax (rng null). */
  function choose(base, n, rng) {
    let best = -1;
    let max = -Infinity;
    for (let c = 0; c < n; c++) {
      if (allowed[base + c] && logits[base + c] > max) {
        max = logits[base + c];
        best = c;
      }
    }
    if (!rng) return best;
    let total = 0;
    for (let c = 0; c < n; c++) total += probs[c] = allowed[base + c] ? Math.exp(logits[base + c] - max) : 0;
    let u = rng() * total;
    for (let c = 0; c < n; c++) {
      if (!allowed[base + c]) continue;
      u -= probs[c];
      if (u < 0) return c;
    }
    return best;
  }

  /**
   * A decision (Int32Array of action_dim) from the logits of the last forward(): every
   * head sampled (rng) or argmaxed (rng null), never a choice its mask forbids. The
   * target, ward and point of a squad are chosen whatever its order; the sim reads them
   * only for the order kind that uses them.
   */
  function decide(rng, out) {
    for (const head of COMMANDER_HEADS) {
      for (let r = 0; r < head.count; r++) out[head.col + r] = choose(head.logitStart + r * head.choices, head.choices, rng);
    }
    return out;
  }

  /** Whether choice `c` of row `r` of head `name` was allowed in the last forward(). */
  function isAllowed(name, r, c) {
    const head = COMMANDER_HEADS.find((x) => x.name === name);
    if (!head) throw new Error(`no commander head ${name}`);
    return allowed[head.logitStart + r * head.choices + c] === 1;
  }

  return {
    manifest,
    forward,
    decide,
    isAllowed,
    /** Run the net on one decision's features and choose: sampled (rng) or argmax (null). */
    act(features, rng, out = new Int32Array(manifest.dims.action_dim)) {
      forward(features);
      return decide(rng, out);
    },
  };
}
