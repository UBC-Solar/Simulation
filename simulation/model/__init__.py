"""
The `model` module is the core of Simulation, containing the primary simulation logic.

1. `ModelBuilder`: a utility class for assembling and compiling a `Model` from its necessary configuration.
2. `Model`: a model of our solar-powered vehicles, complete with physical components and competition environment.
3. `Simulation`: the result of simulating a `Model` with an input speed array.
"""
from .Simulation import Simulation
from .Model import Model
from .ModelBuilder import ModelBuilder

__all__ = [
    "Simulation",
    "Model",
    "ModelBuilder"
]
