import math
import numpy as np

from simulation.motor.base_motor import BaseMotor


class BasicMotor(BaseMotor):

    def __init__(self):
        super().__init__()

        # Instantaneous voltage supplied by the battery to the motor controller
        self.dc_v = 0

        # Instantaneous current supplied by the battery to the motor controller
        self.dc_i = 0

        # TODO: organize this mess
        self.input_power = 0
        self.vehicle_mass = 250
        self.acceleration_g = 9.81
        self.road_friction = 0.0055
        self.tire_radius = 0.2032

        self.air_density = 1.225
        self.vehicle_frontal_area = 0.952
        self.drag_coefficient = 0.223

        self.friction_force = (self.vehicle_mass * self.acceleration_g * self.road_friction)

        self.e_mc = 0.98  # motor controller efficiency, subject to change
        self.e_m = 0.9  # motor efficiency, subject to change

        # print("torque experienced by motor: {} Nm".format(self.constant_torque))

    def calculate_power_out(self):
        """
        Calculates the power transferred to the wheel by the motor and the motor controller
    
        returns: the power transferred to the wheel in W
        """
        power_in = self.dc_v * self.dc_i
        power_controller = power_in * self.e_mc

        # alternatively, power_controller = sqrt(3) / 2 * Vrms * Irms
        power_out = power_controller * self.e_m

        # alternatively, power_out = torque * Revolutions/min = Force* V_car
        # torque = rwheel * Forcewheel, RPM = V/rwheel

        return power_out

    # For the motor, the energy consumed by the motor/motor controller depends on the voltage and
    #   current supplied by the battery to the motor controller
    def update_motor_input(self, dc_v, dc_i):
        """
        For the motor, the energy consumed by the motor/motor controller depends on the voltage 
            and current supplied by the battery to the motor controller
        """

        self.dc_v = dc_v
        self.dc_i = dc_i

    def calculate_power_in(self, required_speed_kmh, gradient, wind_speed):
        """
        For a given road gradient, calculate the power that must be inputted into
            the motor to maintain a required speed

        :param required_speed_kmh: required speed in km/h
        :param gradient: road gradient, where > 0 means uphill and < 0 means downhill
        :param wind_speed: speed of wind in m/s, where > 0 means against the direction of the vehicle.

        returns: power required to travel at a speed and gradient in W
        """

        required_speed_ms = required_speed_kmh / 3.6
        required_angular_speed_rads = required_speed_ms / self.tire_radius

        drag_force = 0.5 * self.air_density * (
                (required_speed_ms + wind_speed) ** 2) * self.drag_coefficient * self.vehicle_frontal_area

        g_force = self.vehicle_mass * self.acceleration_g * gradient

        motor_output_power = required_angular_speed_rads * (self.friction_force + drag_force + g_force)

        motor_input_power = motor_output_power / self.e_m

        self.input_power = motor_input_power / self.e_mc

    def update(self, tick):
        """
        For the motor, the update tick calculates a value for the energy expended in a period
            of time.
        
        :param tick: length of 1 update cycle in seconds
        """

        self.consumed_energy = self.input_power * tick

    @staticmethod
    def calculate_motor_efficiency(motor_angular_speed, motor_output_energy, tick):
        """
        Calculates a NumPy array of motor efficiency from NumPy array of operating angular speeds and NumPy array
            of output power. Based on data obtained from NGM SC-M150 Datasheet and modelling done in MATLAB

        r squared value: 0.873

        :param motor_angular_speed: (float[N]) angular speed motor operates in rad/s
        :param motor_output_energy: (float[N]) energy motor outputs to the wheel in J
        :param tick: length of 1 update cycle in seconds

        :returns e_m: (float[N]) efficiency of the motor
        """

        # Power = Energy / Time
        motor_output_power = motor_output_energy * tick
        rads_rpm_conversion_factor = 30 / math.pi

        revolutions_per_minute = motor_angular_speed * rads_rpm_conversion_factor

        e_m = 0.7382 - (6.281e-5 * motor_output_power) + (6.708e-4 * revolutions_per_minute) \
              - (2.89e-8 * motor_output_power ** 2) + (2.416e-7 * motor_output_power * revolutions_per_minute) \
              - (8.672e-7 * revolutions_per_minute ** 2) + (5.653e-12 * motor_output_power ** 3) \
              - (1.74e-11 * motor_output_power ** 2 * revolutions_per_minute) \
              - (7.322e-11 * motor_output_power * revolutions_per_minute ** 2) \
              + (3.263e-10 * revolutions_per_minute ** 3)

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

        :param motor_angular_speed: (float[N]) angular speed motor operates in rad/s
        :param motor_output_energy: (float[N]) energy motor outputs to the wheel in J
        :param tick: length of 1 update cycle in seconds

        :returns e_mc (float[N]) efficiency of the motor controller

        """

        # Ignore nan warning. Set nan value to 0
        np.seterr(divide='ignore', invalid='ignore')

        # Power = Energy / Time
        motor_output_power = motor_output_energy / tick

        # Torque = Power / Angular Speed
        motor_torque_array = np.nan_to_num(motor_output_power / motor_angular_speed)

        np.seterr(divide='warn', invalid='warn')

        e_mc = 0.7694 + (0.007818 * motor_angular_speed) + (0.007043 * motor_torque_array) \
               - (1.658e-4 * motor_angular_speed ** 2) - (1.806e-5 * motor_torque_array * motor_angular_speed) \
               - (1.909e-4 * motor_torque_array ** 2) + (1.602e-6 * motor_angular_speed ** 3) \
               + (4.236e-7 * motor_angular_speed ** 2 * motor_torque_array) \
               - (2.306e-7 * motor_angular_speed * motor_torque_array ** 2) \
               + (2.122e-06 * motor_torque_array ** 3) - (5.701e-09 * motor_angular_speed ** 4) \
               - (2.054e-9 * motor_angular_speed ** 3 * motor_torque_array) \
               - (3.126e-10 * motor_angular_speed ** 2 * motor_torque_array ** 2) \
               + (1.708e-09 * motor_angular_speed * motor_torque_array ** 3) \
               - (8.094e-09 * motor_torque_array ** 4)

        e_mc[e_mc < 0.9] = 0.9
        e_mc[e_mc > 1] = 1

        return e_mc

    def calculate_energy_in(self, required_speed_kmh, gradients, wind_speeds, tick):
        """
        Create a function which takes in array of elevation, array of wind speed, required
            speed, returns the consumed energy.

        :param required_speed_kmh: (float[N]) required speed array in km/h
        :param gradients: (float[N]) gradient at parts of the road
        :param wind_speeds: (float[N]) speeds of wind in m/s, where > 0 means against the direction of the vehicle
        :param tick: (int) length of 1 update cycle in seconds

        returns: (float[N]) energy expended by the motor at every tick
        """

        required_speed_ms = required_speed_kmh / 3.6

        required_angular_speed_rads = required_speed_ms / self.tire_radius
        required_angular_speed_rads_array = np.ones(len(gradients)) * required_angular_speed_rads

        drag_forces = 0.5 * self.air_density * (
                (required_speed_ms + wind_speeds) ** 2) * self.drag_coefficient * self.vehicle_frontal_area

        angles = np.arctan(gradients)
        g_forces = self.vehicle_mass * self.acceleration_g * np.sin(angles)

        road_friction_array = np.full_like(g_forces, fill_value=self.road_friction)
        road_friction_array = road_friction_array * self.vehicle_mass * self.acceleration_g * np.cos(angles)

        motor_output_energies = required_angular_speed_rads_array * (
                road_friction_array + drag_forces + g_forces) * self.tire_radius * tick

        e_m = self.calculate_motor_efficiency(required_angular_speed_rads_array, motor_output_energies, tick)
        e_mc = self.calculate_motor_controller_efficiency(required_angular_speed_rads_array,
                                                          motor_output_energies, tick)

        motor_controller_input_energies = motor_output_energies / (e_m * e_mc)

        return motor_controller_input_energies

    def __str__(self):
        return (f"Tire radius: {self.tire_radius}m\n"
                f"Rolling resistance coefficient: {self.road_friction}\n"
                f"Vehicle mass: {self.vehicle_mass}kg\n"
                f"Acceleration of gravity: {self.acceleration_g}m/s^2\n"
                f"Motor controller efficiency: {self.e_mc}%\n"
                f"Motor efficiency: {self.e_m}%\n")
