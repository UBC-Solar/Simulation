package main

import "C"
import (
	"unsafe"
)

//export closest_gis_indices_loop
func closest_gis_indices_loop(cumulative_distances_inPtr *float64,
	cumulative_distances_ptrSize int64,
	average_distances_ptr *float64,
	average_distances_Size int64,
	results_outPtr *int64, ) {

	var current_coordinate_index int64 = 0
	result := unsafe.Slice(results_outPtr, cumulative_distances_ptrSize)
	average_distances := unsafe.Slice(average_distances_ptr, average_distances_Size)
	cumulative_distances := unsafe.Slice(cumulative_distances_inPtr, cumulative_distances_ptrSize)

	//for distance in np.nditer(cumulative_distances):
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
