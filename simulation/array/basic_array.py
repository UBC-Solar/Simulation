from simulation.array.base_array import BaseArray

class BasicArray(BaseArray):
    def __init__(self):
        super().__init__()

    def update(self, tick):
        """
        updates model for a single tick

        :param tick: (float) the length of time for the tick (in seconds)
        """
        print("Hello world")
        self._foo()

    # use this for all private functions
    def _foo(self):
        print("bar")