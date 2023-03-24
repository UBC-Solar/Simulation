package main

import "C"
import (
	"math"
	"time"
	"unsafe"
)

//export calculate_array_GHI_times
func calculate_array_GHI_times(local_times_inPtr *int64,
	local_times_ptrSize int64,
	day_of_year_outPtr *float64,
	day_of_year_ptrSize int64,
	local_time_outPtr *float64,
	local_time_ptrSize int64) {

	local_times := unsafe.Slice(local_times_inPtr, local_times_ptrSize)
	var date = make([]time.Time, local_times_ptrSize)

	for i := range local_times {
		unixTimeStamp := local_times[i]
		timeStamp := time.Unix(unixTimeStamp, 0).UTC()

		date[i] = timeStamp
	}

	day_of_year_channel := make(chan []float64)
	local_time_channel := make(chan []float64)

	go get_day_of_year(date, int64(len(date)), day_of_year_channel)
	go get_local_time(date, int64(len(date)), local_time_channel)

	day_of_year_in := <-day_of_year_channel
	local_time_in := <-local_time_channel

	day_of_year_out := unsafe.Slice(day_of_year_outPtr, day_of_year_ptrSize)
	local_time_out := unsafe.Slice(local_time_outPtr, local_time_ptrSize)

	//day_of_year_out = day_of_year_in
	//local_time_out = local_time_in

	for i := range day_of_year_in {
		day_of_year_out[i] = day_of_year_in[i]
		local_time_out[i] = local_time_in[i]
	}
}

func get_local_time(date []time.Time, size int64, channel chan []float64) {
	local_time := make([]float64, size)
	for i := range date {
		local_time[i] = float64(date[i].Hour()) + (float64(date[i].Minute()*60+date[i].Second()) / 3600)
	}
	channel <- local_time
}

func get_day_of_year(date []time.Time, size int64, channel chan []float64) {
	day_of_year := make([]float64, size)
	for i := range date {
		day_of_year[i] = float64(date[i].YearDay())
	}
	channel <- day_of_year
}

//export closest_gis_indices_loop
func closest_gis_indices_loop(averageDistancesPtr *float64,
	averageDistancesSize int64,
	cumulativeDistancesPtr *float64,
	cumulativeDistancesSize int64,
	resultsPtr *int64,
	resultsSize int64,
) {

	//current_coordinate_index = 0
	var currentCoordinateIndex int64 = 0

	result := unsafe.Slice(resultsPtr, resultsSize)
	averageDistances := unsafe.Slice(averageDistancesPtr, averageDistancesSize)
	cumulativeDistances := unsafe.Slice(cumulativeDistancesPtr, cumulativeDistancesSize)

	//for distance in np.nditer(cumulative_distances):
	for i := range cumulativeDistances {
		if cumulativeDistances[i] > averageDistances[currentCoordinateIndex] {
			if currentCoordinateIndex > int64(len(averageDistances)-1) {
				currentCoordinateIndex = int64(len(averageDistances) - 1)
			} else {
				currentCoordinateIndex += 1
				if currentCoordinateIndex > int64(len(averageDistances)-1) {
					currentCoordinateIndex = int64(len(averageDistances) - 1)
				}
			}
		}
		//result.append(current_coordinate_index)
		result[i] = currentCoordinateIndex
	}
}

//export closest_weather_indices_loop
func closest_weather_indices_loop(cumulativeDistancesPtr *float64,
	cumulativeDistancesSize int64,
	averageDistancesPtr *float64,
	averageDistancesSize int64,
	resultsPtr *int64,
	resultsSize int64) {

	var currentCoordinateIndex int64 = 0
	cumulativeDistances := unsafe.Slice(cumulativeDistancesPtr, cumulativeDistancesSize)
	averageDistances := unsafe.Slice(averageDistancesPtr, averageDistancesSize)
	result := unsafe.Slice(resultsPtr, resultsSize)

	for i := range cumulativeDistances {
		if currentCoordinateIndex > averageDistancesSize-1 {
			currentCoordinateIndex = averageDistancesSize - 1
		}

		if cumulativeDistances[i] > averageDistances[currentCoordinateIndex] {
			currentCoordinateIndex += 1
			if currentCoordinateIndex > averageDistancesSize-1 {
				currentCoordinateIndex = averageDistancesSize - 1
			}
		}

		result[i] = currentCoordinateIndex
	}
}

//export speeds_with_waypoints_loop
func speeds_with_waypoints_loop(speeds_inPtr *float64,
	speeds_ptrSize int64,
	distances_inPtr *float64,
	distances_ptrSize int64,
	waypoints_inPtr *int64,
	waypoints_ptrSize int64,
) {

	speeds := unsafe.Slice(speeds_inPtr, speeds_ptrSize)
	distances := unsafe.Slice(distances_inPtr, distances_ptrSize)
	waypoints := unsafe.Slice(waypoints_inPtr, waypoints_ptrSize)

	// margin of error with double arithmetic
	delta := 0.05
	// current path coordinate
	var path_index int64 = 0
	// stores the interim distance travelled between two path coordinates
	temp_distance_travelled := 0.0

	for i := range speeds {
		distance := speeds[i]
		total_distance_travelled := 0.0
		waypoint_flag := 0

		for distance+temp_distance_travelled > distances[path_index]-delta {
			distance = distance + temp_distance_travelled - distances[path_index]
			total_distance_travelled += distances[path_index] - temp_distance_travelled
			temp_distance_travelled = 0
			path_index += 1

			if path_index >= distances_ptrSize {
				break
			}

			if len(waypoints) > 0 && path_index == waypoints[0] {
				// delete the waypoint we just reached from the wp array
				waypoints = append(waypoints[:0], waypoints[1:]...)

				// update the current speed to be only what we travelled this second
				speeds[i] = total_distance_travelled

				// replace the speeds with 0's
				k := i + 1
				for k < i+1+45*60 {
					speeds[k] = 0
					k++
				}

				i += 45*60 - 1
				distance = 0 // shouldn't travel anymore in this second
				waypoint_flag = 1
				break
			}

			if waypoint_flag == 1 {
				continue
			}

		}

		if path_index >= distances_ptrSize {
			break
		}

		// If I still have distance to travel but can't reach the next coordinate
		if distance+temp_distance_travelled < distances[path_index]-delta {
			// Update total distance travelled
			total_distance_travelled += distance

			// Add onto the temporary distance between two coordinates
			temp_distance_travelled += distance
		}

		i += 1

	}
}

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
