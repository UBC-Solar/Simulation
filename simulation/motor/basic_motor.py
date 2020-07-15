from simulation.motor.base_motor import BaseMotor


class BasicMotor(BaseMotor):

    def __init__(self):
        super().__init__()

        # Instantaneous voltage supplied by the battery to the motor controller
        self.dc_v = 0

        # Instantaneous current supplied by the battery to the motor controller
        self.dc_i = 0

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

    # Calculates the power transferred to the wheel by the motor and the motor controller
    def calculate_power_out(self):
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
        self.dc_v = dc_v
        self.dc_i = dc_i

    def calculate_power_in(self, required_speed_kmh):
        required_speed_ms = required_speed_kmh / 3.6
        required_angular_speed_rads = required_speed_ms / self.tire_radius

        drag_force = 0.5 * self.air_density * (
                    required_speed_ms ** 2) * self.drag_coefficient * self.vehicle_frontal_area

        motor_output_power = required_angular_speed_rads * (self.friction_force + drag_force)

        motor_input_power = motor_output_power / self.e_m

        self.input_power = motor_input_power / self.e_mc

    def update(self, tick):
        # For the motor, the update tick calculates a value for the energy expended in a period of time

        self.consumed_energy = self.input_power * tick

    def __str__(self):
        return(f"Tire radius: {self.tire_radius}m\n"
               f"Rolling resistance coefficient: {self.road_friction}\n"
               f"Vehicle mass: {self.vehicle_mass}kg\n"
               f"Acceleration of gravity: {self.acceleration_g}m/s^2\n"
               f"Motor controller efficiency: {self.e_mc}%\n"
               f"Motor efficiency: {self.e_m}%\n")
