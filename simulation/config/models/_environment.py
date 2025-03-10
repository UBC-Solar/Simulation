from simulation.config.models import Config, ConfigDict, CompetitionConfig, WeatherQuery
from anytree.exporter import DotExporter


class EnvironmentConfig(Config):
    model_config = ConfigDict(frozen=True)

    competition_config: CompetitionConfig  # The competition that data is being requisitioned for
    weather_query_config: WeatherQuery


if __name__ == "__main__":
    tree = EnvironmentConfig.tree()

    try:
        DotExporter(tree).to_picture("tree.png")

    except FileNotFoundError:
        print("GraphiViz is missing, and is a system dependency to build the configuration tree!")
