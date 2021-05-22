import json
from abc import ABC, abstractmethod

import simulation
from simulation.common import helpers


class BaseSimulation(ABC):
    """
    Parent Class of ASC and FSGP Simulation Classes

    Includes any simulation variables that are common between the ASC and FSGP races
    Ex: Daybreak properties, Daybreak components, or timing constants

    google_api_key: API key to access GoogleMaps API
    weather_api_key: API key to access OpenWeather API
    tick: length of simulation's discrete time step (in seconds)
    """

    def __init__(self, settings_path):
        # ----- Load arguments -----
        with open(settings_path) as f:
            args = json.load(f)

        # ----- API keys -----

        self.google_api_key = args['google_api_key']
        self.weather_api_key = args['weather_api_key']

        # ----- race type -----
        self.race_type = args['race_type']

        # ----- Route Definitions ------
        self.origin_coord = args['origin_coord']
        self.dest_coord = args['dest_coord']
        self.waypoints = args['waypoints']

        # ----- Simulation Race Independent constants -----

        # ----- Battery Charge -----
        self.initial_battery_charge = args['initial_battery_charge']

        # ----- LVS power loss -----
        self.lvs_power_loss = args['lvs_power_loss']

        # ----- Time constants -----

        self.tick = args['tick']
        self.simulation_duration = args['simulation_duration']
        self.start_hour = args['start_hour']

        # ----- Force update flags -----

        self.gis_force_update = args['gis_force_update']
        self.weather_force_update = args['weather_force_update']

        # ----- Component initialisation -----
        self.basic_array = simulation.BasicArray()

        self.basic_battery = simulation.BasicBattery(self.initial_battery_charge)

        self.basic_lvs = simulation.BasicLVS(self.lvs_power_loss * self.tick)

        self.basic_motor = simulation.BasicMotor()

        self.gis = simulation.GIS(self.google_api_key, self.origin_coord, self.dest_coord, self.waypoints,
                                  self.race_type, force_update=self.gis_force_update)

        self.route_coords = self.gis.get_path()

        # ----- Environment and Weather Calculations -----
        self.vehicle_bearings = self.gis.calculate_current_heading_array()
        self.weather = simulation.WeatherForecasts(self.weather_api_key, self.route_coords,
                                                   self.simulation_duration / 3600,
                                                   self.race_type,
                                                   weather_data_frequency="daily",
                                                   force_update=self.weather_force_update)

        self.weather_hour = helpers.hour_from_unix_timestamp(self.weather.last_updated_time)
        self.time_of_initialization = self.weather.last_updated_time + 3600 * (24 + self.start_hour - self.weather_hour)

        # ----- Solar Calculations Object -----
        self.solar_calculations = simulation.SolarCalculations()

        self.local_times = 0

    @abstractmethod
    def run_model(self):
        raise NotImplementedError
