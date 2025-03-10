import pathlib
import pickle
from io import BytesIO

import numpy as np
import os
from pathlib import Path
from pickle import UnpicklingError
from typing import Dict, Union, TypeAlias, Any
from abc import ABC, abstractmethod
import shelve
from dill import Unpickler, Pickler

HashLike: TypeAlias = Union[str, list, np.ndarray, int]


class DillShelf(shelve.DbfilenameShelf):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        try:
            value = self.cache[key]
        except KeyError:
            f = BytesIO(self.dict[key.encode(self.keyencoding)])
            value = Unpickler(f).load()
            if self.writeback:
                self.cache[key] = value
        return value

    def __setitem__(self, key, value):
        if self.writeback:
            self.cache[key] = value
        f = BytesIO()
        p = Pickler(f, self._protocol)
        p.dump(value)
        self.dict[key.encode(self.keyencoding)] = f.getvalue()


class Cache(ABC):
    """
    An interface to a persistent storage system
    """
    @abstractmethod
    def get(self, file_path: os.PathLike) -> Any:
        raise NotImplementedError

    @abstractmethod
    def put(self, obj: Any, file_path: os.PathLike):
        raise NotImplementedError


class FSCache(Cache):
    def __init__(self, shelve_dir: pathlib.Path):
        self._shelve_dir = shelve_dir

    def get(self, file_path: os.PathLike):
        with DillShelf(self._shelve_dir, protocol=pickle.HIGHEST_PROTOCOL) as db:
            return db[str(file_path)]

    def put(self, obj: Any, file_path: os.PathLike):
        with DillShelf(self._shelve_dir, protocol=pickle.HIGHEST_PROTOCOL) as db:
            db[str(file_path)] = obj
