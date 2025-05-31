import numpy as np

from typing import Union
from numpy.typing import NDArray

from simulation.utils.Plotting import GraphPage
from simulation.utils.Plotting import Plotting
from simulation.model.Simulation import Simulation
from simulation.race import Race, reshape_speed_array, get_granularity_reduced_boolean
from simulation.config import SimulationReturnType

from physics.models.arrays import BaseArray
from physics.models.battery import BaseBattery
from physics.models.lvs import BaseLVS
from physics.models.motor import BaseMotor
from physics.models.regen import BaseRegen
from physics.environment.gis import BaseGIS
from physics.environment.meteorology import BaseMeteorology


class Model:
    """
    A `Model` is a comprehensive model of a solar-powered vehicle's components within a fully qualified environment,
    ready for simulation given an input of driving speeds for the vehicle to perform.
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
        start_time: int,
        num_laps: int
    ):
        """
        Instantiate a `Model`.

        :param SimulationReturnType return_type: Specify the data that should be directly returned by `run_model`.
        :param Race race: A `Race` instance that contains all the data about the race to be simulated.
        :param int speed_dt: The number of seconds that each element of the input speed array should represent.
        :param int simulation_dt: The time discretization of this model's simulations, in seconds.
        :param NDArray speed_limits: An array of speed limits in km/h for each coordinate that will be simulated.
        :param BaseArray array: An instance of `BaseArray` representing the solar array to be simulated.
        :param BaseBattery battery: An instance of `BaseBattery` representing the batter pack to be simulated.
        :param BaseMotor motor: An instance of `BaseMotor` representing the motor to be simulated.
        :param BaseRegen regen: An instance of `BaseRegen` representing the regenerative braking system to be simulated.
        :param BaseLVS lvs: An instance of `BaseLVS` representing the low-voltage systems to be simulated.
        :param BaseGIS gis: An instance of `BaseGIS` which characterizes geographical information about the simulation.
        :param BaseMeteorology meteorology: An instance of `BaseMeteorology` describing the meteorology to be simulated.
        :param float max_acceleration: Maximum allowed acceleration of the car in km/h.
        :param float max_deceleration: Maximum allowed deceleration of the car in km/h.
        :param int start_time: The initial time, in seconds since midnight of the first day, of the simulation.
        :param int num_laps: The number of laps that we are simulating/optimizing
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
        self.num_laps = num_laps

        self.time_of_initialization = self.meteorology.last_updated_time  # Real Time

        self.simulation_duration = race.race_duration - self.start_time

        self.vehicle_bearings = self.gis.calculate_current_heading_array()
        self.route_coords = self.gis.get_path()

        self.plotting = Plotting()

        # NOTE: All attributes ABOVE this comment should be IMMUTABLE and UNMODIFIED during a simulation.

        self._simulation = None

    def run_model(
        self,
        speed=None,
        plot_results=False,
        verbose=False,
        plot_portion=(0.0, 1.0),
        is_optimizer: bool = False,
        **kwargs,
    ):
        """

        Given an array of driving speeds, simulate the model by running calculations sequentially for the entire
        simulation duration.
        Returns either time taken, distance travelled, or void.

        This function is mostly a wrapper
        around `run_simulation_calculations`,
        which is where the magic happens, that deals with processing the driving
        speeds array as well as plotting and handling the calculation results.

        Note: if the speed remains constant throughout this update, knowing the starting
              time, the cumulative distance at every time can be known.
              From the cumulative
              distance, the GIS class updates the new location of the vehicle.
              From the location
              of the vehicle at every tick, the gradients at every tick, the weather at every
              tick, the GHI at every tick, is known.

        Note 2: currently, the simulation can only be run for times during which weather data is available

        :param np.ndarray speed: Array that specifies the solar car's avg driving speed per lap.
        :param bool plot_results: Set to True to plot the results of the simulation.
        :param bool verbose: Boolean to control logging and debugging behaviour.
        :param tuple[float] plot_portion: A tuple containing the beginning and end of the portion of the array we'd
        like to plot, as percentages (0 <= plot_portion <= 1).
        :param kwargs: Variable list of arguments that specify the car's driving speed at each time step.
            Overrides the speed parameter.
        :param plot_portion: A tuple containing the beginning and end of the portion of the array we'd
        like to plot as percentages.
        :param bool is_optimizer: Flag to set whether this method is being run by an optimizer.
        Reduces verbosity
            when true.
        """
        # We want to check that the speed array has at least as many elements as the number of laps we want to simulate
        assert len(speed) >= self.num_laps, (
            "Input driving speeds array must have length greater than or "
            "equal to self.num_laps! Current length is "
            f"{len(speed)} and length of {self.num_laps} is needed!"
        )

        # ----- Reshape speed array -----
        speed_kmh = reshape_speed_array(
            self.race,
            speed,
            self.speed_dt,
            self.start_time,
            self.simulation_dt,
            self.max_acceleration,
            self.max_deceleration,
        )

        # ----- Preserve raw speed -----
        raw_speed = speed_kmh.copy()
        # speed_kmh = core.constrain_speeds(self.speed_limits.astype(float), speed_kmh, self.simulation_dt)

        # ------ Run calculations and get result and modified speed array -------
        self._simulation = Simulation(self)
        self._simulation.run_simulation_calculations(speed_kmh)

        results = self.get_results(
            [
                "time_taken",
                "route_length",
                "distance_travelled",
                "speed_kmh",
                "final_soc",
            ]
        )

        if not kwargs and not is_optimizer:
            print(
                f"Simulation successful!\n"
                f"Time taken: {results[0]}\n"
                f"Route length: {results[1]:.2f}km\n"
                f"Maximum distance traversable: {results[2]:.2f}km\n"
                f"Average speed: {np.average(results[3]):.2f}km/h\n"
                f"Final battery SOC: {results[4]:.2f}%\n"
            )

        # ----- Plotting -----
        if plot_results:
            results_arrays = self.get_results(
                [
                    "speed_kmh",
                    "distances",
                    "state_of_charge",
                    "delta_energy",
                    "solar_irradiances",
                    "wind_speeds",
                    "gis_route_elevations_at_each_tick",
                    "raw_soc",
                ]
            ) + [raw_speed]
            results_labels = [
                "Speed (km/h)",
                "Distance (km)",
                "SOC (%)",
                "Delta energy (J)",
                "Solar irradiance (W/m^2)",
                "Wind speeds (km/h)",
                "Elevation (m)",
                "Raw SOC (%)",
                "Raw Speed (km/h)",
            ]

            self.plotting.add_graph_page_to_queue(
                GraphPage(results_arrays, results_labels, page_name="Results")
            )

            if verbose:
                # Plot energy arrays
                energy_arrays = self.get_results(
                    ["motor_consumed_energy", "array_produced_energy", "delta_energy"]
                )
                energy_labels = [
                    "Motor Consumed Energy (J)",
                    "Array Produced Energy (J)",
                    "Delta Energy (J)",
                ]
                energy_graph = GraphPage(
                    energy_arrays, energy_labels, page_name="Energy Calculations"
                )
                self.plotting.add_graph_page_to_queue(energy_graph)

                # Plot indices and environment arrays
                env_arrays = self.get_results(
                    [
                        "closest_gis_indices",
                        "closest_weather_indices",
                        "gradients",
                        "time_zones",
                        "gis_vehicle_bearings",
                    ]
                )
                env_labels = [
                    "gis ind",
                    "weather ind",
                    "gradients (m)",
                    "time zones",
                    "vehicle bearings",
                ]
                indices_and_environment_graph = GraphPage(
                    env_arrays, env_labels, page_name="Indices and Environment"
                )
                self.plotting.add_graph_page_to_queue(indices_and_environment_graph)

                # Plot speed boolean and SOC arrays
                arrays_to_plot = self.get_results(["speed_kmh", "state_of_charge"])
                logical_arrays = []
                for arr in arrays_to_plot:
                    speed_kmh = arrays_to_plot[0]
                    speed_kmh = np.logical_and(speed_kmh, arr) * speed_kmh
                    logical_arrays.append(speed_kmh)

                boolean_arrays = arrays_to_plot + logical_arrays
                boolean_labels = [
                    "Speed (km/h)",
                    "SOC",
                    "Speed & SOC",
                    "Speed & not_charge",
                ]
                boolean_graph = GraphPage(
                    boolean_arrays, boolean_labels, page_name="Speed Boolean Operations"
                )
                self.plotting.add_graph_page_to_queue(boolean_graph)

            self.plotting.plot_graph_pages(
                self.get_results("timestamps"), plot_portion=plot_portion
            )

        get_return_type = {
            SimulationReturnType.time_taken: -1 * results[0],
            SimulationReturnType.distance_travelled: results[2],
            SimulationReturnType.distance_and_time: (results[2], results[0]),
            SimulationReturnType.void: None,
        }

        return get_return_type[self.return_type]

    def calculations_have_happened(self):
        return self._simulation.calculations_have_happened

    def get_results(
        self, values: Union[np.ndarray, list, tuple, set, str]
    ) -> Union[list, np.ndarray, float]:
        """

        Use this function to extract data from a Simulation model.
        For example, input ["speed_kmh","delta_energy"] to extract speed_kmh and delta_energy. Use
        "default" to extract the properties that used to be in the SimulationResults object.

        :param values: An iterable of strings that should correspond to a certain property of simulation.
        :returns: A list of Simulation properties in the order provided.
        """

        return self._simulation.get_results(values)

    def was_successful(self):
        state_of_charge = self.get_results("state_of_charge")
        if np.min(state_of_charge) < 0.0:
            return False
        return True

    def get_distance_before_exhaustion(self):
        state_of_charge, distances = self.get_results(["state_of_charge", "distances"])
        index = np.argmax(np.abs(state_of_charge) < 1e-03)
        return distances[index]

    def get_driving_time_divisions(self) -> int:
        """

        Returns the number of time divisions (based on granularity) that the car is permitted to be driving.
        Dependent on rules in get_race_timing_constraints_boolean() function in common/helpers.

        :return: Number of hours as an integer

        """

        return (
            get_granularity_reduced_boolean(
                self.race.driving_boolean[self.start_time :], self.speed_dt
            )
            .sum()
            .astype(int)
        )
