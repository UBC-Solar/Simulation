import ctypes
import pathlib
import array
import numpy as np
import os
from simulation.common.exceptions import LibrariesNotFound


class Libraries:
    """

    Manages all GoLang libraries, verifies compatibility, and contains GoLang implementations and pointer generation
    methods.

    """

    # Dictionary for converting between ctypes and their corresponding single-character identifier.
    ctypes_dict = {
        ctypes.c_double: 'd',
        ctypes.c_long: 'l',
        ctypes.c_int: 'i'
    }

    def __init__(self):
        self.go_directory = self.get_go_directory()

        # ----- Load Go Libraries ----- #

        if self.go_directory is not None:
            self.main_library = ctypes.cdll.LoadLibrary(f"{self.go_directory}/main.so")

            self.main_library.closest_gis_indices_loop.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_longlong),
                ctypes.c_longlong,
            ]

            self.main_library.weather_in_time_loop.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.c_longlong
            ]

            self.main_library.closest_weather_indices_loop.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_longlong),
                ctypes.c_longlong
            ]

            self.main_library.calculate_array_GHI_times.argtypes = [
                ctypes.POINTER(ctypes.c_longlong),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong
            ]

            self.main_library.speeds_with_waypoints_loop.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_longlong,
                ctypes.POINTER(ctypes.c_longlong),
                ctypes.c_longlong
            ]
            
            self.perlin_noise_library = ctypes.cdll.LoadLibrary(f"{self.go_directory}/perlin_noise.so")

            self.perlin_noise_library.generatePerlinNoise.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_uint,
                ctypes.c_uint,
                ctypes.c_float,
                ctypes.c_uint,
                ctypes.c_float,
                ctypes.c_float,
                ctypes.c_float,
                ctypes.c_uint
            ]

    @staticmethod
    def get_go_directory():
        """

        Will get the directory to compatible Go libraries else return None/raise an exception.

        :returns: Path to compatible GoLang binaries
        :rtype: str

        """

        binaries_directory = f"{pathlib.Path(__file__).parent}/binaries"

        # Get list of possible folders that could contain binaries, and filter out non-folders
        binary_containers = [f for f in os.listdir(binaries_directory) if
                             os.path.isdir(os.path.join(binaries_directory, f))]

        # Try to find compatible binaries by checking until compatible binaries are found
        for binary_container in binary_containers:
            try:
                ctypes.cdll.LoadLibrary(f"{binaries_directory}/{binary_container}/main.so")
                ctypes.cdll.LoadLibrary(f"{binaries_directory}/{binary_container}/perlin_noise.so")
                return f"{binaries_directory}/{binary_container}"
            except OSError:
                pass
        raise LibrariesNotFound("Go shared libraries not found for your platform. \n"
                                "Please either compile them for your platform or disable Go usage\n"
                                "in Simulation instantiation. \n"
                                "Verify that you have both main.so and perlin_noise.so compiled. \n")

    def found_compatible_binaries(self):
        """

        Check if compatible Go libraries were found and loaded.

        :returns: Boolean which indicates if compatible Go libraries were found and loaded.
        :rtype: bool

        """

        return self.go_directory is not None

    # ---- GoLang implementation of functions and methods ---- #

    def golang_calculate_closest_gis_indices(self, cumulative_distances, average_distances):
        """

        GoLang implementation of golang_calculate_closest_gis_indices. See parent function for documentation details.

        """

        # Generate pointers to arrays to pass to a Go binary
        average_distances_pointer = Libraries.generate_input_pointer(average_distances, ctypes.c_double)
        cumulative_distances_pointer = Libraries.generate_input_pointer(cumulative_distances, ctypes.c_double)
        results_pointer, results = Libraries.generate_output_pointer(len(cumulative_distances), ctypes.c_longlong)

        # Execute the Go shared library (compiled Go function) and pass it the pointers we generated
        self.main_library.closest_gis_indices_loop(
            average_distances_pointer,
            len(average_distances),
            cumulative_distances_pointer,
            len(cumulative_distances),
            results_pointer,
            len(results),
        )

        return np.array(results, 'i')

    def golang_calculate_closest_timestamp_indices(self, unix_timestamps, dt_local_array):
        """

        GoLang implementation of calculate_closest_timestamp_indices. See parent function for documentation details.

        """

        # Generate pointers to arrays to pass to a Go binary
        unix_timestamps_pointer = Libraries.generate_input_pointer(unix_timestamps, ctypes.c_double)
        dt_local_arr_pointer = Libraries.generate_input_pointer(dt_local_array, ctypes.c_double)
        closest_time_stamp_indices_pointer, closest_time_stamp_indices = Libraries.generate_output_pointer(
            unix_timestamps, ctypes.c_double)

        # Execute the Go shared library (compiled Go function) and pass it the pointers we generated
        self.main_library.weather_in_time_loop(
            unix_timestamps_pointer,
            closest_time_stamp_indices_pointer,
            dt_local_arr_pointer,
            len(dt_local_array),
            len(unix_timestamps))

        return np.array(closest_time_stamp_indices, 'i')

    def golang_calculate_closest_weather_indices(self, cumulative_distances, average_distances):
        """

        GoLang implementation of calculate_closest_weather_indices. See parent function for details.

        """

        # Get pointers for GoLang
        cumulative_distances_pointer = Libraries.generate_input_pointer(cumulative_distances, ctypes.c_double)
        average_distances_pointer = Libraries.generate_input_pointer(average_distances, ctypes.c_double)
        closest_weather_indices_pointer, closest_weather_indices = Libraries.generate_output_pointer(
            len(cumulative_distances), ctypes.c_longlong)

        self.main_library.closest_weather_indices_loop(
            cumulative_distances_pointer,
            len(cumulative_distances),
            average_distances_pointer,
            len(average_distances),
            closest_weather_indices_pointer,
            len(closest_weather_indices)
        )

        return np.array(closest_weather_indices, 'i')

    def golang_calculate_array_GHI_times(self, local_times):
        """

        GoLang implementation of calculate_array_GHI_times. See parent function for details.

        """

        # Get pointers for GoLang
        local_times_pointer = Libraries.generate_input_pointer(local_times, ctypes.c_longlong)
        day_of_year_pointer, day_of_year = Libraries.generate_output_pointer(len(local_times), ctypes.c_double)
        local_time_pointer, local_time = Libraries.generate_output_pointer(len(local_times), ctypes.c_double)

        self.main_library.calculate_array_GHI_times(
            local_times_pointer,
            len(local_times),
            day_of_year_pointer,
            len(day_of_year),
            local_time_pointer,
            len(local_time)
        )

        return np.array(day_of_year, 'd'), np.array(local_time, 'd')

    def golang_speeds_with_waypoints_loop(self, speeds, distances, waypoints):
        """

        GoLang implementation of speeds_with_waypoints_loop. See parent function for details.

        """

        # We need to flatten waypoints from a [1x7] matrix to a 1D array.
        flattened_waypoints = np.array([0] * len(waypoints))
        for i in range(len(waypoints)):
            flattened_waypoints[i] = waypoints[i][0]

        # Get pointers for GoLang
        new_speeds_pointer, new_speeds = Libraries.generate_input_output_pointer(speeds, ctypes.c_double)
        distances_pointer = Libraries.generate_input_pointer(distances, ctypes.c_double)
        waypoints_pointer = Libraries.generate_input_pointer(flattened_waypoints, ctypes.c_longlong)

        self.main_library.speeds_with_waypoints_loop(
            new_speeds_pointer,
            len(speeds),
            distances_pointer,
            len(distances),
            waypoints_pointer,
            len(waypoints)
        )

        return np.array(new_speeds, 'd')

    def golang_generate_perlin_noise(self, width=256, height=256, persistence=0.45, numLayers=8, roughness=7.5,
                                     baseRoughness=1.5, strength=1, randomSeed=0):
        """

        GoLang implementation of generate_perlin_noise. See parent function for details.

        """

        output_array = np.array([0] * (width * height))
        output_array_copy = output_array.astype(ctypes.c_float)
        ptr = output_array_copy.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

        self.perlin_noise_library.generatePerlinNoise(
            ptr,
            width,
            height,
            persistence,
            numLayers,
            roughness,
            baseRoughness,
            strength,
            randomSeed
        )

        return np.array(output_array_copy, 'f').reshape(width, height)

    @staticmethod
    def generate_input_pointer(input_array, c_type):
        """

        Generate a pointer to an input array to be passed to a compiled Go library.

        :param input_array: Array in which a pointer will be generated for
        :param c_type: The corresponding ctypes type for input_array
        :return: A pointer pointing to input_array

        """

        input_array_copy = input_array.astype(c_type)
        ptr = input_array_copy.ctypes.data_as(ctypes.POINTER(c_type))
        return ptr

    @staticmethod
    def generate_output_pointer(output_array_length, c_type):
        """

        Generate an array and a pointer to that array for a Go library to write to.

        :param output_array_length: Length of the output array
        :param c_type: The corresponding ctypes type for the output array
        :return: A pointer pointing to output_array, and output array itself

        """

        output_array = np.array([0] * output_array_length)
        output_array_copy = output_array.astype(c_type)
        ptr = output_array_copy.ctypes.data_as(ctypes.POINTER(c_type))
        return ptr, output_array_copy

    @staticmethod
    def generate_input_output_pointer(input_array, c_type):
        """

        Generate an array and a pointer to that array for a Go library to write to that is equal to an existing array.
        This is useful if you want to modify an array instead of creating a new one.

        :param input_array: Array in which a pointer will be generated for
        :param c_type: The corresponding ctypes type for the output array
        :return: A pointer pointing to output_array, and output array itself

        """

        output_array = array.array(Libraries.ctypes_dict[c_type], input_array)
        output_array_pointer = (c_type * len(output_array)).from_buffer(output_array)
        return output_array_pointer, output_array


if __name__ == "__main__":
    library = Libraries()
