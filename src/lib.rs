use chrono::{Datelike, NaiveDateTime, Timelike};
use numpy::ndarray::{s, Array, Array2, ArrayViewD, ArrayViewMut2, ArrayViewMut3, Axis};
use numpy::{PyArray, PyArrayDyn, PyReadwriteArrayDyn};
use pyo3::prelude::*;
use pyo3::types::PyModule;

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
        cumulative_distances: ArrayViewD<'_, f64>,
        average_distances: ArrayViewD<'_, f64>,
    ) -> Vec<i64> {
        let mut current_coord_index: usize = 0;
        let mut result: Vec<i64> = Vec::with_capacity(cumulative_distances.len());

        for &distance in cumulative_distances {
            if distance > average_distances[current_coord_index] {
                if current_coord_index > average_distances.len() - 1 {
                    current_coord_index = average_distances.len() - 1;
                } else {
                    current_coord_index += 1;

                    current_coord_index =
                        std::cmp::min(current_coord_index, average_distances.len() - 1);
                }
            }
            result.push(current_coord_index as i64);
        }

        result
    }

    fn rust_closest_weather_indices_loop(
        cumulative_distances: ArrayViewD<'_, f64>,
        average_distances: ArrayViewD<'_, f64>,
    ) -> Vec<i64> {
        let mut current_coord_index: usize = 0;
        let mut result: Vec<i64> = Vec::with_capacity(cumulative_distances.len());

        for &distance in cumulative_distances {
            current_coord_index = std::cmp::min(current_coord_index, average_distances.len() - 1);

            if distance > average_distances[current_coord_index] {
                current_coord_index += 1;

                current_coord_index =
                    std::cmp::min(current_coord_index, average_distances.len() - 1);
            }

            result.push(current_coord_index as i64);
        }

        result
    }

    fn rust_weather_in_time(
        unix_timestamps: ArrayViewD<'_, i64>,
        indices: ArrayViewD<'_, i64>,
        weather_forecast: ArrayViewD<f64>,
        dt_index: u8
    ) -> Array2<f64> {
        // Obtain dimensions for arrays and slices
        let weather_forecast_raw_dim = weather_forecast.raw_dim();
        let full_forecast_shape = (
            weather_forecast_raw_dim[0],
            weather_forecast_raw_dim[1],
            weather_forecast_raw_dim[2],
        );
        let weather_at_coord_shape = (full_forecast_shape.1, full_forecast_shape.2);
        let weather_in_time_shape = (indices.len(), full_forecast_shape.2);

        // Create an empty full_weather_forecast_at_coords array (all zeros)
        let indexed_weather_shape = (indices.len(), full_forecast_shape.1, full_forecast_shape.2);
        let mut placeholder1: Vec<f64> =
            vec![0.0; indexed_weather_shape.0 * indexed_weather_shape.1 * indexed_weather_shape.2];
        let mut indexed_forecast =
            ArrayViewMut3::from_shape(indexed_weather_shape, &mut placeholder1).unwrap();

        // Fill full_weather_forecast_at_coords with the 2d slices at [indices]
        for (out_index, &coord_index) in indices.iter().enumerate() {
            let slice_2d = weather_forecast
                .slice(s![coord_index as usize, .., ..])
                .into_shape(weather_at_coord_shape)
                .unwrap();
            indexed_forecast
                .slice_mut(s![out_index, .., ..])
                .assign(&slice_2d);
        }

        let mut dt_local_array = Vec::with_capacity(full_forecast_shape.1);
        // Populate dt_local_array with the list of forecast's timestamps at the first coordinate
        // I don't really understand how this works
        let dt_local_arrayview = weather_forecast
            .index_axis_move(Axis(0), 0)
            .index_axis_move(Axis(1), dt_index as usize);
        for &timestamp in dt_local_arrayview {
            dt_local_array.push(timestamp as i64);
        }

        let closest_timestamp_indices =
            rust_closest_timestamp_indices(unix_timestamps, dt_local_array);

        // Create a mutable array of the desired shape with dummy initial values
        let mut placeholder2: Vec<f64> =
            vec![0.0; weather_in_time_shape.0 * weather_in_time_shape.1];
        let mut weather_in_time_arrayview =
            ArrayViewMut2::from_shape(weather_in_time_shape, &mut placeholder2).unwrap();
        for (index_1, &index_2) in closest_timestamp_indices.iter().enumerate() {
            let slice_1d = indexed_forecast
                .slice(s![index_1, index_2, ..])
                .into_shape(full_forecast_shape.2)
                .unwrap();
            weather_in_time_arrayview
                .slice_mut(s![index_1, ..])
                .assign(&slice_1d);
        }

        weather_in_time_arrayview.into_owned()
    }

    fn rust_closest_timestamp_indices(
        unix_timestamps: ArrayViewD<'_, i64>,
        dt_local_array: Vec<i64>,
    ) -> Vec<usize> {
        let mut closest_time_stamp_indices: Vec<usize> = Vec::new();

        for unix_timestamp in unix_timestamps {
            let unix_timestamp_array =
                Array::from_elem(dt_local_array.len(), unix_timestamp as &i64);
            let mut differences: Vec<i64> = Vec::new();

            for i in 0..unix_timestamp_array.len() {
                differences.push((unix_timestamp - dt_local_array[i]).abs());
            }

            let (min_index, _) = differences
                .iter()
                .enumerate()
                .min_by_key(|(_, &v)| v)
                .unwrap();
            closest_time_stamp_indices.push(min_index)
        }
        closest_time_stamp_indices
    }

    #[pyfn(m)]
    #[pyo3(name = "constrain_speeds")]
    fn constrain_speeds_py<'py>(py: Python<'py>, x: PyReadwriteArrayDyn<'py, f64>, y: PyReadwriteArrayDyn<'py, f64>, z: i32) -> &'py PyArrayDyn<f64> {
        let x = x.as_array();
        let y = y.as_array();
        let result = constrain_speeds(x, y, z);
        return PyArray::from_vec(py, result).to_dyn();
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
        python_cumulative_distances: PyReadwriteArrayDyn<'py, f64>,
        python_average_distances: PyReadwriteArrayDyn<'py, f64>,
    ) -> &'py PyArrayDyn<i64> {
        let average_distances = python_average_distances.as_array();
        let cumulative_distances = python_cumulative_distances.as_array();
        let result = rust_closest_gis_indices_loop(cumulative_distances, average_distances);
        let py_result = PyArray::from_vec(py, result).to_dyn();
        py_result
    }

    #[pyfn(m)]
    #[pyo3(name = "closest_weather_indices_loop")]
    fn closest_weather_indices_loop<'py>(
        py: Python<'py>,
        python_cumulative_distances: PyReadwriteArrayDyn<'py, f64>,
        python_average_distances: PyReadwriteArrayDyn<'py, f64>,
    ) -> &'py PyArrayDyn<i64> {
        let average_distances = python_average_distances.as_array();
        let cumulative_distances = python_cumulative_distances.as_array();
        let result = rust_closest_weather_indices_loop(cumulative_distances, average_distances);
        let py_result = PyArray::from_vec(py, result).to_dyn();
        py_result
    }

    #[pyfn(m)]
    #[pyo3(name = "weather_in_time")]
    fn weather_in_time<'py>(
        py: Python<'py>,
        python_unix_timestamps: PyReadwriteArrayDyn<'py, i64>,
        python_indices: PyReadwriteArrayDyn<'py, i64>,
        python_weather_forecast: PyReadwriteArrayDyn<'py, f64>,
        index: u8
    ) -> &'py PyArrayDyn<f64> {
        let unix_timestamps = python_unix_timestamps.as_array();
        let indices = python_indices.as_array();
        let weather_forecast = python_weather_forecast.as_array();
        let mut result = rust_weather_in_time(unix_timestamps, indices, weather_forecast, index);
        let py_result = PyArray::from_array(py, &mut result).to_dyn();
        py_result
    }

    Ok(())
}
