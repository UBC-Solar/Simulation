import sys
import simulation
import numpy as np
import datetime
import seaborn as sns
import pandas as pd
from simulation.common import helpers
import matplotlib.pyplot as plt
from tqdm import tqdm
from scipy.optimize import minimize
from bayes_opt import BayesianOptimization


class Simulation:

    def __init__(self, google_api_key, weather_api_key, origin_coord, dest_coord, waypoints, tick, simulation_duration):
        """
        Instantiates a simple model of the car.

        :param google_api_key: API key to access GoogleMaps API
        :param weather_api_key: API key to access OpenWeather API
        :param origin_coord: array containing latitude and longitude of route start point
        :param dest_coord: array containing latitude and longitude of route end point
        :param waypoints: array containing latitude and longitude pairs of route waypoints
        :param tick: length of simulation's discrete time step (in seconds)
        :param simulation_duration: length of simulated time (in seconds)

        """

        # TODO: replace max_speed with a direct calculation taking into account car elevation and wind_speed

        # ----- Simulation constants -----

        self.initial_battery_charge = 1.0

        # LVS power loss is pretty small so it is neglected
        self.lvs_power_loss = 0

        self.max_speed = 104

        # ----- Time constants -----

        self.tick = tick
        self.simulation_duration = simulation_duration

        # ----- API keys -----

        self.google_api_key = google_api_key
        self.weather_api_key = weather_api_key

        # ----- Route constants -----

        self.origin_coord = origin_coord
        self.dest_coord = dest_coord
        self.waypoints = waypoints

        # ----- Component initialisation -----

        self.basic_array = simulation.BasicArray()

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)

        self.basic_lvs = simulation.BasicLVS(self.lvs_power_loss * self.tick)

        self.basic_motor = simulation.BasicMotor()

        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints)
        self.route_coords = self.gis.get_path()
        self.vehicle_bearings = self.gis.calculate_current_heading_array()

        self.weather = simulation.WeatherForecasts(self.weather_api_key, self.route_coords,
                                                   self.simulation_duration / 3600,
                                                   weather_data_frequency="daily")
        self.time_of_initialization = self.weather.last_updated_time

        self.solar_calculations = simulation.SolarCalculations()

        self.local_times = 0
        self.time_zones = 0

    @helpers.timeit
    def run_model(self, speed=np.array([20,20,20,20,20,20,20,20]), plot_results=True, **kwargs):
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
        :param args: variable list of arguments that specify the car's driving speed at each time step. Overrides the speed parameter.
        """

        # This is mainly used by the optimization function since it passes values as keyword arguments instead of a numpy array
        if kwargs:
            speed = np.empty(len(kwargs))

            # Don't plot results since this code is run by the optimizer
            plot_results = False
            for val in kwargs.values():
                speed = np.append(speed, [val])

        # ----- Reshape speed array -----

        print(f"Input speeds: {speed}\n")

        speed_kmh = helpers.reshape_and_repeat(speed, self.simulation_duration)
        speed_kmh = np.insert(speed_kmh, 0, 0)
        speed_kmh = helpers.add_acceleration(speed_kmh, 500)

        # ----- Expected distance estimate -----

        # Array of cumulative distances hopefully travelled in this round
        timestamps = np.arange(0, self.simulation_duration + self.tick, self.tick)
        tick_array = np.diff(timestamps)
        tick_array = np.insert(tick_array, 0, 0)

        # Array of cumulative distances obtained from the timestamps
        # TODO: there needs to be some kind of mechanism that stops the car travelling the max distance
        #   and past the last coordinate in the provided route
        distances = tick_array * speed_kmh / 3.6
        cumulative_distances = np.cumsum(distances)

        # ----- Weather and location calculations -----

        """ closest_gis_indices is a 1:1 mapping between each point which has within it a timestamp and cumulative
                distance from a starting point, to its closest point on a map.

            closest_weather_indices is a 1:1 mapping between a weather condition, and its closest point on a map.
        """

        closest_gis_indices = self.gis.calculate_closest_gis_indices(cumulative_distances)
        closest_weather_indices = self.weather.calculate_closest_weather_indices(cumulative_distances)

        # Array of elevations at every route point
        gis_route_elevations = self.gis.get_path_elevations()
        gis_route_elevations_at_each_tick = gis_route_elevations[closest_gis_indices]

        # Get the azimuth angle of the vehicle at every location
        gis_vehicle_bearings = self.vehicle_bearings[closest_gis_indices]

        # Get array of path gradients
        gradients = self.gis.get_gradients(closest_gis_indices)

        # Get the time zones of all the starting times
        time_zones = self.gis.get_time_zones(closest_gis_indices)

        # Local times in UNIX timestamps
        local_times = self.gis.adjust_timestamps_to_local_times(timestamps, self.time_of_initialization, time_zones)

        # time_of_day_hour based of UNIX timestamps
        time_of_day_hour = np.array([helpers.hour_from_unix_timestamp(ti) for ti in local_times])

        # Implementing day start/end charging (Charge from 7am-9am and 6pm-8pm)
        # charging_hours = [7, 8, 18, 19]

        bool_lis = [time_of_day_hour == 7, time_of_day_hour == 8, time_of_day_hour == 18, time_of_day_hour == 19]
        not_charge = np.invert(np.logical_or.reduce(bool_lis))

        # Get the weather at every location
        weather_forecasts = self.weather.get_weather_forecast_in_time(closest_weather_indices, local_times)
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

        speed_kmh = np.logical_and(speed_kmh, state_of_charge) * speed_kmh
        time_in_motion = np.logical_and(tick_array, state_of_charge) * self.tick
        speed_kmh = np.logical_and(speed_kmh, not_charge) * speed_kmh

        time_taken = np.sum(time_in_motion)
        time_taken = str(datetime.timedelta(seconds=int(time_taken)))

        final_soc = state_of_charge[-1] * 100 + 0.

        # ----- Target value -----

        distance = speed_kmh * (time_in_motion / 3600)

        distance_travelled = np.sum(distance)

        # TODO: package all the calculated arrays into a SimulationHistory class
        # TODO: have some sort of standardised SimulationResult class

        print(f"Simulation successful!\n"
              f"Time taken: {time_taken}\n"
              f"Maximum distance traversable: {distance_travelled:.2f}km\n"
              f"Average speed: {np.average(speed_kmh):.2f}km/h\n"
              f"Final battery SOC: {final_soc:.2f}%\n")

        # ----- Plotting -----

        if plot_results:
            arrays_to_plot = [speed_kmh, np.cumsum(distance), state_of_charge, delta_energy,
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

    def display_result(self, res):
        print(f"{res.message} \n")
        print(f"Optimal solution: {res.x.round(2)} \n")
        print(f"Average speed: {np.mean(res.x).round(1)}km/h")

        maximum_distance = np.abs(self.run_model(res.x))
        print(f"Maximum distance: {maximum_distance:.2f}km\n")
        
    @helpers.timeit
    def optimize(self, *args, **kwargs):
        bounds = {
            'x0': (20, 70),
            'x1': (20, 70),
            'x2': (20, 70),
            'x3': (20, 70),
            'x4': (20, 70),
            'x5': (20, 70),
            'x6': (20, 70),
            'x7': (20, 70),
        }

        # https://github.com/fmfn/BayesianOptimization
        optimizer = BayesianOptimization(f=self.run_model, pbounds=bounds)

        # configure these parameters depending on whether optimizing for speed or precision
        # see https://github.com/fmfn/BayesianOptimization/blob/master/examples/exploitation_vs_exploration.ipynb for an explanation on some parameters
        # see https://www.cse.wustl.edu/~garnett/cse515t/spring_2015/files/lecture_notes/12.pdf for an explanation on acquisition functions
        optimizer.maximize(init_points=10, n_iter=50, acq='ucb', xi=1e-4, kappa=0.1)

        print(optimizer.max)
        return optimizer.max