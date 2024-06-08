"""

Compute Brightside regen efficiency based on recorded experimental data

All data in SI units unless specified otherwise

"""

import os
import json
import numpy as np
from matplotlib import pyplot as plt
from scipy.interpolate import CubicSpline
from SampleRegenData import SampleGenerator
from simulation.config import config_directory

bs_config_path = os.path.join(config_directory, "BrightSide.json")
with open(bs_config_path) as f:
    brightside_constants = json.load(f)


# --------------------------------------- define conversion functions ---------------------------------------

def a_of_v_control_cs(v_kmh):
    return a_control_kmhs_cs(t_of_v_control_cs(v_kmh)) / 3.6


def a_of_v_regen_cs(v_kmh):
    return a_regen_kmhs_cs(t_of_v_regen_cs(v_kmh)) / 3.6


def electric_p_of_v(v_kmh):
    return regen_power_cs(t_of_v_regen_cs(v_kmh))


def control_kinetic_p_of_v(v_kmh):
    """

    Args:
        v_kmh: velocity in kilometers per hour

    Returns: kinetic deceleration power in W when the car was at v=v_kmh in control test

    Uses kinetic power formula P=Fv=mav

    """
    return np.abs(brightside_constants["vehicle_mass"] * a_of_v_control_cs(v_kmh) * v_kmh / 3.6)


def regen_kinetic_p_of_v(v_kmh):
    """

    Args:
        v_kmh: velocity in kilometers per hour

    Returns: kinetic deceleration power in W when the car was at v=v_kmh in regen test

    Uses kinetic power formula P=Fv=mav

    """
    return np.abs(brightside_constants["vehicle_mass"] * a_of_v_regen_cs(v_kmh) * v_kmh / 3.6)


def regen_only_kinetic_p_of_v(v_kmh):
    """

    Args:
        v_kmh: velocity in kilometers per hour

    Returns: regen force isolated kinetic deceleration power in W when the car was at v=v_kmh

    Uses kinetic power formula P=Fv=mav

    """
    return np.abs(
        brightside_constants["vehicle_mass"] * (a_of_v_regen_cs(v_kmh) - a_of_v_control_cs(v_kmh)) * v_kmh / 3.6)


# --------------------------------------- generate placeholder data -----------------------------------------

placeholder_data = SampleGenerator(100, 5, 40)

# list of timestamps for data
times = placeholder_data.times

v_control_kmh = placeholder_data.v_control_kmh
v_regen_kmh = placeholder_data.v_regen_kmh
regen_current = placeholder_data.regen_current
battery_voltage = placeholder_data.battery_voltage
regen_power = placeholder_data.regen_power

print("Control speeds:\n", v_control_kmh)
print("Regen speeds:\n", v_regen_kmh)
print("Regen currents:\n", regen_current)
print("Battery voltages:\n", battery_voltage)
print("Regen power:\n", regen_power)

# plt.scatter(v_control_kmh[:, 0], v_control_kmh[:, 1], label="v_control_kmh")
# plt.scatter(v_regen_kmh[:, 0], v_regen_kmh[:, 1], label="v_regen_kmh")
# plt.scatter(regen_current[:, 0], regen_current[:, 1], label="regen_current")
# plt.scatter(battery_voltage[:, 0], battery_voltage[:, 1], label="battery_voltage")
# plt.scatter(regen_power[:, 0], regen_power[:, 1], label="regen_power")

# --------------------------------------- derive values -----------------------------------------

# we must cut off the part where zero values repeat to invert
control_not_repeating = np.diff(v_control_kmh[:, 1]) != 0
control_not_repeating = np.insert(control_not_repeating, 0, True)
v_control_kmh_invertible = v_control_kmh[control_not_repeating]

regen_not_repeating = np.diff(v_regen_kmh[:, 1]) != 0
regen_not_repeating = np.insert(regen_not_repeating, 0, True)
v_regen_kmh_invertible = v_regen_kmh[regen_not_repeating]

v_control_cs = CubicSpline(v_control_kmh[:, 0], v_control_kmh[:, 1], )
t_of_v_control_cs = CubicSpline(np.flip(v_control_kmh_invertible[:, 1]), np.flip(v_control_kmh_invertible[:, 0]),
                                extrapolate=False)

v_regen_cs = CubicSpline(v_regen_kmh[:, 0], v_regen_kmh[:, 1], )
t_of_v_regen_cs = CubicSpline(np.flip(v_regen_kmh_invertible[:, 1]), np.flip(v_regen_kmh_invertible[:, 0]),
                              extrapolate=False)

# plt.scatter(times, v_control_cs(times), label="v_control_cs", marker="+")
# plt.scatter(times, v_regen_cs(times), label="v_regen_cs", marker="+")
# # plot inverse on flipped axes to show that curves align
# plt.scatter(t_of_v_control_cs(v_control_kmh[:, 1]), v_control_kmh[:, 1], label="t_of_v_control_cs", alpha=0.5)
# plt.scatter(t_of_v_regen_cs(v_regen_kmh[:, 1]), v_regen_kmh[:, 1], label="t_of_v_regen_cs", alpha=0.5)

# # given a velocity in kmh, determine when that velocity was reached in the test
# plt.scatter(v_control_kmh[:, 1], t_of_v_control_cs(v_control_kmh[:, 1]), label="t_of_v_control_cs", alpha=0.5)
# plt.scatter(v_regen_kmh[:, 1], t_of_v_regen_cs(v_regen_kmh[:, 1]), label="t_of_v_regen_cs", alpha=0.5)

# !! acceleration in km/h/s !!
a_control_kmhs_cs = v_control_cs.derivative()
a_regen_kmhs_cs = v_regen_cs.derivative()

# plt.scatter(v_control_kmh[:, 0], v_control_kmh[:, 1], label="v_control_kmh")
# plt.scatter(v_regen_kmh[:, 0], v_regen_kmh[:, 1], label="v_regen_kmh")
# plt.scatter(times, a_control_kmhs_cs(times), label="a_control_cs", marker="+")
# plt.scatter(times, a_regen_kmhs_cs(times), label="a_regen_cs", marker="+")

test_velocities = np.arange(1, 40, 1)

# # plot acceleration as a function of velocity
# plt.scatter(test_velocities, a_of_v_control_cs(test_velocities), label="a_of_v_control_cs", alpha=0.5)
# plt.scatter(test_velocities, a_of_v_regen_cs(test_velocities), label="a_of_v_regen_cs", alpha=0.5)

regen_power_cs = CubicSpline(regen_power[:, 0], regen_power[:, 1])

fig, ax1 = plt.subplots()
ax1.scatter(test_velocities, control_kinetic_p_of_v(test_velocities), label="control_kinetic_p_of_v", alpha=0.5)
ax1.scatter(test_velocities, regen_kinetic_p_of_v(test_velocities), label="regen_kinetic_p_of_v", alpha=0.5)
ax1.scatter(test_velocities, regen_only_kinetic_p_of_v(test_velocities), label="regen_only_kinetic_p_of_v", alpha=0.5)
ax1.scatter(test_velocities, electric_p_of_v(test_velocities), label="electric_p_of_v", alpha=0.5)
ax2 = ax1.twinx()
ax2.scatter(test_velocities, electric_p_of_v(test_velocities)/regen_only_kinetic_p_of_v(test_velocities)*100,
            label="efficiency", alpha=0.5, color='red')
ax2.set_ylim(0, 100)  # Setting the secondary y-axis limit from 0 to 100
# Combine legends from both axes
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
fig.tight_layout()  # Adjust layout to make room for secondary axis


plt.show()
