from dotenv import load_dotenv
from simulation.config import Config
from abc import ABC, abstractmethod
from typing import TypeVar


load_dotenv()


ConfigType = TypeVar('ConfigType', bound=Config)


class Query[ConfigType](ABC):
    def __init__(self, config: ConfigType):
        self._config: ConfigType = config

    @abstractmethod
    def make(self):
        raise NotImplementedError
