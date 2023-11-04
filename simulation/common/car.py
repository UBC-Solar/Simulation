from simulation.config import config_directory
import os
import json

"""
This Singleton stores constants for UBC Solar's vehicles.
"""


class CarMetaclass(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Car(metaclass=CarMetaclass):
    def __init__(self, name: str):
        config_path = os.path.join(config_directory, f"{name}.json")

        with open(config_path) as f:
            car_constants = json.load(f)

        self.panel_efficiency = car_constants["panel_efficiency"]
        self.panel_size = car_constants["panel_size"]
        self.max_voltage = car_constants["max_voltage"]
        self.min_voltage = car_constants["min_voltage"]
        self.max_current_capacity = car_constants["max_current_capacity"]
        self.max_energy_capacity = car_constants["max_energy_capacity"]
        self.vehicle_mass = car_constants["vehicle_mass"]
        self.road_friction = car_constants["road_friction"]
        self.tire_radius = car_constants["tire_radius"]
        self.vehicle_frontal_area = car_constants["vehicle_frontal_area"]
        self.drag_coefficient = car_constants["drag_coefficient"]
