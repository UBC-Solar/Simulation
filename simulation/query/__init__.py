"""
The `query` module provides high-level querying abstractions for accessing and marshalling data
acquired from external APIs from configuration objects.

The `Query` class defines an interface where an instance of a subclass can be instantiated with a `Config` object
which can then be invoked with the `make` method to acquire data necessary, as described by the `Config` object.

Existing implementations of the `Query` interface include,
    - `TrackRouteQuery`: to query data for a track race as described by a `CompetitionConfig` using the Google Maps API.
    - `RoadRouteQuery`: to query data for a road race as described by a `CompetitionConfig` using the Google Maps API.
    - `SolcastQuery`: to query weather forecasts as described by a `EnvironmentConfig` using the Solcast API.
    - `OpenweatherQuery`: to query weather forecasts as described by a `EnvironmentConfig` using the Openweathermap API.
"""

from ._query import Query, ConfigType

from ._gis import RoadRouteQuery, TrackRouteQuery

from ._weather import SolcastQuery, OpenweatherQuery

__all__ = [
    "Query",
    "ConfigType",
    "RoadRouteQuery",
    "TrackRouteQuery",
    "SolcastQuery",
    "OpenweatherQuery",
]
