"""
The `cache` module provides simple constructs and methods for persistent data storage and retrieval.

The `Cache` class defines a straightforward interface to store data with a `put(object, location)` and retrieve
with `get(location)`.

The `FSCache` class implements the aforementioned interface using `dill` for object serialization
of arbitrary objects without loss of functionality and the `shelve` module for persistent storage.

Additionally, this module defines a few locations: `RoutePath`, `WeatherPath`, and `RacePath` for route data,
weather data, and race data, as well as a static instantiation of the `FSCache` intended for use by other modules
in Simulation, `SimulationCache`.

As an example,

>>> from simulation.cache import SimulationCache
>>> obj = MyComplexObject()
>>> dir(obj)
many_complex_methods, a_lot_of_custom_fields, anything_else
>>> SimulationCache.put(obj, "my_location")
>>> retrieved_obj = SimulationCache.get("my_location")
>>> dir(retrieved_obj)
many_complex_methods, a_lot_of_custom_fields, anything_else

"""

from ._cache import Cache, RoutePath, WeatherPath, RacePath

from ._fs_cache import FSCache, SimulationCache


__all__ = [
    "Cache",
    "FSCache",
    "SimulationCache",
    "RoutePath",
    "RacePath",
    "WeatherPath",
]
