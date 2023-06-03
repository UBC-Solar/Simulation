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
from simulation.common.plotting import Graph, Plotting


class SimulationReturnType(Enum):
    """

    This enum exists to discretize different data types run_model should return.

    """

    time_taken = 0
    distance_travelled = 1
    void = 2


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

        # --------- Results ---------

        self.speed_kmh = None
        self.distances = None
        self.state_of_charge = None
        self.delta_energy = None
        self.solar_irradiances = None
        self.wind_speeds = None
        self.gis_route_elevations_at_each_tick = None
        self.cloud_covers = None
        self.distance = None
        self.route_length = None
        self.time_taken = None
        self.distance_travelled = None

        # --------- Calculations ---------

        self.tick_array = None
        self.time_zones = None
        self.distances = None
        self.cumulative_distances = None
        self.temp = None
        self.closest_gis_indices = None
        self.closest_weather_indices = None
        self.path_distances = None
        self.max_route_distance = None
        self.gis_route_elevations_at_each_tick = None
        self.gis_vehicle_bearings = None
        self.gradients = None
        self.absolute_wind_speeds = None
        self.wind_directions = None
        self.lvs_consumed_energy = None
        self.motor_consumed_energy = None
        self.array_produced_energy = None
        self.raw_soc = None
        self.not_charge = None
        self.consumed_energy = None
        self.produced_energy = None
        self.time_in_motion = None
        self.final_soc = None

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

        speed_boolean_array = helpers.get_race_timing_constraints_boolean(self.start_hour, self.simulation_duration,
                                                                          self.race_type, as_seconds=False).astype(int)
        speed_mapped = helpers.map_array_to_targets(speed, speed_boolean_array)
        speed_mapped_kmh = helpers.reshape_and_repeat(speed_mapped, self.simulation_duration)
        speed_mapped_kmh = np.insert(speed_mapped_kmh, 0, 0)
        self.speed_kmh = helpers.apply_deceleration(speed_mapped_kmh, 20)

        if self.race_type == "ASC":
            speed_kmh_without_checkpoints = self.speed_kmh
            self.speed_kmh = self.gis.speeds_with_waypoints(self.gis.path, self.gis.path_distances,
                                                            self.speed_kmh / 3.6,
                                                            self.waypoints, verbose=False)[:self.simulation_duration + 1]
            if verbose:
                self.plotting.add_graph_to_queue(Graph([speed_kmh_without_checkpoints, self.speed_kmh],
                                                       ["Speed before waypoints", " Speed after waypoints"],
                                                       "Before and After waypoints"))

        self.speed_kmh = helpers.apply_deceleration(self.speed_kmh, 20)
        raw_speed = self.speed_kmh

        # ------ Run calculations and get result and modified speed array -------
        with tqdm(total=20, file=sys.stdout, desc="Running Simulation Calculations") as pbar:
            self.__run_simulation_calculations(pbar)

        if not kwargs:
            print(f"Simulation successful!\n"
                  f"Time taken: {self.time_taken}\n"
                  f"Route length: {self.route_length:.2f}km\n"
                  f"Maximum distance traversable: {self.distance_travelled:.2f}km\n"
                  f"Average speed: {np.average(self.speed_kmh):.2f}km/h\n"
                  f"Final battery SOC: {self.final_soc:.2f}%\n")

        # ----- Plotting -----

        if plot_results:
            arrays_to_plot = [self.speed_kmh, self.distances, self.state_of_charge, self.delta_energy,
                              self.solar_irradiances, self.wind_speeds, self.gis_route_elevations_at_each_tick,
                              self.cloud_covers, self.raw_soc, raw_speed]
            y_label = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                       "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)", "Cloud cover (%)",
                       "Raw SOC (%)", "Raw Speed (km/h)"]

            self.plotting.add_graph_to_queue(Graph(arrays_to_plot, y_label, "Results"))
            self.plotting.plot_graphs(self.timestamps)

            if verbose:
                indices_and_environment_graph = Graph(
                    [self.temp, self.closest_gis_indices, self.closest_weather_indices,
                     self.gradients, self.time_zones, self.gis_vehicle_bearings],
                    ["speed dist (m)", "gis ind", "weather ind", "gradients (m)",
                     "time zones",
                     "vehicle bearings"], "Indices and Environment variables")
                self.plotting.add_graph_to_queue(indices_and_environment_graph)

                speed_boolean_graph = Graph([self.speed_kmh, self.state_of_charge],
                                            ["Speed (km/h)", "SOC", "Speed & SOC", "Speed & not_charge"],
                                            "Speed Boolean Operations")
                self.plotting.add_graph_to_queue(speed_boolean_graph)

        if route_visualization:
            if self.race_type == "FSGP":
                helpers.route_visualization(self.gis.single_lap_path, visible=route_visualization)
            elif self.race_type == "ASC":
                helpers.route_visualization(self.gis.path, visible=route_visualization)

        if self.return_type is SimulationReturnType.distance_travelled:
            return self.distance_travelled
        if self.return_type is SimulationReturnType.time_taken:
            return -1 * self.time_taken
        if self.return_type is SimulationReturnType.void:
            pass
        else:
            raise TypeError("Return type not found.")

    def __run_simulation_calculations(self, pbar):
        """

        Helper method to perform all calculations used in run_model. Returns a SimulationResult object 
        containing members that specify total distance travelled and time taken at the end of the simulation
        and final battery state of charge. This is where most of the main simulation logic happens.

        :param pbar: progress bar used to track Simulation progress

        """

        # ----- Tick array -----

        self.tick_array = np.diff(self.timestamps)
        self.tick_array = np.insert(self.tick_array, 0, 0)

        pbar.update(1)

        # ----- Expected distance estimate -----

        # Array of cumulative distances theoretically achievable via the speed array
        self.distances = self.tick_array * self.speed_kmh / 3.6
        self.cumulative_distances = np.cumsum(self.distances)

        self.temp = self.cumulative_distances
        pbar.update(1)

        # ----- Weather and location calculations -----

        """ closest_gis_indices is a 1:1 mapping between each point which has within it a timestamp and cumulative
                distance from a starting point, to its closest point on a map.

            closest_weather_indices is a 1:1 mapping between a weather condition, and its closest point on a map.
        """

        self.closest_gis_indices = self.gis.calculate_closest_gis_indices(self.cumulative_distances)

        pbar.update(1)

        self.closest_weather_indices = self.weather.calculate_closest_weather_indices(self.cumulative_distances)

        pbar.update(1)

        self.path_distances = self.gis.path_distances
        self.cumulative_distances = np.cumsum(self.path_distances)  # [cumulative_distances] = meters

        pbar.update(1)

        self.max_route_distance = self.cumulative_distances[-1]

        self.route_length = self.max_route_distance / 1000.0  # store the route length in kilometers

        pbar.update(1)

        # Array of elevations at every route point
        gis_route_elevations = self.gis.get_path_elevations()

        self.gis_route_elevations_at_each_tick = gis_route_elevations[self.closest_gis_indices]

        pbar.update(1)

        # Get the azimuth angle of the vehicle at every location
        self.gis_vehicle_bearings = self.vehicle_bearings[self.closest_gis_indices]

        pbar.update(1)

        # Get array of path gradients
        self.gradients = self.gis.get_gradients(self.closest_gis_indices)

        pbar.update(1)

        # ----- Timing Calculations -----

        # Get time zones at each point on the GIS path
        self.time_zones = self.gis.get_time_zones(self.closest_gis_indices)

        # Local times in UNIX timestamps
        local_times = helpers.adjust_timestamps_to_local_times(self.timestamps, self.time_of_initialization,
                                                               self.time_zones)

        pbar.update(1)

        # Get the weather at every location
        weather_forecasts = self.weather.get_weather_forecast_in_time(self.closest_weather_indices, local_times)
        roll_by_tick = 3600 * (24 + self.start_hour - helpers.hour_from_unix_timestamp(weather_forecasts[0, 2]))
        weather_forecasts = np.roll(weather_forecasts, -roll_by_tick, 0)

        pbar.update(2)

        absolute_wind_speeds = weather_forecasts[:, 5]
        self.wind_directions = weather_forecasts[:, 6]
        self.cloud_covers = weather_forecasts[:, 7]

        pbar.update(1)

        # Get the wind speeds at every location
        self.wind_speeds = helpers.get_array_directional_wind_speed(self.gis_vehicle_bearings,
                                                                    absolute_wind_speeds,
                                                                    self.wind_directions)

        pbar.update(1)

        # Get an array of solar irradiance at every coordinate and time
        self.solar_irradiances = self.solar_calculations.calculate_array_GHI(
            self.route_coords[self.closest_gis_indices],
            self.time_zones, local_times,
            self.gis_route_elevations_at_each_tick,
            self.cloud_covers)

        pbar.update(2)

        # TLDR: we have now obtained solar irradiances, wind speeds, and gradients at each tick

        # ----- Energy Calculations -----

        self.basic_lvs.update(self.tick)

        self.lvs_consumed_energy = self.basic_lvs.get_consumed_energy()
        self.motor_consumed_energy = self.basic_motor.calculate_energy_in(self.speed_kmh, self.gradients,
                                                                          self.wind_speeds,
                                                                          self.tick)
        self.array_produced_energy = self.basic_array.calculate_produced_energy(self.solar_irradiances, self.tick)

        self.not_charge = helpers.get_charge_timing_constraints_boolean(start_hour=self.start_hour,
                                                                        simulation_duration=self.simulation_duration,
                                                                        race_type=self.race_type)
        self.array_produced_energy = np.logical_and(self.array_produced_energy,
                                                    self.not_charge) * self.array_produced_energy

        pbar.update(1)

        self.consumed_energy = self.motor_consumed_energy + self.lvs_consumed_energy
        self.produced_energy = self.array_produced_energy

        # net energy added to the battery
        self.delta_energy = self.produced_energy - self.consumed_energy

        pbar.update(1)

        # ----- Array initialisation -----

        # used to calculate the time the car was in motion
        self.tick_array = np.full_like(self.timestamps, fill_value=self.tick, dtype='f4')
        self.tick_array[0] = 0

        # ----- Array calculations -----

        cumulative_delta_energy = np.cumsum(self.delta_energy)
        battery_variables_array = self.basic_battery.update_array(cumulative_delta_energy)

        pbar.update(1)

        # stores the battery SOC at each time step
        self.state_of_charge = battery_variables_array[0]
        self.state_of_charge[np.abs(self.state_of_charge) < 1e-03] = 0
        self.raw_soc = self.basic_battery.get_raw_soc(np.cumsum(self.delta_energy))

        # This functionality may want to be removed in the future (speed array gets mangled when SOC <= 0)
        self.speed_kmh = np.logical_and(self.not_charge, self.state_of_charge) * self.speed_kmh

        pbar.update(1)

        self.time_in_motion = np.logical_and(self.tick_array, self.speed_kmh) * self.tick

        self.final_soc = self.state_of_charge[-1] * 100 + 0.

        self.distance = self.speed_kmh * (self.time_in_motion / 3600)
        self.distances = np.cumsum(self.distance)

        # Car cannot exceed Max distance, and it is not in motion after exceeded
        self.distances = self.distances.clip(0, self.max_route_distance / 1000)

        self.distance_travelled = self.distances[-1]

        pbar.update(1)

        if self.distance_travelled >= self.route_length:
            self.time_taken = helpers.calculate_race_completion_time(
                self.route_length, self.distances)
        else:
            self.time_taken = self.simulation_duration

    def get_driving_hours(self) -> int:
        """

        Returns the number of hours that the car is permitted to be driving.
        Dependent on rules in get_race_timing_constraints_boolean() function in common/helpers.

        :return: number of hours as an integer
        """

        return helpers.get_race_timing_constraints_boolean(self.start_hour, self.simulation_duration,
                                                           self.race_type, as_seconds=False).astype(int).sum()

    def get_results(self, values):
        simulation_results = {
            "speed_kmh": self.speed_kmh,
            "distances": self.distances,
            "state_of_charge": self.state_of_charge,
            "delta_energy": self.delta_energy,
            "solar_irradiances": self.solar_irradiances,
            "wind_speeds": self.wind_speeds,
            "gis_route_elevations_at_each_tick": self.gis_route_elevations_at_each_tick,
            "cloud_covers": self.cloud_covers,
            "distance": self.distance,
            "route_length": self.route_length,
            "time_taken": self.time_taken,
            "tick_array": self.tick_array,
            "time_zones": self.time_zones,
            "cumulative_distances": self.cumulative_distances,
            "temp": self.temp,
            "closest_gis_indices": self.closest_gis_indices,
            "closest_weather_indices": self.closest_weather_indices,
            "path_distances": self.path_distances,
            "max_route_distance": self.max_route_distance,
            "gis_vehicle_bearings": self.gis_vehicle_bearings,
            "gradients": self.gradients,
            "absolute_wind_speeds": self.absolute_wind_speeds,
            "wind_directions": self.wind_directions,
            "lvs_consumed_energy": self.lvs_consumed_energy,
            "motor_consumed_energy": self.motor_consumed_energy,
            "array_produced_energy": self.array_produced_energy,
            "not_charge": self.not_charge,
            "consumed_energy": self.consumed_energy,
            "produced_energy": self.produced_energy,
            "time_in_motion": self.time_in_motion,
            "final_soc": self.final_soc,
            "distance_travelled": self.distance_travelled
        }

        results = []
        for value in values:
            results.append(simulation_results[value])
        return results
