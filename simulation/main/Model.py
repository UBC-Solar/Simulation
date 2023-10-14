"""
Contain calculations and results of Simulation.
"""

import numpy as np

from typing import Union
from simulation.common import helpers

Iterable = Union[np.ndarray, list, set, tuple]


class Model:
    """
    Models should be considered to be immutable. Instantiate a new model when you want to run a different simulation.
    """

    def __init__(self, simulation, speed_kmh):
        self.simulation = simulation
        self.speed_kmh = speed_kmh

        self.calculations_have_happened = False

        # --------- Results ---------

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

        self.timestamps = None
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
        self.regen_produced_energy = None
        self.raw_soc = None
        self.not_charge = None
        self.consumed_energy = None
        self.produced_energy = None
        self.time_in_motion = None
        self.final_soc = None
        self.map_data_indices = None

    def run_simulation_calculations(self) -> None:
        """

        Simulate the model by sequentially running calculations for the entire simulation duration at once.

        To begin, we use the driving speeds array to obtain the theoretical position of the car at every tick.
        Then, we map the position of the car at every tick to a GIS coordinate and to a Weather coordinate. Next,
        we use the GIS coordinates to calculate gradients, vehicle bearings, and we also determine the time in which we
        arrive at each position. Then, we use the time and Weather coordinate to map each tick to a weather
        forecast. From the weather, we can calculate wind speeds, cloud cover, and estimate solar irradiance.
        From the aforementioned calculations, we can determine the energy needed for the motor, and the energy
        that the solar arrays will collect; from those two, we can determine the delta energy at every tick.
        Then, we use the delta energy to determine how much energy we are drawing or storing from/into the battery
        which allows us to determine the battery's state of charge for the entire simulation duration.

        """

        # ----- Tick array -----

        self.timestamps = np.arange(0, self.simulation.simulation_duration + self.simulation.tick, self.simulation.tick)
        self.tick_array = np.diff(self.timestamps)
        self.tick_array = np.insert(self.tick_array, 0, 0)

        # ----- Expected distance estimate -----

        # Array of cumulative distances theoretically achievable via the speed array
        self.distances = self.tick_array * self.speed_kmh / 3.6
        self.cumulative_distances = np.cumsum(self.distances)

        self.temp = self.cumulative_distances

        # ----- Weather and location calculations -----

        """ closest_gis_indices is a 1:1 mapping between each point which has within it a timestamp and cumulative
                distance from a starting point, to its closest point on a map.

            closest_weather_indices is a 1:1 mapping between a weather condition, and its closest point on a map.
        """

        self.closest_gis_indices = self.simulation.gis.calculate_closest_gis_indices(self.cumulative_distances)

        self.closest_weather_indices = self.simulation.weather.calculate_closest_weather_indices(
            self.cumulative_distances)

        self.path_distances = self.simulation.gis.path_distances
        self.cumulative_distances = np.cumsum(self.path_distances)  # [cumulative_distances] = meters

        self.max_route_distance = self.cumulative_distances[-1]

        self.route_length = self.max_route_distance / 1000.0  # store the route length in kilometers

        # Array of elevations at every route point
        gis_route_elevations = self.simulation.gis.get_path_elevations()

        self.gis_route_elevations_at_each_tick = gis_route_elevations[self.closest_gis_indices]

        # Get the azimuth angle of the vehicle at every location
        self.gis_vehicle_bearings = self.simulation.vehicle_bearings[self.closest_gis_indices]

        # Get array of path gradients
        self.gradients = self.simulation.gis.get_gradients(self.closest_gis_indices)

        # ----- Timing Calculations -----

        # Get time zones at each point on the GIS path
        self.time_zones = self.simulation.gis.get_time_zones(self.closest_gis_indices)

        # Local times in UNIX timestamps
        local_times = helpers.adjust_timestamps_to_local_times(self.timestamps,
                                                               self.simulation.time_of_initialization,
                                                               self.time_zones)

        # Get the weather at every location
        weather_forecasts = self.simulation.weather.get_weather_forecast_in_time(self.closest_weather_indices,
                                                                                 local_times)
        roll_by_tick = int(3600 / self.simulation.tick) * (24 + self.simulation.start_hour - helpers.hour_from_unix_timestamp(weather_forecasts[0, 2]))
        weather_forecasts = np.roll(weather_forecasts, -roll_by_tick, 0)

        absolute_wind_speeds = weather_forecasts[:, 5]
        self.wind_directions = weather_forecasts[:, 6]
        self.cloud_covers = weather_forecasts[:, 7]

        # Get the wind speeds at every location
        self.wind_speeds = helpers.get_array_directional_wind_speed(self.gis_vehicle_bearings,
                                                                    absolute_wind_speeds,
                                                                    self.wind_directions)

        # Get an array of solar irradiance at every coordinate and time
        self.solar_irradiances = self.simulation.solar_calculations.calculate_array_GHI(
            self.simulation.route_coords[self.closest_gis_indices],
            self.time_zones, local_times,
            self.gis_route_elevations_at_each_tick,
            self.cloud_covers)

        # TLDR: we have now obtained solar irradiances, wind speeds, and gradients at each tick

        # ----- Energy Calculations -----

        self.simulation.basic_lvs.update(self.simulation.tick)

        self.lvs_consumed_energy = self.simulation.basic_lvs.get_consumed_energy()
        self.motor_consumed_energy = self.simulation.basic_motor.calculate_energy_in(self.speed_kmh,
                                                                                     self.gradients,
                                                                                     self.wind_speeds,
                                                                                     self.simulation.tick)
        self.array_produced_energy = self.simulation.basic_array.calculate_produced_energy(self.solar_irradiances,
                                                                                           self.simulation.tick)

        self.regen_produced_energy = self.simulation.basic_regen.calculate_produced_energy(self.speed_kmh,
                                                                                           self.gis_route_elevations_at_each_tick)

        self.not_charge = helpers.get_charge_timing_constraints_boolean(start_hour=self.simulation.start_hour,
                                                                        simulation_duration=self.simulation.
                                                                        simulation_duration,
                                                                        race_type=self.simulation.race_type)[:self.simulation.simulation_duration + 1]
        if self.simulation.tick != 1:
            self.not_charge = self.not_charge[::self.simulation.tick]

        self.array_produced_energy = np.logical_and(self.array_produced_energy,
                                                    self.not_charge) * self.array_produced_energy

        self.consumed_energy = self.motor_consumed_energy + self.lvs_consumed_energy
        self.produced_energy = self.array_produced_energy + self.regen_produced_energy

        # net energy added to the battery
        self.delta_energy = self.produced_energy - self.consumed_energy

        # ----- Array initialisation -----

        # used to calculate the time the car was in motion
        self.tick_array = np.full_like(self.timestamps, fill_value=self.simulation.tick, dtype='f4')
        self.tick_array[0] = 0

        # ----- Array calculations -----

        cumulative_delta_energy = np.cumsum(self.delta_energy)
        battery_variables_array = self.simulation.basic_battery.update_array(cumulative_delta_energy)

        # stores the battery SOC at each time step
        self.state_of_charge = battery_variables_array[0]
        self.state_of_charge[np.abs(self.state_of_charge) < 1e-03] = 0
        self.raw_soc = self.simulation.basic_battery.get_raw_soc(np.cumsum(self.delta_energy))

        # This functionality may want to be removed in the future (speed array gets mangled when SOC <= 0)
        self.speed_kmh = np.logical_and(self.not_charge, self.state_of_charge) * self.speed_kmh

        self.time_in_motion = np.logical_and(self.tick_array, self.speed_kmh) * self.simulation.tick

        self.final_soc = self.state_of_charge[-1] * 100 + 0.

        self.distance = self.speed_kmh * (self.time_in_motion / 3600)
        self.distances = np.cumsum(self.distance)

        # Car cannot exceed Max distance, and it is not in motion after exceeded
        self.distances = self.distances.clip(0, self.max_route_distance / 1000)

        self.map_data_indices = helpers.get_map_data_indices(self.closest_gis_indices)

        self.distance_travelled = self.distances[-1]

        if self.distance_travelled >= self.route_length:
            self.time_taken = self.timestamps[helpers.calculate_completion_index(self.route_length, self.distances)]
        else:
            self.time_taken = self.simulation.simulation_duration

        self.calculations_have_happened = True

    def get_results(self, requested_properties: Union[Iterable, str]) -> Union[list, np.ndarray, float]:
        """

        Extract data from a Simulation model.

        For example, input ["speed_kmh","delta_energy"] to extract speed_kmh and delta_energy. Use
        "default" to extract the properties that used to be in the deprecated SimulationResults object.

        Note: Multiple properties are returned as a list. If a single property is requested, it will be returned
        without being wrapped in a list.

        Valid Keywords:
            speed_kmh, distances, state_of_charge, delta_energy, solar_irradiances, wind_speeds,
            gis_route_elevations_at_each_tick, cloud_covers, distance, route_length, time_taken,
            tick_array, timestamps, time_zones, cumulative_distances, temp, closest_gis_indices,
            closest_weather_indices, path_distances, max_route_distance, gis_vehicle_bearings,
            gradients, absolute_wind_speeds, wind_directions, lvs_consumed_energy, motor_consumed_energy,
            array_produced_energy, not_charge, consumed_energy, produced_energy, time_in_motion, final_soc,
            distance_travelled, map_data_indices, path_coordinates, raw_soc

        :param requested_properties: an iterable of strings, or a single string equal to a valid keyword.
        :returns: the Simulation properties requested, in the order provided.
        :rtype: Union[list, np.ndarray, float]

        """

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
            "timestamps": self.timestamps,
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
            "regen_produced_energy": self.regen_produced_energy,
            "not_charge": self.not_charge,
            "consumed_energy": self.consumed_energy,
            "produced_energy": self.produced_energy,
            "time_in_motion": self.time_in_motion,
            "final_soc": self.final_soc,
            "distance_travelled": self.distance_travelled,
            "map_data_indices": self.map_data_indices,
            "path_coordinates": self.simulation.gis.get_path(),
            "raw_soc": self.raw_soc
        }

        if "default" in requested_properties or requested_properties == "default":
            # If just "default" was provided, replace values with a list containing the default values
            if isinstance(requested_properties, str):
                requested_properties = ["speed_kmh", "distances", "state_of_charge", "delta_energy",
                                        "solar_irradiances",
                                        "wind_speeds", "gis_route_elevations_at_each_tick", "cloud_covers",
                                        "distance_travelled", "time_taken", "final_soc"]
            else:
                # If default was instead an element in a list of requested properties, insert the default properties
                # where "default" is in the request
                default_index = requested_properties.index("default")
                requested_properties.pop(default_index)
                default_values = ["speed_kmh", "distances", "state_of_charge", "delta_energy", "solar_irradiances",
                                  "wind_speeds", "gis_route_elevations_at_each_tick", "cloud_covers",
                                  "distance_travelled", "time_taken", "final_soc"]
                for index, default_value in enumerate(default_values):
                    if default_value not in requested_properties:
                        requested_properties.insert(index + default_index, default_value)

        # If just a single value was requested, return it without wrapping it in a list
        if isinstance(requested_properties, str) and requested_properties != "default":
            return simulation_results[requested_properties]

        results = []
        for value in requested_properties:
            results.append(simulation_results[value])
        return results
