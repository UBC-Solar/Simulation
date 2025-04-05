from simulation.config import Config
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any

ConfigType = TypeVar("ConfigType", bound=Config)

class Query(Generic[ConfigType], ABC):
    """
    A `Query` encapsulates access to some external API.

    An implementation of `Query` must be parameterized by some `Config` subclass which should entirely describe
    the details of the data required, which is then required to instantiate an instance of the `Query`.

    The `make` method can then be used to invoke the `Query` and acquire and marshall the requested data.
    """

    def __init__(self, config: ConfigType):
        self._config: ConfigType = config

    @abstractmethod
    def make(self) -> Any:
        """
        Invoke this `Query` to acquire and marshall the requested data.
        """
        raise NotImplementedError
