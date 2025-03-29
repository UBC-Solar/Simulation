from simulation.config.models import Config, ConfigDict, CompetitionConfig, WeatherQuery


class EnvironmentConfig(Config):
    model_config = ConfigDict(frozen=True)

    competition_config: (
        CompetitionConfig  # The competition that data is being requisitioned for
    )
    weather_query_config: WeatherQuery
