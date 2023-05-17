import json
import sys
import logging
import os
import numpy as np
import simulation

from tqdm import tqdm
from enum import Enum
from dotenv import load_dotenv
from simulation.common import helpers
from simulation.config import settings_directory
from simulation.main.SimulationResult import SimulationResult
from simulation.common.plotting import Graph, Plotting


class SimulationReturnType(Enum):
    """

    This enum exists to discretize different data types run_model should return.

    """

    time_taken = 0
    distance_travelled = 1
    simulation_results = 2


class Simulation:
    """

    Attributes:
        google_api_key: API key to access GoogleMaps API. Stored in a .env file. Please ask Simulation Lead for this!
        weather_api_key: API key to access OpenWeather API. Stored in a .env file. Please ask Simulation Lead for this!
        origin_coord: array containing latitude and longitude of route start point
        dest_coord: array containing latitude and longitude of route end point
        waypoints: array containing latitude and longitude pairs of route waypoints
        tick: length of simulation's discrete time step (in seconds)
        simulation_duration: length of simulated time (in seconds)
        start_hour: describes the hour to start the simulation (typically either 7 or 9, these
        represent 7am and 9am respectively)

    """

    def __init__(self, initial_conditions, return_type, race_type, golang=True):
        """

        Instantiates a simple model of the car.

        :param race_type: a string that describes the race type to simulate (ASC or FSGP)
        :param initial_conditions: a SimulationState object that provides initial conditions for the simulation
        :param return_type: discretely defines what kind of data run_model should return.
        :param golang: boolean which controls whether GoLang implementations are used when available

        """

        # ----- Return type -----

        assert return_type in SimulationReturnType, "return_type must be of SimulationReturnType enum."

        self.return_type = return_type

        # ----- Race type -----

        assert race_type in ["ASC", "FSGP"]

        self.race_type = race_type

        if race_type == "ASC":
            settings_path = settings_directory / "settings_ASC.json"
        else:
            settings_path = settings_directory / "settings_FSGP.json"

        with open(settings_path) as f:
            args = json.load(f)

        # ----- Load from settings_*.json -----

        self.lvs_power_loss = args['lvs_power_loss']  # LVS power loss is pretty small, so it is neglected

        self.tick = args['tick']

        if self.race_type == "ASC":
            race_length = args['race_length']  # Race length in days, arbitrary as ASC doesn't have a time limit
            self.simulation_duration = race_length * 24 * 60 * 60
        elif self.race_type == "FSGP":
            self.simulation_duration = args['simulation_duration']

        # ----- Load from initial_conditions

        self.initial_battery_charge = initial_conditions.initial_battery_charge

        self.start_hour = initial_conditions.start_hour

        self.origin_coord = initial_conditions.origin_coord
        self.dest_coord = initial_conditions.dest_coord
        self.current_coord = initial_conditions.current_coord
        self.waypoints = initial_conditions.waypoints

        gis_force_update = initial_conditions.gis_force_update
        weather_force_update = initial_conditions.weather_force_update

        # ----- Route Length -----

        self.route_length = 0  # Tentatively set to 0

        # ----- API keys -----

        load_dotenv()

        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY')
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

        # ----- GoLang library initialisation -----
        self.golang = golang
        self.library = simulation.Libraries(raiseExceptionOnFail=False)

        if self.golang and self.library.found_compatible_binaries() is False:
            # If compatible GoLang binaries weren't found, disable GoLang usage.
            self.golang = False
            logging.warning("GoLang binaries not found --> GoLang usage has been disabled. "
                            "To use GoLang implementations, see COMPILING_HOWTO about "
                            "compiling GoLang for your operating system.")

        # ----- Component initialisation -----

        self.basic_array = simulation.BasicArray()

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)

        self.basic_lvs = simulation.BasicLVS(self.lvs_power_loss * self.tick)

        self.basic_motor = simulation.BasicMotor()

        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints,
                                  self.race_type, library=self.library, force_update=gis_force_update,
                                  current_coord=self.current_coord, golang=golang)

        self.route_coords = self.gis.get_path()

        self.vehicle_bearings = self.gis.calculate_current_heading_array()

        self.weather = simulation.WeatherForecasts(self.weather_api_key, self.route_coords,
                                                   self.simulation_duration / 3600,
                                                   self.race_type,
                                                   library=self.library,
                                                   weather_data_frequency="daily",
                                                   force_update=weather_force_update,
                                                   origin_coord=self.gis.launch_point,
                                                   golang=golang)

        weather_hour = helpers.hour_from_unix_timestamp(self.weather.last_updated_time)
        self.time_of_initialization = self.weather.last_updated_time + 3600 * (24 + self.start_hour - weather_hour)

        self.solar_calculations = simulation.SolarCalculations(library=self.library)

        self.local_times = 0

        self.timestamps = np.arange(0, self.simulation_duration + self.tick, self.tick)

        self.plotting = Plotting()

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
        :param kwargs: variable list of arguments that specify the car's driving speed at each time step.
            Overrides the speed parameter.

        """

        # Used by the optimization function as it passes values as keyword arguments instead of a numpy array
        if kwargs:
            speed = np.fromiter(kwargs.values(), dtype=float)

            # Don't plot results since this code is run by the optimizer
            plot_results = False
            verbose = False

        # ----- Reshape speed array -----
        if not kwargs:
            print(f"Input speeds: {speed}\n")

        speed_kmh = helpers.reshape_and_repeat(speed, self.simulation_duration)
        speed_kmh = np.insert(speed_kmh, 0, 0)
        speed_kmh = helpers.apply_deceleration(speed_kmh, 20)

        speed_kmh, not_charge = helpers.apply_race_timing_constraints(speed_kmh=speed_kmh, start_hour=self.start_hour,
                                                                      simulation_duration=self.simulation_duration,
                                                                      race_type=self.race_type,
                                                                      timestamps=self.timestamps,
                                                                      verbose=verbose)

        if self.race_type == "ASC":
            speed_kmh_without_checkpoints = speed_kmh
            speed_kmh = self.gis.speeds_with_waypoints(self.gis.path, self.gis.path_distances, speed_kmh / 3.6,
                                                       self.waypoints, verbose=False)[:self.simulation_duration + 1]
            if verbose:
                self.plotting.add_graph_to_queue(Graph([speed_kmh_without_checkpoints, speed_kmh],
                                                       ["Speed before waypoints", " Speed after waypoints"],
                                                       "Before and After waypoints"))

        speed_kmh = helpers.apply_deceleration(speed_kmh, 20)
        raw_speed = speed_kmh

        # ------ Run calculations and get result and modified speed array -------
        with tqdm(total=20, file=sys.stdout, desc="Running Simulation Calculations") as pbar:
            result = self.__run_simulation_calculations(speed_kmh, not_charge, pbar, verbose=verbose)

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
        raw_soc = self.basic_battery.get_raw_soc(np.cumsum(delta_energy))

        if not kwargs:
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
                              cloud_covers, raw_soc, raw_speed]
            y_label = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                       "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)", "Cloud cover (%)",
                       "Raw SOC (%)", "Raw Speed (km/h)"]

            self.plotting.add_graph_to_queue(Graph(arrays_to_plot, y_label, "Results"))
            self.plotting.plot_graphs(self.timestamps)

        if self.race_type == "FSGP":
            helpers.route_visualization(self.gis.single_lap_path, visible=route_visualization)
        elif self.race_type == "ASC":
            helpers.route_visualization(self.gis.path, visible=route_visualization)

        if self.return_type is SimulationReturnType.distance_travelled:
            return distance_travelled
        if self.return_type is SimulationReturnType.time_taken:
            return -1 * time_taken
        if self.return_type is SimulationReturnType.simulation_results:
            return result
        else:
            raise TypeError("Return type not found.")

    def __run_simulation_calculations(self, speed_kmh, not_charge, pbar, verbose=False):
        """

        Helper method to perform all calculations used in run_model. Returns a SimulationResult object 
        containing members that specify total distance travelled and time taken at the end of the simulation
        and final battery state of charge. This is where most of the main simulation logic happens.

        :param speed_kmh: array that specifies the solar car's driving speed (in km/h) at each time step
        :param not_charge: array that specifies when the car is charging for calculations
        :param pbar: progress bar used to track Simulation progress

        """

        # ----- Tick array -----

        tick_array = np.diff(self.timestamps)
        tick_array = np.insert(tick_array, 0, 0)

        pbar.update(1)

        # ----- Expected distance estimate -----

        # Array of cumulative distances theoretically achievable via the speed array
        distances = tick_array * speed_kmh / 3.6
        cumulative_distances = np.cumsum(distances)

        temp = cumulative_distances
        pbar.update(1)

        # ----- Weather and location calculations -----

        """ closest_gis_indices is a 1:1 mapping between each point which has within it a timestamp and cumulative
                distance from a starting point, to its closest point on a map.

            closest_weather_indices is a 1:1 mapping between a weather condition, and its closest point on a map.
        """

        closest_gis_indices = self.gis.calculate_closest_gis_indices(cumulative_distances)

        pbar.update(1)

        closest_weather_indices = self.weather.calculate_closest_weather_indices(cumulative_distances)

        pbar.update(1)

        path_distances = self.gis.path_distances
        cumulative_distances = np.cumsum(path_distances)  # [cumulative_distances] = meters

        pbar.update(1)

        max_route_distance = cumulative_distances[-1]

        self.route_length = max_route_distance / 1000.0  # store the route length in kilometers

        pbar.update(1)

        # Array of elevations at every route point
        gis_route_elevations = self.gis.get_path_elevations()

        gis_route_elevations_at_each_tick = gis_route_elevations[closest_gis_indices]

        pbar.update(1)

        # Get the azimuth angle of the vehicle at every location
        gis_vehicle_bearings = self.vehicle_bearings[closest_gis_indices]

        pbar.update(1)

        # Get array of path gradients
        gradients = self.gis.get_gradients(closest_gis_indices)

        pbar.update(1)

        # ----- Timing Calculations -----

        # Get time zones at each point on the GIS path
        time_zones = self.gis.get_time_zones(closest_gis_indices)

        # Local times in UNIX timestamps
        local_times = helpers.adjust_timestamps_to_local_times(self.timestamps, self.time_of_initialization, time_zones)

        pbar.update(1)

        # Get the weather at every location
        weather_forecasts = self.weather.get_weather_forecast_in_time(closest_weather_indices, local_times)
        roll_by_tick = 3600 * (24 + self.start_hour - helpers.hour_from_unix_timestamp(weather_forecasts[0, 2]))
        weather_forecasts = np.roll(weather_forecasts, -roll_by_tick, 0)

        pbar.update(2)

        absolute_wind_speeds = weather_forecasts[:, 5]
        wind_directions = weather_forecasts[:, 6]
        cloud_covers = weather_forecasts[:, 7]

        pbar.update(1)

        # Get the wind speeds at every location
        wind_speeds = helpers.get_array_directional_wind_speed(gis_vehicle_bearings, absolute_wind_speeds,
                                                       wind_directions)

        pbar.update(1)

        # Get an array of solar irradiance at every coordinate and time
        solar_irradiances = self.solar_calculations.calculate_array_GHI(self.route_coords[closest_gis_indices],
                                                                        time_zones, local_times,
                                                                        gis_route_elevations_at_each_tick,
                                                                        cloud_covers)

        pbar.update(2)
        # TLDR: we have now obtained solar irradiances, wind speeds, and gradients at each tick

        # ----- Energy Calculations -----

        self.basic_lvs.update(self.tick)

        lvs_consumed_energy = self.basic_lvs.get_consumed_energy()
        motor_consumed_energy = self.basic_motor.calculate_energy_in(speed_kmh, gradients, wind_speeds, self.tick)
        array_produced_energy = self.basic_array.calculate_produced_energy(solar_irradiances, self.tick)

        motor_consumed_energy = np.logical_and(motor_consumed_energy, not_charge) * motor_consumed_energy

        pbar.update(1)

        consumed_energy = motor_consumed_energy + lvs_consumed_energy
        produced_energy = array_produced_energy

        # net energy added to the battery
        delta_energy = produced_energy - consumed_energy

        pbar.update(1)

        # ----- Array initialisation -----

        # used to calculate the time the car was in motion
        tick_array = np.full_like(self.timestamps, fill_value=self.tick, dtype='f4')
        tick_array[0] = 0

        # ----- Array calculations -----

        cumulative_delta_energy = np.cumsum(delta_energy)
        battery_variables_array = self.basic_battery.update_array(cumulative_delta_energy)

        pbar.update(1)

        # stores the battery SOC at each time step
        state_of_charge = battery_variables_array[0]
        state_of_charge[np.abs(state_of_charge) < 1e-03] = 0

        speed_kmh = np.logical_and(not_charge, state_of_charge) * speed_kmh

        if verbose:
            indices_and_environment_graph = Graph([temp, closest_gis_indices, closest_weather_indices, gradients,
                                                   time_zones, gis_vehicle_bearings],
                                                  ["speed dist (m)", "gis ind", "weather ind", "gradients (m)",
                                                   "time zones",
                                                   "vehicle bearings"], "Indices and Environment variables")
            self.plotting.add_graph_to_queue(indices_and_environment_graph)

            speed_boolean_graph = Graph([speed_kmh, state_of_charge],
                                        ["Speed (km/h)", "SOC", "Speed & SOC", "Speed & not_charge"],
                                        "Speed Boolean Operations")
            self.plotting.add_graph_to_queue(speed_boolean_graph)

        pbar.update(1)

        time_in_motion = np.logical_and(tick_array, speed_kmh) * self.tick

        final_soc = state_of_charge[-1] * 100 + 0.

        distance = speed_kmh * (time_in_motion / 3600)
        distances = np.cumsum(distance)

        # Car cannot exceed Max distance, and it is not in motion after exceeded
        distances = distances.clip(0, max_route_distance / 1000)

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

        pbar.update(1)

        if results.distance_travelled >= self.route_length:
            results.time_taken = helpers.calculate_race_completion_time(
                self.route_length, distances)
        else:
            results.time_taken = self.simulation_duration

        results.final_soc = final_soc

        self.time_zones = time_zones
        self.local_times = local_times

        return results
