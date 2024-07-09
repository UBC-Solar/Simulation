import numpy as np
import datetime
from dateutil import parser
import matplotlib.pyplot as plt


class Wave(np.ndarray):
    """
    This class encapsulates time-series data with units, a temporal x–axis, and metadata.

    Data is homogenous and evenly-spaced, such that temporal granularity between subsequent elements is constant.

    TODO: Currently, ``length``, ``start``, and ``stop`` do not have meaning in slices of this class. This is because
    they are not properly recalculated when taking a slice, just copied over from the parent object.
    """

    # __new__ and __array_finalize__ are mandatory to ensure that
    # `Wave` properly acts like a ndarray when necessary.
    def __new__(cls, input_array, meta):
        obj = np.asarray(input_array).view(cls)
        obj._meta = meta
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self._start = getattr(obj, '_start', None)
        self._stop = getattr(obj, '_stop', None)
        self._units = getattr(obj, '_units', None)
        self._length = getattr(obj, '_length', None)
        self._granularity = getattr(obj, '_granularity', None)
        self._meta = getattr(obj, '_meta', None)

    def __init__(self, input_array, meta: dict):
        self._start: datetime.datetime = parser.parse(meta["start"])
        self._stop: datetime.datetime = parser.parse(meta["start"])
        del meta["start"]
        del meta["stop"]

        self._units: str = meta["units"]
        del meta["units"]

        self._granularity: float = meta["granularity"]
        del meta["granularity"]

        self._length: float = meta["length"]
        del meta["length"]

        self._meta: dict = meta

    @property
    def x_axis(self) -> np.ndarray:
        """
        This wave's x–axis in relative seconds, such that the first element is ``t=0``.
        """
        relative_x_axis = np.linspace(0, self.length, len(self))

        return relative_x_axis

    @property
    def unix_x_axis(self) -> np.ndarray:
        """
        This wave's x–axis as UTC UNIX timestamps.
        """
        return self.x_axis + self.start.timestamp()

    @property
    def datetime_x_axis(self) -> np.ndarray:
        """
        This wave's x–axis as ISO 8601 strings, in UTC.
        """
        unix_x_axis = self.unix_x_axis

        date_times = map(
            lambda timestamp: datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ'), unix_x_axis)
        x_axis_datetime = np.array(list(date_times))

        return x_axis_datetime

    @property
    def length(self) -> float:
        """
        Total time between the first and last element of this wave's data
        """

        return self._length

    @property
    def granularity(self) -> float:
        """
        Temporal granularity (delta t) between each element of this wave's data in seconds
        """
        return self._granularity

    @property
    def units(self) -> str:
        """
        The units of this wave's data
        """
        return self._units

    @units.setter
    def units(self, value: str):
        assert isinstance(value, str), f"Units should be a string, not {type(value)}!"
        self._units = value

    @property
    def start(self) -> datetime.datetime:
        """
        UTC datetime of the first data element
        """
        return self._start

    @property
    def stop(self) -> datetime.datetime:
        """
        UTC datetime of the last data element
        """
        return self._stop

    @property
    def meta(self) -> dict:
        """
        Metadata such as the field, measurement, and car.
        """
        return self._meta

    @meta.setter
    def meta(self, new_meta: dict):
        assert isinstance(new_meta, dict), f"New metadata should be a dictionary, not {type(new_meta)}!"
        self._meta = new_meta

    def plot(self) -> None:
        """
        Make a simple plot this data.
        """

        fig, ax = plt.subplots()

        ax.set_title(f"{self.meta['measurement']}: {self.meta['field']}")
        ax.set_ylabel(self.units if self.units != "" else "Arbitrary Units")
        ax.set_xlabel("Time (s)")
        ax.plot(self.x_axis, self, label=self.meta['field'])

        plt.show()
