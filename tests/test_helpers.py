import numpy as np
from simulation.common import helpers


def test_checkForNonConsecutiveZeros():
    test_array_true = np.array([1, 2, 3, 0, 0, 1, 5, 0, 3, 0, 0, 0])
    test_array_false = np.array([1, 3, 4, 5, 0, 0, 0, 0, 0])

    result = tuple(
        (helpers.checkForNonConsecutiveZeros(test_array_true), helpers.checkForNonConsecutiveZeros(test_array_false)))

    assert result == (True, False)


def test_find_runs1():
    """
    Unit test for helpers.find_runs(x). Tests if it can identify small examples of runs in a small array
    """
    input_array = np.array([1, 1, 3, 4, 4, 4, 4])
    expected_output_run_values = np.array([1, 3, 4])
    expected_output_run_starts = np.array([0, 2, 3])
    expected_output_run_lengths = np.array([2, 1, 4])

    test_output_run_values, test_output_run_starts, test_output_run_lengths = helpers.find_runs(input_array)

    assert (expected_output_run_values == test_output_run_values).all()
    assert (expected_output_run_starts == test_output_run_starts).all()
    assert (expected_output_run_lengths == test_output_run_lengths).all()


if __name__ == "__main__":
    test_find_runs1()
    test_checkForNonConsecutiveZeros()
