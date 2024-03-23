import tomllib
import pathlib


class Connect:
    def __init__(self, service):
        self.service = service

        with open(pathlib.Path(__file__).parent / 'network.toml', 'rb') as config_file:
            config = tomllib.load(config_file)

            self.evolution_root_id = config['locations']['EVOLUTION_ROOT_ID']
            self.evolution_number_id = config['locations']['EVOLUTION_NUMBER_ID']
            self.evolution_browser_id = config['locations']['EVOLUTION_BROWSER_ID']

            self.last_evolution_path = (pathlib.Path(__file__).parent / "last_evolution.txt").resolve()
            self.evolution_browser_path = (pathlib.Path(__file__).parent / "evolution_browser.csv").resolve()
