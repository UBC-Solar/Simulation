import functools
import numpy as np
import time as timer
import datetime
import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd

from _datetime import datetime
from _datetime import date

from matplotlib import pyplot as plt
from numba import jit, njit

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


def checkForNonConsecutiveZeros(array, verbose=False):
    zeroed_indices = np.where(array == 0)[0]

    if len(zeroed_indices) == 0:
        if verbose:
            print("No zeroes found in the array!")
        return -1

    zeroed_indices_diff = np.diff(zeroed_indices)

    if np.max(zeroed_indices_diff) == 1 and np.min(zeroed_indices_diff) == 1:
        if verbose:
            print("Only consecutive zeroes found!")
        return False
    else:
        if verbose:
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
                # print("i'm stuck in this if while loop")
                input_array[i + 1] = input_array[i] + acceleration
                i += 1

        else:
            while input_array[i] > input_array[i + 1] and i + 1 < len(input_array) - 1:
                # print("i'm stuck in this else while loop")
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


def compute_elevation_angle_math(declination_angle, hour_angle, latitude):
    """
    Gets the two terms to calculate and return elevation angle, given the
    declination angle, hour angle, and latitude.

    This method separates the math part of the calculation from its caller
    method to optimize for numba compilation.

    declination_angle: The declination angle of the Earth relative to the Sun
    hour_angle: The hour angle of the sun in the sky

    Returns: The elevation angle in degrees
    """
    term_1 = np.sin(np.radians(declination_angle)) * \
             np.sin(np.radians(latitude))

    term_2 = np.cos(np.radians(declination_angle)) * \
             np.cos(np.radians(latitude)) * \
             np.cos(np.radians(hour_angle))

    elevation_angle = np.arcsin(term_1 + term_2)
    return np.degrees(elevation_angle)


def find_runs(x):
    """
    Method to identify runs of consecutive items in NumPy array
    Based on code from: user alimanfoo on https://gist.github.com/alimanfoo/c5977e87111abe8127453b21204c1065

    :returns a tuple of 3 NumPy arrays for (run_values, run_starts, run_lengths)
    Args:
        x: a 1D NumPy array3
    Throws: ValueError if array dimension is greater than 1

    Returns: a tuple of 3 NumPy arrays for (run_values, run_starts, run_lengths)
    """
    x = np.asanyarray(x)
    if x.ndim != 1:
        raise ValueError('only 1D array supported')
    n = x.shape[0]

    # handle empty array
    if n == 0:
        return np.array([]), np.array([]), np.array([])
    else:
        loc_run_start = np.empty(n, dtype=bool)
        loc_run_start[0] = True
        np.not_equal(x[:-1], x[1:], out=loc_run_start[1:])
        run_starts = np.nonzero(loc_run_start)[0]

        run_values = x[loc_run_start]

        run_lengths = np.diff(np.append(run_starts, n))

        return run_values, run_starts, run_lengths


def route_visualization(coords, elevation, speed, distances, state_of_charge, solar_irradiances,
                        cloud_cover, wind_speeds, visible=True):
    """
    Takes in a list of coordinates and translates those points into a visualizable
    route using GeoPanda Library. It labels the starting point and draws a line
    connecting all the coordinate points

    :Param coords: A NumPy array [n][latitude, longitude]

    Outputs a window that visualizes the route with given coordinates
    """
    points = []
    lat = []
    lon = []
    num = len(coords)
    i = 0
    while i < num:
        points.append("Point " + str(i))
        lat.append(coords[i][0])
        lon.append(coords[i][1])
        i += 1

    
    dataframe = pd.DataFrame(list(zip(points, lat, lon, elevation, speed, distances, state_of_charge, solar_irradiances, cloud_cover, wind_speeds)),
                            columns=["Point", "Latitude", "Longitude", "Elevation", "Speed kmh", "Distance", 
                            "State of Charge", "Solar Irradiance", "Cloud Coverage", "Wind Speeds"])

    fig = px.line_mapbox(dataframe, lat="Latitude", lon="Longitude", hover_name=points, hover_data=["Elevation", "Speed kmh", "Distance", 
                            "State of Charge", "Solar Irradiance", "Cloud Coverage", "Wind Speeds"], zoom=3, height=800)

    fig.update_layout(mapbox_style="stamen-terrain", mapbox_zoom=5, mapbox_center_lat = 41,
    margin={"r":0,"t":0,"l":0,"b":0})

    # shows the plotted points and line
    if visible:
        fig.show()



if __name__ == '__main__':
    # speed_array input
    speed_array = np.array([45, 87, 65, 89, 43, 54, 45, 23, 34, 20])

    expanded_speed_array = reshape_and_repeat(speed_array, 9 * 3600)
    expanded_speed_array = np.insert(expanded_speed_array, 0, 0)
    expanded_speed_array = add_acceleration(expanded_speed_array, 20)
    print(expanded_speed_array)
