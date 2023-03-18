package main

import "C"
import (
	"unsafe"
)

//export closest_weather_indices_loop
func closest_weather_indices_loop(cumulative_distances_inPtr *float64,
	cumulative_distances_ptrSize int64,
	average_distances_inPtr *float64,
	average_distances_ptrSize int64,
	results_outPtr *int64,
	results_ptrSize int64) {

	var currentCoordinateIndex int64 = 0
	cumulativeDistances := unsafe.Slice(cumulative_distances_inPtr, cumulative_distances_ptrSize)
	averageDistances := unsafe.Slice(average_distances_inPtr, average_distances_ptrSize)
	result := unsafe.Slice(results_outPtr, results_ptrSize)

	for i := range cumulativeDistances {
		if currentCoordinateIndex > average_distances_ptrSize-1 {
			currentCoordinateIndex = average_distances_ptrSize - 1
		}

		if cumulativeDistances[i] > averageDistances[currentCoordinateIndex] {
			currentCoordinateIndex += 1
			if currentCoordinateIndex > average_distances_ptrSize-1 {
				currentCoordinateIndex = average_distances_ptrSize - 1
			}
		}

		result[i] = currentCoordinateIndex
	}
}

func main() {
}
