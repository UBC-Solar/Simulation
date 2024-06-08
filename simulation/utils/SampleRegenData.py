import numpy as np
from scipy.interpolate import CubicSpline


class SampleGenerator:
    """
    Generate sample data from regen testing.

    Outputs numpy arrays of tuples, where each tuple is in the form (timestamp, value).
    """

    def __init__(self, num_points, test_duration_s, initial_speed_kmh):
        self.num_points = num_points
        self.test_duration_s = test_duration_s

        self.tick_s = self.test_duration_s / self.num_points

        self.times = np.arange(0, test_duration_s, self.tick_s)

        self.INITIAL_SPEED = initial_speed_kmh

        self.v_control_kmh = self.get_control_speed_kmh()
        self.v_regen_kmh = self.get_regen_speed_kmh()
        self.regen_current = self.get_regen_current()
        self.battery_voltage = self.get_battery_voltage()
        self.regen_power = self.get_regen_power()

    def get_control_speed_kmh(self):
        control_speed_kmh = self.INITIAL_SPEED
        control_speeds = np.zeros(self.num_points)

        assert len(control_speeds) == self.num_points

        # generate speed array which decays from initial speed_kmh to zero
        for i in range(self.num_points):
            control_speeds[i] = control_speed_kmh

            control_speed_kmh *= 0.97

            if control_speed_kmh >= 0.3:
                control_speed_kmh -= 0.3
            else:
                control_speed_kmh = 0

        return np.stack((self.times, control_speeds), axis=1)

    def get_regen_speed_kmh(self):
        regen_speed_kmh = self.INITIAL_SPEED
        regen_speeds = np.zeros(self.num_points)

        assert len(regen_speeds) == self.num_points

        # generate speed array which decays from initial speed_kmh to zero
        for i in range(self.num_points):
            regen_speeds[i] = regen_speed_kmh

            regen_speed_kmh *= 0.97

            if regen_speed_kmh >= 0.6:
                regen_speed_kmh -= 0.6
            else:
                regen_speed_kmh = 0

        return np.stack((self.times, regen_speeds), axis=1)

    @staticmethod
    def _smooth_curve_from_list(values, target_len):
        keys = np.linspace(0, 1, num=len(values))
        smooth_keys = np.linspace(0, 1, num=target_len)

        cs = CubicSpline(keys, values)
        smooth_values = cs(smooth_keys)

        return smooth_values
    
    def get_regen_current(self):
        regen_current_values = self._smooth_curve_from_list([35, 14, 4, 2, 1, 0, 0, 0, 0, 0, 0], self.num_points)
        return np.stack((self.times, regen_current_values), axis=1)
    
    def get_battery_voltage(self):
        battery_voltage_values = self._smooth_curve_from_list([103, 104, 108, 108, 103, 103, 103, 103, 103, 103], self.num_points)
        return np.stack((self.times, battery_voltage_values), axis=1)

    def get_regen_power(self):
        regen_current_values = self._smooth_curve_from_list([25, 14, 2, 0, 0, 0, 0, 0, 0, 0, 0], self.num_points)
        battery_voltage_values = self._smooth_curve_from_list([103, 104, 108, 108, 103, 103, 103, 103, 103, 103], self.num_points)
        return np.stack((self.times, np.multiply(regen_current_values, battery_voltage_values)), axis=1)
