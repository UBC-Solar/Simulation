import math
import numpy as np

from simulation.model.car.motor.base_motor import BaseMotor

from simulation.common import BrightSide, constants, DayBreakEquations

from simulation.common.race import Race
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

        # print("torque experienced by motor: {} Nm".format(self.constant_torque))

    def calculate_power_out(self):
        """

        Calculates the power transferred to the wheel by the motor and the motor controller
    
        :returns: the power transferred to the wheel in W
        :rtype: float

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

        :param np.ndarray required_speed_kmh: required speed in km/h
        :param np.ndarray gradient: road gradient, where > 0 means uphill and < 0 means downhill
        :param np.ndarray wind_speed: speed of wind in m/s, where > 0 means against the direction of the vehicle.
        :returns: power required to travel at a speed and gradient in W
        :rtype: np.ndarray

        """

        required_speed_ms = required_speed_kmh / 3.6
        required_angular_speed_rads = required_speed_ms / self.tire_radius


        # As far as I can tell, this function isn't actually being used anywhere
        # Thus these drag calculations use the old method
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
        
        :param int tick: length of 1 update cycle in seconds

        """

        self.consumed_energy = self.input_power * tick


    @staticmethod
    def calculate_motor_efficiency(motor_angular_speed, motor_output_energy, tick):
        """

        Calculates a NumPy array of motor efficiency from NumPy array of operating angular speeds and NumPy array
            of output power. Based on data obtained from NGM SC-M150 Datasheet and modelling done in MATLAB

        r squared value: 0.873

        :param np.ndarray motor_angular_speed: (float[N]) angular speed motor operates in rad/s
        :param np.ndarray motor_output_energy: (float[N]) energy motor outputs to the wheel in J
        :param float tick: length of 1 update cycle in seconds
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
        :param float tick: length of 1 update cycle in seconds
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
    
    def calculate_energy_in(self, required_speed_kmh, gradients, wind_speeds, wind_attack_angles, closest_gis_indices, tick, parameters = None):
        """

        Create a function which takes in array of elevation, array of wind speed, required
            speed, returns the consumed energy.

        :param np.ndarray required_speed_kmh: (float[N]) required speed array in km/h
        :param np.ndarray gradients: (float[N]) gradient at parts of the road
        :param np.ndarray wind_speeds: (float[N]) speeds of wind in m/s, where > 0 means against the direction of the vehicle
        :param np.ndarray wind_attack_angles: (float[N])
        :param int tick: length of 1 update cycle in seconds
        :param float tick: length of 1 update cycle in seconds
        :returns: (float[N]) energy expended by the motor at every tick
        :rtype: np.ndarray

        """
        if parameters is None:
            parameters = self.parameters

        required_speed_ms = required_speed_kmh / 3.6

        acceleration_ms2 = np.clip(np.gradient(required_speed_ms), a_min=0, a_max=None)
        acceleration_force = acceleration_ms2 * self.vehicle_mass
        acceleration_force *= np.polyval([parameters[0], parameters[1]], acceleration_ms2)

        required_angular_speed_rads = required_speed_ms / self.tire_radius


        drag_forces = BasicMotor.calculate_drag_force(wind_speeds, wind_attack_angles, required_speed_ms)
        # Old Drag Force Calculations
        # drag_forces2 = 0.5 * self.air_density * (
        #         (required_speed_ms + wind_speeds) ** 2) * self.drag_coefficient * self.vehicle_frontal_area
        
        # import matplotlib.pyplot as plt
        # plt.plot(drag_forces2)
        # plt.plot(drag_forces)
        # plt.show()

        angles = np.arctan(gradients)
        g_forces = self.vehicle_mass * self.acceleration_g * np.sin(angles)


        road_friction_array = self.road_friction * self.vehicle_mass * self.acceleration_g * np.cos(angles)

        net_force = road_friction_array + drag_forces + g_forces + acceleration_force

        cornering_friction_work = calculate_cornering_losses(required_speed_kmh, closest_gis_indices, tick)

        motor_output_energies = required_angular_speed_rads * net_force * self.tire_radius * tick + cornering_friction_work
        motor_output_energies = np.clip(motor_output_energies, a_min=0, a_max=None)
        motor_output_energies *= np.polyval([parameters[2], parameters[3]], motor_output_energies)

        e_m = self.calculate_motor_efficiency(required_angular_speed_rads, motor_output_energies, tick)
        e_mc = self.calculate_motor_controller_efficiency(required_angular_speed_rads, motor_output_energies, tick)

        motor_controller_input_energies = motor_output_energies / (e_m * e_mc)

        # Filter out and replace negative energy consumption as 0
        motor_controller_input_energies = np.where(motor_controller_input_energies > 0,
                                                   motor_controller_input_energies, 0)

        return motor_controller_input_energies

    @staticmethod
    def calculate_drag_force(wind_speeds, wind_attack_angles, required_speed_ms):
        """
                Calculate the force of drag acting in the direction opposite the movement of the car at every tick.

                :param np.ndarray wind_speeds: (float[N]) speeds of wind in m/s, where > 0 means against the direction of the vehicle
                :param np.ndarray wind_attack_angles: (float[N]) The attack angle of the wind for a given moment
                :param np.ndarray required_speed_ms: (float[N]) required speed array in m/s
                :returns: (float[N]) the drag force in Newtons at every tick of the race
                :rtype: np.ndarray

        """
        #Lookup table mapping wind angle to drag values for a wind speed of 60 km/hr. Comes from CFD simulation in the google drive.
        angle_to_unscaled_drag = {
            0: 23.41,
            18: 39.73,
            36: 101.51,
            54: 208.35,
            72: 316.84,
            90: 411.29,
            108: 352.76,
            126: 270.13,
            144: 94.67,
            162: 36.43,
            180: 23.58
        }

        drag_forces = np.zeros_like(wind_speeds, dtype=float)
        rounded_attack_angles = np.round(wind_attack_angles / 18) * 18
        unscaled_wind_drag = np.array(list(map(lambda x: angle_to_unscaled_drag[x], rounded_attack_angles)))

        # data from lookup table corresponds to wind speed of 16.667 m/s
        direction = np.sign(wind_speeds)
        wind_drag = direction * unscaled_wind_drag * (wind_speeds ** 2) / (16.667 ** 2)
        car_drag = angle_to_unscaled_drag[0] * (required_speed_ms ** 2) / (16.667 ** 2)
        drag_forces = wind_drag + car_drag

        return drag_forces


    def __str__(self):
        return (f"Tire radius: {self.tire_radius}m\n"
                f"Rolling resistance coefficient: {self.road_friction}\n"
                f"Vehicle mass: {self.vehicle_mass}kg\n"
                f"Acceleration of gravity: {self.acceleration_g}m/s^2\n"
                f"Motor controller efficiency: {self.e_mc}%\n"
                f"Motor efficiency: {self.e_m}%\n")

    
