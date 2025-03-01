from .cache import (
    query_npz_from_cache,
    store_npz_to_cache,
    FSCache,
    Cache
)

import pathlib

simulation_cache: Cache = FSCache(pathlib.Path(__file__).parent)
