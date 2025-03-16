from abc import ABC, abstractmethod
from typing import Any
import pathlib
import os


RoutePath: pathlib.Path = pathlib.Path("route")
WeatherPath: pathlib.Path = pathlib.Path("weather")
RacePath: pathlib.Path = pathlib.Path("race")


class Cache(ABC):
    """
    An interface to a persistent storage system with simple `get` and `put` methods.
    """
    @abstractmethod
    def get(self, file_path: os.PathLike) -> Any:
        """
        Get the object stored and uniquely identified by `file_path`.

        Any errors related to deserialization should be considered cache corruption.

        :param file_path: the identifier which maps to the object desired
        :return: the object, if it can be found
        :raises KeyError: if there is no object corresponding to `file_path`.
        """
        raise NotImplementedError

    @abstractmethod
    def put(self, obj: Any, file_path: os.PathLike) -> None:
        """
        Store an object to be retrieved with the identifier `file_path`.

        Will overwrite, without warning or error, if an object is already mapped to `file_path`.

        :param obj: the object to be stored.
        :param file_path: the identifier to map `obj` to.
        """
        raise NotImplementedError
