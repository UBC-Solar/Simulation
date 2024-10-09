from simulation.common import compile_races
from simulation.cache.race import race_directory
from simulation.config import config_directory


if __name__ == "__main__":
    compile_races(config_directory, race_directory)
