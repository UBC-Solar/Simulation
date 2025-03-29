import random
import numpy as np
import os

from geopy.distance import distance
from data import get_FSGP_trajectory
from geometry import calculate_meter_distance
from plotting import plot_mesh

from physics.models.motor import AdvancedMotor
from physics.environment import GIS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
route_data = np.load(os.path.join(BASE_DIR, "route_data_FSGP.npz"))


def latlon_to_meters(lat, lon):
    """Approximates local meters per degree at given latitude."""
    lat_m = distance((lat, lon), (lat + 0.0001, lon)).meters / 0.0001
    lon_m = distance((lat, lon), (lat, lon + 0.0001)).meters / 0.0001
    return lat_m, lon_m

def generate_lateral_mesh(trajectory, lateral_distance_meters, lateral_num_points):
    trajectory = np.array(trajectory)
    mesh = []

    for i in range(len(trajectory)):
        lat, lon = trajectory[i]

        lat_m, lon_m = latlon_to_meters(lat, lon)

        if i == 0:  # Forward difference for first point
            dlat, dlon = trajectory[i + 1] - trajectory[i]
        elif i == len(trajectory) - 1:  # Backward difference for last point
            dlat, dlon = trajectory[i] - trajectory[i - 1]
        else:  # Central difference for interior points
            dlat, dlon = trajectory[i + 1] - trajectory[i - 1]

        # Convert directional difference to meters
        dx = dlon * lon_m
        dy = dlat * lat_m

        # Normalize direction vector
        norm = np.sqrt(dx ** 2 + dy ** 2)
        if norm == 0:  # Avoid division by zero
            mesh.append([(lat, lon)])  # Append at least the original point
            continue
        dx /= norm
        dy /= norm

        # Compute perpendicular vector (rotated 90 degrees)
        perp_dx = -dy
        perp_dy = dx

        # Store the trajectory point at the center of the row
        lateral_points = [(lat, lon)]

        for lateral_i in range(1, lateral_num_points + 1):
            left_lat = lat + (perp_dy * lateral_distance_meters * lateral_i) / lat_m
            left_lon = lon + (perp_dx * lateral_distance_meters * lateral_i) / lon_m

            right_lat = lat - (perp_dy * lateral_distance_meters * lateral_i) / lat_m
            right_lon = lon - (perp_dx * lateral_distance_meters * lateral_i) / lon_m

            lateral_points.insert(0, (left_lat, left_lon))
            lateral_points.append((right_lat, right_lon))

        mesh.append(lateral_points)

    return mesh


def get_random_trajectory(mesh):
    random_trajectory = []
    for i in range(len(mesh)):
        random_index = random.randint(0, len(mesh[0]) - 1)
        random_trajectory.append(mesh[i][random_index])
    return random_trajectory

def get_distances(trajectory):
    distance_array_m = []
    for i in range(1, len(trajectory)):
        point = trajectory[i]
        previous_point = trajectory[i - 1]
        distance_x, distance_y = calculate_meter_distance(point, previous_point)
        distance_norm = np.sqrt(distance_x ** 2 + distance_y ** 2)
        distance_array_m.append(distance_norm)

    distance_array_m.insert(0, 0) # first point has no distance
    return distance_array_m

def run_motor_model(speed_kmh, distances_m, trajectory):
    num_elements = len(trajectory)
    if len(distances_m) != num_elements:
        print("All arrays must have the same length.")
        return

    # no wind
    wind_speed_arr = np.zeros(num_elements)
    tick_arr = np.zeros(num_elements)
    speed_kmh_arr = np.full(num_elements, speed_kmh)
    speed_ms_arr = speed_kmh_arr / 3.6
    for index, d in enumerate(distances):
        tick_arr[index] = d / speed_ms_arr[index]

    # Generating gradient array
    origin_coord, current_coord = [
        38.9281815,
        -95.677021
    ]

    gis = GIS(
        route_data,
        origin_coord,
        current_coord
    )

    closest_gis_indices = np.arange(num_elements)
    gradients_arr = gis.get_gradients(closest_gis_indices)

    # parameters taken from config
    advanced_motor = AdvancedMotor(
        vehicle_mass=350,
        road_friction=0.012,
        tire_radius=0.2032,
        vehicle_frontal_area=1.1853,
        drag_coefficient=0.11609)
    energy_consumed, cornering_work, gradients_arr, road_friction_array, drag_forces, g_forces = advanced_motor.calculate_energy_in(speed_kmh_arr, gradients_arr, wind_speed_arr, tick_arr, trajectory)
    return  energy_consumed, cornering_work, road_friction_array, drag_forces, g_forces, tick_arr, speed_kmh_arr, gradients_arr


if __name__ == '__main__':
    trajectory_FSGP = get_FSGP_trajectory()
    mesh = generate_lateral_mesh(trajectory_FSGP, 1, 3)
    random_trajectory = get_random_trajectory(mesh)

    distances = get_distances(random_trajectory)
    distances_m = np.array(distances)
    energy_consumed, cornering_work, road_friction_array, drag_forces, g_forces, ticks, speeds_kmh, gradients, = run_motor_model(50, distances_m, random_trajectory)

    folium_map = plot_mesh(random_trajectory, mesh, distances_m, speeds_kmh, energy_consumed, ticks, cornering_work, gradients, road_friction_array, drag_forces, g_forces)
    folium_map.save("lateral_mesh_map.html")

