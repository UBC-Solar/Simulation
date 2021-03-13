import functools
import numpy as np
import time as timer
from datetime import datetime

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

      
# add acceleration (for constant acceleration)
def add_acceleration(input_array, acceleration):

    # change type int to float
    input_array = input_array.astype(float)

    # identify points where speed changes
    array_diff = np.diff(input_array)

    # get a list of index at where speed changes
    array_index = np.where(array_diff != 0)

    # acceleration per second
    acceleration = acceleration / 3600

    for i in array_index[0]:
        # check if accelerate or decelerate
        if array_diff[i] > 0:
            while input_array[i] < input_array[i + 1] and i + 1 < len(input_array) - 1:
                input_array[i + 1] = input_array[i] + acceleration
                i += 1

        else:
            while input_array[i] > input_array[i + 1] and i + 1 < len(input_array) - 1:
                input_array[i + 1] = input_array[i] - acceleration
                i += 1

    return input_array
    pass
  
  
def hour_from_unix_timestamp(unix_timestamp):
    val = datetime.utcfromtimestamp(unix_timestamp)
    return val.hour


def adjust_timestamps_to_local_times(timestamps, starting_drive_time, time_zones):
    """
    Takes in the timestamps of the vehicle's driving duration, starting drive time, and a list of time zones,
        returns the local times at each point

    :param timestamps: (int[N]) timestamps starting from 0, in seconds
    :param starting_drive_time: (int[N]) local time that the car was start to be driven in UNIX time (Daylight Saving included)
    :param time_zones: (int[N])
    """

    return np.array(timestamps + starting_drive_time - (time_zones[0] - time_zones), dtype=np.uint64)


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


if __name__ == '__main__':
    # speed_array input
    speed_array = np.array([45, 87, 65, 89, 43, 54, 45, 23, 34, 20])

    expanded_speed_array = reshape_and_repeat(speed_array, 9 * 3600)
    expanded_speed_array = np.insert(expanded_speed_array, 0, 0)
    expanded_speed_array = add_acceleration(expanded_speed_array, 20)
    print(expanded_speed_array)

    pass
