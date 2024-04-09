from simulation.model.Simulation import Simulation, SimulationReturnType


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

        # Model Parameters
        self.race_type = None
        self.lvs_power_loss = None
        self.tick = None
        self.simulation_duration = None
        self.weather_provider = None

        # Execution Parameters
        self.golang = None
        self.return_type = None
        self.granularity = None

    def set_initial_conditions(self, args):
        self.current_coord = args["current_coord"]

        self.start_hour = args["start_hour"]

        self.initial_battery_charge = args["initial_battery_charge"]

        return self

    def set_model_parameters(self, args, race_type):
        self.origin_coord = args["origin_coord"]
        self.dest_coord = args["dest_coord"]
        self.waypoints = args["waypoints"]

        self.race_type = race_type
        self.lvs_power_loss = args['lvs_power_loss']
        self.tick = args['tick']
        self.simulation_duration = args['simulation_duration']
        self.weather_provider = args['weather_provider']

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
