import numpy as np
from numpy.typing import NDArray
from physics.environment.gis import GIS


class LapGIS(GIS):
    """
    Lap mode's track: a `GIS` holding exactly one lap, plus that lap's data in one consistent shape.

    Tick mode keeps using the plain `GIS` that `ModelBuilder` builds. Lap mode makes its own `LapGIS`
    from it with `LapGIS.from_gis(model.gis)`, so nothing lap mode does can affect tick mode.

    Why build on `GIS` rather than a separate data class: a `LapGIS` is still a full `GIS`, so lap
    mode can use any `GIS` method it needs (time zones, path, and so on) on a track with no tiled
    copies. On top of that, its one-lap arrays fix three things about the plain `GIS`: every array
    covers exactly one lap (the `GIS` mixes one-lap arrays with arrays covering every tiled copy;
    TODO:THIS SHOULD BE FIXED LATER ON WHEN TILING IS REMOVED), slopes and headings describe the same
    stretch (the `GIS` numbers them differently), and `headings` closes the loop itself (the `GIS`'s
    heading calculation needs a tiled copy to get the last stretch right; TODO:AGAIN FIX WHEN REMOVE
    TILING).

    The one-lap arrays, one entry per track point:

    - `segment_lengths` (m), `gradients` (rise over run) and `headings` (compass degrees) describe the
      stretch of track **arriving** at point `i`, from point `i - 1`. Index 0 is the stretch from the
      last point back to the start line.
    - `elevations` (m) and `coords` ([latitude, longitude]) describe point `i` itself.

    They're read-only copies.

    Don't call `calculate_current_heading_array` on a `LapGIS`: the inherited `GIS` version needs a
    next tiled copy, so on one lap it gets the last heading wrong. Use `headings`.
    
    TODO:Currently, GIS built always (for per-tick), LapGIS built after. once remove tiling, deal with this duplication 
    (as lap mode does not use GIS). Like right now Lap GIS also duplicates some of GIS's fields (coords, segment lengths...)
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
        """
        Build a one-lap `LapGIS` from any `GIS`, such as the tiled one `ModelBuilder` makes for tick
        mode. Only the first lap is kept, so there are no tiled copies. The arrays are copied, so the
        two never share data and the original can't be changed through the `LapGIS`.
        """
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
        """A read-only copy of `array`, so writing to it raises instead of changing shared data."""
        copy = np.array(array, dtype=np.float64)
        copy.setflags(write=False)
        return copy

    @staticmethod
    def _arriving_headings(coords: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        The compass direction (in degrees) of each stretch, going from point `i - 1` to point `i`.
        The lap is a loop, so point 0's stretch comes from the last point.

        It's the same formula the `GIS` uses, which allows for the Earth being round. This version
        does the whole lap in one go and needs no tiled copies to get the last stretch right.
        """
        lat, lon = np.radians(coords[:, 0]), np.radians(coords[:, 1])
        prev_lat, prev_lon = np.roll(lat, 1), np.roll(lon, 1)
        y = np.sin(lon - prev_lon) * np.cos(lat)
        x = np.cos(prev_lat) * np.sin(lat) - np.sin(prev_lat) * np.cos(lat) * np.cos(lon - prev_lon)
        return (np.degrees(np.arctan2(y, x)) + 360) % 360
