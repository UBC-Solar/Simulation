"""
The `model` module is the core of Simulation, containing the primary simulation logic.

1. `ModelBuilder`: a utility class for assembling and compiling a `Model` from its necessary configuration.
2. `Model`: a model of our solar-powered vehicles, complete with physical components and competition environment.
3. `Simulation`: the result of simulating a `Model` with an input speed array.
4. `LapProfile`: one lap's track data, for lap mode.
5. `schedule_laps` / `ScheduledLap`: lap mode's timing, when each lap starts and ends.
"""

from .Simulation import Simulation
from .Model import Model
from .ModelBuilder import ModelBuilder
from .LapProfile import LapProfile
from .LapSchedule import ScheduledLap, schedule_laps

__all__ = [
    "Simulation",
    "Model",
    "ModelBuilder",
    "LapProfile",
    "ScheduledLap",
    "schedule_laps",
]
