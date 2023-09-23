import datetime
import functools

import numpy as np
import pandas as pd
import plotly.express as px
import time as timer

from bokeh.layouts import gridplot
from bokeh.models import HoverTool
from bokeh.plotting import figure, show, output_file
from matplotlib import pyplot as plt
from simulation.common import constants

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


def generate_deceleration_array(initial_velocity, final_velocity, deceleration_interval):
    """

    Create an array where each element represents a step in the deceleration from initial_velocity to final_velocity.

    :param float initial_velocity: the velocity at which deceleration occurs for the first time (km/h)
    :param float final_velocity: the target velocity that is being decelerated to (km/h)
    :param int deceleration_interval: the time it will take to decelerate from initial velocity to final velocity (s)
    :return: an array of the velocities between initial_velocity and final_velocity
    :rtype: np.ndarray

    """

    deceleration_instance_size = (final_velocity - initial_velocity) / (deceleration_interval + 1)
    return np.arange(initial_velocity, final_velocity, deceleration_instance_size)[1:(deceleration_interval + 1)]


def apply_deceleration(input_speed_array, deceleration_interval):
    """

    Replace instances of instant deceleration in a velocity array with uniform changes in velocity that are spread
    over the deceleration_interval.

    The distance travelled by the simulation will be reduced by a negligible amount.

    :param np.ndarray input_speed_array: the velocity array (km/h)
    :param int deceleration_interval: the duration of the deceleration intervals (s)
    :return: a speed array with uniform deceleration (km/h)
    :rtype: np.ndarray

    """

    if input_speed_array is None:
        return np.array([])
    if deceleration_interval <= 0:
        return input_speed_array

    input_speed_array = input_speed_array.astype(float)
    # Prepending 0 to align acceleration_instances
    acceleration_instances = np.diff(input_speed_array, prepend=[0])
    # array with speed_array
    # [0] must be added because np.where returns an
    deceleration_instances = np.where(acceleration_instances < 0)[0]
    # array with only one element

    for idx in deceleration_instances:
        initial_velocity = input_speed_array[idx - 1]
        final_velocity = input_speed_array[idx]

        if is_valid_speed_array(deceleration_interval, idx, initial_velocity, input_speed_array):
            deceleration_array = generate_deceleration_array(
                initial_velocity, final_velocity, deceleration_interval)
            input_speed_array[idx -
                              deceleration_interval:idx] = deceleration_array
    return input_speed_array


def is_valid_speed_array(deceleration_interval, idx, initial_velocity, input_speed_array):
    """

    Check that the specified speed array is valid in relation to the chosen deceleration interval.

    :param int deceleration_interval: the duration of the deceleration intervals (s)
    :param int idx: the index used to check our deceleration interval
    :param float initial_velocity: the velocity at the beginning of the deceleration period
    :param np.ndarray input_speed_array: the speed array
    :return: True if the array is valid, False if it is not
    :rtype: bool

    """
    if deceleration_interval > len(input_speed_array) - 1:  # Check that the speed array isn't smaller than the
        # deceleration interval
        return False

    # Check that the speed is constant over the deceleration interval
    for i in range(0, deceleration_interval):
        if initial_velocity != input_speed_array[idx - i - 1]:
            return False
    return True


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

    The coordinates are spaced quite tightly together, and they capture the
    features of the road. So, the lines between every pair of adjacent
    coordinates can be treated like a straight line, and the distances can
    thus be obtained.

    :param np.ndarray coords: A NumPy array [n][latitude, longitude]
    :returns path_distances: a NumPy array [n-1][distances],
    :rtype: np.ndarray

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
    delta_elevations = (elevations - offset)[1:]

    # Divide the difference in elevation to get the gradient
    # gradient > 0: uphill
    # gradient < 0: downhill

    gradients = delta_elevations / distances

    return gradients


def cull_dataset(coords, cull_factor=625):  # DEPRECATED
    """

    As we currently have a limited number of API calls(60) every minute with the
        current Weather API, we must shrink the dataset significantly. As the
        OpenWeatherAPI models have a resolution of between 2.5 - 70 km, we will
        go for a resolution of 25km. Assuming we travel at 100km/h for 12 hours,
        1200 kilometres/25 = 48 API calls

    As the Google Maps API has a resolution of around 40m between points,
        we must cull at 625:1 (because 25,000m / 40m = 625)

    :param int cull_factor: factor in which the input array should be culled, default is 625.
    :param np.ndarray coords: array to be culled
    :returns: culled array
    :rtype: np.ndarray

    """
    return coords[::cull_factor]


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


