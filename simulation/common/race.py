"""
This class collects the constants that are related to a specific competition.
"""
import enum

from simulation.config import config_directory
from simulation.cache.race import race_directory
from geopy.distance import geodesic
import os
import json
import pickle
import numpy as np


class Race:
    class RaceType(enum.Enum):
        ASC = "ASC"
        FSGP = "FSGP"

        def __str__(self):
            match self.value:
                case "ASC":
                    return "ASC"
                case "FSGP":
                    return "FSGP"

        def __reduce__(self):
            return self.__class__, (self.name,)

        def __contains__(self, item):
            return item == "ASC" or item == "FSGP"

        def __repr__(self):
            return str(self)

    ASC = RaceType.ASC
    FSGP = RaceType.FSGP

    def __init__(self, race_type: RaceType):
        self.race_type = race_type

        config_path = os.path.join(config_directory, f"settings_{str(self.race_type)}.json")
        with open(config_path) as f:
            self.race_constants = json.load(f)
            race_constants = self.race_constants

        self.days = race_constants["days"]
        self.tiling = race_constants["tiling"]
        self.date = (race_constants["start_year"], race_constants["start_month"], race_constants["start_day"])

        self.race_duration = len(self.days) * 24 * 60 * 60  # Duration (s)
        self.cornering_radii = self.make_cornering_radii_array(race_constants["waypoints"])
        print("_________CORNERING RADII____________")
        print(self.cornering_radii)

        self.driving_boolean = self.make_time_boolean("driving")
        self.charging_boolean = self.make_time_boolean("charging")

    def __str__(self):
        return str(self.race_type)

    def write(self):
        with open(race_directory / f"{str(self.race_type)}.pkl", 'wb') as outfile:
            pickle.dump(self, outfile, protocol=pickle.HIGHEST_PROTOCOL)

    def make_time_boolean(self, boolean_type: str):
        boolean: np.ndarray = np.empty(self.race_duration, dtype=np.int8)
        DAY_LENGTH: int = 24 * 60 * 60  # Length of a day in seconds

        for tick in range(len(boolean)):
            day: int = tick // DAY_LENGTH    # Integer division to determine how many days have passed
            time_of_day = tick % DAY_LENGTH  # Time of day in seconds where 0 is midnight and 43200 is noon
            begin, end = self.days[str(day)][boolean_type]

            # If the time of day is between the beginning and end, then the boolean is True, else False
            boolean[tick] = begin <= time_of_day < end

        return boolean
    
    def make_cornering_radii_array(self, waypoints):
        # pop off last coordinate since first and last coordinate are the same
        waypoints = waypoints[:-1]

        cornering_radii = np.empty(len(waypoints))
        for i in range(len(waypoints)):
            # if the next point or previous point is out of bounds, wrap the index around the array
            i2 = (i - 1) % len(waypoints)
            i3 = (i + 1) % len(waypoints)
            current_point = waypoints[i]
            previous_point = waypoints[i2]
            next_point = waypoints[i3]

            x1 = 0 
            y1 = 0
            x2, y2 = calculate_xy_distance(current_point, previous_point)
            x3, y3 = calculate_xy_distance(current_point, next_point)
            cornering_radii[i] = radius_of_curvature(x1, y1, x2, y2, x3, y3)
        return cornering_radii
def calculate_xy_distance(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Base coordinate
    coord_base = (lat1, lon1)
    # Coordinate for latitude difference (keep longitude the same)
    coord_lat = (lat2, lon1)
    # Coordinate for longitude difference (keep latitude the same)
    coord_long = (lat1, lon2)

    # geodesic is a function from geopy that finds the distance between lat lon coords in meters with high percision
    y_distance = geodesic(coord_base, coord_lat).meters
    x_distance = geodesic(coord_base, coord_long).meters

    return x_distance, y_distance

# uses circumcircle formula
def radius_of_curvature(x1, y1, x2, y2, x3, y3):
    numerator = np.sqrt(
        ((x3 - x2)**2 + (y3 - y2)**2) *
        ((x1 - x3)**2 + (y1 - y3)**2) *
        ((x2 - x1)**2 + (y2 - y1)**2)
    )

    denominator = 2 * abs(
        ((x2 - x1) * (y1 - y3) - (x1 - x3) * (y2 - y1))
    )

    return numerator / denominator

def load_race(race_type: Race.RaceType) -> Race:
    with open(race_directory / f"{str(race_type)}.pkl", 'rb') as infile:
        return pickle.load(infile)
    





def write_slip_angles(min_degrees, max_degrees, num_elements): 
    # Step 1: Generate or define data points (slip angle, tire force)
    # Example data, replace with your actual data
    slip_angles = np.linspace(min_degrees, max_degrees, num_elements)
    tire_forces = 1000 * np.sin(np.radians(slip_angles))  # Example tire force formula

    with open(race_directory / "slip_angle_lookup.pkl", 'wb') as outfile:
        pickle.dump((slip_angles, tire_forces), outfile)


def read_slip_angles():
    # Deserialize the data points from the file
    with open('slip_angle_lookup.pkl', 'rb') as f:
        slip_angles, tire_forces = pickle.load(f)

    print("Lookup table data points have been loaded from 'lookup_table.pkl'.")
    return slip_angles, tire_forces


def get_slip_angle_for_tire_force(desired_tire_force):
    # Read the lookup table data points
    slip_angles, tire_forces = read_slip_angles()

    # Use the numpy interpolation function to find slip angle for the given tire force
    # interpolation estimates unknown slip angle from a tire force that lies between known tire forces (from the lookup table)
    estimated_slip_angle = np.interp(desired_tire_force, tire_forces, slip_angles)
    
    
    return estimated_slip_angle





def compile_races():
    fsgp = Race(Race.FSGP)
    fsgp.write()

    asc = Race(Race.ASC)
    asc.write()

    write_slip_angles(0, 15, 10000)
