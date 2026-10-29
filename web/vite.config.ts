import { resolve } from "node:path";
import { defineConfig } from "vite";

// Multi-page static site (docs/M2_PLAN.md §3). public/bundle/ (gitignored) holds the
// champion bundle that scripts/build_site.sh assembles: sim wasm, policy, catalogue.
export default defineConfig({
  root: __dirname,
  base: "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2022",
    rollupOptions: {
      input: {
        live: resolve(__dirname, "index.html"),
        notebook: resolve(__dirname, "notebook/index.html"),
        hulls: resolve(__dirname, "hulls/index.html"),
      },
    },
  },
});
