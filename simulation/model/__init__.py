"""
The `model` module is the core of Simulation, containing the primary simulation logic.

1. `ModelBuilder`: a utility class for assembling and compiling a `Model` from its necessary configuration.
2. `Model`: a model of our solar-powered vehicles, complete with physical components and competition environment.
3. `Simulation`: the result of simulating a `Model` with an input speed array.
4. `LapGIS`: the track, with one lap's data in a consistent shape for lap mode.
5. `LapSchedule`: lap mode's timing, when each lap starts and ends.
"""

from .Simulation import Simulation
from .Model import Model
from .ModelBuilder import ModelBuilder
from .LapGIS import LapGIS
from .LapSchedule import LapSchedule

__all__ = [
    "Simulation",
    "Model",
    "ModelBuilder",
    "LapGIS",
    "LapSchedule",
]
