from simulation.main.Simulation import Simulation, SimulationReturnType
from abc import ABC


class SimulationBuilder:
    """

    This builder class is used to easily set the parameters and conditions of Simulation.

    """
    def __init__(self):

        # Initial Conditions
        self.origin_coord = None
        self.dest_coord = None
        self.current_coord = None
        self.waypoints = None

        self.start_hour = None

        self.initial_battery_charge = None

        self.gis_force_update = None
        self.weather_force_update = None

        # Model Parameters
        self.race_type = None
        self.lvs_power_loss = None
        self.tick = None
        self.simulation_duration = None

        # Execution Parameters
        self.golang = None
        self.return_type = None
        self.granularity = None

    def set_initial_conditions(self, args):
        self.current_coord = args["current_coord"]

        self.start_hour = args["start_hour"]

        self.initial_battery_charge = args["initial_battery_charge"]

        self.gis_force_update = args["gis_force_update"]
        self.weather_force_update = args["weather_force_update"]

        return self

    def set_model_parameters(self, args, race_type):
        self.origin_coord = args["origin_coord"]
        self.dest_coord = args["dest_coord"]
        self.waypoints = args["waypoints"]

        self.race_type = race_type
        self.lvs_power_loss = args['lvs_power_loss']
        self.tick = args['tick']
        self.simulation_duration = args['simulation_duration']

        return self

    def set_golang(self, golang):
        self.golang = golang

        return self

    def set_return_type(self, return_type):
        self.return_type = SimulationReturnType(return_type.value)
        #                        ^^^^^^^^^^^^^^^^^^^^^^^^^
        # Necessary for this awkward conversion as for some reason, return_type
        # is not recognized as a SimulationReturnType.

        return self

    def set_granularity(self, granularity):
        self.granularity = granularity

        return self

    def get(self):
        return Simulation(self)


class StandardVehicle(ABC):
    """

    This class will hold constants that apply to any vehicle in the future.

    """
    def __init__(self):
        self.dynamic_friction = None


class Daybreak(StandardVehicle):
    """

    This class will hold vehicle constants in the future.

    """
    def __init__(self):
        super().__init__()
        self.vehicle_mass = None


class Brightside(StandardVehicle):
    """

    This class will hold vehicle constants in the future.

    """

    def __init__(self):
        super().__init__()
        self.vehicle_mass = None