def apply_race_timing_constraints(speed_kmh, start_hour, simulation_duration, race_type, timestamps, verbose):
    """

    Applies regulation timing constraints to a speed array.

    :param np.ndarray speed_kmh: A NumPy array representing the speed at each timestamp in km/h
    :param int start_hour: An integer representing the race's start hour
    :param int simulation_duration: An integer representing simulation duration in seconds
    :param str race_type: A string describing the race type. Must be one of "ASC" or "FSGP"
    :param np.ndarray timestamps: A NumPy array representing the timestamps for the simulated race
    :param bool verbose: A flag to show speed array modifications for debugging purposes
    :returns: constrained_speed_kmh, a speed array with race timing constraints applied to it, not_charging_array, a boolean array representing when the car can charge and when it cannot (1 = charge, 0 = not_charging_array)
    :rtype: np.ndarray
    :raises: ValueError is race_type is not one of "ASC" or "FSGP"

    """

    not_charging_array = get_race_timing_constraints_boolean(start_hour, simulation_duration, race_type)

    if verbose:
        plot_graph(timestamps=timestamps,
                   arrays_to_plot=[not_charging_array, speed_kmh],
                   array_labels=["not charge", "updated speed (km/h)"],
                   graph_title="not charge and speed")

    constrained_speed_kmh = np.logical_and(speed_kmh, not_charging_array) * speed_kmh

    return constrained_speed_kmh, not_charging_array


def get_race_timing_constraints_boolean(start_hour, simulation_duration, race_type, granularity, as_seconds=True):
    """

    Applies regulation timing constraints to a speed array.

    :param int start_hour: An integer representing the race's start hour
    :param int simulation_duration: An integer representing simulation duration in seconds
    :param str race_type: A string describing the race type. Must be one of "ASC" or "FSGP"
    :param bool as_seconds: will return an array of seconds, or hours if set to False
    :param float granularity: how granular the time divisions for Simulation's speed array should be, where 1 is hourly and 0.5 is twice per hour.
    :returns: driving_time_boolean, a boolean array with race timing constraints applied to it
    :rtype: np.ndarray
    :raises: ValueError is race_type is not one of "ASC" or "FSGP"

    """

    # (Charge from 7am-9am and 6pm-8pm) for ASC - 13 Hours of Race Day, 9 Hours of Driving
    # (Charge from 8am-9am and 6pm-8pm) for FSGP

    simulation_hours = np.arange(start_hour, start_hour + simulation_duration / (60 * 60), (1.0 / granularity))

    if as_seconds is True:
        simulation_hours_by_second = np.append(np.repeat(simulation_hours, 3600),
                                               start_hour + simulation_duration / (60 * 60)).astype(int)
        if race_type == "ASC":
            driving_time_boolean = [(simulation_hours_by_second % 24) <= 9, (simulation_hours_by_second % 24) >= 18]
        else:  # FSGP
            driving_time_boolean = [(simulation_hours_by_second % 24) <= 9, (simulation_hours_by_second % 24) >= 18]
    else:
        if race_type == "ASC":
            driving_time_boolean = [(simulation_hours % 24) <= 9, (simulation_hours % 24) >= 18]
        else:  # FSGP
            driving_time_boolean = [(simulation_hours % 24) <= 9, (simulation_hours % 24) >= 18]

    return np.invert(np.logical_or.reduce(driving_time_boolean))


