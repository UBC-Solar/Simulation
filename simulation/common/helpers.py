import datetime
import functools
import math
import os
import pathlib

import numpy as np
import pandas as pd
import plotly.express as px
import time as timer

from typing import Union
from bokeh.layouts import gridplot
from bokeh.models import HoverTool
from bokeh.plotting import figure, show, output_file
from cffi.backend_ctypes import long
from matplotlib import pyplot as plt
from numba import jit
from simulation.common import BrightSide
from simulation.common.race import Race
from haversine import haversine, Unit


"""
Description: contains the simulation's helper functions.
"""


def timeit(func):
    """

    Apply this decorator to functions in order to time and print how long they take to execute.

    :param func: function to be timed

    """

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
    """

    Return a stringified UTC datetime from UNIX timestamped.

    :param int unix_timestamp: A unix timestamp

    :returns: A string of the UTC representation of the UNIX timestamp in the format Y-m-d H:M:S
    :rtype: str

    """

    return datetime.datetime.utcfromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')


@jit(nopython=True)
def check_for_non_consecutive_zeros(array, verbose=False):
    """

    Checks if an array has non-consecutive zeroes as elements.

    :param np.ndarray array: array to be examined
    :param bool verbose: whether method should be verbose
    :return: whether the array has non-consecutive zeroes
    :rtype: bool

    """

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
        result = np.append(temp, np.repeat(
            temp[-1], quotient_remainder_tuple[1]))

        return result


def apply_deceleration(input_speed_array, tick):
    """

    Remove sudden drops in speed from input_speed_array

    The modified input_speed_array stays as close to the target speeds as possible such that:
        1. The decrease between any two consecutive speed values cannot exceed max_deceleration_per_tick km/h
        2. Values of 0km/h remain 0km/h

    :param np.ndarray input_speed_array: array to be modified
    :param int tick: time interval between each value in input_speed_array
    :return: modified array
    :rtype: np.ndarray

    """
    max_deceleration_per_tick = BrightSide.max_deceleration_kmh_per_s*tick

    if input_speed_array is None:
        return np.array([])

    # start at the second to last element since the last element can be any speed
    for i in range(len(input_speed_array) - 2, 0, -1):

        # if the car wants to decelerate more than it can, maximize deceleration
        if input_speed_array[i] - input_speed_array[i + 1] > max_deceleration_per_tick:
            input_speed_array[i] = input_speed_array[i + 1] + max_deceleration_per_tick

    return input_speed_array


def apply_acceleration(input_speed_array, tick):
    """

    Remove sudden increases in speed from input_speed_array

    The modified input_speed_array stays as close to the target speeds as possible such that:
        1. The increase between any two consecutive speed values cannot exceed max_acceleration_per_tick km/h
        2. Values of 0km/h remain 0km/h
        3. The first element cannot exceed MAX_ACCELERATION km/h since the car starts at rest

    :param np.ndarray input_speed_array: array to be modified
    :param int tick: time interval between each value in input_speed_array
    :return: modified array
    :rtype: np.ndarray

    """
    max_acceleration_per_tick = BrightSide.max_acceleration_kmh_per_s*tick

    if input_speed_array is None:
        return np.array([])

    for i in range(0, len(input_speed_array)):

        # prevent the car from starting the race at an unattainable speed
        if i == 0 and input_speed_array[i] > max_acceleration_per_tick:
            input_speed_array[i] = max_acceleration_per_tick

        # if the car wants to accelerate more than it can, maximize acceleration
        elif input_speed_array[i] - input_speed_array[i - 1] > max_acceleration_per_tick:
            input_speed_array[i] = input_speed_array[i - 1] + max_acceleration_per_tick

    return input_speed_array


def get_granularity_reduced_boolean(boolean: np.ndarray, granularity: int | float) -> np.ndarray:
    """
    Reduce a boolean where each element represented one second by agglomerating blocks of
    elements into a single element where the result will be False if there are any False
    values in the block; block size is dependent on granularity where a granularity of 1
    will result in a block size of 3600 (1 hour).


    :param boolean:
    :param granularity:
    :return:
    """
    inverse_granularity = int(3600 / granularity)  # Number of seconds. Granularity of 1 should mean 1 per hour
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


