import math
import numpy as np

from simulation.model.car.motor.base_motor import BaseMotor
from simulation.common import DayBreak, BrightSide, constants, DayBreakEquations
from simulation.config.coefficients import MOTOR_ACCELERATION_FACTOR, MOTOR_POWER_FACTOR

class BasicMotor(BaseMotor):

    def __init__(self):
        super().__init__()

        # Instantaneous voltage supplied by the battery to the motor controller
        self.dc_v = 0

        # Instantaneous current supplied by the battery to the motor controller
        self.dc_i = 0

        # TODO: organize this mess
        self.input_power = 0
        self.vehicle_mass = BrightSide.vehicle_mass
        self.acceleration_g = constants.ACCELERATION_G
        self.road_friction = BrightSide.road_friction
        self.tire_radius = BrightSide.tire_radius

        self.air_density = constants.AIR_DENSITY
        self.vehicle_frontal_area = BrightSide.vehicle_frontal_area
        self.drag_coefficient = BrightSide.drag_coefficient

        self.friction_force = (self.vehicle_mass * self.acceleration_g * self.road_friction)

        self.e_mc = 0.98  # motor controller efficiency, subject to change
        self.e_m = 0.9  # motor efficiency, subject to change

        self.coefficients = [MOTOR_ACCELERATION_FACTOR, MOTOR_POWER_FACTOR]

        # print("torque experienced by motor: {} Nm".format(self.constant_torque))

    @staticmethod
    def calculate_motor_efficiency(motor_angular_speed, motor_output_energy, tick):
        """

        Calculates a NumPy array of motor efficiency from NumPy array of operating angular speeds and NumPy array
            of output power. Based on data obtained from NGM SC-M150 Datasheet and modelling done in MATLAB

        r squared value: 0.873

        :param np.ndarray motor_angular_speed: (float[N]) angular speed motor operates in rad/s
        :param np.ndarray motor_output_energy: (float[N]) energy motor outputs to the wheel in J
        :param int tick: length of 1 update cycle in seconds
        :returns e_m: (float[N]) efficiency of the motor
        :rtype: np.ndarray

        """

        # Power = Energy / Time
        motor_output_power = motor_output_energy * tick
        rads_rpm_conversion_factor = 30 / math.pi

        revolutions_per_minute = motor_angular_speed * rads_rpm_conversion_factor

        e_m = DayBreakEquations.calculate_motor_efficiency(motor_output_power, revolutions_per_minute)

        e_m[e_m < 0.7382] = 0.7382
        e_m[e_m > 1] = 1

        return e_m

    @staticmethod
    def calculate_motor_controller_efficiency(motor_angular_speed, motor_output_energy, tick):
        """

        Calculates a NumPy array of motor controller efficiency from NumPy array of operating angular speeds and
        NumPy array of output power. Based on data obtained from the WaveSculptor Motor Controller Datasheet efficiency
        curve for a 90 V DC Bus and modelling done in MATLAB.

        r squared value: 0.7431

        :param np.ndarray motor_angular_speed: (float[N]) angular speed motor operates in rad/s
        :param np.ndarray motor_output_energy: (float[N]) energy motor outputs to the wheel in J
        :param int tick: length of 1 update cycle in seconds
        :returns e_mc (float[N]) efficiency of the motor controller
        :rtype: np.ndarray

        """

        # Ignore nan warning. Set nan value to 0
        np.seterr(divide='ignore', invalid='ignore')

        # Power = Energy / Time
        motor_output_power = motor_output_energy / tick

        # Torque = Power / Angular Speed
        motor_torque_array = np.nan_to_num(motor_output_power / motor_angular_speed)

        np.seterr(divide='warn', invalid='warn')

        e_mc = DayBreakEquations.calculate_motor_controller_efficiency(motor_angular_speed, motor_torque_array)

        e_mc[e_mc < 0.9] = 0.9
        e_mc[e_mc > 1] = 1

        return e_mc

    def calculate_energy_in(self, required_speed_kmh, gradients, wind_speeds, tick, coefficients = None):
        """

        Create a function which takes in array of elevation, array of wind speed, required
            speed, returns the consumed energy.

        :param np.ndarray required_speed_kmh: (float[N]) required speed array in km/h
        :param np.ndarray gradients: (float[N]) gradient at parts of the road
        :param np.ndarray wind_speeds: (float[N]) speeds of wind in m/s, where > 0 means against the direction of the vehicle
        :param int tick: length of 1 update cycle in seconds
        :returns: (float[N]) energy expended by the motor at every tick
        :rtype: np.ndarray

        """
        if coefficients is None:
            coefficients = self.coefficients

        required_speed_ms = required_speed_kmh / 3.6

        acceleration_ms2 = np.clip(np.gradient(required_speed_ms), a_min=0, a_max=None)
        acceleration_force = acceleration_ms2 * self.vehicle_mass * coefficients[0]

        required_angular_speed_rads = required_speed_ms / self.tire_radius

        drag_forces = 0.5 * self.air_density * (
                (required_speed_ms + wind_speeds) ** 2) * self.drag_coefficient * self.vehicle_frontal_area

        angles = np.arctan(gradients)
        g_forces = self.vehicle_mass * self.acceleration_g * np.sin(angles)

        road_friction_array = self.road_friction * self.vehicle_mass * self.acceleration_g * np.cos(angles)

        motor_output_energies = np.clip(required_angular_speed_rads * (
                road_friction_array + drag_forces + g_forces + acceleration_force) * self.tire_radius * tick, a_min=0, a_max=None) * coefficients[1]

        e_m = self.calculate_motor_efficiency(required_angular_speed_rads, motor_output_energies, tick)
        e_mc = self.calculate_motor_controller_efficiency(required_angular_speed_rads,
                                                          motor_output_energies, tick)

        motor_controller_input_energies = motor_output_energies / (e_m * e_mc)

        # Filter out and replace negative energy consumption as 0
        motor_controller_input_energies = np.where(motor_controller_input_energies > 0,
                                                   motor_controller_input_energies, 0)

        return motor_controller_input_energies

    def __str__(self):
        return (f"Tire radius: {self.tire_radius}m\n"
                f"Rolling resistance coefficient: {self.road_friction}\n"
                f"Vehicle mass: {self.vehicle_mass}kg\n"
                f"Acceleration of gravity: {self.acceleration_g}m/s^2\n"
                f"Motor controller efficiency: {self.e_mc}%\n"
                f"Motor efficiency: {self.e_m}%\n")
