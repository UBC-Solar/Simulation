import numpy as np
from numpy.typing import NDArray
from physics.environment.gis import GIS
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class LapProfile(BaseModel):
    """
    `LapProfile` holds the track data for one lap, one entry per track point, so lap mode can read
    everything about the lap from one place. Built once per model.

    Why not read the `GIS` directly: the `GIS` mixes one-lap arrays with arrays covering every
    tiled copy of the track, numbers slopes and headings by different stretches, and has no
    headings of its own. Here every array is one lap long and uses one convention, so lap mode
    can't index the wrong copy or pair a slope with the wrong direction.

    Index `i` refers to track point `i`. `segment_lengths[i]`, `gradients[i]` and `headings[i]` all
    describe the stretch of track arriving at point `i`, from point `i - 1`. Index 0 is the stretch
    from the last point back to the start. `elevations[i]` and `coords[i]` describe point `i` itself.

    Every array is stored as a read-only copy, however the profile is built. Writing to one raises
    an error instead of silently changing data that other code (such as the `GIS`) may share.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    segment_lengths: NDArray[np.float64]  # meters
    gradients: NDArray[np.float64]  # rise over run, unitless (0.012 is a 1.2% slope)
    headings: NDArray[np.float64]  # degrees, compass bearing
    elevations: NDArray[np.float64]  # meters
    coords: NDArray[np.float64]  # degrees, [latitude, longitude] per point

    @field_validator("*", mode="after")
    @classmethod
    def _lock(cls, array) -> NDArray[np.float64]:
        """
        Store every field as a read-only copy. Done here rather than in `from_gis` so that a
        profile built any other way (for example by hand in a test) is protected too.
        """
        copy = np.array(array, dtype=np.float64)
        copy.setflags(write=False)
        return copy

    @model_validator(mode="after")
    def _check_shapes(self) -> "LapProfile":
        """
        Reject a profile whose arrays don't line up, or that has a missing or zero-length stretch,
        as soon as it is built. Lap mode divides by segment lengths, so a bad route would otherwise
        surface later as an infinite or NaN lap time.
        """
        n = len(self.segment_lengths)
        if any(len(a) != n for a in (self.gradients, self.headings, self.elevations, self.coords)):
            raise ValueError("All LapProfile arrays must have one entry per track point.")
        if self.coords.shape != (n, 2):
            raise ValueError("coords must be one [latitude, longitude] pair per track point.")
        if not all(np.isfinite(a).all() for a in (self.segment_lengths, self.gradients,
                                                   self.headings, self.elevations, self.coords)):
            raise ValueError("LapProfile arrays must not contain NaN or infinite values.")
        if np.any(self.segment_lengths <= 0):
            raise ValueError("Every segment must have a positive length.")
        return self

    @property
    def length(self) -> float:
        """
        Length of one lap in meters
        """
        return float(self.segment_lengths.sum())

    @classmethod
    def from_gis(cls, gis: GIS) -> "LapProfile":
        """
        Build a `LapProfile` from a compiled `GIS`, keeping only the first lap.

        Headings are computed here from the lap's own coordinates, as a closed loop, rather than
        taken from `Model.vehicle_bearings`. That way they don't depend on the route being tiled.

        :param GIS gis: The model's `GIS` object.
        :returns: The profile of one lap.
        """
        n = gis.num_unique_coords
        coords = gis.get_path()[:n]
        return cls(
            segment_lengths=gis.get_path_distances()[:n],
            gradients=gis.get_path_gradients()[:n],
            headings=_arriving_headings(coords),
            elevations=gis.get_path_elevations()[:n],
            coords=coords,
        )


def _arriving_headings(coords: NDArray[np.float64]) -> NDArray[np.float64]:
    """
    The compass direction (in degrees) of each stretch, going from point `i - 1` to point `i`.
    The lap is a loop, so point 0's stretch comes from the last point.

    It's the same formula the `GIS` uses (`calculate_current_heading_array`), which allows for the
    Earth being round. This version does the whole lap in one go and only needs one lap's points,
    so the last stretch comes out right without tiled copies. It sits outside the class because it
    only needs coordinates, not a whole profile.
    """
    lat, lon = np.radians(coords[:, 0]), np.radians(coords[:, 1])
    prev_lat, prev_lon = np.roll(lat, 1), np.roll(lon, 1)
    y = np.sin(lon - prev_lon) * np.cos(lat)
    x = np.cos(prev_lat) * np.sin(lat) - np.sin(prev_lat) * np.cos(lat) * np.cos(lon - prev_lon)
    return (np.degrees(np.arctan2(y, x)) + 360) % 360
