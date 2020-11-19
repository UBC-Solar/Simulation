import functools
import numpy as np
import time as timer
from datetime import datetime
from simulation.common import constants

"""
Description: contains the simulation's helper functions.
"""


def timeit(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        print(f">>> Running {func.__name__!r}... \n")
        start = timer.perf_counter()
        value = func(*args, **kwargs)
        stop = timer.perf_counter()
        run_time = stop - start
        print(f"Finished {func.__name__!r} in {run_time:.3f}s. \n")
        return value

    return wrapper_timer


def date_from_unix_timestamp(unix_timestamp):
    return datetime.utcfromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')


def checkForNonConsecutiveZeros(array):
    zeroed_indices = np.where(array == 0)[0]

    if len(zeroed_indices) == 0:
        print("No zeroes found in the array!")
        return -1

    zeroed_indices_diff = np.diff(zeroed_indices)

    if np.max(zeroed_indices_diff) == 1 and np.min(zeroed_indices_diff) == 1:
        print("Only consecutive zeroes found!")
        return False
    else:
        print("Non-consecutive zeroes found!")
        return True


def reshape_and_repeat(input_array, reshape_length):
    if input_array.size >= reshape_length:
        print(f"Input array of shape {input_array.shape} was not reshaped\n")
        return input_array
    else:
        quotient_remainder_tuple = divmod(reshape_length, input_array.size)
        temp = np.repeat(input_array, quotient_remainder_tuple[0])
        result = np.append(temp, np.repeat(temp[-1], quotient_remainder_tuple[1]))

        print(f"Reshaped input array from {input_array.shape} to {result.shape}\n")
        return result


def hour_from_unix_timestamp(unix_timestamp):
    val = datetime.utcfromtimestamp(unix_timestamp)
    return val.hour


def calculate_path_distances(coords):
    """
    The coordinates are spaced quite tightly together, and they capture the
    features of the road. So, the lines between every pair of adjacent
    coordinates can be treated like a straight line, and the distances can
    thus be obtained.

    :param coords: A NumPy array [n][latitude, longitude]

    :returns path_distances: a NumPy array [n-1][distances],
    """

    offset = np.roll(coords, (1, 1))

    # get the latitude and longitude differences, in radians
    diff = (coords - offset)[1:] * np.pi / 180
    diff_lat, diff_lng = np.split(diff, 2, axis=1)
    diff_lat = np.squeeze(diff_lat)
    diff_lng = np.squeeze(diff_lng)

    # get the mean latitude for every latitude, in radians
    mean_lat = ((coords + offset)[1:, 0] * np.pi / 180) / 2
    cosine_mean_lat = np.cos(mean_lat)

    # multiply the latitude difference with the cosine_mean_latitude
    diff_lng_adjusted = cosine_mean_lat * diff_lng

    # square, sum and square-root
    square_lat = np.square(diff_lat)
    square_lng = np.square(diff_lng_adjusted)
    square_sum = square_lat + square_lng

    path_distances = constants.EARTH_RADIUS * np.sqrt(square_sum)

    return path_distances
