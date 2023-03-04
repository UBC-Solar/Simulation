package main

import "C"
import (
	"math"
	"unsafe"
)

//export closest_gis_indices_loop
func closest_gis_indices_loop(path_distances_inPtr *float64,
	distances_ptrSize int64,
	cumulative_distances_inPtr *float64,
	results_outPtr *int64,
	cumulative_distances_ptrSize int64) {

	//current_coordinate_index = 0
	var current_coordinate_index int64 = 0
	//result = []
	result := unsafe.Slice(results_outPtr, cumulative_distances_ptrSize)

	//path_distances = self.path_distances.copy()
	path_distances := unsafe.Slice(path_distances_inPtr, distances_ptrSize)

	//cumulative_path_distances = np.cumsum(path_distances)
	cumulative_path_distances := make([]float64, distances_ptrSize)
	cumulative_path_distances[0] = 0
	var _int64 int64 = 1
	for i := _int64; i < distances_ptrSize-1; i++ {
		cumulative_path_distances[i+1] = cumulative_path_distances[i] + path_distances[i]
	}

	//cumulative_path_distances[::2] *= -1
	for i := range cumulative_path_distances {
		if i%2 == 0 {
			cumulative_path_distances[i] *= -1
		}
	}

	//average_distances = np.abs(np.diff(cumulative_path_distances) / 2)
	average_distances := make([]float64, distances_ptrSize-1)
	average_distances_Size := distances_ptrSize - 1
	for i := _int64; i < average_distances_Size-1; i++ {
		average_distances[i+1] = math.Abs((cumulative_path_distances[i+1] - cumulative_path_distances[i]) / 2)
	}

	//for distance in np.nditer(cumulative_distances):
	cumulative_distances := unsafe.Slice(cumulative_distances_inPtr, cumulative_distances_ptrSize)
	for i := range cumulative_distances {
		//if distance > average_distances[current_coordinate_index]:
		if cumulative_distances[i] > average_distances[current_coordinate_index] {
			//if current_coordinate_index > len(average_distances) - 1:
			if current_coordinate_index > average_distances_Size-1 {
				//current_coordinate_index = len(average_distances) - 1
				current_coordinate_index = average_distances_Size - 1
			} else {
				//current_coordinate_index += 1
				current_coordinate_index += 1
				//if current_coordinate_index > len(average_distances) - 1:
				if current_coordinate_index > average_distances_Size-1 {
					//current_coordinate_index = len(average_distances) - 1
					current_coordinate_index = average_distances_Size - 1
				}
			}
		}
		//result.append(current_coordinate_index)
		result[i] = current_coordinate_index
	}
}

func main() {
}
