import datetime
import json
import os

import numpy as np
from bayes_opt import BayesianOptimization
from bokeh.layouts import gridplot
from bokeh.models import HoverTool
from bokeh.palettes import Bokeh8
from bokeh.plotting import figure, show, output_file
from dotenv import load_dotenv

import simulation
from simulation.common import helpers
from simulation.common.helpers import adjust_timestamps_to_local_times, get_array_directional_wind_speed
from simulation.config import settings_directory
from simulation.main.SimulationResult import SimulationResult


class Simulation:

    def __init__(self, race_type):
        """
        Instantiates a simple model of the car.

        :param race_type: a string that describes the race type to simulate (ASC or FSGP)

        Depending on the race type, the following initialisation parameters are read from the corresponding
        settings json file located in the config folder.

        google_api_key: API key to access GoogleMaps API. Stored in a .env file. Please ask Chris for this!
        weather_api_key: API key to access OpenWeather API. Stored in a .env file. Please ask Chris for this!
        origin_coord: array containing latitude and longitude of route start point
        dest_coord: array containing latitude and longitude of route end point
        waypoints: array containing latitude and longitude pairs of route waypoints
        tick: length of simulation's discrete time step (in seconds)
        simulation_duration: length of simulated time (in seconds)
        start_hour: describes the hour to start the simulation (typically either 7 or 9, these
        represent 7am and 9am respectively)
        """

        # TODO: replace max_speed with a direct calculation taking into account car elevation and wind_speed

        assert race_type in ["ASC", "FSGP"]

        # chooses the appropriate settings file to read from
        if race_type == "ASC":
            settings_path = settings_directory / "settings_ASC.json"
        else:
            settings_path = settings_directory / "settings_FSGP.json"

        with open(settings_path) as f:
            args = json.load(f)

        self.initial_battery_charge = args['initial_battery_charge']

        # LVS power loss is pretty small so it is neglected, but we can change it in the future if needed.
        self.lvs_power_loss = args['lvs_power_loss']

        # ----- Time constants -----

        self.tick = args['tick']
        self.simulation_duration = args['simulation_duration']
        self.start_hour = args['start_hour']

        # ----- API keys -----

        load_dotenv()

        self.weather_api_key = os.environ.get("OPENWEATHER_API_KEY")
        self.google_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

        # ----- Route constants -----

        self.origin_coord = args['origin_coord']
        self.dest_coord = args['dest_coord']
        self.waypoints = args['waypoints']

        # ----- Route Length -----

        self.route_length = 0  # Tentatively set to 0

        # ----- Race type -----

        self.race_type = race_type

        # ----- Force update flags -----

        gis_force_update = args['gis_force_update']
        weather_force_update = args['weather_force_update']

        # ----- Component initialisation -----

        self.basic_array = simulation.BasicArray()

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)

        self.basic_lvs = simulation.BasicLVS(self.lvs_power_loss * self.tick)

        self.basic_motor = simulation.BasicMotor()

        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints,
                                  self.race_type, force_update=gis_force_update)
        self.route_coords = self.gis.get_path()

        self.vehicle_bearings = self.gis.calculate_current_heading_array()
        self.weather = simulation.WeatherForecasts(self.weather_api_key, self.route_coords,
                                                   self.simulation_duration / 3600,
                                                   self.race_type,
                                                   weather_data_frequency="daily",
                                                   force_update=weather_force_update)

        weather_hour = helpers.hour_from_unix_timestamp(self.weather.last_updated_time)
        self.time_of_initialization = self.weather.last_updated_time + 3600 * (24 + self.start_hour - weather_hour)

        self.solar_calculations = simulation.SolarCalculations()

        self.local_times = 0

        self.timestamps = np.arange(0, self.simulation_duration + self.tick, self.tick)

    @helpers.timeit
    def run_model(self, speed=np.array([20, 20, 20, 20, 20, 20, 20, 20]), plot_results=True, verbose=False,
                  route_visualization=False, **kwargs):
        """
        Updates the model in tick increments for the entire simulation duration. Returns
        a final battery charge and a distance travelled for this duration, given an
        initial charge, and a target speed. Also requires the current time and location.
        This is where the magic happens.

        Note: if the speed remains constant throughout this update, and knowing the starting
            time, the cumulative distance at every time can be known. From the cumulative
            distance, the GIS class updates the new location of the vehicle. From the location
            of the vehicle at every tick, the gradients at every tick, the weather at every
            tick, the GHI at every tick, is known.

        Note 2: currently, the simulation can only be run for times during which weather data is available

        :param speed: array that specifies the solar car's driving speed at each time step
        :param plot_results: set to True to plot the results of the simulation (is True by default)
        :param verbose: Boolean to control logging and debugging behaviour
        :param route_visualization: Flag to control route_visualization plot visibility
        :param **kwargs: variable list of arguments that specify the car's driving speed at each time step.
            Overrides the speed parameter.

        """

        # Used by the optimization function as it passes values as keyword arguments instead of a numpy array
        if kwargs:
            speed = np.fromiter(kwargs.values(), dtype=float)

            # Don't plot results since this code is run by the optimizer
            plot_results = False
            verbose=False

        # ----- Reshape speed array -----

        print(f"Input speeds: {speed}\n")

        speed_kmh = helpers.reshape_and_repeat(speed, self.simulation_duration)
        speed_kmh = np.insert(speed_kmh, 0, 0)
        speed_kmh = helpers.add_acceleration(speed_kmh, 500)

        # ------ Run calculations and get result and modified speed array -------

        result = self.__run_simulation_calculations(speed_kmh, verbose=verbose)

        # ------- Parse results ---------
        simulation_arrays = result.arrays
        speed_kmh = simulation_arrays[0]
        distances = simulation_arrays[1]
        state_of_charge = simulation_arrays[2]
        delta_energy = simulation_arrays[3]
        solar_irradiances = simulation_arrays[4]
        wind_speeds = simulation_arrays[5]
        gis_route_elevations_at_each_tick = simulation_arrays[6]
        cloud_covers = simulation_arrays[7]

        distance_travelled = result.distance_travelled
        time_taken = result.time_taken
        final_soc = result.final_soc

        print(f"Simulation successful!\n"
              f"Time taken: {time_taken}\n"
              f"Route length: {self.route_length:.2f}km\n"
              f"Maximum distance traversable: {distance_travelled:.2f}km\n"
              f"Average speed: {np.average(speed_kmh):.2f}km/h\n"
              f"Final battery SOC: {final_soc:.2f}%\n")

        # ----- Plotting -----

        if plot_results:
            arrays_to_plot = [speed_kmh, distances, state_of_charge, delta_energy,
                              solar_irradiances, wind_speeds, gis_route_elevations_at_each_tick,
                              cloud_covers]
            y_label = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                       "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)", "Cloud cover (%)"]

            helpers.plot_graph(timestamps=self.timestamps,
                               arrays_to_plot=arrays_to_plot,
                               array_labels=y_label,
                               graph_title="Simulation Result")

        if self.race_type == "FSGP":
            # Do this so I'm not plotting the entire 300 laps which will look the same as one lap anyway.
            helpers.route_visualization(self.gis.singlelap_path, visible=route_visualization)
        elif self.race_type == "ASC":
            helpers.route_visualization(self.gis.path, visible=route_visualization)

        return distance_travelled

    @helpers.timeit
    def optimize(self, *args, **kwargs):
        """

        Args:
            *args: Do not serve any function.
            **kwargs: variable list of arguments that specify the car's driving speed at each time step.

        Returns: A local maximium for distance found through optimization

        """

        guess_lower_bound = 20
        guess_upper_bound = 80

        bounds = {
            'x0': (guess_lower_bound, guess_upper_bound),
            'x1': (guess_lower_bound, guess_upper_bound),
            'x2': (guess_lower_bound, guess_upper_bound),
            'x3': (guess_lower_bound, guess_upper_bound),
            'x4': (guess_lower_bound, guess_upper_bound),
            'x5': (guess_lower_bound, guess_upper_bound),
            'x6': (guess_lower_bound, guess_upper_bound),
            'x7': (guess_lower_bound, guess_upper_bound),
        }

        # verbose = 1 prints only when a maximum is observed, verbose = 0 is silent
        optimizer = BayesianOptimization(f=self.run_model, pbounds=bounds,
                                         verbose=2)

        # configure these parameters depending on whether optimizing for speed or precision
        # Parameter Explanations: https://github.com/fmfn/BayesianOptimization/blob/master/examples/exploitation_vs_exploration.ipynb
        # Acquisition Functions: https://www.cse.wustl.edu/~garnett/cse515t/spring_2015/files/lecture_notes/12.pdf for an explanation
        optimizer.maximize(init_points=200, n_iter=20, acq='ucb', xi=1e-1, kappa=10)

        result = optimizer.max
        result_params = list(result["params"].values())

        speed_result = np.empty(len(result_params))
        for i in range(len(speed_result)):
            speed_result[i] = result_params[i]

        speed_result = helpers.reshape_and_repeat(speed_result, self.simulation_duration)
        speed_result = np.insert(speed_result, 0, 0)

        arrays_to_plot = self.__run_simulation_calculations(speed_result, verbose=False)

        helpers.plot_graph(timestamps=self.timestamps, arrays_to_plot=arrays_to_plot.arrays,
                           array_labels=["Optimized speed array", "Distance (km)", "SOC (%)", "Delta energy (J)",
                                         "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)",
                                         "Cloud cover (%)"],
                           graph_title="Optimized Result")

        return optimizer.max

    def __plot_graph(self, arrays_to_plot, array_labels, graph_title):
        """

        This is a utility function to plot out any set of NumPy arrays you pass into it.
        The precondition of this function is that the length of arrays_to_plot and array_labels are equal.

        This is because there be a 1:1 mapping of each entry of arrays_to_plot to array_labels such that:
            arrays_to_plot[n] has label array_labels[n]

        Another precondition of this function is that each of the arrays within arrays_to_plot also have the
        same length. This is each of them will share the same time axis.

        Args:
            arrays_to_plot: An array of NumPy arrays to plot
            array_labels: An array of strings for the individual plot titles
            graph_title: A string that serves as the plot's main title

        Result:
            If number of plots is even, produces a 2 x (len(arrays_to_plot) / 2) plot
            If number of plots is odd, produces a 1 x len(arrays_to_plot) plot

        """
        compress_constant = int(self.timestamps.shape[0] / 5000)

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
            figures[index].line(self.timestamps[::compress_constant] * 1000, data_array, line_color=Bokeh8[index],
                                line_width=2)

            figures[index].add_tools(hover_tool)

        grid = gridplot(figures, sizing_mode="scale_both", ncols=3, plot_height=200, plot_width=300)

        output_file(filename=graph_title + '.html', title=graph_title)

        show(grid)

    def __run_simulation_calculations(self, speed_kmh, verbose=False):
        """
        Helper method to perform all calculations used in run_model. Returns a SimulationResult object 
        containing members that specify total distance travelled and time taken at the end of the simulation
        and final battery state of charge. This is where most of the main simulation logic happens.

        :param speed_kmh: array that specifies the solar car's driving speed (in km/h) at each time step
        """

        tick_array = np.diff(self.timestamps)
        tick_array = np.insert(tick_array, 0, 0)

        speed_kmh, not_charge = helpers.apply_race_timing_constraints(speed_kmh=speed_kmh, start_hour=self.start_hour,
                                                                      simulation_duration=self.simulation_duration,
                                                                      race_type=self.race_type,
                                                                      timestamps=self.timestamps,
                                                                      verbose=verbose)

        # Acceleration currently is broken and I'm not sure why. Have to take another look at this soon.
        # speed_kmh = helpers.add_acceleration(speed_kmh, 500)

        # ----- Expected distance estimate -----

        # Array of cumulative distances theoretically achievable via the speed array

        distances = tick_array * speed_kmh / 3.6
        cumulative_distances = np.cumsum(distances)

        temp = cumulative_distances

        # ----- Weather and location calculations -----

        """ closest_gis_indices is a 1:1 mapping between each point which has within it a timestamp and cumulative
                distance from a starting point, to its closest point on a map.

            closest_weather_indices is a 1:1 mapping between a weather condition, and its closest point on a map.
        """

        closest_gis_indices = self.gis.calculate_closest_gis_indices(cumulative_distances)

        closest_weather_indices = self.weather.calculate_closest_weather_indices(cumulative_distances)

        path_distances = self.gis.path_distances
        cumulative_distances = np.cumsum(path_distances)  # [cumulative_distances] = meters

        max_route_distance = cumulative_distances[-1]

        self.route_length = max_route_distance / 1000.0  # store the route length in kilometers

        # Array of elevations at every route point
        gis_route_elevations = self.gis.get_path_elevations()

        gis_route_elevations_at_each_tick = gis_route_elevations[closest_gis_indices]

        # Get the azimuth angle of the vehicle at every location
        gis_vehicle_bearings = self.vehicle_bearings[closest_gis_indices]

        # Get array of path gradients
        gradients = self.gis.get_gradients(closest_gis_indices)

        # ----- Timing Calculations -----

        # Get time zones at each point on the GIS path
        time_zones = self.gis.get_time_zones(closest_gis_indices)

        # Local times in UNIX timestamps
        local_times = adjust_timestamps_to_local_times(self.timestamps, self.time_of_initialization, time_zones)

        # only for reference (may be used in the future)
        local_times_datetime = np.array(
            [datetime.datetime.utcfromtimestamp(local_unix_time) for local_unix_time in local_times])
        time_of_day_hour = np.array([helpers.hour_from_unix_timestamp(ti) for ti in local_times])

        # Get the weather at every location
        weather_forecasts = self.weather.get_weather_forecast_in_time(closest_weather_indices, local_times)
        roll_by_tick = 3600 * (24 + self.start_hour - helpers.hour_from_unix_timestamp(weather_forecasts[0, 2]))
        weather_forecasts = np.roll(weather_forecasts, -roll_by_tick, 0)
        absolute_wind_speeds = weather_forecasts[:, 5]
        wind_directions = weather_forecasts[:, 6]
        cloud_covers = weather_forecasts[:, 7]


        # Get the wind speeds at every location
        wind_speeds = get_array_directional_wind_speed(gis_vehicle_bearings, absolute_wind_speeds,
                                                       wind_directions)

        # Get an array of solar irradiance at every coordinate and time
        solar_irradiances = self.solar_calculations.calculate_array_GHI(self.route_coords[closest_gis_indices],
                                                                        time_zones, local_times,
                                                                        gis_route_elevations_at_each_tick,
                                                                        cloud_covers)

        # TLDR: we have now obtained solar irradiances, wind speeds, and gradients at each tick

        # ----- Energy calculations -----

        self.basic_lvs.update(self.tick)

        lvs_consumed_energy = self.basic_lvs.get_consumed_energy()
        motor_consumed_energy = self.basic_motor.calculate_energy_in(speed_kmh, gradients, wind_speeds, self.tick)
        array_produced_energy = self.basic_array.calculate_produced_energy(solar_irradiances, self.tick)

        motor_consumed_energy = np.logical_and(motor_consumed_energy, not_charge) * motor_consumed_energy

        consumed_energy = motor_consumed_energy + lvs_consumed_energy
        produced_energy = array_produced_energy

        # net energy added to the battery
        delta_energy = produced_energy - consumed_energy

        # ----- Array initialisation -----

        # used to calculate the time the car was in motion
        tick_array = np.full_like(self.timestamps, fill_value=self.tick, dtype='f4')
        tick_array[0] = 0

        # ----- Array calculations -----

        cumulative_delta_energy = np.cumsum(delta_energy)
        battery_variables_array = self.basic_battery.update_array(cumulative_delta_energy)

        # stores the battery SOC at each time step
        state_of_charge = battery_variables_array[0]
        state_of_charge[np.abs(state_of_charge) < 1e-03] = 0

        # when the battery is empty the car will not move
        # TODO: if the car cannot climb the slope, the car also does not move
        # when the car is charging the car does not move
        # at night the car does not move

        if verbose:

            helpers.plot_graph(timestamps=self.timestamps,
                               arrays_to_plot=[temp, closest_gis_indices, closest_weather_indices, gradients,
                                               time_zones, gis_vehicle_bearings],
                               array_labels=["speed dist (m)", "gis ind", "weather ind", "gradients (m)", "time zones",
                                             "vehicle bearings"],
                               graph_title="Indices and Environment variables")
            arrays_to_plot = [speed_kmh, state_of_charge]

            for arr in [state_of_charge, not_charge]:
                speed_kmh = np.logical_and(speed_kmh, arr) * speed_kmh
                arrays_to_plot.append(speed_kmh)

            helpers.plot_graph(timestamps=self.timestamps,
                               arrays_to_plot=arrays_to_plot,
                               array_labels=["Speed (km/h)", "SOC", "Speed & SOC", "Speed & not_charge"],
                               graph_title="Speed Boolean Operations")
        else:
            speed_kmh = np.logical_and(not_charge, state_of_charge) * speed_kmh

        time_in_motion = np.logical_and(tick_array, speed_kmh) * self.tick

        final_soc = state_of_charge[-1] * 100 + 0.

        distance = speed_kmh * (time_in_motion / 3600)
        distances = np.cumsum(distance)

        # Car cannot exceed Max distance, and it is not in motion after exceeded
        distances = distances.clip(0, max_route_distance / 1000)

        try:
            max_dist_index = np.where(distances == max_route_distance / 1000)[0][0]
        except IndexError:
            max_dist_index = len(time_in_motion)

        time_in_motion = np.array(
            (list(time_in_motion[0:max_dist_index])) + list(np.zeros_like(time_in_motion[max_dist_index:])))

        time_taken = np.sum(time_in_motion)
        time_taken = str(datetime.timedelta(seconds=int(time_taken)))

        results = SimulationResult()

        results.arrays = [
            speed_kmh,
            distances,
            state_of_charge,
            delta_energy,
            solar_irradiances,
            wind_speeds,
            gis_route_elevations_at_each_tick,
            cloud_covers
        ]
        results.distance_travelled = distances[-1]
        results.time_taken = time_taken
        results.final_soc = final_soc

        self.time_zones = time_zones
        self.local_times = local_times

        return results
