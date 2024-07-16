"""
This class collects the constants that are related to a specific competition.
"""
import enum

from simulation.config import config_directory
from simulation.cache.race import race_directory

from haversine import haversine, Unit
from pyproj import Proj, Transformer

import os
import json
import pickle
import numpy as np


import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap

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
        cornering_radii = calculate_radii(race_constants["waypoints"])
        
        self.cornering_radii = cornering_radii

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
    


def calculate_radii(waypoints):
    # pop off last coordinate if first and last coordinate are the same
    repeated_last_coordinate = False
    if waypoints[0] == waypoints[len(waypoints) - 1]:
        waypoints = waypoints[:-1]
        repeated_last_coordinate = True

    print(waypoints)

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
        x2, y2 = calculate_meter_distance(current_point, previous_point)
        x3, y3 = calculate_meter_distance(current_point, next_point)
        print(cornering_radii)
        cornering_radii[i] = radius_of_curvature(x1, y1, x2, y2, x3, y3)
    
    # If the last coordinate was removed, duplicate the first radius value to the end of the array
    if repeated_last_coordinate:
        cornering_radii = np.append(cornering_radii, cornering_radii[0])

    plot_coordinates(waypoints, cornering_radii)
    return cornering_radii


def load_race(race_type: Race.RaceType) -> Race:
    with open(race_directory / f"{str(race_type)}.pkl", 'rb') as infile:
        return pickle.load(infile)
    

def calculate_meter_distance(coord1, coord2):
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Base coordinate
    coord_base = (lat1, lon1)
    # Coordinate for latitude difference (keep longitude the same)
    coord_lat = (lat2, lon1)
    # Coordinate for longitude difference (keep latitude the same)
    coord_long = (lat1, lon2)

    # Calculate y distance (latitude difference) using haversine function
    y_distance = haversine(coord_base, coord_lat, unit=Unit.METERS)
    # Calculate x distance (longitude difference) using haversine function
    x_distance = haversine(coord_base, coord_long, unit=Unit.METERS)

    if lat2 < lat1:
        y_distance = -y_distance
    if lon2 < lon1:
        x_distance = -x_distance

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


def write_slip_angles(min_degrees, max_degrees, num_elements): 
    # coefficients for pacekja's majick formula
    # https://www.edy.es/dev/docs/pacejka-94-parameters-explained-a-comprehensive-guide/
    B = 10  # Stiffness (Example value for dry tarmac)
    C = 1.3  # Shape (Example value for dry tarmac)
    D = 1  # Peak (Example value for dry tarmac)
    E = 0.97  # Curvature (Example value for dry tarmac)

    # placeholder value, this is the mass in newtons of a toyota corolla
    Fz = 250*9.81  # Normal load in Newtons


    slip_angles = np.linspace(min_degrees, max_degrees, num_elements)
    tire_forces = Fz * D * np.sin(C * np.arctan(B * slip_angles - E * (B * slip_angles - np.arctan(B * slip_angles))))

    with open(race_directory / "slip_angle_lookup.pkl", 'wb') as outfile:
        pickle.dump((slip_angles, tire_forces), outfile)


def read_slip_angle_lookup():
    # Deserialize the data points from the file
    with open(race_directory / "slip_angle_lookup.pkl", 'rb') as f:
        slip_angles, tire_forces = pickle.load(f)

    print("Lookup table data points have been loaded from 'lookup_table.pkl'.")

    # Plot the relationship between slip angle and lateral force
    plt.figure(figsize=(10, 6))
    plt.plot(slip_angles, tire_forces, marker='o', linestyle='-', color='r')
    plt.title('Relationship between Slip Angle and Lateral Force')
    plt.xlabel('Slip Angle (degrees)')
    plt.ylabel('Lateral Force (N)')
    plt.grid(True)
    plt.show()
    return slip_angles, tire_forces




def get_slip_angle_for_tire_force(desired_tire_force):
    # Read the lookup table data points
    slip_angles, tire_forces = read_slip_angle_lookup()

    # Use the numpy interpolation function to find slip angle for the given tire force
    # interpolation estimates unknown slip angle from a tire force that lies between known tire forces (from the lookup table)
    estimated_slip_angle = np.interp(desired_tire_force, tire_forces, slip_angles)
    
    
    return estimated_slip_angle


import folium
from folium.plugins import MeasureControl

def plot_coordinates(coords, data):
    # Calculate the center of your map
    center_lat = sum([coord[0] for coord in coords]) / len(coords)
    center_lon = sum([coord[1] for coord in coords]) / len(coords)

    # Create the map
    my_map = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    # Add a measurement tool to the map for users to measure distance
    my_map.add_child(MeasureControl())

    # Add points with tooltips
    for coord, datum in zip(coords, data):
        folium.Marker(
            [coord[0], coord[1]],
            tooltip=folium.Tooltip(datum)
        ).add_to(my_map)

    # Save the map to an HTML file
    my_map.save("map.html")

# convert lat lon to utm format
# for short distances, a linear projection is more accurate then a formula like haversine, which factors the curvature of the earth

def latlon_to_utm(latitude, longitude):
    # Calculate the UTM zone from the longitude
    zone_number = int((longitude + 180) / 6) + 1
    # Create a UTM projection string using the calculated zone and WGS84 datum
    utm_crs = f"+proj=utm +zone={zone_number} +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    # Initialize a Transformer object to perform the transformation
    transformer = Transformer.from_crs("epsg:4326", utm_crs, always_xy=True)
    # Transform from geographic (lat, lon) to UTM (x, y)
    x, y = transformer.transform(longitude, latitude)
    return x, y

def compile_races():
    fsgp = Race(Race.FSGP)
    fsgp.write()

    # asc = Race(Race.ASC)
    # asc.write()

    write_slip_angles(0, 100, 1000000)