def reshape_speed_array(race: Race, speed, granularity, start_time: int, tick=1):
    """

    Modify the speed array to reflect:
        - race regulations
        - race length
        - reasonable acceleration
        - reasonable deceleration
        - tick length (time interval between speed array values in seconds)

    :param Race race: Race object containing the timing configuration
    :param np.ndarray speed: A NumPy array representing the speed at each timestamp in km/h
    :param float granularity: how granular the time divisions for Simulation's speed array should be,
                              where 1 is hourly and 0.5 is twice per hour.
    :param int start_time: time since start of the race that simulation is beginning
    :param int tick: The time interval in seconds between each speed in the speed array
    :return: A modified speed array which reflects race constraints and the car's acceleration/deceleration
    :rtype: np.ndarray

    """
    speed_boolean_array = race.driving_boolean.astype(int)[start_time:]

    speed_mapped = map_array_to_targets(speed, get_granularity_reduced_boolean(speed_boolean_array, granularity))

    reshaped_tick_count = math.ceil((race.race_duration - start_time) / float(tick))
    speed_mapped_per_tick = reshape_and_repeat(speed_mapped, reshaped_tick_count)
    speed_smoothed_kmh = apply_deceleration(apply_acceleration(speed_mapped_per_tick, tick), tick)

    return speed_smoothed_kmh


def hour_from_unix_timestamp(unix_timestamp):
    """

    Return the hour of a UNIX timestamp.

    :param float unix_timestamp: a UNIX timestamp
    :return: hour of UTC datetime from unix timestamp
    :rtype: int

    """

    val = datetime.datetime.utcfromtimestamp(unix_timestamp)
    return val.hour


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

    return np.array(timestamps + starting_drive_time - (time_zones[0] - time_zones), dtype=np.uint64)


def calculate_path_distances(coords):
    """

    Obtain the distance between each coordinate by approximating the spline between them
    as a straight line, and use the Haversine formula (https://en.wikipedia.org/wiki/Haversine_formula)
    to calculate distance between coordinates on a sphere.

    :param np.ndarray coords: A NumPy array [n][latitude, longitude]
    :returns path_distances: a NumPy array [n-1][distances],
    :rtype: np.ndarray

    """

    coords_offset = np.roll(coords, (1, 1))
    path_distances = []
    for u, v in zip(coords, coords_offset):
        path_distances.append(haversine(u, v, unit=Unit.METERS))

    return np.array(path_distances)


@jit(nopython=True)
def get_array_directional_wind_speed(vehicle_bearings, wind_speeds, wind_directions):
    """

    Returns the array of wind speed in m/s, in the direction opposite to the
        bearing of the vehicle

    :param np.ndarray vehicle_bearings: (float[N]) The azimuth angles that the vehicle in, in degrees
    :param np.ndarray wind_speeds: (float[N]) The absolute speeds in m/s
    :param np.ndarray wind_directions: (float[N]) The wind direction in the meteorlogical convention. To convert from meteorological convention to azimuth angle, use (x + 180) % 360
    :returns: The wind speeds in the direction opposite to the bearing of the vehicle
    :rtype: np.ndarray

    """

    # wind direction is 90 degrees meteorlogical, so it is 270 degrees azimuthal. car is 90 degrees
    #   cos(90 - 90) = cos(0) = 1. Wind speed is moving opposite to the car,
    # car is 270 degrees, cos(90-270) = -1. Wind speed is in direction of the car.
    return wind_speeds * (np.cos(np.radians(wind_directions - vehicle_bearings)))


def get_day_of_year_map(date):
    """

    Extracts day, month, year, from datetime object

    :param datetime.date date: date to be decomposed

    """
    return get_day_of_year(date.day, date.month, date.year)


def get_day_of_year(day, month, year):
    """

    Calculates the day of the year, given the day, month and year.
    Day refers to a number representing the nth day of the year. So, Jan 1st will be the 1st day of the year

    :param int day: nth day of the year
    :param int month: month
    :param int year: year
    :returns: day of year
    :rtype: int

    """

    return (datetime.date(year, month, day) - datetime.date(year, 1, 1)).days + 1


@jit(nopython=True)
def calculate_declination_angle(day_of_year):
    """

    Calculates the Declination Angle of the Earth at a given day
    https://www.pveducation.org/pvcdrom/properties-of-sunlight/declination-angle

    :param np.ndarray day_of_year: The number of the day of the current year, with January 1 being the first day of the year.
    :returns: The declination angle of the Earth relative to the Sun, in degrees
    :rtype: np.ndarray

    """

    declination_angle = -23.45 * np.cos(np.radians((np.float_(360) / 365) *
                                                   (day_of_year + 10)))

    return declination_angle


# ----- Calculation of Apparent Solar Time -----
@jit(nopython=True)
def calculate_eot_correction(day_of_year):
    """

    Approximates and returns the correction factor between the apparent
    solar time and the mean solar time

    :param np.ndarray day_of_year: The number of the day of the current year, with January 1 being the first day of the year.
    :returns: The Equation of Time correction EoT in minutes, where apparent Solar Time = Mean Solar Time + EoT
    :rtype: np.ndarray

    """

    b = np.radians((np.float_(360) / 364) * (day_of_year - 81))

    eot = 9.87 * np.sin(2 * b) - 7.83 * np.cos(b) - 1.5 * np.sin(b)

    return eot


