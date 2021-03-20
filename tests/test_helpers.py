import numpy as np
from simulation.common import helpers


def test_checkForNonConsecutiveZeros():
    test_array_true = np.array([1, 2, 3, 0, 0, 1, 5, 0, 3, 0, 0, 0])
    test_array_false = np.array([1, 3, 4, 5, 0, 0, 0, 0, 0])

    result = tuple(
        (helpers.checkForNonConsecutiveZeros(test_array_true), helpers.checkForNonConsecutiveZeros(test_array_false)))

    assert result == (True, False)


if __name__ == "__main__":
    test_checkForNonConsecutiveZeros()
