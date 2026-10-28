//! `rlf_sim`: Python bindings for the sim. The batched VecEnv lands in WP9.

use pyo3::prelude::*;

#[pymodule]
fn rlf_sim(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("SIM_VERSION", sim::SIM_VERSION)?;
    Ok(())
}
