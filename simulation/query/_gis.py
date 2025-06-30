import os
import sys
import json
import requests
from simulation.config import CompetitionConfig
from numpy.typing import ArrayLike
from simulation.query import Query
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
import numpy as np
from tqdm import tqdm
import sys
from datetime import datetime
from numpy.typing import NDArray


class TrackRouteQuery(Query[CompetitionConfig]):
    """
    `TrackRouteQuery` encapsulates the acquisition and marshalling of the data required
    to complete the information required to describe a competition that is described
    by a `TrackCompetitionConfig`.
    """

    def __init__(self, config: CompetitionConfig):
        super().__init__(config)

    def make(self) -> tuple[NDArray, NDArray, NDArray, int]:
        """
        Invoke this `TrackRouteQuery` to acquire the path time zones, path elevations for the route described
        by the `CompetitionConfig` used to construct this `TrackRouteQuery`.

        For backwards compatibility reasons, returns the coordinates used as well as the tiling.

        Returns, where N indicates the number of coordinates,
            1. ndarray[N] of time differences in seconds
            2. ndarray[N] of path elevations in meters
            3. ndarray[N, 2] of coordinates as (latitude, longitude)
            4. tiling, a scalar indicating the number of times the route should be tiled

        :return: path_time_zones, path_elevations, coordinates, tiling, as enumerated above.
        """
        coordinates: NDArray = np.array(self._config.route_config.coordinates)
        tiling: int = getattr(self._config, "tiling", 1)

        # Call Google Maps API
        path_elevations = _calculate_path_elevations(coordinates)
        path_time_zones = _calculate_time_zones(coordinates, self._config.date)

        # All of these arrays should have one element per path coordinate!
        assert len(path_time_zones) == len(path_elevations) == len(path_time_zones)

        return path_time_zones, path_elevations, coordinates, tiling


class RoadRouteQuery(Query[CompetitionConfig]):
    def __init__(self, config: CompetitionConfig):
        super().__init__(config)

    def make(self):
        raise NotImplementedError(
            "Support for ASC was deprecated in favour of building a more capable FSGP simulation."
            "Querying for ASC was not re-implemented when querying was refactored. See "
            "https://github.com/UBC-Solar/Simulation/blob"
            "/d33fa563b5feb09585af1db57be60a031964edc8/simulation/utils/Query.py for "
            "inspiration on re-implementation."
        )


def _calculate_path_elevations(coords):
    """

    Returns the elevations of every coordinate in the array of coordinates passed in as a coordinate
    See Error Message Interpretations: https://developers.google.com/maps/documentation/elevation/overview

    :param np.ndarray coords: A NumPy array [n][latitude, longitude]
    :returns: A NumPy array [n][elevation] in metres
    :rtype: np.ndarray

    """

    # construct URL
    url_head = "https://maps.googleapis.com/maps/api/elevation/json?locations="

    location_strings = []
    locations = ""

    for coord in coords:
        locations = locations + f"{coord[0]},{coord[1]}|"

        if len(locations) > 8000:
            location_strings.append(locations[:-1])
            locations = ""

    if len(locations) != 0:
        location_strings.append(locations[:-1])

    url_tail = f"&key={os.environ['GOOGLE_MAPS_API_KEY']}"

    # Get elevations
    elevations = np.zeros(len(coords))

    i = 0
    with tqdm(
        total=len(location_strings), file=sys.stdout, desc="Acquiring Elevation Data"
    ) as pbar:
        for location_string in location_strings:
            url = url_head + location_string + url_tail

            r = requests.get(url)
            response = json.loads(r.text)
            pbar.update(1)

            if response["status"] == "OK":
                for result in response["results"]:
                    elevations[i] = result["elevation"]
                    i = i + 1

            elif response["status"] == "INVALID_REQUEST":
                sys.stderr.write("Error: Request was invalid\n")

            elif response["status"] == "OVER_DAILY_LIMIT":
                sys.stderr.write(
                    "Error: Possible causes - API key is missing or invalid, billing has not been enabled,"
                    " a self-imposed usage cap has been exceeded, or the provided payment method is no longer "
                    " valid. \n"
                )

            elif response["status"] == "OVER_QUERY_LIMIT":
                sys.stderr.write("Error: Requester has exceeded quota\n")

            elif response["status"] == "REQUEST_DENIED":
                sys.stderr.write("Error: API could not complete the request\n")

    return elevations


def _calculate_time_zones(coords: ArrayLike, date: datetime) -> NDArray:
    """
    For each (lat, lng) in coords, find the local timezone
    and return its offset from UTC at the given date, in seconds.

    :param coords: array-like of shape (N, 2) with (latitude, longitude)
    :param date:   a datetime (naive or tz-aware); if naive, assumed UTC
    :returns:      numpy array of length N with offset in seconds
    """
    _tf = TimezoneFinder()

    # ensure date is timezone-aware in UTC
    if date.tzinfo is None:
        date = date.replace(tzinfo=ZoneInfo("UTC"))

    n = len(coords)
    offsets = np.full(n, np.nan, dtype=float)

    with tqdm(total=n, file=sys.stdout, desc="Calculating Time Zones") as pbar:
        for i, (lat, lng) in enumerate(coords):
            pbar.update(1)
            tzname = _tf.timezone_at(lat=lat, lng=lng)

            if tzname is None:
                tzname = _tf.closest_timezone_at(lat=lat, lng=lng)

            try:
                tz = ZoneInfo(tzname)
                local_dt = date.astimezone(tz)
                offsets[i] = local_dt.utcoffset().total_seconds()

            except Exception:
                continue

    return offsets

