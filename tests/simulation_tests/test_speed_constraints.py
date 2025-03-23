import pytest
import numpy as np
import core


def test_constrain_speeds_basic():
    """Testing the constrain_speeds functions with very basic speed_limits and speed arrays. Note that speed limits
    are associated to a distance, so the dimensions of speed_limits and speeds do not necessarily match."""

    speed_limits = np.array([8, 8, 8, 10, 10, 10, 8, 10, 6, 6, 6]).astype(float)
    speeds = np.array([12, 12, 10, 8, 6]).astype(float)
    tick = 1

    result = core.constrain_speeds(speed_limits, speeds, tick)
    expected = np.array([8, 8, 10, 8, 6])

    assert np.array_equal(result, expected)


def test_constrain_speeds_different_tick():
    """Adding a different tick value."""

    speed_limits = np.array([3, 2, 5, 8, 2, 1]).astype(float)
    speeds = np.array([4, 1, 7]).astype(float)
    tick = 3

    result = core.constrain_speeds(speed_limits, speeds, tick)
    expected = np.array([3, 1, 7])

    assert np.array_equal(result, expected)


def test_constrain_speeds_high_speeds():
    """Testing higher speeds with a higher tick value."""

    speed_limits = np.full(64, 30).astype(float)
    speeds = np.array([40, 35, 30, 25, 50]).astype(float)
    tick = 2

    result = core.constrain_speeds(speed_limits, speeds, tick)
    expected = np.array([30, 30, 30, 25, 30])

    assert np.array_equal(result, expected)
