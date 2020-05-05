from simulation.array.base_array import BaseArray

class BasicArray(BaseArray):
    def __init__(self):
        super().__init__()

        self.sunlight = 1000

    @staticmethod
    def calculate_produced_power(sunlight):
        produced_power = sunlight
        return produced_power

    def update(self, tick):
        """
        updates model for a single tick

        :param tick: (float) the length of time for the tick (in seconds)

        """
        self.produced_energy = self.calculate_produced_power(self.sunlight) * tick
        return self.produced_energy

