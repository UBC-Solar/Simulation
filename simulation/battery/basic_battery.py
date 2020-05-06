from simulation.battery.base_battery import BaseBattery

class BasicBattery(BaseBattery):

    def __init__(self, state_of_charge):

        # DayBreak battery constants
        self.max_voltage = 117.6
        self.min_voltage = 70
        self.max_energy_capacity = 4573         # in Wh
        self.max_current_capacity = 48.75       # in Ah

        self.state_of_charge = state_of_charge                      # 0.00 <= state_of_charge <= 1.00
        self.depth_of_discharge = 1 - self.state_of_charge

        self.discharge_capacity = self.calculate_discharge_capacity_from_soc(self.state_of_charge)                                              # calculates discharge capacity from state of charge
        self.voltage = self.calculate_voltage(self.discharge_capacity)                                                                          # calculates voltage of battery from discharge capacity
        self.stored_energy = self.max_energy_capacity - self.calculate_energy_discharged_from_discharge_capacity(self.discharge_capacity)       # calculates stored energy from discharge capacity

        super().__init__(self.stored_energy, self.max_current_capacity, self.max_energy_capacity, self.max_voltage,
                         self.min_voltage, self.voltage, self.state_of_charge)

    @staticmethod
    def calculate_discharge_capacity(energy):
        return (-117.6 + pow(13829.76 - 1.952 * energy, 0.5)) / (-0.976)

    @staticmethod
    def calculate_state_of_charge(discharge_capacity):
        return 1 - (discharge_capacity / 48.75)

    @staticmethod
    def calculate_voltage(discharge_capacity):
        return 117.6 - 0.97641 * discharge_capacity

    @staticmethod
    def calculate_discharge_capacity_from_soc(state_of_charge):
        return 48.75 * (1 - state_of_charge)

    @staticmethod
    def calculate_energy_discharged_from_discharge_capacity(discharge_capacity):
        return 117.6 * discharge_capacity - 0.488 * pow(discharge_capacity, 2)

    def update(self, tick):     # updates relevant battery variables
        discharge_capacity = self.calculate_discharge_capacity(self.max_energy_capacity - self.stored_energy)
        self.state_of_charge = self.calculate_state_of_charge(discharge_capacity)
        self.voltage = self.calculate_voltage(discharge_capacity)

    def charge(self, energy):           # assuming energy parameter is in joules
        super().charge(energy / 3600)   # divide by 3600 to convert from joules to watt-hours
        #self.update(1)                  # this makes it so that the update() method need not always be called separately

    def discharge(self, energy):
        super().discharge(energy / 3600)
        #self.update(1)


# TODO: create class for energy transfer between components maybe?
