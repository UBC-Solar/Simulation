import sys
import datetime
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from simulation.common import helpers
from simulation.simulation_types import *
import numpy as np


class ASC_Simulation(BaseSimulation):
    """
    Instantiates a simple model of the car.

    Fields
    :origin_coord: array containing latitude and longitude of route start point
    :waypoints: array containing latitude and longitude pairs of route waypoints
    :dest_coord: array containing latitude and longitude of route end point
    :param simulation_duration: length of simulated time (in seconds)
    :param input_speed:
    :param start_hour:

    """
    def __init__(self, input_speed, start_hour, simulation_duration):
        super().__init__()

        # ----- Route Definition -----
        self.origin_coord = np.array([39.0918, -94.4172])

        self.waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                                   [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                                   [42.3224, -111.2973], [42.5840, -114.4703]])

        self.dest_coord = np.array([43.6142, -116.2080])

        self.input_speed = input_speed

        # ----- Race-Specific Timing Constants -----

        self.simulation_duration = simulation_duration
        self.start_hour = start_hour

        # ----- Configure
        self.configure_race("ASC")

    def run_model(self, plot_results=True):
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

        note 2: currently, the simulation can only be run for times during which weather data is available

        :param plot_results: set to True to plot the results of the simulation (is True by default)
        """

        # ----- Reshape speed array -----

        print(f"Input speeds: {self.input_speed}\n")

        speed_kmh = helpers.reshape_and_repeat(self.input_speed, self.simulation_duration)
        speed_kmh = np.insert(speed_kmh, 0, 0)

        # ----- Expected distance estimate -----

        # Array of cumulative distances hopefully travelled in this round
        timestamps = np.arange(0, self.simulation_duration + self.tick, self.tick)
        tick_array = np.diff(timestamps)
        tick_array = np.insert(tick_array, 0, 0)

        # Array of cumulative distances obtained from the timestamps

        distances = tick_array * speed_kmh / 3.6
        cumulative_distances = np.cumsum(distances)

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

        # Array of elevations at every route point
        gis_route_elevations = self.gis.get_path_elevations()
        gis_route_elevations_at_each_tick = gis_route_elevations[closest_gis_indices]

        # Get the azimuth angle of the vehicle at every location
        gis_vehicle_bearings = self.vehicle_bearings[closest_gis_indices]

        # Get array of path gradients
        gradients = self.gis.get_gradients(closest_gis_indices)

        # Get time zones at each point on the GIS path
        time_zones = self.gis.get_time_zones(closest_gis_indices)

        # Local times in UNIX timestamps
        local_times = self.gis.adjust_timestamps_to_local_times(timestamps, self.time_of_initialization, time_zones)

        # time_of_day_hour based of UNIX timestamps
        time_of_day_hour = np.array([helpers.hour_from_unix_timestamp(ti) for ti in local_times])

        # Get the weather at every location
        weather_forecasts = self.weather.get_weather_forecast_in_time(closest_weather_indices, local_times)
        roll_by_tick = 3600 * (24 + self.start_hour - helpers.hour_from_unix_timestamp(weather_forecasts[0, 2]))
        # weather_forecasts = np.lib.pad(weather_forecasts[roll_by_tick:, :], ((0, roll_by_tick), (0, 0)), 'constant', constant_values = (0))
        weather_forecasts = np.roll(weather_forecasts, -roll_by_tick, 0)
        absolute_wind_speeds = weather_forecasts[:, 5]
        wind_directions = weather_forecasts[:, 6]
        cloud_covers = weather_forecasts[:, 7]

        # Get the wind speeds at every location
        wind_speeds = self.weather.get_array_directional_wind_speed(gis_vehicle_bearings, absolute_wind_speeds,
                                                                    wind_directions)

        # Get an array of solar irradiance at every coordinate and time
        solar_irradiances = self.solar_calculations.calculate_array_GHI(self.route_coords[closest_gis_indices],
                                                                        time_zones, local_times,
                                                                        gis_route_elevations[closest_gis_indices],
                                                                        cloud_covers)

        # TLDR: we have now obtained solar irradiances, wind speeds, and gradients at each tick

        # Implementing day start/end charging (Charge from 7am-9am and 6pm-8pm) for ASC and
        # (Charge from 8am-9am and 6pm-8pm) for FSGP
        # Ensuring Car does not move at night
        bool_lis = []
        night_lis = []
        # if self.race_type == "FSGP":
        #     bool_lis = [time_of_day_hour == 10, time_of_day_hour == 8, time_of_day_hour == 18, time_of_day_hour == 19]
        #     for time in list(range(20, 24)) + list(range(0, 8)):
        #         night_lis.append(time_of_day_hour == time)
        # elif self.race_type == "ASC":
        bool_lis = [time_of_day_hour == 7, time_of_day_hour == 8, time_of_day_hour == 18, time_of_day_hour == 19]
        for time in list(range(20, 24)) + list(range(0, 8)):
            night_lis.append(time_of_day_hour == time)

        not_charge = np.invert(np.logical_or.reduce(bool_lis))
        not_day = np.invert(np.logical_or.reduce(night_lis))

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
        tick_array = np.full_like(timestamps, fill_value=self.tick, dtype='f4')
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
        speed_kmh = np.logical_and(speed_kmh, state_of_charge) * speed_kmh
        speed_kmh = np.logical_and(speed_kmh, not_charge) * speed_kmh
        speed_kmh = np.logical_and(speed_kmh, not_day) * speed_kmh

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

        # ----- Target values -----
        distance_travelled = distances[-1]

        time_taken = np.sum(time_in_motion)
        time_taken = str(datetime.timedelta(seconds=int(time_taken)))

        # TODO: package all the calculated arrays into a SimulationHistory class
        # TODO: have some sort of standardised SimulationResult class

        print(f"Simulation successful!\n"
              f"Time taken: {time_taken}\n"
              f"Maximum distance traversable: {distance_travelled:.2f}km\n"
              f"Average speed: {np.average(speed_kmh):.2f}km/h\n"
              f"Final battery SOC: {final_soc:.2f}%\n")

        # ----- Plotting -----

        if plot_results:
            arrays_to_plot = [speed_kmh, distances, state_of_charge, delta_energy,
                              solar_irradiances, wind_speeds, gis_route_elevations_at_each_tick,
                              cloud_covers]

            compress_constant = int(timestamps.shape[0] / 5000)

            for index, array in enumerate(arrays_to_plot):
                arrays_to_plot[index] = array[::compress_constant]

            y_label = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                       "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)", "Cloud cover (%)"]
            sns.set_style("whitegrid")
            f, axes = plt.subplots(4, 2, figsize=(12, 8))
            f.suptitle("Simulation results", fontsize=16, weight="bold")

            with tqdm(total=len(arrays_to_plot), file=sys.stdout, desc="Plotting data") as pbar:
                for index, axis in enumerate(axes.flatten()):
                    df = pd.DataFrame(dict(time=timestamps[::compress_constant] / 3600, value=arrays_to_plot[index]))
                    g = sns.lineplot(x="time", y="value", data=df, ax=axis)
                    g.set(xlabel="time (hrs)", ylabel=y_label[index])
                    pbar.update(1)
            print()

            sns.despine()
            plt.setp(axes)
            plt.tight_layout()
            plt.show()

        self.local_times = local_times
        self.time_zones = time_zones

        return distance_travelled

    def __str__(self):
        return "ASC"
