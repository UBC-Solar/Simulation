import numpy as np
import pytest
import simulation as simulation


@pytest.fixture
def solar():
    solar_calculations = simulation.environment.SolarCalculations()
    return solar_calculations


def test_apply_cloud_cover1(solar):
    test_cloud_cover = np.array([0, 0, 0])
    test_GHI = np.array([1, 2, 3])

    result_GHI = solar.apply_cloud_cover(GHI=test_GHI, cloud_cover=test_cloud_cover)

    expected_GHI = np.array([1, 2, 3])
    assert np.all(result_GHI == expected_GHI)


def test_apply_cloud_cover2(solar):
    test_cloud_cover = np.array([100, 100, 100])
    test_GHI = np.array([1, 2, 1])

    result_GHI = solar.apply_cloud_cover(GHI=test_GHI, cloud_cover=test_cloud_cover)

    expected_GHI = np.array([0.25, 0.5, 0.25])
    assert np.all(result_GHI == expected_GHI)
