"""

Compute Brightside regen efficiency based on recorded experimental data

All data in SI units unless specified otherwise

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


def diff_same_shape(array):
    return np.append(np.diff(array), 0)


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
    return np.cumsum(-1*force_decreasing(-1*diff_same_shape(dec_arr))) + arr[0]

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

assert (diff_same_shape(control_speed_kmh) <= 0).all()
assert (diff_same_shape(regen_speed_kmh) <= 0).all()
assert (battery_voltage > 0).all()

plt.plot(control_speed_kmh, label="control_speed_kmh")
plt.plot(regen_speed_kmh, label="regen_speed_kmh")
plt.plot(regen_current, label="regen_current")
plt.plot(battery_voltage, label="battery_voltage")

# --------------------------------------- derive values -----------------------------------------

# calculate acceleration in m/s^2
control_acceleration = diff_same_shape(control_speed_kmh / 3.6) / delta_t
regen_acceleration = diff_same_shape(regen_speed_kmh / 3.6) / delta_t

# F=ma
# note: force is signed -- expect regen_force_n to be more negative
control_force = control_acceleration * brightside_constants["vehicle_mass"]
regen_force = regen_acceleration * brightside_constants["vehicle_mass"]

control_kinetic_power = np.multiply(control_force, control_speed_kmh / 3.6)
regen_kinetic_power = np.multiply(regen_force, control_speed_kmh / 3.6)


# plt.plot(control_acceleration, label="control_acceleration")
# plt.plot(regen_acceleration, label="regen_acceleration")
# plt.plot(control_force, label="control_force")
# plt.plot(regen_force, label="regen_force")
# plt.plot(control_kinetic_power, label="control_kinetic_power")
# plt.plot(regen_kinetic_power, label="regen_kinetic_power")
# plt.plot(smooth_curve_from_list([0, 0], 100), label="zero")

# W = F*d --> P = F*v

'''
Invert:
	v_ctrl(t) →t(v_ctrl) done
    v_regen(t) →t(v_regen) done

Differentiate velocity:
a_ctrl(t) = v_ctrl’(t) done
a_regen(t) = v_regen ’(t) done

Composition:
    a_ctrl(t(v_ctrl)) → a_ctrl(v) done
    a_regen(t(v_ctrl)) → a_regen(v) done

I(t(v)) → I(v)
V_batt(t(v)) → V_batt(v)

Isolate regen:
	a_regen_only(v) =  a_regen(v) - a_ctrl(v)

Use kinetic power formula P=Fv=mav:
	p_kinetic_regen_only(v) = brightside_mass * a_regen_only(v) * v

Use electric power formula P = IV:
	p_electric(v) = I(v) * V_batt(v)

Efficiency(v) = p_electric(v) / p_kinetic_regen_only(v)

'''


plt.legend(loc='best')
plt.show()