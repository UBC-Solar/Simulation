import math
import pytest

import numpy as np

from simulation.common import helpers
from simulation.common.helpers import *


def test_no_deceleration():
    test_speed_array = np.array([50, 50, 50, 50, 50, 50, 50, 50])

    result_speed_array = apply_deceleration(test_speed_array, 3)

    expected_speed_array = np.array([50, 50, 50, 50, 50, 50, 50, 50])
    assert np.all(result_speed_array == expected_speed_array)

def test_no_deceleration_2():
    test_speed_array = np.array([0, 0, 0, 0, 0, 0, 0, 0])

    result_speed_array = apply_deceleration(test_speed_array, 3)

    expected_speed_array = np.array([0, 0, 0, 0, 0, 0, 0, 0])
    assert np.all(result_speed_array == expected_speed_array)

def test_acceleration():
    test_speed_array = np.array([10, 20, 30, 40, 50, 60, 70, 80])

    result_speed_array = apply_deceleration(test_speed_array, 3)

    expected_speed_array = np.array([10, 20, 30, 40, 50, 60, 70, 80])
    assert np.all(result_speed_array == expected_speed_array)

def test_trivial():
    test_speed_array = np.array([50, 50, 50, 50, 0, 0, 0, 0])

    result_speed_array = apply_deceleration(test_speed_array, 3)

    expected_speed_array = np.array([50, 37.5, 25, 12.5, 0, 0, 0, 0])
    assert np.all(result_speed_array == expected_speed_array)
   
def test_trivial_2():
    test_speed_array = np.array([40, 44, 49.9, 50, 50, 50, 50, 0, 0, 0, 0])

    result_speed_array = apply_deceleration(test_speed_array, 3)

    expected_speed_array = np.array([40, 44, 49.9, 50, 37.5, 25, 12.5, 0, 0, 0, 0])
    assert np.all(result_speed_array == expected_speed_array)

def test_trivial_3():
    test_speed_array = np.array([50, 50, 50, 50, 0, 0, 50, 0])

    result_speed_array = apply_deceleration(test_speed_array, 3)

    expected_speed_array = np.array([50, 37.5, 25, 12.5, 0, 0, 50, 0])
    assert np.all(result_speed_array == expected_speed_array)



def test_negative_steps():
    test_speed_array = np.array([50, 50, 50, 50, 0, 0, 0, 0])

    test_interval = -3
    result_speed_array = apply_deceleration(test_speed_array, test_interval)

    expected_speed_array = np.array([50, 50, 50, 50, 0, 0, 0, 0])
    assert np.all(result_speed_array == expected_speed_array)


def test_none_array():
    test_speed_array = None

    test_interval = 123
    result_speed_array = apply_deceleration(test_speed_array, test_interval)

    expected_speed_array = np.array([])

    assert np.all(result_speed_array == expected_speed_array)


def test_huge_interval():

    test_speed_array = np.array([50, 50, 50, 50, 0, 0, 50, 0])

    test_interval = 123
    result_speed_array = apply_deceleration(test_speed_array, test_interval)

    expected_speed_array = np.array([50, 50, 50, 50, 0, 0, 50, 0])
    assert np.all(result_speed_array == expected_speed_array)

def test_interval_size_equal_array_size():
    test_speed_array = np.array([50, 50, 0])

    test_interval = 3
    result_speed_array = apply_deceleration(test_speed_array, test_interval)

    expected_speed_array = np.array([50, 50, 0])
    assert np.all(result_speed_array == expected_speed_array)


def test_large_interval_size():
    a = np.full((1, 100), 50)[0]
    test_speed_array = np.concatenate((a, 0), axis=None)

    test_interval = 60
    result_speed_array = apply_deceleration(test_speed_array, test_interval) # step size should be 50/61
    steps = 0
    test = True
    for i in range(0, len(result_speed_array) - 1):
        size = 50/61
        if result_speed_array[i] != 50.0:
            steps = steps + 1
            if not (math.isclose(result_speed_array[i + 1], (result_speed_array[i] - size), rel_tol=1e-6)):
                if result_speed_array[i + 1] == 0:
                    break
                test = False

    if steps != test_interval:
        test = False
    assert test


if __name__ == '__main__':
    test_large_interval_size()
