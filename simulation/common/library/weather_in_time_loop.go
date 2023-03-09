package main

import "C"
import (
	"math"
	"unsafe"
)

//export weather_in_time_loop
func weather_in_time_loop(unix_timestamps_inPtr *float64,
	closest_time_stamp_indices_outPtr *float64,
	dt_local_array_inPtr *float64,
	dt_local_array_inPtr_size int64,
	io_ptr_size int64) {

	unix_timestamps_in := unsafe.Slice(unix_timestamps_inPtr, io_ptr_size)
	dt_local_array := unsafe.Slice(dt_local_array_inPtr, dt_local_array_inPtr_size)
	closest_time_stamp_indices_out := unsafe.Slice(closest_time_stamp_indices_outPtr, io_ptr_size)

	for index := range unix_timestamps_in {

		//unix_timestamp_array = np.full_like(dt_local_array, fill_value=unix_timestamp)
		unix_timestamp_array := make([]float64, dt_local_array_inPtr_size)
		for i := range unix_timestamp_array {
			var unix_timestamp = unix_timestamps_in[index]
			unix_timestamp_array[i] = unix_timestamp
        }

		//differences = np.abs(unix_timestamp_array - dt_local_array)
		differences := make([]float64, dt_local_array_inPtr_size)
		for j := range unix_timestamp_array {
			differences[j] = math.Abs(float64(unix_timestamp_array[j] - dt_local_array[j]))
		}

		//minimum__index = np.argmin(differences)
		min := differences[0]
		min_index := 0

		for d, d_value := range differences {
			if d_value < min {
				min = d_value
				min_index = d
			}
		}
		//closest_time_stamp_indices.append(minimum_index)
		closest_time_stamp_indices_out[index] = float64(min_index)
	}
}

func main() {
}
