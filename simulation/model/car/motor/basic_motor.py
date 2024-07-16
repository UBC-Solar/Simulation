import math
import numpy as np

from simulation.model.car.motor.base_motor import BaseMotor
from simulation.common import DayBreak, Race, constants, DayBreakEquations

from simulation.common.race import get_slip_angle_for_tire_force, load_race

class BasicMotor(BaseMotor):

    def __init__(self):
        super().__init__()

        # Instantaneous voltage supplied by the battery to the motor controller
        self.dc_v = 0

        # Instantaneous current supplied by the battery to the motor controller
        self.dc_i = 0

        # TODO: organize this mess
        self.input_power = 0
        self.vehicle_mass = DayBreak.vehicle_mass
        self.acceleration_g = constants.ACCELERATION_G
        self.road_friction = DayBreak.road_friction
        self.tire_radius = DayBreak.tire_radius

        self.air_density = constants.AIR_DENSITY
        self.vehicle_frontal_area = DayBreak.vehicle_frontal_area
        self.drag_coefficient = DayBreak.drag_coefficient

        self.friction_force = (self.vehicle_mass * self.acceleration_g * self.road_friction)

        self.e_mc = 0.98  # motor controller efficiency, subject to change
        self.e_m = 0.9  # motor efficiency, subject to change

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

    def calculate_energy_in(self, required_speed_kmh, gradients, wind_speeds, closest_gis_indices, tick):
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

        required_speed_ms = required_speed_kmh / 3.6

        required_angular_speed_rads = required_speed_ms / self.tire_radius
        required_angular_speed_rads_array = np.ones(len(gradients)) * required_angular_speed_rads

        drag_forces = 0.5 * self.air_density * (
                (required_speed_ms + wind_speeds) ** 2) * self.drag_coefficient * self.vehicle_frontal_area

        angles = np.arctan(gradients)
        g_forces = self.vehicle_mass * self.acceleration_g * np.sin(angles)

        road_friction_array = np.full_like(g_forces, fill_value=self.road_friction)
        road_friction_array = road_friction_array * self.vehicle_mass * self.acceleration_g * np.cos(angles)
        
        cornering_friction_work = calculate_cornering_losses(required_speed_kmh, closest_gis_indices, tick)

        motor_output_energies = required_angular_speed_rads_array * (
                road_friction_array + drag_forces + g_forces) * self.tire_radius * tick + cornering_friction_work

        e_m = self.calculate_motor_efficiency(required_angular_speed_rads_array, motor_output_energies, tick)
        e_mc = self.calculate_motor_controller_efficiency(required_angular_speed_rads_array,
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
    

def calculate_cornering_losses(required_speed_kmh, closest_gis_indices, tick):
    # hard coded for FSGP
    current_race = load_race(Race.FSGP)
    # gis_indicies don't reset per lap
    wrapped_indices = closest_gis_indices % current_race.cornering_radii.size
    cornering_radii = current_race.cornering_radii[wrapped_indices]
    required_speed_ms = required_speed_kmh / 3.6
    centripetal_lateral_force = DayBreak.vehicle_mass * (required_speed_ms ** 2) / cornering_radii
    slip_angles_degrees = get_slip_angle_for_tire_force(centripetal_lateral_force)
    slip_angles_radians = np.radians(slip_angles_degrees)

    
    slip_distances = np.tan(slip_angles_radians) * required_speed_ms * tick
    # for i in range(slip_angles_radians.size):
    #     print(f"Slip angle (degrees): {slip_angles_degrees[i]:.6f}")
    #     print(f"Slip angle (radians): {slip_angles_radians[i]:.6f}")
    #     print(f"Slip distance (meters): {slip_distances[i]:.6f}")
    #     print(f"Speed at this point (m/s): {required_speed_ms[i]:.6f}")
    #     print()
    cornering_friction_work = slip_distances * centripetal_lateral_force
    print("total slip distances: ")
    print(np.sum(slip_distances))
    print("\ntotal cornering_firction_work: ")
    print(np.sum(cornering_friction_work))
    print("\n")

    #   # Check for values above 8000 in centripetal_lateral_force
    # for i, force in enumerate(centripetal_lateral_force):
    #     if force > 8000:
    #         print(f"High centripetal force detected: {force} N")
    #         print(f"Speed: {required_speed_ms[i]} m/s")
    #         print(f"Cornering Radius: {cornering_radii[i]} m")
    #         print("\n \n")
    # Plotting the slip angles
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 6))
    plt.plot(slip_angles_degrees, marker='o', linestyle='-', color='b')
    plt.title('plot')
    plt.xlabel('index')
    plt.ylabel('value')
    plt.grid(True)
    plt.show()