import numpy as np
from numpy.polynomial import Polynomial

"""
This class stores equations that have been generated through curve fitting to datasheets.
"""


class DayBreakEquations:
    # ----  Motor Equations  ----
    @staticmethod
    def calculate_motor_efficiency(motor_output_power, revolutions_per_minute):
        return 0.7382 - (6.281e-5 * motor_output_power) + (6.708e-4 * revolutions_per_minute) \
        - (2.89e-8 * motor_output_power ** 2) + (2.416e-7 * motor_output_power * revolutions_per_minute) \
        - (8.672e-7 * revolutions_per_minute ** 2) + (5.653e-12 * motor_output_power ** 3) \
        - (1.74e-11 * motor_output_power ** 2 * revolutions_per_minute) \
        - (7.322e-11 * motor_output_power * revolutions_per_minute ** 2) \
        + (3.263e-10 * revolutions_per_minute ** 3)

    @staticmethod
    def calculate_motor_controller_efficiency(motor_angular_speed, motor_torque_array):
        return 0.7694 + (0.007818 * motor_angular_speed) + (0.007043 * motor_torque_array) \
        - (1.658e-4 * motor_angular_speed ** 2) - (1.806e-5 * motor_torque_array * motor_angular_speed) \
        - (1.909e-4 * motor_torque_array ** 2) + (1.602e-6 * motor_angular_speed ** 3) \
        + (4.236e-7 * motor_angular_speed ** 2 * motor_torque_array) \
        - (2.306e-7 * motor_angular_speed * motor_torque_array ** 2) \
        + (2.122e-06 * motor_torque_array ** 3) - (5.701e-09 * motor_angular_speed ** 4) \
        - (2.054e-9 * motor_angular_speed ** 3 * motor_torque_array) \
        - (3.126e-10 * motor_angular_speed ** 2 * motor_torque_array ** 2) \
        + (1.708e-09 * motor_angular_speed * motor_torque_array ** 3) \
        - (8.094e-09 * motor_torque_array ** 4)

    # ---- Battery Equations ----
    @staticmethod
    def calculate_voltage_from_discharge_capacity():
        return Polynomial([117.6, -0.858896])  # -0.8589x + 117.6

    @staticmethod
    def calculate_energy_from_discharge_capacity():
        return Polynomial([0, 117.6, -0.429448])  # -0.4294x^2 + 117.6x

    @staticmethod
    def calculate_soc_from_discharge_capacity(max_current_capacity):
        return Polynomial([1, -1 / max_current_capacity])

    @staticmethod
    def calculate_discharge_capacity_from_soc(max_current_capacity):
        return Polynomial([max_current_capacity, -max_current_capacity])

    @staticmethod
    def calculate_discharge_capacity_from_energy():
        return lambda x: 136.92 - np.sqrt(18747.06027 - 2.32857 * x)
