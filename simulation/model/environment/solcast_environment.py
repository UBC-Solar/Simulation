from simulation.model.environment import BaseEnvironment


class SolcastEnvironment(BaseEnvironment):
    def __init__(self):
        super().__init__()
        self._ghi = None

    @property
    def ghi(self):
        if (value := self._ghi) is not None:
            return value
        else:
            raise ValueError("ghi is None!")

    @ghi.setter
    def ghi(self, value):
        self._ghi = value
