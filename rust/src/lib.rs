// use numpy::Ix1;
use numpy::ndarray::ArrayViewD;
// use pyo3::ffi::_PyCFunctionFast;
use chrono::{Datelike, NaiveDateTime, Timelike};
use pyo3::prelude::*;
use pyo3::types::PyModule;
// use numpy::borrow::PyReadonlyArray1;
use numpy::{PyArray, PyArrayDyn, PyReadwriteArrayDyn};
// use numpy::ndarray::ArrayViewMutD;

/// A Python module implemented in Rust. The name of this function is the Rust module name!
#[pymodule]
fn rust_simulation(_py: Python, m: &PyModule) -> PyResult<()> {
    fn rust_calculate_array_ghi_times<'a>(
        local_times: ArrayViewD<'_, u64>,
    ) -> (Vec<f64>, Vec<f64>) {
        let mut datetimes: Vec<_> = Vec::with_capacity(local_times.len());

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

    fn rust_closest_gis_indices_loop(
        average_distances: ArrayViewD<'_, f64>,
        cumulative_distances: ArrayViewD<'_, f64>,
    ) -> Vec<i64> {
        let mut current_coord_index: usize = 0;
        let mut result: Vec<i64> = Vec::with_capacity(cumulative_distances.len());

        for &distance in cumulative_distances {
            if distance > average_distances[current_coord_index] {
                if current_coord_index > average_distances.len() - 1 {
                    current_coord_index = average_distances.len() - 1;
                } else {
                    current_coord_index += 1;
                    if current_coord_index > average_distances.len() - 1 {
                        current_coord_index = average_distances.len() - 1;
                    }
                }
            }
            result.push(current_coord_index as i64);
        }

        result
    }

    #[pyfn(m)]
    #[pyo3(name = "calculate_array_ghi_times")]
    fn calculate_array_ghi_times<'py>(
        py: Python<'py>,
        python_local_times: PyReadwriteArrayDyn<'py, u64>,
    ) -> (&'py PyArrayDyn<f64>, &'py PyArrayDyn<f64>) {
        let local_times = python_local_times.as_array();
        let (day_of_year_out, local_time_out) = rust_calculate_array_ghi_times(local_times);
        let py_day_out = PyArray::from_vec(py, day_of_year_out).to_dyn();
        let py_time_out = PyArray::from_vec(py, local_time_out).to_dyn();
        (py_day_out, py_time_out)
    }

    #[pyfn(m)]
    #[pyo3(name = "closest_gis_indices_loop")]
    fn closest_gis_indices_loop<'py>(
        py: Python<'py>,
        python_average_distances: PyReadwriteArrayDyn<'py, f64>,
        python_cumulative_distances: PyReadwriteArrayDyn<'py, f64>,
    ) -> &'py PyArrayDyn<i64> {
        let average_distances = python_average_distances.as_array();
        let cumulative_distances = python_cumulative_distances.as_array();
        let result = rust_closest_gis_indices_loop(average_distances, cumulative_distances);
        let py_result = PyArray::from_vec(py, result).to_dyn();
        py_result
    }

    Ok(())
}
