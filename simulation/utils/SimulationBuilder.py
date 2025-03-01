import pathlib

from simulation.model.Simulation import Simulation, SimulationReturnType
from simulation.utils.hash_util import hash_dict
from simulation.config import CompetitionConfig, InitialConditions
from simulation.cache import simulation_cache, Cache
from simulation.common import Race


class RaceDataNotMatching(Exception):
    "Raised when race data does not match config data"
    pass


class SimulationBuilder:
    """

    This builder class is used to easily set the parameters and conditions of Simulation.

    """
    def __init__(self, cache: Cache = None):
        self._cache: Cache = cache if cache is not None else simulation_cache

        self.model_parameters = None
        self.race_data = None
        self.route_data = None
        self.weather_forecasts = None

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

    def set_initial_conditions(self, initial_conditions: InitialConditions):
        self.current_coord = initial_conditions.current_coord
        self.start_time = initial_conditions.start_time
        self.initial_battery_charge = initial_conditions.initial_battery_soc

        return self

    @staticmethod
    def _truncate_hash(hashed: int, num_chars: int = 12) -> str:
        return str(hashed)[:num_chars]

    def set_competition(self, competition_config: CompetitionConfig):
        competition_hash = SimulationBuilder._truncate_hash(hash(competition_config))

        # Try to find cached race data
        try:
            race = self._cache.get(pathlib.Path("race") / competition_hash)

        # Generate new race data
        except KeyError:
            race = Race(competition_config)
            self._cache.put(race, pathlib.Path("race"))

            print(f"Compiling {race.race_type} race")

        self.race_data = race

        return self

    def set_model_parameters(self, args, race_type):
        # NOTE: cannibalize most of this
        self.origin_coord = args["origin_coord"]
        self.dest_coord = args["dest_coord"]
        self.waypoints = args["waypoints"]

        self.race_type = race_type
        self.lvs_power_loss = args['lvs_power_loss'] # This stuff should go to some model building thing
        self.tick = args['tick']
        self.weather_provider = args['weather_provider']
        self.race_duration = len(args['days'])
        self.model_parameters = args

        return self

    def set_return_type(self, return_type):
        # Merge this crap into some "hyperparameters" thing
        self.return_type = SimulationReturnType(return_type.value)
        #                        ^^^^^^^^^^^^^^^^^^^^^^^^^
        # Necessary for this awkward conversion as for some reason, return_type
        # is not recognized as a SimulationReturnType.

        return self

    def set_granularity(self, granularity):
        # Merge this crap into some "hyperparameters" thing
        self.granularity = granularity

        return self

    def set_race_data(self, race_data):
        # I think this should go away
        self.race_data = race_data

        return self

    def set_route_data(self, route_data):
        # Cache stuff
        self.route_data = route_data

        return self

    def set_weather_forecasts(self, weather_forecasts):
        # Cache stuff
        self.weather_forecasts = weather_forecasts

        return self

    def get(self):
        """
        Returns a Simulation object if race data matches the model parameters' hash.
        Compares the hash of race data with model parameters. Raises RaceDataNotMatching if they differ.

        Returns:
            Simulation: A new Simulation object.

        Raises:
            RaceDataNotMatching: If hashes do not match.
            """
        current_hash = self.race_data.race_data_hash
        new_hash = hash_dict(self.model_parameters)
        if current_hash == new_hash:
            return Simulation(self)
        else:
            raise RaceDataNotMatching
