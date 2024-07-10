import numpy as np
import datetime
from dateutil import parser
import matplotlib.pyplot as plt
import math


class TimeSeries(np.ndarray):
    """
    This class encapsulates time-series data with units, a temporal x–axis, and metadata.

    Data is homogenous and evenly-spaced, such that temporal granularity between subsequent elements is constant.

    TimeSeries can be indexed with a ``float`` or slice with ``float`` components in order to index by relative time.
    For example, for some ``timeSeries``, ``timeSeries[10.43]`` is equivalent to
    ``timeSeries[timeSeries.index_of(10.43)]``.
    """

    # __new__ and __array_finalize__ are mandatory to ensure that
    # `TimeSeries` properly acts like a ndarray when necessary.
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
        assert isinstance(meta["start"], type(meta["stop"])), "Start and stop times are not of same type!"
        if isinstance(meta["start"], datetime.datetime) and isinstance(meta["stop"], datetime.datetime):
            self._start: datetime.datetime = meta["start"]
            self._stop: datetime.datetime = meta["stop"]
        else:
            print(meta["start"])
            self._start: datetime.datetime = parser.parse(meta["start"])
            self._stop: datetime.datetime = parser.parse(meta["stop"])
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
        timestamp_to_iso8601 = lambda timestamp: datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        date_times = map(timestamp_to_iso8601, self.unix_x_axis)
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

    def __getitem__(self, item):
        data_to_slice = self

        if isinstance(item, float):
            index = self.index_of(item)
            return super(TimeSeries, data_to_slice).__getitem__(index)

        if isinstance(item, slice):
            if isinstance(item.start, float):
                start_index = self.index_of(item.start)
            else:
                start_index = item.start

            if isinstance(item.stop, float):
                stop_index = self.index_of(item.stop)
            else:
                stop_index = item.stop

            item = slice(start_index, stop_index, item.step)

            unix_x_axis = data_to_slice.unix_x_axis
            new_start_timestamp: float = unix_x_axis[start_index]
            new_stop_timestamp: float = unix_x_axis[stop_index]

            new_start: datetime.datetime = datetime.datetime.fromtimestamp(new_start_timestamp)
            new_stop: datetime.datetime = datetime.datetime.fromtimestamp(new_stop_timestamp)
            new_length: float = new_stop_timestamp - new_start_timestamp

            new_time_series = TimeSeries(self, {
                "start": new_start,
                "stop": new_stop,
                "car": data_to_slice.meta["car"],
                "measurement": data_to_slice.meta["measurement"],
                "field": data_to_slice.meta["field"],
                "granularity": data_to_slice.granularity,
                "length": new_length,
                "units": data_to_slice.units,
            })

            data_to_slice = new_time_series

        return super(TimeSeries, data_to_slice).__getitem__(item)

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

    def plot(self, show=True) -> None:
        """
        Make a simple plot this data.
        :param bool show: Show plots (disable if you want to stack multiple plots, for example).
        """

        fig, ax = plt.subplots()

        ax.set_title(f"{self.meta['measurement']}: {self.meta['field']}")
        ax.set_ylabel(self.units if self.units != "" else "Arbitrary Units")
        ax.set_xlabel("Time (s)")
        ax.plot(self.x_axis, self, label=self.meta['field'])

        if show:
            plt.show()

    def index_of(self, time: float) -> int:
        """
        Return the index of the data element that represents the time closest to ``time``.

        :param float time: time (in seconds) that will be evaluated against
        :raises: ValueError if ``time`` falls outside of x–axis
        """
        if not (0.0 <= time <= self.length):
            raise ValueError(f"Relative time {time} falls outside of x–axis!")

        return np.argmin(np.abs(self.x_axis - time))

    def relative_time(self, unix_time: float) -> float:
        """
        Return the relative time of the UNIX timestamp ``time``.
        :param float unix_time: UNIX timestamp that will be converted
        """
        if not (self.start.timestamp() <= unix_time <= self.stop.timestamp()):
            raise ValueError(f"UNIX time {unix_time} falls outside of x–axis, which is {self.start.timestamp()}–{self.stop.timestamp()}!")

        return unix_time - self.start.timestamp()

    def promote(self, array: np.ndarray):
        """
        Promote a plain ndarray, ``array``, to a TimeSeries with the same metadata
        as this TimeSeries.

        This method is particularly useful for interfacing
        with libraries such as SciPy and NumPy, which will return an ndarray even when
        given a TimeSeries.

        :param array: plain ndarray to be promoted
        :return: new, promoted TimeSeries with the same metadata as this TimeSeries
        """
        meta: dict = {
            "start": self.start,
            "stop": self.stop,
            "car": self.meta["car"],
            "measurement": self.meta["measurement"],
            "field": self.meta["field"],
            "granularity": self.granularity,
            "length": self.length,
            "units": self.units,
        }

        return TimeSeries(array, meta)

    @staticmethod
    def align(*args) -> list:
        start_time = np.max([arg.start.timestamp() for arg in args])
        end_time = np.min([arg.stop.timestamp() for arg in args])
        granularity = np.max([arg.granularity for arg in args])
        new_length = end_time - start_time

        new_x_axis = np.linspace(0, new_length, math.ceil(new_length / granularity))

        new_args = []
        for array in args:
            start_index = array.index_of(array.relative_time(start_time))
            stop_index = array.index_of(array.relative_time(end_time))

            new_array = array[start_index:stop_index]
            new_array._start = datetime.datetime.fromtimestamp(start_time)
            new_array._stop = datetime.datetime.fromtimestamp(end_time)
            new_array._granularity = granularity
            new_array._length = new_length

            new_array_interpolated = new_array.promote(np.interp(new_x_axis, new_array.x_axis, new_array))

            new_args.append(new_array_interpolated)

        return new_args

