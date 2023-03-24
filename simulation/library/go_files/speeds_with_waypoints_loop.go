package main

//
//import "C"
//import (
//	"fmt"
//	"unsafe"
//)
//
////export speeds_with_waypoints_loop
//func speeds_with_waypoints_loop(speeds_inPtr *float64,
//	speeds_ptrSize int64,
//	distances_inPtr *float64,
//	distances_ptrSize int64,
//	waypoints_inPtr *int64,
//	waypoints_ptrSize int64,
//) {
//
//	speeds := unsafe.Slice(speeds_inPtr, speeds_ptrSize)
//	distances := unsafe.Slice(distances_inPtr, distances_ptrSize)
//	waypoints := unsafe.Slice(waypoints_inPtr, waypoints_ptrSize)
//
//	// margin of error with double arithmetic
//	delta := 0.05
//	// current path coordinate
//	var path_index int64 = 0
//	// stores the interim distance travelled between two path coordinates
//	temp_distance_travelled := 0.0
//
//	for i := range speeds {
//		distance := speeds[i]
//		total_distance_travelled := 0.0
//		waypoint_flag := 0
//
//		for distance+temp_distance_travelled > distances[path_index]-delta {
//			distance = distance + temp_distance_travelled - distances[path_index]
//			total_distance_travelled += distances[path_index] - temp_distance_travelled
//			temp_distance_travelled = 0
//			path_index += 1
//
//			if path_index >= distances_ptrSize {
//				break
//			}
//
//			if len(waypoints) > 0 && path_index == waypoints[0] {
//				fmt.Println("Waypoint :)")
//				// delete the waypoint we just reached from the wp array
//				waypoints = append(waypoints[:0], waypoints[1:]...)
//
//				// update the current speed to be only what we travelled this second
//				speeds[i] = total_distance_travelled
//
//				// replace the speeds with 0's
//				k := i + 1
//				for k < i+1+45*60 {
//					speeds[k] = 0
//					k++
//				}
//
//				i += 45*60 - 1
//				distance = 0 // shouldn't travel anymore in this second
//				waypoint_flag = 1
//				break
//			}
//
//			if waypoint_flag == 1 {
//				continue
//			}
//
//		}
//
//		if path_index >= distances_ptrSize {
//			break
//		}
//
//		// If I still have distance to travel but can't reach the next coordinate
//		if distance+temp_distance_travelled < distances[path_index]-delta {
//			// Update total distance travelled
//			total_distance_travelled += distance
//
//			// Add onto the temporary distance between two coordinates
//			temp_distance_travelled += distance
//		}
//
//		i += 1
//
//	}
//}
//
//func main() {
//
//}
