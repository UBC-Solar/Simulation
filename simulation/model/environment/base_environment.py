class BaseEnvironment:
    def __init__(self):
        self._time_dt = None
        self._latitude = None
        self._longitude = None
        self._wind_speed = None
        self._wind_direction = None

    @property
    def time_dt(self):
        if (value := self._time_dt) is not None:
            return value
        else:
            raise ValueError("time_dt is None!")

    @time_dt.setter
    def time_dt(self, value):
        self._time_dt = value

    @property
    def latitude(self):
        if (value := self._latitude) is not None:
            return value
        else:
            raise ValueError("latitude is None!")

    @latitude.setter
    def latitude(self, value):
        self._latitude = value

    @property
    def longitude(self):
        if (value := self._longitude) is not None:
            return value
        else:
            raise ValueError("longitude is None!")

    @longitude.setter
    def longitude(self, value):
        self._longitude = value

    @property
    def wind_speed(self):
        if (value := self._wind_speed) is not None:
            return value
        else:
            raise ValueError("wind_speed is None!")

    @wind_speed.setter
    def wind_speed(self, value):
        self._wind_speed = value

    @property
    def wind_direction(self):
        if (value := self._wind_direction) is not None:
            return value
        else:
            raise ValueError("wind_direction is None!")

    @wind_direction.setter
    def wind_direction(self, value):
        self._wind_direction = value
