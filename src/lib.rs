use pyo3::prelude::*;
use numpy::ndarray::ArrayViewD;
use numpy::{PyArray, PyArrayDyn, PyReadwriteArrayDyn};

/// A Python module implemented in Rust. The name of this function is the Rust module name!
#[pymodule]
#[pyo3(name = "core")]
fn rust_simulation(_py: Python, m: &PyModule) -> PyResult<()> {
    fn constrain_speeds(speed_limits: ArrayViewD<f64>,  speeds: ArrayViewD<f64>, tick: i32) -> Vec<f64> {
        let mut distance: f64 = 0.0;
        static KMH_TO_MS: f64 = 1.0 / 3.6;

        let ret: Vec<f64> = speeds.iter().map(| speed: &f64 | {
            let speed_limit: f64 = speed_limits[distance.floor() as usize];
            let vehicle_speed: f64 =f64::min(speed_limit, *speed);
            distance += vehicle_speed * KMH_TO_MS * tick as f64;
            vehicle_speed
        }).collect(); 

        return ret

    }

    #[pyfn(m)]
    #[pyo3(name = "constrain_speeds")]
    fn constrain_speeds_py<'py>(py: Python<'py>, x: PyReadwriteArrayDyn<'py, f64>, y: PyReadwriteArrayDyn<'py, f64>, z: i32) -> &'py PyArrayDyn<f64> {
        let x = x.as_array();
        let y = y.as_array();
        let result = constrain_speeds(x, y, z);
        return PyArray::from_vec(py, result).to_dyn();
    }

    Ok(())
}