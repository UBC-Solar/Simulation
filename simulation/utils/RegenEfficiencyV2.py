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


# --------------------------------------- generate placeholder data -----------------------------------------

# each tuple: (speed in kmh, time in s)

num_points = 100
test_duration_s = 5

times = np.arange(0, test_duration_s, test_duration_s/num_points)

control_speeds = np.zeros(num_points)
regen_speeds = np.zeros(num_points)

INITIAL_SPEED = 40

control_speed_kmh = INITIAL_SPEED
regen_speed_kmh = INITIAL_SPEED

assert len(control_speeds) == num_points
assert len(regen_speeds) == len(control_speeds)

# generate speed array which decays from initial speed_kmh to zero
for i in range(num_points):
    control_speeds[i] = control_speed_kmh
    regen_speeds[i] = regen_speed_kmh

    control_speed_kmh *= 0.97
    regen_speed_kmh *= 0.95

    if control_speed_kmh >= 0.4:
        control_speed_kmh -= 0.4
    else:
        control_speed_kmh = 0

    if regen_speed_kmh >= 0.6:
        regen_speed_kmh -= 0.6
    else:
        regen_speed_kmh = 0

v_control_kmh = np.stack((control_speeds, times), axis=1)
v_regen_kmh = np.stack((regen_speeds, times), axis=1)

print("Control speeds:\n", v_control_kmh)
print("Regen speeds:\n", v_regen_kmh)


# --------------------------------------- derive values -----------------------------------------


# we must cut off the part where zero values repeat to invert
not_repeating = np.insert(np.diff(v_control_kmh[:, 0]) != 0, True, 0)
v_control_kmh = v_control_kmh[not_repeating]

v_control_cs = CubicSpline(v_control_kmh[:, 1], v_control_kmh[:, 0],)
t_of_v_control_cs = CubicSpline(np.flip(v_control_kmh[:, 0]), np.flip(v_control_kmh[:, 1]), extrapolate=False)

plt.plot(v_control_cs(times), label="v_control_cs")
plt.plot(1000*t_of_v_control_cs(np.arange(0, INITIAL_SPEED, 1)), label="1000*t_of_v_control_cs")


plt.legend(loc="best")
plt.show()

