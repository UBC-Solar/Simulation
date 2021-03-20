import functools
import numpy as np
import time as timer
import datetime
from _datetime import datetime
from _datetime import date

from numba import jit

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


def add_acceleration(input_array, acceleration):
    """
    Takes in the speed array with sudden speed changes and an acceleration scalar,
    return a speed array with constant acceleration / deceleration
    :param input_array: (int[N]) input speed array (km/h)
    :param acceleration: (int) acceleration (km/h^2)
    :return:speed array with acceleration (int[N])
    """
    input_array = input_array.astype(float)
    array_diff = np.diff(input_array)
    array_index = np.where(array_diff != 0)

    # acceleration per second (kmh/s)
    acceleration = abs(acceleration) / 3600

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

def get_array_directional_wind_speed(vehicle_bearings, wind_speeds, wind_directions):
    """
    Returns the array of wind speed in m/s, in the direction opposite to the
        bearing of the vehicle

    vehicle_bearings: (float[N]) The azimuth angles that the vehicle in, in degrees
    wind_speeds: (float[N]) The absolute speeds in m/s
    wind_directions: (float[N]) The wind direction in the meteorlogical convention. To convert from
        meteorlogical convention to azimuth angle, use (x + 180) % 360

    Returns: The wind speeds in the direction opposite to the bearing of the vehicle
    """

    # wind direction is 90 degrees meteorlogical, so it is 270 degrees azimuthal. car is 90 degrees
    #   cos(90 - 90) = cos(0) = 1. Wind speed is moving opposite to the car,
    # car is 270 degrees, cos(90-270) = -1. Wind speed is in direction of the car.
    return wind_speeds * (np.cos(np.radians(wind_directions - vehicle_bearings)))


def get_day_of_year(day, month, year):
    """
        Calculates the day of the year, given the day, month and year.

        day, month, year: self explanatory
        """

    return (date(year, month, day) -
            date(year, 1, 1)).days + 1


@jit
def calculate_declination_angle(day_of_year):
    """
    Calculates the Declination Angle of the Earth at a given day
    https://www.pveducation.org/pvcdrom/properties-of-sunlight/declination-angle

    day_of_year: The number of the day of the current year, with January 1
        being the first day of the year.

    Returns: The declination angle of the Earth relative to the Sun, in
        degrees
    """

    declination_angle = -23.45 * np.cos(np.radians((np.float_(360) / 365) *
                                                       (day_of_year + 10)))

    return declination_angle


# ----- Calculation of Apparent Solar Time -----
@jit
def calculate_eot_correction(day_of_year):
    """
    Approximates and returns the correction factor between the apparent
    solar time and the mean solar time

    day_of_year: The number of the day of the current year, with January 1
        being the first day of the year.

    Returns: The Equation of Time correction EoT in minutes, where
        Apparent Solar Time = Mean Solar Time + EoT
    """

    b = np.radians((np.float_(360) / 364) * (day_of_year - 81))

    eot = 9.87 * np.sin(2 * b) - 7.83 * np.cos(b) - 1.5 * np.sin(b)

    return eot


def calculate_LSTM(time_zone_utc):
    """
    Calculates and returns the LSTM, or Local Solar Time Meridian.
    https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time

    time_zone_utc: The UTC time zone of your area in hours of UTC offset.

    Returns: The Local Solar Time Meridian in degrees
    """

    return 15 * time_zone_utc


def local_time_to_apparent_solar_time(time_zone_utc, day_of_year, local_time,
                                      longitude):
    """
    Converts between the local time to the apparent solar time and returns the apparent
    solar time.
    https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time

    time_zone_utc: The UTC time zone of your area in hours of UTC offset.
    day_of_year: The number of the day of the current year, with January 1
        being the first day of the year.
    local_time: The local time in hours from midnight (Adjust for Daylight Savings)
    longitude: The longitude of a location on Earth

    note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
            calculation will end up just the same

    Returns: The Apparent Solar Time of a location, in hours from midnight
    """

    lstm = calculate_LSTM(time_zone_utc)
    eot = calculate_eot_correction(day_of_year)

    # local solar time
    lst = local_time + np.float_(longitude - lstm) / 15 + np.float_(eot) / 60

    return lst


def calculate_path_gradients(elevations, distances):
    """
    Get the approximate gradients of every point on the path.

    :param elevations: [N][elevations]
    :param distances: [N-1][distances]

    :returns gradients: [N-1][gradients]

    Note:
        - gradient > 0 corresponds to uphill
        - gradient < 0 corresponds to downhill
    """

    # subtract every next elevation with the previous elevation to
    # get the difference in elevation
    # [1 2 3 4 5]
    # [5 1 2 3 4] -
    # -------------
    #   [1 1 1 1]

    offset = np.roll(elevations, 1)
    delta_elevations = (elevations - offset)[1:]

    # Divide the difference in elevation to get the gradient
    # gradient > 0: uphill
    # gradient < 0: downhill

    gradients = delta_elevations / distances

    return gradients


def cull_dataset(coords):
    """
    As we currently have a limited number of API calls(60) every minute with the
        current Weather API, we must shrink the dataset significantly. As the
        OpenWeatherAPI models have a resolution of between 2.5 - 70 km, we will
        go for a resolution of 25km. Assuming we travel at 100km/h for 12 hours,
        1200 kilometres/25 = 48 API calls

    As the Google Maps API has a resolution of around 40m between points,
        we must cull at 625:1 (because 25,000m / 40m = 625)
    """

    return coords[::625]


if __name__ == '__main__':
    # speed_array input
    speed_array = np.array([45, 87, 65, 89, 43, 54, 45, 23, 34, 20])

    expanded_speed_array = reshape_and_repeat(speed_array, 9 * 3600)
    expanded_speed_array = np.insert(expanded_speed_array, 0, 0)
    expanded_speed_array = add_acceleration(expanded_speed_array, 20)
    print(expanded_speed_array)

    pass
