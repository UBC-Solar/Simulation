from simulation.cache import Cache
from dill import Unpickler, Pickler
from io import BytesIO
from typing import Any
import pathlib
import shelve
import pickle
import os


class DillShelf(shelve.DbfilenameShelf):
    """
    A drop-in replacement for the default `Shelf` from the `shelve` module which uses `dill` for serialization
    and deserialization rather than `pickle`.
    """
    # NOTE: ALL of this code is copied from the CPython 3.13 implementation of `Shelf` class in `shelve/shelf.py`, with
    # references to `pickle` replaced with `dill`. That is, don't blame ME for your IDE complaining.
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


class FSCache(Cache):
    """
    FSCache is an implementation of the `Cache` interface using `dill` for serialization, which permits
    any arbitrary object to be stored without loss of functionality.

    FSCache uses the `shelve` module to create a simple filesystem persistent cache.

    FSCache is not thread-safe.
    """
    def __init__(self, shelve_dir: pathlib.Path):
        self._shelve_dir = shelve_dir / "cache"

    def get(self, file_path: os.PathLike):
        with DillShelf(self._shelve_dir, protocol=pickle.HIGHEST_PROTOCOL) as db:
            return db[str(file_path)]

    def put(self, obj: Any, file_path: os.PathLike):
        with DillShelf(self._shelve_dir, protocol=pickle.HIGHEST_PROTOCOL) as db:
            db[str(file_path)] = obj


SimulationCache: Cache = FSCache(pathlib.Path(__file__).parent)
