import sys
import simulation
import numpy as np
import datetime
import json
import seaborn as sns
import pandas as pd
from simulation.common import helpers
import matplotlib.pyplot as plt
from tqdm import tqdm
from scipy.optimize import minimize
from bayes_opt import BayesianOptimization
from simulation.config import settings_directory
from simulation.main.SimulationResult import SimulationResult


class Simulation:

    def __init__(self, race_type):
        """
        Instantiates a simple model of the car.

        :param race_type: a string that describes the race type to simulate (ASC or FSGP)

        Depending on the race type, the following initialisation parameters are read from the corresponding
        settings json file located in the config folder.

        google_api_key: API key to access GoogleMaps API
        weather_api_key: API key to access OpenWeather API
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
        
        # ----- Load arguments -----
        with open(settings_path) as f:
            args = json.load(f)

        # ----- Simulation Race Independent constants -----

        self.initial_battery_charge = args['initial_battery_charge']

        # LVS power loss is pretty small so it is neglected
        self.lvs_power_loss = args['lvs_power_loss']  # Race-independent

        # ----- Time constants -----

        self.tick = args['tick']
        self.simulation_duration = args['simulation_duration']
        self.start_hour = args['start_hour']

        # ----- API keys -----

        self.google_api_key = args['google_api_key']
        self.weather_api_key = args['weather_api_key']

        # ----- Route constants -----

        self.origin_coord = args['origin_coord']
        self.dest_coord = args['dest_coord']
        self.waypoints = args['waypoints']
        
        # ----- Race type -----
        
        self.race_type = race_type

        # ----- Force update flags -----

        gis_force_update = args['gis_force_update']
        weather_force_update = args['weather_force_update']

        # ----- Component initialisation -----

        self.basic_array = simulation.BasicArray()  # Race-independent

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)  # Race-independent

        self.basic_lvs = simulation.BasicLVS(self.lvs_power_loss * self.tick)  # Race-independent

        self.basic_motor = simulation.BasicMotor()  # Race-independent

        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints,
                                  self.race_type, force_update=gis_force_update)
        self.route_coords = self.gis.get_path()

        self.vehicle_bearings = self.gis.calculate_current_heading_array()
        self.weather = simulation.WeatherForecasts(self.weather_api_key, self.route_coords,
                                                   self.simulation_duration / 3600,
                                                   self.race_type,
                                                   weather_data_frequency="daily",
                                                   force_update=weather_force_update)

        # Implementing starting times (ASC: 7am, FSGP: 8am)
        weather_hour = helpers.hour_from_unix_timestamp(self.weather.last_updated_time)
        self.time_of_initialization = self.weather.last_updated_time + 3600 * (24 + self.start_hour - weather_hour)

        self.solar_calculations = simulation.SolarCalculations()  # Race-Independent

        self.local_times = 0

        self.timestamps = np.arange(0, self.simulation_duration + self.tick, self.tick)

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

        # ------ Run calculations and get result -------

        result = self.__run_simulation_calculations(speed_kmh)

        # ------- Parse results ---------
        simulation_arrays = result.arrays
        distances = simulation_arrays[0] 
        state_of_charge = simulation_arrays[1]
        delta_energy = simulation_arrays[2]
        solar_irradiances = simulation_arrays[3]
        wind_speeds = simulation_arrays[4]
        gis_route_elevations_at_each_tick = simulation_arrays[5]
        cloud_covers = simulation_arrays[6]

        distance_travelled = result.distance_travelled
        time_taken = result.time_taken
        final_soc = result.final_soc

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
            y_label = ["Speed (km/h)", "Distance (km)", "SOC (%)", "Delta energy (J)",
                       "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)", "Cloud cover (%)"]
            
            self.__plot_graph(arrays_to_plot, y_label)

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
            'x0': (20, 100),
            'x1': (20, 100),
            'x2': (20, 100),
            'x3': (20, 100),
            'x4': (20, 100),
            'x5': (20, 100),
            'x6': (20, 100),
            'x7': (20, 100),
        }

        # https://github.com/fmfn/BayesianOptimization
        optimizer = BayesianOptimization(f=self.run_model, pbounds=bounds)

        # configure these parameters depending on whether optimizing for speed or precision
        # see https://github.com/fmfn/BayesianOptimization/blob/master/examples/exploitation_vs_exploration.ipynb for an explanation on some parameters
        # see https://www.cse.wustl.edu/~garnett/cse515t/spring_2015/files/lecture_notes/12.pdf for an explanation on acquisition functions
        optimizer.maximize(init_points=10, n_iter=10, acq='ucb', xi=1e-1, kappa=10)

        result = optimizer.max
        result_params = list(result["params"].values())

        speed_result = np.empty(len(result_params))
        for i in range(len(speed_result)):
            speed_result[i] = result_params[i]
        
        speed_result = helpers.reshape_and_repeat(speed_result, self.simulation_duration)
        speed_result = np.insert(speed_result, 0, 0)

        arrays_to_plot = self.__run_simulation_calculations(speed_result).arrays
        
        self.__plot_graph([speed_result] + arrays_to_plot, ["Optimized speed array", "Distance (km)", "SOC (%)", "Delta energy (J)",
                       "Solar irradiance (W/m^2)", "Wind speeds (km/h)", "Elevation (m)", "Cloud cover (%)"]) 

        return optimizer.max

    def __plot_graph(self, arrays_to_plot, array_labels):
        compress_constant = int(self.timestamps.shape[0] / 5000)
        for index, array in enumerate(arrays_to_plot):
            arrays_to_plot[index] = array[::compress_constant]

        sns.set_style("whitegrid")
        f, axes = plt.subplots(4, 2, figsize=(12, 8))
        f.suptitle(f"Simulation results ({self.race_type})", fontsize=16, weight="bold")

        with tqdm(total=len(arrays_to_plot), file=sys.stdout, desc="Plotting data") as pbar:
            for index, axis in enumerate(axes.flatten()):
                print(index)
                df = pd.DataFrame(dict(time=self.timestamps[::compress_constant] / 3600, value=arrays_to_plot[index]))
                g = sns.lineplot(x="time", y="value", data=df, ax=axis)
                g.set(xlabel="time (hrs)", ylabel=array_labels[index])
        pbar.update(1)
        print()

        sns.despine()
        plt.setp(axes)
        plt.tight_layout()
        plt.show()

    def __run_simulation_calculations(self, speed_kmh):
        """
        Helper method to perform all calculations used in run_model. Returns a SimulationResult object 
        containing members that specify total distance travelled and time taken at the end of the simulation
        and final battery state of charge. This is where most of the main simulation logic happens.

        :param speed_kmh: array that specifies the solar car's driving speed (in km/h) at each time step
        """
        # ----- Expected distance estimate -----

        # Array of cumulative distances hopefully travelled in this round
        tick_array = np.diff(self.timestamps)
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
        local_times = self.gis.adjust_timestamps_to_local_times(self.timestamps, self.time_of_initialization, time_zones)

        # only for reference (may be used in the future)
        local_times_datetime = np.array([datetime.datetime.utcfromtimestamp(local_unix_time) for local_unix_time in local_times])

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

        # TODO: remove after done with testing
        cloud_covers = np.zeros_like(cloud_covers)

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
        if self.race_type == "FSGP":
            bool_lis = [time_of_day_hour == 10, time_of_day_hour == 8, time_of_day_hour == 18, time_of_day_hour == 19]
            for time in list(range(20, 24)) + list(range(0, 8)):
                night_lis.append(time_of_day_hour == time)
        elif self.race_type == "ASC":
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

        time_taken = np.sum(time_in_motion)
        time_taken = str(datetime.timedelta(seconds=int(time_taken)))

        results = SimulationResult()
        results.arrays = [
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