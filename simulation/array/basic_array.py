from simulation.array.base_array import BaseArray

CONSTANT_SUNLIGHT = 1000

class BasicArray(BaseArray):
    def __init__(self):
        super().__init__()

    def update(self, tick):
        """
        updates model for a single tick

        :param tick: (float) the length of time for the tick (in seconds)
        
        """
        return self.produced_energy

     def calculate_produced_energy(self):

         produced_energy = CONSTANT_SUNLIGHT

         self.produced_energy = produced_energy