@jit(nopython=True)
def calculate_LSTM(time_zone_utc):
    """

    Calculates and returns the LSTM, or Local Solar Time Meridian.
    https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time

    :param np.ndarray time_zone_utc: The UTC time zone of your area in hours of UTC offset.
    :returns: The Local Solar Time Meridian in degrees
    :rtype: np.ndarray

    """

    return 15 * time_zone_utc


def local_time_to_apparent_solar_time(time_zone_utc, day_of_year, local_time,
                                      longitude):
    """

    Converts between the local time to the apparent solar time and returns the apparent
    solar time.
    https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time

    Note: If local time and time_zone_utc are both unadjusted for Daylight Savings, the
        calculation will end up just the same

    :param np.ndarray time_zone_utc: The UTC time zone of your area in hours of UTC offset.
    :param np.ndarray day_of_year: The number of the day of the current year, with January 1 being the first day of the year.
    :param np.ndarray local_time: The local time in hours from midnight (Adjust for Daylight Savings)
    :param np.ndarray longitude: The longitude of a location on Earth
    :returns: The Apparent Solar Time of a location, in hours from midnight
    :rtype: np.ndarray

    """

    lstm = calculate_LSTM(time_zone_utc)
    eot = calculate_eot_correction(day_of_year)

    # local solar time
    lst = local_time + np.float_(longitude - lstm) / 15 + np.float_(eot) / 60

    return lst


def calculate_path_gradients(elevations, distances):
    """

    Get the approximate gradients of every point on the path.

    Note:
        - gradient > 0 corresponds to uphill
        - gradient < 0 corresponds to downhill

    :param np.ndarray elevations: [N][elevations]
    :param np.ndarray distances: [N-1][distances]
    :returns gradients: [N-1][gradients]
    :rtype: np.ndarray

    """

    # subtract every next elevation with the previous elevation to
    # get the difference in elevation
    # [1 2 3 4 5]
    # [5 1 2 3 4] -
    # -------------
    #   [1 1 1 1]

    offset = np.roll(elevations, 1)
    delta_elevations = elevations - offset

    # Divide the difference in elevation to get the gradient
    # gradient > 0: uphill
    # gradient < 0: downhill
    with np.errstate(invalid='ignore'):
        gradients = delta_elevations / distances

    return np.nan_to_num(gradients, nan=0.)


@jit(nopython=True)
def compute_elevation_angle_math(declination_angle, hour_angle, latitude):
    """

    Gets the two terms to calculate and return elevation angle, given the
    declination angle, hour angle, and latitude.

    This method separates the math part of the calculation from its caller
    method to optimize for numba compilation.

    :param np.ndarray latitude: array of latitudes
    :param np.ndarray declination_angle: The declination angle of the Earth relative to the Sun
    :param np.ndarray hour_angle: The hour angle of the sun in the sky
    :returns: The elevation angle in degrees
    :rtype: np.ndarray

    """

    term_1 = np.sin(np.radians(declination_angle)) * np.sin(np.radians(latitude))
    term_2 = np.cos(np.radians(declination_angle)) * np.cos(np.radians(latitude)) * np.cos(np.radians(hour_angle))
    elevation_angle = np.arcsin(term_1 + term_2)

    return np.degrees(elevation_angle)


