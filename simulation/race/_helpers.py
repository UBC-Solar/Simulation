import math
import numpy as np
from numba import jit
from simulation.race import Race


def _reshape_and_repeat(input_array, reshape_length):
    """

    Reshape and repeat an input array to have a certain length while maintaining its elements.
    Examples:
        If you want a constant speed for the entire simulation, insert a single element
        into the input_speed array.

            input_speed = np.array([30]) <-- constant speed of 30km/h

        If you want 50km/h in the first half of the simulation and 60km/h in the second half,
        do the following:

            input_speed = np.array([50, 60])

        This logic will apply for all subsequent array lengths (3, 4, 5, etc.)
    Keep in mind, however, that the condition len(input_array) <= reshape_length must be true

    :param np.ndarray input_array: array to be modified
    :param float reshape_length: length for input array to be modified to
    :return: modified array
    :rtype: np.ndarray

    """

    if input_array.size >= reshape_length:
        return input_array
    else:
        quotient_remainder_tuple = divmod(reshape_length, input_array.size)
        temp = np.repeat(input_array, quotient_remainder_tuple[0])
        result = np.append(temp, np.repeat(temp[-1], quotient_remainder_tuple[1]))

        return result


def _apply_deceleration(input_speed_array, tick, max_deceleration: float):
    """

    Remove sudden drops in speed from input_speed_array

    The modified input_speed_array stays as close to the target speeds_directory as possible such that:
        1. The decrease between any two consecutive speed values cannot exceed max_deceleration_per_tick km/h
        2. Values of 0km/h remain 0km/h

    :param np.ndarray input_speed_array: array to be modified
    :param int tick: time interval between each value in input_speed_array
    :param float max_deceleration: the maximum allowed deceleration in m/s^2
    :return: modified array
    :rtype: np.ndarray

    """
    max_deceleration_per_tick = max_deceleration * tick

    if input_speed_array is None:
        return np.array([])

    # start at the second to last element since the last element can be any speed
    for i in range(len(input_speed_array) - 2, 0, -1):
        # if the car wants to decelerate more than it can, maximize deceleration
        if input_speed_array[i] - input_speed_array[i + 1] > max_deceleration_per_tick:
            input_speed_array[i] = input_speed_array[i + 1] + max_deceleration_per_tick

    return input_speed_array


def _apply_acceleration(input_speed_array, tick, max_acceleration: float):
    """

    Remove sudden increases in speed from input_speed_array

    The modified input_speed_array stays as close to the target speeds_directory as possible such that:
        1. The increase between any two consecutive speed values cannot exceed max_acceleration_per_tick km/h
        2. Values of 0km/h remain 0km/h
        3. The first element cannot exceed MAX_ACCELERATION km/h since the car starts at rest

    :param np.ndarray input_speed_array: array to be modified
    :param int tick: time interval between each value in input_speed_array
    :param float max_acceleration: the maximum allowed acceleration in m/s^2
    :return: modified array
    :rtype: np.ndarray

    """
    max_acceleration_per_tick = max_acceleration * tick

    if input_speed_array is None:
        return np.array([])

    for i in range(0, len(input_speed_array)):
        # prevent the car from starting the race at an unattainable speed
        if i == 0 and input_speed_array[i] > max_acceleration_per_tick:
            input_speed_array[i] = max_acceleration_per_tick

        # if the car wants to accelerate more than it can, maximize acceleration
        elif (
            input_speed_array[i] - input_speed_array[i - 1] > max_acceleration_per_tick
        ):
            input_speed_array[i] = input_speed_array[i - 1] + max_acceleration_per_tick

    return input_speed_array


def get_granularity_reduced_boolean(
    boolean: np.ndarray, granularity: int | float
) -> np.ndarray:
    """
    Reduce a boolean where each element represented one second by agglomerating blocks of
    elements into a single element where the result will be False if there are any False
    values in the block; block size is dependent on granularity where a granularity of 1
    will result in a block size of 3600 (1 hour).


    :param boolean:
    :param granularity:
    :return:
    """
    inverse_granularity = int(
        3600 / granularity
    )  # Number of seconds. Granularity of 1 should mean 1 per hour
    duration = len(boolean)
    reduced_duration = math.ceil(duration / inverse_granularity)
    reduced_boolean = np.empty(reduced_duration, dtype=bool)

    i = 0
    n = 0

    while i < len(boolean):
        j = i + inverse_granularity
        truth_value = any(~boolean[i:j].astype(bool))
        reduced_boolean[n] = truth_value

        n += 1
        i = j

    return ~reduced_boolean


def reshape_speed_array(
    race: Race,
    speed,
    start_time: int,
    gis_object,
    tick=1,
    max_acceleration: float = 6,
    max_deceleration: float = 6
):
    """

    Modify the speed array to reflect:
        - race regulations
        - race length
        - reasonable acceleration
        - reasonable deceleration
        - tick length (time interval between speed array values in seconds)

    :param Race race: Race object containing the timing configuration
    :param np.ndarray speed: A NumPy array representing the average speed at each lap in km/h
    :param int start_time: time since start of the race that simulation is beginning
    :param GIS gis_object: GIS object that has access to the calculate_driving_speeds method
    :param int tick: The time interval in seconds between each speed in the speed array
    :param float max_acceleration: the maximum allowed acceleration in m/s^2
    :param float max_deceleration: the maximum allowed deceleration in m/s^2
    :return: A modified speed array which reflects race constraints and the car's acceleration/deceleration
    :rtype: np.ndarray

    """
    # Boolean array that tells us whether we are allowed to drive at each tick
    driving_allowed = race.driving_boolean.astype(int)[start_time::tick]

    # Transforming speed array units from km/hr to m/s
    lap_speeds_ms = np.array(speed) * (1000/3600)
    
    # Idle time for 0m/s entries
    idle_time = int((5*60)/tick) # ticks of idle time; for now this is set to be equivalent to 5 minutes

    # Get a speed array where each entry is the speed at each time step
    speed_ms = gis_object.calculate_driving_speeds(
        lap_speeds_ms,
        tick,
        driving_allowed,
        idle_time
    )
    
    speed_kmh = np.array(speed_ms) * (3600/1000) # Transform back to km/hr

    speed_smoothed_kmh = _apply_deceleration(
        _apply_acceleration(speed_kmh, tick, max_acceleration),
        tick,
        max_deceleration,
    )

    return speed_smoothed_kmh


