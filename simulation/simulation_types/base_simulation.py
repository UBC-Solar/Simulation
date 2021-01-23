from abc import ABC, abstractmethod

import simulation
from simulation.common import helpers


class BaseSimulation(ABC):
    """
    Parent Class of ASC and FSGP Simulations.

    Includes any simulation variables that are common between the ASC and FSGP races
    Ex: Daybreak properties, Daybreak components, or timing constants

    Documentation on some fields:
    google_api_key: API key to access GoogleMaps API
    weather_api_key: API key to access OpenWeather API
    tick: length of simulation's discrete time step (in seconds)

    """

    def __init__(self):
        self.google_api_key = "AIzaSyCPgIT_5wtExgrIWN_Skl31yIg06XGtEHg"
        self.weather_api_key = "51bb626fa632bcac20ccb67a2809a73b"

        # ----- LVS power loss -----
        self.lvs_power_loss = 0

        # ----- Battery Charge -----
        self.initial_battery_charge = 1.0

        # ----- Time Constants -----
        self.tick = 1
        self.local_times = 0
        self.start_hour = None

        # ----- Component initialisation -----
        self.basic_array = simulation.BasicArray()

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)

        self.basic_lvs = simulation.BasicLVS(self.lvs_power_loss * self.tick)

        self.basic_motor = simulation.BasicMotor()

        # ----- Solar Calculations Object -----
        self.solar_calculations = simulation.SolarCalculations()

    def configure_race(self, race_type):
        # ----- Route and GIS Definition -----
        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints,
                                  race_type, force_update=False)
        self.route_coords = self.gis.get_path()

        # ----- Environment and Weather Calculations -----
        self.vehicle_bearings = self.gis.calculate_current_heading_array()
        self.weather = simulation.WeatherForecasts(self.weather_api_key, self.route_coords,
                                                   self.simulation_duration / 3600,
                                                   race_type,
                                                   weather_data_frequency="daily",
                                                   force_update=False)

        self.weather_hour = helpers.hour_from_unix_timestamp(self.weather.last_updated_time)
        self.time_of_initialization = self.weather.last_updated_time + 3600 * (24 + self.start_hour - self.weather_hour)

    @abstractmethod
    def run_model(self):
        raise NotImplementedError
