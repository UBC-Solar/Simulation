from simulation.config.models import Config, ConfigDict, CompetitionConfig


class EnvironmentConfig(Config):
    """
    Configuration object which describes the environment of a simulation (route, competition).
    """

    model_config = ConfigDict(frozen=True)

    competition_config: (
        CompetitionConfig  # The competition that data is being requisitioned for
    )
