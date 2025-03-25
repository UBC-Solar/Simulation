from simulation.config.models import Config, ConfigDict, CompetitionConfig, WeatherQuery


class EnvironmentConfig(Config):
    """
    Configuration object which describes the environment of a simulation (weather, route, competition).

    We can't actually "specify" the weather we want like we can a route, so we specify how the weather forecasts
    should be queried.
    """
    model_config = ConfigDict(frozen=True)

    competition_config: (
        CompetitionConfig  # The competition that data is being requisitioned for
    )
    weather_query_config: WeatherQuery
