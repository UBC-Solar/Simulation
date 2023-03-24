package main

//
//import "C"
//import (
//	"unsafe"
//)
//
////export closest_gis_indices_loop
//func closest_gis_indices_loop(averageDistancesPtr *float64,
//	averageDistancesSize int64,
//	cumulativeDistancesPtr *float64,
//	cumulativeDistancesSize int64,
//	resultsPtr *int64,
//	resultsSize int64,
//) {
//
//	//current_coordinate_index = 0
//	var currentCoordinateIndex int64 = 0
//
//	result := unsafe.Slice(resultsPtr, resultsSize)
//	averageDistances := unsafe.Slice(averageDistancesPtr, averageDistancesSize)
//	cumulativeDistances := unsafe.Slice(cumulativeDistancesPtr, cumulativeDistancesSize)
//
//	//for distance in np.nditer(cumulative_distances):
//	for i := range cumulativeDistances {
//		if cumulativeDistances[i] > averageDistances[currentCoordinateIndex] {
//			if currentCoordinateIndex > int64(len(averageDistances)-1) {
//				currentCoordinateIndex = int64(len(averageDistances) - 1)
//			} else {
//				currentCoordinateIndex += 1
//				if currentCoordinateIndex > int64(len(averageDistances)-1) {
//					currentCoordinateIndex = int64(len(averageDistances) - 1)
//				}
//			}
//		}
//		//result.append(current_coordinate_index)
//		result[i] = currentCoordinateIndex
//	}
//}
//
//func main() {
//}
