// Headless Chromium for the live page's screenshot and soak tools. Playwright is a
// devDependency of web/, so it resolves from web/node_modules. WebGL is real (ANGLE on
// SwiftShader unless RLF_GPU=1 asks for the host GPU).

import { createRequire } from "node:module";
import path from "node:path";
import { REPO } from "./load.mjs";

const require = createRequire(path.join(REPO, "web/package.json"));

export async function launch() {
  const { chromium } = require("playwright");
  const args = process.env.RLF_GPU === "1" ? ["--enable-gpu", "--use-angle=vulkan", "--ignore-gpu-blocklist"] : ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"];
  return chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required", ...args] });
}

/** Collect console errors and uncaught exceptions from a page. */
export function watchErrors(page, label) {
  const errors = [];
  page.on("pageerror", (err) => errors.push(`${label}: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`${label}: console: ${msg.text()}`);
  });
  return errors;
}
