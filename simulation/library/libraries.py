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

            self.perlin_noise_library = ctypes.cdll.LoadLibrary(f"{self.go_directory}/perlin_noise.so")

            self.perlin_noise_library.generatePerlinNoise.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_float,
                ctypes.c_uint32,
                ctypes.c_float,
                ctypes.c_float,
                ctypes.c_float,
                ctypes.c_uint32
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
    def generate_output_pointer(output_array_length: int, c_type):
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
