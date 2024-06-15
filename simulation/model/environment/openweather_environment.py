from simulation.model.environment import BaseEnvironment


class OpenweatherEnvironment(BaseEnvironment):
    def __init__(self):
        super().__init__()
        self._cloud_cover = None

    @property
    def cloud_cover(self):
        if (value := self._cloud_cover) is not None:
            return value
        else:
            raise ValueError("cloud cover is None!")

    @cloud_cover.setter
    def cloud_cover(self, value):
        self._cloud_cover = value
