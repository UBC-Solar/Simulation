package main

import "C"
import (
	"fmt"
	"strconv"
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

func main() {
	unixTimeStamp := "1612076500"
	unixTimeStampInt, _ := strconv.Atoi(unixTimeStamp)
	timeStamp := time.Unix(int64(unixTimeStampInt), 0).UTC()
	fmt.Println(timeStamp)
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
