//! Browser bindings for the sim. `WasmMatch` lands in WP8.

use wasm_bindgen::prelude::*;

/// Lets the web client refuse a bundle built from a different sim version.
#[wasm_bindgen]
pub fn sim_version() -> u32 {
    sim::SIM_VERSION
}