def calculate_cornering_losses(required_speed_kmh, closest_gis_indices, tick):
    required_speed_ms = required_speed_kmh / 3.6

    # hard coded for FSGP
    current_race = load_race(Race.FSGP)

    # gis_indicies don't reset per lap
    wrapped_indices = closest_gis_indices % current_race.cornering_radii.size

    cornering_radii = current_race.cornering_radii[wrapped_indices]
    centripetal_lateral_force = BrightSide.vehicle_mass * (required_speed_ms ** 2) / cornering_radii

    slip_angles_degrees = get_slip_angle_for_tire_force(centripetal_lateral_force)
    slip_angles_radians = np.radians(slip_angles_degrees)

    
    slip_distances = np.tan(slip_angles_radians) * required_speed_ms * tick
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
    # import matplotlib.pyplot as plt
    # plt.figure(figsize=(10, 6))
    # plt.plot(slip_angles_degrees, marker='o', linestyle='-', color='b')
    # plt.title('plot')
    # plt.xlabel('index')
    # plt.ylabel('value')
    # plt.grid(True)
    # plt.show()

    CORNERING_COEFFICIENT = 1
    return cornering_friction_work * CORNERING_COEFFICIENT


if __name__ == "__main__":
    motor = BasicMotor()
    energies = motor.calculate_energy_in(np.array([10, 10]), np.array([0, 0]), np.array([0, 0]), 1)
    energies = motor.calculate_energy_in(np.array([10, 10]), np.array([0, 0]), np.array([0, 0]), 1, [2.3, 1.12, 1.2, 1.233])
