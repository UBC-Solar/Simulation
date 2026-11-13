import numpy as np
from numpy.typing import NDArray
from physics.environment.gis import GIS


class LapGIS(GIS):
    """
    Lap mode's track: a `GIS` holding one lap, with that lap's data as read-only arrays.
    Tick mode keeps the plain `GIS`; lap mode builds this with `LapGIS.from_gis(model.gis)`.

    One entry per track point. `segment_lengths` (m), `gradients` and `headings` (degrees) are for the
    stretch arriving at point i (index 0 = last point back to the start line). `elevations` (m) and
    `coords` are for point i itself.

    Don't call `calculate_current_heading_array` on it (wrong on one lap); use `headings`.

    TODO: when tiling is removed, revisit this class. The plain `GIS` would then hold one lap too, and the
    renamed copies here (`coords`, `segment_lengths`, ...) could go.
    """

    def __init__(self, route_data, origin_coord, current_coord=None):
        super().__init__(route_data, origin_coord, current_coord)

        n = self.num_unique_coords
        self.coords = self._locked(self.path[:n])
        self.segment_lengths = self._locked(self.path_distances[:n])
        self.gradients = self._locked(self.path_gradients[:n])
        self.headings = self._locked(self._arriving_headings(self.coords))
        self.elevations = self._locked(self.path_elevations[:n])

        # Lap mode divides by stretch length, and a zero-length stretch would also make its slope NaN
        if np.any(self.segment_lengths <= 0):
            raise ValueError("Every stretch of track must have a positive length.")

    @classmethod
    def from_gis(cls, gis: GIS) -> "LapGIS":
        """One-lap `LapGIS` from any `GIS` (e.g. tick mode's tiled one). Copies the data, so they never share arrays."""
        n = gis.num_unique_coords
        route_data = {
            "path": gis.path[:n].copy(),
            "elevations": gis.path_elevations[:n].copy(),
            "time_zones": gis.path_time_zones[:n].copy(),
            "num_unique_coords": n,
        }
        return cls(route_data, gis.launch_point)

    @staticmethod
    def _locked(array) -> NDArray[np.float64]:
        """Read-only copy of `array`."""
        copy = np.array(array, dtype=np.float64)
        copy.setflags(write=False)
        return copy

    @staticmethod
    def _arriving_headings(coords: NDArray[np.float64]) -> NDArray[np.float64]:
        """Compass heading (degrees) of each stretch, point i-1 to i, looping at the start. Same formula as `GIS`."""
        lat, lon = np.radians(coords[:, 0]), np.radians(coords[:, 1])
        prev_lat, prev_lon = np.roll(lat, 1), np.roll(lon, 1)
        y = np.sin(lon - prev_lon) * np.cos(lat)
        x = np.cos(prev_lat) * np.sin(lat) - np.sin(prev_lat) * np.cos(lat) * np.cos(lon - prev_lon)
        return (np.degrees(np.arctan2(y, x)) + 360) % 360
