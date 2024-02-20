// use numpy::Ix1;
use numpy::ndarray::ArrayViewD;
// use pyo3::ffi::_PyCFunctionFast;
use chrono::{Datelike, NaiveDateTime, Timelike};
use pyo3::prelude::*;
use pyo3::types::PyModule;
// use numpy::borrow::PyReadonlyArray1;
use numpy::{PyArrayDyn,PyArray, PyReadwriteArrayDyn};
// use numpy::ndarray::ArrayViewMutD;

/// A Python module implemented in Rust. The name of this function is the Rust module name!
#[pymodule]
fn rust_simulation(py: Python, m: &PyModule) -> PyResult<()> {
    
    fn rust_calculate_array_ghi_times<'a>(
        local_times: ArrayViewD<'_, u64>,
        local_times_len: usize,
    ) -> (Vec<f64>, Vec<f64>) {
        let mut datetimes: Vec<_> = Vec::with_capacity(local_times_len);

        for &unix_time_stamp in local_times {
            let datetime = NaiveDateTime::from_timestamp_opt(unix_time_stamp as i64, 0).unwrap();
            datetimes.push(datetime);
        }

        let day_of_year_out: Vec<f64> = datetimes
            .iter()
            .map(|&date| date.date().ordinal() as f64)
            .collect();
        let local_time_out: Vec<f64> = datetimes
            .iter()
            .map(|&date| date.time().num_seconds_from_midnight() as f64 / 3600.0)
            .collect();

        (day_of_year_out, local_time_out)
    }


    // fn closest_gis_indices_loop() {

    // }

    #[pyfn(m)]
    #[pyo3(name = "calculate_array_ghi_times")]
    fn calculate_array_ghi_times<'py>(
        py: Python<'py>,
        python_local_times: PyReadwriteArrayDyn<'py, u64>,
    ) -> (&'py PyArrayDyn<f64>, &'py PyArrayDyn<f64>) {
        let local_times = python_local_times.as_array();
        let local_times_len = local_times.len();
        let (day_of_year_out, local_time_out) =
            rust_calculate_array_ghi_times(local_times, local_times_len);
        let py_day_out = PyArray::from_vec(py, day_of_year_out).to_dyn();
        let py_time_out = PyArray::from_vec(py, local_time_out).to_dyn();
        (py_day_out, py_time_out)
    }

    Ok(())
}
