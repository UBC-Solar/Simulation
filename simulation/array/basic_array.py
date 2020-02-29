from .base_array import BaseArray

class BasicArray(BaseArray):
    def __init__(self):
        super().__init__(self)

    def update(self, tick):
        """
        updates model for a single tick

        :param tick: (float) the length of time for the tick (in seconds)
        """
        print("Hello world")

array = BasicArray()
array.update(1)