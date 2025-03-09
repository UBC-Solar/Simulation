import functools
import core
import numpy as np

from typing import Union
from numpy.typing import NDArray

from simulation.common import helpers
from simulation.utils.Plotting import GraphPage
from simulation.common.exceptions import PrematureDataRecoveryError
from simulation.utils.Plotting import Plotting
from simulation.model.Simulation import Simulation
from simulation.common.race import Race
from simulation.config import SimulationReturnType

from physics.models.arrays import BaseArray
from physics.models.battery import BaseBattery
from physics.models.lvs import BaseLVS
from physics.models.motor import BaseMotor
from physics.models.regen import BaseRegen

from physics.environment.gis import BaseGIS
from physics.environment.meteorology import BaseMeteorology


def simulation_property(func):
    """

    Apply this decorator to all functions that intend to get data from a Simulation model.
    This protects the data from being pulled from Simulation before the model has been simulated.

    :param func: function that will be used to get data

    """

    @functools.wraps(func)
    def property_wrapper(*args, **kwargs):
        assert isinstance(args[0], Model), "simulation_property wrapper applied to non-Simulation function!"
        if not args[0].calculations_have_happened():
            raise PrematureDataRecoveryError("You are attempting to collect information before simulation "
                                             "model calculations have completed.")
        value = func(*args, **kwargs)
        return value

    return property_wrapper


class Model:
    """

    Note: The first time that run_model is called will be SIGNIFICANTLY slower than future calls. This is because
    Simulation components contain many Numba JIT targets, which must be compiled at runtime the first time they are
    called.
    """

    def __init__(
            self,
            return_type: SimulationReturnType,
            race: Race,
            speed_dt: int,
            simulation_dt: int,
            speed_limits: NDArray,
            array: BaseArray,
            battery: BaseBattery,
            motor: BaseMotor,
            regen: BaseRegen,
            lvs: BaseLVS,
            gis: BaseGIS,
            meteorology: BaseMeteorology,
            max_acceleration: float,
            max_deceleration: float,
            start_time: int
    ):
        """

        Instantiates a simple model of the car.

        Do NOT call this constructor directly. Please create a SimulationBuilder and use
        SimulationBuilder.get() after setting parameters and initial conditions.

        :param builder: a SimulationBuilder object that provides settings for the Simulation

        """
        self.return_type = return_type
        self.race = race
        self.speed_limits = speed_limits
        self.speed_dt = speed_dt
        self.simulation_dt = simulation_dt
        self.solar_array = array
        self.motor = motor
        self.regen = regen
        self.battery = battery
        self.gis = gis
        self.meteorology = meteorology
        self.lvs = lvs
        self.max_acceleration = max_acceleration
        self.max_deceleration = max_deceleration
        self.start_time = start_time

        self.time_of_initialization = self.meteorology.last_updated_time  # Real Time

        self.simulation_duration = race.race_duration - self.start_time

        self.vehicle_bearings = self.gis.calculate_current_heading_array()
        self.route_coords = self.gis.get_path()

        self.plotting = Plotting()

        # All attributes ABOVE will NOT be modified when the model is simulated. All attributes BELOW this WILL be
        # mutated over the course of simulation. Ensure that when you modify the behaviour of Simulation that this
        # fact is maintained, else the stability of the optimization process WILL be threatened, as it assumes
        # that the attributes above are independent of whether the model has been previously simulated.

        # A Model is a (mostly) immutable container for simulation calculations and results
        self._model = None

    def run_model(self, speed=None, plot_results=False, verbose=False,
                  route_visualization=False, plot_portion=(0.0, 1.0), is_optimizer: bool = False, **kwargs):
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
        :param bool plot_results: set to True to plot the results of the simulation
        :param bool verbose: Boolean to control logging and debugging behaviour
        :param bool route_visualization: Flag to control route_visualization plot visibility
        :param tuple[float] plot_portion: A tuple containing the beginning and end of the portion of the array we'd
        like to plot, as percentages (0 <= plot_portion <= 1).
        :param kwargs: variable list of arguments that specify the car's driving speed at each time step.
            Overrides the speed parameter.
        :param plot_portion: A tuple containing the beginning and end of the portion of the array we'd
        like to plot as percentages.
        :param bool is_optimizer: flag to set whether this method is being run by an optimizer. Reduces verbosity
            when true.
        """

        if speed is None:
            speed = np.array([30] * self.get_driving_time_divisions())

        # Used by the optimization function as it passes values as keyword arguments instead of a numpy array
        if kwargs or is_optimizer:
            if kwargs:
                speed = np.fromiter(kwargs.values(), dtype=float)

            # Don't plot results since this code is run by the optimizer
            plot_results = False
            verbose = False

        assert len(speed) == self.get_driving_time_divisions(), ("Input driving speeds array must have length equal to "
                                                                 "get_driving_time_divisions()! Current length is "
                                                                 f"{len(speed)} and length of "
                                                                 f"{self.get_driving_time_divisions()} is needed!")

        # ----- Reshape speed array -----
        speed_kmh = helpers.reshape_speed_array(self.race, speed, self.speed_dt, self.start_time, self.simulation_dt, self.max_acceleration, self.max_deceleration)

        # ----- Preserve raw speed -----
        raw_speed = speed_kmh.copy()
        # speed_kmh = core.constrain_speeds(self.speed_limits.astype(float), speed_kmh, self.simulation_dt)

        # ------ Run calculations and get result and modified speed array -------
        self._model = Simulation(self, speed_kmh)
        self._model.run_simulation_calculations()

        results = self.get_results(["time_taken", "route_length", "distance_travelled", "speed_kmh", "final_soc"])

        if not kwargs and not is_optimizer:
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
                                               "raw_soc"]) + [raw_speed]
            results_labels = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                              "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)",
                              "Raw SOC (%)", "Raw Speed (km/h)"]

            self.plotting.add_graph_page_to_queue(GraphPage(results_arrays, results_labels, page_name="Results"))

            if verbose:
                # Plot energy arrays
                energy_arrays = self.get_results(["motor_consumed_energy", "array_produced_energy", "delta_energy"])
                energy_labels = ["Motor Consumed Energy (J)", "Array Produced Energy (J)", "Delta Energy (J)"]
                energy_graph = GraphPage(energy_arrays, energy_labels, page_name="Energy Calculations")
                self.plotting.add_graph_page_to_queue(energy_graph)

                # Plot indices and environment arrays
                env_arrays = self.get_results(["closest_gis_indices", "closest_weather_indices",
                                               "gradients", "time_zones", "gis_vehicle_bearings"])
                env_labels = ["gis ind", "weather ind",
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
        if np.min(state_of_charge) < 0.0:
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

        return helpers.get_granularity_reduced_boolean(self.race.driving_boolean[self.start_time:],
                                                       self.speed_dt).sum().astype(int)

    def get_race_length(self):
        try:
            value = self.get_results("max_route_distance")
        except PrematureDataRecoveryError:
            speed_kmh = np.array([30] * self.get_driving_time_divisions())
            if self._model is None:
                self._model = Model(self, speed_kmh)
            self._model.run_simulation_calculations()
            value = self.get_results("max_route_distance")

        return value
