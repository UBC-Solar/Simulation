// use numpy::Ix1;
use numpy::ndarray::{ArrayViewD, Array};
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
                    
                    current_coord_index = std::cmp::min(current_coord_index, average_distances.len() - 1);
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
                
                current_coord_index = std::cmp::min(current_coord_index, average_distances.len() - 1);
            }
            
            result.push(current_coord_index as i64);
        }

        result
    }


    fn rust_closest_timestamp_indices(
        unix_timestamps: ArrayViewD<'_, i64>,
        dt_local_array: ArrayViewD<'_, i64>,
    ) -> Vec<usize> {
        let mut closest_time_stamp_indices: Vec<usize> = Vec::new();

        for unix_timestamp in unix_timestamps{

            let unix_timestamp_array = Array::from_elem(dt_local_array.shape(), unix_timestamp as &i64);
            let mut differences: Vec<i64> = Vec::new();

            for i in 0..unix_timestamp_array.len() {
                differences.push((unix_timestamp-dt_local_array[i]).abs());
            }
            
            let (min_index, _) = differences.iter().enumerate().min_by_key(|(_, &v)| v).unwrap();
            closest_time_stamp_indices.push(min_index)

        }
        closest_time_stamp_indices
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
    #[pyo3(name = "closest_timestamp_indices")]
    fn closest_timestamp_indices<'py>(
        py: Python<'py>,
        python_unix_timestamps: PyReadwriteArrayDyn<'py, i64>,
        python_dt_local_array: PyReadwriteArrayDyn<'py, i64>,
    ) -> &'py PyArrayDyn<usize> {
        let unix_timestamps = python_unix_timestamps.as_array();
        let dt_local_array = python_dt_local_array.as_array();
        let result = rust_closest_timestamp_indices(unix_timestamps, dt_local_array);
        let py_result = PyArray::from_vec(py, result).to_dyn();
        py_result
    }

    Ok(())
}




    // fn weather_in_time(
    //     weather_forecast: ArrayViewD<'_, f64>,
    //     linearized_reults: ArrayViewD<'_, f64>,
    //     unix_timestamps: ArrayViewD<'_, f64>,
    //     indices: ArrayViewD<'_, i64>,
    // ){

    //     let shape = weather_forecast.shape();
    //     let (weather_coords, weather_times, weather_endpoints) = (shape[0], shape[1], shape[2]);
        
    //     assert_eq!(indices.len(),unix_timestamps.len());
    //     assert_eq!(unix_timestamps.len(),linearized_reults.len());

    //     let simulation_duration = indices.len();

    //     let mut full_weather_forecast_at_coords = ArrayViewD::with_capacity(simulation_duration);
    //     for &index in indices {
    //         full_weather_forecast_at_coords.push(weather_forecast.index_axis(numpy::ndarray::Axis(0), index as usize).to_owned());
    //     }

    //     let weather_times = full_weather_forecast_at_coords[0].shape()[0];

    //     let mut dt_local_array = Vec::with_capacity(weather_times);
    //     for i in 0..weather_times {
    //         dt_local_array.push(full_weather_forecast_at_coords.index_axis(numpy::ndarray::Axis(1), i)[0][4]);
        // }
    // }

    // fn get_weather_in_time(
    //     weather_forecast: Array3<f64>,
    //     unix_timestamps: &[f64],
    //     indices: &[usize],
    // ) -> Array2<f64> {
        
    //     let mut full_weather_forecast_at_coords_slices = Vec::new();
    //     for &index in indices {
    //         let slice = weather_forecast.slice(s![index, .., ..]);
    //         let mut slice_vec = Vec::new();
    //         for row in slice.outer_iter() {
    //             slice_vec.push(row.to_vec());
    //         }
    //         full_weather_forecast_at_coords_slices.push(slice_vec);
    //     }

    //     let mut closest_timestamp_indices = Vec::new();
    //     for &unix_timestamp in unix_timestamps {
    //         let mut current_min_indices = Vec::new();
    //         for full_weather_slice in &full_weather_forecast_at_coords_slices {
    //             let dt_local_array = &full_weather_slice[0][4];
    //             let unix_timestamp_array = Array1::from_elem(full_weather_slice.len(), unix_timestamp);
    //             let differences = (unix_timestamp_array - dt_local_array).mapv(f64::abs);
    //             let minimum_index = differences.argmin().unwrap();
    //             current_min_indices.push(minimum_index);
    //         }
    //         closest_timestamp_indices.push(current_min_indices);
    //     }

    //     let mut result_slices = Vec::new();
    //     for (i, timestamp_indices) in closest_timestamp_indices.iter().enumerate() {
    //         let mut temp = Vec::new();
    //         for (j, &index) in timestamp_indices.iter().enumerate() {
    //             let slice = &full_weather_forecast_at_coords_slices[j][i];
    //             temp.extend_from_slice(&slice);
    //         }
    //         result_slices.push(temp);
    //     }

    //     let len = result_slices[0].len();
    //     Array2::from_shape_vec((result_slices.len(), len), result_slices.into_iter().flatten()).unwrap()
    // }


    // fn calculate_closest_timestamp_indices(
    //     unix_timestamps: &[f64],
    //     dt_local_array: &Array1<f64>,
    // ) -> Vec<usize> {
    //     let mut closest_time_stamp_indices = Vec::new();
    //     for &unix_timestamp in unix_timestamps {
    //         let unix_timestamp_array = Array1::from_elem(dt_local_array.len(), unix_timestamp);
    //         let differences = (unix_timestamp_array - dt_local_array).mapv(f64::abs);
    //         let minimum_index = differences.argmin().unwrap();
    //         closest_time_stamp_indices.push(minimum_index);
    //     }
    //     closest_time_stamp_indices
    // }


        // use ndarray::{Array2, Array1};

    // fn weather_in_time(
    //     unix_timestamps: ArrayViewD<f64>,
    //     indices: ArrayViewD<usize>,
    //     weather_forecast: ArrayViewD<f64>,  
    // ) -> Array2<f64> {
    //     let full_weather_forecast_at_coords = weather_forecast.index_axis(ndarray::Axis(0), indices.to_owned());
    //     let dt_local_array = full_weather_forecast_at_coords.slice(s![0,.., 4]);

    //     let temp_0 = Array1::range(0., full_weather_forecast_at_coords.shape()[0] as f64, 1.);
    //     let closest_timestamp_indices = python_calculate_closest_timestamp_indices(unix_timestamps, &dt_local_array);

    //     full_weather_forecast_at_coords.select(ndarray::Axis(0), &temp_0)
    //         .select(ndarray::Axis(1), &closest_timestamp_indices)
    // }