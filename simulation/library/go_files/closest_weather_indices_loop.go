package main

import "C"

////export closest_weather_indices_loop
//func closest_weather_indices_loop(cumulativeDistancesPtr *float64,
//	cumulativeDistancesSize int64,
//	averageDistancesPtr *float64,
//	averageDistancesSize int64,
//	resultsPtr *int64,
//	resultsSize int64) {
//
//	var currentCoordinateIndex int64 = 0
//	cumulativeDistances := unsafe.Slice(cumulativeDistancesPtr, cumulativeDistancesSize)
//	averageDistances := unsafe.Slice(averageDistancesPtr, averageDistancesSize)
//	result := unsafe.Slice(resultsPtr, resultsSize)
//
//	for i := range cumulativeDistances {
//		if currentCoordinateIndex > averageDistancesSize-1 {
//			currentCoordinateIndex = averageDistancesSize - 1
//		}
//
//		if cumulativeDistances[i] > averageDistances[currentCoordinateIndex] {
//			currentCoordinateIndex += 1
//			if currentCoordinateIndex > averageDistancesSize-1 {
//				currentCoordinateIndex = averageDistancesSize - 1
//			}
//		}
//
//		result[i] = currentCoordinateIndex
//	}
//}

func main() {
}
