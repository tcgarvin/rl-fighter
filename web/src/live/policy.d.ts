// Types for policy.js, which stays plain JS so the Node parity test runs the exact
// file the page ships.

export const MANIFEST_FORMAT: "rlf.web_policy/1";

export type Rng = () => number;

export interface PolicyHead {
  name: string;
  action_start: number;
  count: number;
  choices: number;
  logit_start: number;
  masked_value: number | null;
}

export interface PolicyManifest {
  format: string;
  sim_version: number;
  obs_dim: number;
  action_width: number;
  n_logits: number;
  weights_file: string;
  weights_floats: number;
  heads: PolicyHead[];
  match_config: { arena_radius: number; time_limit_ticks: number; reaction_ticks: number; fleets: string[][] };
  source: { checkpoint: string; sha256: string; update: number | null; kind: string | null };
}

export interface Policy {
  manifest: PolicyManifest;
  forward(obs: Float32Array): Float32Array;
  actFromLogits(logits: Float32Array, headValid: Uint8Array, rng: Rng | null, row: Int8Array): Int8Array;
  act(obs: Float32Array, headValid: Uint8Array, rng: Rng | null, row?: Int8Array): Int8Array;
}

export function mulberry32(seed: number): Rng;

export function createPolicy(
  manifest: PolicyManifest,
  weightsBuffer: ArrayBuffer,
  expect: { simVersion: number; obsDim: number; actionWidth: number },
): Policy;
