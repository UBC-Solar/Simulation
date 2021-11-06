import numpy as np
from simulation.common import helpers
from simulation.common.helpers import *


def test_check_for_non_consecutive_zeros():
    test_array_true = np.array([1, 2, 3, 0, 0, 1, 5, 0, 3, 0, 0, 0])
    test_array_false = np.array([1, 3, 4, 5, 0, 0, 0, 0, 0])

    result = tuple(
        (helpers.check_for_non_consecutive_zeros(test_array_true),
         helpers.check_for_non_consecutive_zeros(test_array_false)))

    assert result == (True, False)


def test_date_from_unix_timestamp():
    expected_result_utc_result = "2021-10-30 19:39:27"
    output = date_from_unix_timestamp(1635622767)
    assert expected_result_utc_result == output


def test_hour_from_unix_timestamp():
    expected_hour = 19
    output = hour_from_unix_timestamp(1635622767)
    assert expected_hour == output


def test_get_day_of_year1():
    expected_day = 1
    output = get_day_of_year(1, 1, 2021)
    assert expected_day == output


def test_get_day_of_year2():
    expected_day = 303
    output = get_day_of_year(30, 10, 2021)
    assert expected_day == output


def test_get_day_of_year3():
    expected_day = 365
    output = get_day_of_year(31, 12, 2021)
    assert expected_day == output


def test_get_day_of_year_leap():
    expected_day = 366
    output = get_day_of_year(31, 12, 2024)
    assert expected_day == output


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
    test_check_for_non_consecutive_zeros()
    test_date_from_unix_timestamp()
