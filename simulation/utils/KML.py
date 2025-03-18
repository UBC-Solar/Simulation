from xml.dom import minidom
import numpy as np
from numpy.typing import NDArray


def _parse_coordinates_from_kml(coords_str: str) -> list[list[float]]:
    """

    Parse a coordinates string from a XML (KML) file into a list of coordinates (2D vectors).
    Requires coordinates in the format "39.,41.,0  39.,40.,0" which will return [ [39., 41.], [39., 40.] ].

    :param coords_str: coordinates string from a XML (KML) file
    :return: list of 2D vectors representing coordinates
    :rtype: np.ndarray

    """

    def parse_coord(pair):
        coord = pair.split(',')
        coord.pop()
        coord = [float(value) for value in coord]
        return coord

    return list(map(parse_coord, coords_str.split()))


def _process_KML_file(route_file):
    """

    Load the FSGP Track from a KML file exported from a Google Earth project.

    Ensure to follow guidelines enumerated in this directory's `README.md` when creating and
    loading new route files.

    :return: Array of N coordinates (latitude, longitude) in the shape [N][2].
    """
    with open(route_file) as f:
        data = minidom.parse(f)
        kml_coordinates = data.getElementsByTagName("coordinates")[0].childNodes[0].data
        coordinates: np.ndarray = np.array(_parse_coordinates_from_kml(kml_coordinates))

        # Google Earth exports coordinates in order longitude, latitude, when we want the opposite
        return np.roll(coordinates, 1, axis=1)


class KMLParser:
    """
    `KMLParser` is a wrapper around KML utilities to process a KML-formatted XML file into a list of coordinates.
    """
    def __init__(self, route_file):
        self.route_file = route_file

    def parse(self) -> NDArray:
        """
        Parse the KML file into a list of coordinates.

        :return: an array of N coordinates (latitude, longitude) in the shape [N][2].
        """
        return _process_KML_file(self.route_file)
