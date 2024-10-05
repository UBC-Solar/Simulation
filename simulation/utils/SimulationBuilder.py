import json

from simulation.cmd.run_simulation import RaceDataNotMatching
from simulation.config import config_directory
from simulation.model.Simulation import Simulation, SimulationReturnType


class SimulationBuilder:
    """

    This builder class is used to easily set the parameters and conditions of Simulation.

    """
    def __init__(self):

        # Initial Conditions
        self.current_coord = None
        self.start_time = None
        self.initial_battery_charge = None

        # Model Parameters
        self.race_type = None
        self.origin_coord = None
        self.dest_coord = None
        self.waypoints = None
        self.race_duration = None
        self.lvs_power_loss = None
        self.tick = None
        self.weather_provider = None

        # Execution Parameters
        self.return_type = None
        self.granularity = None

    def set_initial_conditions(self, args):
        self.current_coord = args["current_coord"]
        self.start_time = int(args["start_time"]) + int(args["timezone_offset"])
        self.initial_battery_charge = args["initial_battery_charge"]

        return self

    def set_model_parameters(self, args, race_type):
        self.origin_coord = args["origin_coord"]
        self.dest_coord = args["dest_coord"]
        self.waypoints = args["waypoints"]

        self.race_type = race_type
        self.lvs_power_loss = args['lvs_power_loss']
        self.tick = args['tick']
        self.weather_provider = args['weather_provider']
        self.race_duration = len(args['days'])

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
        param1 = self.race_constants()
        config_path = config_directory / f"settings_{self.race_type}.json"
        with open(config_path) as f:
            param2 = json.load(f)
        if param1 == param2:
            return Simulation(self)
        else:
            raise RaceDataNotMatching

