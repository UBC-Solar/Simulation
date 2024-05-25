"""

Compute Brightside regen efficiency based on recorded experimental data

"""

import os
import json
import numpy as np
from matplotlib import pyplot as plt
from scipy.interpolate import CubicSpline

from simulation.config import config_directory
bs_config_path = os.path.join(config_directory, "BrightSide.json")
with open(bs_config_path) as f:
    brightside_constants = json.load(f)


def curve_from_keys(key_array, end_index, start_index=0):
    return np.interp(
        np.arange(start_index, end_index),
        np.arange(start_index, end_index, end_index / len(key_array)),
        key_array,
    )


def smooth_curve_from_list(values, target_len):
    keys = np.linspace(0, 1, num=len(values))
    smooth_keys = np.linspace(0, 1, num=target_len)

    cs = CubicSpline(keys, values)
    smooth_values = cs(smooth_keys)

    return smooth_values


def force_decreasing(arr):
    for i in range(1, len(arr)):
        if arr[i] > arr[i-1]:
            arr[i] = arr[i-1]
    return arr


def force_dec_decel(arr):
    """

    Args:
        arr: input array

    Returns: input array modified such that:
        - it is decreasing
        - the absolute value of its derivative is increasing

    """
    dec_arr = force_decreasing(arr)

    # switch sign to get increasing
    return np.cumsum(-1*force_decreasing(-1*np.diff(dec_arr))) + arr[0]

# --------------------------------------- generate placeholder data -----------------------------------------


test_duration_s = 10
num_points = 100
delta_t = test_duration_s / num_points

NUM_KEYS = 10
assert num_points % NUM_KEYS == 0
scale_factor = int(num_points / NUM_KEYS)

control_speed_kmh = force_dec_decel(smooth_curve_from_list([40, 30, 25, 20, 16, 10, 7, 3, 1, 0], num_points))
regen_speed_kmh = force_dec_decel(smooth_curve_from_list([40, 23, 15, 9, 5, 3, 2, 1, 0, 0], num_points))
regen_current = smooth_curve_from_list([0, 10, 25, 35, 20, 19, 13, 12, 5, 0], num_points)
battery_voltage = smooth_curve_from_list([103, 104, 108, 108, 103, 103, 103, 103, 103, 103], num_points)

# assert (np.diff(control_speed_kmh) <= 0).all()
# assert (np.diff(regen_speed_kmh) <= 0).all()
# assert (battery_voltage > 0).all()

plt.plot(control_speed_kmh, label="control_speed_kmh")
plt.plot(regen_speed_kmh, label="regen_speed_kmh")
plt.plot(regen_current, label="regen_current")
plt.plot(battery_voltage, label="battery_voltage")

# --------------------------------------- derive values -----------------------------------------

# calculate acceleration in m/s^2
control_acceleration = np.diff(control_speed_kmh / 3.6) / delta_t
regen_acceleration = np.diff(regen_speed_kmh / 3.6) / delta_t

# note: force is signed -- expect regen_force_n to be more negative
control_force_n = control_acceleration / brightside_constants["vehicle_mass"]
regen_force_n = regen_acceleration / brightside_constants["vehicle_mass"]

regen_only_force_n = regen_force_n - control_force_n

# plt.plot(control_acceleration, label="control_acceleration")
# plt.plot(regen_acceleration, label="regen_acceleration")
plt.plot(control_force_n, label="control_force")
plt.plot(regen_force_n, label="regen_force")
plt.plot(regen_only_force_n, label="regen_only_force_n")
plt.plot(smooth_curve_from_list([0, 0], 100), label="zero")

plt.legend(loc='best')
plt.show()