def adjust_timestamps_to_local_times(timestamps, starting_drive_time, time_zones):
    """

    Takes in the timestamps of the vehicle's driving duration, starting drive time, and a list of time zones,
    returns the local times at each point

    :param np.ndarray timestamps: (int[N]) timestamps starting from 0, in seconds
    :param float starting_drive_time: (int[N]) local time that the car was start to be driven in UNIX time (Daylight Saving included)
    :param np.ndarray time_zones: (int[N])
    :returns: array of local times at each point
    :rtype: np.ndarray

    """

    return np.array(
        timestamps + starting_drive_time - (time_zones[0] - time_zones), dtype=np.uint64
    )


@jit(nopython=True)
def get_array_directional_wind_speed(vehicle_bearings, wind_speeds, wind_directions):
    """

    Returns the array of wind speed in m/s, in the direction opposite to the
        bearing of the vehicle

    :param np.ndarray vehicle_bearings: (float[N]) The azimuth angles that the vehicle in, in degrees
    :param np.ndarray wind_speeds: (float[N]) The absolute speeds_directory in m/s
    :param np.ndarray wind_directions: (float[N]) The wind direction in the meteorological convention. To convert from meteorological convention to azimuth angle, use (x + 180) % 360
    :returns: The wind speeds_directory in the direction opposite to the bearing of the vehicle
    :rtype: np.ndarray

    """

    # wind direction is 90 degrees meteorological, so it is 270 degrees azimuthal. car is 90 degrees
    #   cos(90 - 90) = cos(0) = 1. Wind speed is moving opposite to the car,
    # car is 270 degrees, cos(90-270) = -1. Wind speed is in direction of the car.
    return wind_speeds * (np.cos(np.radians(wind_directions - vehicle_bearings)))


@jit(nopython=True)
def calculate_completion_index(path_length, cumulative_distances):
    """

    This function identifies the index of cumulative_distances where the route has been completed.
    Indexing timestamps with the result of this function will return the time taken to complete the race.

    This problem, although framed in the context of the Simulation, is just to find the array position of the first
    value that is greater or equal to a target value

    :param float path_length: The length of the path the vehicle travels on
    :param np.ndarray cumulative_distances: A NumPy array representing the cumulative distanced travelled by the vehicle

    Pre-Conditions:
        path_length and cumulative_distances may be in any length unit, but they must share the same length unit

    :returns: First index of cumulative_distances where the route has been completed
    :rtype: int

    """

    # Identify the first index which the vehicle has completed the route
    completion_index = np.where(cumulative_distances >= path_length)[0][0]

    return completion_index


@jit(nopython=True)
def _map_array_to_targets(input_array, target_array):
    """

    Will map an array of values to the non-zero elements (a target) of targets_array.
    The assertion that len(input_array) and # of targets must match.

    Examples:
        If input array is [9, 6, 12] and target_array is [0, 1, 1, 0, 1], the output
    would be [0, 9, 6, 0, 12].
        If input array is [7, 4, 3, 1] and target_array is [0, 1, 0, 1, 1], then the assertion will
    fail as there are four elements in input_array and three targets in target_array, thus an error
    will be raised.

    :param input_array: array of values that will be mapped to the boolean array
    :param target_array: a boolean array of zero and non-zero values
    :returns: a new array consisting of the elements of input_array, mapped to the targets values of target_array.
    :rtype: np.ndarray

    """

    if target_array.sum() != len(input_array):
        raise AssertionError(
            "Number of targets and length of input_array do not match."
        )

    output_array = np.zeros(len(target_array), dtype=float)
    i = 0

    for value in input_array:
        while target_array[i] == 0:
            i += 1
        output_array[i] = value
        i += 1

    return output_array


@jit(nopython=True)
def get_map_data_indices(closest_gis_indices):
    """
    gets list of indices of the data to be displayed on corresponding
    coordinates of the client side map

    :param closest_gis_indices: a list of indices of the closest gis coordinate
                                at each tick
    """
    map_data_indices = [0]
    for i in range(len(closest_gis_indices)):
        if i == 0:
            continue
        else:
            if not closest_gis_indices[i] == closest_gis_indices[i - 1]:
                map_data_indices.append(i)
    return map_data_indices


@jit(nopython=True)
def normalize(
    input_array: np.ndarray, max_value: float = None, min_value: float = None
) -> np.ndarray:
    max_value_in_array = np.max(input_array) if max_value is None else max_value
    min_value_in_array = np.min(input_array) if min_value is None else min_value
    return (input_array - min_value_in_array) / (
        max_value_in_array - min_value_in_array
    )


@jit(nopython=True)
def denormalize(
    input_array: np.ndarray, max_value: float, min_value: float = 0
) -> np.ndarray:
    return input_array * (max_value - min_value) + min_value


@jit(nopython=True)
def rescale(input_array: np.ndarray, upper_bound: float, lower_bound: float = 0):
    normalized_array = normalize(input_array)
    return denormalize(normalized_array, upper_bound, lower_bound)
