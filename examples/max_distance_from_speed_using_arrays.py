import simulation
import numpy as np
import datetime
from simulation.common.helpers import timeit

"""
Description: Given a constant driving speed, find the range at the speed
before the battery runs out [speed -> distance]
"""

# ----- Simulation input -----

# speed = float(input("Enter a speed (km/h): "))


class ExampleSimulation:

    def __init__(self, google_api_key, weather_api_key, origin_coord, dest_coord, waypoints):
        """
        Instantiates a simple model of the car

        lvs_power_loss: power loss in Watts due to the lvs system
        max_speed: maximum speed of the vehicle on horizontal ground, with no wind
        """

        # TODO: replace max_speed with a direct calculation taking into account the
        #   elevation and wind_speed
        max_speed = 104

        # LVS power loss is pretty small
        lvs_power_loss = 0

        # ----- Simulation constants -----
        self.initial_battery_charge = 1.0

        self.lvs_power_loss = lvs_power_loss

        self.max_speed = max_speed

        # ----- Component initialisation -----

        self.basic_array = simulation.BasicArray()

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)

        self.basic_lvs = simulation.BasicLVS(lvs_power_loss * tick)

        self.basic_motor = simulation.BasicMotor()

        self.gis = simulation.GIS(google_api_key, origin_coord, dest_coord, waypoints)
        self.route_coords = self.gis.get_path()

        self.time_of_initialization = 1593604800
        self.weather = simulation.WeatherForecasts(weather_api_key, self.route_coords, self.time_of_initialization)

        self.solar_calculations = simulation.SolarCalculations()

    @timeit
    def update_model(self, tick, simulation_duration, speed, unix_dt, start_coords):
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
        """

        # ----- Expected Distance Estimate -----

        # Array of cumulative distances hopefully travelled in this round
        timestamps = np.arange(0, simulation_duration + tick, tick)
        tick_array = np.diff(timestamps)
        tick_array = np.insert(tick_array, 0, 0)

        distances = tick_array * speed
        cumulative_distances = np.cumsum(distances)

        # cumulative_distances = timestamps * speed   # only works if the speed is constant for the entire time frame

        gis_distances = self.gis.get_path_distances()
        cumulative_distances_gis = np.cumsum(gis_distances)

        gis_route_elevations = self.gis.get_path_elevations()

        # From cumulative distances array, create a 1D array of "close_enough" indices
        # of coords from the route of GIS of size (number of ticks)
        closest_gis_indices = self.gis.calculate_closest_gis_indices(cumulative_distances)
        closest_weather_indices = self.weather.calculate_closest_weather_indices(cumulative_distances,
                                                                                 cumulative_distances_gis)

        # Get the azimuth angle of the vehicle at every location
        vehicle_bearings = self.gis.calculate_current_heading_array()[closest_gis_indices]

        # From "close_enough" GIS indices array, get the elevation at every location
        # as an 1D array of size (number of ticks)
        # Similarly, get arrays of time differences at every tick and GHI at every tick
        gradients = self.gis.get_gradients(closest_gis_indices)
        time_zones = self.gis.get_time_zones(closest_gis_indices)
        local_times = self.gis.adjust_timestamps_to_local_times(timestamps, self.time_of_initialization, time_zones)

        # Get the weather at every location
        weather_forecasts = self.weather.get_weather_forecasts(closest_weather_indices)
        absolute_wind_speeds = weather_forecasts[:, :, 2]
        wind_directions = weather_forecasts[:, :, 3]
        cloud_covers = weather_forecasts[:, :, 4]

        wind_speeds = self.weather.get_array_directional_wind_speed(vehicle_bearings, absolute_wind_speeds,
                                                                    wind_directions)
        solar_irradiances = self.solar_calculations.calculate_array_GHI(self.route_coords, time_zones, local_times,
                                                                        gis_route_elevations, cloud_covers)

        # key takeaways: solar_irradiances at every tick, wind_speeds at every tick, gradients at every tick

        # ----- Energy calculations -----

        # Note: This does nothing
        # self.basic_array.update(tick)

        self.basic_lvs.update(tick)
        lvs_consumed_energy = self.basic_lvs.get_consumed_energy()

        motor_consumed_energy = self.basic_motor.calculate_power_in(speed, gradients, wind_speeds)

        # Note: this does nothing
        # self.basic_motor.update(tick)
        # motor_consumed_energy = basic_motor.get_consumed_energy()

        array_produced_energy = self.basic_array.calculate_produced_energy(solar_irradiances, tick)

        consumed_energy = motor_consumed_energy + lvs_consumed_energy
        produced_energy = array_produced_energy

        # net energy added to the battery
        net_energy = produced_energy - consumed_energy

        # ----- Array initialisation -----

        # array of times for the simulation
        # time = np.arange(0, simulation_duration + tick, tick, dtype='f4')

        # stores speed of car at each time step
        speed_kmh = np.full_like(timestamps, fill_value=speed, dtype='f4')

        # stores the amount of energy transferred from/to the battery at each time step
        delta_energy = net_energy
        # delta_energy = np.full_like(timestamps, fill_value=net_energy, dtype='f4')

        # used to calculate the time the car was in motion
        tick_array = np.full_like(timestamps, fill_value=tick, dtype='f4')
        tick_array[0] = 0

        # ----- Array calculations -----
        cumulative_delta_energy = np.cumsum(delta_energy)
        battery_variables_array = self.basic_battery.update_array(cumulative_delta_energy)

        # stores the battery SOC at each time step
        state_of_charge = battery_variables_array[0]
        state_of_charge[np.abs(state_of_charge) < 1e-03] = 0

        # when the battery is empty the car will not move
        # TODO: if the car cannot climb the elevation, the car also does not move
        speed_kmh = np.logical_and(speed_kmh, state_of_charge) * speed_kmh
        time_in_motion = np.logical_and(tick_array, state_of_charge) * tick

        time_taken = np.sum(time_in_motion)
        time_taken = str(datetime.timedelta(seconds=int(time_taken)))

        final_soc = state_of_charge[-1] * 100 + 0.

        # ----- Target value -----

        distance = speed * (time_in_motion / 3600)
        distance_travelled = np.sum(distance)

        print(f"\nSimulation successful!\n"
              f"Time taken: {time_taken}\n"
              f"Maximum distance traversable: {distance_travelled:.2f}km\n"
              f"Speed: {speed}km/h\n"
              f"Final battery SOC: {final_soc:.2f}%\n")


if __name__ == "__main__":
    speed_kmh = [30, 30, 30, 30, 30, 30, 30, 30, 30]
    speed_kmh = np.repeat(speed_kmh, 60 * 60)
    speed_kmh = np.insert(speed_kmh, 0, 0)

    simulation_duration = 60 * 60 * 9
    tick = 1

    google_api_key = "AIzaSyCPgIT_5wtExgrIWN_Skl31yIg06XGtEHg"
    weather_api_key = "51bb626fa632bcac20ccb67a2809a73b"

    origin_coord = np.array([39.0918, -94.4172])

    waypoints = np.array([[39.0379, -95.6764], [40.8838, -98.3734],
                          [41.8392, -103.7115], [42.8663, -106.3372], [42.8408, -108.7452],
                          [42.3224, -111.2973], [42.5840, -114.4703]])

    dest_coord = np.array([43.6142, -116.2080])

    simulation = ExampleSimulation(google_api_key, weather_api_key, origin_coord, dest_coord, waypoints)
    simulation.update_model(tick, simulation_duration, speed=speed_kmh,
                            start_coords=origin_coord, unix_dt=1)