def find_runs(x):
    """

    Method to identify runs of consecutive items in NumPy array
    Based on code from: user alimanfoo on https://gist.github.com/alimanfoo/c5977e87111abe8127453b21204c1065

    :returns a tuple of 3 NumPy arrays for (run_values, run_starts, run_lengths)
    :param x: a 1D NumPy array3
    :raises: ValueError if array dimension is greater than 1

    :returns: a tuple of 3 NumPy arrays for (run_values, run_starts, run_lengths)
    :rtype: tuple

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


def find_multi_index_runs(x):
    run_values, run_starts, run_lengths = find_runs(x)

    # Find where the run_lengths is greater than one
    multi_index_run_indices = np.where(run_lengths > 1)

    # Use these new indices to index the existing run_values, run_tarts, run_lengths.
    # This removes all the runs with length 1
    multi_index_run_starts = run_starts[multi_index_run_indices]
    multi_index_run_values = run_values[multi_index_run_indices]
    multi_index_run_lengths = run_lengths[multi_index_run_indices]

    return multi_index_run_values, multi_index_run_starts, multi_index_run_lengths


def plot_graph(timestamps, arrays_to_plot, array_labels, graph_title, save=True,
               plot_portion: tuple[float] = (0.0, 1.0)):
    """

    This is a utility function to plot out any set of NumPy arrays you pass into it using the Bokeh library.
    The precondition of this function is that the length of arrays_to_plot and array_labels are equal.

    This is because there be a 1:1 mapping of each entry of arrays_to_plot to array_labels such that:
        arrays_to_plot[n] has label array_labels[n]

    Result:
        Produces a 3 x ceil(len(arrays_to_plot) / 3) plot
        If save is enabled, save html file

    Another precondition of this function is that each of the arrays within arrays_to_plot also have the
    same length. This is each of them will share the same time axis.

    :param np.ndarray timestamps: An array of timestamps for the race
    :param list arrays_to_plot: An array of NumPy arrays to plot
    :param list array_labels: An array of strings for the individual plot titles
    :param str graph_title: A string that serves as the plot's main title
    :param bool save: Boolean flag to control whether to save an .html file
    :param plot_portion: tuple containing beginning and end of arrays that we want to plot as percentages which is
    useful if we only want to plot for example the second half of the race in which case we would input (0.5, 1.0).

    """

    if plot_portion != (0.0, 1.0):
        for index, array in enumerate(arrays_to_plot):
            beginning_index = int(len(array) * plot_portion[0])
            end_index = int(len(array) * plot_portion[1])
            arrays_to_plot[index] = array[beginning_index:end_index]

        beginning_index = int(len(timestamps) * plot_portion[0])
        end_index = int(len(timestamps) * plot_portion[1])
        timestamps = timestamps[beginning_index:end_index]

    compress_constant = max(int(timestamps.shape[0] / 5000), 1)

    for index, array in enumerate(arrays_to_plot):
        arrays_to_plot[index] = array[::compress_constant]

    figures = list()

    hover_tool = HoverTool()
    hover_tool.formatters = {"x": "datetime"}
    hover_tool.tooltips = [
        ("time", "$x"),
        ("data", "$y")
    ]

    for index, data_array in enumerate(arrays_to_plot):
        # create figures and put them in list
        figures.append(figure(title=array_labels[index], x_axis_label="Time (hr)",
                              y_axis_label=array_labels[index], x_axis_type="datetime"))

        # add line renderers to each figure
        colours = (
            '#EC1557', '#F05223', '#F6A91B', '#A5CD39', '#20B254', '#00AAAE', '#4998D3', '#892889', '#fa1b9a',
            '#F05223', '#EC1557', '#F05223', '#F6A91B', '#A5CD39', '#20B254', '#00AAAE', '#4998D3', '#892889',
            '#fa1b9a', '#F05223', '#EC1557', '#F05223', '#F6A91B', '#A5CD39', '#20B254', '#00AAAE', '#4998D3',
            '#892889', '#fa1b9a', '#F05223', '#EC1557', '#F05223', '#F6A91B', '#A5CD39', '#EC1557', '#F05223')
        figures[index].line(timestamps[::compress_constant] * 1000, data_array, line_color=colours[index],
                            line_width=2)

        figures[index].add_tools(hover_tool)

    grid = gridplot(figures, ncols=3, height=400, width=450)

    if save:
        filename = graph_title + '.html'
        filepath = pathlib.Path(os.path.abspath(__file__)).parent.parent.parent / "html"
        os.makedirs(filepath / "html", exist_ok=True)
        output_file(filename=str(filepath / filename), title=graph_title)

    show(grid)

    return


def route_visualization(coords, visible=True):
    """

    Takes in a list of coordinates and visualizes them using MapBox.
    Outputs a window that visualizes the route with given coordinates

    :param np.ndarray coords: A NumPy array [n][latitude, longitude]

    """

    point_labels = [f"Point {str(i)}" for i in range(len(coords))]
    colours = [0 for _ in coords]
    sizes = [6 for _ in coords]
    latitudes = [c[0] for c in coords]
    longitudes = [c[1] for c in coords]

    zipped_data = list(zip(point_labels, latitudes,
                           longitudes, colours, sizes))

    colour_hex = "#002145"
    solid_color_hex_continuous_scale = [colour_hex, colour_hex]

    dataframe = pd.DataFrame(zipped_data, columns=[
        "Point", "Latitude", "Longitude", "Colour", "Size"])

    fig = px.scatter_mapbox(dataframe, lat="Latitude", lon="Longitude", color="Colour",
                            hover_name=point_labels, color_continuous_scale=solid_color_hex_continuous_scale,
                            size="Size", size_max=6, zoom=3, height=800)

    fig.update_layout(mapbox_style="stamen-terrain", mapbox_zoom=5, mapbox_center_lat=41,
                      margin={"r": 0, "t": 0, "l": 0, "b": 0})

    if visible:
        fig.show()


def simple_plot_graph(data, title, visible=True):
    """

    Displays a graph of the data using Matplotlib

    :param bool visible: A control flag specifying if the plot should be shown
    :param np.ndarray data: A NumPy[n] array of data to plot
    :param str title: The graph title

    """
    fig, ax = plt.subplots()
    x = np.arange(0, len(data))
    ax.plot(x, data)
    plt.title(title)
    if visible:
        plt.show()


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


def plot_longitudes(coordinates):
    """

    Plots the longitudes of a set of coordinates. Meant to support Simulation development and verification of route data.

    :param np.ndarray coordinates: A NumPy array (float[N][longitude, latitude]) representing a path of coordinates
    :returns: Nothing, but plots the longitudes

    """
    simple_plot_graph(coordinates[:, 0], "Longitudes")


def plot_latitudes(coordinates):
    """

    Plots the latitudes of a set of coordinates. Meant to support Simulation development and verification of route data.

    :param np.ndarray coordinates: A NumPy array (float[N][longitude, latitude]) representing a path of coordinates
    :returns: Nothing, but plots the latitudes

    """

    simple_plot_graph(coordinates[:, 1], "Latitudes")


@jit(nopython=True)
def map_array_to_targets(input_array, target_array):
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
        raise AssertionError("Number of targets and length of input_array do not match.")

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


def PJWHash(key: Union[np.ndarray, list, set, str, tuple]) -> int:
    """
    Hashes a given `key` using the PJW hash function.
    See: https://en.wikipedia.org/wiki/PJW_hash_function

    This function is used to generate a hash to identify `Simulation` objects as representing the same situation, or not.

    Python implementation by Arash Partow - 2002:
    https://github.com/JamzyWang/HashCollector/blob/master/GeneralHashFunctions_Python/GeneralHashFunctions.py

    :param key: Sequence that will be hashed. Should be an iterable of values that can be added with integers.
    :return: Returns the generated hash
    :rtype: int

    """

    BitsInUnsignedInt = 4 * 8
    ThreeQuarters = long((BitsInUnsignedInt * 3) / 4)
    OneEighth = long(BitsInUnsignedInt / 8)
    HighBits = 0xFFFFFFFF << (BitsInUnsignedInt - OneEighth)
    Hash = 0
    Test = 0

    for i in range(len(key)):
        Hash = (Hash << OneEighth) + ord(key[i])
        Test = Hash & HighBits
        if Test != 0:
            Hash = ((Hash ^ (Test >> ThreeQuarters)) & (~HighBits))
    return Hash & 0x7FFFFFFF


def parse_coordinates_from_kml(coords_str: str) -> np.ndarray:
    """

    Parse a coordinates string from a XML (KML) file into a list of coordinates (2D vectors).
    Requires coordinates in the format "39.,41.,0  39.,40.,0" which will return [ [39., 41.], [39., 40.] ].

    :param coords_str: coordinates string from a XML (KML) file
    :return: list of 2D vectors representing coordinates
    :rtype: np.ndarray

    """

    def parse_coord(pair):
        coord = pair.split(',')
        coord.pop()
        coord = [float(value) for value in coord]
        return coord

    return list(map(parse_coord, coords_str.split()))


@jit(nopython=True)
def normalize(input_array: np.ndarray, max_value: float = None, min_value: float = None) -> np.ndarray:
    max_value_in_array = np.max(input_array) if max_value is None else max_value
    min_value_in_array = np.min(input_array) if min_value is None else min_value
    return (input_array - min_value_in_array) / (max_value_in_array - min_value_in_array)


@jit(nopython=True)
def denormalize(input_array: np.ndarray, max_value: float, min_value: float = 0) -> np.ndarray:
    return input_array * (max_value - min_value) + min_value


@jit(nopython=True)
def rescale(input_array: np.ndarray, upper_bound: float, lower_bound: float = 0):
    normalized_array = normalize(input_array)
    return denormalize(normalized_array, upper_bound, lower_bound)


if __name__ == '__main__':
    # speed_array input
    speed_array = np.array([45, 87, 65, 89, 43, 54, 45, 23, 34, 20])

    expanded_speed_array = reshape_and_repeat(speed_array, 9 * 3600)
    expanded_speed_array = np.insert(expanded_speed_array, 0, 0)
    expanded_speed_array = apply_deceleration(expanded_speed_array, 20)
