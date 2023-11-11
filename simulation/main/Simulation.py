import simulation
import functools
import logging
import os
import numpy as np

from typing import Union
from strenum import StrEnum
from dotenv import load_dotenv

from simulation.common import helpers
from simulation.common.exceptions import LibrariesNotFound
from simulation.utils.Plotting import GraphPage


def simulation_property(func):
    """

    Apply this decorator to all functions that intend to get data from a Simulation model.
    This protects the data from being pulled from Simulation before the model has been simulated.

    :param func: function that will be used to get data

    """

    @functools.wraps(func)
    def property_wrapper(*args, **kwargs):
        assert isinstance(args[0], Simulation), "simulation_property wrapper applied to non-Simulation function!"
        if not args[0].calculations_have_happened():
            raise simulation.PrematureDataRecoveryError("You are attempting to collect information before simulation "
                                                        "model calculations have completed.")
        value = func(*args, **kwargs)
        return value

    return property_wrapper


class SimulationReturnType(StrEnum):
    """

    This enum exists to discretize different data types run_model should return.

    """

    time_taken = "time_taken"
    distance_travelled = "distance_travelled"
    distance_and_time = "distance_and_time"
    void = "void"


class Simulation:
    """

    Note: The first time that run_model is called will be SIGNIFICANTLY slower than future calls. This is because
    Simulation components contain many Numba JIT targets, which must be compiled at runtime the first time they are
    called.

    Attributes:
        return_type: defines what data that run_model should return
        race_type: string defining which race, ASC or FSGP, is being simulated
        granularity: controls how granular (detailed) the driving speeds array is
        initial_battery_charge: starting charge of the battery
        golang: define whether Go implementations should be used when applicable
        library: manages and locates Go shared libraries (if possible)
        google_api_key: API key to access GoogleMaps API. Stored in a .env file. Please ask Simulation Lead for this!
        weather_api_key: API key to access OpenWeather API. Stored in a .env file. Please ask Simulation Lead for this!
        origin_coord: array containing latitude and longitude of route start point
        dest_coord: array containing latitude and longitude of route end point
        waypoints: array containing latitude and longitude pairs of route waypoints
        tick: length of simulation's discrete time step (in seconds)
        simulation_duration: length of simulated time (in seconds)
        lvs_power_loss: a constant approximating the power consumption of our low-voltage components
        start_hour: describes the hour to start the simulation (typically either 7 or 9, these
        represent 7am and 9am respectively)

    """

    def __init__(self, builder):
        """

        Instantiates a simple model of the car.

        Do NOT call this constructor directly. Please create a SimulationBuilder and use
        SimulationBuilder.get() after setting parameters and initial conditions.

        :param builder: a SimulationBuilder object that provides settings for the Simulation

        """

        # ----- Return type -----

        assert builder.return_type in SimulationReturnType, "return_type must be of SimulationReturnType enum."

        self.return_type = builder.return_type

        # ----- Race type -----

        assert builder.race_type in ["ASC", "FSGP"]

        self.race_type = builder.race_type

        # ---- Granularity -----
        self.granularity = builder.granularity

        # ----- Load from settings_*.json -----
        self.lvs_power_loss = builder.lvs_power_loss  # LVS power loss is pretty small, so it is neglected

        self.tick = builder.tick
        assert isinstance(self.tick, int), "Discrete tick length must be an integer!"

        self.simulation_duration = builder.simulation_duration
        self.initial_battery_charge = builder.initial_battery_charge

        self.start_hour = builder.start_hour

        self.origin_coord = builder.origin_coord
        self.dest_coord = builder.dest_coord
        self.current_coord = builder.current_coord
        self.waypoints = builder.waypoints

        gis_force_update = builder.gis_force_update
        weather_force_update = builder.weather_force_update

        # ----- API keys -----

        load_dotenv()

        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY')
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')

        # ----- Go library initialisation -----

        # Simulation uses compiled Go libraries to speed up methods that cannot be accelerated with NumPy to achieve
        # a significant performance increase (~75% runtime reduction) when applicable.

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

        self.basic_regen = simulation.BasicRegen()

        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints,
                                  self.race_type, library=self.library, force_update=gis_force_update,
                                  current_coord=self.current_coord, golang=self.golang)

        self.route_coords = self.gis.get_path()

        self.basic_regen = simulation.BasicRegen()

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

        self.plotting = simulation.Plotting()

        # -------- Hash Key ---------

        self.hash_key = self.__hash__()

        # All attributes ABOVE will NOT be modified when the model is simulated. All attributes BELOW this WILL be
        # mutated over the course of simulation. Ensure that when you modify the behaviour of Simulation that this
        # fact is maintained, else the stability of the optimization process WILL be threatened, as it assumes
        # that the attributes above are independent of whether the model has been previously simulated.

        # A Model is a (mostly) immutable container for simulation calculations and results
        self._model = None

    def __hash__(self):
        hash_string = str(self.origin_coord) + str(self.dest_coord) + str(self.current_coord) + str(
            self.start_hour) + str(self.initial_battery_charge) + str(self.tick) + str(self.simulation_duration)
        for value in self.waypoints:
            hash_string += str(value)
        filtered_hash_string = "".join(filter(str.isnumeric, hash_string))
        return helpers.PJWHash(filtered_hash_string)

    def run_model(self, speed=None, plot_results=False, verbose=False,
                  route_visualization=False, plot_portion=(0.0, 1.0), **kwargs):
        """

        Given an array of driving speeds, simulate the model by running calculations sequentially for the entire
        simulation duration. Returns either time taken, distance travelled, or void. This function is mostly a wrapper
        around run_simulation_calculations, which is where the magic happens, that deals with processing the driving
        speeds array as well as plotting and handling the calculation results.

        Note: if the speed remains constant throughout this update, and knowing the starting
              time, the cumulative distance at every time can be known. From the cumulative
              distance, the GIS class updates the new location of the vehicle. From the location
              of the vehicle at every tick, the gradients at every tick, the weather at every
              tick, the GHI at every tick, is known.

        Note 2: currently, the simulation can only be run for times during which weather data is available

        :param np.ndarray speed: array that specifies the solar car's driving speed at each time step
        :param bool plot_results: set to True to plot the results of the simulation (is True by default)
        :param bool verbose: Boolean to control logging and debugging behaviour
        :param bool route_visualization: Flag to control route_visualization plot visibility
        :param tuple[float] plot_portion: A tuple containing the beginning and end of the portion of the array we'd
        like to plot as percentages (0 <= plot_portion <= 1).
        :param kwargs: variable list of arguments that specify the car's driving speed at each time step.
            Overrides the speed parameter.
        :param plot_portion: A tuple containing the beginning and end of the portion of the array we'd
        like to plot as percentages.

        """

        if speed is None:
            speed = np.array([30] * self.get_driving_time_divisions())

        # Used by the optimization function as it passes values as keyword arguments instead of a numpy array
        if kwargs:
            speed = np.fromiter(kwargs.values(), dtype=float)

            # Don't plot results since this code is run by the optimizer
            plot_results = False
            verbose = False

        if not kwargs:
            print(f"Input speeds: {speed}\n")
        assert len(speed) == self.get_driving_time_divisions(), ("Input driving speeds array must have length equal to "
                                                                 "get_driving_time_divisions()! Current length is "
                                                                 f"{len(speed)} and length of "
                                                                 f"{self.get_driving_time_divisions()} is needed!")

        # ----- Reshape speed array -----
        speed_kmh = helpers.reshape_speed_array(self.start_hour, self.simulation_duration, self.race_type,
                                                speed, self.granularity, self.tick)

        # ----- Preserve raw speed -----
        raw_speed = speed_kmh.copy()

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
                                               "solar_irradiances", "wind_speeds",
                                               "gis_route_elevations_at_each_tick",
                                               "cloud_covers", "raw_soc"]) + [raw_speed]
            results_labels = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                              "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)",
                              "Cloud cover (%)", "Raw SOC (%)", "Raw Speed (km/h)"]

            self.plotting.add_graph_page_to_queue(GraphPage(results_arrays, results_labels, page_name="Results"))

            if verbose:
                # Plot energy arrays
                energy_arrays = self.get_results(["motor_consumed_energy", "array_produced_energy", "delta_energy"])
                energy_labels = ["Motor Consumed Energy (J)", "Array Produced Energy (J)", "Delta Energy (J)"]
                energy_graph = GraphPage(energy_arrays, energy_labels, page_name="Energy Calculations")
                self.plotting.add_graph_page_to_queue(energy_graph)

                # Plot indices and environment arrays
                env_arrays = self.get_results(["temp", "closest_gis_indices", "closest_weather_indices",
                                               "gradients", "time_zones", "gis_vehicle_bearings"])
                env_labels = ["speed dist (m)", "gis ind", "weather ind",
                              "gradients (m)", "time zones", "vehicle bearings"]
                indices_and_environment_graph = GraphPage(env_arrays, env_labels, page_name="Indices and Environment")
                self.plotting.add_graph_page_to_queue(indices_and_environment_graph)

                # Plot speed boolean and SOC arrays
                arrays_to_plot = self.get_results(["speed_kmh", "state_of_charge"])
                logical_arrays = []
                for arr in arrays_to_plot:
                    speed_kmh = arrays_to_plot[0]
                    speed_kmh = np.logical_and(speed_kmh, arr) * speed_kmh
                    logical_arrays.append(speed_kmh)

                boolean_arrays = arrays_to_plot + logical_arrays
                boolean_labels = ["Speed (km/h)", "SOC", "Speed & SOC", "Speed & not_charge"]
                boolean_graph = GraphPage(boolean_arrays, boolean_labels, page_name="Speed Boolean Operations")
                self.plotting.add_graph_page_to_queue(boolean_graph)

            self.plotting.plot_graph_pages(self.get_results("timestamps"), plot_portion=plot_portion)

        if route_visualization:
            if self.race_type == "FSGP":
                helpers.route_visualization(self.gis.single_lap_path, visible=route_visualization)
            elif self.race_type == "ASC":
                helpers.route_visualization(self.gis.path, visible=route_visualization)

        get_return_type = {
            SimulationReturnType.time_taken: -1 * results[0],
            SimulationReturnType.distance_travelled: results[2],
            SimulationReturnType.distance_and_time: (results[2], results[0]),
            SimulationReturnType.void: None
        }

        return get_return_type[self.return_type]

    def calculations_have_happened(self):
        return self._model.calculations_have_happened

    @simulation_property
    def get_results(self, values: Union[np.ndarray, list, tuple, set, str]) -> Union[list, np.ndarray, float]:
        """

        Use this function to extract data from a Simulation model.
        For example, input ["speed_kmh","delta_energy"] to extract speed_kmh and delta_energy. Use
        "default" to extract the properties that used to be in the SimulationResults object.

        :param values: an iterable of strings that should correspond to a certain property of simulation.
        :returns: a list of Simulation properties in the order provided.
        :rtype: list

        """

        return self._model.get_results(values)

    @simulation_property
    def was_successful(self):
        state_of_charge = self.get_results("state_of_charge")
        if np.min(np.abs(state_of_charge)) < 1e-03:
            return False
        return True

    @simulation_property
    def get_distance_before_exhaustion(self):
        state_of_charge, distances = self.get_results(["state_of_charge", "distances"])
        index = np.argmax(np.abs(state_of_charge) < 1e-03)
        return distances[index]

    def get_driving_time_divisions(self) -> int:
        """

        Returns the number of time divisions (based on granularity) that the car is permitted to be driving.
        Dependent on rules in get_race_timing_constraints_boolean() function in common/helpers.

        :return: number of hours as an integer

        """

        return helpers.get_race_timing_constraints_boolean(self.start_hour, self.simulation_duration,
                                                           self.race_type, self.granularity,
                                                           as_seconds=False).sum().astype(int)

    def get_race_length(self):
        try:
            value = self.get_results("max_route_distance")
        except simulation.PrematureDataRecoveryError:
            speed_kmh = np.array([30] * self.get_driving_time_divisions())
            if self._model is None:
                self._model = simulation.Model(self, speed_kmh)
            self._model.run_simulation_calculations()
            value = self.get_results("max_route_distance")

        return value
