from haversine import haversine, Unit
import numpy as np

def calculate_meter_distance(coord1, coord2):
    """
    Calculate the x and y distance in meters between two latitude-longitude coordinates.

    :param tuple coord1: (float[2]) The (latitude, longitude) coordinates of the first point
    :param tuple coord2: (float[2]) The (latitude, longitude) coordinates of the second point
    :returns: (float[2]) The x (longitude) and y (latitude) distances in meters
    :rtype: tuple
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Base coordinate
    coord_base = (lat1, lon1)
    # Coordinate for latitude difference (keep longitude the same)
    coord_lat = (lat2, lon1)
    # Coordinate for longitude difference (keep latitude the same)
    coord_long = (lat1, lon2)

    # Calculate y distance (latitude difference)
    y_distance = haversine(coord_base, coord_lat, unit=Unit.METERS)
    # Calculate x distance (longitude difference)
    x_distance = haversine(coord_base, coord_long, unit=Unit.METERS)

    if lat2 < lat1:
        y_distance = -y_distance
    if lon2 < lon1:
        x_distance = -x_distance

    return x_distance, y_distance

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