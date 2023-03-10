import ctypes
import pathlib
import array
import numpy as np
import os

class Libraries:
    """
    Manages all GoLang binaries, verifies compatibility, and contains GoLang implementations and pointer generation
    methods.
    """
    def __init__(self, raiseExceptionOnFail=True):
        """
        :param raiseExceptionOnFail: Boolean to control whether an exception should be raised if Go binaries cant be found. Should not be set to false unless that scenario is handled.
        """
        self.raiseExceptionOnFail = raiseExceptionOnFail

        self.go_directory = self.GetGoDirectory()

        if self.go_directory is not None:
            self.gis_library = ctypes.cdll.LoadLibrary(f"{self.go_directory}/closest_gis_indices_loop.so")
            self.gis_library.closest_gis_indices_loop.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_long,
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_int64),
                ctypes.c_long,
            ]

            self.weather_library = ctypes.cdll.LoadLibrary(f"{self.go_directory}/weather_in_time_loop.so")
            self.weather_library.weather_in_time_loop.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.c_longlong
            ]

    def GetGoDirectory(self):
        """
        Will get the directory to compatible go binaries else return None/raise an exception.
        :returns: Path to compatible GoLang binaries
        """

        binaries_directory = f"{pathlib.Path(__file__).parent}/binaries"

        # Get list of possible folders that could contain binaries, and filter out non-folders
        binary_containers = [f for f in os.listdir(binaries_directory) if os.path.isdir(os.path.join(binaries_directory, f))]

        # Try to find compatible binaries by checking until compatible binaries are found
        try:
            for binary_container in binary_containers:
                try:
                    ctypes.cdll.LoadLibrary(f"{binaries_directory}/{binary_container}/compatibility_check.so")
                    return f"{binaries_directory}/{binary_container}"
                except:
                    pass
        except:
            if self.raiseExceptionOnFail:
                raise Exception("GoLang binaries not found for your operating system. "
                                "Please either compile them for your operating system or disable GoLang usage "
                                "in Simulation instantiation.")
            return None

    def found_compatible_binaries(self):
        """
        :returns: Boolean which indicates if compatible Go binaries were found and loaded.
        """
        return self.go_directory is not None

    # ---- GoLang implementation of functions and methods ---- #

    def calculate_closest_gis_indices(self, cumulative_distances, path_distances):
        """
        Faster GoLang implementation of calculate_closest_gis_indices

        :param cumulative_distances: (float[N]) array of distances, where cumulative_distances[x] > cumulative_distances[x-1]

        :returns: (float[N]) array of indices of path
        """

        path_distances = path_distances.copy()

        # Generate pointers to arrays to pass to a Go binary
        path_distances_copy = array.array('d', path_distances)
        path_distances_pointer = (
                ctypes.c_double * len(path_distances_copy)).from_buffer(path_distances_copy)

        cumulative_distances_copy = array.array('d', cumulative_distances)
        cumulative_distances_pointer = (
                ctypes.c_double * len(cumulative_distances_copy)).from_buffer(cumulative_distances_copy)

        # While the previous two pointers are for inputs, this pointer will point to an empty array that Go can write to
        results = array.array('l', [0] * len(cumulative_distances))
        results_pointer = (
                ctypes.c_long * len(results)).from_buffer(results)

        # Execute the Go shared library (compiled Go function) and pass it the pointers we generated
        self.gis_library.closest_gis_indices_loop(
            path_distances_pointer,
            len(path_distances),
            cumulative_distances_pointer,
            results_pointer,
            len(cumulative_distances))

        return np.array(results, 'i')

    def calculate_closest_timestamp_indices(self, unix_timestamps, dt_local_array):
        """
        GoLang implementation to find the indices of the closest timestamps in dt_local_array and package them into a NumPy Array

        :param unix_timestamps: NumPy Array (float[N]) unix timestamps of the vehicle's journey
        :param dt_local_array: NumPy Array (float[N]) local times, represented as unix timestamps

        :returns: NumPy Array (int[N]) containing closest timestamp indices used by get_weather_forecast_in_time
        """

        # Generate pointers to arrays to pass to a Go binary
        unix_timestamps_copy = array.array('d', unix_timestamps)
        unix_timestamps_pointer = (ctypes.c_double * len(unix_timestamps_copy)).from_buffer(unix_timestamps_copy)

        dt_local_arr_copy = array.array('d', dt_local_array)
        dt_local_arr_pointer = (ctypes.c_double * len(dt_local_arr_copy)).from_buffer(dt_local_arr_copy)

        # While the previous two pointers are for inputs, this pointer will point to an empty array that Go can write to
        closest_time_stamp_indices = array.array('d', [0] * len(unix_timestamps))
        closest_time_stamp_indices_pointer = (
                ctypes.c_double * len(closest_time_stamp_indices)).from_buffer(closest_time_stamp_indices)

        # Execute the Go shared library (compiled Go function) and pass it the pointers we generated
        self.weather_library.weather_in_time_loop(
            unix_timestamps_pointer,
            closest_time_stamp_indices_pointer,
            dt_local_arr_pointer,
            len(dt_local_array),
            len(unix_timestamps))

        return np.array(closest_time_stamp_indices, 'i')


if __name__ == "__main__":
    library = Libraries()
