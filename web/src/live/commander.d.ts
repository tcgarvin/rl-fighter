// Types for commander.js, which stays plain JS so the Node parity test runs the exact
// file the page ships.

import type { Rng } from "./policy.js";

export const COMMANDER_FORMAT: "rlf.web_commander/1";

export interface CommanderHead {
  name: "launch" | "waypoint" | "squad" | "order" | "target" | "ward" | "point";
  /** First action column. */
  col: number;
  count: number;
  choices: number;
  logitStart: number;
}

export const COMMANDER_HEADS: CommanderHead[];
export const COMMANDER_N_LOGITS: number;

/** [name, offset, width] of one block of WasmMatch.commander_features. */
export type FlatLayoutEntry = [string, number, number];

export interface CommanderManifest {
  format: string;
  io_version: number;
  dims: Record<string, number>;
  masked_logit: number;
  features_len: number;
  flat_layout: FlatLayoutEntry[];
  weights_file: string;
  weights_floats: number;
  tensors: Array<{ name: string; shape: number[]; offset: number }>;
  source: { checkpoint: string; sha256: string; update: number | null };
}

export interface Commander {
  manifest: CommanderManifest;
  forward(features: Float32Array): Float32Array;
  decide(rng: Rng | null, out: Int32Array): Int32Array;
  isAllowed(head: CommanderHead["name"], row: number, choice: number): boolean;
  act(features: Float32Array, rng: Rng | null, out?: Int32Array): Int32Array;
}

export function createCommander(
  manifest: CommanderManifest,
  weightsBuffer: ArrayBuffer,
  expect: { ioVersion: number; featuresLen: number; actionDim: number; flatLayout: FlatLayoutEntry[] },
): Commander;
