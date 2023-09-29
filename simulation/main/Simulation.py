import logging
import os
from typing import Union

import numpy as np
import simulation

from enum import Enum
from dotenv import load_dotenv
from simulation.common import helpers
from simulation.common.plotting import Graph, Plotting
from simulation.common.exceptions import LibrariesNotFound


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

    def __init__(self, builder):
        """

        Instantiates a simple model of the car.

        :param builder: a SimulationState object that provides settings for the Simulation

        """

        # A Model is a (mostly) immutable container for simulation calculations and results
        self._model = None

        # ----- Return type -----

        assert builder.return_type in SimulationReturnType, "return_type must be of SimulationReturnType enum."

        self.return_type = builder.return_type

        # ----- Race type -----

        assert builder.race_type in ["ASC", "FSGP"]

        self.race_type = builder.race_type

        # ---- Granularity -----
        self.granularity = builder.granularity

        # ---- Granularity -----
        self.granularity = builder.granularity

        # ----- Load from settings_*.json -----
        self.lvs_power_loss = builder.lvs_power_loss  # LVS power loss is pretty small, so it is neglected

        self.tick = builder.tick
        assert isinstance(self.tick, int), "Discrete tick length must be an integer!"

        if self.race_type == "ASC":
            race_length = builder.race_length  # Race length in days, arbitrary as ASC doesn't have a time limit
            self.simulation_duration = race_length * 24 * 60 * 60
        elif self.race_type == "FSGP":
            self.simulation_duration = builder.simulation_duration

        self.initial_battery_charge = builder.initial_battery_charge

        self.start_hour = builder.start_hour

        self.origin_coord = builder.origin_coord
        self.dest_coord = builder.dest_coord
        self.current_coord = builder.current_coord
        self.waypoints = builder.waypoints

        gis_force_update = builder.gis_force_update
        weather_force_update = builder.weather_force_update

        # ----- Route Length -----

        self.route_length = 0  # Tentatively set to 0

        # ----- API keys -----

        load_dotenv()

        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY')
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

        # ----- Go library initialisation -----
        self.golang = builder.golang
        if self.golang:
            try:
                self.library = simulation.Libraries()
            except LibrariesNotFound:
                # If compatible Go binaries weren't found, disable GoLang usage.
                self.golang = False
                self.library = None
                logging.warning("Go binaries not found ==> Go usage has been disabled. \n"
                                "To use Go implementations, see simulation/libraries/COMPILING_HOWTO.md \n"
                                "about compiling GoLang for your operating system.\n")
        else:
            self.library = None
        # ----- Component initialisation -----

        self.basic_array = simulation.BasicArray()

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)

        self.basic_lvs = simulation.BasicLVS(self.lvs_power_loss * self.tick)

        self.basic_motor = simulation.BasicMotor()

        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints,
                                  self.race_type, library=self.library, force_update=gis_force_update,
                                  current_coord=self.current_coord, golang=self.golang)

        self.route_coords = self.gis.get_path()

        self.vehicle_bearings = self.gis.calculate_current_heading_array()

        self.weather = simulation.WeatherForecasts(self.weather_api_key, self.route_coords,
                                                   self.simulation_duration / 3600,
                                                   self.race_type,
                                                   library=self.library,
                                                   weather_data_frequency="daily",
                                                   force_update=weather_force_update,
                                                   origin_coord=self.gis.launch_point,
                                                   golang=self.golang)

        weather_hour = helpers.hour_from_unix_timestamp(self.weather.last_updated_time)
        self.time_of_initialization = self.weather.last_updated_time + 3600 * (24 + self.start_hour - weather_hour)

        self.solar_calculations = simulation.SolarCalculations(golang=self.golang, library=self.library)

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
        assert len(speed) == self.get_driving_time_divisions(), ("Input driving speeds array must have length equal to "
                                                                 "get_driving_time_divisions()! Current length is "
                                                                 f"{len(speed)} and length of "
                                                                 f"{self.get_driving_time_divisions()} is needed!")
        speed_boolean_array = helpers.get_race_timing_constraints_boolean(self.start_hour, self.simulation_duration,
                                                                          self.race_type, as_seconds=False,
                                                                          granularity=self.granularity).astype(int)
        speed_mapped = helpers.map_array_to_targets(speed, speed_boolean_array)
        speed_mapped_kmh = helpers.reshape_and_repeat(speed_mapped, self.simulation_duration)
        speed_mapped_kmh = np.insert(speed_mapped_kmh, 0, 0)
        speed_kmh = helpers.apply_deceleration(speed_mapped_kmh, 20)

        if self.race_type == "ASC":
            speed_kmh_without_checkpoints = speed_kmh
            speed_kmh = self.gis.speeds_with_waypoints(self.gis.path, self.gis.path_distances, speed_kmh / 3.6,
                                                       self.waypoints, verbose=False)[:self.simulation_duration + 1]
            if verbose:
                self.plotting.add_graph_to_queue(Graph([speed_kmh_without_checkpoints, speed_kmh],
                                                       ["Speed before waypoints", " Speed after waypoints"],
                                                       "Before and After waypoints"))

        if self.tick != 1:
            speed_kmh = speed_kmh[::self.tick]
        raw_speed = speed_kmh

        # ------ Run calculations and get result and modified speed array -------
        self._model = simulation.Model(self, speed_kmh)
        self._model.run_simulation_calculations()

        results = self.get_results(["time_taken", "route_length", "distance_travelled", "speed_kmh", "final_soc"])
        if not kwargs:
            print(f"Simulation successful!\n"
                  f"Time taken: {results[0]}\n"
                  f"Route length: {results[1]:.2f}km\n"
                  f"Maximum distance traversable: {results[2]:.2f}km\n"
                  f"Average speed: {np.average(results[3]):.2f}km/h\n"
                  f"Final battery SOC: {results[4]:.2f}%\n")

        # ----- Plotting -----

        if plot_results:
            results_arrays = self.get_results(["speed_kmh", "distances", "state_of_charge", "delta_energy",
                                               "solar_irradiances", "wind_speeds", "gis_route_elevations_at_each_tick",
                                               "cloud_covers", "raw_soc"]) + [raw_speed]
            results_labels = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                              "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)",
                              "Cloud cover (%)", "Raw SOC (%)", "Raw Speed (km/h)"]

            self.plotting.add_graph_to_queue(Graph(results_arrays, results_labels, graph_name="Results"))

            if verbose:
                # Plot indices and environment arrays
                env_arrays = self.get_results(["temp", "closest_gis_indices", "closest_weather_indices",
                                               "gradients", "time_zones", "gis_vehicle_bearings"])
                env_labels = ["speed dist (m)", "gis ind", "weather ind",
                              "gradients (m)", "time zones", "vehicle bearings"]
                indices_and_environment_graph = Graph(env_arrays, env_labels, graph_name="Indices and Environment")
                self.plotting.add_graph_to_queue(indices_and_environment_graph)

                # Plot speed boolean and SOC arrays
                arrays_to_plot = self.get_results(["speed_kmh", "state_of_charge"])
                logical_arrays = []
                for arr in arrays_to_plot:
                    speed_kmh = np.logical_and(speed_kmh, arr) * speed_kmh
                    logical_arrays.append(speed_kmh)

                boolean_arrays = arrays_to_plot + logical_arrays
                boolean_labels = ["Speed (km/h)", "SOC", "Speed & SOC", "Speed & not_charge"]
                boolean_graph = Graph(boolean_arrays, boolean_labels, graph_name="Speed Boolean Operations")
                self.plotting.add_graph_to_queue(boolean_graph)

            self.plotting.plot_graphs(self.timestamps)

        if route_visualization:
            if self.race_type == "FSGP":
                helpers.route_visualization(self.gis.single_lap_path, visible=route_visualization)
            elif self.race_type == "ASC":
                helpers.route_visualization(self.gis.path, visible=route_visualization)

        if self.return_type is SimulationReturnType.distance_travelled:
            return float(results[2])
        if self.return_type is SimulationReturnType.time_taken:
            return -1 * float(results[0])
        if self.return_type is SimulationReturnType.void:
            pass
        else:
            raise TypeError("Return type not found.")

    def get_results(self, values: Union[np.ndarray, list, tuple, set]) -> list:
        """

        Use this function to extract data from a Simulation model.
        For example, input ["speed_kmh","delta_energy"] to extract speed_kmh and delta_energy. Use
        "default" to extract the properties that used to be in the SimulationResults object.

        :param values: an iterable of strings that should correspond to a certain property of simulation.
        :returns: a list of Simulation properties in the order provided.
        :rtype: list

        """

        return self._model.get_results(values)

    def get_driving_time_divisions(self) -> int:
        """

        Returns the number of time divisions (based on granularity) that the car is permitted to be driving.
        Dependent on rules in get_race_timing_constraints_boolean() function in common/helpers.

        :return: number of hours as an integer

        """

        return helpers.get_race_timing_constraints_boolean(self.start_hour, self.simulation_duration,
                                                           self.race_type, self.granularity,
                                                           as_seconds=False).sum().astype(int)