def get_charge_timing_constraints_boolean(start_hour, simulation_duration, race_type, as_seconds=True):
    """

    Applies regulation timing constraints to an array representing when the car will be able to charge.

    :param int start_hour: An integer representing the race's start hour
    :param int simulation_duration: An integer representing simulation duration in seconds
    :param str race_type: A string describing the race type. Must be one of "ASC" or "FSGP"
    :param bool as_seconds: will return an array of seconds, or hours if set to False
    :returns: driving_time_boolean, a boolean array with charge timing constraints applied to it
    :rtype: np.ndarray
    :raises: ValueError is race_type is not one of "ASC" or "FSGP"

    """

    # (Charge from 7am-9am and 6pm-8pm) for ASC - 13 Hours of Race Day, 9 Hours of Driving
    # (Charge from 8am-9am and 6pm-8pm) for FSGP

    simulation_hours = np.arange(start_hour, start_hour + simulation_duration / (60 * 60))

    if as_seconds is True:
        simulation_hours_by_second = np.append(np.repeat(simulation_hours, 3600),
                                               start_hour + simulation_duration / (60 * 60)).astype(int)
        if race_type == "ASC":
            driving_time_boolean = [(simulation_hours_by_second % 24) <= 7, (simulation_hours_by_second % 24) >= 20]
        else:  # FSGP
            driving_time_boolean = [(simulation_hours_by_second % 24) <= 8, (simulation_hours_by_second % 24) >= 20]
    else:
        if race_type == "ASC":
            driving_time_boolean = [(simulation_hours % 24) <= 7, (simulation_hours % 24) >= 20]
        else:  # FSGP
            driving_time_boolean = [(simulation_hours % 24) <= 8, (simulation_hours % 24) >= 20]

    return np.invert(np.logical_or.reduce(driving_time_boolean))


def plot_graph(timestamps, arrays_to_plot, array_labels, graph_title, save=True):
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

    """

    compress_constant = int(timestamps.shape[0] / 5000)

    for index, array in enumerate(arrays_to_plot):
        arrays_to_plot[index] = array[::compress_constant]

    figures = list()

    hover_tool = HoverTool()
    hover_tool.formatters = {"x": "datetime"}
    hover_tool.tooltips = [
        ("time", "$x"),
        ("data", "$y")
    ]

    for (index, data_array) in enumerate(arrays_to_plot):
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

    grid = gridplot(figures, sizing_mode="scale_both",
                    ncols=3, plot_height=200, plot_width=300)

    if save:
        output_file(filename=graph_title + '.html', title=graph_title)

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


def calculate_race_completion_time(path_length, cumulative_distances):
    """

    This function uses the maximum path distance and cumulative distances travelled
    during the simulation to identify how long the car takes to finish travelling the route.

    This problem, although framed in the context of the Simulation, is just to find the array position of the first
    value that is greater or equal to a target value

    :param float path_length: The length of the path the vehicle travels on
    :param np.ndarray cumulative_distances: A NumPy array representing the cumulative distanced travelled by the vehicle

    Pre-Conditions:
        path_length and cumulative_distances may be in any length unit, but they must share the same length unit
        Each index of the cumulative_distances array represents one second of the simulation

    :returns: The number of seconds the vehicle requires to travel the full path length. If vehicle does not travel the full path length, returns
    :rtype: int

    """

    # Create a boolean array to encode whether the vehicle has completed or not completed the route at a given timestamp
    # This is based on the assumption that each index represents a single timestamp of one second
    crossed_finish_line = np.where(cumulative_distances >= path_length, 1, 0)

    # Based on the boolean encoding, identify the first index which the vehicle has completed the route
    completion_index = np.where(crossed_finish_line == 1)

    if len(completion_index[0]) > 0:
        return completion_index[0][0]
    else:
        return len(cumulative_distances) + 1


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


def normalize(input_array: np.ndarray, max_value: float = None, min_value: float = None) -> np.ndarray:
    max_value_in_array = np.max(input_array) if max_value is None else max_value
    min_value_in_array = np.min(input_array) if min_value is None else min_value
    return (input_array - min_value_in_array) / (max_value_in_array - min_value_in_array)


if __name__ == '__main__':
    out = map_array_to_targets([90, 60, 10], [0, 1, 1, 1, 0])

    # speed_array input
    speed_array = np.array([45, 87, 65, 89, 43, 54, 45, 23, 34, 20])

    expanded_speed_array = reshape_and_repeat(speed_array, 9 * 3600)
    expanded_speed_array = np.insert(expanded_speed_array, 0, 0)
    expanded_speed_array = apply_deceleration(expanded_speed_array, 20)
